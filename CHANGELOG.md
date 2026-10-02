# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `PROXMOX_READ_ONLY` mode: when `true`, the client refuses every POST/PUT/DELETE
  request, so only read tools work (#24, thanks @volodic-vinted).

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

[2.1.0]: https://github.com/ry-ops/proxmox-mcp-server/compare/v1.0.0.1...v2.1.0
[1.0.0.1]: https://github.com/ry-ops/proxmox-mcp-server/releases/tag/v1.0.0.1
