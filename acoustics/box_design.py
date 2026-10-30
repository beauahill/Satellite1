#!/usr/bin/env python3
"""
Box alignment calculator for a Satellite1 (TAS2780) speaker.

Lumped-element model (Thiele/Small, Small 1972/73):
  electrical  V = I(Re + jwLe) + Bl*u
  mechanical  Bl*I = u*(Rms + jwMms + 1/(jwCms)) + Sd^2*Zab*u
  acoustic    sealed : Zab = 1/(jw Cab)                      (|| leakage RaL)
              vented : Zab = 1/(jw Cab) || (jw Map + Rap)    (|| leakage RaL)
SPL is computed from the net radiated volume velocity (cone + port + leak)
into half space (2*pi), which matches how driver sensitivity is quoted.
The model is a rigid piston: trust it below ~2 kHz only (no cone breakup, beaming,
baffle diffraction or room gain). Above that, the slope depends on the assumed Le.

Usage examples
  python3 box_design.py                       # all drivers, default report
  python3 box_design.py --driver RS100-4 --vb 2.4
  python3 box_design.py --driver RS100-4 --vented --vb 3.5 --fb 62 --port-d 34
  python3 box_design.py --list
  python3 box_design.py --driver RS100-4 --plot   # writes PNG next to script
To add a driver, add an entry to DRIVERS. Missing Bl / Mms / Sd are derived
from the others when possible.
"""
import argparse
import math
import sys

import numpy as np

RHO = 1.204        # kg/m^3 air at 20 C
C = 343.2          # m/s
P_REF = 20e-6

# ---------------------------------------------------------------------------
# Amplifier: TI TAS2780 on the Satellite1 HAT (schematic rev6.1: IC1 TAS2780RYAR,
# PVDD tied to USB-C VBUS). Firmware requests a 20 V PD contract
# (Satellite1-ESPHome config/satellite1.base.yaml: fusb302b request_voltage: 20).
# TI rating: 25 W / 4 ohm / 18 V / 1 % THD+N, 30 W at 10 %, min load 3.2 ohm.
# AMP_LEVEL register tops out at 21 dBV full-scale output (tas2780.cpp comment),
# i.e. 11.2 Vrms, which is the practical ceiling regardless of PVDD.
# FPH recommends a 30 W USB-C PD supply for the whole board.
# ---------------------------------------------------------------------------
AMP = dict(
    name="TI TAS2780 (mono, BTL class-D)",
    pvdd=20.0,
    amp_level_max_dbv=21.0,
    min_load_ohm=3.2,
    rated_w_4ohm=25.0,
    supply_w=30.0,          # USB-C PD budget recommended by FPH (whole board)
    board_overhead_w=4.0,   # ESP32-S3 + XMOS + LEDs, rough allowance (assumption)
    efficiency=0.88,        # class-D at mid power, rough (assumption)
)

# ---------------------------------------------------------------------------
# Driver database. Units: Hz, ohm, mH, litres, cm^2, T*m, grams, mm, dB.
# sens = dB SPL @ 2.83 V / 1 m (half space) as published by vendor.
# 'src' lists where the numbers came from; 'flags' lists anything assumed.
# ---------------------------------------------------------------------------
DRIVERS = {
    "RS100-4": dict(
        name="Dayton Audio RS100-4 4in Reference full-range",
        fs=84.8, re=3.0, le=None, qms=2.55, qes=0.66, vas=1.45, sd=35.3,
        bl=3.18, mms=4.3, xmax=4.0, sens=87.5, z_nom=4, p_rms=30,
        cutout_mm=77.2, od_mm=98.0, depth_mm=51.0, bcd_mm=89.9, holes=6,
        price="~$35-49 (Parts Express #295-378; verify stock)",
        src="Dayton product page / spec sheet; Vas+Qms per SpeakerBoxLite",
        flags=["Le not published in sources found -> 0.1 mH assumed",
               "bolt circle 89.9 mm is third-party (diyaudiocart); measure"],
    ),
    "ND105-4": dict(
        name="Dayton Audio ND105-4 4in aluminum midbass (2-way woofer option)",
        fs=78.7, re=3.7, le=0.76, qms=7.42, qes=0.66, vas=1.95, sd=51.5,
        bl=None, mms=None, xmax=4.0, sens=86.8, z_nom=4, p_rms=30,
        cutout_mm=None, od_mm=None, depth_mm=None, bcd_mm=None, holes=None,
        price="~$33-41 (needs tweeter + crossover)",
        src="Dayton/Parts Express listing via Reverb + loudspeakerdatabase",
        flags=["Bl, Mms derived from Fs/Vas/Sd/Qes",
               "metal-cone breakup: needs LP crossover ~2.5-3 kHz"],
    ),
    "TG9FD10-04": dict(
        name="Peerless TG9FD10-04 3.5in glass-fiber full-range (budget)",
        fs=113.0, re=3.25, le=None, qms=3.0, qes=1.14, vas=0.98, sd=None,
        bl=2.4, mms=2.83, xmax=3.9, sens=84.0, z_nom=4, p_rms=10,
        cutout_mm=None, od_mm=None, depth_mm=None, bcd_mm=None, holes=None,
        price="~$13-20 (distributors; Parts Express listing not found)",
        src="Parts Express data as reproduced by distributors; Vas from loudspeakerdatabase",
        flags=["Sources disagree (Fs 113 vs 130 Hz); Sd derived", "10 W rating"],
    ),
}


def complete_driver(d):
    """Fill derived parameters; returns SI dict."""
    d = dict(d)
    d["le"] = 0.1 if d.get("le") is None else d["le"]
    qts = d["qms"] * d["qes"] / (d["qms"] + d["qes"])
    ws = 2 * math.pi * d["fs"]
    vas = d["vas"] * 1e-3
    if d.get("sd") is None:
        cms = 1.0 / (ws ** 2 * d["mms"] * 1e-3)
        d["sd"] = math.sqrt(vas / (RHO * C ** 2 * cms)) * 1e4
    sd = d["sd"] * 1e-4
    cms = vas / (RHO * C ** 2 * sd ** 2)
    if d.get("mms") is None:
        d["mms"] = 1e3 / (ws ** 2 * cms)
    mms = d["mms"] * 1e-3
    if d.get("bl") is None:
        d["bl"] = math.sqrt(ws * mms * d["re"] / d["qes"])
    rms = ws * mms / d["qms"]
    d.update(qts=qts, Cms=cms, Mms=mms, Rms=rms, Sd=sd, Vas=vas, Le=d["le"] * 1e-3)
    return d


# ---------------------------------------------------------------------------
# Core frequency-domain solver
# ---------------------------------------------------------------------------
def simulate(d, f, vb_l, vented=False, fb=None, port_d_mm=None, ql=7.0, v_rms=2.83,
             fill_factor=1.0, r_m=1.0):
    """Returns dict of arrays: spl (dB @ r_m, half space), x_pk (mm), vport_pk (m/s), zin."""
    w = 2 * np.pi * f
    s = 1j * w
    vb = vb_l * 1e-3 * fill_factor          # stuffing raises effective volume
    cab = vb / (RHO * C ** 2)
    if vented:
        wb = 2 * np.pi * fb
        map_ = 1.0 / (wb ** 2 * cab)
        rap = 0.0
        ral = ql / (wb * cab)
        zport = s * map_ + rap
        zab = 1.0 / (s * cab + 1.0 / zport + 1.0 / ral)
    else:
        ral = ql * 20 / (2 * np.pi * d["fs"] * cab)  # sealed: very small leak
        zport = None
        zab = 1.0 / (s * cab + 1.0 / ral)
    ze = d["re"] + s * d["Le"]
    zm = d["Rms"] + s * d["Mms"] + 1.0 / (s * d["Cms"]) + d["Sd"] ** 2 * zab
    u = d["bl"] * v_rms / (ze * zm + d["bl"] ** 2)          # cone velocity (rms)
    ud = d["Sd"] * u
    pb = -ud * zab                                          # box pressure
    up = pb / zport if vented else 0 * u
    ul = pb / ral
    u_tot = ud + up + ul
    p = RHO * s * u_tot / (2 * np.pi * r_m)                 # half-space
    spl = 20 * np.log10(np.abs(p) / P_REF)
    x_pk = np.abs(u / s) * math.sqrt(2) * 1e3
    v_port = (np.abs(up) / (math.pi * (port_d_mm * 1e-3 / 2) ** 2) * math.sqrt(2)
              if vented else np.zeros_like(f))
    i = v_rms / (ze + d["bl"] ** 2 / zm)
    zin = v_rms / i
    return dict(spl=spl, x_pk=x_pk, vport_pk=v_port, zin=zin)


def f_at(f, spl, ref, drop):
    """Lowest frequency where response is still within -drop dB of ref (scan down)."""
    idx = np.where(spl >= ref - drop)[0]
    if len(idx) == 0:
        return float("nan")
    # first contiguous region from the top end
    k = idx[-1]
    while k - 1 in idx:
        k -= 1
    return float(f[k])


def passband_ref(f, spl):
    band = (f > 300) & (f < 1000)
    return float(np.mean(spl[band]))


def sealed_vb_for_qtc(d, qtc):
    """Net volume giving the target Qtc. If the driver's Qts is already near/above the
    target, fall back to Qtc = 1.25*Qts (a small box only raises Q further)."""
    qtc = max(qtc, 1.25 * d["qts"])
    a = (qtc / d["qts"]) ** 2 - 1.0
    return d["vas"] / a


def port_length(vb_l, fb, d_mm, flanged_ends=1):
    """Physical port length (mm) for tuning fb with a round port of diameter d.
    End correction: 0.85r per flanged end + 0.61r per free end (r=radius)."""
    r = d_mm / 2e3
    sp = math.pi * r ** 2
    leff = C ** 2 * sp / ((2 * math.pi * fb) ** 2 * vb_l * 1e-3)
    corr = (0.85 * flanged_ends + 0.61 * (2 - flanged_ends)) * r
    return (leff - corr) * 1e3


def port_pipe_resonance(l_mm, d_mm):
    """First open-open pipe mode of the port (Hz) - leaks through as a midrange peak."""
    leff = l_mm / 1e3 + 1.46 * d_mm / 2e3
    return C / (2 * leff)


def amp_limits(d):
    v_amp = 10 ** (AMP["amp_level_max_dbv"] / 20)              # 11.2 Vrms
    v_pvdd = 0.9 * AMP["pvdd"] / math.sqrt(2)                   # BTL, ~90 % swing
    v_thermal = math.sqrt(d["p_rms"] * d["z_nom"])
    p_supply = (AMP["supply_w"] - AMP["board_overhead_w"]) * AMP["efficiency"]
    v_supply = math.sqrt(p_supply * d["z_nom"])                 # continuous sine
    v_max = min(v_amp, v_pvdd, v_thermal)
    return dict(v_amp=v_amp, v_pvdd=v_pvdd, v_thermal=v_thermal, v_supply_cont=v_supply,
                v_max=v_max, p_max_nom=v_max ** 2 / d["z_nom"])


def max_spl_curve(d, f, **box):
    """Max SPL vs f limited by min(voltage ceiling, Xmax)."""
    lim = amp_limits(d)
    r = simulate(d, f, v_rms=1.0, **box)
    v_x = d["xmax"] / r["x_pk"]                       # volts that hit Xmax
    v = np.minimum(v_x, lim["v_max"])
    return r["spl"] + 20 * np.log10(v), v_x


def best_vented(d, f, vb_max=3.5):
    """Grid search: lowest F3 with passband ripple <= +1.0 dB (no big hump),
    for net volumes up to vb_max litres (keeps the box shelf-sized)."""
    best = None
    for vb in np.linspace(0.6 * d["vas"], min(4.0 * d["vas"], vb_max), 40):
        for fb in np.linspace(0.55 * d["fs"], 1.15 * d["fs"], 40):
            r = simulate(d, f, vb, vented=True, fb=fb, port_d_mm=30)
            ref = passband_ref(f, r["spl"])
            if np.max(r["spl"][(f > 40) & (f < 1000)]) - ref > 1.0:
                continue
            f3 = f_at(f, r["spl"], ref, 3)
            if best is None or f3 < best[2]:
                best = (vb, fb, f3)
    return best


def size_port(d, vb, fb, f, v_limit=0.05 * C, max_len_mm=150):
    """Smallest round port keeping peak air speed < v_limit at max drive."""
    lim = amp_limits(d)
    for dia in np.arange(20, 61, 1.0):
        L = port_length(vb, fb, dia)
        if L > max_len_mm:
            return None
        r = simulate(d, f, vb, vented=True, fb=fb, port_d_mm=dia, v_rms=lim["v_max"])
        # cap drive where cone hits Xmax (we'd high-pass/limit there anyway)
        scale = np.minimum(1.0, d["xmax"] / r["x_pk"])
        vmax = float(np.max(r["vport_pk"] * scale))
        if vmax <= v_limit:
            return dia, L, vmax
    return None


def isolator_report(mass_kg=0.13, e_mpa=(12, 26, 45), w_mm=2.5, t_mm=1.0, l_mm=5.5,
                    spokes=3, n_iso=4):
    """Vertical natural frequency of the head on 4 printed TPU spoke springs.
    Spoke = fixed-guided beam: k = E*w*t^3/L^3."""
    out = []
    for e in e_mpa:
        k1 = e * 1e6 * (w_mm * 1e-3) * (t_mm * 1e-3) ** 3 / (l_mm * 1e-3) ** 3
        k = k1 * spokes * n_iso
        fn = math.sqrt(k / mass_kg) / (2 * math.pi)
        sag = mass_kg * 9.81 / k * 1e3
        out.append((e, k, fn, sag))
    return out


def lr2_crossover(fc, r_woofer, r_tweeter):
    """2nd-order Linkwitz-Riley starting values (resistive-load approximation)."""
    return dict(L_lp_mH=r_woofer / (math.pi * fc) * 1e3,
                C_lp_uF=1e6 / (4 * math.pi * fc * r_woofer),
                C_hp_uF=1e6 / (4 * math.pi * fc * r_tweeter),
                L_hp_mH=r_tweeter / (math.pi * fc) * 1e3)


def zobel(re, le_mh):
    return dict(R=1.25 * re, C_uF=le_mh * 1e-3 / re ** 2 * 1e6)


# ---------------------------------------------------------------------------
def report(key, args, f):
    d = complete_driver(DRIVERS[key])
    lim = amp_limits(d)
    print("=" * 78)
    print(f"{d['name']}  [{key}]")
    print(f"  T/S: Fs={d['fs']:.1f} Hz  Re={d['re']:.2f} ohm  Le={d['le']:.2f} mH  "
          f"Qms={d['qms']:.2f}  Qes={d['qes']:.2f}  Qts={d['qts']:.3f}")
    print(f"       Vas={d['vas']:.2f} L  Sd={d['sd']:.1f} cm2  Bl={d['bl']:.2f} Tm  "
          f"Mms={d['mms']:.2f} g  Xmax={d['xmax']:.1f} mm  sens={d['sens']} dB/2.83V")
    print(f"  EBP = Fs/Qes = {d['fs']/d['qes']:.0f}  (<50 sealed-leaning, >90 vented-leaning)")
    print(f"  Price: {d['price']}")
    for fl in d["flags"]:
        print(f"  ! {fl}")
    z = simulate(d, f, 2.0)["zin"]
    zmin = float(np.min(np.abs(z[(f > 150) & (f < 20000)])))
    print(f"  Amp match: Znom={d['z_nom']} ohm, |Z|min~{zmin:.2f} ohm vs TAS2780 min "
          f"{AMP['min_load_ohm']} ohm -> {'OK' if zmin >= AMP['min_load_ohm'] else 'slightly below, see notes'}")
    print(f"  Voltage ceilings: AMP_LEVEL {lim['v_amp']:.1f} V, PVDD {lim['v_pvdd']:.1f} V, "
          f"driver thermal {lim['v_thermal']:.1f} V -> {lim['v_max']:.1f} Vrms "
          f"({lim['p_max_nom']:.1f} W into {d['z_nom']} ohm)")
    print(f"  30 W PD supply sustains ~{lim['v_supply_cont']:.1f} Vrms continuous sine "
          f"(music crest factor makes peaks fine)")

    # ---- sealed
    vb_q707 = sealed_vb_for_qtc(d, 0.707)
    vb = args.vb if (args.vb and not args.vented) else vb_q707
    a = d["vas"] / (vb * args.fill)
    qtc = d["qts"] * math.sqrt(a + 1)
    fc = d["fs"] * math.sqrt(a + 1)
    r = simulate(d, f, vb, fill_factor=args.fill)
    ref = passband_ref(f, r["spl"])
    f3, f6 = f_at(f, r["spl"], ref, 3), f_at(f, r["spl"], ref, 6)
    mx, _ = max_spl_curve(d, f, vb_l=vb, fill_factor=args.fill)
    print(f"  SEALED  Vb(net)={vb:.2f} L (Qtc .707 -> {vb_q707:.2f} L), fill x{args.fill:.2f}")
    print(f"          Qtc={qtc:.3f}  Fc={fc:.1f} Hz  F3={f3:.0f} Hz  F6={f6:.0f} Hz  "
          f"passband {ref:.1f} dB/2.83V/1m")
    for fq in (60, 80, 100, 150):
        k = np.argmin(np.abs(f - fq))
        print(f"          max SPL @1m {fq:>3} Hz: {mx[k]:5.1f} dB")

    # ---- vented
    if args.vented and args.vb and args.fb:
        vbv, fbv = args.vb, args.fb
    else:
        bv = best_vented(d, f, args.vb_max)
        vbv, fbv = (bv[0], bv[1]) if bv else (None, None)
    if vbv:
        port = (args.port_d, port_length(vbv, fbv, args.port_d), None) if args.port_d else \
            size_port(d, vbv, fbv, f)
        if port:
            pd, pl, _ = port
            rv = simulate(d, f, vbv, vented=True, fb=fbv, port_d_mm=pd)
            refv = passband_ref(f, rv["spl"])
            f3v = f_at(f, rv["spl"], refv, 3)
            mxv, _ = max_spl_curve(d, f, vb_l=vbv, vented=True, fb=fbv, port_d_mm=pd)
            lim_r = simulate(d, f, vbv, vented=True, fb=fbv, port_d_mm=pd, v_rms=lim["v_max"])
            scale = np.minimum(1.0, d["xmax"] / lim_r["x_pk"])
            vp = float(np.max(lim_r["vport_pk"] * scale))
            print(f"  VENTED  Vb={vbv:.2f} L  Fb={fbv:.1f} Hz  F3={f3v:.0f} Hz  "
                  f"port {pd:.0f} mm dia x {pl:.0f} mm long")
            print(f"          peak port air speed at max drive: {vp:.1f} m/s "
                  f"({100*vp/C:.1f} % of c; aim < 5 %, < 3 % near mics)")
            print(f"          port pipe resonance ~{port_pipe_resonance(pl, pd):.0f} Hz "
                  f"(falls in speech band 300-4000 Hz -> leaks into mics)")
            for fq in (60, 80, 100):
                k = np.argmin(np.abs(f - fq))
                print(f"          max SPL @1m {fq:>3} Hz: {mxv[k]:5.1f} dB")
        else:
            print(f"  VENTED  Vb={vbv:.2f} L Fb={fbv:.1f} Hz: no round port fits under the "
                  f"speed/length limits")
    return d


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--driver", default=None, help="key from DRIVERS (default: all)")
    ap.add_argument("--vb", type=float, help="net box volume, litres")
    ap.add_argument("--vented", action="store_true")
    ap.add_argument("--fb", type=float, help="vent tuning, Hz")
    ap.add_argument("--port-d", type=float, help="port diameter, mm")
    ap.add_argument("--fill", type=float, default=1.0,
                    help="stuffing volume factor (1.0 none, ~1.1-1.2 loose polyfill)")
    ap.add_argument("--vb-max", type=float, default=3.5,
                    help="largest net volume the vented search may use, litres")
    ap.add_argument("--plot", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--head-mass", type=float, default=0.13, help="kg on isolators")
    args = ap.parse_args()

    if args.list:
        for k, v in DRIVERS.items():
            print(f"{k:12s} {v['name']}")
        return
    f = np.logspace(np.log10(20), np.log10(20000), 1200)
    keys = [args.driver] if args.driver else list(DRIVERS)
    for k in keys:
        if k not in DRIVERS:
            sys.exit(f"unknown driver {k}; use --list")
        report(k, args, f)

    print("=" * 78)
    print("Head isolators (4x TPU spoke springs, 3 spokes each, w2.5 t1.0 L5.5 mm):")
    for e, k, fn, sag in isolator_report(mass_kg=args.head_mass):
        print(f"  E={e:>3} MPa: k={k:7.0f} N/m  f_n={fn:5.1f} Hz  static sag={sag:.2f} mm  "
              f"-> isolation above ~{fn*1.41:.0f} Hz, {20*math.log10(((500/fn)**2)-1):.0f} dB at 500 Hz")
    print("\n2-way reference only (not used in the recommended build):")
    x = lr2_crossover(3000, 4.0, 4.0)
    print(f"  LR2 @3 kHz, 4 ohm: woofer L={x['L_lp_mH']:.2f} mH, C={x['C_lp_uF']:.1f} uF; "
          f"tweeter C={x['C_hp_uF']:.1f} uF, L={x['L_hp_mH']:.2f} mH (+ L-pad, polarity reversed)")
    zb = zobel(3.7, 0.76)
    print(f"  ND105-4 Zobel: R={zb['R']:.1f} ohm, C={zb['C_uF']:.0f} uF")

    if args.plot:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        k = keys[0]
        d = complete_driver(DRIVERS[k])
        vb = args.vb or sealed_vb_for_qtc(d, 0.707)
        fig, ax = plt.subplots(2, 1, figsize=(8, 7), sharex=True)
        r = simulate(d, f, vb, fill_factor=args.fill)
        ax[0].semilogx(f, r["spl"], label=f"sealed {vb:.2f} L")
        bv = best_vented(d, f, args.vb_max)
        if bv:
            rv = simulate(d, f, bv[0], vented=True, fb=bv[1], port_d_mm=30)
            ax[0].semilogx(f, rv["spl"], label=f"vented {bv[0]:.2f} L / {bv[1]:.0f} Hz")
        ax[0].set_ylabel("dB SPL @2.83 V 1 m"); ax[0].grid(True, which="both"); ax[0].legend()
        ax[0].set_ylim(60, 95)
        ax[1].semilogx(f, r["x_pk"] * amp_limits(d)["v_max"] / 2.83, label="sealed")
        ax[1].axhline(d["xmax"], ls="--", c="k", label="Xmax")
        ax[1].set_ylabel("cone excursion mm pk @ Vmax"); ax[1].set_xlabel("Hz")
        ax[1].grid(True, which="both"); ax[1].legend(); ax[1].set_xlim(20, 20000)
        out = f"{__file__.rsplit('/', 1)[0]}/response_{k}.png"
        fig.tight_layout(); fig.savefig(out, dpi=110)
        print("wrote", out)


if __name__ == "__main__":
    main()
