#!/usr/bin/env python3
"""
Parametric sealed enclosure for the FutureProofHomes Satellite1 dev kit (HAT rev6.1 /
R2025.03.18 + Core rev5.1) with a single 4" full-range driver (default Dayton RS100-4).

Coordinate frame (use orientation)
  x right, y toward the REAR (I/O side), z up, origin = centre of footprint at table level.
  The HAT is placed with its flat (I/O) edge against the rear wall of the head.

Parts
  chamber      sealed box minus the front baffle; prints lying on its back (no supports)
  baffle       front plate with driver cutout + glue tongue; prints face-down
  head         top cap carrying the HAT, mics, LED window, buttons, I/O; prints upside-down
  diffuser     LED light ring (clear/natural PETG or white PLA); prints flat
  button_cap   x4; prints top-down
  isolator     x4 TPU spoke springs between head and chamber; prints flat
  mic_gasket   x4 TPU (or cut closed-cell foam) rings sealing mic ports to the head
  driver_gasket  TPU flat ring under the driver flange (skip if driver has one)

Run:  python3 enclosure.py            -> writes out/*.stl (print orientation) + out/assembly.step
      python3 enclosure.py --check    -> also checks fit against the FPH HAT STEP model
All dimensions are millimetres.
"""
import argparse
import math
import os
import sys

import cadquery as cq

# =============================================================================
# 1. ACOUSTIC TARGET  (from acoustics/box_design.py)
# =============================================================================
V_NET_L = 1.80            # net air volume behind the driver (RS100-4: Qtc ~0.70, F3 ~115 Hz)
DRIVER_DISP_L = 0.10      # driver displacement estimate (magnet + basket); water-test to refine

# =============================================================================
# 2. DRIVER  (Dayton RS100-4, Dayton spec page; bolt circle is third-party -> verify)
# =============================================================================
DRIVER_CUTOUT_D = 77.2
DRIVER_OD = 98.0
DRIVER_DEPTH = 51.0        # front of flange to back of magnet
DRIVER_BCD = 89.9          # bolt circle (measure your driver!)
DRIVER_HOLES = 6
DRIVER_HOLE_ANGLE0 = 90.0  # first hole angle (deg, 0 = +x)
DRIVER_PILOT_D = 2.5       # #4 / M3 thread-forming screw pilot
FLANGE_RECESS = 0.0        # >0 for flush mounting (then print baffle back-face down)
CUTOUT_REAR_CHAMFER = 4.0  # opens the cutout behind the cone
DRIVER_Z_ABOVE_FLOOR = 10.0  # gap between driver flange and inner floor level

# =============================================================================
# 3. BOX SHELL
# =============================================================================
W = 130.0                  # outer width (x)
D = 94.0                   # outer depth (y); ~2*(HAT_FLAT_Y+IO_GAP+HEAD_WALL) centres the LED ring
R_CORNER = 10.0            # vertical edge radius
EDGE_FILLET = 2.5          # top/bottom outer edge rounding
WALL = 4.0                 # chamber side/back walls
WALL_BOT = 5.0             # chamber floor
TOP_WALL = 10.0            # chamber roof (thick: mass + isolator sockets)
BAFFLE_T = 8.0
TONGUE_DEPTH = 4.0         # baffle glue/alignment tongue that enters the chamber
TONGUE_W = 4.0
TONGUE_CLEAR = 0.2
CAVITY_BACK_FILLET = 6.0
BRACE_ENABLE = True
BRACE_T = 5.0              # U-brace (left/back/right) thickness in z
BRACE_W = 10.0             # how far it projects from the walls
BUMPER_D = 12.7            # 1/2" adhesive silicone / Sorbothane bumpers
BUMPER_RECESS = 1.0
BUMPER_INSET = 22.0

# Optional vent (OFF: sealed is the recommended alignment for mic reliability)
PORT_ENABLE = False
PORT_D = 30.0
PORT_LEN = 144.0           # from box_design.py --vented --vb 3.0 --fb 65 --port-d 30
PORT_Z = 30.0
PORT_FLARE = 4.0

# =============================================================================
# 4. SATELLITE1 HAT  (all from FPH STEP: Satellite1-Hardware/hat/rev6.1hat3D.step,
#    cross-checked with Satellite1-Enclosures/assets/Hat R2025.03.18.step and the
#    OEM Sat1.1 top plate). Coordinates relative to the HAT circle centre, +y = flat edge.
# =============================================================================
HAT_R = 44.0               # board is a 88 mm circle ...
HAT_FLAT_Y = 42.0          # ... with one flat edge 42 mm from centre (I/O side)
HAT_T = 1.6                # rev6.1 model 1.51; R2025 model 1.60
HAT_MOUNT_HOLES = [(-29.0, -24.5), (29.0, -24.5), (-29.0, 24.5), (29.0, 24.5)]  # 3.2 mm
HAT_SPARE_HOLES = [(-29.0, -1.5), (29.0, -1.5)]                                  # 3.2 mm, unused
HAT_HOLE_D = 3.2
MIC_PORTS = [(0.0, 35.5), (35.5, 0.0), (0.0, -35.5), (-35.5, 0.0)]  # MK1..MK4 top ports, d0.65
MIC_TOP_ABOVE_PCB = 1.23   # CUI CMM-4030DT top surface above PCB top
LED_RING_R = 41.0          # 24 LEDs, 15 deg pitch, first at 90 deg
LED_COUNT = 24
BUTTONS = [(-16.0, 0.0), (0.0, 16.0), (16.0, 0.0), (0.0, -16.0)]   # SW1..SW4, 6x6 tact
SW_TOP_ABOVE_PCB = 5.0
SENSOR_HOLES = [(10.0, -33.0), (-10.0, -33.0)]   # U4 LTR-303 lux, U12 temp/humidity
# bottom-side I/O (z relative to PCB bottom face, negative = below board)
USB_C = [(-13.5, -1.12), (13.5, -1.12)]          # J5, J2 centre x / centre z; mouth at y=40.2
USB_W, USB_H = 8.94, 4.28
JACK = (0.0, -2.56)                               # 3.5 mm jack centre x / z; face at y=43.23
JACK_W, JACK_H = 7.9, 5.75
SPK_CONN = (-34.9, 10.0)                          # J4 2-pin 2.5 mm speaker connector (bottom)
BELOW_PCB_STACK = 10.0     # Core board stack below HAT; FPH OEM leaves 7.1-8.6 mm. MEASURE.

# =============================================================================
# 5. HEAD (top cap) + ISOLATION
# =============================================================================
HEAD_WALL = 2.5
TOP_T = 2.4                # top plate thickness
BAY_CLEAR = 14.0           # chamber roof -> HAT bottom (>= BELOW_PCB_STACK + margin)
GAP_TOP = 6.4              # HAT top -> underside of top plate (switches are 5.0 tall)
IO_GAP = 0.4               # HAT flat edge -> inner face of rear wall
SHADOW_GAP = 1.5           # visible reveal between head and chamber (head floats)
HAT_BOSS_D = 5.5
HAT_PILOT_D = 2.7          # M3 thread-forming (FPH OEM uses M3x10 into 2.75)
MIC_HOLE_D = 1.0           # through the top plate, short to keep pipe resonance > 15 kHz
MIC_BOSS_D = 4.0
MIC_GASKET_OD, MIC_GASKET_ID, MIC_GASKET_T = 2.8, 1.4, 1.5   # compressed to MIC_GASKET_COMP
MIC_GASKET_COMP = 1.0
LED_SLOT_RI, LED_SLOT_RO = 39.8, 42.2
LED_CBORE_RI, LED_CBORE_RO, LED_CBORE_DEPTH = 38.8, 43.2, 1.0
LED_BRIDGE_ANGLES = [7.5, 97.5, 187.5, 277.5]   # between LEDs (LEDs sit on multiples of 15 deg)
LED_BRIDGE_W = 3.0
BTN_HOLE_D = 10.4
BTN_CAP_D, BTN_FLANGE_D, BTN_FLANGE_T, BTN_STEM_D = 10.0, 13.0, 0.8, 4.0
BTN_PROUD = 0.4
BTN_TRAVEL_CLEAR = 0.2
SENSOR_HOLE_D = 2.5
USB_CUT_W, USB_CUT_H, USB_CUT_R = 12.6, 7.2, 2.5   # passes a typical USB-C overmold
JACK_CUT_W, JACK_CUT_H, JACK_CUT_R = 8.6, 6.6, 2.0   # jack body pokes 0.8 mm into the wall
IO_CHAMFER = 0.8

ISO_INSET = 14.0           # isolator / post centres at (+-(W/2-ISO_INSET), +-(D/2-ISO_INSET))
ISO_OD, ISO_RING_W, ISO_RING_H = 22.0, 1.5, 3.0
ISO_HUB_D, ISO_HUB_H, ISO_HUB_PROUD = 8.0, 5.0, 2.0
ISO_SPOKES, ISO_SPOKE_W, ISO_SPOKE_T = 3, 2.5, 1.0
ISO_POCKET_EXTRA = 2.5
PIN_D = 4.0
PIN_INTERFERENCE = 0.3
POST_D = 8.0

GLAND_XY = (-40.0, None)   # speaker-wire pass-through; y=None -> under J4
GLAND_D = 5.0

# =============================================================================
# derived layout
# =============================================================================
ISO_X, ISO_Y = W / 2 - ISO_INSET, D / 2 - ISO_INSET
HAT_Y = D / 2 - HEAD_WALL - IO_GAP - HAT_FLAT_Y            # HAT centre y in enclosure frame
Y_SPLIT = -D / 2 + BAFFLE_T                               # baffle / chamber joint
CAV_W = W - 2 * WALL
CAV_Y0, CAV_Y1 = Y_SPLIT, D / 2 - WALL


def hat(x, y):
    """HAT-frame -> enclosure-frame xy."""
    return (x, y + HAT_Y)


def rounded_box(w, d, h, r, z0=0.0, edge=0.0):
    b = cq.Workplane("XY").box(w, d, h, centered=(True, True, False)).translate((0, 0, z0))
    b = b.edges("|Z").fillet(r)
    if edge > 0:
        b = b.faces(">Z or <Z").edges().fillet(edge)
    return b


def cylinder(d, h, x, y, z0, axis="Z"):
    wp = {"Z": "XY", "Y": "XZ", "X": "YZ"}[axis]
    c = cq.Workplane(wp).circle(d / 2).extrude(h)
    if axis == "Z":
        return c.translate((x, y, z0))
    if axis == "Y":   # XZ workplane normal is -Y: runs from y down to y-h
        return c.translate((x, y, z0))
    raise ValueError


def cavity_solid(h_cav):
    cav = (cq.Workplane("XY")
           .box(CAV_W, CAV_Y1 - CAV_Y0, h_cav, centered=(True, False, False))
           .translate((0, CAV_Y0, WALL_BOT)))
    return cav.edges("|Z and >Y").fillet(CAVITY_BACK_FILLET)


def brace_solid(h_cav, z_drv):
    z = z_drv + DRIVER_OD / 2 + 12.0
    if not BRACE_ENABLE or z + BRACE_T > WALL_BOT + h_cav - 8:
        return None
    y0 = Y_SPLIT + TONGUE_DEPTH + 0.5
    outer = (cq.Workplane("XY").box(CAV_W, CAV_Y1 - y0, BRACE_T, centered=(True, False, False))
             .translate((0, y0, z)))
    inner = (cq.Workplane("XY")
             .box(CAV_W - 2 * BRACE_W, CAV_Y1 - y0 - BRACE_W + 1, BRACE_T + 2, centered=(True, False, False))
             .translate((0, y0 - 1, z - 1)))
    return outer.cut(inner)


def tongue_solid(h_cav):
    y0 = Y_SPLIT
    ow, oh = CAV_W - 2 * TONGUE_CLEAR, h_cav - 2 * TONGUE_CLEAR
    o = cq.Workplane("XZ").rect(ow, oh).extrude(-TONGUE_DEPTH)
    i = cq.Workplane("XZ").rect(ow - 2 * TONGUE_W, oh - 2 * TONGUE_W).extrude(-TONGUE_DEPTH)
    return o.cut(i).translate((0, y0, WALL_BOT + h_cav / 2))


def port_solid(h_cav):
    """Port tube (material) and bore (air) entering from the rear wall."""
    tube = cylinder(PORT_D + 6, PORT_LEN, 0, D / 2, PORT_Z, axis="Y")
    bore = cylinder(PORT_D, PORT_LEN + 2, 0, D / 2 + 1, PORT_Z, axis="Y")
    return tube, bore


def air_volume_l(h_cav, z_drv):
    v = cavity_solid(h_cav).val().Volume()
    v -= tongue_solid(h_cav).val().Volume()
    b = brace_solid(h_cav, z_drv)
    if b is not None:
        v -= b.val().Volume()
    if PORT_ENABLE:
        t, bo = port_solid(h_cav)
        v -= t.val().Volume() - bo.val().Volume()
    return v * 1e-6 - DRIVER_DISP_L


def solve_cavity_height():
    z_drv = WALL_BOT + DRIVER_Z_ABOVE_FLOOR + DRIVER_OD / 2
    h = 1e6 * (V_NET_L + DRIVER_DISP_L) / (CAV_W * (CAV_Y1 - CAV_Y0))
    for _ in range(6):
        err = V_NET_L - air_volume_l(h, z_drv)
        h += 1e6 * err / (CAV_W * (CAV_Y1 - CAV_Y0))
        if abs(err) < 0.002:
            break
    return h, z_drv


H_CAV, Z_DRV = solve_cavity_height()
H_CH = WALL_BOT + H_CAV + TOP_WALL                 # chamber outer height
ZC = H_CH                                          # chamber roof (top surface)
Z_HB = ZC + BAY_CLEAR                              # HAT bottom face
Z_HT = Z_HB + HAT_T                                # HAT top face
Z_U = Z_HT + GAP_TOP                               # underside of top plate
Z_TOP = Z_U + TOP_T                                # top of enclosure
GLAND = (GLAND_XY[0], GLAND_XY[1] if GLAND_XY[1] is not None else hat(*SPK_CONN)[1])


# =============================================================================
# parts (use orientation)
# =============================================================================
def shell():
    outer = rounded_box(W, D, H_CH, R_CORNER, edge=EDGE_FILLET)
    s = outer.cut(cavity_solid(H_CAV))
    b = brace_solid(H_CAV, Z_DRV)
    if b is not None:
        s = s.union(b)
    return s


def chamber():
    keep = cq.Workplane("XY").box(W + 2, D, H_CH + 2, centered=(True, False, False)) \
        .translate((0, Y_SPLIT, -1))
    c = shell().intersect(keep)
    # isolator sockets (ring seat) + pockets (hub/spokes free to move)
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * ISO_X, sy * ISO_Y
            c = c.cut(cylinder(ISO_OD + 0.3, ISO_RING_H + 1, x, y, ZC - ISO_RING_H))
            c = c.cut(cylinder(ISO_OD - 2 * ISO_RING_W, ISO_RING_H + ISO_POCKET_EXTRA + 1, x, y,
                               ZC - ISO_RING_H - ISO_POCKET_EXTRA))
    # speaker wire gland
    c = c.cut(cylinder(GLAND_D, TOP_WALL + 2, GLAND[0], GLAND[1], ZC - TOP_WALL - 1))
    # bumper recesses
    for sx in (-1, 1):
        for sy in (-1, 1):
            c = c.cut(cylinder(BUMPER_D + 0.4, BUMPER_RECESS, sx * (W / 2 - BUMPER_INSET),
                               sy * (D / 2 - BUMPER_INSET), 0))
    if PORT_ENABLE:
        assert PORT_LEN < CAV_Y1 - CAV_Y0 - 15, \
            f"port {PORT_LEN} mm does not fit a {CAV_Y1 - CAV_Y0:.0f} mm deep cavity (fold it)"
        tube, bore = port_solid(H_CAV)
        c = c.union(tube.intersect(cavity_solid(H_CAV))).cut(bore)
        flare = (cq.Workplane("XZ").workplane(offset=-D / 2).circle(PORT_D / 2 + PORT_FLARE)
                 .workplane(offset=PORT_FLARE).circle(PORT_D / 2).loft()).translate((0, 0, PORT_Z))
        c = c.cut(flare)
    return c


def baffle():
    keep = cq.Workplane("XY").box(W + 2, BAFFLE_T, H_CH + 2, centered=(True, False, False)) \
        .translate((0, -D / 2, -1))
    b = shell().intersect(keep).union(tongue_solid(H_CAV))
    # driver cutout, rear chamfer, optional flush recess
    cut = cq.Workplane("XZ").workplane(offset=D / 2).center(0, Z_DRV) \
        .circle(DRIVER_CUTOUT_D / 2).extrude(-(BAFFLE_T + 1))
    b = b.cut(cut.translate((0, -0.5, 0)))
    ch = (cq.Workplane("XZ").workplane(offset=-Y_SPLIT + CUTOUT_REAR_CHAMFER).center(0, Z_DRV)
          .circle(DRIVER_CUTOUT_D / 2).workplane(offset=-(CUTOUT_REAR_CHAMFER + 0.01))
          .circle(DRIVER_CUTOUT_D / 2 + CUTOUT_REAR_CHAMFER + 0.01).loft())
    b = b.cut(ch)
    if FLANGE_RECESS > 0:
        rec = cq.Workplane("XZ").workplane(offset=D / 2).center(0, Z_DRV) \
            .circle(DRIVER_OD / 2 + 0.5).extrude(-FLANGE_RECESS)
        b = b.cut(rec)
    for k in range(DRIVER_HOLES):
        a = math.radians(DRIVER_HOLE_ANGLE0 + 360 * k / DRIVER_HOLES)
        x, z = DRIVER_BCD / 2 * math.cos(a), Z_DRV + DRIVER_BCD / 2 * math.sin(a)
        h = cq.Workplane("XZ").workplane(offset=D / 2 - FLANGE_RECESS).center(x, z) \
            .circle(DRIVER_PILOT_D / 2).extrude(-(BAFFLE_T - 1.5 - FLANGE_RECESS))
        b = b.cut(h)
    return b


def head():
    h_out = Z_TOP - (ZC + SHADOW_GAP)
    z0 = ZC + SHADOW_GAP
    outer = rounded_box(W, D, h_out, R_CORNER, z0=z0)
    outer = outer.faces(">Z").edges().fillet(EDGE_FILLET)
    inner = rounded_box(W - 2 * HEAD_WALL, D - 2 * HEAD_WALL, Z_U - z0 + 1, R_CORNER - HEAD_WALL,
                        z0=z0 - 1)
    hd = outer.cut(inner)

    # HAT mounting bosses
    for (x, y) in HAT_MOUNT_HOLES:
        X, Y = hat(x, y)
        hd = hd.union(cylinder(HAT_BOSS_D, GAP_TOP + 0.5, X, Y, Z_HT))
        hd = hd.cut(cylinder(HAT_PILOT_D, GAP_TOP - 0.5, X, Y, Z_HT - 0.01))
    # mic bosses + holes
    boss_bot = Z_HT + MIC_TOP_ABOVE_PCB + MIC_GASKET_COMP
    for (x, y) in MIC_PORTS:
        X, Y = hat(x, y)
        hd = hd.union(cylinder(MIC_BOSS_D, Z_U - boss_bot + 0.5, X, Y, boss_bot))
        hd = hd.cut(cylinder(MIC_HOLE_D, Z_TOP - boss_bot + 2, X, Y, boss_bot - 1))
        hd = hd.cut(cq.Workplane("XY").workplane(offset=Z_TOP - 0.4).center(X, Y)
                    .circle(MIC_HOLE_D / 2).workplane(offset=0.41).circle(MIC_HOLE_D / 2 + 0.4).loft())
    # corner posts + pins onto the isolators
    z_sh = ZC + ISO_HUB_PROUD
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * ISO_X, sy * ISO_Y
            hd = hd.union(cylinder(POST_D, Z_U - z_sh + 0.5, x, y, z_sh))
            hd = hd.union(cylinder(PIN_D, ISO_HUB_H + 1.5, x, y, z_sh - ISO_HUB_H - 1.5))
    # buttons, sensors
    for (x, y) in BUTTONS:
        hd = hd.cut(cylinder(BTN_HOLE_D, TOP_T + 2, *hat(x, y), Z_U - 1))
    for (x, y) in SENSOR_HOLES:
        hd = hd.cut(cylinder(SENSOR_HOLE_D, TOP_T + 2, *hat(x, y), Z_U - 1))
    # LED window: counterbore from top + through slots with bridges
    cx, cy = hat(0, 0)
    cb = (cq.Workplane("XY").circle(LED_CBORE_RO).circle(LED_CBORE_RI)
          .extrude(LED_CBORE_DEPTH + 0.01).translate((cx, cy, Z_TOP - LED_CBORE_DEPTH)))
    slot = (cq.Workplane("XY").circle(LED_SLOT_RO).circle(LED_SLOT_RI)
            .extrude(TOP_T + 1).translate((cx, cy, Z_U - 0.5)))
    for a in LED_BRIDGE_ANGLES:
        br = (cq.Workplane("XY").box(LED_SLOT_RO + 2, LED_BRIDGE_W, TOP_T + 2, centered=(False, True, False))
              .rotate((0, 0, 0), (0, 0, 1), a).translate((cx, cy, Z_U - 1)))
        slot = slot.cut(br)
    hd = hd.cut(cb).cut(slot)
    # rear I/O
    yw = D / 2 - HEAD_WALL - 1
    for (x, zr) in USB_C:
        cut = (cq.Workplane("XZ").workplane(offset=-yw).center(x, Z_HB + zr)
               .rect(USB_CUT_W, USB_CUT_H).extrude(-(HEAD_WALL + 2)))
        cut = cut.edges("|Y").fillet(USB_CUT_R)
        hd = hd.cut(cut)
    jx, jz = JACK
    jc = (cq.Workplane("XZ").workplane(offset=-yw).center(jx, Z_HB + jz)
          .rect(JACK_CUT_W, JACK_CUT_H).extrude(-(HEAD_WALL + 2)))
    hd = hd.cut(jc.edges("|Y").fillet(JACK_CUT_R))
    return hd


def diffuser():
    cx, cy = hat(0, 0)
    flange = (cq.Workplane("XY").circle(LED_CBORE_RO - 0.1).circle(LED_CBORE_RI + 0.1)
              .extrude(LED_CBORE_DEPTH))
    plug_h = TOP_T - LED_CBORE_DEPTH
    plug = (cq.Workplane("XY").circle(LED_SLOT_RO - 0.1).circle(LED_SLOT_RI + 0.1)
            .extrude(plug_h).translate((0, 0, -plug_h)))
    for a in LED_BRIDGE_ANGLES:
        plug = plug.cut(cq.Workplane("XY").box(LED_SLOT_RO + 2, LED_BRIDGE_W + 0.4, plug_h + 2,
                                               centered=(False, True, False))
                        .rotate((0, 0, 0), (0, 0, 1), a).translate((0, 0, -plug_h - 1)))
    return flange.union(plug).translate((cx, cy, Z_TOP - LED_CBORE_DEPTH))


def button_cap(x=0.0, y=0.0):
    X, Y = hat(x, y)
    body_h = TOP_T + BTN_PROUD
    stem = GAP_TOP - BTN_FLANGE_T - SW_TOP_ABOVE_PCB - BTN_TRAVEL_CLEAR
    assert stem >= 0, "GAP_TOP too small for button caps"
    cap = cylinder(BTN_CAP_D, body_h, X, Y, Z_U)
    cap = cap.union(cylinder(BTN_FLANGE_D, BTN_FLANGE_T, X, Y, Z_U - BTN_FLANGE_T))
    if stem > 0:
        cap = cap.union(cylinder(BTN_STEM_D, stem, X, Y, Z_U - BTN_FLANGE_T - stem))
    return cap.faces(">Z").edges().fillet(0.6)


def isolator(x=0.0, y=0.0):
    """Ring seated in the roof socket; hub carries the head pin; spokes are the springs."""
    z0 = ZC - ISO_RING_H
    ring = (cq.Workplane("XY").circle(ISO_OD / 2).circle(ISO_OD / 2 - ISO_RING_W)
            .extrude(ISO_RING_H))
    hub = cq.Workplane("XY").circle(ISO_HUB_D / 2).circle((PIN_D - PIN_INTERFERENCE) / 2) \
        .extrude(ISO_HUB_H)
    iso = ring.union(hub)
    ln = ISO_OD / 2 - ISO_RING_W - ISO_HUB_D / 2 + 1.0
    for k in range(ISO_SPOKES):
        sp = (cq.Workplane("XY").box(ln, ISO_SPOKE_W, ISO_SPOKE_T, centered=(False, True, False))
              .translate((ISO_HUB_D / 2 - 0.5, 0, 0)).rotate((0, 0, 0), (0, 0, 1), 360 * k / ISO_SPOKES + 90))
        iso = iso.union(sp)
    iso = iso.cut(cylinder(PIN_D - PIN_INTERFERENCE, ISO_HUB_H + 2, 0, 0, -1))
    return iso.translate((x, y, z0))


def mic_gasket(x=0.0, y=0.0):
    X, Y = hat(x, y)
    g = cq.Workplane("XY").circle(MIC_GASKET_OD / 2).circle(MIC_GASKET_ID / 2).extrude(MIC_GASKET_COMP)
    return g.translate((X, Y, Z_HT + MIC_TOP_ABOVE_PCB))


def driver_gasket():
    g = cq.Workplane("XZ").circle(DRIVER_OD / 2).circle(DRIVER_CUTOUT_D / 2 + 1.0).extrude(1.0)
    return g.translate((0, -D / 2, Z_DRV))


# =============================================================================
# export / checks
# =============================================================================
BUILD_VOL = (340.0, 320.0, 340.0)   # Bambu Lab H2S


def to_bed(wp, rot=None):
    """Rotate into print orientation, drop onto z=0, centre on x/y."""
    s = wp.val()
    if rot is not None:
        axis, ang = rot
        s = s.rotate(cq.Vector(0, 0, 0), cq.Vector(*axis), ang)
    bb = s.BoundingBox()
    s = s.translate(cq.Vector(-(bb.xmin + bb.xmax) / 2, -(bb.ymin + bb.ymax) / 2, -bb.zmin))
    return s


def parts():
    p = {
        "chamber": (chamber(), ((1, 0, 0), -90)),        # back wall on the bed
        "baffle": (baffle(), ((1, 0, 0), 90)),           # front face on the bed
        "head": (head(), ((1, 0, 0), 180)),              # top face on the bed
        "diffuser": (diffuser(), ((1, 0, 0), 180)),      # visible face on the bed
        "button_cap": (button_cap(*BUTTONS[0]), ((1, 0, 0), 180)),
        "isolator": (isolator(-ISO_X, -ISO_Y), None),
        "mic_gasket": (mic_gasket(*MIC_PORTS[0]), None),
        "driver_gasket": (driver_gasket(), ((1, 0, 0), 90)),
    }
    return p


def summary():
    v = air_volume_l(H_CAV, Z_DRV)
    print(f"net air volume  : {v:.3f} L (target {V_NET_L} L, driver disp {DRIVER_DISP_L} L assumed)")
    print(f"chamber         : {W:.0f} x {D:.0f} x {H_CH:.1f} mm (cavity height {H_CAV:.1f})")
    print(f"overall height  : {Z_TOP:.1f} mm   driver centre z={Z_DRV:.1f}")
    mic_z = Z_TOP
    print(f"driver centre -> mic plane : {mic_z - Z_DRV:.0f} mm vertical")
    print(f"HAT centre y offset        : {HAT_Y:.1f} mm toward rear; bay clearance {BAY_CLEAR} mm "
          f"(assumed Core stack {BELOW_PCB_STACK} mm)")
    post_gap = math.hypot(ISO_X, ISO_Y - HAT_Y) - HAT_R - POST_D / 2
    print(f"LED ring centre offset from top-face centre: {HAT_Y:.1f} mm; post-to-HAT clearance "
          f"{post_gap:.1f} mm")
    assert post_gap > 1.0, "isolator posts hit the HAT"
    print(f"basket clearance to back wall: {CAV_Y1 - (-D / 2 + DRIVER_DEPTH):.1f} mm")
    assert BAY_CLEAR >= BELOW_PCB_STACK + 2, "bay too shallow for Core stack"
    assert -D / 2 + DRIVER_DEPTH < CAV_Y1 - 5, "driver too deep for box"


def export(outdir):
    os.makedirs(outdir, exist_ok=True)
    asm = cq.Assembly()
    for name, (wp, rot) in parts().items():
        s = to_bed(wp, rot)
        bb = s.BoundingBox()
        fits = bb.xlen <= BUILD_VOL[0] and bb.ylen <= BUILD_VOL[1] and bb.zlen <= BUILD_VOL[2]
        cq.exporters.export(cq.Workplane().add(s), os.path.join(outdir, f"{name}.stl"),
                            tolerance=0.05, angularTolerance=0.1)
        print(f"  {name:14s} print bbox {bb.xlen:6.1f} x {bb.ylen:6.1f} x {bb.zlen:6.1f}  "
              f"{'fits H2S' if fits else 'DOES NOT FIT'}")
        asm.add(wp, name=name)
    for i, (x, y) in enumerate(BUTTONS[1:], 2):
        asm.add(button_cap(x, y), name=f"button_cap_{i}")
    for i, (x, y) in enumerate(MIC_PORTS[1:], 2):
        asm.add(mic_gasket(x, y), name=f"mic_gasket_{i}")
    for i, (sx, sy) in enumerate([(1, -1), (-1, 1), (1, 1)], 2):
        asm.add(isolator(sx * ISO_X, sy * ISO_Y), name=f"isolator_{i}")
    asm.save(os.path.join(outdir, "assembly.step"))


def check_against_hat(step_path):
    """Load the FPH HAT STEP and report interference with the head + buttons."""
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
    hat_shape = cq.importers.importStep(step_path).val()
    # FPH rev6.1 STEP: board circle centre at (150,-100), PCB bottom at z=0
    hat_shape = hat_shape.translate(cq.Vector(-150.0, 100.0 + HAT_Y, Z_HB))
    hd = head().val()
    caps = [button_cap(x, y).val() for (x, y) in BUTTONS]
    gaskets = [mic_gasket(x, y).val() for (x, y) in MIC_PORTS]
    worst = []
    for sol in hat_shape.Solids():
        bb = sol.BoundingBox()
        for name, other in [("head", hd)] + [(f"cap{i}", c) for i, c in enumerate(caps)]:
            ob = other.BoundingBox()
            if bb.xmax < ob.xmin or bb.xmin > ob.xmax or bb.ymax < ob.ymin or bb.ymin > ob.ymax \
                    or bb.zmax < ob.zmin or bb.zmin > ob.zmax:
                continue
            v = cq.Shape.cast(BRepAlgoAPI_Common(sol.wrapped, other.wrapped).Shape()).Volume()
            if v > 1e-3:
                worst.append((v, name, bb.center))
    if worst:
        for v, n, c in sorted(worst, reverse=True)[:20]:
            print(f"  INTERFERENCE {n}: {v:.3f} mm3 near ({c.x:.1f},{c.y:.1f},{c.z:.1f})")
    else:
        print("  no interference between HAT model and head/button caps")
    # gasket seats: each mic gasket must sit over a mic body, not over air or another part
    for (x, y) in MIC_PORTS:
        print(f"  mic port {x:+.1f},{y:+.1f} -> head hole at {hat(x, y)}")
    return not worst


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "out"))
    ap.add_argument("--check", metavar="HAT_STEP", help="path to FPH rev6.1hat3D.step")
    a = ap.parse_args()
    summary()
    export(a.out)
    if a.check:
        ok = check_against_hat(a.check)
        sys.exit(0 if ok else 1)
