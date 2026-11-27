"""In-development banner: getting ready for Proxmox VE 9's opt-in Linux 7.3 kernel."""

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
    PURPLE_T,
    Anim,
    svg,
)

A = Anim(14)
END = 13.4
b = []

# Header: status pill, title, subtitle
b.append(
    f'  <rect x="40" y="26" width="168" height="26" rx="13" fill="#2d2410" stroke="{AMBER}"/>'
    f'<circle class="hum" cx="58" cy="39" r="5" fill="{AMBER}"/>'
    f'<text x="70" y="44" font-size="12" font-weight="800" letter-spacing=".08em" style="fill:#ffd88a">IN DEVELOPMENT</text>'
)
b.append(
    '  <text x="40" y="88" font-size="28" font-weight="800">Getting ready for Linux 7.3 on Proxmox VE 9</text>'
)
b.append(
    '  <text x="40" y="114" font-size="15" class="muted">Proxmox has an opt-in 7.3 kernel. '
    "Here is what we're building, testing and watching. Plans may change.</text>"
)

# Left: a nested test node moving from 7.0 to 7.3
b.append(
    f'  <rect x="30" y="134" width="300" height="214" rx="14" fill="{PANEL}" stroke="{LINE}"/>'
)
b.append(
    '  <text x="48" y="160" font-size="11" font-weight="700" class="muted" letter-spacing=".1em">NESTED TEST NODE</text>'
)
b.append(
    f'  <rect x="48" y="172" width="264" height="44" rx="10" fill="{CARD}" stroke="{LINE}"/>'
    '<text x="62" y="191" font-size="12" class="muted">running kernel</text>'
)
b.append(
    f'  <g class="{A.fade(0.2, 5.6)}"><text x="62" y="208" font-size="13" class="mono" style="fill:{BLUE_T}">7.0.14-pve</text>'
    f'<text x="298" y="208" text-anchor="end" font-size="11" class="muted">default</text></g>'
)
b.append(
    f'  <g class="{A.fade(6.4, END)}"><text x="62" y="208" font-size="13" class="mono" style="fill:{GREEN_T}">7.3.5-1-pve</text>'
    f'<text x="298" y="208" text-anchor="end" font-size="11" style="fill:{GREEN_T}">opt-in</text></g>'
)
b.append(
    f'  <g class="{A.fade(1.0, END)}"><text x="48" y="240" font-size="11.5" class="mono" style="fill:{ORANGE_T}">apt install proxmox-kernel-7.3</text></g>'
)
b.append('  <rect x="48" y="250" width="264" height="10" rx="5" fill="#232c3f"/>')
b.append(
    f'  <rect class="{A.grow(1.4, 4.4, 264, END)}" x="48" y="250" width="264" height="10" rx="5" fill="{ORANGE}"/>'
)
b.append(
    f'  <g class="{A.fade(4.8, END)}"><text x="48" y="282" font-size="11.5" class="mono" style="fill:{PURPLE_T}">reboot</text>'
    f'<text x="312" y="282" text-anchor="end" font-size="11" class="muted">into the new kernel</text></g>'
)
b.append(
    f'  <g class="{A.fade(6.8, END)}"><rect x="48" y="296" width="264" height="36" rx="10" fill="#0b0f18" stroke="{GREEN}"/>'
    f'<text x="62" y="319" font-size="12" class="mono"><tspan style="fill:{GREEN_T}">get_node_status</tspan>'
    f'<tspan class="muted"> kernel 7.3 ✓</tspan></text></g>'
)

# Right: three columns of what's planned, what might move, what stays put
b.append(
    f'  <rect x="346" y="134" width="584" height="214" rx="14" fill="{PANEL}" stroke="{LINE}"/>'
)
cols = [
    (
        "ON THE TABLE",
        ORANGE,
        ORANGE_T,
        [
            "kernel + package versions",
            "deploy_pve_vm (nested)",
            "live-run the deploy tools",
            "a 2nd cluster for PDM",
        ],
        1.2,
    ),
    (
        "COULD CHANGE",
        AMBER,
        "#ffd88a",
        [
            "ZFS disk %util readings",
            "kernel.org-based build",
            "missing NIC firmware",
            "new boot-log messages",
        ],
        5.6,
    ),
    (
        "STAYS THE SAME",
        BLUE,
        BLUE_T,
        [
            "the Proxmox VE API",
            "every existing tool",
            "7.0 stays the default",
            "nothing on production",
        ],
        9.4,
    ),
]
for ci, (head, col, tcol, items, t0) in enumerate(cols):
    x = 362 + ci * 188
    b.append(
        f'  <g class="{A.fade(t0 - 0.4, END)}"><text x="{x}" y="160" font-size="11" font-weight="700" '
        f'letter-spacing=".1em" style="fill:{tcol}">{head}</text></g>'
    )
    for i, item in enumerate(items):
        y = 174 + i * 42
        b.append(
            f'  <g class="{A.fade(t0 + i * 0.7, END)}"><rect x="{x}" y="{y}" width="176" height="32" rx="8" '
            f'fill="{CARD}" stroke="{col}"/><text x="{x + 12}" y="{y + 20}" font-size="11.5">{item}</text></g>'
        )

title = "In development: getting ready for Linux 7.3 on Proxmox VE 9"
desc = (
    "An in-development banner. A nested test node shows its running kernel as 7.0.14-pve, the default. "
    "apt install proxmox-kernel-7.3 runs, the node reboots, and get_node_status reports kernel 7.3.5-1-pve, opt-in. "
    "Beside it, three columns fill in. On the table: a kernel and package versions tool, deploy_pve_vm for a nested "
    "node, a live run of the deploy tools, and a second cluster for Datacenter Manager. Could change: ZFS disk "
    "utilization readings, a build based on kernel.org instead of Ubuntu, missing NIC firmware, and new boot-log messages. "
    "Stays the same: the Proxmox VE API, every existing tool, 7.0 as the default, and nothing on production."
)
extra = ".hum { animation: hum 2.4s ease-in-out infinite; } @keyframes hum { 0%,100% { opacity: .35; } 50% { opacity: 1; } }"
open(sys.argv[1], "w").write(svg(960, 370, title, desc, A.style(extra), "\n".join(b)))
