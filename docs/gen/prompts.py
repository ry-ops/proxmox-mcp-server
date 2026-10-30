import sys

from common import (
    AMBER,
    BG,
    BLUE,
    BLUE_T,
    CARD,
    GREEN,
    GREEN_T,
    LINE,
    MUTED,
    ORANGE,
    ORANGE_T,
    PANEL,
    RED,
    RED_T,
    TEXT,
    Anim,
    svg,
)

A = Anim(16)
END = 15.4
b = []
b.append(
    """  <text x="40" y="52" font-size="28" font-weight="800">Workflows built in</text>
  <text x="40" y="78" font-size="15" class="muted">Pick a prompt and the assistant runs the steps with real tools, under the same rules as always.</text>"""
)

# Left: client
b.append(f'  <rect x="30" y="98" width="440" height="330" rx="14" fill="{PANEL}" stroke="{LINE}"/>')
b.append(f'  <rect x="46" y="112" width="408" height="34" rx="10" fill="{BG}" stroke="{LINE}"/>')
b.append(
    f'  <g class="alt {A.fade(0.3, 2.9, rise=0)}"><text x="60" y="134" font-size="13" class="mono" style="fill:{TEXT}">/mcp__proxmox__</text></g>'
)
b.append(
    f'  <g class="{A.fade(3.0, END, rise=0)}"><text x="60" y="134" font-size="13" class="mono" style="fill:{ORANGE_T}">/mcp__proxmox__cluster_health_check</text></g>'
)
menu = [
    "cluster_health_check",
    "capacity_report",
    "safe_change",
    "investigate_failed_tasks",
    "decommission_guest",
]
mc = A.fade(0.6, 2.9)
b.append(
    f'  <g class="alt {mc}"><rect x="46" y="150" width="408" height="{len(menu)*28 + 12}" rx="10" fill="{CARD}" stroke="{LINE}"/>'
)
b.append('<rect x="52" y="156" width="396" height="26" rx="7" fill="#2a3550"/>')
for i, m in enumerate(menu):
    b.append(
        f'<text x="64" y="{174 + i*28}" font-size="12.5" class="mono" style="fill:{ORANGE_T if i == 0 else MUTED}">{m}</text>'
    )
b.append("</g>")
steps = [
    "get_cluster_status",
    "get_cluster_resources",
    "list_cluster_tasks",
    "get_task_log",
    "get_ha_status",
]
for i, s in enumerate(steps):
    t = 3.6 + i * 0.8
    y = 160 + i * 34
    b.append(
        f'  <g class="{A.fade(t, END)}"><rect x="46" y="{y}" width="300" height="26" rx="8" fill="{CARD}" stroke="{ORANGE}"/>'
        f'<text x="58" y="{y+18}" font-size="12.5" class="mono" style="fill:{ORANGE_T}">{s}</text>'
        f'<text x="358" y="{y+18}" font-size="11" font-weight="800" style="fill:{GREEN_T}">READ-ONLY ✓</text></g>'
    )
b.append(f'  <line x1="46" y1="342" x2="454" y2="342" stroke="{LINE}"/>')
b.append(
    '  <text x="46" y="364" font-size="11" font-weight="700" class="muted" letter-spacing=".1em">RESOURCES · LIVE STATE, NO TOOL CALL</text>'
)
for i, r in enumerate(
    ["proxmox://cluster/resources", "proxmox://nodes", "proxmox://vms/{node}/{vmid}/config"]
):
    x = 46 + (0 if i != 1 else 214)
    y = 376 if i < 2 else 404
    w = 204 if i == 0 else (146 if i == 1 else 270)
    b.append(
        f'  <g class="{A.fade(10.5 + i*0.5, END)}"><rect x="{x}" y="{y}" width="{w}" height="22" rx="11" fill="#10283a" stroke="{BLUE}"/>'
        f'<text x="{x+12}" y="{y+15}" font-size="11" class="mono" style="fill:{BLUE_T}">{r}</text></g>'
    )

# Right: report
b.append(
    f'  <rect x="490" y="98" width="440" height="330" rx="14" fill="{PANEL}" stroke="{LINE}"/>'
)
b.append(
    '  <text x="508" y="124" font-size="11" font-weight="700" class="muted" letter-spacing=".1em">THE ASSISTANT REPORTS</text>'
)
sections = [
    (
        "CRITICAL",
        RED,
        RED_T,
        [
            "Backup job on pve2 failed: storage 'nas' unreachable",
            "Fix: check the NFS mount, then rerun the job",
        ],
    ),
    (
        "WARNING",
        AMBER,
        "#ffd48a",
        ["local-lvm on pve1 is almost full", "Fix: prune old snapshots or grow the pool"],
    ),
    (
        "OK",
        GREEN,
        GREEN_T,
        ["Quorum held, all nodes online", "HA resources in their requested state"],
    ),
]
for i, (label, col, tcol, lines) in enumerate(sections):
    y = 140 + i * 84
    t = 8.0 + i * 0.9
    b.append(
        f'  <g class="{A.fade(t, END)}"><rect x="508" y="{y}" width="404" height="72" rx="10" fill="{CARD}"/>'
        f'<rect x="508" y="{y}" width="5" height="72" rx="2" fill="{col}"/>'
        f'<text x="526" y="{y+22}" font-size="11" font-weight="800" letter-spacing=".08em" style="fill:{tcol}">{label}</text>'
        f'<text x="526" y="{y+42}" font-size="13">{lines[0]}</text>'
        f'<text x="526" y="{y+61}" font-size="12" class="muted">{lines[1]}</text></g>'
    )
b.append(
    f'  <g class="{A.fade(11.0, END)}"><text x="508" y="412" font-size="13" font-weight="700">Verdict: healthy, one backup to fix today.</text></g>'
)

title = "Built-in MCP prompts and resources"
desc = (
    "In the client, typing /mcp__proxmox__ lists five prompts. Choosing cluster_health_check runs five read-only "
    "tools: get_cluster_status, get_cluster_resources, list_cluster_tasks, get_task_log and get_ha_status. The "
    "assistant reports one critical item, one warning and what is OK, with a verdict. Resources such as "
    "proxmox://cluster/resources attach live state without a tool call."
)
open(sys.argv[1], "w").write(
    svg(960, 444, title, desc, A.style(".alt { opacity: 0; }"), "\n".join(b))
)
