"""In-development banner for the Linux 7.3 roadmap (ROADMAP-KERNEL.md).

A Proxmox server in a flat sticker style: the chassis plate (the Proxmox VE API) stays put, and each
roadmap item snaps into a socket. Standalone: it uses its own warm palette, not common.py.
"""

import math
import random
import sys

INK = "#1d1d1b"
CREAM = "#f6efe2"
PAPER = "#fffaf0"
ORANGE = "#e06a2c"
ORANGE_D = "#b9531f"
GREEN = "#1f4a33"
GREEN2 = "#2f5a3d"
NAVY = "#1f3a5a"
TAN = "#d4a061"
TAN_D = "#b98446"
BLUE = "#3d7cb3"
BLUE_D = "#2c5d88"
RED = "#c2362b"
GREY = "#aab3bd"
BROWN = "#6b3f22"
DUR = 18.0
END = 17.0
rules = []
n = [0]


def p(t):
    return f"{max(0, min(100, 100 * t / DUR)):.2f}%"


def cls():
    n[0] += 1
    return f"k{n[0]}"


def drop(t, dy=-150, out=END):
    c = cls()
    rules.append(
        f"@keyframes {c} {{ 0%,{p(t)} {{ transform: translateY({dy}px); opacity: 0; }} {p(t + 0.05)} {{ opacity: 1; }} "
        f"{p(t + 0.32)} {{ transform: translateY(6px) scaleY(.94); }} {p(t + 0.45)} {{ transform: translateY(-3px); }} "
        f"{p(t + 0.58)},{p(out)} {{ transform: translateY(0); opacity: 1; }} {p(out + 0.35)},100% {{ transform: translateY(-40px); opacity: 0; }} }} "
        f".{c} {{ animation: {c} {DUR}s infinite; transform-box: fill-box; transform-origin: 50% 100%; }}"
    )
    return c


def swap_out(t_in, t_off):
    c = cls()
    rules.append(
        f"@keyframes {c} {{ 0%,{p(t_in)} {{ transform: translateY(-150px); opacity: 0; }} {p(t_in + 0.05)} {{ opacity: 1; }} "
        f"{p(t_in + 0.32)} {{ transform: translateY(6px); }} {p(t_in + 0.45)} {{ transform: translateY(-3px); }} "
        f"{p(t_in + 0.58)},{p(t_off)} {{ transform: translate(0,0) rotate(0); opacity: 1; }} "
        f"{p(t_off + 0.5)},100% {{ transform: translate(-150px,-90px) rotate(-40deg); opacity: 0; }} }} "
        f".{c} {{ animation: {c} {DUR}s infinite; opacity: 0; transform-box: fill-box; transform-origin: 50% 50%; }}"
    )
    return c


def stick(t, out=END):
    c = cls()
    rules.append(
        f"@keyframes {c} {{ 0%,{p(t)} {{ transform: scale(1.35); opacity: 0; }} {p(t + 0.2)} {{ transform: scale(.95); opacity: 1; }} "
        f"{p(t + 0.35)},{p(out)} {{ transform: scale(1); opacity: 1; }} {p(out + 0.3)},100% {{ transform: scale(1); opacity: 0; }} }} "
        f".{c} {{ animation: {c} {DUR}s infinite; transform-box: fill-box; transform-origin: 50% 50%; }}"
    )
    return c


def window(t0, t1, hidden=False):
    c = cls()
    rules.append(
        f"@keyframes {c} {{ 0%,{p(t0)} {{ opacity: 0; transform: translateY(4px); }} {p(t0 + 0.3)},{p(t1)} {{ opacity: 1; transform: translateY(0); }} {p(t1 + 0.3)},100% {{ opacity: 0; }} }} "
        f".{c} {{ animation: {c} {DUR}s infinite;{' opacity: 0;' if hidden else ''} }}"
    )
    return c


POTATO = (
    "M120 40C176 38 202 92 197 152C192 216 164 254 120 254C74 254 46 216 44 152C42 90 66 42 120 40Z"
)


CHASSIS = "#e8dfcf"
CHASSIS_S = "#c9bda6"
CHASSIS_T = "#f4ecdd"
SCREEN = "#12261d"
PHOS = "#9ff0c4"


def slide(t, dx=220, out=END):
    c = cls()
    rules.append(
        f"@keyframes {c} {{ 0%,{p(t)} {{ transform: translateX({dx}px); opacity: 0; }} {p(t + 0.05)} {{ opacity: 1; }} "
        f"{p(t + 0.45)} {{ transform: translateX(-5px); }} {p(t + 0.58)},{p(out)} {{ transform: translateX(0); opacity: 1; }} "
        f"{p(out + 0.35)},100% {{ transform: translateX({dx}px); opacity: 0; }} }} .{c} {{ animation: {c} {DUR}s infinite; }}"
    )
    return c


def cartridge(fill, band, label):
    ridges = "".join(
        f'<path d="M{x} -8v12" stroke="{band}" stroke-width="2.4" stroke-linecap="round"/>'
        for x in (82, 90, 98)
    )
    return (
        f'<rect x="72" y="-16" width="76" height="52" rx="7" fill="{fill}" stroke="{INK}" stroke-width="3.2"/>{ridges}'
        f'<rect x="104" y="-10" width="38" height="22" rx="5" fill="{CREAM}" stroke="{INK}" stroke-width="2.4"/>'
        f'<text x="123" y="6" text-anchor="middle" font-size="13" font-weight="900" class="rnd" style="fill:{INK}">{label}</text>'
    )


def server():
    T_SCREEN, T_C70, T_C70OFF, T_C73, T_WRENCH, T_SLED, T_PLUG = 1.0, 2.2, 3.8, 4.3, 6.2, 7.6, 9.0
    g = []
    g.append('<ellipse cx="116" cy="292" rx="132" ry="10" fill="#000" opacity=".22"/>')
    # cartridges sit in the top slot, drawn before the chassis so it hides their lower half
    g.append(f'<g class="{swap_out(T_C70, T_C70OFF)}">{cartridge(BLUE, BLUE_D, "7.0")}</g>')
    g.append(f'<g class="{drop(T_C73, -170)}">{cartridge(ORANGE, ORANGE_D, "7.3")}</g>')
    # power cable (behind chassis), plugs into the side
    g.append(
        f'<g class="{slide(T_PLUG, 160)}"><path d="M236 236C276 236 262 292 330 292" stroke="{INK}" stroke-width="10" fill="none" stroke-linecap="round"/>'
        f'<path d="M236 236C276 236 262 292 330 292" stroke="#3b3a37" stroke-width="5" fill="none" stroke-linecap="round"/>'
        f'<rect x="226" y="226" width="22" height="20" rx="4" fill="#3b3a37" stroke="{INK}" stroke-width="3"/></g>'
    )
    # chassis: the part that stays
    g.append(
        f'<g stroke="{INK}" stroke-width="3.2" stroke-linejoin="round">'
        f'<path d="M0 40L32 20H232L200 40Z" fill="{CHASSIS_T}"/>'
        f'<rect x="70" y="26" width="80" height="9" rx="3" fill="#3b3a37" stroke-width="2.4"/>'
        f'<path d="M200 40L232 20V262L200 282Z" fill="{CHASSIS_S}"/>'
        f'<rect x="0" y="40" width="200" height="242" rx="10" fill="{CHASSIS}"/>'
        f'<path d="M212 60v40M212 116v40M220 54v40M220 110v40" stroke="#a89a80" stroke-width="2.4" stroke-linecap="round"/>'
        f'<rect x="18" y="58" width="164" height="72" rx="8" fill="none" stroke="#a89a80" stroke-width="2.4" stroke-dasharray="6 5"/>'
        f'<rect x="18" y="144" width="164" height="34" rx="6" fill="#d6ccb9" stroke-width="2.6"/>'
        f'<rect x="18" y="186" width="164" height="34" rx="6" fill="#d6ccb9" stroke-width="2.6"/>'
        f'<rect x="18" y="242" width="164" height="28" rx="6" fill="{TAN}" stroke-width="2.6"/>'
        f'<path d="M12 282h20v8h-20zM168 282h20v8h-20z" fill="#3b3a37"/></g>'
        f'<g style="fill:{INK}">'
        + "".join(f'<circle cx="{cx}" cy="256" r="2.4"/>' for cx in (28, 172))
        + "</g>"
        f'<text x="100" y="260" text-anchor="middle" font-size="11" font-weight="900" class="rnd" letter-spacing=".06em" style="fill:{INK}">PROXMOX VE API</text>'
        f'<circle cx="34" cy="231" r="7" fill="{CREAM}" stroke="{INK}" stroke-width="2.6"/><path d="M34 226v5" stroke="{INK}" stroke-width="2.2" stroke-linecap="round"/>'
        + "".join(
            f'<circle cx="{x}" cy="231" r="4" fill="#9a917f" stroke="{INK}" stroke-width="1.8"/>'
            for x in (130, 146, 162)
        )
    )
    # LEDs light once plugged in
    g.append(
        f'<g class="{window(T_PLUG + 0.6, END)}">'
        + "".join(
            f'<circle class="{c}" cx="{x}" cy="231" r="4" fill="#3ddc84" stroke="{INK}" stroke-width="1.8"/>'
            for x, c in ((130, "led"), (146, "led2"), (162, "led"))
        )
        + "</g>"
    )
    # version screen
    g.append(
        f'<g class="{drop(T_SCREEN, -120)}"><rect x="18" y="58" width="164" height="72" rx="8" fill="{SCREEN}" stroke="{INK}" stroke-width="3.2"/>'
        f'<text x="30" y="80" font-size="10.5" class="mono" style="fill:#5f8f78">$ versions</text>'
        f'<g class="{window(T_SCREEN + 0.4, T_C70OFF, hidden=True)}"><text x="30" y="98" font-size="11.5" class="mono" style="fill:{PHOS}">kernel 7.0.14-pve</text><text x="30" y="116" font-size="11.5" class="mono" style="fill:#5f8f78">7.3 not installed</text></g>'
        f'<g class="{window(T_C73 + 0.6, END)}"><text x="30" y="98" font-size="11.5" class="mono" style="fill:{PHOS}">kernel 7.3.5-1-pve</text><text x="30" y="116" font-size="11.5" class="mono" style="fill:#5f8f78">7.0 kept as fallback</text></g>'
        f'<rect class="blink2" x="100" y="71" width="7" height="11" fill="{PHOS}"/></g>'
    )
    # nested node sled slides into the top bay
    g.append(
        f'<g class="{slide(T_SLED)}"><rect x="18" y="144" width="164" height="34" rx="6" fill="{ORANGE}" stroke="{INK}" stroke-width="3.2"/>'
        f'<rect x="26" y="151" width="22" height="20" rx="4" fill="{CREAM}" stroke="{INK}" stroke-width="2.2"/><path d="M31 157h12M31 162h12M31 167h8" stroke="{INK}" stroke-width="1.8"/>'
        f'<text x="56" y="166" font-size="12" font-weight="900" class="rnd" style="fill:{CREAM}">NESTED PVE</text>'
        f'<circle class="led2" cx="166" cy="161" r="4" fill="#3ddc84" stroke="{INK}" stroke-width="1.8"/><path d="M150 152v18" stroke="{ORANGE_D}" stroke-width="3" stroke-linecap="round"/></g>'
    )
    # wrench hangs on a hook on the side
    g.append(
        f'<path d="M226 92h16v10" stroke="{INK}" stroke-width="4" fill="none" stroke-linecap="round"/>'
    )
    g.append(
        f'<g class="{drop(T_WRENCH, -140)}"><g class="swing"><path d="M242 104L244 190" stroke="{INK}" stroke-width="13" stroke-linecap="round"/><path d="M242 104L244 190" stroke="{GREY}" stroke-width="7" stroke-linecap="round"/>'
        f'<circle cx="242" cy="102" r="9" fill="{GREY}" stroke="{INK}" stroke-width="3"/><circle cx="242" cy="102" r="3.5" fill="{CHASSIS_S}" stroke="{INK}" stroke-width="2"/>'
        f'<path d="M230 186Q228 206 244 210Q260 206 258 186L252 194H236Z" fill="{GREY}" stroke="{INK}" stroke-width="3" stroke-linejoin="round"/></g></g>'
    )
    return '<g transform="translate(596 150)"><g>' + "".join(g) + "</g></g>"


def pine(x, base, h, col):
    w = h * 0.42
    return (
        f'<path d="M{x} {base - h} L{x + w * 0.55} {base - h * 0.55} H{x + w * 0.3} L{x + w * 0.8} {base - h * 0.2} H{x + w * 0.4} L{x + w} {base} H{x - w} L{x - w * 0.4} {base - h * 0.2} H{x - w * 0.8} L{x - w * 0.3} {base - h * 0.55} H{x - w * 0.55} Z" fill="{col}"/>'
        f'<rect x="{x - 2}" y="{base}" width="4" height="6" fill="{col}"/>'
    )


def scene():
    s = []
    s.append('<rect width="960" height="500" fill="url(#sky)"/>')
    s.append('<circle cx="830" cy="300" r="62" fill="#ffc27a" opacity=".9"/>')
    for i, (x, y) in enumerate([(820, 70), (850, 88), (872, 62), (836, 108)]):
        s.append(
            f'<path class="bird b{i % 2}" d="M{x} {y}q6-6 12 0q6-6 12 0" stroke="#e9eef5" stroke-width="2.4" fill="none" stroke-linecap="round"/>'
        )
    s.append('<path d="M0 330Q160 270 330 312T660 300T960 282V460H0Z" fill="#6b7a99"/>')
    s.append(f'<path d="M0 372Q200 330 420 360T960 342V460H0Z" fill="{GREEN2}"/>')
    random.seed(7)
    for x in range(10, 960, 34):
        y = 372 - 22 * math.sin((x / 960) * math.pi * 1.2) + random.uniform(-4, 4)
        if random.random() < 0.45:
            s.append(
                f'<circle cx="{x + 12}" cy="{y + 2}" r="{random.uniform(6, 9):.1f}" fill="{random.choice(["#e06a2c", "#f2a93b", "#d9483a", "#f2c14e"])}"/>'
            )
        s.append(pine(x, y + 8, random.uniform(26, 44), "#1d3f2b"))
    s.append(f'<path d="M0 418Q240 386 520 410T960 404V460H0Z" fill="{GREEN}"/>')
    for x, h in [(30, 70), (70, 52), (930, 74), (520, 46)]:
        s.append(pine(x, 446, h, CREAM))
    s.append(f'<path d="M0 446Q120 438 240 446T480 446T720 446T960 446V500H0Z" fill="{CREAM}"/>')
    return "".join(s)


def stickers():
    items = [
        (0.4, "Same API underneath", "Proxmox VE API: unchanged", "body"),
        (1.3, "Version readout", "installed kernels + packages", "eyes"),
        (4.8, "Kernel 7.3 cartridge", "opt-in · 7.0 stays default", "beanie"),
        (6.7, "deploy_pve_vm", "builds a nested PVE node", "wrench"),
        (8.1, "Nested node sled", "a 2nd cluster for PDM tests", "mini"),
        (9.6, "Plugged in", "live-run the deploy tools", "boots"),
    ]
    out = []
    for i, (t, title, sub, icon) in enumerate(items):
        col, row = i % 2, i // 2
        x, y = 40 + col * 262, 210 + row * 64
        tilt = (-2.2, 1.6, 1.2, -1.8, -1.4, 2.0)[i]
        ix, iy = x + 26, y + 26
        icons = {
            "body": f'<rect x="{ix - 14}" y="{iy - 8}" width="28" height="16" rx="4" fill="{TAN}" stroke="{INK}" stroke-width="2.2"/><circle cx="{ix - 9}" cy="{iy}" r="1.6" fill="{INK}"/><circle cx="{ix + 9}" cy="{iy}" r="1.6" fill="{INK}"/><path d="M{ix - 4} {iy}h8" stroke="{INK}" stroke-width="2"/>',
            "eyes": f'<rect x="{ix - 14}" y="{iy - 10}" width="28" height="20" rx="4" fill="{SCREEN}" stroke="{INK}" stroke-width="2.2"/><path d="M{ix - 9} {iy - 3}h12M{ix - 9} {iy + 3}h8" stroke="{PHOS}" stroke-width="2" stroke-linecap="round"/>',
            "beanie": f'<rect x="{ix - 11}" y="{iy - 12}" width="22" height="24" rx="4" fill="{ORANGE}" stroke="{INK}" stroke-width="2.2"/><text x="{ix}" y="{iy + 4}" text-anchor="middle" font-size="9" font-weight="900" class="rnd" style="fill:{CREAM}">7.3</text>',
            "wrench": f'<path d="M{ix - 9} {iy + 11}L{ix + 5} {iy - 3}" stroke="{INK}" stroke-width="7" stroke-linecap="round"/><path d="M{ix - 9} {iy + 11}L{ix + 5} {iy - 3}" stroke="{GREY}" stroke-width="3.5" stroke-linecap="round"/><path d="M{ix + 1} {iy - 9}q4-8 12-5l-5 5 2 4 4 1 5-4q2 8-6 11z" fill="{GREY}" stroke="{INK}" stroke-width="2"/>',
            "mini": f'<rect x="{ix - 15}" y="{iy - 6}" width="30" height="12" rx="3" fill="{ORANGE}" stroke="{INK}" stroke-width="2.2"/><circle cx="{ix + 9}" cy="{iy}" r="2" fill="#3ddc84"/><path d="M{ix - 20} {iy}h-0" stroke="{INK}"/><path d="M{ix - 10} {iy}h10" stroke="{CREAM}" stroke-width="2"/>',
            "boots": f'<path d="M{ix - 12} {iy + 8}C{ix - 4} {iy + 8} {ix - 6} {iy - 4} {ix + 2} {iy - 4}" stroke="{INK}" stroke-width="3" fill="none"/><rect x="{ix + 1}" y="{iy - 10}" width="11" height="12" rx="2" fill="#3b3a37" stroke="{INK}" stroke-width="2"/><path d="M{ix + 12} {iy - 7}h4M{ix + 12} {iy - 1}h4" stroke="{INK}" stroke-width="2.2"/>',
        }[icon]
        mono = ' class="mono"' if title.startswith("deploy_") else ' class="rnd"'
        out.append(
            f'<g class="{stick(t)}"><g transform="rotate({tilt} {x + 125} {y + 26})">'
            f'<rect x="{x}" y="{y}" width="250" height="52" rx="13" fill="{CREAM}" stroke="{INK}" stroke-width="3"/>'
            f'<circle cx="{ix}" cy="{iy}" r="19" fill="{PAPER}" stroke="{INK}" stroke-width="2" stroke-dasharray="3 3"/>{icons}'
            f'<text x="{x + 52}" y="{y + 23}" font-size="14.5" font-weight="900"{mono} style="fill:{INK}">{title}</text>'
            f'<text x="{x + 52}" y="{y + 40}" font-size="11.5" style="fill:#5b5a55">{sub}</text>'
            f'<circle cx="{x + 242}" cy="{y + 6}" r="10" fill="#2f7a4b" stroke="{INK}" stroke-width="2.4"/>'
            f'<path d="M{x + 237} {y + 6}l3.5 3.5 6-7" stroke="#fff" stroke-width="2.6" fill="none" stroke-linecap="round" stroke-linejoin="round"/></g></g>'
        )
    return "".join(out)


def bubble():
    tips = [
        ("ZFS disks may show higher %util on 7.3.", "Real load, or new counting? Still checking."),
        ("7.3 is built from kernel.org, not Ubuntu,", "so a patch or two may be missing."),
        ("New boot-log lines (W^X, TDX) are expected.", "Same Proxmox VE API underneath."),
    ]
    spans = [(10.5, 12.6), (12.9, 14.6), (14.9, 16.8)]
    b = [
        f'<g class="{window(10.2, END)}"><g transform="rotate(1.5 762 74)"><rect x="596" y="30" width="332" height="88" rx="10" fill="{PAPER}" stroke="{INK}" stroke-width="3"/>'
        f'<rect x="732" y="20" width="62" height="20" fill="#f2c14e" opacity=".75" transform="rotate(-4 763 30)"/>'
        f'<text x="614" y="56" font-size="13" font-weight="900" class="rnd" style="fill:{ORANGE}">HEADS UP <tspan style="fill:#8a8780" font-weight="700">· could change</tspan></text>'
    ]
    for i, ((l1, l2), (a, z)) in enumerate(zip(tips, spans)):  # noqa: B905
        b.append(
            f'<g class="{window(a, z, hidden=(i > 0))}"><text x="614" y="80" font-size="13" style="fill:{INK}">{l1}</text><text x="614" y="99" font-size="13" style="fill:{INK}">{l2}</text></g>'
        )
    b.append("</g></g>")
    return "".join(b)


def marquee():
    phrases = [
        "IN DEVELOPMENT",
        "TRY ON KERNEL 7.3",
        "SAME API UNDERNEATH",
        "PARTS MAY SWAP",
        "NESTED NODE INCOMING",
        "ONE API, NEW PARTS",
    ]
    cw, gap, fs = 15.2, 74, 22
    xs, x = [], 0
    for ph in phrases:
        xs.append(x)
        x += len(ph) * cw + gap
    P = x
    out = [
        '<path d="M0 492'
        + "".join("q30 -6 60 0" for _ in range(17))
        + f'" stroke="{ORANGE}" stroke-width="2" stroke-dasharray="1 7" stroke-linecap="round" fill="none" opacity=".7"/>'
    ]
    rules.append(
        f"@keyframes mq {{ from {{ transform: translateX(0); }} to {{ transform: translateX(-{P:.0f}px); }} }} .mq {{ animation: mq 26s linear infinite; }}"
    )
    out.append('<g class="mq">')
    for rep in range(2):
        for i, (ph, x0) in enumerate(zip(phrases, xs)):  # noqa: B905
            X = 20 + x0 + rep * P
            rot = -2.5 if i % 2 == 0 else 2.0
            y = 480 if i % 2 == 0 else 476
            out.append(
                f'<text x="{X:.0f}" y="{y}" font-size="{fs}" font-weight="900" class="rnd" transform="rotate({rot} {X:.0f} {y})" style="fill:{GREEN}" letter-spacing=".02em">{ph}</text>'
            )
            out.append(
                f'<text x="{X + len(ph) * cw + gap / 2 - 9:.0f}" y="{y - 1}" font-size="20" style="fill:{ORANGE}">✦</text>'
            )
    out.append("</g>")
    return "".join(out)


body = [scene(), server(), bubble()]
# headline block
body.append(
    f'<g><rect x="40" y="24" width="176" height="30" rx="15" fill="{ORANGE}" stroke="{INK}" stroke-width="3"/><circle class="hum" cx="60" cy="39" r="5.5" fill="{CREAM}"/>'
    f'<text x="73" y="45" font-size="13" font-weight="900" class="rnd" letter-spacing=".08em" style="fill:{CREAM}">IN DEVELOPMENT</text></g>'
)
body.append(
    f'<text x="40" y="104" font-size="44" font-weight="800" class="serif" style="fill:{CREAM}">One API.</text>'
)
body.append(
    f'<text x="40" y="152" font-size="44" font-weight="800" class="serif" style="fill:{CREAM}"><tspan style="fill:#f0874a">New kernel</tspan> to try on.</text>'
)
body.append(
    '<text x="42" y="184" font-size="15" style="fill:#e9dcc7">Proxmox VE 9 has an opt-in Linux 7.3 kernel. We\'re fitting the parts now.</text>'
)
body.append(stickers())
mq = marquee()
body.append(mq)

extra = """
    text { font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif; }
    .rnd { font-family: "Arial Rounded MT Bold", ui-rounded, "SF Pro Rounded", "Nunito", system-ui, sans-serif; }
    .serif { font-family: "Recoleta", "Cooper Black", "Georgia", serif; }
    .mono { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
    .bob { animation: bob 2.8s ease-in-out infinite; } @keyframes bob { 50% { transform: translateY(-4px); } }
    .swing { animation: swing 2.2s ease-in-out infinite; transform-box: fill-box; transform-origin: 50% 0%; } @keyframes swing { 0%,100% { transform: rotate(-5deg); } 50% { transform: rotate(5deg); } }
    .blink2 { animation: led 1s steps(1) infinite; }
    .blink { animation: blink 4.2s infinite; transform-box: fill-box; transform-origin: 50% 50%; } @keyframes blink { 0%,92%,100% { transform: scaleY(1); } 95% { transform: scaleY(.1); } }
    .look { animation: look 6s ease-in-out infinite; } @keyframes look { 0%,30%,100% { transform: translate(0,0); } 40%,55% { transform: translate(-4px,-2px); } 65%,85% { transform: translate(3px,1px); } }
    .wave { animation: wave 1.6s ease-in-out infinite; transform-box: fill-box; transform-origin: 100% 100%; } @keyframes wave { 50% { transform: rotate(7deg); } }
    .led { animation: led 1.1s steps(1) infinite; } .led2 { animation: led 1.7s steps(1) infinite; } @keyframes led { 50% { opacity: .25; } }
    .hum { animation: hum 1.6s ease-in-out infinite; } @keyframes hum { 0%,100% { opacity: .35; } 50% { opacity: 1; } }
    .bird { animation: fly 7s ease-in-out infinite; } .b1 { animation-duration: 9s; } @keyframes fly { 50% { transform: translate(-14px,-6px); } }
"""
style = (
    "<style>"
    + extra
    + "\n    "
    + "\n    ".join(rules)
    + "\n    @media (prefers-reduced-motion: reduce) { * { animation: none !important; } }\n  </style>"
)
title = "In development: getting ready for Linux 7.3 on Proxmox VE 9"
desc = (
    "A Proxmox server drawn in a flat, sticker-style illustration stands on a wooded hill at sunset. Its chassis plate reads Proxmox VE API, the part that stays the same. "
    "Parts snap into its sockets one at a time, each a roadmap item: a version screen reading the installed kernel; a blue 7.0 kernel cartridge that is ejected "
    "and swapped for an orange 7.3 one, the opt-in kernel; a wrench on a side hook for deploy_pve_vm; a nested PVE sled that slides into a drive bay, a second cluster "
    "for Datacenter Manager tests; and a power cable that plugs in and lights the LEDs, for live runs of the deploy tools. Stickers on the left check off each part. "
    "A taped-on heads-up note cycles through what could change: ZFS disk utilization readings, the kernel.org-based build, and new boot-log lines. "
    "A wavy sticker marquee along the bottom reads In development, Try on kernel 7.3, Same API underneath, Parts may swap, Nested node incoming, One API, new parts."
)
svg = (
    f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 500" width="960" height="500" role="img" aria-labelledby="t d">\n'
    f'  <title id="t">{title}</title>\n  <desc id="d">{desc}</desc>\n'
    f'  <defs><linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1b3352"/><stop offset=".45" stop-color="#34557a"/><stop offset=".72" stop-color="#d88a5a"/><stop offset="1" stop-color="#f2b277"/></linearGradient>'
    f'<clipPath id="frame"><rect width="960" height="500" rx="20"/></clipPath></defs>\n  {style}\n'
    f'  <g clip-path="url(#frame)">' + "\n".join(body) + "</g>\n</svg>\n"
)
open(sys.argv[1], "w").write(svg)
