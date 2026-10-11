#include "TouchGesture.h"
#include <cassert>
#include <cstdio>

int main() {
  // A normal button tap fires once, on release.
  TouchGesture clean;
  assert(clean.update(true, 4, false, 0) == -1);
  assert(clean.update(true, 4, false, 12) == -1);
  assert(clean.pressed == 4);
  assert(clean.update(false, -1, false, 60) == 4);
  assert(clean.update(false, -1, false, 72) == -1);

  // Ignore a displaced first reading, even if it lands on another button.
  TouchGesture initialNoise;
  initialNoise.update(true, 2, false, 0);
  initialNoise.update(true, 4, false, 12);
  initialNoise.update(true, 4, false, 24);
  assert(initialNoise.update(false, -1, false, 72) == 4);

  // A single displaced reading while lifting must not swallow the tap.
  TouchGesture releaseNoise;
  releaseNoise.update(true, 4, false, 0);
  releaseNoise.update(true, 4, false, 12);
  releaseNoise.update(true, 1, false, 24);
  assert(releaseNoise.update(false, -1, false, 60) == 4);

  // Moving past the drawn edge within retention tolerance stays captured.
  TouchGesture edge;
  edge.update(true, 4, false, 0);
  edge.update(true, 4, false, 12);
  edge.update(true, -1, true, 30);
  edge.update(true, -1, true, 60);
  assert(edge.update(false, -1, false, 96) == 4);

  // Deliberately dragging off cancels; sliding onto another button or back
  // cannot transfer/revive the gesture.
  TouchGesture drag;
  drag.update(true, 4, false, 0);
  drag.update(true, 4, false, 12);
  drag.update(true, 2, false, 24);
  drag.update(true, 2, false, 36);
  drag.update(true, 2, false, 60);
  assert(drag.pressed == -1);
  drag.update(true, 4, true, 72);
  assert(drag.update(false, -1, false, 108) == -1);

  // A gesture beginning away from buttons cannot slide in much later.
  TouchGesture slideIn;
  slideIn.update(true, -1, false, 0);
  slideIn.update(true, 4, false, 180);
  slideIn.update(true, 4, false, 192);
  assert(slideIn.update(false, -1, false, 228) == -1);

  // Changed/disabled app actions explicitly cancel an in-flight touch.
  TouchGesture disabled;
  disabled.update(true, 1, false, 0);
  disabled.update(true, 1, false, 12);
  disabled.cancel();
  assert(disabled.update(false, -1, false, 60) == -1);

  // One sensor reading or an implausibly short gesture is insufficient.
  TouchGesture spike;
  spike.update(true, 4, false, 0);
  assert(spike.update(false, -1, false, 60) == -1);
  spike.update(true, 4, false, 100);
  spike.update(true, 4, false, 112);
  assert(spike.update(false, -1, false, 120) == -1);

  // Cancellation does not poison the next independent tap.
  drag.update(true, 0, false, 200);
  drag.update(true, 0, false, 212);
  assert(drag.update(false, -1, false, 260) == 0);

  // millis() wrap-around does not break the minimum duration.
  TouchGesture wrap;
  wrap.update(true, 4, false, UINT32_MAX - 20);
  wrap.update(true, 4, false, UINT32_MAX - 8);
  assert(wrap.update(false, -1, false, 40) == 4);

  // A display redraw can delay the next poll; a steady target still works.
  TouchGesture redraw;
  redraw.update(true, 4, false, 0);
  redraw.update(true, 4, false, 200);
  assert(redraw.update(false, -1, false, 260) == 4);
  std::puts("PASS: 11 resistive touch gesture scenarios");
}
