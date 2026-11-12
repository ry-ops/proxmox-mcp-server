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
    Anim,
    svg,
)

A = Anim(18)
END = 17.4
b = []
b.append(
    """  <text x="40" y="52" font-size="28" font-weight="800">Ask for a machine, get a running one</text>
  <text x="40" y="78" font-size="15" class="muted">Official image, checksum checked, installed unattended, reachable when the tool returns.</text>"""
)

# Left: the request
b.append(f'  <rect x="30" y="98" width="300" height="250" rx="14" fill="{PANEL}" stroke="{LINE}"/>')
b.append('  <text x="48" y="124" font-size="11" font-weight="700" class="muted" letter-spacing=".1em">YOU ASK</text>')
b.append(
    f'  <g class="{A.fade(0.4, END)}"><rect x="48" y="138" width="264" height="46" rx="12" fill="{CARD}" stroke="{BLUE}"/>'
    f'<text x="62" y="158" font-size="13.5" style="fill:{BLUE_T}">Spin up a Kali VM</text>'
    f'<text x="62" y="175" font-size="13.5" style="fill:{BLUE_T}">for the lab, please.</text></g>'
)
b.append(
    f'  <g class="{A.fade(1.4, END)}"><rect x="48" y="198" width="264" height="30" rx="8" fill="{CARD}" stroke="{ORANGE}"/>'
    f'<text x="60" y="218" font-size="12" class="mono"><tspan style="fill:{ORANGE_T}">deploy_kali_vm</tspan><tspan class="muted"> node=pve01</tspan></text></g>'
)
b.append(
    f'  <g class="{A.fade(10.4, END)}"><rect x="48" y="244" width="264" height="88" rx="12" fill="#0b0f18" stroke="{GREEN}"/>'
    f'<text x="62" y="266" font-size="12" class="mono" style="fill:{GREEN_T}" xml:space="preserve">status   ready</text>'
    f'<text x="62" y="284" font-size="12" class="mono" style="fill:{GREEN_T}" xml:space="preserve">ip       10.0.0.77</text>'
    f'<text x="62" y="302" font-size="12" class="mono" style="fill:{GREEN_T}" xml:space="preserve">user     kali</text>'
    f'<text x="62" y="320" font-size="12" class="mono" style="fill:{GREEN_T}" xml:space="preserve">password •••••••• (once)</text></g>'
)

# Middle: the steps
b.append(f'  <rect x="346" y="98" width="584" height="250" rx="14" fill="{PANEL}" stroke="{LINE}"/>')
b.append('  <text x="364" y="124" font-size="11" font-weight="700" class="muted" letter-spacing=".1em">THE SERVER DOES</text>')
steps = [
    ("Fetch Kali's official cloud image", "241 MB · SHA-256 checked", ORANGE_T),
    ("Repack the sparse disk as qcow2", "25 GiB → 1.06 GiB uploaded", AMBER),
    ("Build a seed ISO: cloud-init cidata", "user, key or password, guest agent", PURPLE_T),
    ("Create VM 120 and boot it", "VirtIO disk and NIC, your bridge and VLAN", BLUE_T),
    ("Wait for the guest agent", "reads the address: 10.0.0.77", GREEN_T),
    ("Delete the seed ISO", "it held the credentials", GREEN_T),
]
for i, (step, detail, col) in enumerate(steps):
    y = 146 + i * 33
    t = 2.2 + i * 1.35
    b.append(
        f'  <g class="{A.fade(t, END)}"><circle cx="374" cy="{y-4}" r="9" fill="{CARD}" stroke="{col}" stroke-width="2"/>'
        f'<text x="374" y="{y}" text-anchor="middle" font-size="11" font-weight="800" style="fill:{col}">✓</text>'
        f'<text x="392" y="{y}" font-size="13.5" font-weight="700">{step}</text>'
        f'<text x="912" y="{y}" text-anchor="end" font-size="11.5" class="muted">{detail}</text></g>'
    )

# Bottom: four OSes building side by side
b.append(f'  <rect x="30" y="364" width="900" height="150" rx="14" fill="{PANEL}" stroke="{LINE}"/>')
b.append(
    '  <text x="48" y="390" font-size="11" font-weight="700" class="muted" letter-spacing=".1em">ONE TOOL PER OS · SAME RESULT</text>'
)
oses = [
    ("deploy_ubuntu_vm", "Ubuntu 24.04 LTS", "ready · ssh ubuntu@10.0.0.71", 3.0, 6.5, ORANGE, ORANGE_T),
    ("deploy_kali_vm", "Kali Linux 2026.3", "ready · ssh kali@10.0.0.77", 3.4, 9.6, BLUE, BLUE_T),
    ("deploy_windows11_vm", "Windows 11 (TPM 2.0, Secure Boot)", "ready · RDP or console, admin", 3.8, 14.0, PURPLE, PURPLE_T),
    ("deploy_pdm_vm", "Datacenter Manager on Debian 13", "ready · https://10.0.0.80:8443", 4.2, 11.6, GREEN, GREEN_T),
]
for i, (tool, label, done, t0, t1, col, tcol) in enumerate(oses):
    y = 412 + i * 25
    b.append(
        f'  <g class="{A.fade(t0 - 0.6, END)}"><text x="48" y="{y+4}" font-size="11.5" class="mono" style="fill:{tcol}">{tool}</text>'
        f'<text x="246" y="{y+4}" font-size="12" class="muted">{label}</text></g>'
    )
    b.append(f'  <rect x="470" y="{y-7}" width="230" height="12" rx="6" fill="#232c3f"/>')
    b.append(f'  <rect class="{A.grow(t0, t1, 230, END)}" x="470" y="{y-7}" width="230" height="12" rx="6" fill="{col}"/>')
    b.append(
        f'  <g class="{A.fade(t1 + 0.1, END)}"><text x="912" y="{y+4}" text-anchor="end" font-size="12" font-weight="700" style="fill:{tcol}">{done}</text></g>'
    )

title = "Deploy an OS by asking"
desc = (
    "You ask for a Kali VM and the server runs deploy_kali_vm: it fetches Kali's official cloud image and checks its "
    "SHA-256, repacks the sparse 25 GiB disk as a 1.06 GiB qcow2, builds a cloud-init seed ISO, creates and boots VM "
    "120, waits for the guest agent to report 10.0.0.77, and deletes the seed ISO. The result shows the address, the "
    "user and a password returned once. Below, Ubuntu, Kali, Windows 11 and Datacenter Manager build side by side, "
    "each tool finishing with how to reach the machine."
)
open(sys.argv[1], "w").write(svg(960, 532, title, desc, A.style(), "\n".join(b)))
