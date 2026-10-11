"""Exercise a freshly installed device. Resets its timer and test session count."""
import argparse
import json
from pathlib import Path
import time
from device import Device


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--port")
    p.add_argument("--fresh-device", action="store_true", required=True,
                   help="Acknowledge that this test resets the timer and session count.")
    p.add_argument("--output", type=Path, default=Path(".local/device-verification.json"))
    args = p.parse_args()
    d = Device(args.port)
    checks = []

    def check(condition, name):
        if not condition:
            raise AssertionError(name)
        checks.append(name)
        print("PASS: " + name, flush=True)

    def rejects(command, expected, **params):
        try:
            d.request(command, **params)
        except RuntimeError as error:
            check(str(error) == expected, command + " rejects " + expected)
        else:
            raise AssertionError(command + " unexpectedly accepted")

    try:
        d.request("reset")
        d.request("mode", value="focus")
        d.request("duration", minutes=1)
        d.request("clear_sessions", confirm=True)
        rejects("duration", "invalid_duration", minutes=0)
        rejects("duration", "invalid_duration", minutes=181)
        rejects("resume", "not_paused")
        started = d.request("start")
        time.sleep(1.25)
        running = d.request("status")
        check(started["phase"] == running["phase"] == "running" and
              1000 <= started["remaining_ms"] - running["remaining_ms"] <= 1800,
              "wall-clock countdown")
        paused = d.request("pause")
        time.sleep(1.25)
        check(d.request("status")["remaining_ms"] == paused["remaining_ms"], "pause freezes time")
        d.capture(Path("artifacts/device-paused.png"))
        rejects("duration", "session_active", minutes=25)
        rejects("mode", "session_active", value="break")
        d.request("resume")
        time.sleep(0.5)
        check(d.request("status")["remaining_ms"] < paused["remaining_ms"], "resume continues remaining time")
        confirmation = d.request("tap", x=260, y=200)
        check(confirmation["view"] == "confirm" and confirmation["phase"] == "running", "reset asks before discarding time")
        d.capture(Path("artifacts/device-confirm.png"))
        cancelled = d.request("tap", x=70, y=200)
        check(cancelled["view"] == "timer" and cancelled["phase"] == "running", "cancel preserves session")
        d.request("tap", x=260, y=200)
        reset = d.request("tap", x=240, y=200)
        check(reset["phase"] == "idle" and reset["seconds"] == 60, "confirmed reset")
        d.request("tap", x=270, y=23)
        plus = d.request("tap", x=276, y=129)
        check(plus["focus_minutes"] == 6, "settings +5 touch target")
        minus = d.request("tap", x=40, y=129)
        check(minus["focus_minutes"] == 1, "settings -5 touch target")
        d.request("home")
        d.request("start")
        beginning = time.monotonic()
        while time.monotonic() - beginning < 63:
            time.sleep(1)
            state = d.request("status")
            if state["phase"] == "complete":
                break
        elapsed = time.monotonic() - beginning
        check(state["phase"] == "complete" and state["seconds"] == 0 and
              state["completed_sessions"] == 1 and 59 <= elapsed < 63,
              "real one-minute expiry and single completion count")
        time.sleep(1)
        check(d.request("status")["completed_sessions"] == 1, "completion does not count twice")
        rest = d.request("tap", x=100, y=200)
        check(rest["mode"] == "break" and rest["phase"] == "running", "completed-session break action")
        d.request("reset")
        d.request("duration", minutes=5)
        d.request("mode", value="focus")
        d.request("duration", minutes=25)
        d.request("clear_sessions", confirm=True)
        d.request("start")
        time.sleep(0.25)
        checkpoint = d.request("pause")
        d.serial.rts = True
        time.sleep(0.15)
        d.serial.rts = False
        time.sleep(2.5)
        restored = d.request("status")
        check(restored["phase"] == "paused" and restored["remaining_ms"] == checkpoint["remaining_ms"],
              "reset restores exact paused checkpoint from flash")
        d.request("reset")
        d.request("tap", x=270, y=23)
        d.capture(Path("artifacts/device-settings.png"))
        d.request("home")
        d.capture(Path("artifacts/device-screen.png"))
        final = d.request("status")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps({"checks": checks, "physical_touch_tested": False,
                                         "final_state": final}, indent=2))
        print("PASS: " + str(len(checks)) + " checks. Physical touch alignment needs a person.")
    finally:
        d.close()


if __name__ == "__main__":
    main()
