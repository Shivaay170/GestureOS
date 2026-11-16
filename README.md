<div align="center">

# GestureOS
**Two hands. A webcam. Desktop control.**

An experimental Python interface that turns hand landmarks into cursor movement, clicks, and drag-and-drop.

[Controls](#controls) · [Run locally](#run-locally) · [Record a demo](#record-a-demo)

</div>

---

## What it does

GestureOS explores an alternative to mouse input using OpenCV, MediaPipe hand tracking, and PyAutoGUI. The camera preview shows hand landmarks, gesture state, and a rolling FPS estimate while gestures drive the desktop.

**Status:** experimental desktop prototype. Despite the name, this is an input-control application, not an operating system. Behavior below is documented from `main.py`; it has not been validated across hardware configurations.

## Controls

| Input | Behavior in the current code |
| :--- | :--- |
| Left hand visible, not a fist | Move the cursor using the index fingertip |
| Left fist, classified as 0–1 extended fingers | Hold the left mouse button and drag |
| Open the left hand or remove it from view | Release the drag |
| Right hand with 1–2 extended fingers | Move the cursor when the left hand is absent |
| Right open hand with 4–5 extended fingers | Double-click after a hold; repeated clicks have a cooldown |
| Right closed fist with 0 extended fingers | Left-click after a hold |
| Escape with the camera window focused | Exit |

The right-hand movement branch takes precedence for one extended finger. There is no dedicated close-window gesture. Opening a file uses the normal desktop double-click behavior.

## How it works

1. OpenCV reads and mirrors frames from camera index `0`.
2. MediaPipe identifies up to two hands and their landmarks.
3. Finger-position heuristics classify gestures.
4. Normalized fingertip coordinates are mapped to the screen and smoothed.
5. Gesture state triggers PyAutoGUI mouse actions.

The left-hand drag state is released when tracking is lost. The right-hand click path uses hold timers, while cursor movement uses exponential smoothing.

## Run locally

Use a Windows desktop with a webcam and a Python environment compatible with MediaPipe's `mp.solutions.hands` API.

```powershell
git clone https://github.com/Shivaay170/GestureOS.git
cd GestureOS
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install opencv-python mediapipe pyautogui
.\.venv\Scripts\python.exe main.py
```

Dependency versions are not pinned in this repository. If `mp.solutions` is unavailable, the installed MediaPipe API does not match this implementation; use a compatible release before running.

**Before testing:** use a blank desktop or disposable folder. The script currently disables PyAutoGUI's corner failsafe, so moving the pointer to a corner will not stop it. Keep the camera window accessible for Escape, or stop the process from its terminal.

## Tuning

| Constant | Current value | Purpose |
| :--- | :--- | :--- |
| `SMOOTHING_FACTOR` | `0.5` | Balance responsiveness against cursor jitter |
| `SCREEN_PADDING` | `0.15` | Inset the mapped cursor area |
| `GESTURE_HOLD_TIME` | `0.15` seconds | Delay right-hand click triggers |
| `DOUBLE_CLICK_COOLDOWN` | `0.5` seconds | Space repeated double-clicks |

The camera requests 1280 × 720 at 60 FPS. This is a capture setting, **not a measured performance guarantee**.

## Record a demo

Capture 20–30 seconds of the real desktop and camera preview together:

1. Show the cursor following the left hand.
2. Drag a disposable desktop item with a left fist.
3. Open the hand to release it.
4. Use a right open hand to double-click that item.
5. Show Escape exiting the application.

Keep the gesture overlay visible so viewers can connect the hand movement to the desktop action. Include the actual Python/package versions, camera, and hardware with the recording. Avoid private files and notifications. No demo video is included yet.

## Limitations and next steps

- Finger-count heuristics depend on hand orientation, lighting, and camera framing.
- Holding a gesture can trigger repeated clicks.
- Cursor mapping uses the primary screen dimensions; multi-monitor behavior needs validation.
- Dependency locking, calibration, a pause control, and a reliable emergency stop would improve reproducibility and usability.

## Repository guide

| File | Role |
| :--- | :--- |
| [main.py](main.py) | Camera capture, hand tracking, gesture logic, and mouse control |
| [test_env.py](test_env.py) | Existing environment-check script |
| [GestureOS-Readme.txt](GestureOS-Readme.txt) | Earlier project notes; this README documents current controls |

Built by [Shivaay Srivastava](https://github.com/Shivaay170).
