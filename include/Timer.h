#pragma once
#include <cstdint>

namespace flowsight {
enum class Mode : uint8_t { Focus, Break };
enum class Phase : uint8_t { Idle, Running, Paused, Complete };

struct Snapshot {
  uint32_t magic = 0x46530101;
  uint32_t remainingMs = 25 * 60000;
  uint32_t durationMs = 25 * 60000;
  uint32_t completed = 0;
  uint16_t focusMinutes = 25;
  uint16_t breakMinutes = 5;
  Mode mode = Mode::Focus;
  Phase phase = Phase::Idle;
};

class Timer {
 public:
  Snapshot state;
  bool tick(uint32_t now) {
    const uint32_t elapsed = now - lastTick_;
    lastTick_ = now;
    if (state.phase != Phase::Running) return false;
    if (elapsed >= state.remainingMs) {
      state.remainingMs = 0;
      state.phase = Phase::Complete;
      if (state.mode == Mode::Focus) ++state.completed;
      return true;
    }
    state.remainingMs -= elapsed;
    return false;
  }
  void start(uint32_t now) {
    tick(now);
    if (state.phase == Phase::Complete) reset(now);
    if (state.phase == Phase::Idle || state.phase == Phase::Paused)
      state.phase = Phase::Running;
  }
  void pause(uint32_t now) {
    tick(now);
    if (state.phase == Phase::Running) state.phase = Phase::Paused;
  }
  bool resume(uint32_t now) {
    tick(now);
    if (state.phase != Phase::Paused && state.phase != Phase::Running) return false;
    state.phase = Phase::Running;
    return true;
  }
  void reset(uint32_t now) {
    state.durationMs = minutes() * 60000UL;
    state.remainingMs = state.durationMs;
    state.phase = Phase::Idle;
    lastTick_ = now;
  }
  bool busy() const { return state.phase == Phase::Running || state.phase == Phase::Paused; }
  uint16_t minutes() const { return state.mode == Mode::Focus ? state.focusMinutes : state.breakMinutes; }
  uint32_t seconds() const { return (state.remainingMs + 999) / 1000; }
  bool configure(uint16_t minutes, uint32_t now) {
    if (busy() || minutes < 1 || minutes > (state.mode == Mode::Focus ? 180 : 60)) return false;
    if (state.mode == Mode::Focus) state.focusMinutes = minutes;
    else state.breakMinutes = minutes;
    reset(now);
    return true;
  }
  bool setMode(Mode mode, uint32_t now, bool discard = false) {
    if (mode == state.mode) return true;
    if (busy() && !discard) return false;
    state.mode = mode;
    reset(now);
    return true;
  }
  bool restore(const Snapshot& saved, uint32_t now) {
    if (saved.magic != state.magic || saved.focusMinutes < 1 || saved.focusMinutes > 180 ||
        saved.breakMinutes < 1 || saved.breakMinutes > 60 ||
        static_cast<unsigned>(saved.mode) > 1 || static_cast<unsigned>(saved.phase) > 3 ||
        saved.durationMs != (saved.mode == Mode::Focus ? saved.focusMinutes : saved.breakMinutes) * 60000UL ||
        saved.remainingMs > saved.durationMs ||
        (saved.phase == Phase::Complete && saved.remainingMs != 0) ||
        (saved.phase != Phase::Complete && saved.remainingMs == 0) ||
        (saved.phase == Phase::Idle && saved.remainingMs != saved.durationMs)) return false;
    state = saved;
    if (state.phase == Phase::Running) state.phase = Phase::Paused;
    lastTick_ = now;
    return true;
  }
 private:
  uint32_t lastTick_ = 0;
};
}  // namespace flowsight
