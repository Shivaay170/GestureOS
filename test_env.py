import cv2
import mediapipe as mp
import numpy as np

print("✅ Environment check")
print("OpenCV version   :", cv2.__version__)
print("MediaPipe version:", mp.__version__)
print("NumPy version    :", np.__version__)

# This is the critical test
print("Hands module OK  :", mp.solutions.hands)
