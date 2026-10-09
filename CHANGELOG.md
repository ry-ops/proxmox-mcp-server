# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.4.0] - 2026-10-08

### Added
- `deploy_cloud_vms`: create one or more VMs from a cloud image (for example Ubuntu's
  `noble-server-cloudimg` in `local:import`) with cloud-init: user, SSH public key, and a static
  IP per VM or DHCP, on a chosen bridge and VLAN. Imports the disk, grows it, starts each VM and
  returns VMIDs, names, MACs and IPs. Refuses names or VMIDs already in use, and validates
  addresses before calling the API. Built to hand nodes to k3s-mcp-server's `create_cluster`.

### Fixed
- The server starts again after a fresh `uv run`. Dependabot's #28 raised the requirement to
  `mcp>=2.2.0,<3`, but mcp 2.x removed the `@app.list_tools()`/`@app.call_tool()` decorators
  the server uses, so re-resolving installed 2.3.0 and the server exited with
  `AttributeError: 'Server' object has no attribute 'list_tools'`. mcp is capped below 2 again,
  and Dependabot now skips mcp major versions.

## [2.3.0] - 2026-10-03

### Added
- `deploy_fortigate_vm`: deploy a FortiGate-VM from Fortinet's KVM qcow2 image. It imports
  the disk (from an `import` volume, or downloads the image first), creates the VM with a WAN
  NIC and optional LAN/extra NICs on chosen bridges and VLANs, an optional log disk and a
  serial console, waits for the import, optionally starts it, and returns each FortiGate port
  with its MAC. Defaults (1 vCPU, 2 GB) fit the free permanent evaluation license.
- `create_vm` accepts `net1`–`net3`, `scsi1`, `serial0`, `vga` and `extra_config` (any other
  VM config key), so multi-NIC and cloud-init VMs no longer need a follow-up `set_vm_config`.

### Fixed
- A `.env` file is now actually loaded. `client.py` read its settings at import time,
  before `server.py` called `load_dotenv()`, so a clone configured only through `.env`
  stopped with "PROXMOX_HOST and PROXMOX_USER must be set".
- The server no longer prints a `RuntimeError: Event loop is closed` traceback on exit.
  The HTTP client was closed in a new event loop instead of the one its connections
  belonged to.
- API errors now include the reason Proxmox gives. A failed request used to report only
  "400 Parameter verification failed"; it now names the offending parameter, e.g.
  `net0.tag: value must have a maximum value of 4094`.
- `download_url_to_storage` sent `checksum_algorithm` and `verify_certificates`, which the API
  rejects; it now sends `checksum-algorithm` and `verify-certificates`. The tool also documents
  `content=import` for disk images.
- `import_vm_disk` called a nonexistent `/importdisk` endpoint. It now imports through the VM
  config (`<disk>: <storage>:0,import-from=<volume>`), with optional `disk`, `format` and
  `options`.

## [2.2.0] - 2026-10-02

### Added
- `PROXMOX_READ_ONLY` mode: when `true`, the client refuses every POST/PUT/DELETE
  request before it reaches the Proxmox API, so only read tools work. 149 of the 338
  tools keep working (#42, from #24, thanks @volodic-vinted).
- First automated tests (`tests/test_read_only.py`) (#42).

### Changed
- `agent-card.json` lists all 338 tools in 13 skill categories, generated from the
  tool registry (it previously described 21 v1 tools) (#41).

### Fixed
- Release builds can attach the SBOM to the GitHub release. The v2.1.0 build failed
  at that step for lack of `contents: write` (#40).
- `USAGE.md` referred to tools that no longer exist (`get_storage_status`,
  `list_tasks`) (#41).

## [2.1.0] - 2026-10-01

First tagged release since 1.0.0.1. It includes the 2.0.0 rewrite, which was never
released on its own.

### Added
- Full Proxmox VE API coverage: 338 tools across nodes, QEMU, LXC, storage, cluster,
  access, firewall, disks, Ceph, ACME, SDN, notifications and pools (2.0.0 rewrite
  into the modular `proxmox_mcp` package).
- `vm_agent_exec` accepts an `args` list, passed to the guest program as separate
  arguments (#35).
- `vm_agent_exec_status` tool to read a guest agent process's exit code, stdout and
  stderr (#35).
- `CHANGELOG.md`.

### Fixed
- Boolean tool parameters are sent as `1`/`0`. Proxmox rejected `true`/`false` with
  HTTP 400 (#30, #33).
- `docker-compose.yaml` and `.env.example` use the environment variable names the
  server actually reads, and a bare `PROXMOX_HOST` plus `PROXMOX_PORT` (#31, #34).
- The Docker image starts again. It ran a corrupted legacy module and installed
  an incompatible `mcp` 2.x (#32, #36).

### Changed
- `mcp` is capped below 2.0. mcp 2.x removed the decorator API the server uses (#36).
- The Docker image installs dependencies from `pyproject.toml` and runs the
  `proxmox-mcp-server` console script (#36).
- Bumped GitHub Actions: docker/build-push-action 7, docker/metadata-action 6,
  docker/setup-buildx-action 4, docker/login-action 4, anchore/sbom-action 0.24
  (#7–#11). All actions are pinned to commit SHAs (#4, #14).
- Raised minimum versions: httpx 0.28.1 (#12), python-dotenv 1.2.3 (#26).

### Removed
- The legacy single-file `proxmox_mcp_server` package. `proxmox_mcp` is now the
  only implementation (#32, #36).

### Security
- Locked anyio 4.15.1, PyJWT 2.15.1, cryptography 50.0.2 and mcp 1.30.0 to resolve
  18 Dependabot advisories, 2 of them critical (#37).

## [1.0.0.1] - 2026-02-03

Initial release.

[2.4.0]: https://github.com/ry-ops/proxmox-mcp-server/compare/v2.3.0...v2.4.0
[2.3.0]: https://github.com/ry-ops/proxmox-mcp-server/compare/v2.2.0...v2.3.0
[2.2.0]: https://github.com/ry-ops/proxmox-mcp-server/compare/v2.1.0...v2.2.0
[2.1.0]: https://github.com/ry-ops/proxmox-mcp-server/compare/v1.0.0.1...v2.1.0
[1.0.0.1]: https://github.com/ry-ops/proxmox-mcp-server/releases/tag/v1.0.0.1
