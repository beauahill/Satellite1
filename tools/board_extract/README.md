# Board data extraction

These scripts pulled every Satellite1 dimension used in `cad/enclosure.py` from FPH's own STEP files.
Clone the upstream repos first:

    git clone --depth 1 https://github.com/FutureProofHomes/Satellite1-Hardware
    git clone --depth 1 https://github.com/FutureProofHomes/Satellite1-Enclosures

| script | what it prints |
|---|---|
| `step_names.py <step>` | every component's reference, footprint, and bounding box (e.g. MK1-4, J2/J4/J5, SW1-4, LEDs) |
| `pcb_holes.py <step> <cx> <cy>` | PCB outline (circle + flat) and all holes relative to (cx, cy); rev6.1 uses `150 -101` |
| `mic_port.py <step>` | acoustic port circles on top of each MEMS mic |
| `circles.py <step> [rmin]` | circular features of an enclosure part (OEM posts, driver cutouts, mic holes) |
| `oem_bay_depth.py <OEM STEP dir>` | clear depth under the HAT in FPH's Sat1.1 enclosure |

Run them with CadQuery installed: `python -I script.py ...`.
