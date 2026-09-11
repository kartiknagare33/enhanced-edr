# Enhanced Event Data Recorder (eEDR) — Software

A forensic-grade "black box" for vehicles: it continuously records driving
telemetry, detects crashes, freezes the data around the event, analyses it, and
stores it with tamper-evident integrity — then reports the loss of power to
software so the record is safely written even if the vehicle loses power.

This is the **software** half of the project. It runs today as a physics-based
simulation on a laptop, and is architected so the same code runs on a Raspberry
Pi 3B with real sensors by changing **one line**.

---

## Why the architecture matters

The entire system is built around a **Hardware Abstraction Layer (HAL)**. The
crash-detection core reads samples through one interface (`DataSource`) and never
knows whether the data is simulated or real:

```
            ┌─────────────────────────────────────────────┐
            │             EDR CORE (unchanged)             │
            │  ring buffer → detector → analytics → store  │
            └───────────────────────▲─────────────────────┘
                                    │ EDRSample (40 params)
                    ┌───────────────┴───────────────┐
                    │                                │
          SimulatedDataSource              HardwareDataSource
          (physics sim, today)             (CAN/IMU/GPS, on the Pi)
```

To move to hardware you implement `edr/hal/hardware.py` (CAN, IMU, GPS, power
sense) and swap which source `run.py` instantiates. Buffer, detector, analytics,
storage, lock, and reporting are all untouched. That hardware-independence is the
central design claim.

---

## Quick start

Pure standard library — no installation needed. Python 3.8+.

```bash
python run.py list                       # list scenarios
python run.py run frontal_collision      # run one scenario
python run.py run all                    # run every scenario
python run.py replay EVENT_0001          # print a stored crash report
python run.py verify EVENT_0001          # re-check integrity
python run.py tamper EVENT_0001          # alter a record; show it's detected
python run.py test                       # run the unit tests
```

Output (crash records, logs, reports) is written under `run_output/<scenario>/`.

---

## What it does, step by step

1. **Monitor** — every 10 ms (100 Hz) a 40-parameter sample enters a circular
   buffer holding the last 20 s (2000 samples). Once per second a sample is also
   appended to the continuous SD driving log.
2. **Detect** — each sample is checked against four independent triggers: IMU
   G-spike, abrupt speed drop, ECU crash flag (over CAN), and power-fail.
3. **Freeze** — on any trigger the buffer is frozen (the pre-crash window is
   snapshotted) and post-crash samples are recorded for a further 5 s.
4. **Analyse** — the event window yields peak G, **delta-V**, **PDOF / impact
   direction**, rollover, a Crash Severity Index, and a severity classification.
5. **Store & lock** — the crash-critical parameter subset is written to
   simulated flash with a **SHA-256 checksum**; a **write-protect lock** is then
   asserted so the record cannot be altered. The full 40-parameter window is
   saved separately, and a human-readable report is generated.

---

## Layout

```
edr_system/
├── run.py                  CLI / entry point
├── edr/
│   ├── config.py           all thresholds, rates, and the crash-critical subset
│   ├── model.py            the 40-parameter EDRSample
│   ├── hal/
│   │   ├── base.py         DataSource interface (the swap point)
│   │   ├── simulated.py    physics-based driving + crash simulator
│   │   └── hardware.py     real-sensor scaffold for the Pi (implement here)
│   ├── core/
│   │   ├── ring_buffer.py  circular buffer with freeze-on-crash
│   │   ├── detector.py     multi-trigger crash detection state machine
│   │   └── analytics.py    delta-V, PDOF, rollover, CSI, severity
│   ├── storage/
│   │   ├── flash.py        crash image + SHA-256 integrity
│   │   ├── sd_logger.py    continuous 1 Hz CSV log
│   │   └── lock.py         forensic write-protect lock
│   ├── recorder.py         the runtime state machine tying it together
│   ├── report.py           human-readable crash report
│   └── scenarios.py        scripted driving/crash scenarios
└── tests/                  unit tests (buffer, detector, analytics)
```

---

## Parameters: 40 tracked, 28 locked

The full sample carries **40 parameters** (vehicle dynamics, IMU, GPS, system/
power). The forensically-critical **28** written to flash are defined explicitly
in `config.CRASH_CRITICAL_PARAMS` — edit that one list to change what gets
locked, with no logic changes.

---

## Forensic integrity demo

```bash
python run.py run frontal_collision
python run.py verify EVENT_0001     # PASS
python run.py tamper EVENT_0001     # alter one stored value
python run.py verify EVENT_0001     # FAIL — tampering detected
```

The checksum lets an investigator prove a record is exactly what the device
wrote.

---

## Moving to the Raspberry Pi

1. Implement the driver reads in `edr/hal/hardware.py` (CAN via MCP2515, IMU via
   MPU6050, GPS via NEO-6M, power sense via the voltage divider → GPIO).
2. In `run.py`, instantiate `HardwareDataSource()` instead of
   `SimulatedDataSource(...)`.
3. Wire the power-fail GPIO interrupt to raise a sample with `power_fail=True` —
   the detector already treats that as a crash trigger, so the freeze→write→lock
   sequence runs on supercapacitor power exactly as in simulation.
```
