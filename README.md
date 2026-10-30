# Satellite1 shelf speaker: single full-range, sealed, floating mic head

A 3D-printable enclosure for the FutureProofHomes Satellite1 PCB dev kit (HAT rev6.1 / R2025.03.18 + Core rev5.1). It uses one Dayton RS100-4 4" full-range driver in a 1.8 L sealed box. The board sits in a "head" that floats on TPU springs above the speaker chamber.

```
acoustics/box_design.py      Thiele/Small simulator: sealed/vented, F3, excursion, port speed, amp limits
acoustics/response_RS100-4.png
cad/enclosure.py             parametric CadQuery model (all key dimensions at the top), exports STL + STEP
cad/render.py                renders cad/out/render*.png
cad/out/                     print-ready STLs (print orientation), step/ per-part STEP (assembled position), assembly.step
tools/board_extract/         scripts that pulled every board dimension out of FPH's STEP files
```

Rebuild everything:

```bash
pip install cadquery numpy matplotlib
python3 acoustics/box_design.py                       # all drivers
python3 acoustics/box_design.py --driver RS100-4 --vb 1.8 --fill 1.1 --plot
python3 cad/enclosure.py                              # STLs + STEP into cad/out
python3 cad/enclosure.py --check path/to/rev6.1hat3D.step   # interference check vs FPH HAT model
```

---

## 1. Board facts (from FPH sources, not guessed)

Sources:
- [Satellite1-Hardware](https://github.com/FutureProofHomes/Satellite1-Hardware): `hat/rev6.1hat3D.step`, `hat/rev6.1hatSCH.pdf`, `core/rev5.1core3D.step`.
- [Satellite1-Enclosures](https://github.com/FutureProofHomes/Satellite1-Enclosures): `assets/Hat R2025.03.18.step`, plus the OEM Sat1.1 Smart Speaker STEP files.
- [Satellite1-ESPHome](https://github.com/FutureProofHomes/Satellite1-ESPHome) firmware.
- [Documentation](https://github.com/FutureProofHomes/Documentation), the source of docs.futureproofhomes.net. The live site was blocked from this environment, so I read the docs repo instead.

**The HAT is not an 88 × 88 mm square.** It is a **Ø88.0 mm circle with one flat edge 42.0 mm from the centre**. The flat edge carries the I/O. 88 × 88 (well, 88 × 86) is only its bounding box. All coordinates below are relative to the circle centre, with +y toward the flat (I/O) edge. The OEM enclosure uses the same frame.

| Item | Value | Where it came from |
|---|---|---|
| PCB | Ø88 circle, flat at y = +42, 1.51 mm (rev6.1) / 1.60 mm (R2025) | PCB solid in both STEPs |
| Mounting holes (used) | 4 × Ø3.2 at (±29, −24.5) and (±29, +24.5) | PCB holes; matches the FPH OEM Sat1.1 enclosure's 4 posts |
| Spare holes | 2 × Ø3.2 at (±29, −1.5) | PCB holes |
| Mics MK1–MK4 | CUI CMM-4030DT top-port. Ports Ø0.65 at (0, +35.5), (+35.5, 0), (0, −35.5), (−35.5, 0). Package top 1.23 mm above PCB | Mic solids in STEP; the OEM top plate has Ø1.56 holes at the same 4 points |
| LED ring | 24 LEDs on r = 41.0 mm, 15° pitch, first at 90° | 24 identical parts in STEP; OEM diffuser annulus Ø79.7–84.3 |
| Buttons SW1–4 | 6 × 6 tact at (−16, 0), (0, +16), (+16, 0), (0, −16); top 5.0 mm above PCB | STEP, OEM top plate |
| Sensors | U4 LTR-303 lux at (+10, −33); U12 temp/humidity at (−10, −33) | STEP, OEM top plate holes |
| USB-C J5 / J2 | Bottom-side, centred x = −13.5 / +13.5, mouth at y = 40.2, body z −3.26…+1.02 from PCB bottom | STEP. The docs say power must go into the port silk-labelled **CORE/ESP** |
| 3.5 mm jack | Bottom-side, x = 0, protrudes to y = 43.23 (1.2 mm past the flat edge) | STEP |
| Speaker connector J4 | 2-pin 2.5 mm (JST-XH-compatible), bottom side, centred (−34.9, +10.0) | STEP, docs |
| Core stack below HAT | ≈10 mm. FPH's OEM enclosure leaves 7.1 mm under the HAT, 8.6 mm in a central Ø60 pocket | Probed from the OEM chamber STEP (`tools/board_extract/oem_bay_depth.py`) |
| Amplifier | **TI TAS2780RYAR (IC1), mono BTL class-D**. PVDD = USB-C VBUS. Firmware requests a **20 V** PD contract | Schematic rev6.1; `config/satellite1.base.yaml` (`fusb302b: request_voltage: 20`) |
| Amp rating | 25 W into 4 Ω at 18 V, 1 % THD+N (30 W at 10 %). Min load 3.2 Ω. PVDD up to ~23–24 V | [TI TAS2780](https://www.ti.com/product/TAS2780) via search (ti.com itself was blocked here) |
| Gain ceiling | `AMP_LEVEL` 11–21 dBV full scale, so at most **11.2 Vrms**. Selectable in the firmware developer config | `esphome/components/tas2780/tas2780.cpp` |
| Mono or stereo | **Mono to the speaker.** I2S is stereo, but the TAS2780 takes one TDM slot. The 3.5 mm line out (PCM5122) is stereo | firmware `speaker.yaml`, `tas2780.cpp` |
| Supply | FPH recommends a 30 W USB-C PD adapter; under-powering causes distortion | docs FAQ |

`cad/enclosure.py --check` loads FPH's HAT STEP, places it in the head, and intersects every component with the head and button caps. Result: **no interference**. A deliberately broken copy, with the board pushed 1 mm into the rear wall, does report interference, so the check is live.

## 2. What FPH did in the Sat1.1 Smart Speaker, and why I went the other way

The FPH kit pairs an LG 3" woofer (MLW78-F4-R6015, 15 W, 4 Ω, Ø71 cutout) with an LG 1.2" tweeter (MLT20-F4-S4830, Ø36 cutout). A generic passive 2-way crossover with bass/treble boost jumpers sits between them. The 110 × 110 × ~182 mm PETG box is **ported**: a rear port (Ø20 mm with a Ø30 mm flared mouth) about 19 mm above the base, as far from the mics as the box allows.

Their stated reasons are sound quality, compatibility with the amp and crossover, and reliable bulk supply. A tweeter also gets a 3" woofer's beaming top end back for a commercial product. FPH's own docs warn that *"at full volume, the wake word may not be heard perfectly"*, that it depends on the enclosure being airtight and on a non-vibrating surface, and that the cause is *"vibrations traveling through the enclosure to the microphones."*

**My call: one 4" full-range driver in a sealed box.**

- **Voice pickup comes first.** The XMOS AEC cancels the *linear* echo of the music well. What breaks wake-word detection under music is energy the AEC can't model: port chuffing and port pipe resonance, panel and part rattles, structure-borne vibration into the mic packages, and cone distortion. Here's how each is handled:
  - **Port noise is gone entirely.** For this driver, a shelf-sized ported box needs a 30 mm × 144 mm port. It would hit 43 m/s (12.7 % of the speed of sound) at full drive, and its pipe resonance lands at about 1 kHz, inside the speech band (`box_design.py --vented --vb 3.0 --fb 65 --port-d 30`). It also wouldn't fit straight in the box.
  - **Fewer things can buzz.** No crossover board, inductor or capacitors are screwed to the enclosure, and there's no tweeter faceplate.
  - **One source.** A single source gives one short, clean echo path. There's no crossover overlap in the 2–4 kHz region where wake-word energy lives.
  - **Mechanical isolation.** The mic board is isolated by TPU springs (section 5), and each mic port is gasket-sealed to its own short hole in the top plate.
- **Amp power doesn't favour 2-way.** At about 11 Vrms the TAS2780 is limited by its gain ceiling, not by PVDD. A passive crossover plus tweeter L-pad would burn part of that headroom.
- **Budget.** All the money goes into one better driver instead of two cheaper ones plus crossover parts.
- **What you give up.** A 4" cone narrows above roughly 4–5 kHz, so treble is best roughly on-axis. On a shelf, aimed at the bed, that's fine.

## 3. Driver shortlist

T/S values come from vendor or retailer listings, linked at the bottom. Values marked * are derived by the script from the other parameters.

| | **Dayton RS100-4** (pick) | Dayton ND105-4 (+ tweeter, 2-way) | Peerless TG9FD10-04 (budget) |
|---|---|---|---|
| Type | 4" full-range, 4 Ω | 4" aluminium midbass, 4 Ω | 3.5" glass-fibre full-range, 4 Ω |
| Fs / Qts / Vas | 84.8 Hz / 0.52 / 1.45 L | 78.7 Hz / 0.61 / 1.95 L | 113 Hz / 0.83 / 0.98 L (sources disagree: 113 vs 130 Hz) |
| Qms / Qes | 2.55 / 0.66 | 7.42 / 0.66 | 3.0 / 1.14 |
| Re / Bl / Mms | 3.0 Ω / 3.18 Tm / 4.3 g | 3.7 Ω / 4.68* / 7.9 g* | 3.25 Ω / 2.4 Tm / 2.83 g |
| Sd / Xmax | 35.3 cm² / 4.0 mm | 51.5 cm² / 4.0 mm | 31* cm² / 3.9 mm |
| Sensitivity (2.83 V / 1 m) | 87.5 dB | 86.8 dB | 84 dB |
| Power | 30 W RMS | 30 W RMS | 10 W |
| Impedance vs TAS2780 (3.2 Ω min) | |Z|min ≈ 3.0 Ω, marginal (see note) | 3.75 Ω, OK | 3.27 Ω, OK |
| Sealed box | **1.8 L: Qtc 0.69, F3 114 Hz, F6 86 Hz** | 3.5 L: F3 86 Hz (box ~2× bigger) | 1.7 L: Qtc 1.03, peaky, F3 114 Hz |
| Max SPL at 1 m, 80 Hz (Xmax-limited) | 87.7 dB | 91.0 dB | 85.2 dB |
| Price | ~$35–49 (Parts Express #295-378) | ~$33–41, plus ~$35–45 for tweeter and crossover | ~$13–20 |
| Fits $60–80/unit? | Yes, ~$45–60 all-in | At the limit | Yes, but it's the weakest |

**Why the RS100-4:**
- Highest sensitivity of the three, and a full-range response, so no crossover.
- Its Xmax is the same as the ND105-4's.
- At about 9.6 Vrms continuous from a 30 W PD supply it reaches roughly 98 dB at 1 m in the midrange, which is plenty for a 350 sq ft bedroom.
- FPH's earlier Squircle and Cylindrical enclosures listed its 3" sibling, the RS75-4, so this driver family is already proven with this amp.
- Its 51 mm depth and 98 mm OD keep the box slim.

I ruled out the Tang Band W4-1720: better bass (Fs 60 Hz, Qts 0.42) but about $110 and 82–92 mm deep.

**Impedance note.** The RS100-4's Re of 3.0 Ω is a hair under TI's 3.2 Ω minimum load. In practice, 4 Ω-nominal drivers are what this amp is rated for, and FPH ships 4 Ω drivers. At the moderate volume this design targets, the current stays well inside limits. If you want margin, the RS100-8 has the same frame. Add its T/S to `DRIVERS` and rerun the script; expect about 3 dB less maximum SPL.

## 4. Box alignment

Run `python3 acoustics/box_design.py --driver RS100-4 --vb 1.8 --fill 1.1`.

The script is a full lumped-element model, not just the rule-of-thumb formulas:
- electrical: Re + jωLe
- mechanical: Rms, Mms, Cms
- acoustic: Cab, plus a port mass and leakage for vented boxes

It reports Qtc, Fc, F3/F6, cone excursion, max SPL limited by both voltage and Xmax, port length, port air speed, port pipe resonance, and amp and supply ceilings.

| | Sealed (built) | Vented (rejected) |
|---|---|---|
| Net volume | 1.80 L (driver 0.10 L and damping 0.10 L added on top; cavity solved exactly in CAD) | 3.0 L |
| Alignment | Qtc 0.69 (0.68 with light polyfill), Fc 112 Hz | Fb 65 Hz |
| F3 / F6 | 114 Hz / 86 Hz (anechoic; shelf/wall gain adds several dB below ~200 Hz) | 59 Hz |
| Port | none | Ø30 × 144 mm; 43 m/s peak; pipe mode ≈1 kHz |

Sealed F3 hardly moves with box size for this driver: 114 Hz at 1.8, 2.4 or 3.0 L. So the box was kept at the Qtc ≈ 0.7 volume to stay compact.

**Excursion.** At the 11 Vrms ceiling the cone passes Xmax below about 150 Hz (see `acoustics/response_RS100-4.png`). For reliable wake words, keep the cone in its linear range:
- Cap the maximum volume. Use `vol_range_max` in the Satellite1 developer settings, or the player volume limit in Music Assistant.
- If your Music Assistant DSP offers a high-pass filter, add a 12 dB/oct one at about 70–80 Hz.
- Don't add bass boost.

At moderate listening levels (−10 dB from max) peak excursion is about 2.4 mm, well inside Xmax.

## 5. Enclosure (cad/enclosure.py)

Overall size: **130 W × 94 D × 242 H mm**. The driver centre is 64 mm above the table, which puts it **178 mm below the mic plane**.

This is 10 mm taller than the 232 mm I first quoted. The wall damping in section 6 displaces about 0.10 L, and the chamber grows to keep 1.8 L of air. If you skip the foam and butyl, set `DAMPING_DISP_L = 0` and it drops back to 232 mm.

### Output files

| Path | Contents |
|---|---|
| `cad/out/*.stl` | One STL per part, already in print orientation |
| `cad/out/step/*.step` | One STEP per part in **assembled position**, so they line up when you import them together into Fusion 360 |
| `cad/out/assembly.step` | Everything, including all 4 button caps, isolators and mic gaskets, as one assembly |

Every STEP re-imports as a single valid solid.

### Parts

| Part | Qty | Material | Print orientation | Notes |
|---|---|---|---|---|
| `chamber` | 1 | PETG-HF (or ASA) | lying on its back | 4 mm walls, 5 mm floor, 10 mm roof for mass and isolator sockets. U-brace above the driver. Wire gland, 4 bumper recesses |
| `baffle` | 1 | PETG-HF | front face on bed | 8 mm thick. Ø77.2 cutout with rear chamfer, 6 pilot holes (Ø2.5 × 7 mm deep) on a Ø89.9 bolt circle. Glue tongue enters the chamber 4 mm |
| `head` | 1 | PETG-HF or matte PLA | top face on bed | Carries the HAT on 4 M3 bosses. Mic bosses with Ø1.0 holes, LED window with 4 bridges, button and sensor holes, USB-C ×2 and jack cutouts. 4 posts with Ø4 pins |
| `diffuser` | 1 | translucent PETG or white PLA | visible face on bed | Drops into the LED counterbore and slots |
| `button_cap` | 4 | same as head | top down | Captured between top plate and switch, 0.2 mm pre-travel gap |
| `isolator` | 4 | TPU 95A HF | flat, spokes on bed | Ring sits in the roof socket; hub carries the head pin; 3 spokes are the springs |
| `mic_gasket` | 4 | TPU 95A, or punch from 1.5 mm closed-cell foam | flat | OD 2.8 / ID 1.4. Seals each mic port to its hole |
| `driver_gasket` | 1 | TPU 95A, or the gasket that ships with the driver | flat | |

Every part fits the **H2S build volume (340 × 320 × 340 mm)**. The largest is the chamber at 130 × 218 × 86 mm. Nothing needs supports; the overhangs that remain are 45° chamfers and short bridges (I/O cutouts, gland, sockets).

### How the mics stay separated from the driver

1. **The driver** bolts to an 8 mm baffle through a gasket. The baffle is glued into a rebate on a heavy, damped box (10 mm roof, U-brace), and the box stands on bumpers.
2. **The air volumes are separate.**
   - The driver cavity is sealed under the 10 mm roof. The only opening, the wire gland, is sealed with silicone.
   - The board sits in the head, which is a separate space open to the room only through the I/O cutouts and the shadow gap.
3. **The head never touches the box.** It rests on four TPU spoke springs, with a visible 1.5 mm "shadow line" all round.
   - With 95A TPU (E ≈ 26 MPa) and a head mass of about 130 g, the vertical resonance is about **30 Hz**, so isolation starts at about 43 Hz. It is about −49 dB at 500 Hz.
   - Lateral stiffness is higher. My hand estimate is around 100 Hz; the script doesn't compute it. That still isolates the speech band.
   - Run `box_design.py` to see this for 12, 26 and 45 MPa TPU.
4. **The HAT screws to the head only.** The speaker wire is the only link to the box, and it's flexible. Leave it slack.
5. **Each mic port** is sealed by a TPU or foam ring to its own Ø1.0 mm hole.
   - The hole runs through the mic boss and the top plate, about 7.6 mm including the gasket.
   - Its first resonance is about 10 kHz, above the 8 kHz band a 16 kHz voice pipeline uses.
   - The inside of the head isn't open to the mic.
6. **Sealed box: no port** anywhere near the head.

### Key parameters (top of `enclosure.py`)

| Parameter | What it controls |
|---|---|
| `V_NET_L`, `DRIVER_DISP_L`, `DAMPING_DISP_L` | Target net air volume. The cavity height is solved to hit it, after subtracting the brace, tongue, driver and damping |
| `W`, `D`, `WALL`, `WALL_BOT`, `TOP_WALL`, `BAFFLE_T` | Shell size and wall thicknesses. `D` = 94 keeps the LED ring within 2 mm of the top centre, since the HAT's I/O edge must touch the rear wall |
| `DRIVER_*`, `FLANGE_RECESS`, `CUTOUT_REAR_CHAMFER` | Driver cutout, bolt circle, depth, optional flush mount |
| `HAT_*`, `MIC_PORTS`, `LED_*`, `BUTTONS`, `SENSOR_HOLES`, `USB_C`, `JACK` | Board data from section 1 |
| `BAY_CLEAR`, `BELOW_PCB_STACK`, `GAP_TOP`, `IO_GAP` | Board placement |
| `MIC_HOLE_D`, `MIC_BOSS_D`, `MIC_GASKET_*` | Mic openings and seals |
| `LED_SLOT_*`, `LED_CBORE_*`, `LED_BRIDGE_*` | LED window |
| `ISO_*`, `PIN_D`, `POST_D`, `SHADOW_GAP` | Isolation between head and chamber |
| `PORT_ENABLE`, `PORT_*` | Vented option. Off by default; asserts if the port won't fit |
| `GLAND_XY`, `GLAND_D` | Speaker-wire exit |
| `BUILD_VOL` | Printer volume used by the fit check |

## 6. Print settings and damping (stiff, dead cabinet)

### Material choice

- **PETG-HF for the chamber and baffle.** It has more internal damping than PLA, so it rings less when tapped. It won't creep or soften in a sunny room the way PLA can, and it bonds well with epoxy.
- **ASA** is an equally good alternative if you print it enclosed.
- **Avoid PLA for the cabinet.** It is stiffer but rings more, and it creeps under the driver screws.

### Slicer settings (Bambu Studio, 0.4 mm nozzle)

| Part | Layer | Walls | Top / bottom | Infill | Notes |
|---|---|---|---|---|---|
| chamber | 0.20 mm | 6 (≈2.5 mm) | 6 / 6 | 40 % gyroid | Gyroid's curved cells break up panel modes. Wall order inner/outer/inner for stiffness. 5 mm brim, since it's a tall print on a small base. Slow outer walls for appearance |
| baffle | 0.20 mm | 6 | 6 / 6 | **100 %** | Most mass and stiffness exactly where the driver pushes. Front face on a smooth or textured PEI plate for the visible finish |
| head | 0.16 mm | 3 | 5 / 5 | 25 % gyroid | Visible part. Ironing on the top face optional |
| button caps | 0.12 mm | 3 | — | 100 % | |
| diffuser | 0.16 mm | 2 | — | 100 % | Translucent PETG. A 0.12 mm first layer gives a frosted look |
| isolators, gaskets | 0.20 mm | 2 | — | 100 % | TPU 95A HF, ≤ 3 mm³/s, no cooling fan for the first 2 layers, glue stick on the plate |

Filament per unit: about **650–750 g PETG** (chamber ~350 g, baffle ~240 g, head ~60 g), **~10 g TPU**, **~3 g translucent**. Two speakers come to roughly 1.5 kg of PETG, so buy two 1 kg spools.

### Where the damping goes (inside the chamber)

| Location | Material | Why |
|---|---|---|
| **Back wall**, full panel above the bottom 20 mm | ½" open-cell foam with PSA (Sonic Barrier 260-520). Cut 120 × 175 mm | The back wall is directly behind the cone, 39 mm away. The foam absorbs the back wave before it reflects through the cone, which would otherwise colour the 1–3 kHz voice band |
| **Both side walls**, centred | 2 mm butyl/foil sheet (one 10 × 10" sheet per side, trimmed to about 75 × 150 mm) | Constrained-layer damping. Kills the largest-panel modes so the box doesn't buzz. That buzz is what reaches the mics as structure-borne noise |
| **Cavity fill** | 10–15 g loose polyester fibre (Acousta-Stuf 260-317), fluffed | Lowers the effective Qtc slightly (fill ×1.1 in the script) and damps standing waves along the 200 mm height |
| **Roof underside** | none needed | The 10 mm roof is already stiff |
| **Baffle** | none | 100 % infill |
| **Head** | optional: one strip of felt or foam on the inside of the top plate, away from mic bosses and LED window | Only if you hear the head ring when tapped |

Don't put fill or foam in front of the cone or against the back of the driver magnet: keep 10 mm clear. Don't put any of it in the head near the mic bosses.

## 7. Bill of materials (per unit, excluding the dev kit)

Prices are from search snapshots; check stock before ordering. Links that aren't to a specific product page are marked.

| # | Qty | Item | Part number | Link | Approx. |
|---|---|---|---|---|---|
| 1 | 1 | Dayton Audio RS100-4 4" Reference full-range, 4 Ω | Parts Express **295-378** | [Parts Express](https://www.parts-express.com/Dayton-Audio-RS100-4-4-Reference-Full-Range-Driver-4-Ohm-295-378) | $35–49 |
| 2 | ~15 g | Acousta-Stuf polyfill, 1 lb bag (enough for many speakers) | Parts Express **260-317** | [Parts Express](https://parts-express.com/Acousta-Stuf-Polyfill-1-lb.-Bag-260-317) | $1 (bag ~$12) |
| 3 | 1 piece | Sonic Barrier ½" acoustic foam with PSA, 18 × 24" (one sheet does ~12 speakers) | Parts Express **260-520** | [Parts Express](https://parts-express.com/Sonic-Barrier-1-2-Acoustic-Foam-w-PSA-18-x-24-260-520) | $1 (sheet ~$11) |
| 4 | 2 sheets | Butyl/foil damping sheet, 10 × 10" (kit has 2) | Rockford Fosgate **RFDS-SPEAKER** | [Rockford Fosgate](https://rockfordfosgate.com/products/details/rfds-speaker) | ~$15/kit |
| 5 | 6 | Driver screws: M3 × 12 pan head, thread-forming for plastic, stainless | McMaster **96817A912** | [McMaster](https://www.mcmaster.com/product/96817A912/) | ~$1 |
| 6 | 4 | HAT screws: M3 × 8 pan head, thread-forming for plastic (45°, six-lobe) | Fastener Superstore **547301** (zinc) | [Fastener Superstore](https://www.fastenersuperstore.com/products/547301/thread-forming-screws) | ~$1 |
| 7 | 4 | Feet: 3M Bumpon SJ5312, Ø12.7 × 3.6 mm, polyurethane, clear | 3M **SJ5312** (DigiKey 3866068) | [DigiKey](https://www.digikey.com/en/products/detail/3m/SJ5312/3866068) (URL built from DigiKey's part ID; only a regional DigiKey page turned up in search) | ~$1 |
| 8 | 0.4 m | 20 AWG 2-conductor speaker wire | Encore Wire **C1360.21.90** (DigiKey 5126287, 50 ft) | [DigiKey](https://www.digikey.com.au/en/products/detail/encore-wire/C1360-21-90/5126287) | ~$1 |
| 9 | 1 | JST-XH 2-pin pigtail for the HAT speaker connector | as recommended by FPH (no part number) | [FPH-recommended listing](https://amzn.to/4ly9LDA) | ~$1 |
| 10 | — | 2-part epoxy (any 5-minute epoxy) for the baffle joint | generic | — | ~$1 |
| 11 | — | Neutral-cure silicone for the wire gland | generic | — | <$1 |
| 12 | ~700 g | Bambu PETG-HF, 1.75 mm (chamber, baffle, head, caps) | Bambu PETG-HF | [retailer listing](https://3dprintingcanada.com/fr/products/grey-bambu-lab-petg-hf-filament-1-75mm-1-kg?notify=1) | ~$14 |
| 13 | ~10 g | Bambu TPU 95A HF (isolators, gaskets) | SKU BBL-U00-W0-1.75-1000-SPL | [Stemfinity](https://stemfinity.com/products/bambu-lab-tpu-95a-hf-1) | ~$0.5 |
| 14 | ~3 g | Translucent PETG (diffuser) | any | — | — |
| | | **Total per unit** | | | **≈ $60–75** (inside your $60–80) |

The shared-sheet items (polyfill, foam, butyl) are counted at the per-unit share; buying them for two speakers costs about $40 up front.

Before ordering screws, measure the RS100-4 flange holes. The baffle pilots are sized for M3 thread-forming (Ø2.5 mm, 7 mm deep). If the flange and gasket together are thinner than 5 mm, an M3 × 12 screw will bottom out; use M3 × 10 instead (same series).

## 8. Assembly

**Chamber**
1. Test-fit the baffle on the chamber dry. Lightly sand both glue faces with 120 grit and wipe with isopropyl alcohol.
2. Damping, before closing the box:
   - Stick the ½" foam on the back wall.
   - Stick butyl on both side walls; roll it down firmly.
3. Glue the baffle tongue into the chamber rebate with epoxy around the entire rim. Clamp or weight it face-down on a flat surface. This joint must be airtight. Let it cure fully.

**Driver and wiring**

4. Feed 40 cm of speaker wire up through the roof gland from inside, via the driver hole. Seal the gland from outside with silicone.
5. Solder the wire to the driver tabs. Red to the + tab.
6. Loosely add 10–15 g of polyfill through the driver hole, keeping it 10 mm clear of the magnet.
7. Fit the driver gasket and the driver. Six screws, tightened in a star pattern until snug; don't strip the plastic.
8. **Leak test.** Gently press the cone in with two fingers on the dust-cap edge. It should spring back slowly, which means the box is sealed. If it returns instantly, find the leak at the baffle joint or the gland.

**Base and isolators**

9. Press the 4 isolators into the roof sockets, spokes down. Stick the 4 bumpers into the base recesses.

**Head** (on the bench, upside down)

10. Snap in the diffuser and the 4 button caps.
11. Stick a mic gasket centred on each mic boss.
12. Plug the Core into the HAT. Lay the HAT face-down into the head with the flat I/O edge against the rear cutouts. Fasten it with 4 × M3 × 8 thread-forming screws, snug only.
13. Press each button and check it clicks.
14. On a Sat1.1 kit, stick the external WiFi antenna to the inside of a head side wall. It's plastic, so there's no shielding. Clip its IPEX connector to the Core.

**Final assembly**

15. Crimp the JST-XH 2-pin connector onto the speaker wire. Plug it into J4 on the underside of the HAT; check polarity against the HAT silkscreen.
16. Lower the head onto the isolators, pins into the hubs, rear I/O at the back. Check the 1.5 mm shadow gap is even all round; nothing may touch.
17. Power the **CORE/ESP** USB-C port from a 30 W USB-C PD adapter.

**Tuning**

18. Cap the maximum volume (`vol_range_max` / Music Assistant player limit) and add a 70–80 Hz high-pass if your Music Assistant DSP offers one.
19. Then test: play music at your normal level and say the wake word from across the room.

## 9. Crossover

None. It's a single full-range driver. If you later build the 2-way ND105-4 variant, `box_design.py` prints these starting points:
- LR2 at 3 kHz into 4 Ω: woofer 0.42 mH + 6.6 µF; tweeter 6.6 µF + 0.42 mH, wired in reverse polarity, plus an L-pad.
- A Zobel across the ND105-4: 4.6 Ω + 56 µF, to flatten its 0.76 mH Le.

Treat these as a start only. A 2-way needs measured responses (REW plus a calibrated mic) to finish.

## 10. Open items

1. **Core stack height.** You confirmed the 10 mm assumption. The bay leaves 14 mm. If a measurement ever shows more than 12 mm, raise `BAY_CLEAR`.
2. **Board revision.** The public STEP is HAT rev6.1 (Public Batch #2). Sat1.1 kits (external antenna, Feb 2026) still mount on the same 4 posts in FPH's OEM Sat1.1 enclosure. Check that your HAT's mounting holes and I/O match before printing the head.
3. **Driver mechanicals.** Check the RS100-4 bolt circle (89.9 mm is a third-party figure), its hole size, and its flange thickness. Set `DRIVER_HOLE_ANGLE0` to your driver's hole pattern and pick M3 × 10 or × 12 screws (section 7). Print the baffle first (about 3 h) and test-fit before printing the chamber.
4. **Le.** The RS100-4's voice-coil inductance wasn't in the sources I could reach, so the script assumes 0.1 mH. That only affects the simulated slope above about 2 kHz.
5. **Network.** docs.futureproofhomes.net, ti.com and loudspeakerdatabase.com were blocked from this environment. Board data came from FPH's GitHub repos (including the docs source repo). Amp and driver specs came from search results, which are cited.

## Sources

- FPH GitHub: [Satellite1-Hardware](https://github.com/FutureProofHomes/Satellite1-Hardware), [Satellite1-Enclosures](https://github.com/FutureProofHomes/Satellite1-Enclosures), [Satellite1-ESPHome](https://github.com/FutureProofHomes/Satellite1-ESPHome), [Documentation](https://github.com/FutureProofHomes/Documentation) (`docs/satellite1-smart-speaker.md`, `satellite1-faqs.md`, `satellite1-squircle-enclosures.md`, `satellite1-cylindrical-enclosure.md`)
- TAS2780: [TI product page](https://www.ti.com/product/TAS2780), [TI datasheet](https://ti.com/lit/gpn/tas2780), [Mouser](https://www.mouser.ca/ti-tas2780-amps)
- RS100-4: [Dayton Audio](https://www.daytonaudio.com/product/89/rs100-4-4-reference-full-range-driver-4-ohm), [Parts Express](https://www.parts-express.com/Dayton-Audio-RS100-4-4-Reference-Full-Range-Driver-4-Ohm-295-378), [SpeakerBoxLite](https://speakerboxlite.com/subwoofers/dayton-audio-rs100-4/specifications), [loudspeakerdatabase](https://loudspeakerdatabase.com/Dayton/RS100-4), [diyaudiocart](https://diyaudiocart.com/product/dayton-audio-rs100-4-4-reference-full-range-driver-4-ohm)
- ND105-4: [Dayton Audio](https://www.daytonaudio.com/product/55/nd105-4-4-aluminum-cone-midbass-driver-4-ohm), [Reverb listing](https://reverb.com/item/41526170-dayton-audio-nd105-4-4-aluminum-cone-midbass-neo-driver-4-ohm), [loudspeakerdatabase](https://loudspeakerdatabase.com/Dayton/ND105-4)
- TG9FD10-04: [loudspeakerdatabase](https://loudspeakerdatabase.com/Peerless/TG9FD10-04), [LCSC](https://www.lcsc.com/product-detail/C6880843.html), [toutlehautparleur](https://en.toutlehautparleur.com/fullrange-speaker-peerless-tg9fd10-04-4-ohm-3-3-inch.html)
- W4-1720 (rejected): [Parts Express](https://parts-express.com/Tang-Band-W4-1720-4-Underhung-Midbass-Driver-264-872), [rumoh.eu](https://www.rumoh.eu/speakers/woofer/woofer-4-inch/2704/tangband-w4-1720)
- BOM: [Acousta-Stuf 260-317](https://parts-express.com/Acousta-Stuf-Polyfill-1-lb.-Bag-260-317), [Sonic Barrier 260-520](https://parts-express.com/Sonic-Barrier-1-2-Acoustic-Foam-w-PSA-18-x-24-260-520), [Rockford Fosgate RFDS-SPEAKER](https://rockfordfosgate.com/products/details/rfds-speaker), [McMaster 96817A912](https://www.mcmaster.com/product/96817A912/), [Fastener Superstore 547301](https://www.fastenersuperstore.com/products/547301/thread-forming-screws), [3M SJ5312 listing](https://www.hillas.com/Categories/Cylindrical/3M-Bumpon-Blister-Pack-SJ5312-Clear-0-500-in-x-0-140-in-18-blisters-per-case-56-Bumpons-per-blis.html), [Encore C1360.21.90](https://www.digikey.com.au/en/products/detail/encore-wire/C1360-21-90/5126287), [Bambu TPU 95A HF](https://stemfinity.com/products/bambu-lab-tpu-95a-hf-1), [Bambu PETG-HF](https://3dprintingcanada.com/fr/products/grey-bambu-lab-petg-hf-filament-1-75mm-1-kg?notify=1)
- Bambu Lab H2S build volume: [3D Printing Industry](https://3dprintingindustry.com/news/bambu-lab-launches-the-new-h2s-technical-specifications-and-pricing-243603/), [Core Electronics](https://core-electronics.com.au/bambu-lab-h2s-3d-printer-machine-only.html)
