#include <Arduino.h>
#include <ArduinoJson.h>
#include <Preferences.h>
#include <cmath>
#include <algorithm>
#include "Display.h"
#include "Timer.h"
#include "Fonts.h"

using flowsight::Mode;
using flowsight::Phase;
Display lcd;
lgfx::LGFX_Sprite canvas(&lcd);
// The classic ESP32 cannot always allocate 153,600 contiguous bytes.
// Render RGB565 in two strips using a single 76,800-byte buffer.
int canvasY = 0;
Preferences prefs;
flowsight::Timer timer;

constexpr uint32_t BG = 0x101d25, PANEL = 0x1a2c36, INK = 0xe5f0f1;
constexpr uint32_t MUTED = 0xadbec8, ACCENT = 0x6cdfd0, LINE = 0x2a414b;
enum class View { Timer, Settings, Confirm, Calibration };
enum class Action { None, Settings, Back, Primary, Reset, Focus, Break, Minus, Plus, Calibrate, Brightness, Confirm, Cancel };
View view = View::Timer;
Action pending = Action::None;
struct Button { int x, y, w, h; Action action; bool enabled; };
Button buttons[10];
int buttonCount = 0, pressed = -1;
bool dirty = true, touchDown = false;
uint32_t downAt = 0, lastSample = 0, lastSecond = 0xffffffff, lastSave = 0, lastUsb = 0;
uint32_t touchCount = 0;
int lastX = -1, lastY = -1, lastRawX = -1, lastRawY = -1;
uint8_t brightness = 180;
int panelReadbackMatches = -1;
struct Calibration { uint32_t magic; float x[3]; float y[3]; } calibration{};
int calIndex = 0, calSamples = 0;
int64_t calSumX = 0, calSumY = 0;
float calRaw[4][2];
constexpr int calTargets[4][2] = {{26,26},{294,26},{26,214},{294,214}};
uint32_t calStart = 0;
int runTimerSelfTests();
char input[384];
size_t inputLength = 0;
bool inputOverflow = false;

const char* phaseName() {
  switch (timer.state.phase) {
    case Phase::Running: return "running";
    case Phase::Paused: return "paused";
    case Phase::Complete: return "complete";
    default: return "idle";
  }
}
const char* viewName() {
  switch (view) {
    case View::Settings: return "settings";
    case View::Confirm: return "confirm";
    case View::Calibration: return "calibration";
    default: return "timer";
  }
}
bool validCalibration(const Calibration& c) {
  if (c.magic != 0x46534331) return false;
  for (int i = 0; i < 3; ++i)
    if (!std::isfinite(c.x[i]) || !std::isfinite(c.y[i])) return false;
  return std::abs(c.x[0]) < 1 && std::abs(c.x[1]) < 1 &&
         std::abs(c.y[0]) < 1 && std::abs(c.y[1]) < 1 &&
         std::abs(c.x[2]) < 1000 && std::abs(c.y[2]) < 1000;
}
void persist() {
  prefs.putBytes("timer", &timer.state, sizeof(timer.state));
  lastSave = millis();
}
void stateMessage(const char* event = "state", const char* error = nullptr, int id = 0) {
  JsonDocument d;
  d["event"] = event;
  d["id"] = id;
  d["ok"] = error == nullptr;
  if (error) d["error"] = error;
  d["version"] = FLOWSIGHT_VERSION;
  d["board"] = "ESP32-2432S028R";
  d["mode"] = timer.state.mode == Mode::Focus ? "focus" : "break";
  d["phase"] = phaseName();
  d["remaining_ms"] = timer.state.remainingMs;
  d["seconds"] = timer.seconds();
  d["duration_seconds"] = timer.state.durationMs / 1000;
  d["focus_minutes"] = timer.state.focusMinutes;
  d["break_minutes"] = timer.state.breakMinutes;
  d["completed_sessions"] = timer.state.completed;
  d["view"] = viewName();
  d["touch_calibrated"] = validCalibration(calibration);
  d["touch_count"] = touchCount;
  d["touch_x"] = lastX;
  d["touch_y"] = lastY;
  d["raw_x"] = lastRawX;
  d["raw_y"] = lastRawY;
  d["brightness"] = brightness;
  d["panel_readback_matches"] = panelReadbackMatches;
  d["free_heap"] = ESP.getFreeHeap();
  d["uptime_ms"] = millis();
  serializeJson(d, Serial);
  Serial.println();
}

const uint8_t* selectedFont = nullptr;
void useFont(const uint8_t* font) {
  if (selectedFont != font) { canvas.loadFont(font); selectedFont = font; }
}
void label(const String& text, int x, int y, uint32_t color = INK,
           const uint8_t* font = FontBody, bool center = false) {
  useFont(font);
  canvas.setTextSize(1);
  canvas.setTextColor(color);
  canvas.setTextDatum(center ? textdatum_t::middle_center : textdatum_t::top_left);
  canvas.drawString(text, x, y-canvasY);
}
void button(int x, int y, int w, int h, const String& text, Action action,
            bool primary = false, bool enabled = true) {
  const int index = buttonCount++;
  buttons[index] = {x,y,w,h,action,enabled};
  uint32_t fill = primary ? ACCENT : PANEL;
  uint32_t color = primary ? BG : INK;
  if (!enabled) { fill = BG; color = MUTED; }
  else if (pressed == index) { fill = primary ? 0x35bfae : LINE; }
  canvas.fillRoundRect(x,y-canvasY,w,h,10,fill);
  if (!enabled) canvas.drawRoundRect(x,y-canvasY,w,h,10,LINE);
  label(text, x+w/2, y+h/2, color, FontBody, true);
}
void renderBand(int top, bool push) {
  canvasY = top;
  buttonCount = 0;
  canvas.fillScreen(BG);
  if (view == View::Timer) {
    // The mark echoes FlowSight's two moving strokes; no bitmap assets required.
    canvas.fillRoundRect(12,15-canvasY,19,5,2,ACCENT);
    canvas.fillRoundRect(18,24-canvasY,19,5,2,ACCENT);
    label("FlowSight", 44, 8, INK, FontTitle);
    button(240,2,72,44,"Ajustes",Action::Settings);
    label(timer.state.mode == Mode::Focus ? "Concentración" : "Descanso",12,47,ACCENT);
    const String count = String(timer.state.completed) + (timer.state.completed == 1 ? " sesión" : " sesiones");
    useFont(FontBody);
    label(count,308-canvas.textWidth(count),47,MUTED);
    char clock[12];
    const auto sec = timer.seconds();
    snprintf(clock,sizeof(clock),"%02lu:%02lu",static_cast<unsigned long>(sec/60),static_cast<unsigned long>(sec%60));
    canvas.setTextDatum(textdatum_t::middle_center);
    canvas.setTextColor(INK);
    useFont(FontClock);
    canvas.setTextSize(sec/60 >= 100 ? 0.8f : 1.0f);
    canvas.drawString(clock,160,105-canvasY);
    const char* status = "Todo listo. Empieza cuando quieras.";
    if (timer.state.phase == Phase::Running) status = "Un paso cada vez.";
    if (timer.state.phase == Phase::Paused) status = "En pausa. Tu tiempo está guardado.";
    if (timer.state.phase == Phase::Complete) status = timer.state.mode == Mode::Focus ? "Sesión completada. Tómate un respiro." : "Descanso terminado. ¿Seguimos?";
    label(status,160,146,MUTED,FontBody,true);
    canvas.fillRoundRect(12,162-canvasY,296,4,2,LINE);
    int progress = timer.state.durationMs ? ((uint64_t)(timer.state.durationMs-timer.state.remainingMs)*296/timer.state.durationMs) : 0;
    if (progress > 0) canvas.fillRoundRect(12,162-canvasY,progress,4,2,ACCENT);
    const char* action = "Empezar";
    if (timer.state.phase == Phase::Running) action = "Pausar";
    if (timer.state.phase == Phase::Paused) action = "Reanudar";
    if (timer.state.phase == Phase::Complete) action = timer.state.mode == Mode::Focus ? "Descansar" : "Volver al foco";
    button(12,178,190,50,action,Action::Primary,true);
    button(212,178,96,50,"Reiniciar",Action::Reset,false,timer.state.phase != Phase::Idle);
  } else if (view == View::Settings) {
    label("Ajustes",12,10,INK,FontTitle);
    button(240,2,72,44,"Volver",Action::Back);
    button(12,51,144,44,"Foco",Action::Focus,timer.state.mode == Mode::Focus);
    button(164,51,144,44,"Descanso",Action::Break,timer.state.mode == Mode::Break);
    button(12,107,58,48,"-5",Action::Minus,false,!timer.busy() && timer.minutes()>1);
    button(250,107,58,48,"+5",Action::Plus,false,!timer.busy() && timer.minutes()<(timer.state.mode==Mode::Focus?180:60));
    label(String(timer.minutes())+" min",160,130,INK,FontTitle,true);
    button(12,168,144,44,"Calibrar táctil",Action::Calibrate);
    button(164,168,144,44,"Brillo",Action::Brightness);
    label(timer.busy() ? "Reinicia para cambiar la duración." : "Tus ajustes quedan guardados.",160,228,MUTED,FontBody,true);
  } else if (view == View::Confirm) {
    const bool changingMode=pending==Action::Focus || pending==Action::Break;
    const char* title=pending==Action::Focus ? "¿Cambiar a foco?" : pending==Action::Break ? "¿Cambiar a descanso?" : "¿Reiniciar sesión?";
    label(title,160,54,INK,FontTitle,true);
    label("Se descartará el tiempo de este bloque.",160,97,MUTED,FontBody,true);
    label("Tus sesiones completadas se conservan.",160,122,MUTED,FontBody,true);
    button(12,178,144,50,"Cancelar",Action::Cancel);
    button(164,178,144,50,changingMode?"Cambiar":"Reiniciar",Action::Confirm,true);
  } else {
    const int x = calTargets[calIndex][0], y = calTargets[calIndex][1];
    canvas.drawCircle(x,y-canvasY,12,ACCENT);
    canvas.drawFastHLine(x-18,y-canvasY,37,ACCENT);
    canvas.drawFastVLine(x,y-18-canvasY,37,ACCENT);
    label("Calibrar táctil",160,89,INK,FontTitle,true);
    label("Toca y suelta el punto "+String(calIndex+1)+" de 4",160,122,MUTED,FontBody,true);
    label("Pulsa BOOT para salir",160,154,MUTED,FontBody,true);
  }
  if (push) canvas.pushSprite(0,top);
}
void render() {
  dirty=false;
  renderBand(0,true);
  renderBand(120,true);
}

void beginCalibration() {
  timer.pause(millis());
  persist();
  calIndex = 0;
  calSamples = 0;
  calSumX = calSumY = 0;
  calStart = millis();
  view = View::Calibration;
  pressed = -1;
  dirty = true;
}
bool finishCalibration() {
  const float x0=calRaw[0][0], y0=calRaw[0][1];
  const float ux=calRaw[1][0]-x0, uy=calRaw[1][1]-y0;
  const float vx=calRaw[2][0]-x0, vy=calRaw[2][1]-y0;
  const float det=ux*vy-uy*vx;
  if (std::abs(det)<100000) return false;
  Calibration c{};
  c.magic=0x46534331;
  c.x[0]=268*vy/det; c.x[1]=-268*vx/det; c.x[2]=26-c.x[0]*x0-c.x[1]*y0;
  c.y[0]=-188*uy/det; c.y[1]=188*ux/det; c.y[2]=26-c.y[0]*x0-c.y[1]*y0;
  const float cx=c.x[0]*calRaw[3][0]+c.x[1]*calRaw[3][1]+c.x[2];
  const float cy=c.y[0]*calRaw[3][0]+c.y[1]*calRaw[3][1]+c.y[2];
  if (!validCalibration(c) || std::abs(cx-294)>22 || std::abs(cy-214)>22) return false;
  calibration=c;
  prefs.putBytes("touch",&calibration,sizeof(calibration));
  return true;
}
void activate(Action action) {
  const uint32_t now = millis();
  if (timer.tick(now)) {
    pressed=-1; dirty=true; persist(); stateMessage("completed");
    // A press that straddles expiry must not accidentally start a break.
    if (action==Action::Primary) return;
  }
  switch (action) {
    case Action::Settings: view=View::Settings; break;
    case Action::Back: view=View::Timer; break;
    case Action::Primary:
      if (timer.state.phase==Phase::Running) timer.pause(now);
      else {
        if (timer.state.phase==Phase::Complete)
          timer.setMode(timer.state.mode==Mode::Focus?Mode::Break:Mode::Focus,now);
        timer.start(now);
      }
      break;
    case Action::Reset:
      if (timer.busy()) { pending=action; view=View::Confirm; }
      else timer.reset(now);
      break;
    case Action::Focus: case Action::Break: {
      const Mode mode=action==Action::Focus?Mode::Focus:Mode::Break;
      if (!timer.setMode(mode,now)) { pending=action; view=View::Confirm; }
      break;
    }
    case Action::Minus: timer.configure(timer.minutes()>5?timer.minutes()-5:1,now); break;
    case Action::Plus: timer.configure(std::min<int>(timer.minutes()+5,timer.state.mode==Mode::Focus?180:60),now); break;
    case Action::Brightness:
      brightness=brightness==255?80:brightness==80?180:255;
      lcd.setBrightness(brightness);
      prefs.putUChar("brightness",brightness);
      break;
    case Action::Calibrate: beginCalibration(); break;
    case Action::Confirm:
      if (pending==Action::Focus || pending==Action::Break)
        timer.setMode(pending==Action::Focus?Mode::Focus:Mode::Break,now,true);
      else timer.reset(now);
      view=pending==Action::Reset?View::Timer:View::Settings;
      pending=Action::None;
      break;
    case Action::Cancel: view=pending==Action::Reset?View::Timer:View::Settings; pending=Action::None; break;
    default: break;
  }
  pressed=-1;
  persist();
  dirty=true;
  stateMessage("action");
}
int hit(int x,int y) {
  for (int i=0;i<buttonCount;++i) {
    const auto& b=buttons[i];
    if (b.enabled && x>=b.x && y>=b.y && x<b.x+b.w && y<b.y+b.h) return i;
  }
  return -1;
}
void touchEvent(bool down,int x,int y) {
  if (down && !touchDown) {
    pressed=hit(x,y);
    downAt=millis();
    dirty=true;
  } else if (down && pressed>=0 && hit(x,y)!=pressed) {
    pressed=-1;  // Sliding off cancels; sliding back does not reactivate.
    dirty=true;
  } else if (!down && touchDown) {
    const int released=pressed;
    pressed=-1;
    dirty=true;
    if (released>=0 && millis()-downAt>=35) activate(buttons[released].action);
  }
  touchDown=down;
}
void pollTouch() {
  if (millis()-lastSample<12) return;
  lastSample=millis();
  int32_t rawX=0,rawY=0;
  const bool down=lcd.getTouchRaw(&rawX,&rawY)>0;
  static uint8_t misses=0;
  if (down) misses=0;
  else if (touchDown && ++misses<3) return;
  if (down) { lastRawX=rawX; lastRawY=rawY; }
  if (view==View::Calibration) {
    if (down && calSamples<30) { calSumX+=rawX; calSumY+=rawY; ++calSamples; }
    if (!down && touchDown && calSamples>=4) {
      calRaw[calIndex][0]=static_cast<float>(calSumX)/calSamples;
      calRaw[calIndex][1]=static_cast<float>(calSumY)/calSamples;
      ++calIndex;
      if (calIndex==4) {
        const bool valid=finishCalibration();
        if (valid) { view=View::Timer; stateMessage("calibrated"); }
        else { calIndex=0; stateMessage("calibration_error","Repite los cuatro puntos con precisión."); }
      }
      dirty=true;
    }
    if (!down) { calSamples=0; calSumX=calSumY=0; }
    touchDown=down;
    if (millis()-calStart>90000) { view=View::Timer; touchDown=false; dirty=true; stateMessage("calibration_timeout"); }
    return;
  }
  int32_t x=rawX,y=rawY;
  if (down) {
    if (validCalibration(calibration)) {
      x=lroundf(calibration.x[0]*rawX+calibration.x[1]*rawY+calibration.x[2]);
      y=lroundf(calibration.y[0]*rawX+calibration.y[1]*rawY+calibration.y[2]);
    } else lcd.convertRawXY(&x,&y);
    lastX=x; lastY=y;
    if (!touchDown) ++touchCount;
  }
  touchEvent(down,x,y);
}

void screenshot(int id) {
  render();
  Serial.printf("{\"event\":\"frame\",\"id\":%d,\"width\":320,\"height\":240,\"format\":\"rgb565-rle-le\"}\n",id);
  uint16_t pixel=0,run=0;
  auto flush=[&]() {
    const uint8_t bytes[4]={static_cast<uint8_t>(run),static_cast<uint8_t>(run>>8),static_cast<uint8_t>(pixel),static_cast<uint8_t>(pixel>>8)};
    Serial.write(bytes,4);
  };
  for (int band=0;band<2;++band) {
    renderBand(band*120,false);
    for (int y=0;y<120;++y) for (int x=0;x<320;++x) {
      const uint16_t next=canvas.readPixel(x,y);
      if (run && (next!=pixel || run==65535)) { flush(); run=0; }
      pixel=next;
      ++run;
    }
  }
  flush();
  Serial.println();
}
void command(const char* line) {
  JsonDocument d;
  if (deserializeJson(d,line)) { stateMessage("response","invalid_json"); return; }
  const char* cmd=d["cmd"] | "";
  const int id=d["id"] | 0;
  const uint32_t now=millis();
  if (timer.tick(now)) { persist(); dirty=true; stateMessage("completed"); }
  lastUsb=now;
  const char* error=nullptr;
  bool changed=false;
  if (!strcmp(cmd,"status")) {}
  else if (!strcmp(cmd,"start")) { timer.start(now); changed=true; }
  else if (!strcmp(cmd,"pause")) { timer.pause(now); changed=true; }
  else if (!strcmp(cmd,"resume")) { if (!timer.resume(now)) error="not_paused"; else changed=true; }
  else if (!strcmp(cmd,"reset")) { timer.reset(now); view=View::Timer; changed=true; }
  else if (!strcmp(cmd,"clear_sessions")) {
    if (timer.busy()) error="session_active";
    else if (!d["confirm"].is<bool>() || !d["confirm"].as<bool>()) error="confirmation_required";
    else { timer.state.completed=0; changed=true; }
  }
  else if (!strcmp(cmd,"mode")) {
    const char* mode=d["value"] | "";
    if (strcmp(mode,"focus") && strcmp(mode,"break")) error="invalid_mode";
    else if (!timer.setMode(!strcmp(mode,"focus")?Mode::Focus:Mode::Break,now)) error="session_active";
    else changed=true;
  } else if (!strcmp(cmd,"duration")) {
    if (!d["minutes"].is<int>() || d["minutes"].as<int>()<1 || d["minutes"].as<int>()>180) error="invalid_duration";
    else if (!timer.configure(d["minutes"].as<int>(),now)) error=timer.busy()?"session_active":"invalid_duration";
    else changed=true;
  } else if (!strcmp(cmd,"screen")) { screenshot(id); return; }
  else if (!strcmp(cmd,"panel_check")) {
    if (dirty) render();
    constexpr int points[6][2]={{0,0},{16,17},{20,26},{160,105},{18,184},{216,184}};
    panelReadbackMatches=0;
    for (int band=0;band<2;++band) {
      renderBand(band*120,false);
      for (const auto& p : points)
        if (p[1]/120==band && lcd.readPixel(p[0],p[1])==canvas.readPixel(p[0],p[1]-band*120)) ++panelReadbackMatches;
    }
  }
  else if (!strcmp(cmd,"calibrate")) { beginCalibration(); changed=true; }
  else if (!strcmp(cmd,"home")) { view=View::Timer; pending=Action::None; changed=true; }
  else if (!strcmp(cmd,"tap")) {
    // USB automation, deliberately separate from physical touch_count.
    if (!d["x"].is<int>() || !d["y"].is<int>()) error="invalid_coordinates";
    else {
      if (dirty) render();
      const int index=hit(d["x"].as<int>(),d["y"].as<int>());
      if (index<0) error="no_button";
      else { activate(buttons[index].action); changed=true; }
    }
  } else error="unknown_command";
  if (changed) { pressed=-1; persist(); dirty=true; }
  stateMessage("response",error,id);
}
void pollSerial() {
  // Bound work per loop so malformed/continuous serial input cannot starve touch.
  for (int count=0;count<128 && Serial.available();++count) {
    const char c=Serial.read();
    if (c=='\n') {
      input[inputLength]=0;
      if (inputOverflow) stateMessage("response","line_too_long");
      else if (inputLength) command(input);
      inputLength=0; inputOverflow=false;
    } else if (c!='\r') {
      if (inputLength<sizeof(input)-1) input[inputLength++]=c;
      else inputOverflow=true;
    }
  }
}
void pollBoot() {
  static bool wasDown=false,held=false;
  static uint32_t since=0;
  const bool down=digitalRead(0)==LOW;
  if (down && !wasDown) { since=millis(); held=false; }
  if (down && !held && millis()-since>1500) { held=true; beginCalibration(); }
  if (!down && wasDown && !held && millis()-since>30) {
    if (view==View::Calibration) { view=View::Timer; dirty=true; }
    else { view=View::Timer; activate(Action::Primary); }
  }
  wasDown=down;
}
void setup() {
  Serial.begin(115200);
  runTimerSelfTests();
  Serial.println("{\"event\":\"selftest\",\"ok\":true}");
  pinMode(0,INPUT_PULLUP);
  // CYD RGB LED is active-low. Keep it off; no radio or networking is started.
  for (int pin : {4,16,17}) { pinMode(pin,OUTPUT); digitalWrite(pin,HIGH); }
  pinMode(5,OUTPUT); digitalWrite(5,HIGH);  // Deselect unused SD.
  prefs.begin("flowsight",false);
  flowsight::Snapshot saved;
  if (prefs.getBytesLength("timer")==sizeof(saved)) { prefs.getBytes("timer",&saved,sizeof(saved)); timer.restore(saved,millis()); }
  brightness=prefs.getUChar("brightness",180);
  if (brightness<40) brightness=180;
  if (prefs.getBytesLength("touch")==sizeof(calibration)) prefs.getBytes("touch",&calibration,sizeof(calibration));
  lcd.init();
  lcd.setRotation(1);
  lcd.setBrightness(brightness);
  canvas.setColorDepth(16);
  if (!canvas.createSprite(320,120)) {
    lcd.fillScreen(BG); lcd.setTextColor(INK); lcd.drawString("Sin memoria. Reinicia.",12,100);
    Serial.println("{\"event\":\"fatal\",\"error\":\"framebuffer_allocation\"}");
    while (true) delay(1000);
  }
  canvas.setTextWrap(false);
  render();
  stateMessage("ready");
}
void loop() {
  if (timer.tick(millis())) { pressed=-1; persist(); dirty=true; stateMessage("completed"); }
  pollSerial();
  pollTouch();
  pollBoot();
  const uint32_t sec=timer.seconds();
  if (sec!=lastSecond) { lastSecond=sec; if (view==View::Timer) dirty=true; if (lastUsb && millis()-lastUsb<15000) stateMessage(); }
  if (timer.state.phase==Phase::Running && millis()-lastSave>=30000) persist();
  if (dirty) render();
  delay(2);
}
