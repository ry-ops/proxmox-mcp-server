# Roadmap

Work we plan to do in an upcoming release. Items here are not scheduled yet.

## Planned

### Deploy an OS by asking: Ubuntu, Kali, Windows 11 and PDM

Ask "create a Kali VM" (or Ubuntu, Windows 11, a Datacenter Manager) and get a running,
reachable guest, with the image fetched, checked and installed unattended. Today
`deploy_cloud_vms` needs a cloud image already on storage and knows no OS by name.

**Tools.** One per OS, so a request maps to a tool by name, each with only its own inputs:
`deploy_ubuntu_vm`, `deploy_kali_vm`, `deploy_windows11_vm`, `deploy_pdm_vm`, plus
`list_os_images` (what's cached on storage, and the latest official version of each). They share
one internal builder. `deploy_cloud_vms` stays as it is.

**Images**, from official sources only, checksum-verified, cached on `local` and reused:

| OS | Source | How it gets onto Proxmox |
|---|---|---|
| Ubuntu 24.04 | `cloud-images.ubuntu.com`, `SHA256SUMS` | `download-url` (import) |
| PDM | Debian 13 `genericcloud` from `cloud.debian.org`, `SHA512SUMS`; PDM from Proxmox's `pdm-no-subscription` repo | `download-url` (import), then cloud-init installs PDM |
| Kali | `kali.download/cloud-images`, `SHA256SUMS`. Published only as `.tar.xz`, which Proxmox can't decompress (it handles gz, lzo, zst, bz2) | The server downloads it (≈240 MB), repacks the sparse 25 GiB `disk.raw` as qcow2 holding only its ≈1 GiB of data, and uploads that (`upload`, import) |
| Windows 11 | Microsoft gives no stable download URL, so a Windows 11 ISO already on storage, found automatically; VirtIO drivers from `fedorapeople.org` (stable URL) | Existing ISO; `download-url` (iso) for the drivers |

**Unattended setup through a seed ISO.** Proxmox's upload API accepts ISO, template and import
files but not cloud-init snippets, so the server builds a small ISO in memory (ISO 9660 with
Joliet names) and uploads it:

- **Linux and PDM:** a `cidata` volume (cloud-init's NoCloud source) with `user-data`,
  `meta-data` and `network-config`. It sets the user and key or password, installs
  `qemu-guest-agent`, and for PDM adds the repository and installs `proxmox-datacenter-manager`
  and its UI.
- **Windows 11:** `autounattend.xml`. It loads the VirtIO storage driver during Setup, makes a UEFI
  GPT layout, installs Windows 11 Pro without activation (licensing stays with you), creates the
  Administrator account, and installs the VirtIO guest tools (drivers plus guest agent) at first
  logon. The VM is q35 with UEFI, Secure Boot keys, TPM 2.0 and VirtIO disk and network. The
  server answers "Press any key to boot from CD" with `sendkey`.
- Seed ISOs hold credentials, so they're deleted once the guest reports through its agent.

**Credentials.** An SSH public key if given; otherwise a generated password for the default
user (Linux) or Administrator (Windows), returned once in the tool result. The audit log redacts
it, and nothing else stores it.

**Done means reachable.** Linux tools wait for the guest agent and report the IP; `deploy_pdm_vm`
also waits for cloud-init to finish and returns the PDM URL; `deploy_windows11_vm` waits for the
guest tools (an install takes 20 to 40 minutes) and accepts `wait` limits like other long tasks.

**Safety.** Writes, not destructive. They refuse a name or VMID already in use, respect
`PROXMOX_PROTECTED_VMIDS` and read-only mode, and never touch existing guests.

**Order.** Seed ISO builder and Ubuntu, then PDM, Kali and Windows 11, each tested end to end on a
live node with throwaway guests.

### Proxmox Datacenter Manager (PDM) support

**Status:** phases 1 and 2 shipped in v2.13.0 (the `pdm` toolset, 89 tools, tested against
PDM 1.1.9). Phase 3 is planned. Seven of the 89 reach endpoints PDM 1.1 reserves for
`root@pam` with a password (no access rule), so API tokens get 403; their descriptions say so,
and the generator flags them again on each PDM release.

Add PDM as a `pdm` toolset in this server, so one server can manage several Proxmox VE
clusters and Proxmox Backup Servers through PDM, alongside the existing tools that talk to one
Proxmox VE API. Phases 1 and 2 ship together in the first release.

The map below covers every endpoint in PDM's published API schema
([API viewer](https://pdm.proxmox.com/docs/api-viewer/)), 327 in all:
94 in phase 1, 27 in phase 2, 142 in phase 3, and 64 not planned,
each with its reason. QEMU and LXC versions of the same call share one tool with a `type` input.

#### Design

- **Toolset.** `pdm`, loaded when `PDM_HOST` is set. `PROXMOX_TOOLSETS`, `PROXMOX_READ_ONLY`,
  `PROXMOX_NO_DESTRUCTIVE`, HTTP roles and the audit log apply to it like any other toolset.
  The server starts with Proxmox VE settings, PDM settings, or both.
- **Connection.** `PDM_HOST`, `PDM_PORT` (default `8443`), `PDM_TOKEN_ID` (`user@realm!name`),
  `PDM_TOKEN_SECRET`. TLS: `PDM_CA_BUNDLE` (PDM's own certificate or CA) or `PDM_VERIFY_SSL`, with
  the same unverified-TLS warning as Proxmox VE.
- **Protected guests.** VMIDs are only unique within a cluster, so PDM tools use
  `PDM_PROTECTED_GUESTS` with remote-scoped entries: `pve01:104,pve01:105`, or `*:9000-9010` for
  every remote. Migrations check the source and the target.
- **Safety classes.** Reads are read-only. Stop, shutdown, rollback, snapshot delete, task stop and
  both migrations are destructive. Start, resume, snapshot create/update and the refresh calls are
  writes. The argument checks (whole-number IDs, no `/` in path inputs, no `..` paths) cover the
  new `remote`, `node`, `storage`, `datastore`, `snapname` and `upid` inputs.
- **Waiting.** Actions return a task ID; `wait` follows it through PDM's task status endpoints
  (remote tasks through `/pve` or `/pbs`, PDM's own through `/nodes/localhost`).
- **Verify on a live PDM before release.** The token header format, task ID formats, and which
  endpoints PDM 1.1.9 serves (the public schema may be newer). Tests run against PDM 1.1.9 with
  one Proxmox VE remote; cross-cluster migration can't be tested live until there's a second.

#### Phase 1: read (71 tools)

`pdm_ceph_cluster`, `pdm_ceph_list_clusters`, `pdm_get_remote_config`, `pdm_get_remote_rrddata`, `pdm_get_remote_version`, `pdm_list_remote_tasks`, `pdm_list_remotes`, `pdm_list_resources`, `pdm_list_tasks`, `pdm_location_info`, `pdm_metric_collection_status`, `pdm_my_permissions`, `pdm_node_status`, `pdm_pbs_datastore_rrddata`, `pdm_pbs_list_datastores`, `pdm_pbs_list_namespaces`, `pdm_pbs_list_remotes`, `pdm_pbs_list_snapshots`, `pdm_pbs_list_tasks`, `pdm_pbs_node_apt_changelog`, `pdm_pbs_node_apt_repositories`, `pdm_pbs_node_apt_updates`, `pdm_pbs_node_subscription`, `pdm_pbs_rrddata`, `pdm_pbs_status`, `pdm_pbs_task_log`, `pdm_pbs_task_status`, `pdm_ping`, `pdm_pve_cluster_firewall`, `pdm_pve_cluster_options`, `pdm_pve_cluster_status`, `pdm_pve_firewall_status_all`, `pdm_pve_guest_config`, `pdm_pve_guest_firewall`, `pdm_pve_guest_pending`, `pdm_pve_guest_rrddata`, `pdm_pve_guest_status`, `pdm_pve_list_guests`, `pdm_pve_list_nodes`, `pdm_pve_list_remotes`, `pdm_pve_list_snapshots`, `pdm_pve_list_storage`, `pdm_pve_list_tasks`, `pdm_pve_migrate_preconditions`, `pdm_pve_next_vmid`, `pdm_pve_node_apt_changelog`, `pdm_pve_node_apt_repositories`, `pdm_pve_node_apt_updates`, `pdm_pve_node_config`, `pdm_pve_node_firewall`, `pdm_pve_node_network`, `pdm_pve_node_rrddata`, `pdm_pve_node_status`, `pdm_pve_node_subscription`, `pdm_pve_resources`, `pdm_pve_sdn_vnet_mac_vrf`, `pdm_pve_sdn_zone_ip_vrf`, `pdm_pve_storage_rrddata`, `pdm_pve_storage_status`, `pdm_pve_task_log`, `pdm_pve_task_status`, `pdm_pve_updates`, `pdm_remote_task_statistics`, `pdm_resource_status`, `pdm_sdn_list`, `pdm_subscription_status`, `pdm_task_log`, `pdm_task_status`, `pdm_top_entities`, `pdm_update_summary`, `pdm_version`.

#### Phase 2: actions (18 tools)

`pdm_collect_metrics`, `pdm_pbs_node_apt_refresh`, `pdm_pbs_stop_task`, `pdm_pve_create_snapshot`, `pdm_pve_delete_snapshot`, `pdm_pve_migrate_guest`, `pdm_pve_node_apt_refresh`, `pdm_pve_remote_migrate_guest`, `pdm_pve_resume_vm`, `pdm_pve_rollback_snapshot`, `pdm_pve_shutdown_guest`, `pdm_pve_start_guest`, `pdm_pve_stop_guest`, `pdm_pve_stop_task`, `pdm_pve_update_snapshot`, `pdm_refresh_remote_tasks`, `pdm_refresh_updates`, `pdm_stop_task`.

#### Phase 3: later

- PDM users, tokens, ACLs and TFA (21 endpoints)
- Automated installation (12 endpoints)
- PDM realms and TFA settings (21 endpoints)
- PDM certificates and ACME (20 endpoints)
- Notes (2 endpoints)
- Views (5 endpoints)
- PDM host administration (29 endpoints)
- Remote management (10 endpoints)
- Firewall writes (4 endpoints)
- SDN writes (2 endpoints)
- Subscription key pool (16 endpoints)

#### Not planned

- Directory indexes (navigation only; each tool calls the endpoint it needs): 47
- Browser OpenID login flow: 2
- Logout for browser sessions; tokens don't use tickets: 1
- Login handshake; the client authenticates with an API token: 1
- Called by the Proxmox installer, not by people: 1
- Compatibility shim; PDM has one node, `localhost`: 1
- Interactive console (terminal proxy), not usable over MCP: 5
- Interactive console (websocket), not usable over MCP: 5
- Interactive console (VNC proxy), not usable over MCP: 1

#### Full API map

<details>
<summary>All 327 endpoints, by area</summary>

**Root, version and ping**

| Method | Path | Phase | Tool or reason |
|---|---|---|---|
| GET | `/` | — | directory index |
| GET | `/ping` | 1 | `pdm_ping` |
| GET | `/version` | 1 | `pdm_version` |

**PDM access control**

| Method | Path | Phase | Tool or reason |
|---|---|---|---|
| GET | `/access` | — | directory index |
| GET | `/access/acl` | 3 | PDM users, tokens, ACLs and TFA |
| PUT | `/access/acl` | 3 | PDM users, tokens, ACLs and TFA |
| GET | `/access/domains` | 3 | PDM users, tokens, ACLs and TFA |
| POST | `/access/domains/{realm}/sync` | 3 | PDM users, tokens, ACLs and TFA |
| GET | `/access/openid` | — | directory index |
| POST | `/access/openid/auth-url` | — | browser OpenID login flow |
| POST | `/access/openid/login` | — | browser OpenID login flow |
| GET | `/access/permissions` | 1 | `pdm_my_permissions` |
| GET | `/access/roles` | 3 | PDM users, tokens, ACLs and TFA |
| GET | `/access/tfa` | 3 | PDM users, tokens, ACLs and TFA |
| GET | `/access/tfa/{userid}` | 3 | PDM users, tokens, ACLs and TFA |
| POST | `/access/tfa/{userid}` | 3 | PDM users, tokens, ACLs and TFA |
| DELETE | `/access/tfa/{userid}/{id}` | 3 | PDM users, tokens, ACLs and TFA |
| GET | `/access/tfa/{userid}/{id}` | 3 | PDM users, tokens, ACLs and TFA |
| PUT | `/access/tfa/{userid}/{id}` | 3 | PDM users, tokens, ACLs and TFA |
| DELETE | `/access/ticket` | — | logout for browser sessions; tokens don't use tickets |
| POST | `/access/ticket` | — | login handshake; the client authenticates with an API token |
| GET | `/access/users` | 3 | PDM users, tokens, ACLs and TFA |
| POST | `/access/users` | 3 | PDM users, tokens, ACLs and TFA |
| DELETE | `/access/users/{userid}` | 3 | PDM users, tokens, ACLs and TFA |
| GET | `/access/users/{userid}` | 3 | PDM users, tokens, ACLs and TFA |
| PUT | `/access/users/{userid}` | 3 | PDM users, tokens, ACLs and TFA |
| GET | `/access/users/{userid}/token` | 3 | PDM users, tokens, ACLs and TFA |
| DELETE | `/access/users/{userid}/token/{token-name}` | 3 | PDM users, tokens, ACLs and TFA |
| GET | `/access/users/{userid}/token/{token-name}` | 3 | PDM users, tokens, ACLs and TFA |
| POST | `/access/users/{userid}/token/{token-name}` | 3 | PDM users, tokens, ACLs and TFA |
| PUT | `/access/users/{userid}/token/{token-name}` | 3 | PDM users, tokens, ACLs and TFA |

**Automated installation**

| Method | Path | Phase | Tool or reason |
|---|---|---|---|
| GET | `/auto-install` | — | directory index |
| POST | `/auto-install/answer` | — | called by the Proxmox installer, not by people |
| GET | `/auto-install/installations` | 3 | automated installation |
| DELETE | `/auto-install/installations/{uuid}` | 3 | automated installation |
| POST | `/auto-install/installations/{uuid}/post-hook` | 3 | automated installation |
| GET | `/auto-install/prepared` | 3 | automated installation |
| POST | `/auto-install/prepared` | 3 | automated installation |
| DELETE | `/auto-install/prepared/{id}` | 3 | automated installation |
| GET | `/auto-install/prepared/{id}` | 3 | automated installation |
| PUT | `/auto-install/prepared/{id}` | 3 | automated installation |
| GET | `/auto-install/tokens` | 3 | automated installation |
| POST | `/auto-install/tokens` | 3 | automated installation |
| DELETE | `/auto-install/tokens/{id}` | 3 | automated installation |
| PUT | `/auto-install/tokens/{id}` | 3 | automated installation |

**Ceph clusters**

| Method | Path | Phase | Tool or reason |
|---|---|---|---|
| GET | `/ceph` | — | directory index |
| GET | `/ceph/clusters` | 1 | `pdm_ceph_list_clusters` |
| GET | `/ceph/clusters/{cluster}` | — | directory index |
| GET | `/ceph/clusters/{cluster}/flags` | 1 | `pdm_ceph_cluster` |
| GET | `/ceph/clusters/{cluster}/fs` | 1 | `pdm_ceph_cluster` |
| GET | `/ceph/clusters/{cluster}/mds` | 1 | `pdm_ceph_cluster` |
| GET | `/ceph/clusters/{cluster}/mgr` | 1 | `pdm_ceph_cluster` |
| GET | `/ceph/clusters/{cluster}/mon` | 1 | `pdm_ceph_cluster` |
| GET | `/ceph/clusters/{cluster}/osd-tree` | 1 | `pdm_ceph_cluster` |
| GET | `/ceph/clusters/{cluster}/pools` | 1 | `pdm_ceph_cluster` |
| GET | `/ceph/clusters/{cluster}/status` | 1 | `pdm_ceph_cluster` |
| GET | `/ceph/clusters/{cluster}/summary` | 1 | `pdm_ceph_cluster` |

**PDM configuration**

| Method | Path | Phase | Tool or reason |
|---|---|---|---|
| GET | `/config` | — | directory index |
| GET | `/config/access` | — | directory index |
| GET | `/config/access/ad` | 3 | PDM realms and TFA settings |
| POST | `/config/access/ad` | 3 | PDM realms and TFA settings |
| DELETE | `/config/access/ad/{realm}` | 3 | PDM realms and TFA settings |
| GET | `/config/access/ad/{realm}` | 3 | PDM realms and TFA settings |
| PUT | `/config/access/ad/{realm}` | 3 | PDM realms and TFA settings |
| GET | `/config/access/ldap` | 3 | PDM realms and TFA settings |
| POST | `/config/access/ldap` | 3 | PDM realms and TFA settings |
| DELETE | `/config/access/ldap/{realm}` | 3 | PDM realms and TFA settings |
| GET | `/config/access/ldap/{realm}` | 3 | PDM realms and TFA settings |
| PUT | `/config/access/ldap/{realm}` | 3 | PDM realms and TFA settings |
| GET | `/config/access/openid` | 3 | PDM realms and TFA settings |
| POST | `/config/access/openid` | 3 | PDM realms and TFA settings |
| DELETE | `/config/access/openid/{realm}` | 3 | PDM realms and TFA settings |
| GET | `/config/access/openid/{realm}` | 3 | PDM realms and TFA settings |
| PUT | `/config/access/openid/{realm}` | 3 | PDM realms and TFA settings |
| GET | `/config/access/pam` | 3 | PDM realms and TFA settings |
| PUT | `/config/access/pam` | 3 | PDM realms and TFA settings |
| GET | `/config/access/pdm` | 3 | PDM realms and TFA settings |
| PUT | `/config/access/pdm` | 3 | PDM realms and TFA settings |
| GET | `/config/access/tfa` | — | directory index |
| GET | `/config/access/tfa/webauthn` | 3 | PDM realms and TFA settings |
| PUT | `/config/access/tfa/webauthn` | 3 | PDM realms and TFA settings |
| GET | `/config/acme` | — | directory index |
| GET | `/config/acme/account` | 3 | PDM certificates and ACME |
| POST | `/config/acme/account` | 3 | PDM certificates and ACME |
| DELETE | `/config/acme/account/{name}` | 3 | PDM certificates and ACME |
| GET | `/config/acme/account/{name}` | 3 | PDM certificates and ACME |
| PUT | `/config/acme/account/{name}` | 3 | PDM certificates and ACME |
| GET | `/config/acme/challenge-schema` | 3 | PDM certificates and ACME |
| GET | `/config/acme/directories` | 3 | PDM certificates and ACME |
| GET | `/config/acme/plugins` | 3 | PDM certificates and ACME |
| POST | `/config/acme/plugins` | 3 | PDM certificates and ACME |
| DELETE | `/config/acme/plugins/{id}` | 3 | PDM certificates and ACME |
| GET | `/config/acme/plugins/{id}` | 3 | PDM certificates and ACME |
| PUT | `/config/acme/plugins/{id}` | 3 | PDM certificates and ACME |
| GET | `/config/acme/tos` | 3 | PDM certificates and ACME |
| GET | `/config/certificate` | 3 | PDM certificates and ACME |
| PUT | `/config/certificate` | 3 | PDM certificates and ACME |
| GET | `/config/notes` | 3 | notes |
| PUT | `/config/notes` | 3 | notes |
| GET | `/config/views` | 3 | views |
| POST | `/config/views` | 3 | views |
| DELETE | `/config/views/{id}` | 3 | views |
| GET | `/config/views/{id}` | 3 | views |
| PUT | `/config/views/{id}` | 3 | views |

**The PDM host itself**

| Method | Path | Phase | Tool or reason |
|---|---|---|---|
| GET | `/nodes` | — | compatibility shim; PDM has one node, `localhost` |
| GET | `/nodes/{node}` | — | directory index |
| GET | `/nodes/{node}/apt` | — | directory index |
| GET | `/nodes/{node}/apt/changelog` | 3 | PDM host administration |
| GET | `/nodes/{node}/apt/repositories` | 3 | PDM host administration |
| POST | `/nodes/{node}/apt/repositories` | 3 | PDM host administration |
| PUT | `/nodes/{node}/apt/repositories` | 3 | PDM host administration |
| GET | `/nodes/{node}/apt/update` | 3 | PDM host administration |
| POST | `/nodes/{node}/apt/update` | 3 | PDM host administration |
| GET | `/nodes/{node}/apt/versions` | 3 | PDM host administration |
| GET | `/nodes/{node}/certificates` | — | directory index |
| GET | `/nodes/{node}/certificates/acme` | — | directory index |
| POST | `/nodes/{node}/certificates/acme/certificate` | 3 | PDM certificates and ACME |
| PUT | `/nodes/{node}/certificates/acme/certificate` | 3 | PDM certificates and ACME |
| DELETE | `/nodes/{node}/certificates/custom` | 3 | PDM certificates and ACME |
| POST | `/nodes/{node}/certificates/custom` | 3 | PDM certificates and ACME |
| GET | `/nodes/{node}/certificates/info` | 3 | PDM certificates and ACME |
| GET | `/nodes/{node}/config` | 3 | PDM host administration |
| PUT | `/nodes/{node}/config` | 3 | PDM host administration |
| GET | `/nodes/{node}/dns` | 3 | PDM host administration |
| PUT | `/nodes/{node}/dns` | 3 | PDM host administration |
| GET | `/nodes/{node}/journal` | 3 | PDM host administration |
| DELETE | `/nodes/{node}/network` | 3 | PDM host administration |
| GET | `/nodes/{node}/network` | 3 | PDM host administration |
| POST | `/nodes/{node}/network` | 3 | PDM host administration |
| PUT | `/nodes/{node}/network` | 3 | PDM host administration |
| DELETE | `/nodes/{node}/network/{iface}` | 3 | PDM host administration |
| GET | `/nodes/{node}/network/{iface}` | 3 | PDM host administration |
| PUT | `/nodes/{node}/network/{iface}` | 3 | PDM host administration |
| GET | `/nodes/{node}/report` | 3 | PDM host administration |
| GET | `/nodes/{node}/rrddata` | 3 | PDM host administration |
| GET | `/nodes/{node}/sdn` | — | directory index |
| GET | `/nodes/{node}/sdn/vnets/{vnet}` | — | directory index |
| GET | `/nodes/{node}/sdn/vnets/{vnet}/mac-vrf` | 3 | PDM host administration |
| GET | `/nodes/{node}/sdn/zones/{zone}` | — | directory index |
| GET | `/nodes/{node}/sdn/zones/{zone}/ip-vrf` | 3 | PDM host administration |
| GET | `/nodes/{node}/status` | 1 | `pdm_node_status` |
| POST | `/nodes/{node}/status` | 3 | PDM host administration |
| GET | `/nodes/{node}/subscription` | 3 | PDM host administration |
| POST | `/nodes/{node}/subscription` | 3 | PDM host administration |
| GET | `/nodes/{node}/syslog` | 3 | PDM host administration |
| GET | `/nodes/{node}/tasks` | 1 | `pdm_list_tasks` |
| DELETE | `/nodes/{node}/tasks/{upid}` | 2 | `pdm_stop_task` |
| GET | `/nodes/{node}/tasks/{upid}` | — | directory index |
| GET | `/nodes/{node}/tasks/{upid}/log` | 1 | `pdm_task_log` |
| GET | `/nodes/{node}/tasks/{upid}/status` | 1 | `pdm_task_status` |
| POST | `/nodes/{node}/termproxy` | — | interactive console (terminal proxy), not usable over MCP |
| GET | `/nodes/{node}/time` | 3 | PDM host administration |
| PUT | `/nodes/{node}/time` | 3 | PDM host administration |
| GET | `/nodes/{node}/vncwebsocket` | — | interactive console (websocket), not usable over MCP |

**Proxmox Backup Server remotes**

| Method | Path | Phase | Tool or reason |
|---|---|---|---|
| GET | `/pbs` | — | directory index |
| POST | `/pbs/probe-tls` | 3 | remote management |
| GET | `/pbs/realms` | 3 | remote management |
| GET | `/pbs/remotes` | 1 | `pdm_pbs_list_remotes` |
| GET | `/pbs/remotes/{remote}` | — | directory index |
| GET | `/pbs/remotes/{remote}/datastore` | 1 | `pdm_pbs_list_datastores` |
| GET | `/pbs/remotes/{remote}/datastore/{datastore}` | — | directory index |
| GET | `/pbs/remotes/{remote}/datastore/{datastore}/namespaces` | 1 | `pdm_pbs_list_namespaces` |
| GET | `/pbs/remotes/{remote}/datastore/{datastore}/rrddata` | 1 | `pdm_pbs_datastore_rrddata` |
| GET | `/pbs/remotes/{remote}/datastore/{datastore}/snapshots` | 1 | `pdm_pbs_list_snapshots` |
| GET | `/pbs/remotes/{remote}/nodes/{node}` | — | directory index |
| GET | `/pbs/remotes/{remote}/nodes/{node}/apt` | — | directory index |
| GET | `/pbs/remotes/{remote}/nodes/{node}/apt/changelog` | 1 | `pdm_pbs_node_apt_changelog` |
| GET | `/pbs/remotes/{remote}/nodes/{node}/apt/repositories` | 1 | `pdm_pbs_node_apt_repositories` |
| GET | `/pbs/remotes/{remote}/nodes/{node}/apt/update` | 1 | `pdm_pbs_node_apt_updates` |
| POST | `/pbs/remotes/{remote}/nodes/{node}/apt/update` | 2 | `pdm_pbs_node_apt_refresh` |
| GET | `/pbs/remotes/{remote}/nodes/{node}/subscription` | 1 | `pdm_pbs_node_subscription` |
| POST | `/pbs/remotes/{remote}/nodes/{node}/termproxy` | — | interactive console (terminal proxy), not usable over MCP |
| GET | `/pbs/remotes/{remote}/nodes/{node}/vncwebsocket` | — | interactive console (websocket), not usable over MCP |
| GET | `/pbs/remotes/{remote}/rrddata` | 1 | `pdm_pbs_rrddata` |
| GET | `/pbs/remotes/{remote}/status` | 1 | `pdm_pbs_status` |
| GET | `/pbs/remotes/{remote}/tasks` | 1 | `pdm_pbs_list_tasks` |
| DELETE | `/pbs/remotes/{remote}/tasks/{upid}` | 2 | `pdm_pbs_stop_task` |
| GET | `/pbs/remotes/{remote}/tasks/{upid}` | — | directory index |
| GET | `/pbs/remotes/{remote}/tasks/{upid}/log` | 1 | `pdm_pbs_task_log` |
| GET | `/pbs/remotes/{remote}/tasks/{upid}/status` | 1 | `pdm_pbs_task_status` |
| POST | `/pbs/scan` | 3 | remote management |

**Proxmox VE remotes**

| Method | Path | Phase | Tool or reason |
|---|---|---|---|
| GET | `/pve` | — | directory index |
| GET | `/pve/firewall` | — | directory index |
| GET | `/pve/firewall/status` | 1 | `pdm_pve_firewall_status_all` |
| POST | `/pve/probe-tls` | 3 | remote management |
| GET | `/pve/realms` | 3 | remote management |
| GET | `/pve/remotes` | 1 | `pdm_pve_list_remotes` |
| GET | `/pve/remotes/{remote}` | — | directory index |
| GET | `/pve/remotes/{remote}/cluster-nextid` | 1 | `pdm_pve_next_vmid` |
| GET | `/pve/remotes/{remote}/cluster-status` | 1 | `pdm_pve_cluster_status` |
| GET | `/pve/remotes/{remote}/firewall` | — | directory index |
| GET | `/pve/remotes/{remote}/firewall/options` | 1 | `pdm_pve_cluster_firewall` |
| PUT | `/pve/remotes/{remote}/firewall/options` | 3 | firewall writes |
| GET | `/pve/remotes/{remote}/firewall/rules` | 1 | `pdm_pve_cluster_firewall` |
| GET | `/pve/remotes/{remote}/firewall/status` | 1 | `pdm_pve_cluster_firewall` |
| GET | `/pve/remotes/{remote}/lxc` | 1 | `pdm_pve_list_guests` |
| GET | `/pve/remotes/{remote}/lxc/{vmid}` | — | directory index |
| GET | `/pve/remotes/{remote}/lxc/{vmid}/config` | 1 | `pdm_pve_guest_config` |
| GET | `/pve/remotes/{remote}/lxc/{vmid}/firewall` | — | directory index |
| GET | `/pve/remotes/{remote}/lxc/{vmid}/firewall/options` | 1 | `pdm_pve_guest_firewall` |
| PUT | `/pve/remotes/{remote}/lxc/{vmid}/firewall/options` | 3 | firewall writes |
| GET | `/pve/remotes/{remote}/lxc/{vmid}/firewall/rules` | 1 | `pdm_pve_guest_firewall` |
| POST | `/pve/remotes/{remote}/lxc/{vmid}/migrate` | 2 | `pdm_pve_migrate_guest` |
| GET | `/pve/remotes/{remote}/lxc/{vmid}/pending` | 1 | `pdm_pve_guest_pending` |
| POST | `/pve/remotes/{remote}/lxc/{vmid}/remote-migrate` | 2 | `pdm_pve_remote_migrate_guest` |
| GET | `/pve/remotes/{remote}/lxc/{vmid}/rrddata` | 1 | `pdm_pve_guest_rrddata` |
| POST | `/pve/remotes/{remote}/lxc/{vmid}/shutdown` | 2 | `pdm_pve_shutdown_guest` |
| GET | `/pve/remotes/{remote}/lxc/{vmid}/snapshot` | 1 | `pdm_pve_list_snapshots` |
| POST | `/pve/remotes/{remote}/lxc/{vmid}/snapshot` | 2 | `pdm_pve_create_snapshot` |
| DELETE | `/pve/remotes/{remote}/lxc/{vmid}/snapshot/{snapname}` | 2 | `pdm_pve_delete_snapshot` |
| PUT | `/pve/remotes/{remote}/lxc/{vmid}/snapshot/{snapname}/config` | 2 | `pdm_pve_update_snapshot` |
| POST | `/pve/remotes/{remote}/lxc/{vmid}/snapshot/{snapname}/rollback` | 2 | `pdm_pve_rollback_snapshot` |
| POST | `/pve/remotes/{remote}/lxc/{vmid}/start` | 2 | `pdm_pve_start_guest` |
| GET | `/pve/remotes/{remote}/lxc/{vmid}/status` | 1 | `pdm_pve_guest_status` |
| POST | `/pve/remotes/{remote}/lxc/{vmid}/stop` | 2 | `pdm_pve_stop_guest` |
| POST | `/pve/remotes/{remote}/lxc/{vmid}/termproxy` | — | interactive console (terminal proxy), not usable over MCP |
| GET | `/pve/remotes/{remote}/lxc/{vmid}/vncwebsocket` | — | interactive console (websocket), not usable over MCP |
| GET | `/pve/remotes/{remote}/nodes` | 1 | `pdm_pve_list_nodes` |
| GET | `/pve/remotes/{remote}/nodes/{node}` | — | directory index |
| GET | `/pve/remotes/{remote}/nodes/{node}/apt` | — | directory index |
| GET | `/pve/remotes/{remote}/nodes/{node}/apt/changelog` | 1 | `pdm_pve_node_apt_changelog` |
| GET | `/pve/remotes/{remote}/nodes/{node}/apt/repositories` | 1 | `pdm_pve_node_apt_repositories` |
| GET | `/pve/remotes/{remote}/nodes/{node}/apt/update` | 1 | `pdm_pve_node_apt_updates` |
| POST | `/pve/remotes/{remote}/nodes/{node}/apt/update` | 2 | `pdm_pve_node_apt_refresh` |
| GET | `/pve/remotes/{remote}/nodes/{node}/config` | 1 | `pdm_pve_node_config` |
| GET | `/pve/remotes/{remote}/nodes/{node}/firewall` | — | directory index |
| GET | `/pve/remotes/{remote}/nodes/{node}/firewall/options` | 1 | `pdm_pve_node_firewall` |
| PUT | `/pve/remotes/{remote}/nodes/{node}/firewall/options` | 3 | firewall writes |
| GET | `/pve/remotes/{remote}/nodes/{node}/firewall/rules` | 1 | `pdm_pve_node_firewall` |
| GET | `/pve/remotes/{remote}/nodes/{node}/firewall/status` | 1 | `pdm_pve_node_firewall` |
| GET | `/pve/remotes/{remote}/nodes/{node}/network` | 1 | `pdm_pve_node_network` |
| GET | `/pve/remotes/{remote}/nodes/{node}/rrddata` | 1 | `pdm_pve_node_rrddata` |
| GET | `/pve/remotes/{remote}/nodes/{node}/sdn` | — | directory index |
| GET | `/pve/remotes/{remote}/nodes/{node}/sdn/vnets/{vnet}` | — | directory index |
| GET | `/pve/remotes/{remote}/nodes/{node}/sdn/vnets/{vnet}/mac-vrf` | 1 | `pdm_pve_sdn_vnet_mac_vrf` |
| GET | `/pve/remotes/{remote}/nodes/{node}/sdn/zones/{zone}` | — | directory index |
| GET | `/pve/remotes/{remote}/nodes/{node}/sdn/zones/{zone}/ip-vrf` | 1 | `pdm_pve_sdn_zone_ip_vrf` |
| GET | `/pve/remotes/{remote}/nodes/{node}/status` | 1 | `pdm_pve_node_status` |
| GET | `/pve/remotes/{remote}/nodes/{node}/storage` | 1 | `pdm_pve_list_storage` |
| GET | `/pve/remotes/{remote}/nodes/{node}/storage/{storage}` | — | directory index |
| GET | `/pve/remotes/{remote}/nodes/{node}/storage/{storage}/rrddata` | 1 | `pdm_pve_storage_rrddata` |
| GET | `/pve/remotes/{remote}/nodes/{node}/storage/{storage}/status` | 1 | `pdm_pve_storage_status` |
| GET | `/pve/remotes/{remote}/nodes/{node}/subscription` | 1 | `pdm_pve_node_subscription` |
| POST | `/pve/remotes/{remote}/nodes/{node}/termproxy` | — | interactive console (terminal proxy), not usable over MCP |
| GET | `/pve/remotes/{remote}/nodes/{node}/vncwebsocket` | — | interactive console (websocket), not usable over MCP |
| GET | `/pve/remotes/{remote}/options` | 1 | `pdm_pve_cluster_options` |
| GET | `/pve/remotes/{remote}/qemu` | 1 | `pdm_pve_list_guests` |
| GET | `/pve/remotes/{remote}/qemu/{vmid}` | — | directory index |
| GET | `/pve/remotes/{remote}/qemu/{vmid}/config` | 1 | `pdm_pve_guest_config` |
| GET | `/pve/remotes/{remote}/qemu/{vmid}/firewall` | — | directory index |
| GET | `/pve/remotes/{remote}/qemu/{vmid}/firewall/options` | 1 | `pdm_pve_guest_firewall` |
| PUT | `/pve/remotes/{remote}/qemu/{vmid}/firewall/options` | 3 | firewall writes |
| GET | `/pve/remotes/{remote}/qemu/{vmid}/firewall/rules` | 1 | `pdm_pve_guest_firewall` |
| GET | `/pve/remotes/{remote}/qemu/{vmid}/migrate` | 1 | `pdm_pve_migrate_preconditions` |
| POST | `/pve/remotes/{remote}/qemu/{vmid}/migrate` | 2 | `pdm_pve_migrate_guest` |
| GET | `/pve/remotes/{remote}/qemu/{vmid}/pending` | 1 | `pdm_pve_guest_pending` |
| POST | `/pve/remotes/{remote}/qemu/{vmid}/remote-migrate` | 2 | `pdm_pve_remote_migrate_guest` |
| POST | `/pve/remotes/{remote}/qemu/{vmid}/resume` | 2 | `pdm_pve_resume_vm` |
| GET | `/pve/remotes/{remote}/qemu/{vmid}/rrddata` | 1 | `pdm_pve_guest_rrddata` |
| POST | `/pve/remotes/{remote}/qemu/{vmid}/shutdown` | 2 | `pdm_pve_shutdown_guest` |
| GET | `/pve/remotes/{remote}/qemu/{vmid}/snapshot` | 1 | `pdm_pve_list_snapshots` |
| POST | `/pve/remotes/{remote}/qemu/{vmid}/snapshot` | 2 | `pdm_pve_create_snapshot` |
| DELETE | `/pve/remotes/{remote}/qemu/{vmid}/snapshot/{snapname}` | 2 | `pdm_pve_delete_snapshot` |
| PUT | `/pve/remotes/{remote}/qemu/{vmid}/snapshot/{snapname}/config` | 2 | `pdm_pve_update_snapshot` |
| POST | `/pve/remotes/{remote}/qemu/{vmid}/snapshot/{snapname}/rollback` | 2 | `pdm_pve_rollback_snapshot` |
| POST | `/pve/remotes/{remote}/qemu/{vmid}/start` | 2 | `pdm_pve_start_guest` |
| GET | `/pve/remotes/{remote}/qemu/{vmid}/status` | 1 | `pdm_pve_guest_status` |
| POST | `/pve/remotes/{remote}/qemu/{vmid}/stop` | 2 | `pdm_pve_stop_guest` |
| POST | `/pve/remotes/{remote}/qemu/{vmid}/termproxy` | — | interactive console (terminal proxy), not usable over MCP |
| POST | `/pve/remotes/{remote}/qemu/{vmid}/vncproxy` | — | interactive console (VNC proxy), not usable over MCP |
| GET | `/pve/remotes/{remote}/qemu/{vmid}/vncwebsocket` | — | interactive console (websocket), not usable over MCP |
| GET | `/pve/remotes/{remote}/resources` | 1 | `pdm_pve_resources` |
| GET | `/pve/remotes/{remote}/tasks` | 1 | `pdm_pve_list_tasks` |
| DELETE | `/pve/remotes/{remote}/tasks/{upid}` | 2 | `pdm_pve_stop_task` |
| GET | `/pve/remotes/{remote}/tasks/{upid}` | — | directory index |
| GET | `/pve/remotes/{remote}/tasks/{upid}/log` | 1 | `pdm_pve_task_log` |
| GET | `/pve/remotes/{remote}/tasks/{upid}/status` | 1 | `pdm_pve_task_status` |
| GET | `/pve/remotes/{remote}/updates` | 1 | `pdm_pve_updates` |
| POST | `/pve/scan` | 3 | remote management |

**Remotes, cross-remote tasks, updates and metrics**

| Method | Path | Phase | Tool or reason |
|---|---|---|---|
| GET | `/remotes` | — | directory index |
| GET | `/remotes/metric-collection/status` | 1 | `pdm_metric_collection_status` |
| POST | `/remotes/metric-collection/trigger` | 2 | `pdm_collect_metrics` |
| GET | `/remotes/remote` | 1 | `pdm_list_remotes` |
| POST | `/remotes/remote` | 3 | remote management |
| DELETE | `/remotes/remote/{id}` | 3 | remote management |
| GET | `/remotes/remote/{id}` | — | directory index |
| PUT | `/remotes/remote/{id}` | 3 | remote management |
| GET | `/remotes/remote/{id}/config` | 1 | `pdm_get_remote_config` |
| POST | `/remotes/remote/{id}/probe-certificate` | 3 | remote management |
| GET | `/remotes/remote/{id}/rrddata` | 1 | `pdm_get_remote_rrddata` |
| GET | `/remotes/remote/{id}/version` | 1 | `pdm_get_remote_version` |
| GET | `/remotes/tasks` | — | directory index |
| GET | `/remotes/tasks/list` | 1 | `pdm_list_remote_tasks` |
| POST | `/remotes/tasks/refresh` | 2 | `pdm_refresh_remote_tasks` |
| GET | `/remotes/tasks/statistics` | 1 | `pdm_remote_task_statistics` |
| GET | `/remotes/updates` | — | directory index |
| POST | `/remotes/updates/refresh` | 2 | `pdm_refresh_updates` |
| GET | `/remotes/updates/summary` | 1 | `pdm_update_summary` |

**Resources across all remotes**

| Method | Path | Phase | Tool or reason |
|---|---|---|---|
| GET | `/resources` | — | directory index |
| GET | `/resources/list` | 1 | `pdm_list_resources` |
| GET | `/resources/location-info` | 1 | `pdm_location_info` |
| GET | `/resources/status` | 1 | `pdm_resource_status` |
| GET | `/resources/subscription` | 1 | `pdm_subscription_status` |
| GET | `/resources/top-entities` | 1 | `pdm_top_entities` |

**SDN across remotes**

| Method | Path | Phase | Tool or reason |
|---|---|---|---|
| GET | `/sdn` | — | directory index |
| GET | `/sdn/controllers` | 1 | `pdm_sdn_list` |
| GET | `/sdn/vnets` | 1 | `pdm_sdn_list` |
| POST | `/sdn/vnets` | 3 | SDN writes |
| GET | `/sdn/zones` | 1 | `pdm_sdn_list` |
| POST | `/sdn/zones` | 3 | SDN writes |

**Subscription key pool**

| Method | Path | Phase | Tool or reason |
|---|---|---|---|
| GET | `/subscriptions` | — | directory index |
| POST | `/subscriptions/adopt-all` | 3 | subscription key pool |
| POST | `/subscriptions/adopt-key` | 3 | subscription key pool |
| POST | `/subscriptions/apply-pending` | 3 | subscription key pool |
| POST | `/subscriptions/auto-assign` | 3 | subscription key pool |
| POST | `/subscriptions/bulk-assign` | 3 | subscription key pool |
| POST | `/subscriptions/check` | 3 | subscription key pool |
| POST | `/subscriptions/clear-pending` | 3 | subscription key pool |
| GET | `/subscriptions/keys` | 3 | subscription key pool |
| POST | `/subscriptions/keys` | 3 | subscription key pool |
| DELETE | `/subscriptions/keys/{key}` | 3 | subscription key pool |
| GET | `/subscriptions/keys/{key}` | 3 | subscription key pool |
| DELETE | `/subscriptions/keys/{key}/assignment` | 3 | subscription key pool |
| POST | `/subscriptions/keys/{key}/assignment` | 3 | subscription key pool |
| GET | `/subscriptions/node-status` | 3 | subscription key pool |
| POST | `/subscriptions/queue-clear` | 3 | subscription key pool |
| POST | `/subscriptions/revert-pending-clear` | 3 | subscription key pool |

</details>

## Done

### Container restores: `restore_container_backup`

Reported by Will Furphy ([@wfurphy](https://github.com/wfurphy)) in #89. Thank you!

- **Restore flag.** Confirmed in Proxmox's `pve-container` 6.1.19 source (Proxmox VE 9): without `restore=1`, the
  backup's configuration is skipped and `unique` is refused. The tool now always sends it.
- **Disk sizes on restore.** `rootfs` and `mp0` to `mp255` set the disks to create. Disk
  inputs that name a protected guest's volume are refused, on this tool and every other.
- **Overwrite behavior.** The description says `force` replaces an existing container. The
  tool stays destructive, so `PROXMOX_NO_DESTRUCTIVE` hides it and the operator role can't
  call it.
