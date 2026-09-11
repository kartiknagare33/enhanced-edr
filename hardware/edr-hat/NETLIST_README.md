# EDR HAT — KiCad netlist import guide

`edr_hat.net` is an importable KiCad netlist for the main EDR Unit (Raspberry Pi HAT).
It drops all 18 parts onto a blank PCB with the correct ratsnest (connection lines),
so you skip drawing the schematic and go straight to placement + routing.

**This is a scaffold, not plug-and-play. Read the two caveats below before trusting it.**

---

## How to import (KiCad 6 / 7 / 8)

1. Open **KiCad → PCB Editor** (pcbnew) with a new, empty board.
2. Menu: **File → Import → Netlist…**  (older versions: **Tools → Load Netlist**).
3. Browse to `edr_hat.net`, then click **Load and Test Netlist** (checks for errors).
4. If clean, click **Update PCB**. All parts appear stacked at the origin.
5. Click to place them, then route. Ratsnest lines show every connection.

If a **footprint error** appears for any part, it means that footprint name isn't in
your installed libraries. Fix it by editing that component's footprint to an equivalent
you do have (right-click part → Properties → Footprint → browse). The connections stay intact.

---

## ⚠ CAVEAT 1 — verify every module's pin order

Each sensor module is represented as a plain pin-header footprint. The netlist assumes
a specific pin order for each. **Real modules vary by vendor — check yours against the
tables below and fix any mismatch** (re-assign the net on the affected header pad),
or the ratsnest will point to the wrong physical pin.

**U1 · MCP2515 CAN** (1×10 header assumed)
| Pad | Signal | Net |
|---|---|---|
| 1 | VCC | +3V3 |
| 2 | GND | GND |
| 3 | CS | SPI_CE0_CAN |
| 4 | SO (MISO) | SPI_MISO |
| 5 | SI (MOSI) | SPI_MOSI |
| 6 | SCK | SPI_SCLK |
| 7 | INT | CAN_INT |
| 9 | CANH | CANH → J2 |
| 10 | CANL | CANL → J2 |

*Most MCP2515 modules put CANH/CANL on their own screw terminal, not header pins.
If so, ignore pads 9/10 and just wire that terminal to J2.*

**U2 · MPU6050** (1×8 header assumed: VCC, GND, SCL, SDA, …)
| Pad | Signal | Net |
|---|---|---|
| 1 | VCC | +3V3 |
| 2 | GND | GND |
| 3 | SCL | I2C_SCL |
| 4 | SDA | I2C_SDA |

**U3 · NEO-6M GPS** (1×5 header assumed: VCC, GND, TX, RX, PPS)
| Pad | Signal | Net |
|---|---|---|
| 1 | VCC | +5V *(change to +3V3 if your module is 3.3 V)* |
| 2 | GND | GND |
| 3 | TX | UART_RXD (→ Pi RX) |
| 4 | RX | UART_TXD (→ Pi TX) |

*Common alternative order is VCC, RX, TX, GND — check yours.*

**U4 · DS3231 RTC** (1×6 header assumed: 32K, SQW, SCL, SDA, VCC, GND)
| Pad | Signal | Net |
|---|---|---|
| 3 | SCL | I2C_SCL |
| 4 | SDA | I2C_SDA |
| 5 | VCC | +3V3 |
| 6 | GND | GND |

**U5 · W25Q128 flash** (1×8, SOIC-breakout order: CS, DO, WP, GND, DI, CLK, HOLD, VCC)
| Pad | Signal | Net |
|---|---|---|
| 1 | CS | SPI_CE1_FLASH |
| 2 | DO (MISO) | SPI_MISO |
| 3 | WP | +3V3 (disable write-protect) |
| 4 | GND | GND |
| 5 | DI (MOSI) | SPI_MOSI |
| 6 | CLK | SPI_SCLK |
| 7 | HOLD | +3V3 |
| 8 | VCC | +3V3 |

---

## ⚠ CAVEAT 2 — power rails

- All modules are on **+3V3** except the GPS (**+5V** by default). If your GPS runs at
  3.3 V, move U3 pin 1 and C5 pin 1 from +5V to +3V3.
- The MCP2515 module is placed on **+3V3** per our "no level shifter" decision. If your
  specific module's transceiver is 5 V-only, that's the one part to reconsider.

---

## Net list (what connects to what)

| Net | Nodes |
|---|---|
| +3V3 | J1.1, J1.17, U1.1, U2.1, U4.5, U5.8, U5.3, U5.7, R1.2, R2.2, C1–C4.1, C6.1 |
| +5V | J1.2, J1.4, U3.1, C5.1 |
| GND | J1.6/9/14/20/25/30/34/39, all module GND, all cap −, LED1.1, J3.2 |
| I2C_SDA | J1.3, U2.4, U4.4, R1.1 |
| I2C_SCL | J1.5, U2.3, U4.3, R2.1 |
| SPI_MOSI | J1.19, U1.5, U5.5 |
| SPI_MISO | J1.21, U1.4, U5.2 |
| SPI_SCLK | J1.23, U1.6, U5.6 |
| SPI_CE0_CAN | J1.24, U1.3 |
| SPI_CE1_FLASH | J1.26, U5.1 |
| CAN_INT | J1.22, U1.7 |
| UART_RXD | J1.10, U3.3 |
| UART_TXD | J1.8, U3.4 |
| PWR_FAIL | J1.11, J3.1 |
| LED_CTRL | J1.13, R3.1 |
| LED_A | R3.2, LED1.2 |
| CANH | U1.9, J2.1 |
| CANL | U1.10, J2.2 |

---

## Honest note
For a 13-part board, importing this netlist saves you the schematic-wiring step, but you
still place and route by hand — and you must verify the module pinouts above. If the import
fights you on footprints, hand-placing in Eeschema from this same table is the fallback and
takes ~30 minutes.
