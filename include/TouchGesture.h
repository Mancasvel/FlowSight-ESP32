#pragma once
#include <stdint.h>

// Resistive panels can report a displaced point as contact starts or ends.
// Confirm the initial target, retain it across isolated noise, and still cancel
// a deliberate drag. A gesture never transfers to another button after capture.
class TouchGesture {
 public:
  int pressed = -1;
  const char* result = "none";

  void cancel() {
    pressed = -1;
    cancelled_ = true;
  }

  int update(bool down, int target, bool insidePressed, uint32_t now) {
    if (down && !down_) {
      pressed = -1;
      candidate_ = -1;
      candidateSamples_ = outsideSamples_ = 0;
      cancelled_ = false;
      started_ = now;
      result = "holding";
    }
    int released = -1;
    if (down && !cancelled_) {
      if (pressed < 0) {
        if (now - started_ > 150 && target != candidate_) {
          cancel();
        } else {
          if (target != candidate_) {
            candidate_ = target;
            candidateSamples_ = 0;
          }
          if (target >= 0 && ++candidateSamples_ >= 2) pressed = target;
        }
      } else if (insidePressed) {
        outsideSamples_ = 0;
      } else {
        if (outsideSamples_++ == 0) outsideSince_ = now;
        if (outsideSamples_ >= 3 && now - outsideSince_ >= 36) cancel();
      }
    } else if (!down && down_) {
      if (!cancelled_ && pressed >= 0 && now - started_ >= 35) {
        released = pressed;
        result = "tap";
      } else {
        result = cancelled_ ? "cancelled" : "unconfirmed";
      }
      pressed = -1;
    }
    down_ = down;
    return released;
  }

 private:
  bool down_ = false, cancelled_ = false;
  int candidate_ = -1;
  uint8_t candidateSamples_ = 0, outsideSamples_ = 0;
  uint32_t started_ = 0, outsideSince_ = 0;
};
