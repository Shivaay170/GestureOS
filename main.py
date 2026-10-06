
import cv2
import mediapipe as mp
import pyautogui
import math
import time
from collections import deque

# ================= CONFIGURATION =================
pyautogui.FAILSAFE = False

# Smoothing & Movement
SMOOTHING_FACTOR = 0.5  # Lower = more responsive (0.3-0.7)
MOVEMENT_THRESHOLD = 2
SCREEN_PADDING = 0.15

# Gesture Settings
GESTURE_HOLD_TIME = 0.15  # How long to hold gesture before triggering
DOUBLE_CLICK_COOLDOWN = 0.5

# ================= INITIALIZATION =================
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    max_num_hands=2,  # TWO HANDS!
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7,
    model_complexity=1
)
mp_draw = mp.solutions.drawing_utils

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
cap.set(cv2.CAP_PROP_FPS, 60)

screen_w, screen_h = pyautogui.size()

# Effective screen area
eff_w = int(screen_w * (1 - SCREEN_PADDING))
eff_h = int(screen_h * (1 - SCREEN_PADDING))
offset_x = int(screen_w * SCREEN_PADDING / 2)
offset_y = int(screen_h * SCREEN_PADDING / 2)

# ================= STATE VARIABLES =================
# Cursor smoothing (separate for each hand)
smooth_x_left = screen_w // 2
smooth_y_left = screen_h // 2
smooth_x_right = screen_w // 2
smooth_y_right = screen_h // 2

# Gesture states
right_gesture_start = 0
left_gesture_start = 0
last_double_click = 0
is_dragging = False

# Performance
fps_buffer = deque(maxlen=30)
last_time = time.time()

# ================= HELPER FUNCTIONS =================
def get_hand_label(hand_landmarks, hand_handedness):
    """Determine if hand is Left or Right"""
    return hand_handedness.classification[0].label

def count_extended_fingers(hand):
    """Count how many fingers are extended"""
    fingers_up = 0
    
    # Thumb - check x position relative to palm
    if hand.landmark[4].x < hand.landmark[3].x:  # Right hand
        if hand.landmark[4].x < hand.landmark[2].x:
            fingers_up += 1
    else:  # Left hand
        if hand.landmark[4].x > hand.landmark[2].x:
            fingers_up += 1
    
    # Other fingers - check if tip is above middle joint
    finger_tips = [8, 12, 16, 20]
    finger_mids = [6, 10, 14, 18]
    
    for tip, mid in zip(finger_tips, finger_mids):
        if hand.landmark[tip].y < hand.landmark[mid].y:
            fingers_up += 1
    
    return fingers_up

def is_fist(hand):
    """Check if hand is making a fist (0-1 fingers up)"""
    return count_extended_fingers(hand) <= 1

def is_open_hand(hand):
    """Check if hand is fully open (4-5 fingers up)"""
    return count_extended_fingers(hand) >= 4

def map_to_screen(x, y):
    """Map hand coordinates to screen"""
    screen_x = int(x * eff_w + offset_x)
    screen_y = int(y * eff_h + offset_y)
    
    screen_x = max(0, min(screen_w - 1, screen_x))
    screen_y = max(0, min(screen_h - 1, screen_y))
    
    return screen_x, screen_y

def smooth_movement(target_x, target_y, hand="left"):
    """Apply smoothing to cursor movement"""
    global smooth_x_left, smooth_y_left, smooth_x_right, smooth_y_right
    
    if hand == "left":
        smooth_x_left = smooth_x_left * SMOOTHING_FACTOR + target_x * (1 - SMOOTHING_FACTOR)
        smooth_y_left = smooth_y_left * SMOOTHING_FACTOR + target_y * (1 - SMOOTHING_FACTOR)
        return int(smooth_x_left), int(smooth_y_left)
    else:  # right
        smooth_x_right = smooth_x_right * SMOOTHING_FACTOR + target_x * (1 - SMOOTHING_FACTOR)
        smooth_y_right = smooth_y_right * SMOOTHING_FACTOR + target_y * (1 - SMOOTHING_FACTOR)
        return int(smooth_x_right), int(smooth_y_right)

def draw_ui(frame, left_gesture, right_gesture, fps):
    """Draw compact UI overlay"""
    h, w = frame.shape[:2]
    
    # Compact info box - top right corner
    box_w, box_h = 200, 70
    box_x = w - box_w - 10
    cv2.rectangle(frame, (box_x, 10), (box_x + box_w, 10 + box_h), (0, 0, 0), -1)
    cv2.rectangle(frame, (box_x, 10), (box_x + box_w, 10 + box_h), (0, 255, 0), 1)
    
    # Compact text
    cv2.putText(frame, f"L: {left_gesture[:12]}", (box_x + 10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 200, 255), 1)
    cv2.putText(frame, f"R: {right_gesture[:12]}", (box_x + 10, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 255, 100), 1)
    cv2.putText(frame, f"FPS: {fps:.0f}", (box_x + 10, 68),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

# ================= MAIN LOOP =================
print("🚀 Two-Hand Gesture Control Started!")
print("\n=== CONTROLS ===")
print("LEFT HAND (Blue):")
print("  ☝️  Index finger → Move cursor")
print("  ✊  Fist → Drag & hold")
print("\nRIGHT HAND (Green):")
print("  ☝️  Index finger → Move cursor (backup)")
print("  🖐️  Open hand (5 fingers) → Double click")
print("  ✊  Fist → Left click")
print("\nPress ESC to exit\n")

while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    frame = cv2.flip(frame, 1)
    h, w, _ = frame.shape
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = hands.process(rgb)
    
    # Calculate FPS
    current_time = time.time()
    fps_buffer.append(1 / (current_time - last_time + 0.0001))
    last_time = current_time
    avg_fps = sum(fps_buffer) / len(fps_buffer)
    
    # Default states
    left_hand_data = None
    right_hand_data = None
    left_gesture = "NO HAND"
    right_gesture = "NO HAND"
    
    # ================= DETECT HANDS =================
    if result.multi_hand_landmarks and result.multi_handedness:
        for hand_landmarks, handedness in zip(result.multi_hand_landmarks, result.multi_handedness):
            label = get_hand_label(hand_landmarks, handedness)
            
            # Draw landmarks with color coding
            if label == "Left":
                # Draw left hand in BLUE
                connections_color = (255, 200, 100)  # Blue
                landmark_color = (255, 100, 100)
                mp_draw.draw_landmarks(
                    frame, hand_landmarks, mp_hands.HAND_CONNECTIONS,
                    mp_draw.DrawingSpec(color=landmark_color, thickness=2, circle_radius=3),
                    mp_draw.DrawingSpec(color=connections_color, thickness=2)
                )
                left_hand_data = hand_landmarks
            else:  # Right
                # Draw right hand in GREEN
                connections_color = (100, 255, 100)  # Green
                landmark_color = (100, 200, 100)
                mp_draw.draw_landmarks(
                    frame, hand_landmarks, mp_hands.HAND_CONNECTIONS,
                    mp_draw.DrawingSpec(color=landmark_color, thickness=2, circle_radius=3),
                    mp_draw.DrawingSpec(color=connections_color, thickness=2)
                )
                right_hand_data = hand_landmarks
    
    # ================= LEFT HAND CONTROL (CURSOR & DRAG) =================
    if left_hand_data:
        index_tip = left_hand_data.landmark[8]
        fingers_count = count_extended_fingers(left_hand_data)
        
        # Map cursor position
        target_x, target_y = map_to_screen(index_tip.x, index_tip.y)
        final_x, final_y = smooth_movement(target_x, target_y, hand="left")
        
        # Check gesture
        if is_fist(left_hand_data):
            # FIST = DRAG
            left_gesture = "DRAG"
            
            if not is_dragging:
                pyautogui.mouseDown(_pause=False)
                is_dragging = True
                print("🖱️ LEFT: Drag Started")
            
            # Move while dragging
            pyautogui.moveTo(final_x, final_y, _pause=False)
        
        else:
            # OPEN = MOVE CURSOR
            left_gesture = f"MOVE ({fingers_count}F)"
            
            # Release drag if was dragging
            if is_dragging:
                pyautogui.mouseUp(_pause=False)
                is_dragging = False
                print("🖱️ LEFT: Drag Released")
            
            # Move cursor
            pyautogui.moveTo(final_x, final_y, _pause=False)
    
    else:
        # No left hand - release drag
        if is_dragging:
            pyautogui.mouseUp(_pause=False)
            is_dragging = False
            print("🖱️ LEFT: Hand lost - Drag Released")
    
    # ================= RIGHT HAND CONTROL (CURSOR + CLICKS) =================
    if right_hand_data:
        index_tip = right_hand_data.landmark[8]
        fingers_count = count_extended_fingers(right_hand_data)
        
        # Map cursor position for right hand
        target_x, target_y = map_to_screen(index_tip.x, index_tip.y)
        final_x_right, final_y_right = smooth_movement(target_x, target_y, hand="right")
        
        # If only index finger up (1-2 fingers), use RIGHT hand for cursor control
        if fingers_count >= 1 and fingers_count <= 2:
            right_gesture = f"MOVE ({fingers_count}F)"
            
            # Move cursor with right hand (only if left hand not present)
            if not left_hand_data:
                pyautogui.moveTo(final_x_right, final_y_right, _pause=False)
        
        # OPEN HAND = DOUBLE CLICK
        elif is_open_hand(right_hand_data):
            right_gesture = f"OPEN ({fingers_count}F)"
            
            # Track how long hand has been open
            if right_gesture_start == 0:
                right_gesture_start = time.time()
            
            # Trigger after hold time
            elif (time.time() - right_gesture_start) >= GESTURE_HOLD_TIME:
                if (time.time() - last_double_click) > DOUBLE_CLICK_COOLDOWN:
                    right_gesture = "DBL CLICK!"
                    pyautogui.doubleClick(_pause=False)
                    last_double_click = time.time()
                    print(" RIGHT: DOUBLE CLICK!")
                    right_gesture_start = 0 
        
       
        elif is_fist(right_hand_data):
            right_gesture = f"FIST ({fingers_count}F)"
            
           
            if left_gesture_start == 0:
                left_gesture_start = time.time()
            
          
            elif (time.time() - left_gesture_start) >= GESTURE_HOLD_TIME:
                right_gesture = "CLICK!"
                pyautogui.click(button='left', _pause=False)
                print(" RIGHT: Left Click")
                left_gesture_start = 0  
                time.sleep(0.2)  
        
        else:
            
            right_gesture = f"READY ({fingers_count}F)"
            right_gesture_start = 0
            left_gesture_start = 0
    
    else:
    
        right_gesture_start = 0
        left_gesture_start = 0
    
   
    draw_ui(frame, left_gesture, right_gesture, avg_fps)
    cv2.imshow("Two-Hand Gesture Control", frame)
    
    if cv2.waitKey(1) & 0xFF == 27:  
        break


if is_dragging:
    pyautogui.mouseUp()

cap.release()
cv2.destroyAllWindows()
print("\n Gesture Control Stopped")