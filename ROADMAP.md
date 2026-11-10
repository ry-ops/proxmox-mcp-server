# Roadmap

Work we plan to do in an upcoming release. Items here are not scheduled yet.

## Under review

Nothing right now.

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
