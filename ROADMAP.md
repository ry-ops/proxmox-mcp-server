# Roadmap

Work we plan to do in an upcoming release. Items here are not scheduled yet.

## Under review

### Container restores: check `restore_container_backup`

- **Restore flag.** Check that `restore_container_backup` tells Proxmox the request is a
  restore. If it doesn't, Proxmox may treat the backup as a template and skip the backup's
  own configuration (network, mount points, features). Confirm against a live Proxmox VE
  node before changing anything.
- **Disk sizes on restore.** Look at letting a restore set the root disk and mount point
  sizes, which is the only way to shrink a container disk. Make sure any new inputs can't
  get around `PROXMOX_PROTECTED_VMIDS`.
- **Overwrite behavior.** If restores can replace an existing container, document it and
  keep the tool behind the destructive-tool switches.
