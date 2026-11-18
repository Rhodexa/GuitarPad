#!/usr/bin/env python3
"""Draw docs/wiring.svg from the pins in src/config.h.

Usage:  python3 tools/wiring_diagram.py

Takes the Raspberry Pi Pico pinout (pico-pinout.svg), hides the UART/I2C/SPI
label columns we don't use, and draws the switches, the whammy pot and their
wires on top. Rerun it whenever you change pins in config.h.
"""
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "src" / "config.h"
PINOUT = ROOT / "pico-pinout.svg"
OUT = ROOT / "docs" / "wiring.svg"

SVG_NS = "http://www.w3.org/2000/svg"
NS = "{%s}" % SVG_NS
ET.register_namespace("", SVG_NS)
ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")

# Physical pin number for each GPIO on a Raspberry Pi Pico.
GPIO_TO_PIN = {
    0: 1, 1: 2, 2: 4, 3: 5, 4: 6, 5: 7, 6: 9, 7: 10, 8: 11, 9: 12,
    10: 14, 11: 15, 12: 16, 13: 17, 14: 19, 15: 20, 16: 21, 17: 22,
    18: 24, 19: 25, 20: 26, 21: 27, 22: 29, 26: 31, 27: 32, 28: 34,
}
LEFT_GND_PINS = [3, 8, 13, 18]
RIGHT_GND_PINS = [23, 28, 38]
PIN_3V3 = 36

# Label colours in the pinout to hide: SPI, I2C and UART (incl. "default" shades).
HIDDEN_LABEL_CLASSES = {"st31", "st32", "st33", "st34", "st35", "st39"}
CONNECTOR_CLASS = "st8"   # thin grey lines joining labels
ADC_CLASS = "st38"

WIRE_COLOURS = {
    "green": "#22a045", "red": "#e03b3b", "yellow": "#e8c000",
    "blue": "#2f7fd8", "orange": "#ee8a1c",
}
OTHER_COLOURS = ["#7b4fc4", "#13998a", "#6b7785", "#c0478f", "#8a6d3b", "#2c3e50"]
GND_COLOUR = "#30343b"
POWER_COLOUR = "#e03b3b"
FONT = "Roboto, 'Helvetica Neue', Arial, sans-serif"


# ---------------------------------------------------------------------------
#  Read config.h
# ---------------------------------------------------------------------------
def read_config():
    text = CONFIG.read_text()
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"//[^\n]*", "", text)

    m = re.search(r"#define\s+GUITAR_BUTTONS((?:[^\n]*\\\n)*[^\n]*)", text)
    if not m:
        sys.exit("Couldn't find GUITAR_BUTTONS in config.h")
    buttons = [(name, int(pin)) for name, pin in
               re.findall(r'\{\s*"([^"]+)"\s*,\s*(\d+)\s*\}', m.group(1))]

    def define(name):
        d = re.search(r"#define\s+%s\s+(-?\d+)" % name, text)
        return int(d.group(1)) if d else -1

    for name, gpio in buttons:
        if gpio not in GPIO_TO_PIN:
            sys.exit(f"'{name}' uses GPIO {gpio}, which isn't on the Pico's header")
    return buttons, define("WHAMMY_PIN"), define("TILT_AXIS_PIN")


# ---------------------------------------------------------------------------
#  Pinout geometry + cleanup
# ---------------------------------------------------------------------------
def first_point(elem):
    for e in elem.iter():
        if e.tag == NS + "rect":
            return float(e.get("x")), float(e.get("y"))
        if e.tag == NS + "path":
            m = re.match(r"\s*[Mm]\s*([-\d.]+)[\s,]*([-\d.]+)", e.get("d", ""))
            if m:
                return float(m.group(1)), float(m.group(2))
        if e.tag == NS + "polygon":
            n = re.findall(r"-?[\d.]+", e.get("points", ""))
            if len(n) >= 2:
                return float(n[0]), float(n[1])
    return None


class Pinout:
    def __init__(self, root):
        self.root = root
        self.labels = next(e for e in root.iter() if e.get("id", "").startswith("Pinout_0"))

        rects = []
        for group in self.labels:
            for r in group.iter(NS + "rect"):
                x, y, w, h = (float(r.get(k)) for k in ("x", "y", "width", "height"))
                rects.append(dict(group=group, x=x, y=y, w=w, h=h, cls=r.get("class")))
        self.rects = rects

        # Pin-number boxes (grey, "st11") give the row centres.
        nums = [r for r in rects if r["cls"] == "st11"]
        left = sorted((r for r in nums if r["x"] < 300), key=lambda r: r["y"])
        right = sorted((r for r in nums if r["x"] > 300), key=lambda r: r["y"])
        self.left_rows = [r["y"] + r["h"] / 2 for r in left]     # pins 1..20
        self.right_rows = [r["y"] + r["h"] / 2 for r in right]   # pins 40..21

    def pin_y(self, pin):
        return self.left_rows[pin - 1] if pin <= 20 else self.right_rows[40 - pin]

    def row_of(self, y, side_rows):
        return min(range(len(side_rows)), key=lambda i: abs(side_rows[i] - y))

    def hide_unused_labels(self):
        hidden = [r for r in self.rects if r["cls"] in HIDDEN_LABEL_CLASSES]
        adc_rows = {self.row_of(r["y"] + r["h"] / 2, self.right_rows)
                    for r in self.rects if r["cls"] == ADC_CLASS}

        def connector_hidden(r):
            if r["cls"] != CONNECTOR_CLASS:
                return False
            if r["x"] < 177:                       # left of the GP column
                return True
            if r["x"] > 550:                       # right of the ADC column
                return True
            if 490 < r["x"] < 500:                 # GP -> ADC/SPI/I2C link
                return self.row_of(r["y"] + r["h"] / 2, self.right_rows) not in adc_rows
            return False

        drop = {id(r["group"]) for r in hidden if True} | \
               {id(r["group"]) for r in self.rects if connector_hidden(r)}

        # The text of each label is its own group, sitting inside the label's box.
        for group in list(self.labels):
            if id(group) in drop:
                continue
            p = first_point(group)
            if p and any(r["x"] - 1 <= p[0] <= r["x"] + r["w"] + 1 and
                         r["y"] - 1 <= p[1] <= r["y"] + r["h"] + 1 for r in hidden):
                drop.add(id(group))

        for group in list(self.labels):
            if id(group) in drop:
                self.labels.remove(group)
        self.rects = [r for r in self.rects if id(r["group"]) not in drop]

        # The colour key (top right) mostly explains the labels we just hid.
        # Its shapes are unnamed siblings of the board and the labels.
        wrapper = next(p for p in self.root.iter() if self.labels in list(p))
        for child in list(wrapper):
            if child is self.labels or child.get("id"):
                continue
            if any(child.get("id", "").startswith("Picoboard") for child in child.iter()):
                continue
            p = first_point(child)
            if p and p[0] > 660:
                wrapper.remove(child)

    def left_edge(self):
        return min(r["x"] for r in self.rects if r["cls"] not in ("st8", "st11") and r["x"] < 300)

    def right_edge(self, pin):
        """x where the last visible label of a right-side pin's row ends."""
        y = self.pin_y(pin)
        row = [r for r in self.rects if r["x"] > 430 and r["cls"] not in ("st8", "st11")
               and abs(r["y"] + r["h"] / 2 - y) < 3]
        return max(r["x"] + r["w"] for r in row)


# ---------------------------------------------------------------------------
#  Drawing helpers
# ---------------------------------------------------------------------------
class Drawing:
    def __init__(self):
        self.g = ET.Element(NS + "g", id="Guitar_Wiring")

    def add(self, tag, **attrs):
        return ET.SubElement(self.g, NS + tag, {k.replace("_", "-"): str(v) for k, v in attrs.items()})

    def wire(self, points, colour, width=2.2):
        self.add("polyline", points=" ".join(f"{x:.1f},{y:.1f}" for x, y in points),
                 fill="none", stroke=colour, stroke_width=width,
                 stroke_linejoin="round", stroke_linecap="round")

    def dot(self, x, y, colour, r=2.4):
        self.add("circle", cx=f"{x:.1f}", cy=f"{y:.1f}", r=r, fill=colour)

    def text(self, x, y, s, size=8.5, anchor="start", weight="normal", colour="#30343b"):
        t = self.add("text", x=f"{x:.1f}", y=f"{y:.1f}", font_family=FONT, font_size=size,
                     font_weight=weight, text_anchor=anchor, fill=colour)
        t.text = s

    def switch(self, cx, y, tilt=False):
        """Normally-open push button (or a tilt switch) with its terminals at cx±9."""
        ink = "#30343b"
        for x in (cx - 9, cx + 9):
            self.add("circle", cx=f"{x:.1f}", cy=f"{y:.1f}", r=1.8, fill="#fff",
                     stroke=ink, stroke_width=1.1)
        if tilt:
            self.add("line", x1=f"{cx - 7.5:.1f}", y1=f"{y - 0.8:.1f}", x2=f"{cx + 9:.1f}", y2=f"{y - 7:.1f}",
                     stroke=ink, stroke_width=1.3, stroke_linecap="round")
            self.add("circle", cx=f"{cx + 1:.1f}", cy=f"{y - 7.8:.1f}", r=1.7, fill=ink)
        else:
            self.add("line", x1=f"{cx - 11:.1f}", y1=f"{y - 4.5:.1f}", x2=f"{cx + 11:.1f}", y2=f"{y - 4.5:.1f}",
                     stroke=ink, stroke_width=1.3, stroke_linecap="round")
            self.add("line", x1=f"{cx:.1f}", y1=f"{y - 4.5:.1f}", x2=f"{cx:.1f}", y2=f"{y - 8.5:.1f}",
                     stroke=ink, stroke_width=1.3)
            self.add("line", x1=f"{cx - 3:.1f}", y1=f"{y - 8.5:.1f}", x2=f"{cx + 3:.1f}", y2=f"{y - 8.5:.1f}",
                     stroke=ink, stroke_width=1.3, stroke_linecap="round")

    def resistor_vertical(self, x, y0, y1, colour="#30343b"):
        n, amp = 6, 5
        step = (y1 - y0) / (n * 2)
        pts = [(x, y0)]
        for i in range(n * 2):
            pts.append((x + (amp if i % 2 == 0 else -amp), y0 + step * (i + 0.5)))
        pts.append((x, y1))
        self.wire(pts, colour, width=1.5)


def pretty(name):
    return name.replace("_", " ").title()


# ---------------------------------------------------------------------------
#  Main
# ---------------------------------------------------------------------------
def main():
    buttons, whammy_gpio, tilt_axis_gpio = read_config()

    tree = ET.parse(PINOUT)
    root = tree.getroot()
    pinout = Pinout(root)
    pinout.hide_unused_labels()

    d = Drawing()
    others = iter(OTHER_COLOURS * 4)
    colour_of = {name: WIRE_COLOURS.get(name.lower()) or next(others) for name, _ in buttons}

    # Title
    d.text(16, 34, "Guitar controller wiring", size=17, weight="bold")
    d.text(16, 50, "Every switch: one leg to its GPIO, the other leg to GND.", size=8.5)
    d.text(16, 61, "No resistors needed (the internal pull-ups are used).", size=8.5)
    d.text(16, 76, "Generated from src/config.h by tools/wiring_diagram.py", size=7, colour="#8a8f98")

    # --- Switches on the left side of the board --------------------------------
    left = [(n, g) for n, g in buttons if GPIO_TO_PIN[g] <= 20]
    right = [(n, g) for n, g in buttons if GPIO_TO_PIN[g] > 20]

    if left:
        x_label = pinout.left_edge()          # where the GPx labels start
        rail_x, sw_x = 26, x_label - 42
        ys = [pinout.pin_y(GPIO_TO_PIN[g]) for _, g in left]
        gnd_pin = min(LEFT_GND_PINS, key=lambda p: abs(pinout.pin_y(p) - min(ys)))
        gnd_y = pinout.pin_y(gnd_pin)
        top, bottom = min(ys + [gnd_y]), max(ys + [gnd_y])

        d.wire([(rail_x, top), (rail_x, bottom)], GND_COLOUR, width=2.6)
        d.wire([(rail_x, gnd_y), (x_label, gnd_y)], GND_COLOUR, width=2.6)
        d.dot(rail_x, gnd_y, GND_COLOUR)
        d.text(rail_x + 6, gnd_y - 3.5, "GND", size=7.5, weight="bold", colour=GND_COLOUR)

        for name, gpio in left:
            y = pinout.pin_y(GPIO_TO_PIN[gpio])
            c = colour_of[name]
            d.wire([(x_label, y), (sw_x + 9, y)], c)
            d.wire([(sw_x - 9, y), (rail_x, y)], c)
            d.dot(rail_x, y, GND_COLOUR)
            d.switch(sw_x, y, tilt="tilt" in name.lower())
            d.text(rail_x + 6, y - 3.5, pretty(name), size=8, weight="bold", colour=c)

    # --- Switches on the right side (none by default) -------------------------
    if right:
        rail_x = 650
        ys = [pinout.pin_y(GPIO_TO_PIN[g]) for _, g in right]
        gnd_pin = min(RIGHT_GND_PINS, key=lambda p: abs(pinout.pin_y(p) - min(ys)))
        gnd_y = pinout.pin_y(gnd_pin)
        d.wire([(rail_x, min(ys + [gnd_y])), (rail_x, max(ys + [gnd_y]))], GND_COLOUR, width=2.6)
        d.wire([(pinout.right_edge(gnd_pin), gnd_y), (rail_x, gnd_y)], GND_COLOUR, width=2.6)
        d.dot(rail_x, gnd_y, GND_COLOUR)
        for name, gpio in right:
            pin = GPIO_TO_PIN[gpio]
            y, x0 = pinout.pin_y(pin), pinout.right_edge(pin)
            sw_x = rail_x - 62
            c = colour_of[name]
            d.wire([(x0, y), (sw_x - 9, y)], c)
            d.wire([(sw_x + 9, y), (rail_x, y)], c)
            d.dot(rail_x, y, GND_COLOUR)
            d.switch(sw_x, y, tilt="tilt" in name.lower())
            d.text(x0 + 8, y - 3.5, pretty(name), size=8, weight="bold", colour=c)

    # --- Whammy potentiometer --------------------------------------------------
    if whammy_gpio >= 0:
        if whammy_gpio not in (26, 27, 28):
            sys.exit(f"WHAMMY_PIN {whammy_gpio} isn't an analog pin (use 26, 27 or 28)")
        pot_x = 735
        y_3v3 = pinout.pin_y(PIN_3V3)
        gnd_pin = 28
        y_gnd = pinout.pin_y(gnd_pin)
        wiper_pin = GPIO_TO_PIN[whammy_gpio]
        y_wiper = pinout.pin_y(wiper_pin)

        d.wire([(pinout.right_edge(PIN_3V3), y_3v3), (pot_x, y_3v3), (pot_x, y_3v3 + 22)], POWER_COLOUR)
        d.resistor_vertical(pot_x, y_3v3 + 22, y_gnd - 18)
        d.wire([(pot_x, y_gnd - 18), (pot_x, y_gnd), (pinout.right_edge(gnd_pin), y_gnd)], GND_COLOUR)

        wire_end = pot_x - 9
        d.wire([(pinout.right_edge(wiper_pin), y_wiper), (wire_end - 4, y_wiper)], "#22a045")
        d.add("polygon", fill="#30343b",
              points=f"{wire_end:.1f},{y_wiper:.1f} {wire_end - 7:.1f},{y_wiper - 3.5:.1f} "
                     f"{wire_end - 7:.1f},{y_wiper + 3.5:.1f}")

        lx = pot_x + 14
        d.text(lx, y_3v3 + 40, "Whammy", size=11, weight="bold")
        d.text(lx, y_3v3 + 52, "potentiometer", size=8.5)
        d.text(lx, y_3v3 + 63, "(10k linear)", size=8.5, colour="#6b7785")
        d.text(pot_x + 6, y_3v3 - 4, "outer leg → 3V3(OUT)", size=7.5, colour=POWER_COLOUR)
        d.text(wire_end - 10, y_wiper - 4, "middle leg", size=7.5, anchor="end")
        d.text(pot_x + 6, y_gnd + 11, "outer leg → GND", size=7.5, colour=GND_COLOUR)
        d.text(pot_x - 120, y_gnd + 38, "Use 3V3(OUT), never VBUS/VSYS (5V):", size=8, weight="bold",
               colour=POWER_COLOUR)
        d.text(pot_x - 120, y_gnd + 49, "the analog pins can't take more than 3.3V.", size=8,
               colour=POWER_COLOUR)

    if tilt_axis_gpio >= 0:
        y = pinout.pin_y(GPIO_TO_PIN[tilt_axis_gpio])
        x0 = pinout.right_edge(GPIO_TO_PIN[tilt_axis_gpio])
        d.wire([(x0, y), (600, y)], "#7b4fc4")
        d.add("rect", x=600, y=f"{y - 8:.1f}", width=60, height=16, rx=3,
              fill="#fff", stroke="#7b4fc4", stroke_width=1.3)
        d.text(630, y + 3, "Tilt sensor OUT", size=6.5, anchor="middle")

    # White background so it's readable in dark-mode viewers too.
    vb = root.get("viewBox").split()
    bg = ET.Element(NS + "rect", x=vb[0], y=vb[1], width=vb[2], height=vb[3], fill="#ffffff")
    style_idx = next(i for i, e in enumerate(root) if e.tag == NS + "style")
    root.insert(style_idx + 1, bg)
    root.append(d.g)

    OUT.parent.mkdir(exist_ok=True)
    tree.write(OUT, encoding="utf-8", xml_declaration=True)
    print(f"Wrote {OUT.relative_to(ROOT)}: {len(buttons)} switches"
          + (f", whammy on GP{whammy_gpio}" if whammy_gpio >= 0 else ""))


if __name__ == "__main__":
    main()
