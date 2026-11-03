#!/usr/bin/env python3
"""
Board fit check: FPH HAT + Core STEP models placed in the enclosure exactly as assembled.

  python3 cad/fit_check.py --hat rev6.1hat3D.step --core rev5.1core3D.step

Placement
  HAT   top face against the head bosses (z = Z_HT), circle centre at (0, HAT_Y).
  Core  rotated 180 deg so its 4 holes line up with HAT holes (+-29,-24.5) and (+-29,-1.5)
        and its 2x20 header with the HAT's J3; bottom face BELOW_PCB_STACK under the HAT top.
  Screws  front M3 x HAT_SCREW_FRONT through Core + HAT, rear M3 x HAT_SCREW_REAR through HAT.
Reports interference of every board component with every printed part and the screws,
plus named clearances (I/O cutouts, mics/gaskets, switches/caps, LEDs/window, sensors, Core).
"""
import argparse
import math
import os
import sys

import cadquery as cq
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.TCollection import TCollection_ExtendedString
from OCP.TDataStd import TDataStd_Name
from OCP.TDF import TDF_Label, TDF_LabelSequence
from OCP.TDocStd import TDocStd_Document
from OCP.TopLoc import TopLoc_Location
from OCP.XCAFDoc import XCAFDoc_DocumentTool, XCAFDoc_ShapeTool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import enclosure as E  # noqa: E402

FAIL = []


def named_solids(path):
    """[(reference designator, cq.Shape)] from a KiCad STEP via XCAF."""
    doc = TDocStd_Document(TCollection_ExtendedString("doc"))
    r = STEPCAFControl_Reader(); r.SetNameMode(True); r.ReadFile(path); r.Transfer(doc)
    st = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())

    def name(l):
        a = TDataStd_Name()
        return a.Get().ToExtString() if l.FindAttribute(TDataStd_Name.GetID_s(), a) else "?"
    out = []

    def walk(lab, loc):
        comps = TDF_LabelSequence(); XCAFDoc_ShapeTool.GetComponents_s(lab, comps, False)
        for i in range(1, comps.Length() + 1):
            c = comps.Value(i); ref = TDF_Label(); XCAFDoc_ShapeTool.GetReferredShape_s(c, ref)
            l2 = loc * XCAFDoc_ShapeTool.GetLocation_s(c)
            sub = TDF_LabelSequence(); XCAFDoc_ShapeTool.GetComponents_s(ref, sub, False)
            if sub.Length():
                walk(ref, l2)
            else:
                s = cq.Shape.cast(XCAFDoc_ShapeTool.GetShape_s(ref).Moved(l2))
                if s.Solids():
                    out.append((name(c).split(":")[0], s))
    roots = TDF_LabelSequence(); st.GetFreeShapes(roots)
    for i in range(1, roots.Length() + 1):
        walk(roots.Value(i), TopLoc_Location())
    return out


def common(a, b):
    return cq.Shape.cast(BRepAlgoAPI_Common(a.wrapped, b.wrapped).Shape()).Volume()


def gap(a, b):
    d = BRepExtrema_DistShapeShape(a.wrapped, b.wrapped); d.Perform(); return d.Value()


def touch(a, b):
    ba, bb = a.BoundingBox(), b.BoundingBox()
    return not (ba.xmax < bb.xmin or ba.xmin > bb.xmax or ba.ymax < bb.ymin or ba.ymin > bb.ymax
                or ba.zmax < bb.zmin or ba.zmin > bb.zmax)


def check(cond, msg):
    print(("  OK   " if cond else "  FAIL ") + msg)
    if not cond:
        FAIL.append(msg)


def screw(x, y, z_head_bottom, length):
    head = E.cylinder(5.5, 2.4, x, y, z_head_bottom - 2.4).val()
    shank = E.cylinder(2.9, length, x, y, z_head_bottom).val()
    return head, shank


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hat", required=True)
    ap.add_argument("--core", required=True)
    a = ap.parse_args()

    hat = named_solids(a.hat)
    pcb = max(hat, key=lambda t: t[1].BoundingBox().xlen * t[1].BoundingBox().ylen)[1]
    zshift = E.Z_HT - pcb.BoundingBox().zmax           # seat PCB top face on the bosses
    hat = [(n, s.translate(cq.Vector(-150.0, 100.0 + E.HAT_Y, zshift))) for n, s in hat]
    hat_pcb = [s for n, s in hat if s.BoundingBox().xlen > 80][0]
    core = named_solids(a.core)
    core = [(n, s.rotate(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), 180)
             .translate(cq.Vector(32.5, E.HAT_Y - 24.5 + 26.5, E.Z_HT - E.BELOW_PCB_STACK))) for n, s in core]
    core_pcb = [s for n, s in core if 60 < s.BoundingBox().xlen < 70 and s.BoundingBox().zlen < 2][0]

    head = E.head().val()
    caps = [E.button_cap(*xy).val() for xy in E.BUTTONS]
    gaskets = [E.mic_gasket(*xy).val() for xy in E.MIC_PORTS]
    chamber, baffle = E.chamber().val(), E.baffle().val()
    isos = [E.isolator(sx * E.ISO_X, sy * E.ISO_Y).val() for sx in (-1, 1) for sy in (-1, 1)]
    zcb = core_pcb.BoundingBox().zmin
    screws = []
    for (x, y) in E.HAT_MOUNT_HOLES:
        X, Y = E.hat(x, y)
        if y < 0:
            screws.append((f"front M3x{E.HAT_SCREW_FRONT:.0f}", *screw(X, Y, zcb, E.HAT_SCREW_FRONT)))
        else:
            screws.append((f"rear M3x{E.HAT_SCREW_REAR:.0f}", *screw(X, Y, E.Z_HB + (E.HAT_T - pcb.BoundingBox().zlen), E.HAT_SCREW_REAR)))

    printed = [("head", head), ("chamber", chamber), ("baffle", baffle)] + \
        [(f"cap{i + 1}", c) for i, c in enumerate(caps)] + [(f"iso{i + 1}", s) for i, s in enumerate(isos)]

    print("== 1. interference: every HAT/Core component vs printed parts, gaskets and screws")
    hits = []
    for brd, parts in (("HAT", hat), ("Core", core)):
        for n, s in parts:
            for pn, p in printed + [(f"gasket{i + 1}", g) for i, g in enumerate(gaskets)]:
                if touch(s, p):
                    v = common(s, p)
                    if v > 1e-3:
                        hits.append(f"{brd} {n} x {pn}: {v:.3f} mm3")
            for sn, h, sh in screws:
                for part, pn in ((h, "head"), (sh, "shank")):
                    if touch(s, part):
                        v = common(s, part)
                        if v > 1e-3:
                            hits.append(f"{brd} {n} x {sn} {pn}: {v:.3f} mm3")
    for h in hits:
        print("   ", h)
    check(not hits, f"no board/printed-part/screw interference ({len(hat)} HAT + {len(core)} Core solids)")
    for sn, h, sh in screws:
        check(all(common(h, p) < 1e-3 for _, p in printed), f"{sn} head clear of all printed parts")
    for sn, h, sh in screws:
        tip = sh.BoundingBox().zmax
        check(E.Z_HT + 4.0 <= tip <= E.Z_HT + E.HAT_PILOT_DEPTH - 0.5,
              f"{sn} tip {tip - E.Z_HT:.1f} mm into boss (pilot {E.HAT_PILOT_DEPTH})")

    byname = {}
    for n, s in hat:
        byname.setdefault(n, []).append(s)
    bb = lambda n: byname[n][0].BoundingBox()

    print("== 2. board edge and rear I/O")
    wall_in_y = E.D / 2 - E.HEAD_WALL
    # walls only: slice of the head below the boss faces (the PCB top is meant to touch the bosses)
    slab = cq.Workplane("XY").box(400, 400, hat_pcb.BoundingBox().zlen - 0.1, centered=(True, True, False)) \
        .translate((0, 0, hat_pcb.BoundingBox().zmin + 0.05)).val()
    side_gap = gap(hat_pcb, head.intersect(slab))
    check(side_gap >= 0.2, f"HAT PCB edge to head walls/posts min gap {side_gap:.2f} mm")
    jack = [s for n, s in hat if s.BoundingBox().ymax > wall_in_y - 0.1 and s.BoundingBox().zmin < E.Z_HB]
    for j in jack:
        jb = j.BoundingBox()
        check(common(j, head) < 1e-3, f"3.5 mm jack (protrudes {jb.ymax - wall_in_y:.2f} mm into wall) clear of cutout, gap {gap(j, head):.2f} mm")
    for ref, (xr, zr) in zip(("J5", "J2"), E.USB_C):
        b = bb(ref)
        dx = (b.xmin + b.xmax) / 2 - xr
        dz = (b.zmin + b.zmax) / 2 - (E.Z_HB + zr)
        check(abs(dx) < 0.3 and abs(dz) < 0.3 and b.xlen < E.USB_CUT_W - 2 and b.zlen < E.USB_CUT_H - 2,
              f"USB-C {ref} centred on cutout (dx {dx:+.2f}, dz {dz:+.2f}); receptacle {b.xlen:.1f}x{b.zlen:.1f} in {E.USB_CUT_W}x{E.USB_CUT_H}")

    print("== 3. mics")
    for i, ref in enumerate(("MK1", "MK2", "MK3", "MK4")):
        b = bb(ref); X, Y = E.hat(*E.MIC_PORTS[i]); r = E.MIC_GASKET_OD / 2
        inside = b.xmin <= X - r and X + r <= b.xmax and b.ymin <= Y - r and Y + r <= b.ymax
        zgap = (E.Z_HT + E.MIC_TOP_ABOVE_PCB) - b.zmax
        check(inside and abs(zgap) < 0.05,
              f"{ref}: gasket OD{E.MIC_GASKET_OD} lands on the mic body (margins x {X - r - b.xmin:.2f}/{b.xmax - X - r:.2f}, "
              f"y {Y - r - b.ymin:.2f}/{b.ymax - Y - r:.2f}); seat height error {zgap:+.2f} mm")

    print("== 4. buttons")
    for i, ref in enumerate(("SW1", "SW2", "SW3", "SW4")):
        b = bb(ref); X, Y = E.hat(*E.BUTTONS[i]); cb = caps[i].BoundingBox()
        off = math.hypot((b.xmin + b.xmax) / 2 - X, (b.ymin + b.ymax) / 2 - Y)
        check(off < 0.3 and 0.05 <= cb.zmin - b.zmax <= 0.4,
              f"{ref}: cap centred ({off:.2f} mm), stem-to-switch pre-travel gap {cb.zmin - b.zmax:.2f} mm")

    print("== 5. LEDs under the light window")
    cx, cy = E.hat(0, 0)
    leds = [s for n, s in hat if 1.2 < s.BoundingBox().xlen < 1.9 and 1.2 < s.BoundingBox().ylen < 1.9
            and 38 < math.hypot(s.BoundingBox().center.x - cx, s.BoundingBox().center.y - cy) < 44
            and s.BoundingBox().zmin > E.Z_HT - 0.2]
    bad = 0
    for s in leds:
        c = s.BoundingBox().center
        rr = math.hypot(c.x - cx, c.y - cy); ang = math.degrees(math.atan2(c.y - cy, c.x - cx)) % 360
        under_bridge = any(abs(((ang - a + 180) % 360) - 180) * math.pi / 180 * rr < E.LED_BRIDGE_W / 2 + 0.65
                           for a in E.LED_BRIDGE_ANGLES)
        if not (E.LED_SLOT_RI <= rr <= E.LED_SLOT_RO) or under_bridge:
            bad += 1
    check(len(leds) == 24 and bad == 0, f"{len(leds)} LEDs found, {bad} outside the slot or under a bridge")

    print("== 6. sensors")
    for ref, (x, y) in zip(("U4", "U12"), E.SENSOR_HOLES):
        b = bb(ref); X, Y = E.hat(x, y)
        off = math.hypot((b.xmin + b.xmax) / 2 - X, (b.ymin + b.ymax) / 2 - Y)
        check(off < 1.0, f"{ref} under its {E.SENSOR_HOLE_D} mm hole (offset {off:.2f} mm)")

    print("== 7. Core")
    hdr = [s for n, s in core if n == "J1"][0].BoundingBox()
    j3 = bb("J3")
    check(abs(hdr.center.x - j3.center.x) < 0.1 and abs(hdr.center.y - j3.center.y) < 0.1,
          f"Core header J1 over HAT J3 (dx {hdr.center.x - j3.center.x:+.2f}, dy {hdr.center.y - j3.center.y:+.2f})")
    core_all = cq.Compound.makeCompound([s for _, s in core])
    check(gap(core_all, chamber) > 2.0, f"Core to chamber roof {gap(core_all, chamber):.1f} mm")
    check(gap(core_all, head) > 1.0, f"Core to head walls/posts {gap(core_all, head):.1f} mm")
    sh_min = min(gap(h, chamber) for _, h, _ in screws)
    check(sh_min > 1.0, f"screw heads to chamber roof {sh_min:.1f} mm")
    print("\nRESULT:", "PASS" if not FAIL else f"{len(FAIL)} FAIL")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
