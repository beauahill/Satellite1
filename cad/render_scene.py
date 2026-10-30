#!/usr/bin/env python3
"""
Export the full assembled scene (enclosure + representative RS100-4 + FPH HAT/Core boards +
damping) as STL meshes with a manifest for cad/render/render.html.

    python3 cad/render_scene.py --hat path/to/rev6.1hat3D.step --core path/to/rev5.1core3D.step
    node cad/render/render.mjs          # writes cad/out/render_*.png

The driver model is representative (Dayton publishes outline dims only: OD 98, cutout 77.2,
depth 51); the boards are FPH's own STEP models. Core orientation under the HAT is illustrative.
"""
import argparse
import json
import os
import sys

import cadquery as cq

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import enclosure as E  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out", "scene")


def rs100_model():
    """Simplified RS100-4, built along +z (front at z=0), then placed on the baffle."""
    flange_t = 4.0
    flange = (cq.Workplane("XY").circle(E.DRIVER_OD / 2).circle(E.DRIVER_CUTOUT_D / 2 - 1)
              .extrude(flange_t).translate((0, 0, -flange_t)))
    for k in range(E.DRIVER_HOLES):
        import math
        a = math.radians(E.DRIVER_HOLE_ANGLE0 + 360 * k / E.DRIVER_HOLES)
        x, y = E.DRIVER_BCD / 2 * math.cos(a), E.DRIVER_BCD / 2 * math.sin(a)
        flange = flange.union(cq.Workplane("XY").circle(2.8).extrude(1.6).translate((x, y, 0)))
    # surround (half torus) + cone + phase plug, as a revolved profile
    surround = (cq.Workplane("XZ").center(33.5, -2.0).circle(4.0).revolve(360, (-33.5, 0, 0), (-33.5, 1, 0))
                .intersect(cq.Workplane("XY").circle(40).extrude(-6.0).translate((0, 0, 2))))
    cone = (cq.Workplane("XY").workplane(offset=-18.5).circle(15.0)
            .workplane(offset=16.0).circle(30.0).loft())
    plug = cq.Workplane("XY").sphere(13.0).intersect(
        cq.Workplane("XY").circle(14).extrude(10).translate((0, 0, -12))).translate((0, 0, -5))
    def frustum(r_front, r_back, z_front, length):
        return (cq.Workplane("XY").workplane(offset=z_front - length).circle(r_back)
                .workplane(offset=length).circle(r_front).loft())
    basket = frustum(E.DRIVER_CUTOUT_D / 2 - 1.5, 26.0, -flange_t, 22).cut(
        frustum(E.DRIVER_CUTOUT_D / 2 - 3.0, 24.5, -flange_t + 0.5, 23))
    magnet = cq.Workplane("XY").circle(31.0).extrude(-(E.DRIVER_DEPTH - 26 - flange_t)) \
        .translate((0, 0, -26 - flange_t))
    plate = cq.Workplane("XY").circle(33.0).extrude(-2.5).translate((0, 0, -26 - flange_t))
    parts = dict(drv_frame=flange.union(basket).union(plate), drv_cone=cone, drv_surround=surround,
                 drv_plug=plug, drv_magnet=magnet)
    placed = {}
    for k, wp in parts.items():
        s = wp.val().rotate(cq.Vector(0, 0, 0), cq.Vector(1, 0, 0), 90)       # +z -> -y
        s = s.translate(cq.Vector(0, -E.D / 2 - 1.0, E.Z_DRV))                 # on the gasket
        placed[k] = cq.Workplane().add(s)
    return placed


def board_parts(hat_step, core_step):
    out = {}
    if hat_step:
        shp = cq.importers.importStep(hat_step).val().translate(cq.Vector(-150.0, 100.0 + E.HAT_Y, E.Z_HB))
        pcb, comps = [], []
        for s in shp.Solids():
            bb = s.BoundingBox()
            (pcb if (bb.xlen > 80 and bb.ylen > 80 and bb.zlen < 2) else comps).append(s)
        out["hat_pcb"] = cq.Workplane().add(cq.Compound.makeCompound(pcb))
        out["hat_parts"] = cq.Workplane().add(cq.Compound.makeCompound(comps))
    if core_step:
        shp = cq.importers.importStep(core_step).val()
        # rev5.1 frame: PCB 0..65 x 0..30.5, 2x20 header centred (32.5, 26.5) on top.
        # Header pins rise into the HAT's J3 at HAT (0, -24.5); body kept under the board.
        shp = shp.rotate(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), 180)
        shp = shp.translate(cq.Vector(32.5, E.HAT_Y - 24.5 + 26.5, E.Z_HB - 8.6))
        pcb, comps = [], []
        for s in shp.Solids():
            bb = s.BoundingBox()
            (pcb if (bb.xlen > 60 and bb.ylen > 28 and bb.zlen < 2) else comps).append(s)
        out["core_pcb"] = cq.Workplane().add(cq.Compound.makeCompound(pcb))
        out["core_parts"] = cq.Workplane().add(cq.Compound.makeCompound(comps))
    return out


def damping_parts():
    foam_t, butyl_t = 12.7, 2.0
    z0 = E.WALL_BOT + 20
    h = E.H_CAV - 30
    foam = (cq.Workplane("XY").box(E.CAV_W - 4, foam_t, h, centered=(True, False, False))
            .translate((0, E.CAV_Y1 - foam_t, z0)))
    butyl = []
    for sx in (-1, 1):
        b = (cq.Workplane("XY").box(butyl_t, 70, 150, centered=(False, True, False))
             .translate((sx * (E.CAV_W / 2) - (butyl_t if sx > 0 else 0), (E.CAV_Y0 + E.CAV_Y1) / 2 + 5, z0 + 20)))
        butyl.append(b)
    bumpers = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            bumpers.append(E.cylinder(E.BUMPER_D, 3.6, sx * (E.W / 2 - E.BUMPER_INSET),
                                      sy * (E.D / 2 - E.BUMPER_INSET), E.BUMPER_RECESS - 3.6))
    u = lambda lst: lst[0].union(lst[1]) if len(lst) == 2 else lst[0].union(lst[1]).union(lst[2]).union(lst[3])
    return dict(foam=foam, butyl=u(butyl), bumpers=u(bumpers))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hat")
    ap.add_argument("--core")
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)

    caps = E.button_cap(*E.BUTTONS[0])
    for xy in E.BUTTONS[1:]:
        caps = caps.union(E.button_cap(*xy))
    isos = E.isolator(-E.ISO_X, -E.ISO_Y)
    for sx, sy in [(1, -1), (-1, 1), (1, 1)]:
        isos = isos.union(E.isolator(sx * E.ISO_X, sy * E.ISO_Y))
    gaskets = E.mic_gasket(*E.MIC_PORTS[0])
    for xy in E.MIC_PORTS[1:]:
        gaskets = gaskets.union(E.mic_gasket(*xy))

    # name: (workplane, colour, explode offset [x,y,z] mm, callout no., label)
    ex_top = 150
    scene = {
        "chamber": (E.chamber(), "#3b3f46", [0, 0, 0], 1, "Chamber (PETG)"),
        "baffle": (E.baffle(), "#33363c", [0, -120, 0], 4, "Front baffle (glued)"),
        "driver_gasket": (E.driver_gasket(), "#111111", [0, -150, 0], 5, "Driver gasket (TPU)"),
        "foam": (damping_parts()["foam"], "#6b6f7a", [0, 150, 0], 2, "1/2\" foam, back wall"),
        "butyl": (damping_parts()["butyl"], "#d9dde2", [230, 0, 0], 3, "Butyl sheet, side walls"),
        "bumpers": (damping_parts()["bumpers"], "#d8dde3", [0, 0, -40], 6, "Bumpon SJ5312 feet x4"),
        "isolators": (isos, "#e07b39", [0, 0, 45], 7, "TPU isolators x4"),
        "head": (E.head(), "#e8e6e1", [0, 0, ex_top + 40], 12, "Head (top cap)"),
        "diffuser": (E.diffuser(), "#bfe8ff", [0, 0, ex_top + 85], 13, "LED diffuser"),
        "button_caps": (caps, "#cfccc4", [0, 0, ex_top + 70], 14, "Button caps x4"),
        "mic_gaskets": (gaskets, "#d23c3c", [0, 0, ex_top + 15], 11, "Mic gaskets x4"),
    }
    for k, wp in rs100_model().items():
        col = {"drv_frame": "#1c1d20", "drv_cone": "#5a5f66", "drv_surround": "#141414",
               "drv_plug": "#9aa1aa", "drv_magnet": "#2a2b2e"}[k]
        scene[k] = (wp, col, [0, -190, 0], 8 if k == "drv_cone" else 0, "Dayton RS100-4")
    for k, wp in board_parts(a.hat, a.core).items():
        col = {"hat_pcb": "#1d3b2a", "hat_parts": "#8a8f96", "core_pcb": "#1d2f3b", "core_parts": "#7a7f86"}[k]
        lab = {"hat_pcb": (10, "Satellite1 HAT"), "core_pcb": (9, "Satellite1 Core")}.get(k, (0, ""))
        scene[k] = (wp, col, [0, 0, ex_top - 30 + (0 if k.startswith("hat") else -25)], lab[0], lab[1])

    manifest = []
    for name, (wp, col, off, num, label) in scene.items():
        f = f"{name}.stl"
        cq.exporters.export(wp, os.path.join(OUT, f), tolerance=0.08, angularTolerance=0.15)
        manifest.append(dict(name=name, file=f, color=col, explode=off, callout=num, label=label))
        print("  exported", name)
    meta = dict(parts=manifest, Z_TOP=E.Z_TOP, ZC=E.ZC, W=E.W, D=E.D, Z_DRV=E.Z_DRV, HAT_Y=E.HAT_Y)
    with open(os.path.join(OUT, "manifest.json"), "w") as fh:
        json.dump(meta, fh, indent=1)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
