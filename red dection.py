"""
Real-Time Vision & Logic Challenge
===================================
Detects a bright RED object via webcam.
A rectangular ROI (Region of Interest) is drawn on screen.
Counter increments each time the object ENTERS and then EXITS the ROI.

Author  : [Your Name]
Task    : AI / Software Engineering Internship
"""

import cv2
import numpy as np

# ──────────────────────────────────────────────
# CONFIGURATION
# ──────────────────────────────────────────────
# HSV range for RED color detection
# Red wraps around in HSV, so we use two ranges and combine them
RED_LOWER1 = np.array([0,   120,  70])
RED_UPPER1 = np.array([10,  255, 255])
RED_LOWER2 = np.array([170, 120,  70])
RED_UPPER2 = np.array([180, 255, 255])

# Minimum contour area to ignore tiny noise blobs (in pixels²)
MIN_CONTOUR_AREA = 1500

# ──────────────────────────────────────────────
# STATE VARIABLES
# ──────────────────────────────────────────────
count        = 0          # total valid trigger events
object_in_roi = False     # tracks whether object is currently inside the ROI


def get_roi(frame_w, frame_h):
    """
    Define the ROI rectangle as a centred box (40% width, 50% height).
    Returns (x1, y1, x2, y2).
    """
    x1 = int(frame_w * 0.30)
    y1 = int(frame_h * 0.25)
    x2 = int(frame_w * 0.70)
    y2 = int(frame_h * 0.75)
    return x1, y1, x2, y2


def is_centroid_in_roi(cx, cy, roi):
    """
    Check whether the object's centroid (cx, cy) lies inside the ROI.
    roi = (x1, y1, x2, y2)
    """
    x1, y1, x2, y2 = roi
    return x1 <= cx <= x2 and y1 <= cy <= y2


def detect_red_object(frame):
    """
    Convert frame to HSV, build a red mask (two ranges), denoise,
    and return the largest contour (or None if nothing found).
    """
    hsv  = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # Build red mask from both hue ranges
    mask1 = cv2.inRange(hsv, RED_LOWER1, RED_UPPER1)
    mask2 = cv2.inRange(hsv, RED_LOWER2, RED_UPPER2)
    mask  = cv2.bitwise_or(mask1, mask2)

    # ── Noise reduction ──────────────────────────────────
    # Morphological opening removes small specks (bonus: reduces false triggers)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    mask   = cv2.morphologyEx(mask, cv2.MORPH_OPEN,  kernel)
    mask   = cv2.morphologyEx(mask, cv2.MORPH_DILATE, kernel)
    # ─────────────────────────────────────────────────────

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL,
                                   cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        return None, mask

    # Pick the largest contour — most likely our target object
    largest = max(contours, key=cv2.contourArea)
    if cv2.contourArea(largest) < MIN_CONTOUR_AREA:
        return None, mask   # too small → treat as noise

    return largest, mask


def draw_ui(frame, roi, count, object_present, centroid=None, bbox=None):
    """
    Render all UI elements onto the frame:
      • ROI rectangle (green when object inside, blue otherwise)
      • Bounding box around detected object (yellow)
      • Centroid dot
      • Counter overlay
      • Instruction banner
    """
    x1, y1, x2, y2 = roi
    h, w = frame.shape[:2]

    # ── ROI rectangle ────────────────────────────────────
    roi_color = (0, 255, 0) if object_present else (255, 100, 0)
    cv2.rectangle(frame, (x1, y1), (x2, y2), roi_color, 2)
    cv2.putText(frame, "ROI", (x1 + 5, y1 - 8),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, roi_color, 2)

    # ── Bounding box + centroid of detected object ───────
    if bbox is not None:
        bx, by, bw, bh = bbox
        cv2.rectangle(frame, (bx, by), (bx + bw, by + bh), (0, 255, 255), 2)

    if centroid is not None:
        cv2.circle(frame, centroid, 6, (0, 0, 255), -1)

    # ── Counter (top-left) ───────────────────────────────
    cv2.rectangle(frame, (10, 10), (280, 50), (0, 0, 0), -1)   # dark bg
    cv2.putText(frame, f"Objects Counted: {count}",
                (18, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.9,
                (0, 255, 128), 2)

    # ── Status indicator ─────────────────────────────────
    status     = "IN ROI" if object_present else "outside"
    status_col = (0, 255, 0) if object_present else (100, 100, 255)
    cv2.putText(frame, f"Status: {status}",
                (18, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_col, 2)

    # ── Exit hint (bottom) ───────────────────────────────
    cv2.putText(frame, "Press 'q' to quit",
                (10, h - 12), cv2.FONT_HERSHEY_SIMPLEX,
                0.5, (200, 200, 200), 1)

    return frame


# ──────────────────────────────────────────────
# MAIN LOOP
# ──────────────────────────────────────────────
def main():
    global count, object_in_roi

    cap = cv2.VideoCapture(0)          # 0 = default webcam
    if not cap.isOpened():
        print("[ERROR] Could not open webcam.")
        return

    # Try to set a comfortable resolution
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    print("[INFO] Webcam opened. Hold a RED object in front of the camera.")
    print("[INFO] Press 'q' to quit.\n")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("[ERROR] Failed to grab frame.")
            break

        frame = cv2.flip(frame, 1)          # mirror for natural interaction
        h, w  = frame.shape[:2]
        roi   = get_roi(w, h)

        # ── Detect red object ────────────────────────────
        contour, _ = detect_red_object(frame)

        centroid = None
        bbox     = None
        currently_in = False

        if contour is not None:
            # Compute centroid via image moments
            M  = cv2.moments(contour)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
                centroid = (cx, cy)

            # Bounding rectangle for the visual box
            bbox = cv2.boundingRect(contour)

            # Check if centroid is inside ROI
            currently_in = is_centroid_in_roi(cx, cy, roi)

        # ── Trigger / counting logic ──────────────────────
        # A valid event = object ENTERS the ROI (False → True)
        #                 followed by EXITING  (True  → False)
        #
        # We count on the EXIT so each full pass = 1 count.
        if object_in_roi and not currently_in:
            # Object just left the ROI → complete trigger event
            count += 1
            print(f"[TRIGGER] Object exited ROI → Count = {count}")

        object_in_roi = currently_in   # update state for next frame

        # ── Draw UI ───────────────────────────────────────
        frame = draw_ui(frame, roi, count,
                        object_present=currently_in,
                        centroid=centroid,
                        bbox=bbox)

        cv2.imshow("Real-Time Vision Counter", frame)

        # ── Exit condition ────────────────────────────────
        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("[INFO] 'q' pressed — exiting.")
            break

    cap.release()
    cv2.destroyAllWindows()
    print(f"\n[DONE] Final count: {count}")


if __name__ == "__main__":
    main()