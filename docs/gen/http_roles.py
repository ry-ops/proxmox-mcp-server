import sys

from common import (
    AMBER,
    BG,
    BLUE,
    BLUE_T,
    CARD,
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
    """  <text x="40" y="52" font-size="28" font-weight="800">One server, many clients</text>
  <text x="40" y="78" font-size="15" class="muted">Serve it over HTTP and give every client its own token and role. Each sees only what its role allows.</text>"""
)

rows = [
    ("ops", "Claude Code", "admin", ORANGE, ORANGE_T, "341 tools", "everything"),
    ("ci", "pipeline", "operator", AMBER, "#ffd48a", "268 tools", "no destructive tools"),
    ("grafana", "dashboard", "read", BLUE, BLUE_T, "150 tools", "reads only"),
    ("unknown", "no token", "—", RED, RED_T, "401", "Unauthorized"),
]
b.append(
    f'  <rect x="400" y="112" width="170" height="226" rx="16" fill="{CARD}" stroke="{ORANGE}" stroke-width="2.5"/>'
)
b.append(
    '  <text x="485" y="200" text-anchor="middle" font-size="14" font-weight="800">proxmox-mcp</text>'
)
b.append(
    '  <text x="485" y="218" text-anchor="middle" font-size="14" font-weight="800">-server-http</text>'
)
b.append(
    '  <text x="485" y="242" text-anchor="middle" font-size="11" class="mono muted">:8811/mcp</text>'
)
b.append(
    '  <text x="485" y="262" text-anchor="middle" font-size="10.5" class="muted">bearer tokens · roles</text>'
)
for i, (name, what, role, col, tcol, result, note) in enumerate(rows):
    y = 112 + i * 58
    cy = y + 23
    t = 0.8 + i * 1.7
    b.append(
        f'  <rect x="40" y="{y}" width="250" height="46" rx="10" fill="{PANEL}" stroke="{LINE}"/>'
    )
    b.append(f'  <text x="56" y="{y+20}" font-size="14" font-weight="700">{name}</text>')
    b.append(f'  <text x="56" y="{y+37}" font-size="11.5" class="muted">{what}</text>')
    b.append(
        f'  <rect x="196" y="{y+12}" width="80" height="22" rx="11" fill="{BG}" stroke="{col}"/>'
        f'<text x="236" y="{y+27}" text-anchor="middle" font-size="11" font-weight="700" class="mono" style="fill:{tcol}">{role}</text>'
    )
    b.append(
        f'  <line x1="292" y1="{cy}" x2="398" y2="{cy}" stroke="{LINE}" stroke-width="2" stroke-dasharray="2 6" stroke-linecap="round"/>'
    )
    b.append(f'  <circle class="{A.move(t, t + 0.8, 100)}" cx="296" cy="{cy}" r="6" fill="{col}"/>')
    b.append(
        f'  <line x1="572" y1="{cy}" x2="640" y2="{cy}" stroke="{LINE}" stroke-width="2" stroke-dasharray="2 6" stroke-linecap="round"/>'
    )
    b.append(
        f'  <circle class="{A.move(t + 0.9, t + 1.3, 64)}" cx="574" cy="{cy}" r="6" fill="{col}"/>'
    )
    b.append(
        f'  <g class="{A.fade(t + 1.3, END)}"><rect x="644" y="{y}" width="286" height="46" rx="10" fill="{PANEL}" stroke="{col}"/>'
        f'<text x="662" y="{y+29}" font-size="18" font-weight="800" style="fill:{tcol}">{result}</text>'
        f'<text x="912" y="{y+28}" text-anchor="end" font-size="12" class="muted">{note}</text></g>'
    )

b.append(f'  <rect x="30" y="352" width="900" height="76" rx="14" fill="#0b0f18" stroke="{LINE}"/>')
b.append(
    '  <text x="48" y="374" font-size="11" font-weight="700" class="muted" letter-spacing=".1em">AUDIT LOG · WHO DID WHAT</text>'
)
for i, (t, line, col) in enumerate(
    [
        (
            9.0,
            '{"who":"ci","via":"http","tool":"clone_vm","args":{"vmid":9000,"newid":123},"outcome":"ok","task_ok":true}',
            GREEN_T,
        ),
        (
            10.8,
            '{"who":"grafana","via":"http","tool":"stop_vm","outcome":"refused","error":"…not allowed for grafana (role: read)"}',
            RED_T,
        ),
    ]
):
    b.append(
        f'  <g class="{A.fade(t, END)}"><text x="48" y="{396 + i*20}" font-size="11.5" class="mono" style="fill:{col}" xml:space="preserve">{line}</text></g>'
    )

title = "HTTP clients with their own tokens and roles"
desc = (
    "Four clients call proxmox-mcp-server-http. ops with the admin role sees 341 tools, ci with the operator role sees "
    "268, grafana with the read role sees 150, and a client with no token gets 401 Unauthorized. The audit log records "
    "ci's clone_vm as ok and grafana's stop_vm as refused for its role."
)
open(sys.argv[1], "w").write(svg(960, 444, title, desc, A.style(), "\n".join(b)))
