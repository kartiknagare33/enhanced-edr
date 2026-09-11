# Power Survivability Unit — Build Guide (final, safe version)

Power backup for the eEDR project that keeps the Raspberry Pi alive long enough after a power cut to freeze the crash buffer, write it to flash, and lock it — then reports the power loss to software so that sequence actually fires.

Streamlined design: clean regulated backup, two tuning steps, no fragile parts, and the Pi is never exposed to more than 5.1V.

---

## 1. How it works (plain english)

**Normal running:** 12V passes through protection (fuse + reverse-polarity diode), then a buck converter drops it to ~5.3V to power the Pi. The supercapacitors trickle-charge to ~5V off that same 5.3V rail through a current-limiting resistor. The boost regulator on the cap output sits idle because the buck (5.3V) is higher than the boost target (5.1V), so the buck supplies the Pi.

**On power cut:** the buck output collapses. A diode stops the caps from draining backward into the dead buck, so they discharge *forward* through the boost regulator (HW-432 / XL6009), which holds a steady 5.1V to the Pi as the caps sag from ~5V toward ~3.8V. Because the caps never charge above ~5V, the boost is always stepping *up* — so the Pi never sees an overvoltage. Separately, a voltage divider on the 12V line lets the Pi sense the drop on a GPIO pin and fire the freeze → write → lock sequence.

---

## 2. Why charge the caps from the 5.3V rail (not the 12V line)?

This is the key safety decision. If the caps charged to a high voltage (e.g. 6.5–8V) and fed a plain boost regulator, then early in discharge — while the caps are still above 5.1V — the Pi could briefly see more than 5V, because a boost regulator can only step *up*, not down. Charging from the 5.3V rail caps them at ~5V, always below the 5.1V target, so the boost always regulates cleanly and the Pi is never over-volted. The trade is shorter backup (~2.5s), which is still far more than the <1s actually needed.

---

## 3. Backup time (verified calculation)

- Bank: 3× 10F supercaps in series = **3.33 F**
- Charged to **~5.0V** off the rail; the HW-432 (XL6009) boost regulates down to **~3.8V** input
- Usable energy = 0.85 × 0.5 × 3.33 × (4.95² − 3.8²) ≈ **15 J**

| Pi load | Backup time |
|---|---|
| 4.0 W (0.8A) | ~3.7 s |
| 5.0 W (1.0A) | ~3.0 s |
| 6.0 W (1.2A, realistic) | **~2.5 s** |
| 7.5 W (1.5A, peak) | ~2.0 s |

**What you need:** freeze buffer (instant) + flash write (~0.3s) + assert lock (~0.1s) = **under 1 second**. So ~2.5s at realistic load is still a comfortable ~2.5× margin on the critical path. (The XL6009 stops pulling energy from the caps at a higher input voltage than an MT3608 would, so hold-up is shorter than the earlier design — but well above the <1s requirement.)

---

## 4. Bill of materials

| # | Component | Spec | Easy substitute | Approx. cost |
|---|---|---|---|---|
| 1 | 12V source | bench supply (lab) — don't buy | any 12V lab supply | ₹0 |
| 2 | Toggle switch | SPST, 12V-rated | any 12V toggle/rocker | ₹30–50 |
| 3 | Fuse holder + fuse | 2A fast-blow | any 1–2A fuse | ₹20–30 |
| 4 | Rectifier diode | 1N5401 (3A) | 1N5408 / 1N4007 | ₹5–10 |
| 5 | Buck converter | LM2596, set 5.3V | any adjustable buck | ₹73 |
| 6 | Supercapacitors ×3 | 2.7V 10F | any 2.7V 10F EDLC | ₹150 |
| 7 | Balancing resistors ×3 | 1kΩ, 1 per cap | 470Ω–1kΩ | ₹5 |
| 8 | Charge-limit resistor | 22Ω, 2W | 22–47Ω, 2W | ₹5 |
| 9 | Blocking diode | 1N5819 Schottky | 1N5817 / 1N5822 | ₹5 |
| 10 | Boost regulator | HW-432 (XL6009), set 5.1V | MT3608 / any adjustable boost | ₹60–90 |
| 11 | Divider resistors | 10kΩ + 2.2kΩ | — | ₹2–5 |
| 12 | Perfboard + jumper wires | — | breadboard fine | ₹100–150 |
| | **Total** | | | **≈ ₹450–570** |

**Keep cost low:** check lab stock first (buck/boost/breadboard often available); buy resistors as a kit; get commodity parts locally; only the LM2596, HW-432, and supercaps are worth ordering online. Don't buy a 12V source (use lab supply) or a dummy load (reuse any Arduino you own).

---

## 5. Wiring — the three branches

All three share one PROTECTED 12V node (after the fuse and reverse-polarity diode) and one common GND.

### Branch 1 — main power
```
12V → switch → fuse → 1N5401 → PROTECTED 12V → LM2596 buck (5.3V) → 5V RAIL → Pi USB
```
Trim the buck to **5.3V** (multimeter, no load) before connecting the Pi.

### Branch 2 — supercapacitor backup
```
5V RAIL → 22Ω 2W → 1N5819 (D1) → CAP+ → [3× 2.7V 10F series, 1kΩ across each] → GND
CAP+ → HW-432 IN+ ┃ HW-432 OUT+ → Pi USB ┃ HW-432 IN−/OUT− → GND
```
Trim the HW-432 boost to **5.1V** (its trimmer is multi-turn — ~10–15 turns to move the output, so keep going). Caps reach ~5V; boost holds 5.1V on discharge.

### Branch 3 — power-fail sensing
```
PROTECTED 12V → 10kΩ → NODE A → 2.2kΩ → GND
NODE A → Pi GPIO17
```
NODE A ≈ 2.16V at 12V (safely under the 3.3V GPIO limit); it falls when input drops. Software watches GPIO17 and fires freeze → write → lock on the drop.

**Merge behavior:** both the 5.3V rail and the 5.1V boost connect to the Pi's USB power input. Normally the higher rail (5.3V) supplies the Pi and the boost idles; when the rail collapses, the boost (5.1V) takes over automatically.

---

## 6. Build & test order — don't skip ahead

1. **Branch 1 only.** Trim buck to 5.3V, verify with multimeter, no load.
2. **Dummy load test.** Arduino/resistor+LED on the rail. Flip switch on/off; output stays ~5.3V.
3. **Backup alone.** Let caps charge (~6min), trim the HW-432 to 5.1V (multi-turn pot), cut the 12V, confirm the boost holds 5.1V into the dummy load. **Time it — expect ~2.5s above 4.8V at ~6W.** Record measured-vs-calculated for your report.
4. **Sensing.** Confirm NODE A reads ~2.16V at 12V and drops when the switch is cut.
5. **Only now connect the real Pi** via USB. Wire GPIO17. Full test: cut power → GPIO drop detected → buffer freezes → flash write completes → lock asserts → (optional clean shutdown), all on cap power.

---

## 7. Design rationale (for report & viva)

Five defensible engineering decisions:

1. **Rejected a more complex dual-converter topology** (two bucks + comparator + voltage-based handover) as it added tuning points and oscillation risk without proportional benefit — deliberately choosing a cleaner design that meets the requirement.
2. **Boost regulator instead of caps directly on the 5V rail** — a naive cap-on-rail only charges to ~4.65V (below the Pi's ~4.75V floor); regulating the output uses the charge down to ~3.8V, multiplying usable energy.
3. **Charging from the 5.3V rail, not 12V** — deliberately caps the bank at ~5V so a plain boost never lets the Pi see an overvoltage. A conscious safety-vs-runtime trade.
4. **Cell balancing on the series stack** — a resistor across each cap prevents any cell exceeding its 2.7V rating.
5. **Power-fail detection via divided voltage to GPIO** — reuses the same crash-response path as IMU/CAN triggers, unifying the event model.

---

## 8. Safety

- Never connect the Pi until buck (5.3V) and boost (5.1V) are both verified on a dummy load across several switch cycles.
- No HDMI/Ethernet/USB-to-laptop cables on the Pi during switching tests — isolate first.
- Power the Pi via USB, not raw GPIO 5V pins.
- Check every diode orientation before powering on — reversed diodes break the charge/block logic and can cause damage.
- Supercaps hold charge and can deliver a strong short-circuit current — discharge them through a resistor before handling the board.

---

## 9. Quick reference

**Backup ≈ 2.5s at realistic ~6W (need <1s). Pi never sees >5.1V. Two trims (buck 5.3V, HW-432 boost 5.1V), one timed test.**
