import sys

from common import (
    AMBER,
    CARD,
    GREEN,
    GREEN_T,
    LINE,
    MUTED,
    ORANGE,
    ORANGE_T,
    PANEL,
    TEXT,
    Anim,
    svg,
)

A = Anim(16)
alt = "{ opacity: 0; }"


def chip(x, y, w, tool, args, cls, color=ORANGE, tcolor=ORANGE_T):
    return (
        f'<g class="{cls}"><rect x="{x}" y="{y}" width="{w}" height="30" rx="9" fill="{CARD}" stroke="{color}"/>'
        f'<text x="{x+14}" y="{y+20}" font-size="13" class="mono"><tspan style="fill:{tcolor}">{tool}</tspan>'
        f'<tspan class="muted"> {args}</tspan></text></g>'
    )


def json_block(x, y, lines, cls, extra=""):
    out = [f'<g class="{cls}{extra}">']
    for i, (t, color) in enumerate(lines):
        out.append(
            f'<text x="{x}" y="{y + i*19}" font-size="12.5" class="mono" style="fill:{color}" xml:space="preserve">{t}</text>'
        )
    out.append("</g>")
    return "".join(out)


body = []
body.append(
    f"""  <text x="40" y="52" font-size="28" font-weight="800">Wait for the slow stuff</text>
  <text x="40" y="78" font-size="15" class="muted">Add <tspan class="mono" style="fill:{ORANGE_T}">wait: true</tspan>, or hand any task ID to <tspan class="mono" style="fill:{ORANGE_T}">wait_for_task</tspan>. Slow never means failed.</text>
  <rect x="660" y="100" width="270" height="318" rx="14" fill="{PANEL}" stroke="{LINE}"/>
  <text x="678" y="124" font-size="11" font-weight="700" class="muted" letter-spacing=".1em">WHAT THE ASSISTANT GETS BACK</text>"""
)

# Lane 1: clone with wait:true
body.append(
    '  <text x="40" y="118" font-size="11" font-weight="700" class="muted" letter-spacing=".1em">CLONE · FINISHES IN TIME</text>'
)
body.append(
    chip(40, 130, 590, "clone_vm", "node=pve2 vmid=9000 newid=123 wait:true", A.fade(0.4, 15.4))
)
body.append('  <rect x="40" y="178" width="590" height="14" rx="7" fill="#232c3f"/>')
body.append(
    f'  <rect class="{A.grow(1.0, 6.0, 590, 15.4)}" x="40" y="178" width="590" height="14" rx="7" fill="{GREEN}"/>'
)
for i, t in enumerate((1.4, 2.6, 4.2)):
    body.append(
        f'  <g class="{A.fade(t, 6.0)}"><text x="{60 + i*150}" y="214" font-size="11" class="mono muted">poll · running</text></g>'
    )
body.append(
    f'  <g class="{A.fade(6.1, 15.4)}"><text x="40" y="236" font-size="14" font-weight="800" style="fill:{GREEN_T}">✓ stopped · exitstatus OK</text>'
    f'<text x="262" y="236" font-size="12" class="muted">one call, no polling by the model</text></g>'
)
body.append(
    json_block(
        678,
        150,
        [
            ('{"data":"UPID:pve2:…:qmclone:…",', MUTED),
            (' "task":{"status":"stopped",', TEXT),
            ('         "exitstatus":"OK",', TEXT),
            ('         "ok":true}}', GREEN_T),
        ],
        A.fade(6.5, 15.4),
    )
)

# Lane 2: backup that outlasts the timeout
body.append(
    '  <text x="40" y="282" font-size="11" font-weight="700" class="muted" letter-spacing=".1em">BACKUP · OUTLASTS THE TIMEOUT</text>'
)
body.append(
    chip(40, 294, 590, "backup_vm", "node=pve1 vmid=120 storage=nas wait:true", A.fade(7.6, 15.4))
)
body.append('  <rect x="40" y="342" width="590" height="14" rx="7" fill="#232c3f"/>')
body.append(
    f'  <rect class="{A.grow(8.2, 11.6, 400, 15.4)}" x="40" y="342" width="400" height="14" rx="7" fill="{AMBER}"/>'
)
body.append(
    f'  <rect class="{A.grow(13.2, 14.6, 590, 15.4)}" x="40" y="342" width="590" height="14" rx="7" fill="{GREEN}"/>'
)
body.append(
    f'  <g class="alt {A.fade(11.7, 13.1)}"><text x="452" y="354" font-size="12" font-weight="800" style="fill:{AMBER}">timeout · still running</text></g>'
)
body.append(chip(40, 372, 460, "wait_for_task", "upid=UPID:pve1:…:vzdump:120:", A.fade(12.6, 15.4)))
body.append(
    f'  <g class="{A.fade(14.7, 15.4)}"><text x="516" y="392" font-size="14" font-weight="800" style="fill:{GREEN_T}">✓ OK</text></g>'
)
body.append(
    json_block(
        678,
        268,
        [
            ('{"task":{"status":"running",', AMBER),
            (' "note":"Still running after', MUTED),
            ('  900s. Call wait_for_task…"}}', MUTED),
        ],
        A.fade(11.9, 14.6),
        " alt",
    )
)
body.append(
    json_block(
        678,
        268,
        [
            ('{"status":"stopped",', TEXT),
            (' "exitstatus":"OK","ok":true}', GREEN_T),
        ],
        A.fade(14.8, 15.4),
    )
)
body.append(
    '  <text x="678" y="398" font-size="11.5" class="muted">A failed task adds its last 20 log lines.</text>'
)

title = "Waiting for long Proxmox tasks"
desc = (
    "clone_vm with wait: true shows a progress bar while the server polls the task, then returns status stopped, "
    "exitstatus OK and ok true in one result. A backup with wait: true outlasts the timeout and returns status "
    "running with a note; wait_for_task with its UPID then waits until it finishes OK. A failed task adds its last 20 log lines."
)
open(sys.argv[1], "w").write(svg(960, 440, title, desc, A.style(f".alt {alt}"), "\n".join(body)))
