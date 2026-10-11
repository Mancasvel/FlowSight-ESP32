#pragma once
#include <LovyanGFX.hpp>

// ESP32-2432S028R (CYD): LCD and touch use separate SPI buses.
class Display : public lgfx::LGFX_Device {
  lgfx::Bus_SPI bus_;
#ifdef FLOWSIGHT_ST7789
  lgfx::Panel_ST7789 panel_;
#else
  lgfx::Panel_ILI9341 panel_;
#endif
  lgfx::Light_PWM light_;
  lgfx::Touch_XPT2046 touch_;
 public:
  Display() {
    auto bus = bus_.config();
    bus.spi_host = HSPI_HOST;
    bus.spi_mode = 0;
    bus.freq_write = 40000000;
    bus.freq_read = 16000000;
    bus.spi_3wire = false;
    bus.use_lock = true;
    bus.dma_channel = SPI_DMA_CH_AUTO;
    bus.pin_sclk = 14;
    bus.pin_mosi = 13;
    bus.pin_miso = 12;
    bus.pin_dc = 2;
    bus_.config(bus);
    panel_.setBus(&bus_);

    auto panel = panel_.config();
    panel.pin_cs = 15;
    panel.pin_rst = -1;
    panel.pin_busy = -1;
    panel.panel_width = 240;
    panel.panel_height = 320;
    panel.memory_width = 240;
    panel.memory_height = 320;
    panel.offset_x = 0;
    panel.offset_y = 0;
    panel.offset_rotation = 0;
#ifdef FLOWSIGHT_ST7789
    panel.invert = true;
#else
    panel.invert = false;
#endif
    panel.rgb_order = false;
    panel.readable = true;
    panel.bus_shared = false;
    panel_.config(panel);

    auto light = light_.config();
    light.pin_bl = 21;
    light.invert = false;
    light.freq = 12000;
    light.pwm_channel = 7;
    light_.config(light);
    panel_.setLight(&light_);

    auto touch = touch_.config();
    touch.spi_host = VSPI_HOST;
    touch.freq = 1000000;
    touch.pin_sclk = 25;
    touch.pin_mosi = 32;
    touch.pin_miso = 39;
    touch.pin_cs = 33;
    touch.pin_int = 36;
    touch.bus_shared = false;
    touch.x_min = 200;
    touch.x_max = 3900;
    touch.y_min = 200;
    touch.y_max = 3900;
    touch.offset_rotation = 0;
    touch_.config(touch);
    panel_.setTouch(&touch_);
    setPanel(&panel_);
  }
};
