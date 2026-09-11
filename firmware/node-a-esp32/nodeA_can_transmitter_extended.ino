/**********************************************************************
 *  eEDR - Node A : Vehicle ECU  (CAN transmitter, extended)
 *  ESP32 + MCP2515.  Sends many vehicle parameters over several CAN IDs
 *  and prints a structured block each cycle.
 *  LIBRARY: "mcp_can" by coryjfowler | SERIAL MONITOR: 115200 baud
 **********************************************************************/
#include <SPI.h>
#include <mcp_can.h>

#define CAN_CS   5
#define CAN_INT  4
MCP_CAN CAN0(CAN_CS);

// ---- CAN IDs ----
#define ID_POWERTRAIN 0x100
#define ID_DYNAMICS   0x101
#define ID_ENGINE     0x110
#define ID_FUEL       0x120
#define ID_BODY       0x130
#define ID_TRIP       0x140
#define ID_AMBIENT    0x150
#define ID_VIN        0x200

const char* VIN = "MAJEDR26VESIT0001";   // 17-char (fake) vehicle ID

// ---- vehicle state ----
float speed=0; int rpm=900, throttle=0, brake=0; char gear='P';
int steering=0, yaw=0;
float coolant=25, oilT=25, intakeT=30, load=0;
float fuel=80, fuelRate=0.8; int range=560;
float odo=45200, trip=0;
int ambient=28; float batt=13.8;
bool absOn=false, tcsOn=false, belt=true, lights=true, wipers=false;
unsigned long t0, lastOdo;

void setup(){
  Serial.begin(115200); delay(600); Serial.println();
  Serial.println("eEDR Node A - Vehicle ECU (CAN transmitter)");
  if (CAN0.begin(MCP_ANY, CAN_500KBPS, MCP_8MHZ)==CAN_OK)   // 16 MHz module? use MCP_16MHZ
       Serial.println("MCP2515 init OK (500 kbps)\n");
  else { Serial.println("MCP2515 init FAILED - check wiring / crystal"); while(1) delay(1000); }
  CAN0.setMode(MCP_NORMAL);
  pinMode(CAN_INT, INPUT);
  t0=millis(); lastOdo=millis();
}

void updateVehicle(){
  float t=(millis()-t0)/1000.0, ph=fmod(t,14.0);
  if(ph<6){ throttle=70; brake=0; gear='D'; speed+=0.6; if(speed>90)speed=90; }
  else if(ph<10){ throttle=30; brake=0; gear='D'; }
  else if(ph<12){ throttle=0; brake=90; speed-=1.2; if(speed<0)speed=0; }
  else { throttle=0; brake=20; speed-=0.3; if(speed<0)speed=0; if(speed<0.1)gear='P'; }

  rpm = 900 + throttle*45 + (int)(speed*25);
  steering = (int)(8*sin(t));
  yaw = (int)(steering * speed / 60.0);
  load = throttle*0.9 + 8;
  absOn = brake>60; tcsOn = (throttle>60 && speed<20);

  if(coolant<90) coolant += 0.05;                 // warms up
  oilT = coolant + 6; intakeT = 30 + throttle*0.05;
  fuelRate = 0.8 + throttle*0.09 + speed*0.03;     // L/h
  fuel -= fuelRate/3600.0;  if(fuel<0) fuel=0;
  range = (int)(fuel * 7.0);
  batt = (throttle>0?14.2:13.6) + (random(-5,6)/100.0);
  ambient = 28 + random(-1,2);

  unsigned long now=millis();
  float dt=(now-lastOdo)/1000.0; lastOdo=now;
  float dkm = speed/3600.0*dt; odo+=dkm; trip+=dkm;
}

// send one frame + print a structured, labelled line
void tx(uint32_t id, const char* name, byte* d, byte len, const char* decoded){
  byte res = CAN0.sendMsgBuf(id, 0, len, d);
  char hex[30]=""; for(byte i=0;i<len;i++){char b[4]; sprintf(b,"%02X ",d[i]); strcat(hex,b);}
  Serial.printf("  0x%03X %-10s | %-24s| %s%s\n", id, name, hex, decoded, res==CAN_OK?"":"  [TX FAIL]");
}

void sendAll(){
  char s[80];
  Serial.printf("\n====== CAN TX SET  |  t = %.1f s ======\n",(millis()-t0)/1000.0);

  { uint16_t sp=(uint16_t)(speed*10), rp=rpm; byte d[8]={(byte)(sp>>8),(byte)sp,(byte)(rp>>8),(byte)rp,(byte)throttle,(byte)brake,(byte)gear,0};
    snprintf(s,sizeof(s),"speed=%.1fkm/h rpm=%d thr=%d%% brk=%d%% gear=%c",speed,rpm,throttle,brake,gear); tx(ID_POWERTRAIN,"POWERTRAIN",d,8,s); }

  { byte d[4]={(byte)(int8_t)steering,(byte)absOn,(byte)tcsOn,(byte)(int8_t)yaw};
    snprintf(s,sizeof(s),"steer=%ddeg abs=%d tcs=%d yaw=%d",steering,absOn,tcsOn,yaw); tx(ID_DYNAMICS,"DYNAMICS",d,4,s); }

  { byte d[4]={(byte)coolant,(byte)oilT,(byte)intakeT,(byte)load};
    snprintf(s,sizeof(s),"coolant=%dC oil=%dC intake=%dC load=%d%%",(int)coolant,(int)oilT,(int)intakeT,(int)load); tx(ID_ENGINE,"ENGINE",d,4,s); }

  { uint16_t rg=range; byte d[4]={(byte)fuel,(byte)(fuelRate*10),(byte)(rg>>8),(byte)rg};
    snprintf(s,sizeof(s),"level=%d%% rate=%.1fL/h range=%dkm",(int)fuel,fuelRate,range); tx(ID_FUEL,"FUEL",d,4,s); }

  { byte doors=0x00; byte d[4]={doors,(byte)belt,(byte)lights,(byte)wipers};
    snprintf(s,sizeof(s),"doors=closed belt=%s lights=%s wipers=%s",belt?"ON":"off",lights?"ON":"off",wipers?"ON":"off"); tx(ID_BODY,"BODY",d,4,s); }

  { uint32_t od=(uint32_t)odo; uint16_t tp=(uint16_t)(trip*10);
    byte d[6]={(byte)(od>>24),(byte)(od>>16),(byte)(od>>8),(byte)od,(byte)(tp>>8),(byte)tp};
    snprintf(s,sizeof(s),"odometer=%lukm trip=%.1fkm",(unsigned long)od,trip); tx(ID_TRIP,"TRIP",d,6,s); }

  { byte d[2]={(byte)(int8_t)ambient,(byte)(batt*10)};
    snprintf(s,sizeof(s),"ambient=%dC battery=%.1fV",ambient,batt); tx(ID_AMBIENT,"AMBIENT",d,2,s); }

  { byte d[8]; for(int i=0;i<8;i++) d[i]=VIN[i];
    snprintf(s,sizeof(s),"\"%s\"",VIN); tx(ID_VIN,"VIN",d,8,s); }
}

void loop(){
  updateVehicle();
  sendAll();
  delay(500);          // one full set every 0.5 s
}
