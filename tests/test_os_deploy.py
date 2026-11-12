"""OS deploy tools: seed ISOs, the qcow2 repack, and each tool's steps against a fake Proxmox."""

import io
import json
import lzma
import os
import string
import tarfile
import xml.etree.ElementTree as ET

import pytest

from proxmox_mcp import qcow2, registry, seediso
from proxmox_mcp.tools import os_deploy

UBUNTU_SUMS = "aaa111 *noble-server-cloudimg-amd64.img\nbbb222 *other.img\n"
DEBIAN_SUMS = "ddd444  debian-13-genericcloud-amd64.qcow2\n"
KALI_SUMS = "kkk777  kali-linux-2026.3-cloud-genericcloud-amd64.tar.xz\n"
UPID = "UPID:pve01:0003A1B2:01C9D3E4:6720F0A1:qmcreate:120:root@pam:"


# --- building blocks ---


def test_seed_iso_round_trip():
    files = {"user-data": b"#cloud-config\n", "meta-data": b"instance-id: x\n", "network-config": b"{}"}
    label, read = seediso.read(seediso.build("cidata", files))
    assert label == "cidata" and read == files


def test_seed_iso_layout_is_iso9660():
    iso = seediso.build("autounattend", {"autounattend.xml": b"<unattend/>"})
    assert len(iso) % seediso.BLOCK == 0
    assert iso[16 * 2048 + 1 : 16 * 2048 + 6] == b"CD001"  # primary volume descriptor
    assert iso[16 * 2048 + 40 : 16 * 2048 + 52] == b"AUTOUNATTEND"
    assert iso[18 * 2048] == 255  # terminator


def test_qcow2_keeps_only_data():
    size = 600 * 1024 * 1024 + 4096  # spans two L2 tables, with a partial last cluster
    raw = bytearray(size)
    raw[0:5] = b"hello"
    raw[512 * 1024 * 1024 : 512 * 1024 * 1024 + 3] = b"abc"
    raw[-1] = 7
    out = io.BytesIO()
    result = qcow2.write(io.BytesIO(bytes(raw)), size, out)
    assert result["data_clusters"] == 3
    assert result["file_size"] < 2 * 1024 * 1024
    assert qcow2.read_cluster(out, 0)[:5] == b"hello"
    assert qcow2.read_cluster(out, (512 * 1024 * 1024) // qcow2.CLUSTER)[:3] == b"abc"
    assert qcow2.read_cluster(out, size // qcow2.CLUSTER)[size % qcow2.CLUSTER - 1] == 7
    assert qcow2.read_cluster(out, 1) == bytes(qcow2.CLUSTER)


def test_repack_reads_the_disk_from_a_tar_xz(tmp_path):
    disk = bytearray(3 * qcow2.CLUSTER)
    disk[qcow2.CLUSTER : qcow2.CLUSTER + 4] = b"kali"
    archive = tmp_path / "k.tar.xz"
    with tarfile.open(archive, "w:xz") as tar:
        info = tarfile.TarInfo("disk.raw")
        info.size = len(disk)
        tar.addfile(info, io.BytesIO(bytes(disk)))
    result = os_deploy._repack(str(archive), str(tmp_path / "k.qcow2"))
    assert result["data_clusters"] == 1
    with open(tmp_path / "k.qcow2", "rb") as f:
        assert qcow2.read_cluster(f, 1)[:4] == b"kali"


def test_generated_passwords_meet_windows_complexity():
    for _ in range(50):
        pw = os_deploy.generate_password()
        assert len(pw) == 20
        assert any(c in string.ascii_uppercase for c in pw) and any(c in string.ascii_lowercase for c in pw)
        assert any(c in string.digits for c in pw) and any(c in "-_.@%+=" for c in pw)
        assert not set(pw) & set("<>&'\"\\$`")


def test_checksum_from_both_list_styles():
    assert os_deploy.checksum_from(UBUNTU_SUMS, "noble-server-cloudimg-amd64.img") == "aaa111"
    assert os_deploy.checksum_from(DEBIAN_SUMS, "debian-13-genericcloud-amd64.qcow2") == "ddd444"
    with pytest.raises(ValueError, match="checksum list"):
        os_deploy.checksum_from(DEBIAN_SUMS, "missing.qcow2")


def user_data(iso):
    _, files = seediso.read(iso)
    text = files["user-data"].decode()
    assert text.startswith("#cloud-config\n")
    return json.loads(text.removeprefix("#cloud-config\n")), files


def test_cloud_init_seed_with_password_and_static_ip():
    net = os_deploy._network_config({"ip": "10.0.0.30/24", "gateway": "10.0.0.1", "nameservers": "1.1.1.1, 9.9.9.9"})
    data, files = user_data(os_deploy.cloud_init_seed("web", "ubuntu", "S3cret-pw", [], net))
    user = data["users"][0]
    assert user["name"] == "ubuntu" and user["plain_text_passwd"] == "S3cret-pw" and not user["lock_passwd"]
    assert data["ssh_pwauth"] is True and "qemu-guest-agent" in data["packages"]
    eth = json.loads(files["network-config"])["ethernets"]["eth0"]
    assert eth["addresses"] == ["10.0.0.30/24"] and eth["routes"][0]["via"] == "10.0.0.1"
    assert eth["nameservers"]["addresses"] == ["1.1.1.1", "9.9.9.9"]
    assert json.loads(files["meta-data"])["local-hostname"] == "web"


def test_cloud_init_seed_with_key_has_no_password():
    data, _ = user_data(os_deploy.cloud_init_seed("k", "kali", None, ["ssh-ed25519 AAA me"], {"version": 2}))
    user = data["users"][0]
    assert user["lock_passwd"] and "plain_text_passwd" not in user and data["ssh_pwauth"] is False
    assert user["ssh_authorized_keys"] == ["ssh-ed25519 AAA me"]


def test_pdm_seed_installs_datacenter_manager():
    extra = os_deploy.pdm_extra("pdm2", "Root-pw1")
    data, _ = user_data(os_deploy.cloud_init_seed("pdm2", "debian", "Pw-1x", [], {"version": 2}, extra))
    assert "qemu-guest-agent" in data["packages"] and "curl" in data["packages"]
    assert data["write_files"][0]["path"] == "/etc/apt/sources.list.d/pdm.sources"
    assert "pdm-no-subscription" in data["write_files"][0]["content"]
    assert data["chpasswd"]["users"] == [{"name": "root", "password": "Root-pw1", "type": "text"}]
    script = data["runcmd"][-1][-1]
    assert "proxmox-datacenter-manager proxmox-datacenter-manager-ui" in script
    assert "rm -f /etc/apt/sources.list.d/pdm-enterprise.sources" in script


def test_autounattend_is_valid_and_escaped():
    iso = os_deploy.autounattend("Windows 11 Pro", "WIN-01", "admin", "a<b&c", "UTC", "en-US")
    _, files = seediso.read(iso)
    root = ET.fromstring(files["autounattend.xml"])
    text = ET.tostring(root, encoding="unicode")
    assert "Windows 11 Pro" in text and "WIN-01" in text and "vioscsi" in text
    ns = {"u": "urn:schemas-microsoft-com:unattend"}
    passwords = [p.text for p in root.iterfind(".//u:Password/u:Value", ns)]
    assert passwords == ["a<b&c", "a<b&c"]  # the account and its one autologon, escaped in the file
    assert "virtio-win-guest-tools.exe" in text


def test_bad_ip_is_refused_before_anything_is_created():
    with pytest.raises(ValueError, match="prefix length"):
        os_deploy._network_config({"ip": "10.0.0.30"})


# --- the tools, against a fake Proxmox ---


class FakeProxmox:
    def __init__(self, isos=(), imports=(), vms=(), agent=True):
        self.calls = []
        self.isos = list(isos)
        self.imports = list(imports)
        self.vms = list(vms)
        self.agent = agent
        self.uploads = {}

    async def get(self, path, params=None):
        self.calls.append(("GET", path, params))
        if path == "/cluster/resources":
            return {"data": self.vms}
        if path == "/cluster/nextid":
            return {"data": "120"}
        if path.endswith("/storage"):
            return {"data": [{"storage": "local", "content": "iso,import,vztmpl"}]}
        if path.endswith("/content"):
            kind = (params or {}).get("content")
            return {"data": [{"volid": v} for v in (self.isos if kind == "iso" else self.imports)]}
        if path.endswith("/agent/network-get-interfaces"):
            return {"data": {"result": [
                {"name": "lo", "ip-addresses": [{"ip-address": "127.0.0.1", "ip-address-type": "ipv4"}]},
                {"name": "eth0", "ip-addresses": [{"ip-address": "10.0.0.77", "ip-address-type": "ipv4"}]},
            ]}}
        if path.endswith("/agent/exec-status"):
            return {"data": {"exited": 1, "exitcode": 0}}
        if "/tasks/" in path:
            return {"data": {"status": "stopped", "exitstatus": "OK"}}
        return {"data": {}}

    async def post(self, path, data=None):
        self.calls.append(("POST", path, data))
        if path.endswith("/agent/ping"):
            if not self.agent:
                raise RuntimeError("QEMU guest agent is not running")
            return {"data": {}}
        if path.endswith("/agent/exec"):
            return {"data": {"pid": 42}}
        return {"data": UPID}

    async def put(self, path, data=None):
        self.calls.append(("PUT", path, data))
        return {"data": UPID if path.endswith("/resize") else None}

    async def delete(self, path, params=None):
        self.calls.append(("DELETE", path, params))
        return {"data": None}

    async def upload(self, node, storage, content, filename, fileobj, timeout=3600):
        self.calls.append(("UPLOAD", f"{storage}:{content}/{filename}", None))
        self.uploads[filename] = fileobj.read()
        return {"data": UPID}

    def find(self, method, suffix):
        return [c for c in self.calls if c[0] == method and c[1].endswith(suffix)]


@pytest.fixture
def upstream(monkeypatch):
    sums = {
        os_deploy.CATALOG["ubuntu"]["sums"]: UBUNTU_SUMS,
        os_deploy.CATALOG["debian"]["sums"]: DEBIAN_SUMS,
        os_deploy.CATALOG["kali"]["sums"]: KALI_SUMS,
    }

    async def fetch(url):
        return sums[url]

    monkeypatch.setattr(os_deploy, "_fetch_text", fetch)
    monkeypatch.setattr(os_deploy.asyncio, "sleep", lambda *_: _done())


async def _done():
    return None


async def test_ubuntu_end_to_end(upstream):
    pve = FakeProxmox()
    out = await os_deploy.handle("deploy_ubuntu_vm", {"node": "pve01", "name": "web1"}, pve)
    download = pve.find("POST", "/download-url")[0][2]
    assert download["checksum"] == "aaa111" and download["checksum-algorithm"] == "sha256"
    assert download["filename"] == "noble-server-cloudimg-amd64.qcow2" and download["content"] == "import"
    config = pve.find("POST", "/nodes/pve01/qemu")[0][2]
    assert config["vmid"] == 120 and config["scsi0"].startswith("local-lvm:0,import-from=local:import/noble")
    assert config["ide2"].startswith("local:iso/seed-120-") and config["agent"] == "enabled=1"
    assert pve.find("PUT", "/resize")[0][2] == {"disk": "scsi0", "size": "20G"}
    seed_name = next(iter(pve.uploads))
    data, _ = user_data(pve.uploads[seed_name])
    assert data["users"][0]["plain_text_passwd"] == out["password"]
    assert out["status"] == "ready" and out["ip"] == "10.0.0.77" and out["user"] == "ubuntu"
    # The seed ISO holds the password: detached and deleted once the guest is up.
    assert pve.find("PUT", "/qemu/120/config")[0][2] == {"delete": "ide2"}
    assert pve.find("DELETE", f"local%3Aiso%2F{seed_name}")


async def test_cached_image_is_reused(upstream):
    pve = FakeProxmox(imports=["local:import/noble-server-cloudimg-amd64.qcow2"])
    out = await os_deploy.handle("deploy_ubuntu_vm", {"node": "pve01", "ssh_public_keys": "ssh-ed25519 AAA me"}, pve)
    assert not pve.find("POST", "/download-url") and "password" not in out and out["ssh_keys"] == 1
    assert any("reused cached" in s for s in out["steps"])


async def test_name_or_vmid_in_use_is_refused_before_anything_is_created(upstream):
    pve = FakeProxmox(vms=[{"name": "web1", "vmid": 101}])
    with pytest.raises(ValueError, match="already exists"):
        await os_deploy.handle("deploy_ubuntu_vm", {"node": "pve01", "name": "web1"}, pve)
    with pytest.raises(ValueError, match="in use"):
        await os_deploy.handle("deploy_ubuntu_vm", {"node": "pve01", "name": "web2", "vmid": 101}, pve)
    assert not [c for c in pve.calls if c[0] != "GET"]


async def test_pdm_reports_url_and_root_login(upstream):
    pve = FakeProxmox()
    out = await os_deploy.handle("deploy_pdm_vm", {"node": "pve01", "name": "pdm2"}, pve)
    assert pve.find("POST", "/download-url")[0][2]["checksum-algorithm"] == "sha512"
    assert out["url"] == "https://10.0.0.77:8443" and out["pdm_ready"] is True
    assert out["web_login"]["user"] == "root@pam" and len(out["web_login"]["password"]) == 20
    commands = [c[2]["command"] for c in pve.find("POST", "/agent/exec")]
    assert ["cloud-init", "status", "--wait"] in commands


async def test_kali_repacks_the_official_image(upstream, monkeypatch):
    seen = {}

    async def repack(client, node, storage, url, sha256, filename):
        seen.update(url=url, sha256=sha256, filename=filename)

    monkeypatch.setattr(os_deploy, "_repack_kali", repack)
    pve = FakeProxmox()
    out = await os_deploy.handle("deploy_kali_vm", {"node": "pve01"}, pve)
    assert seen == {
        "url": "https://kali.download/cloud-images/current/kali-linux-2026.3-cloud-genericcloud-amd64.tar.xz",
        "sha256": "kkk777",
        "filename": "kali-linux-2026.3-cloud-genericcloud-amd64.qcow2",
    }
    assert pve.find("PUT", "/resize")[0][2]["size"] == "32G" and out["user"] == "kali"


async def test_not_ready_keeps_the_seed_and_says_so(upstream):
    pve = FakeProxmox(agent=False)
    out = await os_deploy.handle("deploy_ubuntu_vm", {"node": "pve01", "ready_timeout": 0}, pve)
    assert out["status"] == "starting" and "seed ISO" in out["note"]
    assert not pve.find("DELETE", ".iso")


async def test_windows11_needs_an_iso(upstream):
    with pytest.raises(ValueError, match="No Windows 11 ISO"):
        await os_deploy.handle("deploy_windows11_vm", {"node": "pve01"}, FakeProxmox())


async def test_windows11_end_to_end(upstream):
    pve = FakeProxmox(isos=["local:iso/Win11_25H2_English_x64.iso", "local:iso/virtio-win-0.1.285.iso"])
    out = await os_deploy.handle("deploy_windows11_vm", {"node": "pve01", "name": "win-lab"}, pve)
    config = pve.find("POST", "/nodes/pve01/qemu")[0][2]
    assert config["ostype"] == "win11" and config["machine"] == "q35" and config["bios"] == "ovmf"
    assert config["tpmstate0"] == "local-lvm:1,version=v2.0"
    assert config["efidisk0"] == "local-lvm:1,efitype=4m,pre-enrolled-keys=1"
    assert config["ide2"] == "local:iso/Win11_25H2_English_x64.iso,media=cdrom"
    assert config["ide0"] == "local:iso/virtio-win-0.1.285.iso,media=cdrom"
    assert config["boot"] == "order=ide2;scsi0" and config["scsi0"].startswith("local-lvm:64,")
    assert len(pve.find("PUT", "/sendkey")) == 8  # "Press any key to boot from CD"
    assert not pve.find("POST", "/download-url")  # VirtIO ISO already on storage
    _, files = seediso.read(next(iter(pve.uploads.values())))
    assert out["password"] in files["autounattend.xml"].decode()
    assert out["status"] == "ready" and out["computer_name"] == "win-lab"
    assert pve.find("PUT", "/qemu/120/config")[0][2] == {"delete": "ide1"}


async def test_windows11_downloads_virtio_when_missing(upstream):
    pve = FakeProxmox(isos=["local:iso/Win11_25H2_English_x64.iso"], agent=False)
    out = await os_deploy.handle("deploy_windows11_vm", {"node": "pve01", "ready_timeout": 0}, pve)
    assert pve.find("POST", "/download-url")[0][2]["filename"] == "virtio-win.iso"
    assert out["status"] == "installing" and "20 to 40 minutes" in out["note"]


async def test_list_os_images(upstream):
    pve = FakeProxmox(isos=["local:iso/Win11_25H2_English_x64.iso"],
                      imports=["local:import/noble-server-cloudimg-amd64.qcow2"])
    out = await os_deploy.handle("list_os_images", {"node": "pve01", "check_upstream": True}, pve)
    assert out["images"]["ubuntu"]["cached"] == ["local:import/noble-server-cloudimg-amd64.qcow2"]
    assert out["images"]["windows11"]["cached"] == ["local:iso/Win11_25H2_English_x64.iso"]
    assert out["images"]["kali"]["latest"] == "kali-linux-2026.3-cloud-genericcloud-amd64.tar.xz"
    assert all(c[0] == "GET" for c in pve.calls)


def test_safety_classes():
    for name in ("deploy_ubuntu_vm", "deploy_kali_vm", "deploy_pdm_vm", "deploy_windows11_vm"):
        assert not registry.is_read_only(name) and not registry.is_destructive(name)
    assert registry.is_read_only("list_os_images")


def test_passwords_are_redacted_in_the_audit_log():
    from proxmox_mcp import audit

    assert audit.redact({"password": "x", "root_password": "y", "node": "pve01"}) == {
        "password": "***", "root_password": "***", "node": "pve01",
    }


def test_no_live_network_in_these_tests():
    assert os.environ.get("PROXMOX_HOST", "") in ("", "pve.test") and lzma  # imports used
