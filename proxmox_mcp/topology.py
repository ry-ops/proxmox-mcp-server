"""Cluster topology as a graph: hosts, interfaces, bridges, guests, storage and SDN, and how they connect.

Proxmox spreads this over many endpoints (cluster status and resources, each node's network,
each guest's config, storage definitions, SDN VNets, HA resources). get_cluster_topology
reads them all and returns one graph, so a client can draw the lab or check it for drift
without stitching dozens of calls together.

Node ids reuse Proxmox's own resource ids where there is one (node/pve1, qemu/100, lxc/101,
storage/pve1/local), and add iface/<node>/<name>, bridge/<node>/<name> and vnet/<name>.
"""

from __future__ import annotations

import asyncio
import re
from typing import Any

from .client import ProxmoxClient

_GUEST_NET = re.compile(r"^net\d+$")
_GUEST_DISK = re.compile(r"^(scsi|virtio|sata|ide|efidisk|tpmstate|unused)\d+$|^rootfs$|^mp\d+$")
_MAC = re.compile(r"([0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5})")
_SIZE = re.compile(r"(?:^|,)size=([^,]+)")
_PHYSICAL = {"eth", "bond", "OVSBond", "OVSIntPort", "vlan", "fabric"}
_BRIDGES = {"bridge", "OVSBridge"}


def _kv(value: str) -> dict[str, str]:
    """Parse Proxmox's key=value,key=value property strings. A bare first item keeps its own key."""
    out: dict[str, str] = {}
    for part in str(value).split(","):
        if "=" in part:
            k, v = part.split("=", 1)
            out[k.strip()] = v.strip()
        elif part.strip():
            out.setdefault("_", part.strip())
    return out


def parse_guest_nic(key: str, value: str, kind: str) -> dict[str, Any]:
    """One guest NIC: netN=virtio=MAC,bridge=vmbr0,tag=10 (QEMU) or name=eth0,bridge=...,hwaddr=... (LXC)."""
    kv = _kv(value)
    model, mac = None, kv.get("hwaddr") or kv.get("macaddr")
    if kind == "qemu":
        for model_name in ("virtio", "e1000", "e1000e", "rtl8139", "vmxnet3"):
            if model_name in kv:
                model, mac = model_name, kv[model_name]
                break
    if not mac:
        m = _MAC.search(value)
        mac = m.group(1) if m else None
    nic: dict[str, Any] = {
        "nic": key,
        "bridge": kv.get("bridge"),
        "mac": mac.lower() if mac else None,
    }
    if model:
        nic["model"] = model
    if kind == "lxc" and kv.get("name"):
        nic["name"] = kv["name"]
    if kv.get("tag"):
        nic["vlan"] = int(kv["tag"]) if kv["tag"].isdigit() else kv["tag"]
    if kv.get("trunks"):
        nic["trunks"] = kv["trunks"]
    if kv.get("firewall") == "1":
        nic["firewall"] = True
    if kv.get("link_down") == "1":
        nic["link_down"] = True
    for k in ("ip", "ip6", "gw"):
        if kv.get(k):
            nic[k] = kv[k]
    return nic


def parse_guest_disk(key: str, value: str) -> dict[str, Any] | None:
    """One guest disk as {disk, storage, volume, size}; None for CD-ROMs, passthrough and bind mounts."""
    if "media=cdrom" in value:
        return None
    first = str(value).split(",", 1)[0]
    if ":" not in first or first.startswith("/"):
        return None
    storage, volume = first.split(":", 1)
    disk: dict[str, Any] = {"disk": key, "storage": storage, "volume": volume}
    m = _SIZE.search(value)
    if m:
        disk["size"] = m.group(1)
    return disk


async def _safe(coro: Any) -> Any:
    """Optional sections (SDN, HA) fail on clusters without them: treat a failure as empty."""
    try:
        res = await coro
    except Exception:  # noqa: BLE001 - an absent feature, not an error for the caller
        return []
    return res.get("data", res) if isinstance(res, dict) else res


async def build_topology(
    client: ProxmoxClient,
    node_filter: str | None = None,
    include_stopped: bool = True,
    include_storage: bool = True,
) -> dict[str, Any]:
    status, resources, storage_defs, vnets, ha = await asyncio.gather(
        _safe(client.get("/cluster/status")),
        _safe(client.get("/cluster/resources")),
        _safe(client.get("/storage")) if include_storage else asyncio.sleep(0, []),
        _safe(client.get("/cluster/sdn/vnets")),
        _safe(client.get("/cluster/ha/resources")),
    )
    cluster = next((s for s in status or [] if s.get("type") == "cluster"), None)
    member_ip = {s.get("name"): s.get("ip") for s in status or [] if s.get("type") == "node"}
    hosts = [
        r
        for r in resources or []
        if r.get("type") == "node" and (not node_filter or r.get("node") == node_filter)
    ]
    host_names = {h["node"] for h in hosts}
    guests = [
        r
        for r in resources or []
        if r.get("type") in ("qemu", "lxc")
        and r.get("node") in host_names
        and (include_stopped or r.get("status") == "running")
    ]
    shared = {s.get("storage"): bool(s.get("shared")) for s in storage_defs or []}
    stype = {s.get("storage"): s.get("type") for s in storage_defs or []}
    ha_ids = {h.get("sid") for h in ha or []}
    vnet_names = {v.get("vnet"): v for v in vnets or []}

    sem = asyncio.Semaphore(8)

    async def limited(path: str) -> Any:
        async with sem:
            return await _safe(client.get(path))

    online = [h["node"] for h in hosts if h.get("status") == "online"]
    nets, configs = await asyncio.gather(
        asyncio.gather(*(limited(f"/nodes/{n}/network") for n in online)),
        asyncio.gather(
            *(limited(f"/nodes/{g['node']}/{g['type']}/{g['vmid']}/config") for g in guests)
        ),
    )
    net_by_node = dict(zip(online, nets, strict=True))

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add_node(n: dict[str, Any]) -> None:
        if n["id"] not in seen:
            seen.add(n["id"])
            nodes.append({k: v for k, v in n.items() if v is not None})

    def add_edge(source: str, target: str, kind: str, **attrs: Any) -> None:
        edges.append(
            {
                "source": source,
                "target": target,
                "kind": kind,
                **{k: v for k, v in attrs.items() if v is not None},
            }
        )

    if cluster:
        add_node(
            {
                "id": f"cluster/{cluster.get('name')}",
                "kind": "cluster",
                "label": cluster.get("name"),
                "quorate": bool(cluster.get("quorate")),
                "nodes": cluster.get("nodes"),
            }
        )

    for h in hosts:
        hid = f"node/{h['node']}"
        add_node(
            {
                "id": hid,
                "kind": "host",
                "label": h["node"],
                "status": h.get("status"),
                "ip": member_ip.get(h["node"]),
                "cpus": h.get("maxcpu"),
                "memory": h.get("maxmem"),
            }
        )
        if cluster:
            add_edge(f"cluster/{cluster.get('name')}", hid, "member")
        for iface in net_by_node.get(h["node"]) or []:
            name, itype = iface.get("iface"), iface.get("type")
            if itype in _BRIDGES:
                iid = f"bridge/{h['node']}/{name}"
                add_node(
                    {
                        "id": iid,
                        "kind": "bridge",
                        "label": name,
                        "node": h["node"],
                        "type": itype,
                        "cidr": iface.get("cidr"),
                        "vlan_aware": bool(iface.get("bridge_vlan_aware")),
                        "vids": iface.get("bridge_vids"),
                        "active": bool(iface.get("active")),
                        "comment": iface.get("comments"),
                    }
                )
                add_edge(hid, iid, "has")
                for port in str(iface.get("bridge_ports") or iface.get("ovs_ports") or "").split():
                    add_edge(iid, f"iface/{h['node']}/{port}", "port")
            elif itype in _PHYSICAL or itype is None:
                iid = f"iface/{h['node']}/{name}"
                add_node(
                    {
                        "id": iid,
                        "kind": "interface",
                        "label": name,
                        "node": h["node"],
                        "type": itype,
                        "cidr": iface.get("cidr"),
                        "active": bool(iface.get("active")),
                        "bond_mode": iface.get("bond_mode"),
                        "comment": iface.get("comments"),
                    }
                )
                add_edge(hid, iid, "has")
                for slave in str(iface.get("slaves") or iface.get("ovs_bonds") or "").split():
                    add_edge(iid, f"iface/{h['node']}/{slave}", "bond_member")
                if itype == "vlan":
                    raw = iface.get("vlan-raw-device") or (
                        name.rsplit(".", 1)[0] if "." in name else None
                    )
                    vid = iface.get("vlan-id") or (name.rsplit(".", 1)[1] if "." in name else None)
                    if raw:
                        parent = (
                            f"bridge/{h['node']}/{raw}"
                            if any(
                                i.get("iface") == raw and i.get("type") in _BRIDGES
                                for i in net_by_node.get(h["node"]) or []
                            )
                            else f"iface/{h['node']}/{raw}"
                        )
                        add_edge(parent, iid, "vlan", vlan=int(vid) if str(vid).isdigit() else vid)

    for name, v in vnet_names.items():
        add_node(
            {
                "id": f"vnet/{name}",
                "kind": "vnet",
                "label": name,
                "zone": v.get("zone"),
                "vlan": v.get("tag"),
                "alias": v.get("alias"),
            }
        )

    if include_storage:
        for r in resources or []:
            if r.get("type") == "storage" and r.get("node") in host_names:
                sid = r.get("storage")
                is_shared = shared.get(sid, bool(r.get("shared")))
                nid = f"storage/{sid}" if is_shared else f"storage/{r['node']}/{sid}"
                add_node(
                    {
                        "id": nid,
                        "kind": "storage",
                        "label": sid,
                        "type": stype.get(sid) or r.get("plugintype"),
                        "shared": is_shared,
                        "content": r.get("content"),
                        "status": r.get("status"),
                        "used": r.get("disk"),
                        "total": r.get("maxdisk"),
                    }
                )
                add_edge(f"node/{r['node']}", nid, "storage")

    for g, cfg in zip(guests, configs, strict=True):
        cfg = cfg if isinstance(cfg, dict) else {}
        gid = f"{g['type']}/{g['vmid']}"
        nics = [
            parse_guest_nic(k, v, g["type"]) for k, v in sorted(cfg.items()) if _GUEST_NET.match(k)
        ]
        disks = [
            d
            for k, v in sorted(cfg.items())
            if _GUEST_DISK.match(k) and (d := parse_guest_disk(k, v))
        ]
        add_node(
            {
                "id": gid,
                "kind": g["type"],
                "label": g.get("name"),
                "vmid": g["vmid"],
                "node": g["node"],
                "status": g.get("status"),
                "template": bool(g.get("template")),
                "tags": g.get("tags"),
                "cpus": g.get("maxcpu"),
                "memory": g.get("maxmem"),
                "ostype": cfg.get("ostype"),
                "ha": gid.replace("qemu/", "vm:").replace("lxc/", "ct:") in ha_ids or None,
                "nics": nics,
                "disks": disks,
            }
        )
        add_edge(gid, f"node/{g['node']}", "runs_on")
        for nic in nics:
            br = nic.get("bridge")
            if not br:
                continue
            target = f"vnet/{br}" if br in vnet_names else f"bridge/{g['node']}/{br}"
            add_edge(
                gid,
                target,
                "nic",
                nic=nic["nic"],
                vlan=nic.get("vlan"),
                mac=nic.get("mac"),
                firewall=nic.get("firewall"),
                link_down=nic.get("link_down"),
            )
        if include_storage:
            for d in disks:
                st = d["storage"]
                target = f"storage/{st}" if shared.get(st) else f"storage/{g['node']}/{st}"
                add_edge(gid, target, "disk", disk=d["disk"], size=d.get("size"))

    edges = [e for e in edges if e["source"] in seen and e["target"] in seen]
    vlans = sorted({e["vlan"] for e in edges if isinstance(e.get("vlan"), int)})
    return {
        "summary": {
            "cluster": cluster.get("name") if cluster else None,
            "hosts": len(hosts),
            "guests": len(guests),
            "bridges": sum(n["kind"] == "bridge" for n in nodes),
            "storage": sum(n["kind"] == "storage" for n in nodes),
            "vnets": len(vnet_names),
            "vlans": vlans,
        },
        "nodes": nodes,
        "edges": edges,
    }


def _mid(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", s)


def to_mermaid(graph: dict[str, Any]) -> str:
    """A Mermaid flowchart: one subgraph per host, guests wired to their bridges with VLAN labels."""
    by_id = {n["id"]: n for n in graph["nodes"]}
    lines = ["flowchart TB"]
    shapes = {
        "host": ('[["', '"]]'),
        "bridge": ('{{"', '"}}'),
        "interface": ('(["', '"])'),
        "storage": ('[("', '")]'),
        "vnet": ('{{"', '"}}'),
        "cluster": ('(("', '"))'),
    }

    def label(n: dict[str, Any]) -> str:
        text = n.get("label") or n["id"]
        if n["kind"] in ("qemu", "lxc"):
            text = f"{text} ({n['kind'].upper()} {n['vmid']})"
        if n.get("cidr"):
            text += f"<br/>{n['cidr']}"
        return text.replace('"', "'")

    hosts = [n for n in graph["nodes"] if n["kind"] == "host"]
    placed: set[str] = set()
    for h in hosts:
        lines.append(f'  subgraph {_mid(h["id"])}_box["{h["label"]}"]')
        for n in graph["nodes"]:
            if (
                n.get("node") == h["label"]
                or n["id"] == h["id"]
                or n["id"].startswith(f"storage/{h['label']}/")
            ):
                o, c = shapes.get(n["kind"], ('["', '"]'))
                lines.append(f"    {_mid(n['id'])}{o}{label(n)}{c}")
                placed.add(n["id"])
        lines.append("  end")
    for n in graph["nodes"]:
        if n["id"] not in placed:
            o, c = shapes.get(n["kind"], ('["', '"]'))
            lines.append(f"  {_mid(n['id'])}{o}{label(n)}{c}")
    drawn: set[str] = set()
    for e in graph["edges"]:
        if e["kind"] == "runs_on" or e["source"] not in by_id or e["target"] not in by_id:
            continue
        if e.get("vlan") is not None:
            text = f"VLAN {e['vlan']}"
        elif e["kind"] == "nic":
            text = "untagged"
        else:
            text = "" if e["kind"] in ("has", "member", "storage", "disk") else e["kind"]
        arrow = "-.->" if e["kind"] in ("disk", "storage") else "-->"
        lbl = f"|{text}|" if text else ""
        line = f"  {_mid(e['source'])} {arrow}{lbl} {_mid(e['target'])}"
        if line not in drawn:  # a guest with three disks on one storage gets one line
            drawn.add(line)
            lines.append(line)
    return "\n".join(lines)
