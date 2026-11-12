"""Deploy an OS by asking: Ubuntu, Kali, Windows 11 and Proxmox Datacenter Manager VMs.

Each tool fetches the official image (checksum-verified, cached on storage and reused), builds a
seed ISO with the first-boot settings (cloud-init `cidata`, or Windows' `autounattend.xml`),
creates and starts the VM, waits until its guest agent answers, reports how to reach it, and
deletes the seed ISO, which holds the credentials. Part of the `appliances` toolset.
"""

from __future__ import annotations

import asyncio
import hashlib
import io
import ipaddress
import json
import os
import re
import secrets
import string
import tarfile
import tempfile
from typing import Any
from urllib.parse import quote
from xml.sax.saxutils import escape

import httpx

from .. import qcow2, seediso

NODE = {"type": "string", "description": "Node name (e.g. pve01)"}
OPT_STR = lambda desc: {"type": "string", "description": desc}  # noqa: E731
OPT_INT = lambda desc: {"type": "integer", "description": desc}  # noqa: E731
OPT_BOOL = lambda desc: {"type": "boolean", "description": desc}  # noqa: E731

READY_TIMEOUT = float(os.getenv("PROXMOX_WAIT_TIMEOUT", "900"))

# Official images. `sums` is the checksum list published next to the image.
CATALOG: dict[str, dict[str, Any]] = {
    "ubuntu": {
        "label": "Ubuntu 24.04 LTS (cloud image)",
        "url": "https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img",
        "sums": "https://cloud-images.ubuntu.com/noble/current/SHA256SUMS",
        "algorithm": "sha256",
        # Proxmox's import storage accepts .qcow2/.raw/.vmdk; the .img is qcow2.
        "filename": "noble-server-cloudimg-amd64.qcow2",
        "user": "ubuntu",
    },
    "debian": {
        "label": "Debian 13 (cloud image, base for Datacenter Manager)",
        "url": "https://cloud.debian.org/images/cloud/trixie/latest/debian-13-genericcloud-amd64.qcow2",
        "sums": "https://cloud.debian.org/images/cloud/trixie/latest/SHA512SUMS",
        "algorithm": "sha512",
        "filename": "debian-13-genericcloud-amd64.qcow2",
        "user": "debian",
    },
    "kali": {
        "label": "Kali Linux (cloud image)",
        "index": "https://kali.download/cloud-images/current/",
        "sums": "https://kali.download/cloud-images/current/SHA256SUMS",
        "algorithm": "sha256",
        "pattern": r"kali-linux-[\d.]+-cloud-genericcloud-amd64\.tar\.xz",
        "user": "kali",
    },
    "virtio-win": {
        "label": "VirtIO drivers for Windows (Fedora)",
        "url": "https://fedorapeople.org/groups/virt/virtio-win/direct-downloads/stable-virtio/virtio-win.iso",
        "filename": "virtio-win.iso",
    },
}

PDM_REPO = """Types: deb
URIs: http://download.proxmox.com/debian/pdm
Suites: trixie
Components: pdm-no-subscription
Signed-By: /usr/share/keyrings/proxmox-archive-keyring.gpg
"""
PDM_KEYRING = "https://enterprise.proxmox.com/debian/proxmox-archive-keyring-trixie.gpg"

# --- tool definitions ---


def _linux_props(os_key: str, default_name: str, disk_gb: int, memory: int) -> dict[str, Any]:
    user = CATALOG["debian" if os_key == "pdm" else os_key]["user"]
    return {
        "node": NODE,
        "name": OPT_STR(f"VM name and hostname (default {default_name})"),
        "vmid": OPT_INT("VM ID (default: the next free one)"),
        "cores": OPT_INT("vCPUs (default 2)"),
        "memory": OPT_INT(f"RAM in MB (default {memory})"),
        "disk_gb": OPT_INT(f"Disk size in GB (default {disk_gb})"),
        "disk_storage": OPT_STR("Storage for the VM's disk (default local-lvm)"),
        "image_storage": OPT_STR("Storage for the cached image and the seed ISO (default local)"),
        "bridge": OPT_STR("Bridge for the NIC (default vmbr0)"),
        "vlan": OPT_INT("VLAN tag for the NIC"),
        "ip": OPT_STR("Static address in CIDR form, e.g. 10.0.0.30/24 (default: DHCP)"),
        "gateway": OPT_STR("Default gateway, with ip"),
        "nameservers": OPT_STR("DNS servers, comma-separated, with ip"),
        "username": OPT_STR(f"Login user (default {user})"),
        "ssh_public_keys": OPT_STR(
            "SSH public key(s), one per line. Without one, a password is generated and returned once"
        ),
        "onboot": OPT_BOOL("Start with the host (default false)"),
        "tags": OPT_STR("Tags, ';'-separated"),
        "description": OPT_STR("VM description"),
        "wait_until_ready": OPT_BOOL(
            "Wait until the guest agent answers and report the address (default true)"
        ),
        "ready_timeout": OPT_INT("Seconds to wait for that (default PROXMOX_WAIT_TIMEOUT, 900)"),
    }


TOOLS = [
    {
        "name": "deploy_ubuntu_vm",
        "description": (
            "Create an Ubuntu 24.04 LTS VM just by asking: fetches the official cloud image (checksum "
            "verified, cached and reused), sets the user with your SSH key or a generated password "
            "(returned once), installs the guest agent, starts it, and reports its IP when it's ready."
        ),
        "inputSchema": {"type": "object", "properties": _linux_props("ubuntu", "ubuntu", 20, 2048), "required": ["node"]},
    },
    {
        "name": "deploy_kali_vm",
        "description": (
            "Create a Kali Linux VM just by asking: downloads Kali's official cloud image (checksum "
            "verified), repacks its sparse 25 GiB disk as qcow2 so only the ~1 GiB of data is "
            "uploaded, sets the user with your SSH key or a generated password (returned once), "
            "installs the guest agent, starts it, and reports its IP when it's ready."
        ),
        "inputSchema": {"type": "object", "properties": _linux_props("kali", "kali", 32, 4096), "required": ["node"]},
    },
    {
        "name": "deploy_pdm_vm",
        "description": (
            "Create a Proxmox Datacenter Manager just by asking: a Debian 13 VM (official cloud image) "
            "where cloud-init installs PDM from Proxmox's no-subscription repository. Sets the root "
            "password (generated and returned once) for the web UI, and when ready reports "
            "https://<ip>:8443 and the login."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                **_linux_props("pdm", "pdm", 16, 2048),
                "root_password": OPT_STR("Password for root@pam, the web UI login (default: generated)"),
            },
            "required": ["node"],
        },
    },
    {
        "name": "deploy_windows11_vm",
        "description": (
            "Create a Windows 11 VM just by asking: q35 with UEFI, Secure Boot keys, TPM 2.0 and VirtIO "
            "disk and network, installed unattended from a Windows 11 ISO already on storage (found "
            "automatically; Microsoft has no stable download link) with VirtIO drivers and guest "
            "tools. Creates a local administrator with a generated password (returned once). Installs "
            "Windows 11 Pro without activation by default. Setup takes 20 to 40 minutes."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "name": OPT_STR("VM name (default windows11)"),
                "vmid": OPT_INT("VM ID (default: the next free one)"),
                "iso": OPT_STR("Windows 11 ISO volume (default: the first one found, e.g. local:iso/Win11_25H2_English_x64.iso)"),
                "virtio_iso": OPT_STR("VirtIO drivers ISO volume (default: one on storage, else downloaded)"),
                "cores": OPT_INT("vCPUs (default 4)"),
                "memory": OPT_INT("RAM in MB (default 8192)"),
                "disk_gb": OPT_INT("Disk size in GB (default 64, Windows 11's minimum)"),
                "disk_storage": OPT_STR("Storage for the disk, EFI vars and TPM state (default local-lvm)"),
                "iso_storage": OPT_STR("Storage for the VirtIO and seed ISOs (default local)"),
                "bridge": OPT_STR("Bridge for the NIC (default vmbr0)"),
                "vlan": OPT_INT("VLAN tag for the NIC"),
                "edition": OPT_STR("Edition to install (default 'Windows 11 Pro')"),
                "computer_name": OPT_STR("Windows computer name, 15 characters at most (default: from name)"),
                "username": OPT_STR("Local administrator to create (default admin)"),
                "password": OPT_STR("Its password (default: generated)"),
                "timezone": OPT_STR("Windows time zone ID (default UTC)"),
                "locale": OPT_STR("Language and locale (default en-US)"),
                "onboot": OPT_BOOL("Start with the host (default false)"),
                "tags": OPT_STR("Tags, ';'-separated"),
                "description": OPT_STR("VM description"),
                "wait_until_ready": OPT_BOOL("Wait until setup finishes and the guest agent answers (default true)"),
                "ready_timeout": OPT_INT("Seconds to wait for that (default PROXMOX_WAIT_TIMEOUT, 900)"),
            },
            "required": ["node"],
        },
    },
    {
        "name": "list_os_images",
        "description": (
            "OS images the deploy tools use: which are cached on the node's storage, and with "
            "check_upstream, the latest official version of each."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": NODE,
                "check_upstream": OPT_BOOL("Also fetch the latest official versions (default false)"),
            },
            "required": ["node"],
        },
    },
]

NAMES = frozenset(t["name"] for t in TOOLS)

# --- helpers ---


def generate_password(length: int = 20) -> str:
    """A password with upper, lower, digit and symbol characters (Windows' complexity rule),
    without characters that need quoting in XML, YAML or a shell."""
    symbols = "-_.@%+="
    pools = [string.ascii_uppercase, string.ascii_lowercase, string.digits, symbols]
    chars = [secrets.choice(pool) for pool in pools]
    alphabet = "".join(pools)
    chars += [secrets.choice(alphabet) for _ in range(length - len(chars))]
    secrets.SystemRandom().shuffle(chars)
    return "".join(chars)


async def _fetch_text(url: str) -> str:
    async with httpx.AsyncClient(timeout=60, follow_redirects=True) as http:
        response = await http.get(url)
        response.raise_for_status()
        return response.text


def checksum_from(sums: str, filename: str) -> str:
    """The hash for filename in a SHA*SUMS file ("hash  name" or "hash *name")."""
    for line in sums.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1].lstrip("*") == filename:
            return parts[0].lower()
    raise ValueError(f"{filename} isn't in the published checksum list")


async def _wait_task(client: Any, node: str, response: Any, timeout: float) -> None:
    from .appliances import wait_task

    upid = (response or {}).get("data")
    if isinstance(upid, str) and upid.startswith("UPID:"):
        await wait_task(client, node, upid, timeout=timeout)


async def _volumes(client: Any, node: str, storage: str, content: str) -> list[str]:
    data = (await client.get(f"/nodes/{node}/storage/{storage}/content", {"content": content})).get("data") or []
    return [item["volid"] for item in data if isinstance(item, dict) and "volid" in item]


async def _all_isos(client: Any, node: str) -> list[str]:
    storages = (await client.get(f"/nodes/{node}/storage", {"content": "iso"})).get("data") or []
    found: list[str] = []
    for s in storages:
        if isinstance(s, dict) and s.get("storage"):
            found += await _volumes(client, node, s["storage"], "iso")
    return found


async def ensure_image(client: Any, node: str, storage: str, os_key: str, steps: list[str]) -> str:
    """The import volume for os_key's cloud image, downloaded and checked if not cached."""
    entry = CATALOG[os_key]
    cached = await _volumes(client, node, storage, "import")
    if os_key == "kali":
        sums = await _fetch_text(entry["sums"])
        archive = next(iter(re.findall(entry["pattern"], sums)), None)
        if not archive:
            raise ValueError("Kali's checksum list names no amd64 cloud image")
        filename = archive.removesuffix(".tar.xz") + ".qcow2"
        volid = f"{storage}:import/{filename}"
        if volid in cached:
            steps.append(f"reused cached {volid}")
            return volid
        await _repack_kali(client, node, storage, entry["index"] + archive, checksum_from(sums, archive), filename)
        steps.append(f"downloaded {archive}, repacked as qcow2 and uploaded as {volid}")
        return volid

    volid = f"{storage}:import/{entry['filename']}"
    if volid in cached:
        steps.append(f"reused cached {volid}")
        return volid
    sums = await _fetch_text(entry["sums"])
    upstream_name = os.path.basename(entry["url"])
    response = await client.post(
        f"/nodes/{node}/storage/{storage}/download-url",
        {
            "url": entry["url"],
            "content": "import",
            "filename": entry["filename"],
            "checksum": checksum_from(sums, upstream_name),
            "checksum-algorithm": entry["algorithm"],
        },
    )
    await _wait_task(client, node, response, timeout=1800)
    steps.append(f"downloaded {upstream_name} (checksum verified) as {volid}")
    return volid


def _repack(archive_path: str, out_path: str) -> dict[str, int]:
    """disk.raw from Kali's .tar.xz, as qcow2. GNU sparse entries read their holes as zeros."""
    with tarfile.open(archive_path, "r:xz") as tar:
        member = next((m for m in tar if m.name.endswith(".raw")), None)
        if member is None:
            raise ValueError("no .raw disk in the Kali archive")
        src = tar.extractfile(member)
        if src is None:
            raise ValueError("the Kali disk entry isn't a file")
        with open(out_path, "wb") as out:
            return qcow2.write(src, member.size, out)


async def _repack_kali(client: Any, node: str, storage: str, url: str, sha256: str, filename: str) -> None:
    with tempfile.TemporaryDirectory(prefix="kali-") as tmp:
        archive = os.path.join(tmp, "kali.tar.xz")
        digest = hashlib.sha256()
        async with httpx.AsyncClient(timeout=None, follow_redirects=True) as http:
            async with http.stream("GET", url) as response:
                response.raise_for_status()
                with open(archive, "wb") as f:
                    async for chunk in response.aiter_bytes(1 << 20):
                        digest.update(chunk)
                        f.write(chunk)
        if digest.hexdigest() != sha256:
            raise ValueError(f"Kali image checksum mismatch: expected {sha256}, got {digest.hexdigest()}")
        out = os.path.join(tmp, filename)
        await asyncio.to_thread(_repack, archive, out)
        with open(out, "rb") as f:
            response = await client.upload(node, storage, "import", filename, f)
        await _wait_task(client, node, response, timeout=1800)


async def _upload_seed(client: Any, node: str, storage: str, vmid: int, iso: bytes) -> str:
    filename = f"seed-{vmid}-{secrets.token_hex(4)}.iso"
    response = await client.upload(node, storage, "iso", filename, io.BytesIO(iso), timeout=300)
    await _wait_task(client, node, response, timeout=300)
    return f"{storage}:iso/{filename}"


async def _check_free(client: Any, node: str, name: str, vmid: Any) -> int:
    existing = (await client.get("/cluster/resources", {"type": "vm"})).get("data") or []
    if any(vm.get("name") == name for vm in existing):
        raise ValueError(f"A guest named {name} already exists; pick another name")
    if vmid:
        if any(int(vm.get("vmid", 0)) == int(vmid) for vm in existing):
            raise ValueError(f"VMID {vmid} is in use")
        return int(vmid)
    return int((await client.get("/cluster/nextid")).get("data"))


def _nic(args: dict[str, Any]) -> str:
    spec = f"virtio,bridge={args.get('bridge', 'vmbr0')}"
    if args.get("vlan") not in (None, ""):
        spec += f",tag={int(args['vlan'])}"
    return spec


def _network_config(args: dict[str, Any]) -> dict[str, Any]:
    eth: dict[str, Any] = {"match": {"name": "e*"}, "set-name": "eth0"}
    if args.get("ip"):
        iface = ipaddress.ip_interface(args["ip"])
        if iface.network.prefixlen == iface.max_prefixlen:
            raise ValueError(f"ip needs a prefix length, e.g. {iface.ip}/24")
        eth["addresses"] = [str(iface)]
        if args.get("gateway"):
            eth["routes"] = [{"to": "default", "via": str(ipaddress.ip_address(args["gateway"]))}]
        if args.get("nameservers"):
            eth["nameservers"] = {"addresses": [s.strip() for s in args["nameservers"].split(",") if s.strip()]}
    else:
        eth["dhcp4"] = True
    return {"version": 2, "ethernets": {"eth0": eth}}


def cloud_init_seed(
    hostname: str,
    user: str,
    password: str | None,
    keys: list[str],
    network: dict[str, Any],
    extra: dict[str, Any] | None = None,
) -> bytes:
    """A NoCloud `cidata` ISO. YAML is a superset of JSON, so the documents are JSON."""
    account: dict[str, Any] = {
        "name": user,
        "groups": ["sudo"],
        "shell": "/bin/bash",
        "sudo": "ALL=(ALL) NOPASSWD:ALL",
        "lock_passwd": password is None,
    }
    if password:
        account["plain_text_passwd"] = password
    if keys:
        account["ssh_authorized_keys"] = keys
    config: dict[str, Any] = {
        "hostname": hostname,
        "users": [account],
        "ssh_pwauth": bool(password),
        "package_update": True,
        "packages": ["qemu-guest-agent"],
        "runcmd": [["systemctl", "enable", "--now", "qemu-guest-agent"]],
    }
    for key, value in (extra or {}).items():
        if key in ("packages", "runcmd", "write_files"):
            config[key] = config.get(key, []) + value
        else:
            config[key] = value
    files = {
        "user-data": ("#cloud-config\n" + json.dumps(config, indent=1)).encode(),
        "meta-data": json.dumps({"instance-id": f"iid-{secrets.token_hex(8)}", "local-hostname": hostname}).encode(),
        "network-config": json.dumps(network, indent=1).encode(),
    }
    return seediso.build("cidata", files)


def pdm_extra(hostname: str, root_password: str) -> dict[str, Any]:
    """cloud-init additions that install Datacenter Manager on Debian 13."""
    script = " && ".join(
        [
            "export DEBIAN_FRONTEND=noninteractive",
            "echo 'postfix postfix/main_mailer_type select Local only' | debconf-set-selections",
            f"echo 'postfix postfix/mailname string {hostname}' | debconf-set-selections",
            f"curl -fsSL {PDM_KEYRING} -o /usr/share/keyrings/proxmox-archive-keyring.gpg",
            "apt-get update",
            "apt-get install -y proxmox-datacenter-manager proxmox-datacenter-manager-ui",
            # The package adds the enterprise repository, which needs a subscription.
            "rm -f /etc/apt/sources.list.d/pdm-enterprise.sources",
        ]
    )
    return {
        "packages": ["curl", "ca-certificates"],
        "write_files": [{"path": "/etc/apt/sources.list.d/pdm.sources", "content": PDM_REPO}],
        "chpasswd": {"expire": False, "users": [{"name": "root", "password": root_password, "type": "text"}]},
        "runcmd": [["bash", "-c", script]],
    }


def autounattend(
    edition: str,
    computer_name: str,
    username: str,
    password: str,
    timezone: str,
    locale: str,
) -> bytes:
    """Windows 11 unattended setup: VirtIO storage driver, UEFI GPT disk, local admin, guest tools."""
    values = {"edition": edition, "computer": computer_name, "user": username, "pw": password,
              "tz": timezone, "loc": locale}
    x = {k: escape(v) for k, v in values.items()}
    arch = 'processorArchitecture="amd64" publicKeyToken="31bf3856ad364e35" language="neutral" versionScope="nonSxS" xmlns:wcm="http://schemas.microsoft.com/WMIConfig/2002/State"'
    driver_paths = "".join(
        f'<PathAndCredentials wcm:action="add" wcm:keyValue="{i}"><Path>{letter}:\\{drv}\\w11\\amd64</Path></PathAndCredentials>'
        for i, (letter, drv) in enumerate(
            ((letter, drv) for letter in "DEFG" for drv in ("vioscsi", "viostor", "NetKVM")), start=1
        )
    )
    tools = (
        'cmd /c "for %d in (D E F G H) do if exist %d:\\virtio-win-guest-tools.exe '
        'start /wait %d:\\virtio-win-guest-tools.exe /install /quiet /norestart"'
    )
    xml = f"""<?xml version="1.0" encoding="utf-8"?>
<unattend xmlns="urn:schemas-microsoft-com:unattend">
 <settings pass="windowsPE">
  <component name="Microsoft-Windows-International-Core-WinPE" {arch}>
   <SetupUILanguage><UILanguage>{x['loc']}</UILanguage></SetupUILanguage>
   <InputLocale>{x['loc']}</InputLocale><SystemLocale>{x['loc']}</SystemLocale>
   <UILanguage>{x['loc']}</UILanguage><UserLocale>{x['loc']}</UserLocale>
  </component>
  <component name="Microsoft-Windows-PnpCustomizationsWinPE" {arch}>
   <DriverPaths>{driver_paths}</DriverPaths>
  </component>
  <component name="Microsoft-Windows-Setup" {arch}>
   <DiskConfiguration>
    <Disk wcm:action="add">
     <DiskID>0</DiskID><WillWipeDisk>true</WillWipeDisk>
     <CreatePartitions>
      <CreatePartition wcm:action="add"><Order>1</Order><Type>EFI</Type><Size>260</Size></CreatePartition>
      <CreatePartition wcm:action="add"><Order>2</Order><Type>MSR</Type><Size>16</Size></CreatePartition>
      <CreatePartition wcm:action="add"><Order>3</Order><Type>Primary</Type><Extend>true</Extend></CreatePartition>
     </CreatePartitions>
     <ModifyPartitions>
      <ModifyPartition wcm:action="add"><Order>1</Order><PartitionID>1</PartitionID><Format>FAT32</Format><Label>System</Label></ModifyPartition>
      <ModifyPartition wcm:action="add"><Order>2</Order><PartitionID>2</PartitionID></ModifyPartition>
      <ModifyPartition wcm:action="add"><Order>3</Order><PartitionID>3</PartitionID><Format>NTFS</Format><Label>Windows</Label><Letter>C</Letter></ModifyPartition>
     </ModifyPartitions>
    </Disk>
   </DiskConfiguration>
   <ImageInstall>
    <OSImage>
     <InstallFrom><MetaData wcm:action="add"><Key>/IMAGE/NAME</Key><Value>{x['edition']}</Value></MetaData></InstallFrom>
     <InstallTo><DiskID>0</DiskID><PartitionID>3</PartitionID></InstallTo>
    </OSImage>
   </ImageInstall>
   <UserData><AcceptEula>true</AcceptEula></UserData>
  </component>
 </settings>
 <settings pass="specialize">
  <component name="Microsoft-Windows-Shell-Setup" {arch}>
   <ComputerName>{x['computer']}</ComputerName><TimeZone>{x['tz']}</TimeZone>
  </component>
 </settings>
 <settings pass="oobeSystem">
  <component name="Microsoft-Windows-International-Core" {arch}>
   <InputLocale>{x['loc']}</InputLocale><SystemLocale>{x['loc']}</SystemLocale>
   <UILanguage>{x['loc']}</UILanguage><UserLocale>{x['loc']}</UserLocale>
  </component>
  <component name="Microsoft-Windows-Shell-Setup" {arch}>
   <OOBE>
    <HideEULAPage>true</HideEULAPage><HideOEMRegistrationScreen>true</HideOEMRegistrationScreen>
    <HideOnlineAccountScreens>true</HideOnlineAccountScreens><HideWirelessSetupInOOBE>true</HideWirelessSetupInOOBE>
    <ProtectYourPC>3</ProtectYourPC>
   </OOBE>
   <UserAccounts>
    <LocalAccounts>
     <LocalAccount wcm:action="add">
      <Name>{x['user']}</Name><Group>Administrators</Group>
      <Password><Value>{x['pw']}</Value><PlainText>true</PlainText></Password>
     </LocalAccount>
    </LocalAccounts>
   </UserAccounts>
   <AutoLogon>
    <Enabled>true</Enabled><LogonCount>1</LogonCount><Username>{x['user']}</Username>
    <Password><Value>{x['pw']}</Value><PlainText>true</PlainText></Password>
   </AutoLogon>
   <FirstLogonCommands>
    <SynchronousCommand wcm:action="add"><Order>1</Order><CommandLine>{escape(tools)}</CommandLine><Description>VirtIO guest tools and agent</Description></SynchronousCommand>
   </FirstLogonCommands>
  </component>
 </settings>
</unattend>
"""
    return seediso.build("autounattend", {"autounattend.xml": xml.encode("utf-8")})


async def _agent_ready(client: Any, node: str, vmid: int, timeout: float) -> bool:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while loop.time() < deadline:
        try:
            await client.post(f"/nodes/{node}/qemu/{vmid}/agent/ping")
            return True
        except Exception:
            await asyncio.sleep(5)
    return False


async def _guest_ipv4(client: Any, node: str, vmid: int) -> str | None:
    try:
        data = (await client.get(f"/nodes/{node}/qemu/{vmid}/agent/network-get-interfaces")).get("data") or {}
    except Exception:
        return None
    for iface in data.get("result") or []:
        for addr in iface.get("ip-addresses") or []:
            ip = addr.get("ip-address", "")
            if addr.get("ip-address-type") == "ipv4" and not ip.startswith(("127.", "169.254.")):
                return str(ip)
    return None


async def _agent_run(client: Any, node: str, vmid: int, command: list[str], timeout: float) -> int | None:
    """Run a command through the guest agent; its exit code, or None if it didn't finish."""
    pid = ((await client.post(f"/nodes/{node}/qemu/{vmid}/agent/exec", {"command": command})).get("data") or {}).get("pid")
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while loop.time() < deadline:
        status = (await client.get(f"/nodes/{node}/qemu/{vmid}/agent/exec-status", {"pid": pid})).get("data") or {}
        if status.get("exited"):
            return int(status.get("exitcode", 1))
        await asyncio.sleep(5)
    return None


async def _remove_seed(client: Any, node: str, vmid: int, slot: str, volid: str) -> None:
    await client.put(f"/nodes/{node}/qemu/{vmid}/config", {"delete": slot})
    storage = volid.split(":", 1)[0]
    await client.delete(f"/nodes/{node}/storage/{storage}/content/{quote(volid, safe='')}")


# --- the tools ---


async def deploy_linux(os_key: str, args: dict[str, Any], client: Any) -> dict[str, Any]:
    node = args["node"]
    image_os = "debian" if os_key == "pdm" else os_key
    name = args.get("name") or os_key
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]{0,62}", name):
        raise ValueError("name must be a hostname: letters, digits and hyphens")
    keys = [k.strip() for k in (args.get("ssh_public_keys") or "").splitlines() if k.strip()]
    user = args.get("username") or CATALOG[image_os]["user"]
    network = _network_config(args)  # validates ip and gateway before anything is created
    password = None if keys else generate_password()
    root_password = (args.get("root_password") or generate_password()) if os_key == "pdm" else None
    timeout = float(READY_TIMEOUT if args.get("ready_timeout") is None else args["ready_timeout"])

    vmid = await _check_free(client, node, name, args.get("vmid"))
    steps: list[str] = []
    image_storage = args.get("image_storage", "local")
    image = await ensure_image(client, node, image_storage, image_os, steps)
    extra = pdm_extra(name, root_password) if root_password else None
    seed = await _upload_seed(client, node, image_storage, vmid,
                              cloud_init_seed(name, user, password, keys, network, extra))
    steps.append(f"built and uploaded seed ISO {seed}")

    disk_storage = args.get("disk_storage", "local-lvm")
    defaults = {"ubuntu": (2048, 20), "kali": (4096, 32), "pdm": (2048, 16)}[os_key]
    config: dict[str, Any] = {
        "vmid": vmid,
        "name": name,
        "ostype": "l26",
        "cpu": "host",
        "cores": int(args.get("cores", 2)),
        "memory": int(args.get("memory", defaults[0])),
        "scsihw": "virtio-scsi-single",
        "scsi0": f"{disk_storage}:0,import-from={image},discard=on,iothread=1",
        "ide2": f"{seed},media=cdrom",
        "boot": "order=scsi0",
        "agent": "enabled=1",
        "net0": _nic(args),
        "serial0": "socket",
        "onboot": 1 if args.get("onboot") else 0,
        "tags": args.get("tags", f"{os_key};deployed"),
    }
    if args.get("description"):
        config["description"] = args["description"]
    await _wait_task(client, node, await client.post(f"/nodes/{node}/qemu", config), timeout=1800)
    disk_gb = int(args.get("disk_gb", defaults[1]))
    await _wait_task(client, node, await client.put(f"/nodes/{node}/qemu/{vmid}/resize",
                                                   {"disk": "scsi0", "size": f"{disk_gb}G"}), timeout=300)
    await _wait_task(client, node, await client.post(f"/nodes/{node}/qemu/{vmid}/status/start"), timeout=120)
    steps += [f"created VM {vmid} ({disk_gb} GB disk)", "started"]

    out: dict[str, Any] = {"vmid": vmid, "name": name, "node": node, "user": user}
    if password:
        out["password"] = password
    if keys:
        out["ssh_keys"] = len(keys)
    if os_key == "pdm":
        out["web_login"] = {"user": "root@pam", "password": root_password}
    if args.get("wait_until_ready", True):
        if await _agent_ready(client, node, vmid, timeout):
            out["ip"] = await _guest_ipv4(client, node, vmid)
            if os_key == "pdm":
                code = await _agent_run(client, node, vmid, ["cloud-init", "status", "--wait"], timeout)
                active = await _agent_run(client, node, vmid, ["systemctl", "is-active", "proxmox-datacenter-api"], 60)
                out["pdm_ready"] = code == 0 and active == 0
                if out.get("ip"):
                    out["url"] = f"https://{out['ip']}:8443"
            await _remove_seed(client, node, vmid, "ide2", seed)
            steps.append("guest agent answered; seed ISO removed")
            out["status"] = "ready"
        else:
            out["status"] = "starting"
            out["note"] = (f"The guest agent didn't answer within {timeout:.0f}s. The seed ISO {seed} holds "
                           "the credentials: once the VM is up, detach it (ide2) and delete it.")
    else:
        out["status"] = "starting"
        out["note"] = f"Not waiting. Detach and delete the seed ISO {seed} (ide2) once the VM is up: it holds the credentials."
    out["steps"] = steps
    return out


async def deploy_windows11(args: dict[str, Any], client: Any) -> dict[str, Any]:
    node = args["node"]
    name = args.get("name") or "windows11"
    computer = (args.get("computer_name") or re.sub(r"[^A-Za-z0-9-]", "", name))[:15] or "WIN11"
    password = args.get("password") or generate_password()
    username = args.get("username") or "admin"
    timeout = float(READY_TIMEOUT if args.get("ready_timeout") is None else args["ready_timeout"])
    iso_storage = args.get("iso_storage", "local")
    disk_storage = args.get("disk_storage", "local-lvm")
    steps: list[str] = []

    isos = await _all_isos(client, node)
    iso = args.get("iso") or next((v for v in isos if re.search(r"win(dows)?[ _-]?11", v, re.I)), None)
    if not iso:
        raise ValueError(
            "No Windows 11 ISO on the node's storage. Download one from Microsoft (microsoft.com/software-download/windows11) "
            "and upload it, or pass iso"
        )
    vmid = await _check_free(client, node, name, args.get("vmid"))
    virtio = args.get("virtio_iso") or next((v for v in isos if re.search(r"virtio-win", v, re.I)), None)
    if not virtio:
        entry = CATALOG["virtio-win"]
        response = await client.post(f"/nodes/{node}/storage/{iso_storage}/download-url",
                                     {"url": entry["url"], "content": "iso", "filename": entry["filename"]})
        await _wait_task(client, node, response, timeout=1800)
        virtio = f"{iso_storage}:iso/{entry['filename']}"
        steps.append(f"downloaded VirtIO drivers as {virtio}")
    seed = await _upload_seed(client, node, iso_storage, vmid, autounattend(
        args.get("edition") or "Windows 11 Pro", computer, username, password,
        args.get("timezone") or "UTC", args.get("locale") or "en-US",
    ))
    steps.append(f"built and uploaded autounattend ISO {seed}")

    config: dict[str, Any] = {
        "vmid": vmid,
        "name": name,
        "ostype": "win11",
        "machine": "q35",
        "bios": "ovmf",
        "cpu": "host",
        "cores": int(args.get("cores", 4)),
        "memory": int(args.get("memory", 8192)),
        "scsihw": "virtio-scsi-single",
        "efidisk0": f"{disk_storage}:1,efitype=4m,pre-enrolled-keys=1",
        "tpmstate0": f"{disk_storage}:1,version=v2.0",
        "scsi0": f"{disk_storage}:{int(args.get('disk_gb', 64))},iothread=1,discard=on",
        "ide2": f"{iso},media=cdrom",
        "ide0": f"{virtio},media=cdrom",
        "ide1": f"{seed},media=cdrom",
        "boot": "order=ide2;scsi0",
        "net0": _nic(args),
        "agent": "enabled=1",
        "onboot": 1 if args.get("onboot") else 0,
        "tags": args.get("tags", "windows11;deployed"),
    }
    if args.get("description"):
        config["description"] = args["description"]
    await _wait_task(client, node, await client.post(f"/nodes/{node}/qemu", config), timeout=900)
    await _wait_task(client, node, await client.post(f"/nodes/{node}/qemu/{vmid}/status/start"), timeout=120)
    # The Windows ISO waits for a key press before booting ("Press any key to boot from CD").
    for _ in range(8):
        await asyncio.sleep(1.5)
        try:
            await client.put(f"/nodes/{node}/qemu/{vmid}/sendkey", {"key": "ret"})
        except Exception:
            pass
    steps += [f"created VM {vmid} (UEFI, Secure Boot keys, TPM 2.0)", "started and answered the boot prompt"]

    out: dict[str, Any] = {
        "vmid": vmid, "name": name, "node": node, "computer_name": computer,
        "username": username, "password": password,
        "license": "Installed without a product key: activate it with your own license.",
    }
    if args.get("wait_until_ready", True) and await _agent_ready(client, node, vmid, timeout):
        out["ip"] = await _guest_ipv4(client, node, vmid)
        await _remove_seed(client, node, vmid, "ide1", seed)
        steps.append("setup finished, guest agent answered; autounattend ISO removed")
        out["status"] = "ready"
    else:
        out["status"] = "installing"
        out["note"] = (
            "Windows Setup takes 20 to 40 minutes. When vm_agent_ping answers, setup is done: then detach "
            f"ide1 and delete {seed}, which holds the password."
        )
    out["steps"] = steps
    return out


async def list_os_images(args: dict[str, Any], client: Any) -> dict[str, Any]:
    node = args["node"]
    storages = (await client.get(f"/nodes/{node}/storage")).get("data") or []
    cached: list[str] = []
    for s in storages:
        content = str((s or {}).get("content", ""))
        for kind in ("import", "iso"):
            if kind in content.split(","):
                cached += await _volumes(client, node, s["storage"], kind)
    images: dict[str, Any] = {}
    patterns = {
        "ubuntu": r"noble-server-cloudimg",
        "debian": r"debian-13-genericcloud",
        "kali": r"kali-linux-.*cloud",
        "virtio-win": r"virtio-win",
        "windows11": r"win(dows)?[ _-]?11",
    }
    for key, pattern in patterns.items():
        images[key] = {
            "label": CATALOG[key]["label"] if key in CATALOG else "Windows 11 ISO (bring your own)",
            "cached": [v for v in cached if re.search(pattern, v, re.I)],
        }
    if args.get("check_upstream"):
        for key in ("ubuntu", "debian", "kali"):
            try:
                sums = await _fetch_text(CATALOG[key]["sums"])
                if key == "kali":
                    latest = next(iter(re.findall(CATALOG[key]["pattern"], sums)), None)
                else:
                    latest = os.path.basename(CATALOG[key]["url"])
                images[key]["latest"] = latest
                images[key]["checksum"] = checksum_from(sums, latest) if latest else None
            except Exception as e:  # report, don't fail the listing
                images[key]["latest_error"] = str(e) or type(e).__name__
    return {"node": node, "images": images}


async def handle(name: str, args: dict[str, Any], client: Any) -> Any:
    if name == "deploy_ubuntu_vm":
        return await deploy_linux("ubuntu", args, client)
    if name == "deploy_kali_vm":
        return await deploy_linux("kali", args, client)
    if name == "deploy_pdm_vm":
        return await deploy_linux("pdm", args, client)
    if name == "deploy_windows11_vm":
        return await deploy_windows11(args, client)
    if name == "list_os_images":
        return await list_os_images(args, client)
    raise ValueError(f"Unknown tool: {name}")
