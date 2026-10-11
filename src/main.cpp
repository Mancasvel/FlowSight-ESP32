#include <Arduino.h>
#include <ArduinoJson.h>
#include <Preferences.h>
#include <cmath>
#include <algorithm>
#include "Display.h"
#include "Fonts.h"

Display lcd;
lgfx::LGFX_Sprite canvas(&lcd);
// One 320 x 120 RGB565 buffer, reused for both halves of the display.
int canvasY = 0;
Preferences prefs;
constexpr uint32_t BG=0x101d25, PANEL=0x1a2c36, INK=0xe5f0f1;
constexpr uint32_t MUTED=0xadbec8, ACCENT=0x6cdfd0, LINE=0x2a414b;
enum class View { Timer, Settings, Confirm, Calibration };
enum class Action { None, Settings, Back, Primary, Stop, Normal, Pomodoro, Calibrate, Brightness, Confirm, Cancel };
View view=View::Timer;
Action pending=Action::None;
struct Button { int x,y,w,h; Action action; bool enabled; };
Button buttons[10];
int buttonCount=0,pressed=-1;
bool dirty=true,touchDown=false,hasState=false,online=false;
uint32_t downAt=0,lastSample=0,lastSync=0,requestAt=0,nextId=1,waitingId=0;
uint32_t touchCount=0;
int lastX=-1,lastY=-1,lastRawX=-1,lastRawY=-1;
uint8_t brightness=180;
String language="es",mode="normal",modeLabel="",kind="",clockText="--:--:--",status="",phase="";
String goalLabel="",goalValue="",context="",primaryAction="",primaryLabel="";
String feedback="";
uint32_t feedbackAt=0;
double totalSeconds=0,goalSeconds=0;
bool primaryEnabled=false,stopEnabled=false,modeEnabled=false,busy=false;
struct Calibration { uint32_t magic; float x[3]; float y[3]; } calibration{};
int calIndex=0,calSamples=0;
int64_t calSumX=0,calSumY=0;
float calRaw[4][2];
constexpr int calTargets[4][2]={{26,26},{294,26},{26,214},{294,214}};
uint32_t calStart=0;
char input[4096];
size_t inputLength=0;
bool inputOverflow=false;
const char* tr(const char* es,const char* en) { return language=="es"?es:en; }
bool connected() { return hasState && millis()-lastSync<5000; }
bool canControl() { return connected() && !busy && !waitingId; }
const char* viewName() {
  switch(view) { case View::Settings:return "settings"; case View::Confirm:return "confirm"; case View::Calibration:return "calibration"; default:return "timer"; }
}
bool validCalibration(const Calibration& c) {
  if (c.magic != 0x46534331) return false;
  for (int i = 0; i < 3; ++i)
    if (!std::isfinite(c.x[i]) || !std::isfinite(c.y[i])) return false;
  return std::abs(c.x[0]) < 1 && std::abs(c.x[1]) < 1 &&
         std::abs(c.y[0]) < 1 && std::abs(c.y[1]) < 1 &&
         std::abs(c.x[2]) < 1000 && std::abs(c.y[2]) < 1000;
}
void stateMessage(const char* event="response",const char* error=nullptr,int id=0) {
  JsonDocument d;
  d["event"]=event; d["id"]=id; d["ok"]=error==nullptr;
  if(error) d["error"]=error;
  d["product"]="flowsight-esp32"; d["protocol"]=2; d["version"]=FLOWSIGHT_VERSION;
  d["board"]="CS-32 N4XX / 2432S024R profile";
  d["connected"]=connected(); d["language"]=language; d["clock"]=clockText;
  d["mode"]=mode; d["phase"]=phase; d["status"]=status; d["kind"]=kind;
  d["goal_value"]=goalValue; d["goal_seconds"]=goalSeconds; d["total_seconds"]=totalSeconds;
  d["primary_action"]=primaryAction; d["primary_enabled"]=canControl()&&primaryEnabled;
  d["view"]=viewName(); d["waiting_id"]=waitingId;
  d["touch_calibrated"]=validCalibration(calibration); d["touch_count"]=touchCount;
  d["touch_x"]=lastX; d["touch_y"]=lastY; d["raw_x"]=lastRawX; d["raw_y"]=lastRawY;
  d["brightness"]=brightness; d["free_heap"]=ESP.getFreeHeap();
  serializeJson(d,Serial); Serial.println();
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
// Truncate at a UTF-8 boundary to fit the physical panel.
String fit(String text,int width,const uint8_t* font=FontBody) {
  useFont(font); canvas.setTextSize(1);
  if(canvas.textWidth(text)<=width) return text;
  while(text.length() && canvas.textWidth(text+"...")>width) {
    size_t end=text.length()-1;
    while(end && (static_cast<uint8_t>(text[end])&0xc0)==0x80) --end;
    text.remove(end);
  }
  return text+"...";
}
void renderBand(int top,bool push) {
  canvasY=top; buttonCount=0; canvas.fillScreen(BG);
  if(view==View::Timer) {
    canvas.fillRoundRect(12,15-canvasY,19,5,2,ACCENT);
    canvas.fillRoundRect(18,24-canvasY,19,5,2,ACCENT);
    label("FlowSight",44,8,INK,FontTitle);
    button(230,2,82,44,tr("Ajustes","Settings"),Action::Settings);
    label(fit(hasState?kind:tr("Conecta FlowSight","Connect FlowSight"),185),12,48,MUTED);
    // Right align mode; no independently advancing clock on the device.
    canvas.fillRect(205,46-canvasY,115,24,BG);
    useFont(FontBody);
    String shownMode=fit(modeLabel,103);
    label(shownMode,308-canvas.textWidth(shownMode),48,ACCENT);
    useFont(FontClock); canvas.setTextSize(1);
    const int clockWidth=canvas.textWidth(clockText);
    canvas.setTextSize(std::min(0.68f,296.0f/std::max(1,clockWidth)));
    canvas.setTextDatum(textdatum_t::middle_center); canvas.setTextColor(INK);
    canvas.drawString(clockText,160,98-canvasY); canvas.setTextSize(1);
    String shownStatus=connected()?status:tr("Sin conexión · Abre FlowSight","Offline · Open FlowSight");
    if(waitingId) shownStatus=tr("Aplicando en FlowSight...","Applying in FlowSight...");
    if(feedback.length() && millis()-feedbackAt<3500) shownStatus=feedback;
    label(fit(shownStatus,296),160,131,MUTED,FontBody,true);
    label(fit(hasState?goalLabel:tr("Objetivo diario","Daily goal"),180),12,146,MUTED);
    useFont(FontBody); String goal=fit(goalValue,105);
    label(goal,308-canvas.textWidth(goal),146,INK);
    canvas.fillRoundRect(12,168-canvasY,296,3,1,LINE);
    int progress=goalSeconds>0?static_cast<int>(std::min(1.0,std::max(0.0,totalSeconds/goalSeconds))*296):0;
    if(progress>0) canvas.fillRoundRect(12,168-canvasY,progress,3,1,ACCENT);
    label(fit(context,296),160,181,MUTED,FontBody,true);
    button(12,192,192,44,fit(primaryLabel.length()?primaryLabel:tr("Esperando app","Waiting for app"),170),Action::Primary,true,canControl()&&primaryEnabled);
    button(214,192,94,44,tr("Detener","Stop"),Action::Stop,false,canControl()&&stopEnabled);
  } else if(view==View::Settings) {
    label(tr("Ajustes","Settings"),12,10,INK,FontTitle);
    button(230,2,82,44,tr("Volver","Back"),Action::Back);
    label(tr("Modo del temporizador","Timer mode"),12,53,MUTED);
    button(12,78,144,46,"Normal",Action::Normal,mode=="normal",canControl()&&modeEnabled);
    button(164,78,144,46,"Pomodoro",Action::Pomodoro,mode=="pomodoro",canControl()&&modeEnabled);
    button(12,139,144,48,tr("Calibrar táctil","Calibrate touch"),Action::Calibrate);
    button(164,139,144,48,tr("Brillo","Brightness"),Action::Brightness);
    label(tr("El idioma sigue a la app.","Language follows the app."),160,209,MUTED,FontBody,true);
    label(connected()?tr("FlowSight conectado","FlowSight connected"):tr("Abre FlowSight en el PC.","Open FlowSight on your PC."),160,231,MUTED,FontBody,true);
  } else if(view==View::Confirm) {
    const bool stop=pending==Action::Stop;
    label(stop?tr("¿Detener sesión?","Stop session?"):tr("¿Cambiar modo?","Change mode?"),160,55,INK,FontTitle,true);
    label(stop?tr("Se detendrá el registro en la app.","Tracking will stop in the app."):tr("El modo cambiará también en la app.","The app will change mode too."),160,99,MUTED,FontBody,true);
    label(tr("El tiempo de hoy se conserva.","Today's recorded time is kept."),160,124,MUTED,FontBody,true);
    button(12,178,144,50,tr("Cancelar","Cancel"),Action::Cancel);
    button(164,178,144,50,stop?tr("Detener","Stop"):tr("Cambiar","Change"),Action::Confirm,true,canControl());
  } else {
    const int x=calTargets[calIndex][0],y=calTargets[calIndex][1];
    canvas.drawCircle(x,y-canvasY,12,ACCENT);
    canvas.drawFastHLine(x-18,y-canvasY,37,ACCENT); canvas.drawFastVLine(x,y-18-canvasY,37,ACCENT);
    label(tr("Calibrar táctil","Calibrate touch"),160,89,INK,FontTitle,true);
    label(String(tr("Toca y suelta el punto ","Touch and release point "))+String(calIndex+1)+tr(" de 4"," of 4"),160,122,MUTED,FontBody,true);
    label(tr("Pulsa BOOT para salir","Press BOOT to exit"),160,154,MUTED,FontBody,true);
  }
  if(push) canvas.pushSprite(0,top);
}
void render() { dirty=false; renderBand(0,true); renderBand(120,true); }

void beginCalibration() {
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
bool allowed(const String& action) {
  if(!canControl()) return false;
  if(action=="stop") return stopEnabled;
  if(action=="mode_normal" || action=="mode_pomodoro") return modeEnabled;
  return primaryEnabled && action==primaryAction;
}
void requestAction(const String& action) {
  if(!allowed(action)) return;
  waitingId=nextId++; requestAt=millis();
  JsonDocument d; d["event"]="control"; d["id"]=waitingId; d["action"]=action;
  serializeJson(d,Serial); Serial.println(); dirty=true;
}
void activate(Action action) {
  switch(action) {
    case Action::Settings:view=View::Settings;break;
    case Action::Back:view=View::Timer;break;
    case Action::Primary:requestAction(primaryAction);break;
    case Action::Stop:if(allowed("stop")) {pending=action;view=View::Confirm;}break;
    case Action::Normal:case Action::Pomodoro:
      if(canControl()&&modeEnabled && mode!=(action==Action::Normal?"normal":"pomodoro")) {pending=action;view=View::Confirm;}break;
    case Action::Brightness:
      brightness=brightness==255?80:brightness==80?180:255;
      lcd.setBrightness(brightness);prefs.putUChar("brightness",brightness);break;
    case Action::Calibrate:beginCalibration();break;
    case Action::Confirm:
      requestAction(pending==Action::Stop?"stop":pending==Action::Normal?"mode_normal":"mode_pomodoro");
      view=pending==Action::Stop?View::Timer:View::Settings;pending=Action::None;break;
    case Action::Cancel:view=pending==Action::Stop?View::Timer:View::Settings;pending=Action::None;break;
    default:break;
  }
  pressed=-1;dirty=true;
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
        else { calIndex=0; stateMessage("calibration_error","calibration_points_invalid"); }
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
bool acceptSnapshot(JsonVariant s) {
  if(!s.is<JsonObject>()) return false;
  for(const char* key:{"language","mode","mode_label","kind","clock","status","phase","goal_label","goal_value","context","primary_action","primary_label"})
    if(!s[key].is<const char*>() || strlen(s[key])>300) return false;
  String lang=s["language"].as<String>();
  if(lang!="es" && lang!="en") return false;
  String value=s["clock"].as<String>();
  if(value.length()<4 || value.length()>10) return false;
  for(char c:value) if((c<'0'||c>'9')&&c!=':') return false;
  for(const char* key:{"primary_enabled","stop_enabled","mode_enabled","busy"}) if(!s[key].is<bool>()) return false;
  if(!s["total_seconds"].is<double>() || !s["goal_seconds"].is<double>()) return false;
  if(primaryAction!=s["primary_action"].as<String>() || mode!=s["mode"].as<String>() || !s["primary_enabled"].as<bool>()) pressed=-1;
  if(language!=lang) {language=lang;prefs.putString("language",language);}
  mode=s["mode"].as<String>();modeLabel=s["mode_label"].as<String>();kind=s["kind"].as<String>();
  clockText=value;status=s["status"].as<String>();phase=s["phase"].as<String>();
  goalLabel=s["goal_label"].as<String>();goalValue=s["goal_value"].as<String>();context=s["context"].as<String>();
  totalSeconds=s["total_seconds"].as<double>();goalSeconds=s["goal_seconds"].as<double>();
  primaryAction=s["primary_action"].as<String>();primaryLabel=s["primary_label"].as<String>();
  primaryEnabled=s["primary_enabled"];stopEnabled=s["stop_enabled"];modeEnabled=s["mode_enabled"];busy=s["busy"];
  hasState=true;lastSync=millis();dirty=true;return true;
}
void command(const char* line) {
  JsonDocument d;
  if(deserializeJson(d,line)) {stateMessage("response","invalid_json");return;}
  const char* cmd=d["cmd"]|"";const int id=d["id"]|0;
  const char* error=nullptr;
  if(!strcmp(cmd,"hello")) {stateMessage("hello");return;}
  if(!strcmp(cmd,"sync")) {
    if(!acceptSnapshot(d["state"])) {stateMessage("response","invalid_snapshot",id);return;}
    JsonDocument reply;
    reply["event"]="synced";reply["id"]=id;reply["clock"]=clockText;
    reply["language"]=language;reply["phase"]=phase;reply["touch_count"]=touchCount;
    reply["touch_calibrated"]=validCalibration(calibration);
    serializeJson(reply,Serial);Serial.println();return;
  }
  if(!strcmp(cmd,"ack")) {
    if(waitingId && d["id"].as<uint32_t>()==waitingId) {
      waitingId=0;dirty=true;
      if(!d["ok"].as<bool>()) {feedback=tr("Acción no aplicada. Revisa la app.","Action not applied. Check the app.");feedbackAt=millis();}
    }
    return;
  }
  if(!strcmp(cmd,"status")) {}
  else if(!strcmp(cmd,"screen")) {screenshot(id);return;}
  else if(!strcmp(cmd,"calibrate")) beginCalibration();
  else if(!strcmp(cmd,"home")) {view=View::Timer;pending=Action::None;dirty=true;}
  else if(!strcmp(cmd,"tap")) {
    if(!d["x"].is<int>() || !d["y"].is<int>()) error="invalid_coordinates";
    else {if(dirty) render();const int index=hit(d["x"],d["y"]);if(index<0) error="no_button";else activate(buttons[index].action);}
  } else error="unknown_command";
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
  Serial.begin(115200);pinMode(0,INPUT_PULLUP);
  for(int pin:{4,16,17}) {pinMode(pin,OUTPUT);digitalWrite(pin,HIGH);}
  pinMode(5,OUTPUT);digitalWrite(5,HIGH);
  prefs.begin("flowsight",false);
  brightness=prefs.getUChar("brightness",180);if(brightness<40) brightness=180;
  language=prefs.getString("language","es");
  if(prefs.getBytesLength("touch")==sizeof(calibration)) prefs.getBytes("touch",&calibration,sizeof(calibration));
  lcd.init();lcd.setRotation(1);lcd.setBrightness(brightness);canvas.setColorDepth(16);
  if(!canvas.createSprite(320,120)) {
    lcd.fillScreen(BG);lcd.setTextColor(INK);lcd.drawString("Memory unavailable. Restart.",12,100);
    while(true) delay(1000);
  }
  canvas.setTextWrap(false);render();stateMessage("hello");
}
void loop() {
  pollSerial();pollTouch();pollBoot();
  const bool current=connected();
  if(current!=online) {online=current;pressed=-1;dirty=true;}
  if(waitingId && millis()-requestAt>8000) {
    waitingId=0;feedback=tr("Sin respuesta. Revisa FlowSight.","No response. Check FlowSight.");feedbackAt=millis();dirty=true;
  }
  if(feedback.length() && millis()-feedbackAt>=3500) {feedback="";dirty=true;}
  if(dirty) render();delay(2);
}
