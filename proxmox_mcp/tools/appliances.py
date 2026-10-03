"""Appliance deployment: FortiGate-VM (KVM image) as a ready-to-boot QEMU VM."""

from __future__ import annotations

import asyncio
import os
import re
from typing import Any
from urllib.parse import urlparse

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
