#include "Timer.h"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <cstdio>
#include <limits>
using namespace flowsight;

int runTimerSelfTests() {
  Timer t;
  t.start(1000);
  t.tick(2200);
  assert(t.state.remainingMs == 1498800);
  t.pause(2600);
  assert(t.state.remainingMs == 1498400);
  t.tick(20000);
  assert(t.state.remainingMs == 1498400);
  assert(t.resume(21000));
  t.tick(22200);
  assert(t.state.remainingMs == 1497200);
  assert(!t.configure(10, 22200));
  assert(!t.setMode(Mode::Break, 22200));
  t.reset(30000);
  assert(!t.configure(0, 30000));
  assert(!t.configure(181, 30000));
  assert(t.configure(1, 30000));
  t.start(30000);
  t.pause(90000);  // An exact-deadline pause still completes the session.
  assert(t.state.phase == Phase::Complete && t.state.completed == 1);
  t.tick(1000000);
  assert(t.state.completed == 1);
  assert(t.setMode(Mode::Break, 1000000));
  assert(!t.configure(61, 1000000));
  assert(t.configure(1, 1000000));
  t.start(1000000);
  t.tick(1060000);
  assert(t.state.completed == 1);
  t.setMode(Mode::Focus, 1060000);
  t.start(0xfffffff0U);
  t.tick(0x000003d8U);  // millis() wrap: 1000 ms elapsed.
  assert(t.state.remainingMs == 59000);
  Snapshot saved = t.state;
  Timer restored;
  assert(restored.restore(saved, 100));
  assert(restored.state.phase == Phase::Paused);
  restored.tick(1000000);
  assert(restored.state.remainingMs == 59000);
  saved.remainingMs = saved.durationMs + 1;
  assert(!restored.restore(saved, 0));
  saved = t.state;
  saved.mode = static_cast<Mode>(9);
  assert(!restored.restore(saved, 0));
  t.reset(50);
  assert(!t.resume(100));
  t.start(100);
  t.start(200);
  assert(t.state.remainingMs == 59900);  // Duplicate start must not reset.
  puts("PASS: countdown, pause/resume, boundaries, completion, mode, wrap, restore, idempotency");
  return 0;
}

#ifndef ARDUINO
int main() { return runTimerSelfTests(); }
#endif
