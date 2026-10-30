#!/usr/bin/env python3
"""Quick matplotlib renders of the enclosure: exploded iso view + x=0 section."""
import os
import sys

import cadquery as cq
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import enclosure as E  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
COLORS = dict(chamber="#8a8f98", baffle="#5d6470", head="#b9bec7", diffuser="#f3e6a1",
              button_cap="#4a7bd1", isolator="#e07b39", mic_gasket="#e04040", driver_gasket="#333333")


def tris(shape, tol=0.4):
    v, t = shape.tessellate(tol, 0.5)
    return [[(v[i].x, v[i].y, v[i].z) for i in tri] for tri in t]


def solids(explode=0.0):
    p = {
        "chamber": E.chamber(), "baffle": E.baffle().translate((0, -explode, 0)),
        "head": E.head().translate((0, 0, explode)),
        "diffuser": E.diffuser().translate((0, 0, 1.6 * explode)),
    }
    for i, xy in enumerate(E.BUTTONS):
        p[f"button_cap{i}"] = E.button_cap(*xy).translate((0, 0, 1.4 * explode))
    for i, (sx, sy) in enumerate([(-1, -1), (1, -1), (-1, 1), (1, 1)]):
        p[f"isolator{i}"] = E.isolator(sx * E.ISO_X, sy * E.ISO_Y).translate((0, 0, 0.5 * explode))
    return p


def draw(ax, parts, clip_x=None):
    for name, wp in parts.items():
        s = wp.val()
        if clip_x is not None:
            half = cq.Workplane("XY").box(400, 400, 600, centered=(False, True, False)) \
                .translate((clip_x, 0, -50)).val()
            s = s.cut(half)
            if s.Volume() < 1e-6:
                continue
        key = name.rstrip("0123456789")
        pc = Poly3DCollection(tris(s), facecolor=COLORS.get(key, "#999"), edgecolor="none",
                              alpha=1.0, linewidths=0)
        pc.set_shade = True
        ax.add_collection3d(pc)


def section(ax, parts, x=0.0):
    """2D cut of every part at plane x, drawn in the y-z plane, plus board/driver envelopes."""
    from matplotlib.patches import PathPatch, Rectangle
    from matplotlib.path import Path
    from OCP.BRepTools import BRepTools_WireExplorer
    from OCP.TopAbs import TopAbs_REVERSED
    from OCP.TopoDS import TopoDS
    slab = cq.Workplane("XY").box(0.02, 400, 600, centered=(True, True, False)) \
        .translate((x, 0, -50)).val()
    for name, wp in parts.items():
        cut = wp.val().intersect(slab)
        key = name.rstrip("0123456789")
        for f in cut.Faces():
            if abs(f.normalAt().x) < 0.9:
                continue
            verts, codes = [], []
            for w in [f.outerWire()] + f.innerWires():
                pts = []
                exp = BRepTools_WireExplorer(TopoDS.Wire_s(w.wrapped))
                while exp.More():
                    e = cq.Edge(exp.Current())
                    n = 1 if e.geomType() == "LINE" else 16
                    ps = [e.positionAt(k / n) for k in range(n + 1)]
                    if exp.Orientation() == TopAbs_REVERSED:
                        ps = ps[::-1]
                    pts += ps[:-1]
                    exp.Next()
                verts += [(p.y, p.z) for p in pts] + [(pts[0].y, pts[0].z)]
                codes += [Path.MOVETO] + [Path.LINETO] * (len(pts) - 1) + [Path.CLOSEPOLY]
            ax.add_patch(PathPatch(Path(verts, codes), facecolor=COLORS.get(key, "#999"),
                                   edgecolor="k", lw=0.3))
    # HAT, Core envelope, driver envelope (not modelled as parts)
    y0 = E.HAT_Y - E.HAT_R
    ax.add_patch(Rectangle((y0, E.Z_HB), E.HAT_R + E.HAT_FLAT_Y, E.HAT_T, color="#2e8b57", label="HAT"))
    ax.add_patch(Rectangle((y0 + 5, E.Z_HB - E.BELOW_PCB_STACK), 70, E.BELOW_PCB_STACK - 0.1,
                           fill=False, ls="--", ec="#2e8b57", label="Core stack envelope"))
    ax.add_patch(Rectangle((-E.D / 2 - 3, E.Z_DRV - E.DRIVER_OD / 2), 3, E.DRIVER_OD, color="#222"))
    ax.add_patch(Rectangle((-E.D / 2 + E.BAFFLE_T, E.Z_DRV - 25), E.DRIVER_DEPTH - E.BAFFLE_T, 50,
                           fill=False, ec="#222", ls="--", label="driver basket/magnet"))
    ax.set_xlim(-70, 70); ax.set_ylim(-5, E.Z_TOP + 10); ax.set_aspect("equal")
    ax.set_xlabel("y (mm, rear ->)"); ax.set_ylabel("z (mm)"); ax.legend(loc="lower right", fontsize=7)
    ax.grid(True, lw=0.3)


def setup(ax, elev, azim):
    ax.set_xlim(-80, 80); ax.set_ylim(-80, 80); ax.set_zlim(0, 300)
    ax.set_box_aspect((160, 160, 300))
    ax.view_init(elev=elev, azim=azim)
    ax.set_axis_off()


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    fig = plt.figure(figsize=(11, 8))
    ax = fig.add_subplot(1, 2, 1, projection="3d")
    draw(ax, solids(explode=45.0))
    setup(ax, 18, -60)
    ax.set_title("exploded (front-left)")
    ax2 = fig.add_subplot(1, 2, 2)
    section(ax2, solids(0.0), x=0.0)
    ax2.set_title("section x=0 (looking from the left; front = left)")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "render.png"), dpi=110)

    # top view of the head (mic holes, LED ring, buttons, sensors) and rear I/O
    fig = plt.figure(figsize=(11, 5.5))
    a = fig.add_subplot(1, 2, 1, projection="3d")
    draw(a, {"head": E.head(), "diffuser": E.diffuser(),
             **{f"button_cap{i}": E.button_cap(*xy) for i, xy in enumerate(E.BUTTONS)}})
    a.set_xlim(-70, 70); a.set_ylim(-70, 70); a.set_zlim(E.Z_TOP - 30, E.Z_TOP)
    a.set_box_aspect((140, 140, 30)); a.view_init(elev=89, azim=-90); a.set_axis_off()
    a.set_title("head, top (rear = up)")
    b = fig.add_subplot(1, 2, 2, projection="3d")
    draw(b, {"head": E.head(), "chamber": E.chamber()})
    b.set_xlim(-70, 70); b.set_ylim(-70, 70); b.set_zlim(E.ZC - 20, E.Z_TOP + 5)
    b.set_box_aspect((140, 140, 50)); b.view_init(elev=5, azim=90); b.set_axis_off()
    b.set_title("rear I/O")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "render_head.png"), dpi=110)
    print("wrote", OUT)
