# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.8.0] - 2026-10-30

### Added
- Per-client tokens with roles for the HTTP entrypoint. `MCP_AUTH_TOKENS`
  (`name:role:token,…`) or `MCP_AUTH_TOKENS_FILE` (one `name role token` per line) give each
  client its own token, with role `read`, `operator` (everything but destructive tools) or
  `admin`. Each client lists only the tools its role allows, and other calls are refused before
  reaching Proxmox. Roles narrow the server's own settings; they never widen them.
  `MCP_AUTH_TOKEN` still works as an admin token named `default`.
- `PROXMOX_AUDIT_LOG`: a JSON-lines log of every write call (file or `stderr`), with time, caller,
  transport, tool, arguments with secrets redacted, outcome, error, task UPID and result, and
  duration. Refused calls are logged too. `PROXMOX_AUDIT_READS=true` adds reads.
- MCP prompts: `cluster_health_check`, `capacity_report`, `safe_change` (snapshot, change after
  your go-ahead, verify, offer rollback), `investigate_failed_tasks` and `decommission_guest`.
  They only guide the model; every step is a normal tool call under the usual rules.
- MCP resources: `proxmox://cluster/status`, `cluster/resources`, `cluster/tasks`, `nodes` and
  `storage`, plus templates for one node's status and one VM's or container's config. Each is a
  single validated GET, so they work in read-only mode and for every role.

### Changed
- Four new README animations: waiting for tasks, the safety settings with the audit log,
  HTTP clients with roles, and the built-in prompts and resources. `docs/gen/build.py`
  regenerates them.
- CI runs Ruff, and the 29 remaining lint warnings in the tool modules are fixed.

## [2.7.0] - 2026-10-30

### Added
- `wait_for_task`: wait for any Proxmox task (UPID) to finish. It returns `status`,
  `exitstatus` and `ok`, plus the last 20 log lines when the task failed. If the task is still
  running after `PROXMOX_WAIT_TIMEOUT` seconds (default 900) it returns `status: "running"`
  instead of failing. It loads with every toolset selection.
- `wait: true` on 30 long-running tools (power actions, create, clone, delete, migrate, disk
  moves, snapshots, backup, restore, URL downloads) returns the task's outcome with the result.
- `PROXMOX_NO_DESTRUCTIVE=true` hides the 73 tools labelled destructive and keeps safe writes
  such as start, create, clone and snapshot: 268 tools instead of 341.
- `PROXMOX_PROTECTED_VMIDS` (IDs and ranges, e.g. `100,9000-9010`) refuses any write aimed
  at those guests before a request is sent: power, config, snapshots, migration, disk moves,
  deletion, guest-agent commands, HA changes, and deleting their volumes or backups. Cloning
  from them, backing them up and opening a console stay allowed. Node-wide and bulk power or
  migrate actions need an explicit `vms` list while any guest is protected.

### Changed
- Tool results are compact JSON instead of indented, which cut a sample 60-guest cluster listing
  by about a third.
- The startup banner says which safety settings are active.

## [2.6.0] - 2026-10-30

### Added
- `proxmox-mcp-server-http`: a streamable-HTTP entrypoint that serves the same tools at `/mcp`,
  so the server can run as a network service. It binds to `127.0.0.1` by default and refuses
  any other address without `MCP_AUTH_TOKEN`, a bearer token checked in constant time, unless
  `MCP_HTTP_ALLOW_NO_AUTH=true`. On loopback it enables DNS-rebinding protection. `/healthz`
  answers without auth. Based on #29 by @djstachniak.

### Changed
- README and its animations cover toolsets, tool annotations and the HTTP entrypoint, with
  Claude Code setup and troubleshooting for missing tools and HTTP errors (#65).

## [2.5.0] - 2026-10-30

### Added
- `PROXMOX_TOOLSETS`: load only the API areas you need, e.g. `nodes,qemu,lxc,storage`.
  All 340 tool schemas cost a client roughly 40k tokens of context on every turn; that
  set is 126 tools and about 18k. `vms` and `containers` are aliases for `qemu` and `lxc`,
  and an unknown name stops the server at startup with the valid list.
- MCP tool annotations on every tool: `readOnlyHint` on the 149 that only read, and
  `destructiveHint` on the 73 that delete, stop, wipe, roll back, restore over or run guest
  commands. Clients can use them to auto-approve reads and confirm destructive calls.
- A test that runs every tool against a recording client and checks its read-only label
  against the HTTP methods it sends, plus schema checks for all 340 tools.
- CI runs the test suite on Python 3.10 to 3.13 for every push and pull request.
- `agent-card.json` marks each capability `read_only` and `destructive`, matching the
  tool annotations.

### Fixed
- Password auth keeps working past two hours. Proxmox tickets expire after 2 hours and the
  client never renewed them, so every call failed with 401 after that. It now logs in again
  after 90 minutes, and retries once with a new ticket if Proxmox answers 401 anyway.
  Concurrent requests share one login. Token auth is unchanged.

### Security
- `certifi` 2026.10.23 (critical advisory; versions before 2026.10.18 are affected) and
  `black` 26.10.1 (dev only; high advisory) in `uv.lock`.

### Changed
- `PROXMOX_READ_ONLY=true` now advertises only the 149 read tools instead of all 340.
  The write tools were already refused, so clients no longer see tools they cannot use.
- Calling a tool that is not loaded returns an error that names `PROXMOX_TOOLSETS` and
  `PROXMOX_READ_ONLY` as the likely cause.

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

[2.8.0]: https://github.com/ry-ops/proxmox-mcp-server/compare/v2.7.0...v2.8.0
[2.7.0]: https://github.com/ry-ops/proxmox-mcp-server/compare/v2.6.0...v2.7.0
[2.6.0]: https://github.com/ry-ops/proxmox-mcp-server/compare/v2.5.0...v2.6.0
[2.5.0]: https://github.com/ry-ops/proxmox-mcp-server/compare/v2.4.0...v2.5.0
[2.4.0]: https://github.com/ry-ops/proxmox-mcp-server/compare/v2.3.0...v2.4.0
[2.3.0]: https://github.com/ry-ops/proxmox-mcp-server/compare/v2.2.0...v2.3.0
[2.2.0]: https://github.com/ry-ops/proxmox-mcp-server/compare/v2.1.0...v2.2.0
[2.1.0]: https://github.com/ry-ops/proxmox-mcp-server/compare/v1.0.0.1...v2.1.0
[1.0.0.1]: https://github.com/ry-ops/proxmox-mcp-server/releases/tag/v1.0.0.1
