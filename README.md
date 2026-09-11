# Enhanced Automobile Event Data Recorder (eEDR)

A forensic-grade vehicle "black box." It continuously records 40 vehicle parameters at
100 Hz into a rolling 20-second buffer, detects a crash through multiple redundant
triggers, writes the crash-critical data to tamper-evident storage with a hardware
write-lock, and survives loss of vehicle power long enough to complete that write.

## Repository layout

```
firmware/
  node-a-esp32/        ESP32 CAN-transmitter code (the simulated vehicle ECU)
software/
  simulation/          Python EDR engine (recorder core, tested)
  visualization/       Forensic analysis workstation (offline web app)
hardware/
  power-survivability-unit/  backup-power build guide, wiring, schematic
  edr-hat/             Raspberry Pi HAT netlist + wiring reference
docs/
  diagrams/            system + power-unit block diagrams and schematic
  pcb/                 KiCad PCB layout images
  PROJECT_HANDOFF.md   full project brief (every decision & spec)
  eEDR_Project_Review.pptx   review presentation
```

---

## System architecture

- **Node A — Vehicle ECU:** ESP32 + MCP2515 CAN module. Broadcasts vehicle data
  frames (speed, rpm, throttle, brake, temps, fuel, etc.) on the CAN bus.
  See `firmware/node-a-esp32/`.
- **Node B — EDR Unit:** Raspberry Pi 4B + MPU6050 (IMU), NEO-6M (GPS), DS3231 (RTC),
  W25Q128 (SPI flash), MCP2515 (CAN receive). Receives CAN + reads its own sensors,
  detects crashes, records to tamper-evident flash. See `hardware/edr-hat/`.
- **Power Survivability Unit:** 12 V → LM2596 buck → Pi, with an 18650 Li-ion + TP4056
  backup feeding an XL6009 (HW-432) boost that holds 5 V during a power cut.
  See `hardware/power-survivability-unit/`.

**Crash-capture sequence:** detect → freeze 20 s buffer → write to flash → assert
write-lock → verify SHA-256.

---

## Quick start

**Run the simulation engine** (pure Python, no dependencies):
```bash
cd software/simulation
python run.py list
python run.py run frontal_collision
python run.py test
```

**Open the analysis workstation:** open
`software/visualization/edr_forensic_workstation.html` in any browser (works offline).

**Flash Node A (ESP32):** open `firmware/node-a-esp32/nodeA_can_transmitter_extended.ino`
in the Arduino IDE, install the `mcp_can` library (by coryjfowler), select an ESP32
board, upload, and open the Serial Monitor at 115200 baud.

---

## Status

- [x] Simulation engine — complete, tested (14/14 tests, 6 scenarios)
- [x] Analysis workstation — complete (10 analysis modules)
- [x] Node A firmware — complete (CAN transmitter with structured output)
- [x] Power Survivability Unit — designed, wired, PCB routed
- [x] EDR HAT — netlist + wiring done, PCB routed
- [ ] Fabrication, sensor integration, and on-bench validation

See `docs/PROJECT_HANDOFF.md` for the complete project brief.
