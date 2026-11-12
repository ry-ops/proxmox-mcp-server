import sys

from common import (
    AMBER,
    BLUE,
    BLUE_T,
    CARD,
    GREEN,
    GREEN_T,
    LINE,
    ORANGE,
    ORANGE_T,
    PANEL,
    PURPLE,
    PURPLE_T,
    RED,
    RED_T,
    Anim,
    svg,
)

A = Anim(18)
END = 17.4
b = []
b.append(
    """  <text x="40" y="52" font-size="28" font-weight="800">One connection, every cluster</text>
  <text x="40" y="78" font-size="15" class="muted">Point the server at Proxmox Datacenter Manager and 89 tools reach every remote it manages.</text>"""
)

# Server -> PDM -> remotes
b.append(
    f'  <rect x="30" y="160" width="170" height="96" rx="14" fill="{PANEL}" stroke="{ORANGE}" stroke-width="2"/>'
    f'<text x="115" y="196" text-anchor="middle" font-size="15" font-weight="800">proxmox-mcp</text>'
    f'<text x="115" y="216" text-anchor="middle" font-size="12" class="muted">pdm toolset</text>'
    f'<text x="115" y="236" text-anchor="middle" font-size="11" class="mono" style="fill:{ORANGE_T}">PDMAPIToken</text>'
)
b.append(
    f'  <rect x="300" y="146" width="200" height="124" rx="14" fill="{PANEL}" stroke="{GREEN}" stroke-width="2"/>'
    f'<text x="400" y="182" text-anchor="middle" font-size="15" font-weight="800">Datacenter Manager</text>'
    f'<text x="400" y="202" text-anchor="middle" font-size="12" class="muted">PDM 1.1 · :8443</text>'
    f'<text x="400" y="230" text-anchor="middle" font-size="11" class="mono" style="fill:{GREEN_T}">327 endpoints mapped</text>'
    f'<text x="400" y="248" text-anchor="middle" font-size="11" class="mono" style="fill:{GREEN_T}">from its own schema</text>'
)
b.append(f'  <line x1="200" y1="208" x2="300" y2="208" stroke="{LINE}" stroke-width="2"/>')
remotes = [
    ("pve-lab", "Proxmox VE · 1 node", 104, BLUE, BLUE_T),
    ("pve-prod", "Proxmox VE · 3-node cluster", 208, PURPLE, PURPLE_T),
    ("pbs-backup", "Backup Server · 2 datastores", 312, AMBER, "#ffd48a"),
]
for name, what, y, col, tcol in remotes:
    b.append(
        f'  <rect x="620" y="{y}" width="310" height="76" rx="14" fill="{PANEL}" stroke="{col}" stroke-width="2"/>'
        f'<text x="640" y="{y+30}" font-size="15" font-weight="800" style="fill:{tcol}">{name}</text>'
        f'<text x="640" y="{y+52}" font-size="12" class="muted">{what}</text>'
    )
    b.append(f'  <line x1="500" y1="208" x2="620" y2="{y+38}" stroke="{LINE}" stroke-width="2"/>')

# A read fans out
b.append(f'  <circle class="{A.move(0.6, 1.6, 100, 0)}" cx="200" cy="208" r="6" fill="{ORANGE}"/>')
for name, _, y, col, _ in remotes:
    b.append(f'  <circle class="{A.move(1.7, 2.6, 120, y + 38 - 208)}" cx="500" cy="208" r="6" fill="{col}"/>')
b.append(
    f'  <g class="{A.fade(0.4, END)}"><rect x="30" y="100" width="300" height="30" rx="8" fill="{CARD}" stroke="{ORANGE}"/>'
    f'<text x="42" y="120" font-size="12" class="mono"><tspan style="fill:{ORANGE_T}">pdm_list_resources</tspan><tspan class="muted"> every remote</tspan></text></g>'
)
b.append(
    f'  <g class="{A.fade(2.9, END)}"><text x="42" y="300" font-size="13" font-weight="700" style="fill:{GREEN_T}">✓ 31 guests · 5 nodes · 2 datastores, one call</text></g>'
)

# Cross-cluster migration
b.append(
    f'  <g class="{A.fade(4.2, END)}"><rect x="30" y="406" width="430" height="30" rx="8" fill="{CARD}" stroke="{PURPLE}"/>'
    f'<text x="42" y="426" font-size="12" class="mono"><tspan style="fill:{PURPLE_T}">pdm_pve_remote_migrate_guest</tspan><tspan class="muted"> web-01 → pve-prod</tspan></text></g>'
)
b.append(
    f'  <g class="{A.move(4.8, 7.0, 0, 104, hide_after=0.6)}"><rect x="850" y="122" width="66" height="22" rx="6" fill="{BLUE}"/>'
    f'<text x="883" y="137" text-anchor="middle" font-size="11" font-weight="800" style="fill:#0f1420">web-01</text></g>'
)
b.append(
    f'  <rect class="alt {A.fade(7.0, 9.0, rise=0)}" x="620" y="208" width="310" height="76" rx="14" fill="none" stroke="{GREEN}" stroke-width="4"/>'
)
b.append(
    f'  <g class="{A.fade(7.2, END)}"><text x="476" y="426" font-size="12.5" font-weight="800" style="fill:{GREEN_T}">✓ moved across clusters, task OK</text></g>'
)

# Guardrails
b.append(
    f'  <g class="{A.fade(9.6, END)}"><rect x="30" y="446" width="430" height="30" rx="8" fill="{CARD}" stroke="{ORANGE}"/>'
    f'<text x="42" y="466" font-size="12" class="mono"><tspan style="fill:{ORANGE_T}">pdm_pve_stop_guest</tspan><tspan class="muted"> pve-lab:104</tspan></text></g>'
)
b.append(
    f'  <g class="{A.fade(10.3, END)}"><text x="476" y="466" font-size="12.5" font-weight="800" style="fill:{RED_T}">✕ refused · protected (PDM_PROTECTED_GUESTS)</text></g>'
)
b.append(
    f'  <g class="{A.fade(12.0, END)}"><rect x="30" y="486" width="430" height="30" rx="8" fill="{CARD}" stroke="{ORANGE}"/>'
    f'<text x="42" y="506" font-size="12" class="mono"><tspan style="fill:{ORANGE_T}">pdm_collect_metrics</tspan><tspan class="muted"> all remotes</tspan></text></g>'
)
b.append(
    f'  <g class="{A.fade(12.7, END)}"><text x="476" y="506" font-size="12.5" font-weight="800" style="fill:#ffd48a">! needs root@pam with a password: here is what to use</text></g>'
)
b.append(f'  <rect class="alt {A.fade(10.3, 11.8, rise=0)}" x="620" y="104" width="310" height="76" rx="14" fill="none" stroke="{RED}" stroke-width="4"/>')

title = "Proxmox Datacenter Manager through one connection"
desc = (
    "proxmox-mcp's pdm toolset connects to Proxmox Datacenter Manager with an API token. One pdm_list_resources call "
    "fans out to three remotes, pve-lab, pve-prod and pbs-backup, and returns their guests, nodes and datastores. "
    "pdm_pve_remote_migrate_guest moves web-01 from pve-lab to the pve-prod cluster. pdm_pve_stop_guest on the "
    "protected guest pve-lab:104 is refused, and pdm_collect_metrics, which PDM reserves for root@pam, explains the "
    "elevated permission it needs and what to use instead."
)
open(sys.argv[1], "w").write(svg(960, 534, title, desc, A.style(".alt { opacity: 0; }"), "\n".join(b)))
