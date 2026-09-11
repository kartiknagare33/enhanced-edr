# eEDR PROJECT — COMPLETE HANDOFF / CONTINUATION BRIEF

> Paste this whole document into a new AI chat to continue the project seamlessly.
> It contains the full context: what the project is, every design decision, all
> technical specifics (pin maps, wiring, BOMs, values), what has been built, the
> current status, and what remains.

---

## 0. HOW TO USE THIS DOC
I'm a final-year engineering student building the project below. A previous AI
assistant helped me design and document it. This brief is the full state of the
project. Continue helping me from here. Key preferences: concise answers, lead with
the answer, explain hardware simply (I'm still learning electronics).

---

## 1. PROJECT IDENTITY
- **Title:** Enhanced Automobile Event Data Recorder (eEDR) — a forensic-grade crash "black box" for vehicles.
- **Type:** Final-year major project, Semester 6.
- **Institute:** Vivekanand Education Society's Institute of Technology (VESIT), Mumbai — autonomous, affiliated to University of Mumbai. Department: EXTC.
- **Team:** Kartik Nagare (Roll 24 / D19A), Jyotiraditya Bhosale (8 / D19A), Prince Eppakayal (13 / D19A).
- **Mentor:** Dr. Nandini Ammanagi, Assistant Professor, EXTC *(designation inferred — verify)*.
- **GitHub:** https://github.com/kartiknagare33/enhanced_edr

## 2. WHAT THE PROJECT DOES (one paragraph)
The eEDR continuously records 40 vehicle parameters at 100 Hz into a rolling 20-second
buffer. On a crash (detected by multiple redundant triggers), it freezes the buffer,
writes the crash-critical data to tamper-evident flash, asserts a hardware write-lock,
and verifies a SHA-256 integrity digest. A dedicated power-survivability stage keeps the
recorder alive after vehicle power is cut, long enough to finish that write+lock.

---

## 3. SYSTEM ARCHITECTURE

**Node A — Vehicle ECU (CAN transmitter)**
- ESP32 DevKit + MCP2515 CAN module (with onboard transceiver).
- Simulates the car's ECU; broadcasts vehicle data frames on the CAN bus.

**Node B — EDR Unit (the recorder)**
- Raspberry Pi 4B (upgraded from 3B).
- Sensors/peripherals: MPU6050 IMU (accel+gyro, I²C), NEO-6M GPS (UART), DS3231 RTC (I²C), W25Q128 SPI flash (tamper-lock storage), MCP2515 CAN module (receives Node A, SPI).
- Receives CAN + reads its own sensors; runs detection, analytics, storage.

**Power Survivability Unit**
- 12 V → buck → Pi (normal). 18650 Li-ion backup via TP4056; boost holds 5 V on power cut.

**Crash-capture sequence:** Detect → Freeze 20 s buffer → Write to flash → Assert write-lock → Verify SHA-256.

**Analysis software** (offline web app) reconstructs and analyses each captured event.

---

## 4. TECHNICAL CONVENTIONS (used everywhere)
- Axes: +x forward, +y left, +z up. Frontal impact → negative accel_x.
- PDOF (principal direction of force) = atan2(-a_y, -a_x), degrees.
- Clock position: 12 = front, 3 = right, 6 = rear, 9 = left.
- Thresholds: crash |a| ≥ 4 g; speed-drop ≥ 2.5 km/h per 10 ms tick; roll ≥ 45°; power-fail < 9 V.
- CSI (Crash Severity Index) = peak_g / 40 × 100.
- Severity: Severe if rollover OR ΔV ≥ 40 km/h; Moderate if ΔV ≥ 16; else Minor.
- 40 parameters tracked total; 28 are "crash-critical" (locked to flash).
- Sampling 100 Hz; buffer 2000 samples = 20 s; +4 s post-trigger capture.

---

## 5. SOFTWARE — WHAT'S BUILT (COMPLETE & TESTED)

### 5a. Python simulation engine  (folder `edr_system/`, also `edr_system.zip`)
- Pure Python standard library, **zero dependencies**. Hardware-abstraction layer (HAL)
  so the identical core runs on PC (simulated) and on the Pi (real sensors).
- **14/14 unit tests pass.** 6 scenarios verified physically correct.
- Structure:
  - `edr/config.py` — thresholds/constants
  - `edr/model.py` — 40-param `EDRSample` dataclass; `CRASH_CRITICAL_PARAMS` (28)
  - `edr/hal/{base.py (DataSource ABC), simulated.py (physics sim), hardware.py (Pi stub)}`
  - `edr/core/{ring_buffer.py, detector.py (4-trigger), analytics.py (CSI/ΔV/PDOF/rollover)}`
  - `edr/storage/{flash.py (SHA-256), sd_logger.py, lock.py}`
  - `edr/recorder.py` — state machine BOOT→MONITORING→CAPTURING→FINALIZING→LOCKED
  - `edr/report.py`, `edr/scenarios.py`, `run.py` (CLI)
  - `tests/`, `README.md`
- Run: `cd edr_system && python run.py list` / `python run.py run frontal_collision` / `python run.py test`
- **Scenarios:** frontal_collision, side_impact_left, rollover, hard_brake, normal_drive, power_loss_during_crash.
- **Verified analysis outputs:**
  - frontal → 30 g, ΔV 21, Moderate, 12 o'clock, HIC 156
  - side (left) → 22 g, 9 o'clock, Left, Minor
  - rollover → Severe, 3 o'clock, roll > 45°
  - power-loss → Severe, HIC 142
  - hard_brake & normal_drive → correctly NO event (no false triggers)

### 5b. Forensic Analysis Workstation  (`edr_forensic.html`)
- **Single self-contained HTML file**, no dependencies, runs offline in any browser
  (double-click to open). Same engine logic as the Python core (viva point: "same core").
- **Light/white professional "engineering tool" theme**, Verdana font.
- **10 tabs:**
  1. Overview — accelerometer + velocity oscilloscope with 4 g threshold line
  2. Reconstruction — animated scaled top-down car on a metric grid, speed-coloured trail, velocity + g-force vectors, progressive crumple on impact; scrubbable replay
  3. Crash Pulse — |a| pulse with ΔV shown as shaded integrated area (∫a·dt)
  4. Biomechanics — real HIC (Head Injury Criterion) from upsampled resultant accel; AIS3+ risk
  5. Kinematics — professional top-down car schematic with deformation zones + PDOF arrow + clock position; ΔV polar vector diagram
  6. Spectrum — radix-2 FFT of the acceleration pulse
  7. Trajectory — GPS lat/lon path with impact marker
  8. Data Frame — all 40 parameters live, grouped
  9. Forensic — SHA-256, write-lock, chain of custody, RE-VERIFY / SIMULATE-TAMPER / EXPORT-REPORT buttons, acquisition timeline
  10. Report — auto-generated worded incident narrative + a 5-frame crash-sequence strip (approach→contact→peak crush→max deform→rest); DOWNLOAD .TXT
- History (context): dashboard → Three.js 3D console (dropped, "game-like") → 3D CAD workstation (dropped) → this 2D forensic workstation (final, best).

---

## 6. HARDWARE — POWER SURVIVABILITY UNIT

### 6a. Design evolution (IMPORTANT — current design is the 18650 one)
- **Original:** supercapacitor bank — 3× 2.7 V 10 F supercaps in series (~5 V), 3× 1 kΩ balancing resistors, 22 Ω 2 W charge-limit resistor, boost regulator.
- **Change 1 — boost swap:** MT3608 was out of stock → switched to **HW-432 (XL6009)** boost. Both are adjustable step-up modules, so it's a drop-in. XL6009 min input ~3.8 V (vs MT3608 ~2 V), so backup time is a bit shorter but still fine.
- **Change 2 — supercaps → battery (CURRENT):** supercaps were costly/unavailable → switched to **one 18650 Li-ion cell (3.7 V) + a protected TP4056 charger**. This *removed* the 3 supercaps, 3 balancing resistors, and the 22 Ω resistor; raised backup from ~2.5 s to tens of minutes (only < 1 s needed); solved availability.

### 6b. Current 18650 circuit — exact wiring
Setpoints (set BEFORE connecting the Pi): **LM2596 buck = 5.3 V, HW-432 boost = 5.1 V.**
(The buck sits higher so the boost stays idle during normal running; on power cut the
boost feeds the rail through diode D2 automatically — no software needed.)

- 12 V(+) → SW1 toggle → F1 fuse (2 A) → D1 (1N5401) anode; D1 cathode = **P12** node.
- 12 V(−) → common **GND**.
- P12 → LM2596 IN+ ; GND → LM2596 IN−.
- LM2596 OUT+ → **RAIL_5V** (Pi 5 V node) ; OUT− → GND.
- RAIL_5V → TP4056 IN+ ; GND → TP4056 IN−.
- TP4056 B+ → 18650(+) ; TP4056 B− → 18650(−).
- TP4056 OUT+ → HW-432 IN+ ; TP4056 OUT− → GND ; HW-432 IN− → GND.
- HW-432 OUT+ → D2 (1N5819 Schottky) anode ; D2 cathode → RAIL_5V ; HW-432 OUT− → GND.
- Power-fail sense: P12 → R1 (10 kΩ) → **NODE_A** → R2 (2.2 kΩ) → GND ; NODE_A → Pi **GPIO17** (physical pin 11).
- Output to Pi: RAIL_5V → Pi 5 V (Pi 4B is **USB-C**, or tap 5 V GPIO pins 2/4); GND → Pi GND.
- Diodes: D1 (1N5401) = reverse-polarity protection; D2 (1N5819 Schottky) = automatic failover.

### 6c. Power unit — components to buy for the 18650 design
- 18650 Li-ion cell, 3.7 V, 2000–2600 mAh (~₹80–150) — buy genuine, ignore fake "9900 mAh".
- 18650 holder, single-cell with leads (~₹15–30).
- **TP4056 WITH protection** (the 6-pad version with DW01 chip) (~₹25–40).
- (Keep from before: LM2596 buck, HW-432/XL6009 boost, 1N5401, 1N5819, 10 kΩ + 2.2 kΩ ¼ W resistors, 2 A fuse+holder, SPST toggle, board, jumpers.)
- **Resistor note:** only the (now-removed) 22 Ω needed 2 W. R1/R2 divider are ordinary ¼ W. Buy a ¼ W assortment kit for the small values.

### 6d. Backup-unit build/test order
1. Set buck to 5.3 V (meter only). 2. Set boost to 5.1 V (feed ~3.7 V in, meter out).
3. Wire input, verify P12 ≈ 12 V. 4. Wire buck, verify RAIL_5V ≈ 5.3 V. 5. Wire TP4056+battery (charge LED lights). 6. Wire boost+D2. 7. Wire divider, verify NODE_A ≈ 2.1 V. 8. THEN connect Pi. 9. Failover test: run Pi, flip SW1 off — Pi should stay up; RAIL_5V holds ~4.8–5.0 V.
> Note: backup time (~2.5 s) is **calculated, not yet measured**. Present as an estimate.

---

## 7. HARDWARE — EDR HAT (Node B sensor board)

### 7a. Form + approach
- A **HAT** that stacks on the Pi 4B's 40-pin header (2×20). Modules mounted on **female headers** (not bare chips). KiCad, 2-layer, ~65×56 mm HAT outline.
- **No level shifter:** run the CAN module at **3.3 V** (avoids the 5 V→3.3 V issue).

### 7b. EDR HAT pin map (Raspberry Pi PHYSICAL pin numbers)
- I²C (MPU6050 + DS3231): SDA = pin 3, SCL = pin 5
- SPI (MCP2515 + W25Q128 share): MOSI = pin 19, MISO = pin 21, SCLK = pin 23
- **Chip-selects (critical, must be separate):** MCP2515 CS = pin 24 (CE0); W25Q128 CS = pin 26 (CE1)
- MCP2515 INT = pin 22
- GPS: Pi RX ← GPS TX = pin 10 ; Pi TX → GPS RX = pin 8
- Power-fail sense (from backup unit) = pin 11 (GPIO17)
- Status LED (optional) = pin 13 (GPIO27)
- Power: 3.3 V = pins 1, 17 ; 5 V (GPS if 5 V) = pins 2, 4 ; GND = pins 6, 9, 14, 20, 25, 30, 34, 39

### 7c. Per-module wiring (match by LABEL on your actual module — pin order varies by vendor)
- MPU6050: VCC→3.3V, GND→GND, SDA→pin3, SCL→pin5
- DS3231: VCC→3.3V, GND→GND, SDA→pin3, SCL→pin5 (shares I²C)
- NEO-6M GPS: VCC→3.3V (or 5V), GND→GND, TX→pin10, RX→pin8
- MCP2515: VCC→3.3V, GND→GND, SI→pin19, SO→pin21, SCK→pin23, CS→pin24, INT→pin22; CANH/CANL → screw terminal to Node A
- W25Q128: VCC→3.3V, GND→GND, DI→pin19, DO→pin21, CLK→pin23, CS→pin26 (WP & HOLD → 3.3V)

### 7d. HAT components
40-pin female header; MCP2515, MPU6050, NEO-6M+antenna, DS3231, W25Q128 modules; female header strips; 2× 2-pin screw terminals (CAN out, power-fail in); blank PCB.
Optional (user leaning to drop): status LED + 330 Ω; 4.7 kΩ×2 I²C pull-ups (most modules have onboard); 100 nF×5 + 10 µF decoupling (modules have onboard). Netlist file exists (`edr_hat.net`) — module pinouts in it are ASSUMED, must be verified against real modules.

### 7e. Node A components
ESP32 DevKit, MCP2515 CAN module, micro-USB cable. (CAN termination: enable the onboard 120 Ω jumper on the MCP2515 modules at both bus ends.)

### 7f. Not in project
**GSM module** — never part of the design; explicitly dropped.

---

## 8. PCBs (both designed in KiCad)
- **Backup Unit PCB:** routed 2-layer; buck/boost as sub-modules on headers; screw terminals (12V In, Buck IN/OUT, Boost IN/OUT, Raspi Power). **Needs revision** for the 18650 design: remove supercap (C1–C3) + balancing resistor (RB1–3) + 22 Ω footprints; add TP4056 sub-module footprint + a 2-pin battery terminal (BAT+/BAT−). Footprint labels are placeholders (e.g. a "1N4148" label is really the 1N5401).
- **EDR HAT PCB:** routed; stacks on 40-pin header; module headers (Conn_01x06/07/08 etc.); shared SPI/I²C with dual chip-selects.
- Screenshots saved: `pcb_backup.png`, `pcb_hat.png`.

---

## 9. DIAGRAMS PRODUCED (SVG source + PNG)
- `system_block_diagram.(svg|png)` — overall system (Node A → CAN → Node B + sensors; Power unit; Analysis software; capture-sequence legend).
- `backup_block_diagram.(svg|png)` — power unit flow (green normal path, red backup path).
- `backup_circuit_schematic.(svg|png)` — full 18650 circuit with component symbols.
- (Note: AI image generators make garbage schematics — these were drawn as accurate SVG instead. Regenerate/edit the SVG if changes needed.)

---

## 10. PRESENTATION
- `eEDR_Project_Review.pptx` (15 slides) + `eEDR_Project_Review.pdf` (backup).
- Institutional VESIT format (matches college template): white bg, blue centered titles,
  Arial, thin border, two college logos on cover + a Thank You closer, page numbers.
- Emphasis on WORK DONE. Slides: 1 Title · 2 Contents · 3 Introduction · 4 Problem
  Statement · 5 System Overview (system block diagram) · 6 Work Done–Overview · 7
  Software: EDR Engine · 8 Software: Analysis Workstation · 9 Power Unit–Block Diagram ·
  10 Power Unit–Circuit Schematic · 11 Custom PCBs (real board images) · 12 Design
  Challenges & Decisions · 13 Remaining Work · 14 Conclusion · 15 Thank You.
- Recent tweaks applied: em dashes replaced with " - "; fonts enlarged; content centered;
  one diagram per slide; Contents left-aligned; plain Thank You; References removed.

---

## 11. GITHUB REPO
- Repo: https://github.com/kartiknagare33/enhanced_edr  (packaged as `enhanced_edr.zip`).
- Structure: `README.md`, `LICENSE` (MIT), `docs/BILL_OF_MATERIALS.md`,
  `hardware/power-survivability-unit/` (BUILD_GUIDE.md, WIRING.md, schematic),
  `hardware/edr-hat/` (edr_hat.net, NETLIST_README.md),
  `software/simulation/` (Python engine), `software/visualization/` (the HTML app).
- Push note: had a README merge conflict; resolved with `git checkout --ours README.md`
  → `git add` → `git commit` → `git push`. (Use a Personal Access Token, not password.)

---

## 12. FULL FILE LIST (deliverables produced)
- `edr_forensic.html` — the analysis workstation (main app)
- `edr_system/` + `edr_system.zip` — Python engine
- `power_survivability_unit_build_guide.md` — build guide (updated for HW-432)
- `enhanced_edr/` + `enhanced_edr.zip` — the GitHub repo bundle
- `hardware/.../WIRING.md` — exact 18650 wiring
- `edr_hat.net` + `edr_hat_netlist_README.md` — KiCad netlist for the HAT
- `system_block_diagram`, `backup_block_diagram`, `backup_circuit_schematic` (.svg + .png)
- `pcb_backup.png`, `pcb_hat.png` — KiCad board screenshots
- `logo_left.png`, `logo_right.png` — college logos
- `eEDR_Project_Review.pptx` + `.pdf` — the review deck
- Older/alternate (superseded): `edr_dashboard.html`, `edr_3d_console.zip`, `edr_workstation.zip`, `three.min.js`

---

## 13. CURRENT STATUS
- Simulation engine — **COMPLETE** (tested).
- Analysis workstation — **COMPLETE**.
- Power Survivability Unit — **DESIGNED & WIRED** (18650); PCB routed but needs revision for 18650.
- EDR HAT — **DESIGNED** (netlist + routed PCB).
- Presentation & repo — **DONE**.

## 14. REMAINING WORK
1. Fabricate & populate both PCBs (backup unit + EDR HAT).
2. Integrate sensors on the Pi; enable SPI/I²C in `/boot/config.txt` (overlays), verify each module (i2cdetect, etc.).
3. Bench-test power failover; confirm hold-up during a live flash write.
4. Demonstrate end-to-end crash capture: Node A (CAN) → Node B → locked, verified record.
5. Validate measured vs simulated; finish documentation.

## 15. OPEN ITEMS / THINGS TO VERIFY
- Confirm Dr. Ammanagi's exact designation (assumed "Assistant Professor, EXTC").
- Backup hold-up time is calculated (~2.5 s), not yet measured — measure it.
- Revise the backup-unit PCB for the 18650 (remove supercap/resistor footprints, add TP4056 + battery terminal).
- Verify each module's real pin order before soldering / trusting the netlist.
- Set buck (5.3 V) and boost (5.1 V) with a multimeter BEFORE connecting the Pi.

---

*End of handoff. Continue the project from this state.*
