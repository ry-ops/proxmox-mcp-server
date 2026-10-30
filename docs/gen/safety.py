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
    RED,
    RED_T,
    Anim,
    svg,
)

A = Anim(16)
END = 15.4
b = []
b.append(
    """  <text x="40" y="52" font-size="28" font-weight="800">Guardrails in the server</text>
  <text x="40" y="78" font-size="15" class="muted">Choose how much the assistant can touch, fence off the guests that matter, and keep a record.</text>"""
)

# Left: tool counts per mode
b.append(f'  <rect x="30" y="98" width="420" height="214" rx="14" fill="{PANEL}" stroke="{LINE}"/>')
b.append(
    '  <text x="48" y="124" font-size="11" font-weight="700" class="muted" letter-spacing=".1em">TOOLS THE CLIENT SEES</text>'
)
modes = [
    ("default", "every tool", 341, ORANGE, ORANGE_T),
    ("PROXMOX_NO_DESTRUCTIVE=true", "no delete, stop, wipe, rollback", 268, AMBER, "#ffd48a"),
    ("PROXMOX_READ_ONLY=true", "reads only", 150, BLUE, BLUE_T),
]
for i, (env, what, n, col, tcol) in enumerate(modes):
    y = 146 + i * 54
    w = round(260 * n / 341)
    t0 = 0.5 + i * 1.2
    b.append(
        f'  <g class="{A.fade(t0, END)}"><text x="48" y="{y}" font-size="12" class="mono" style="fill:{tcol}">{env}</text>'
        f'<text x="432" y="{y}" text-anchor="end" font-size="11" class="muted">{what}</text></g>'
    )
    b.append(f'  <rect x="48" y="{y+8}" width="260" height="16" rx="8" fill="#232c3f"/>')
    b.append(
        f'  <rect class="{A.grow(t0 + 0.2, t0 + 1.2, w, END)}" x="48" y="{y+8}" width="{w}" height="16" rx="8" fill="{col}"/>'
    )
    b.append(
        f'  <g class="{A.fade(t0 + 1.1, END)}"><text x="{48 + w + 10}" y="{y+21}" font-size="15" font-weight="800" style="fill:{tcol}">{n}</text></g>'
    )

# Right: protected guests on a node
b.append(
    f'  <rect x="470" y="98" width="460" height="214" rx="14" fill="{PANEL}" stroke="{LINE}"/>'
)
b.append(
    '  <text x="488" y="124" font-size="11" font-weight="700" class="muted" letter-spacing=".1em">PROTECTED GUESTS</text>'
)
b.append(
    f'  <text x="912" y="124" text-anchor="end" font-size="11.5" class="mono" style="fill:{GREEN_T}">PROXMOX_PROTECTED_VMIDS=100,101</text>'
)
guests = [
    (100, "router", True),
    (101, "dns", True),
    (120, "web-01", False),
    (121, "web-02", False),
    (130, "db", False),
]
for i, (vmid, name, prot) in enumerate(guests):
    x = 488 + i * 86
    stroke = GREEN if prot else LINE
    b.append(
        f'  <rect x="{x}" y="138" width="78" height="62" rx="10" fill="{CARD}" stroke="{stroke}" stroke-width="2"/>'
    )
    b.append(
        f'  <text x="{x+39}" y="162" text-anchor="middle" font-size="14" font-weight="800">{vmid}</text>'
    )
    b.append(
        f'  <text x="{x+39}" y="180" text-anchor="middle" font-size="11" class="muted">{name}</text>'
    )
    if prot:
        b.append(
            f'  <text x="{x+39}" y="194" text-anchor="middle" font-size="9.5" font-weight="800" letter-spacing=".05em" style="fill:{GREEN_T}">PROTECTED</text>'
        )
# flashes on tiles
b.append(
    f'  <rect class="alt {A.fade(5.6, 7.0, rise=0)}" x="660" y="138" width="78" height="62" rx="10" fill="none" stroke="{AMBER}" stroke-width="4"/>'
)
b.append(
    f'  <rect class="alt {A.fade(8.1, 9.6, rise=0)}" x="488" y="138" width="78" height="62" rx="10" fill="none" stroke="{RED}" stroke-width="4"/>'
)
calls = [
    (5.0, "stop_vm", "vmid=120", "✓ stopped", GREEN_T),
    (7.5, "delete_vm", "vmid=100", "✕ refused · 100 is protected", RED_T),
    (10.0, "node_stopall", "node=pve1", "✕ refused · list the guests", RED_T),
]
for i, (t, tool, args, verdict, vcol) in enumerate(calls):
    y = 214 + i * 30
    b.append(
        f'  <g class="{A.fade(t, END)}"><rect x="488" y="{y}" width="200" height="24" rx="7" fill="{CARD}" stroke="{ORANGE}"/>'
        f'<text x="498" y="{y+16}" font-size="12" class="mono"><tspan style="fill:{ORANGE_T}">{tool}</tspan><tspan class="muted"> {args}</tspan></text></g>'
    )
    b.append(
        f'  <g class="{A.fade(t + 0.8, END)}"><text x="700" y="{y+16}" font-size="12.5" font-weight="800" style="fill:{vcol}">{verdict}</text></g>'
    )

# Bottom: audit log
b.append(
    f'  <rect x="30" y="326" width="900" height="100" rx="14" fill="#0b0f18" stroke="{LINE}"/>'
)
b.append(
    '  <text x="48" y="350" font-size="11" font-weight="700" class="muted" letter-spacing=".1em">AUDIT LOG · PROXMOX_AUDIT_LOG=/var/log/proxmox-mcp/audit.jsonl</text>'
)
lines = [
    (
        6.2,
        '{"who":"ops","tool":"stop_vm","args":{"node":"pve1","vmid":120},"outcome":"ok","upid":"UPID:pve1:…"}',
        GREEN_T,
    ),
    (
        8.7,
        '{"who":"ops","tool":"delete_vm","args":{"node":"pve1","vmid":100},"outcome":"refused","error":"…protected"}',
        RED_T,
    ),
    (
        11.0,
        '{"who":"ops","tool":"node_stopall","args":{"node":"pve1"},"outcome":"refused","error":"…include protected guests"}',
        RED_T,
    ),
]
for i, (t, line, col) in enumerate(lines):
    b.append(
        f'  <g class="{A.fade(t, END)}"><text x="48" y="{372 + i*20}" font-size="11.5" class="mono" style="fill:{col}" xml:space="preserve">{line}</text></g>'
    )

title = "Guardrails: modes, protected guests and the audit log"
desc = (
    "Three bars show how many tools the client sees: 341 by default, 268 with PROXMOX_NO_DESTRUCTIVE, 150 with "
    "PROXMOX_READ_ONLY. On a node, guests 100 and 101 are protected. stop_vm on 120 succeeds, delete_vm on 100 is "
    "refused, and node_stopall without a guest list is refused. Each call appears in the JSON-lines audit log."
)
open(sys.argv[1], "w").write(
    svg(960, 444, title, desc, A.style(".alt { opacity: 0; }"), "\n".join(b))
)
