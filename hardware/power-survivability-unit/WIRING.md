# Power Survivability Unit — Exact Wiring (18650 design)

Backup power for the Raspberry Pi. During normal running the 12 V line powers the Pi
through a buck regulator and trickle-charges an 18650 cell. On a power cut the cell
feeds a boost regulator that holds the 5 V rail up long enough to finish the crash
write + lock.

---

## 1. Voltage setpoints — SET THESE FIRST (before connecting the Pi)

| Module | Set output to | How |
|---|---|---|
| LM2596 buck | **5.3 V** | meter on OUT+, turn trimmer, no Pi connected |
| HW-432 (XL6009) boost | **5.1 V** | feed ~3.7 V into IN+, meter on OUT+, turn trimmer |

The buck (5.3 V) sits above the boost (5.1 V) on purpose: during normal running the
buck holds the rail high, so the boost's output diode is reverse-biased and the boost
stays idle. When the 12 V dies, the rail falls and the boost automatically takes over.

---

## 2. Components and their terminals

| Ref | Part | Terminals |
|---|---|---|
| — | 12 V supply | (+), (−) |
| SW1 | SPST toggle | 2 pins |
| F1 | 2 A fuse + holder | 2 pins |
| D1 | 1N5401 diode | A (anode), K (cathode = banded end) |
| U1 | LM2596 buck | IN+, IN−, OUT+, OUT− |
| U2 | TP4056 charger (protected) | IN+, IN−, B+, B−, OUT+, OUT− |
| BT1 | 18650 cell | (+), (−) |
| U3 | HW-432 boost | IN+, IN−, OUT+, OUT− |
| D2 | 1N5819 Schottky | A (anode), K (cathode = banded end) |
| R1 | 10 kΩ | 2 pins |
| R2 | 2.2 kΩ | 2 pins |

---

## 3. Exact connection list (every wire)

### Input & protection
| # | From | To |
|---|---|---|
| 1 | 12 V supply (+) | SW1 pin 1 |
| 2 | SW1 pin 2 | F1 pin 1 |
| 3 | F1 pin 2 | D1 anode (A) |
| 4 | D1 cathode (K) | **P12** node |
| 5 | 12 V supply (−) | **GND** |

### Buck — normal 5 V for the Pi
| # | From | To |
|---|---|---|
| 6 | P12 | U1 IN+ |
| 7 | GND | U1 IN− |
| 8 | U1 OUT+ | **RAIL_5V** node |
| 9 | U1 OUT− | GND |

### Battery charging (TP4056)
| # | From | To |
|---|---|---|
| 10 | RAIL_5V | U2 IN+ |
| 11 | GND | U2 IN− |
| 12 | U2 B+ | BT1 (+) |
| 13 | U2 B− | BT1 (−) |

### Backup boost — 18650 → 5.1 V on power cut
| # | From | To |
|---|---|---|
| 14 | U2 OUT+ | U3 IN+ |
| 15 | U2 OUT− | GND |
| 16 | U3 IN− | GND |
| 17 | U3 OUT+ | D2 anode (A) |
| 18 | D2 cathode (K) | RAIL_5V |
| 19 | U3 OUT− | GND |

### Power-fail sensing (Pi detects the cut)
| # | From | To |
|---|---|---|
| 20 | P12 | R1 pin 1 |
| 21 | R1 pin 2 | **NODE_A** |
| 22 | NODE_A | R2 pin 1 |
| 23 | R2 pin 2 | GND |
| 24 | NODE_A | Pi GPIO17 (physical pin 11) |

### Output to the Pi
| # | From | To |
|---|---|---|
| 25 | RAIL_5V | Pi 5 V (GPIO pin 2 or 4, **or** USB-C +5 V) |
| 26 | GND | Pi GND (GPIO pin 6, **or** USB-C GND) |

---

## 4. The three key nodes (every wire above lands on one of these)

| Node | Everything connected to it |
|---|---|
| **P12** | D1 K, U1 IN+, R1 pin 1 |
| **RAIL_5V** | U1 OUT+, U2 IN+, D2 K, → Pi 5 V |
| **NODE_A** | R1 pin 2, R2 pin 1, → GPIO17 |
| **GND** (common) | supply −, U1 IN−/OUT−, U2 IN−/OUT−, U3 IN−/OUT−, D2 return, R2 pin 2, → Pi GND |
| **18650** | BT1+ → U2 B+ · BT1− → U2 B− (battery ties ONLY to the TP4056 B± pads) |

---

## 5. Why the diodes are there

- **D1 (1N5401)** — reverse-polarity protection. Connect 12 V backwards and it blocks,
  saving the circuit.
- **D2 (1N5819 Schottky)** — the automatic failover. During normal running RAIL_5V is
  held at 5.3 V by the buck, so D2 (anode at the boost's 5.1 V) is reverse-biased and the
  boost does nothing. When the 12 V dies and RAIL_5V falls, the boost's 5.1 V forward-biases
  D2 and it supplies the rail. No switch, no MCU action — it's automatic.

---

## 6. Build & test order

1. Set **U1 (buck) to 5.3 V** — meter only, nothing else connected.
2. Set **U3 (boost) to 5.1 V** — feed ~3.7 V into its IN+, meter on OUT+.
3. Wire the input section (rows 1–5), verify **P12 ≈ 12 V**.
4. Wire the buck (rows 6–9), verify **RAIL_5V ≈ 5.3 V**.
5. Wire the TP4056 + battery (rows 10–13), confirm the charge LED lights.
6. Wire the boost + D2 (rows 14–19).
7. Wire the sensing divider (rows 20–24), verify **NODE_A ≈ 2.1–2.2 V** with 12 V present.
8. **Only now** connect the Pi (rows 25–26).
9. **Failover test:** with the Pi running, flip SW1 off. The Pi should keep running on the
   battery. Watch RAIL_5V on the meter — it should hold ~4.8–5.0 V.

---

## 7. Safety notes

- Use a **protected** TP4056 (the 6-pad version with the DW01 chip) — the battery load
  and charge both route through its protection, guarding against over-discharge and short.
- The 18650 connects **only** to the TP4056 B+ / B− pads — never directly to the boost or
  the rail.
- Never connect the Pi before the buck and boost are trimmed to their setpoints. A boost
  cannot exceed its set voltage, so setting 5.1 V first guarantees the Pi never sees an
  overvoltage.
- Observe 18650 polarity in the holder; a reversed cell into the TP4056 can damage it.
