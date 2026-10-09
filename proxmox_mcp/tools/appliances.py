"""Appliance deployment: FortiGate-VM (KVM image) and cloud-image VMs ready for a cluster."""

from __future__ import annotations

import asyncio
import ipaddress
import os
import re
from typing import Any
from urllib.parse import quote, urlparse

from ..client import ProxmoxClient

NODE = {"type": "string", "description": "Node name (e.g. pve01)"}
OPT_STR = lambda desc: {"type": "string", "description": desc}  # noqa: E731
OPT_INT = lambda desc: {"type": "integer", "description": desc}  # noqa: E731
OPT_BOOL = lambda desc: {"type": "boolean", "description": desc}  # noqa: E731

# The free FortiGate-VM permanent evaluation license (FGVMEV) caps the VM at these.
EVAL_MAX_CORES = 1
EVAL_MAX_MEMORY_MB = 2048
EVAL_MAX_INTERFACES = 3

TOOLS = [
    {
        "name": "deploy_fortigate_vm",
        "description": (
            "Deploy a FortiGate-VM from Fortinet's KVM qcow2 image: import the disk, create the VM "
            "with a WAN NIC (port1) and optional LAN/extra NICs (port2, port3...) on chosen bridges "
            "and VLANs, wait for the import, and optionally start it. Give either image (an "
            "import-content volume such as local:import/fortios.qcow2) or image_url (a URL of the "
            ".qcow2 itself; Fortinet's download is a .zip, so unzip it and serve the qcow2). "
            "Defaults (1 vCPU, 2 GB) fit the free permanent evaluation license, which allows at most "
            "3 interfaces. Returns each FortiGate port with its MAC so you can reserve DHCP leases."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "vmid": OPT_INT("VM ID (omit to use the next free one)"),
                "name": OPT_STR("VM name (default fortigate)"),
                "image": OPT_STR("Existing import volume, e.g. local:import/fortios.qcow2"),
                "image_url": OPT_STR("URL of the FortiGate .qcow2 to download first (instead of image)"),
                "image_storage": OPT_STR("Storage to download image_url into (default local; needs the import content type)"),
                "disk_storage": OPT_STR("Storage for the VM disks (default local-lvm)"),
                "wan_bridge": OPT_STR("Bridge for port1 / WAN (default vmbr0)"),
                "wan_vlan": OPT_INT("VLAN tag for port1"),
                "lan_bridge": OPT_STR("Bridge for port2 / LAN (omit for a single-port VM)"),
                "lan_vlan": OPT_INT("VLAN tag for port2"),
                "extra_nics": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "More ports as 'bridge' or 'bridge:vlan', e.g. ['vmbr1:160'] for port3",
                },
                "cores": OPT_INT("vCPUs (default 1; the evaluation license allows 1)"),
                "memory": OPT_INT("RAM in MB (default 2048; the evaluation license allows 2048)"),
                "log_disk_gb": OPT_INT("Add a second disk of this size for FortiGate logs (optional)"),
                "start": OPT_BOOL("Start the VM when done (default true)"),
                "onboot": OPT_BOOL("Start with the host (default false)"),
                "tags": OPT_STR("Tags (default fortigate)"),
                "description": OPT_STR("VM description"),
            },
            "required": ["node"],
        },
    },
    {
        "name": "deploy_cloud_vms",
        "description": (
            "Create one or more VMs from a cloud image (for example Ubuntu's noble-server-cloudimg qcow2 in "
            "local:import) with cloud-init: user, SSH public key, and a static IP per VM (or DHCP). Imports "
            "the disk, grows it, starts each VM and waits for the start task. Returns VMIDs, names, MACs and "
            "the IPs given. It does not wait for SSH: check reachability from the machine that will connect "
            "(for example k3s-mcp-server's plan_cluster). Refuses a name or VMID that already exists."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "names": {"type": "array", "items": {"type": "string"},
                          "description": "One VM name per VM, e.g. ['k3s-test-1', 'k3s-test-2', 'k3s-test-3']"},
                "image": OPT_STR("Cloud image import volume, e.g. local:import/noble-server-cloudimg-amd64.qcow2"),
                "ip_addresses": {"type": "array", "items": {"type": "string"},
                                 "description": "Static address per VM in CIDR form, e.g. ['10.0.0.21/24', ...], "
                                                "in the same order as names. Omit for DHCP."},
                "gateway": OPT_STR("Default gateway for the static addresses"),
                "nameserver": OPT_STR("DNS server(s), space-separated (default: the node's)"),
                "searchdomain": OPT_STR("DNS search domain"),
                "ssh_public_keys": OPT_STR("Public key(s) for the cloud-init user, one per line (required)"),
                "ciuser": OPT_STR("Cloud-init user (default ubuntu)"),
                "bridge": OPT_STR("Bridge for net0 (default vmbr0)"),
                "vlan": OPT_INT("VLAN tag for net0"),
                "first_vmid": OPT_INT("VMID for the first VM; the rest count up from it (default: next free)"),
                "cores": OPT_INT("vCPUs per VM (default 2)"),
                "memory": OPT_INT("RAM per VM in MB (default 2048)"),
                "disk_gb": OPT_INT("Grow the boot disk to this size in GB (default 20)"),
                "disk_storage": OPT_STR("Storage for disks and the cloud-init drive (default local-lvm)"),
                "start": OPT_BOOL("Start the VMs (default true)"),
                "onboot": OPT_BOOL("Start with the host (default false)"),
                "tags": OPT_STR("Tags, ';'-separated (default cloud)"),
                "description": OPT_STR("VM description"),
            },
            "required": ["node", "names", "image", "ssh_public_keys"],
        },
    },
]


async def wait_task(client: ProxmoxClient, node: str, upid: str, timeout: float = 600, poll: float = 2) -> dict[str, Any]:
    """Poll a task until it stops; raise if it fails or times out."""
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while True:
        status = (await client.get(f"/nodes/{node}/tasks/{upid}/status")).get("data") or {}
        if status.get("status") == "stopped":
            if status.get("exitstatus") != "OK":
                raise RuntimeError(f"Task {upid} failed: {status.get('exitstatus')}")
            return status
        if loop.time() > deadline:
            raise TimeoutError(f"Task {upid} still running after {timeout:.0f}s")
        await asyncio.sleep(poll)


def _nic(bridge: str, vlan: Any = None) -> str:
    spec = f"virtio,bridge={bridge}"
    if vlan not in (None, ""):
        spec += f",tag={int(vlan)}"
    return spec


def _filename(url: str) -> str:
    name = os.path.basename(urlparse(url).path) or "fortios.qcow2"
    if not re.search(r"\.(qcow2|raw|vmdk|img)$", name):
        raise ValueError(f"image_url must point at a disk image (.qcow2/.raw/.vmdk/.img), not {name!r}")
    return name


async def handle(name: str, args: dict[str, Any], client: ProxmoxClient) -> Any:
    if name == "deploy_cloud_vms":
        return await deploy_cloud_vms(args, client)
    if name != "deploy_fortigate_vm":
        raise ValueError(f"Unknown tool: {name}")

    node = args["node"]
    if bool(args.get("image")) == bool(args.get("image_url")):
        raise ValueError("Give exactly one of image (an import volume) or image_url")

    nics = [_nic(args.get("wan_bridge", "vmbr0"), args.get("wan_vlan"))]
    if args.get("lan_bridge"):
        nics.append(_nic(args["lan_bridge"], args.get("lan_vlan")))
    for extra in args.get("extra_nics") or []:
        bridge, _, vlan = extra.partition(":")
        nics.append(_nic(bridge, vlan or None))
    if len(nics) > 8:
        raise ValueError("At most 8 NICs")

    cores = args.get("cores", EVAL_MAX_CORES)
    memory = args.get("memory", EVAL_MAX_MEMORY_MB)
    warnings = []
    if cores > EVAL_MAX_CORES or memory > EVAL_MAX_MEMORY_MB:
        warnings.append(
            f"The free evaluation license uses at most {EVAL_MAX_CORES} vCPU and {EVAL_MAX_MEMORY_MB} MB; "
            "extra resources only help with a paid license."
        )
    if len(nics) > EVAL_MAX_INTERFACES:
        warnings.append(f"The free evaluation license allows at most {EVAL_MAX_INTERFACES} configured interfaces.")

    steps = []
    image = args.get("image")
    if args.get("image_url"):
        storage = args.get("image_storage", "local")
        filename = _filename(args["image_url"])
        upid = (await client.post(f"/nodes/{node}/storage/{storage}/download-url",
                                  {"url": args["image_url"], "content": "import", "filename": filename})).get("data")
        await wait_task(client, node, upid, timeout=1800)
        image = f"{storage}:import/{filename}"
        steps.append(f"downloaded {image}")

    vmid = args.get("vmid") or int((await client.get("/cluster/nextid")).get("data"))
    disk_storage = args.get("disk_storage", "local-lvm")
    config: dict[str, Any] = {
        "vmid": vmid,
        "name": args.get("name", "fortigate"),
        "ostype": "l26",
        "cpu": "host",
        "cores": cores,
        "memory": memory,
        "scsihw": "virtio-scsi-pci",
        "scsi0": f"{disk_storage}:0,import-from={image}",
        "boot": "order=scsi0",
        "serial0": "socket",
        "onboot": 1 if args.get("onboot") else 0,
        "tags": args.get("tags", "fortigate"),
    }
    for i, spec in enumerate(nics):
        config[f"net{i}"] = spec
    if args.get("log_disk_gb"):
        config["scsi1"] = f"{disk_storage}:{int(args['log_disk_gb'])}"
    if args.get("description"):
        config["description"] = args["description"]

    upid = (await client.post(f"/nodes/{node}/qemu", config)).get("data")
    await wait_task(client, node, upid, timeout=900)
    steps.append(f"created VM {vmid} with disk imported from {image}")

    if args.get("start", True):
        upid = (await client.post(f"/nodes/{node}/qemu/{vmid}/status/start")).get("data")
        await wait_task(client, node, upid, timeout=120)
        steps.append("started")

    cfg = (await client.get(f"/nodes/{node}/qemu/{vmid}/config")).get("data") or {}
    ports = []
    for i in range(len(nics)):
        net = cfg.get(f"net{i}", "")
        mac = re.search(r"=((?:[0-9A-F]{2}:){5}[0-9A-F]{2})", net, re.I)
        tag = re.search(r"tag=(\d+)", net)
        bridge = re.search(r"bridge=([^,]+)", net)
        ports.append({"port": f"port{i + 1}", "nic": f"net{i}", "mac": mac.group(1).lower() if mac else None,
                      "bridge": bridge.group(1) if bridge else None, "vlan": int(tag.group(1)) if tag else None})

    out: dict[str, Any] = {
        "vmid": vmid,
        "name": config["name"],
        "node": node,
        "ports": ports,
        "steps": steps,
        "next_steps": [
            "Open the VM console and log in as admin with an empty password; FortiOS asks for a new one "
            "(12+ chars with upper, lower, number and symbol).",
            "port1 starts as a DHCP client on FortiGate-VM KVM images; find its address in your DHCP "
            "server using port1's MAC above, or run 'get system interface physical' on the console.",
            "Until it is licensed the GUI goes blank after login and most API calls return 401: activate "
            "the free permanent evaluation license with your FortiCloud account (GUI license page, or "
            "fortigate-mcp-server's activate_vm_eval_license).",
        ],
    }
    if warnings:
        out["warnings"] = warnings
    return out


def _mac(net: str) -> str | None:
    found = re.search(r"=((?:[0-9A-F]{2}:){5}[0-9A-F]{2})", net, re.I)
    return found.group(1).lower() if found else None


async def _maybe_wait(client: ProxmoxClient, node: str, response: Any, timeout: float) -> None:
    """Wait for a task when the API returned one (some calls are synchronous)."""
    upid = (response or {}).get("data")
    if isinstance(upid, str) and upid.startswith("UPID:"):
        await wait_task(client, node, upid, timeout=timeout)


async def deploy_cloud_vms(args: dict[str, Any], client: ProxmoxClient) -> dict[str, Any]:
    node = args["node"]
    names = list(args.get("names") or [])
    if not names:
        raise ValueError("names must list at least one VM name")
    if len(set(names)) != len(names):
        raise ValueError("names must be unique")
    keys = (args.get("ssh_public_keys") or "").strip()
    if not keys:
        raise ValueError("ssh_public_keys is required: cloud images have no password login")

    ips = list(args.get("ip_addresses") or [])
    if ips and len(ips) != len(names):
        raise ValueError(f"ip_addresses has {len(ips)} entries for {len(names)} names")
    for ip in ips:
        iface = ipaddress.ip_interface(ip)  # raises on a bad address
        if iface.network.prefixlen == iface.max_prefixlen:
            raise ValueError(f"{ip} needs a prefix length, e.g. {iface.ip}/24")
    gateway = args.get("gateway")
    if gateway:
        ipaddress.ip_address(gateway)

    existing = (await client.get("/cluster/resources", {"type": "vm"})).get("data") or []
    taken_names = {vm.get("name") for vm in existing}
    taken_ids = {int(vm["vmid"]) for vm in existing if "vmid" in vm}
    clash = [n for n in names if n in taken_names]
    if clash:
        raise ValueError(f"VMs already named {', '.join(clash)}; pick other names")

    first = args.get("first_vmid") or int((await client.get("/cluster/nextid")).get("data"))
    vmids = list(range(int(first), int(first) + len(names)))
    used = [v for v in vmids if v in taken_ids]
    if used:
        raise ValueError(f"VMIDs {', '.join(map(str, used))} are in use; choose another first_vmid")

    storage = args.get("disk_storage", "local-lvm")
    nic = _nic(args.get("bridge", "vmbr0"), args.get("vlan"))
    disk_gb = int(args.get("disk_gb", 20))
    vms = []
    for i, (vm_name, vmid) in enumerate(zip(names, vmids, strict=True)):
        ipconfig = f"ip={ips[i]}" + (f",gw={gateway}" if gateway else "") if ips else "ip=dhcp"
        config: dict[str, Any] = {
            "vmid": vmid,
            "name": vm_name,
            "ostype": "l26",
            "cpu": "host",
            "cores": int(args.get("cores", 2)),
            "memory": int(args.get("memory", 2048)),
            "scsihw": "virtio-scsi-pci",
            "scsi0": f"{storage}:0,import-from={args['image']},discard=on",
            "ide2": f"{storage}:cloudinit",
            "boot": "order=scsi0",
            "serial0": "socket",
            "vga": "serial0",
            "agent": "enabled=1",
            "net0": nic,
            "ciuser": args.get("ciuser", "ubuntu"),
            # Proxmox wants the keys URL-encoded, spaces and newlines included
            "sshkeys": quote(keys, safe=""),
            "ipconfig0": ipconfig,
            "onboot": 1 if args.get("onboot") else 0,
            "tags": args.get("tags", "cloud"),
        }
        for key in ("nameserver", "searchdomain", "description"):
            if args.get(key):
                config[key] = args[key]

        await _maybe_wait(client, node, await client.post(f"/nodes/{node}/qemu", config), timeout=900)
        await _maybe_wait(client, node, await client.put(f"/nodes/{node}/qemu/{vmid}/resize",
                                                         {"disk": "scsi0", "size": f"{disk_gb}G"}), timeout=300)
        steps = [f"created from {args['image']}", f"disk grown to {disk_gb}G"]
        if args.get("start", True):
            await _maybe_wait(client, node, await client.post(f"/nodes/{node}/qemu/{vmid}/status/start"), timeout=120)
            steps.append("started")

        cfg = (await client.get(f"/nodes/{node}/qemu/{vmid}/config")).get("data") or {}
        vms.append({
            "vmid": vmid,
            "name": vm_name,
            "ip": str(ipaddress.ip_interface(ips[i]).ip) if ips else None,
            "mac": _mac(cfg.get("net0", "")),
            "steps": steps,
        })

    out: dict[str, Any] = {"node": node, "network": nic.removeprefix("virtio,"), "vms": vms}
    if not ips:
        out["note"] = ("DHCP: the addresses aren't known yet. Read them from your DHCP server by MAC, or with "
                       "vm_agent_get_network_interfaces once a guest agent runs in the VMs.")
    return out
