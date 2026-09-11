/**********************************************************************
 *  eEDR - Node A : Vehicle ECU  (CAN transmitter)
 *  ESP32 + MCP2515 CAN module
 *
 *  Simulates a driving cycle (accelerate -> cruise -> hard brake -> stop)
 *  and broadcasts the vehicle data on the CAN bus. Every frame that is
 *  sent is also printed to the Serial Monitor so you can watch the data.
 *
 *  LIBRARY:  install "mcp_can" by coryjfowler  (Arduino Library Manager)
 *  BOARD:    any ESP32 dev board
 *  SERIAL MONITOR: set baud to 115200
 **********************************************************************/

#include <SPI.h>
#include <mcp_can.h>          // coryjfowler MCP_CAN library

// ---------- WIRING  (MCP2515  ->  ESP32) ----------
//   VCC  -> 3V3     (see note at bottom about 3.3V vs 5V)
//   GND  -> GND
//   CS   -> GPIO5
//   SO   -> GPIO19  (MISO)
//   SI   -> GPIO23  (MOSI)
//   SCK  -> GPIO18
//   INT  -> GPIO4   (optional for transmit-only)
#define CAN_CS   5
#define CAN_INT  4

MCP_CAN CAN0(CAN_CS);

// ---------- CAN message IDs ----------
const uint32_t ID_POWERTRAIN = 0x100;   // speed, rpm, throttle, brake, gear
const uint32_t ID_DYNAMICS   = 0x101;   // steering, ABS flag, brake

// ---------- simulated vehicle state ----------
float speed    = 0;      // km/h
int   rpm      = 900;
int   throttle = 0;      // %
int   brake    = 0;      // %
char  gear     = 'P';
int   steering = 0;      // deg
unsigned long t0;

void setup() {
  Serial.begin(115200);
  delay(600);
  Serial.println();
  Serial.println("=====================================================");
  Serial.println(" eEDR  Node A - Vehicle ECU (CAN transmitter)");
  Serial.println("=====================================================");

  // NOTE: match the crystal on YOUR module.
  //   most cheap modules = 8 MHz  -> MCP_8MHZ
  //   some modules       = 16 MHz -> MCP_16MHZ
  if (CAN0.begin(MCP_ANY, CAN_500KBPS, MCP_8MHZ) == CAN_OK) {
    Serial.println(" MCP2515 init OK  (500 kbps)");
  } else {
    Serial.println(" MCP2515 init FAILED - check wiring / crystal (8 vs 16 MHz)");
    while (1) { delay(1000); }
  }
  CAN0.setMode(MCP_NORMAL);        // MUST be NORMAL mode to transmit
  pinMode(CAN_INT, INPUT);
  t0 = millis();

  Serial.println();
  Serial.println(" time(ms)   ID     DLC  data (hex)            decoded");
  Serial.println(" ----------------------------------------------------------------");
}

// ---- simple driving cycle, loops about every 14 s ----
void simulateDriving() {
  float t = (millis() - t0) / 1000.0;
  float phase = fmod(t, 14.0);

  if (phase < 6) {                 // accelerate
    throttle = 70; brake = 0; gear = 'D';
    speed += 0.6; if (speed > 90) speed = 90;
  } else if (phase < 10) {         // cruise
    throttle = 30; brake = 0; gear = 'D';
  } else if (phase < 12) {         // hard braking
    throttle = 0; brake = 90;
    speed -= 1.2; if (speed < 0) speed = 0;
  } else {                         // roll to a stop
    throttle = 0; brake = 20;
    speed -= 0.3; if (speed < 0) speed = 0;
    if (speed < 0.1) gear = 'P';
  }
  rpm = 900 + throttle * 45 + (int)(speed * 25);
  steering = (int)(8 * sin(t));    // gentle steering wander
}

// ---- pack + send the powertrain frame ----
void sendPowertrain() {
  uint16_t sp = (uint16_t)(speed * 10);   // 0.1 km/h resolution
  uint16_t rp = (uint16_t)rpm;
  byte d[8];
  d[0] = sp >> 8;  d[1] = sp & 0xFF;
  d[2] = rp >> 8;  d[3] = rp & 0xFF;
  d[4] = (byte)throttle;
  d[5] = (byte)brake;
  d[6] = (byte)gear;
  d[7] = 0;
  byte res = CAN0.sendMsgBuf(ID_POWERTRAIN, 0, 8, d);   // (id, standard, len, data)
  printFrame(ID_POWERTRAIN, 8, d, res);
}

// ---- pack + send the dynamics frame ----
void sendDynamics() {
  int8_t st = (int8_t)steering;
  byte d[3];
  d[0] = (byte)st;                    // steering angle (signed)
  d[1] = (brake > 60) ? 1 : 0;        // ABS-active flag (demo)
  d[2] = (byte)brake;
  byte res = CAN0.sendMsgBuf(ID_DYNAMICS, 0, 3, d);
  printFrame(ID_DYNAMICS, 3, d, res);
}

// ---- print one frame to the Serial Monitor ----
void printFrame(uint32_t id, byte len, byte* d, byte res) {
  char hex[40] = "";
  for (byte i = 0; i < len; i++) { char b[4]; sprintf(b, "%02X ", d[i]); strcat(hex, b); }
  Serial.printf(" %8lu  0x%03X   %d   %-21s", millis(), id, len, hex);

  if (id == ID_POWERTRAIN) {
    uint16_t sp = (d[0] << 8) | d[1];
    uint16_t rp = (d[2] << 8) | d[3];
    Serial.printf("spd=%.1f km/h  rpm=%d  thr=%d%%  brk=%d%%  gear=%c",
                  sp / 10.0, rp, d[4], d[5], (char)d[6]);
  } else if (id == ID_DYNAMICS) {
    Serial.printf("steer=%d deg  abs=%d  brk=%d%%", (int8_t)d[0], d[1], d[2]);
  }
  if (res != CAN_OK) Serial.print("   [TX FAIL]");
  Serial.println();
}

void loop() {
  simulateDriving();
  sendPowertrain();
  delay(50);
  sendDynamics();
  delay(50);            // ~10 frames/sec total
}

/**********************************************************************
 *  WIRING NOTE - 3.3 V vs 5 V (important for ESP32)
 *  The ESP32's pins are NOT 5 V tolerant. The one wire that matters is
 *  the module's SO (MISO) going INTO the ESP32.
 *
 *  - If your module's CAN transceiver is a 3.3 V type (e.g. SN65HVD230),
 *    just power the module at 3.3 V. Simplest and safe.
 *  - If it's a 5 V transceiver (e.g. TJA1050 - very common), either:
 *      (a) power the module at 3.3 V (often still works on a short
 *          2-node bench bus), OR
 *      (b) power at 5 V and drop the SO->MISO line to 3.3 V with a
 *          resistor divider (e.g. 1 k in series + 2 k to GND) or a
 *          level shifter. MOSI/SCK/CS from the 3.3 V ESP32 are read
 *          fine by a 5 V MCP2515.
 *
 *  If CAN0.begin() prints "init OK" you're good. If it FAILS, check the
 *  crystal setting (MCP_8MHZ vs MCP_16MHZ) and the wiring/power first.
 **********************************************************************/
