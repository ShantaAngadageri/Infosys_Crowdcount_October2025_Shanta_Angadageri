import cv2
from ultralytics import YOLO

# Load YOLO model
model = YOLO('yolov8n.pt')

_video_unique_ids = {}
_video_in_zone_ids = {}
_video_stop_flags = {}

ZONE_X1, ZONE_Y1 = 700, 0
ZONE_X2, ZONE_Y2 = 1024, 576
ZONE_THRESHOLD = 10


def put_text_rect(frame, text, pos, scale=1, thickness=2, color=(255, 255, 255), bg_color=(0, 0, 0)):
    font = cv2.FONT_HERSHEY_SIMPLEX
    text_size, _ = cv2.getTextSize(text, font, scale, thickness)
    x, y = pos
    rect_pt1 = (x, y - text_size[1] - 10)
    rect_pt2 = (x + text_size[0] + 10, y + 5)
    cv2.rectangle(frame, rect_pt1, rect_pt2, bg_color, cv2.FILLED)
    cv2.putText(frame, text, (x + 5, y - 5), font, scale, color, thickness)


def generate_live_frames():
    cap = cv2.VideoCapture(0)  # Default webcam

    # Reset unique IDs and in-zone IDs at the start of streaming
    _video_unique_ids["webcam"] = set()
    _video_in_zone_ids["webcam"] = set()
    _video_stop_flags["webcam"] = False

    while True:
        if _video_stop_flags.get("webcam", False):
            break
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.resize(frame, (1024, 576))

        results = model(frame, classes=[0])  # Detect people class only

        ids_in_zone = set()
        _video_unique_ids["webcam"] = set()  # Clear IDs before this frame's detections
        centers_zone1 = []
        centers_zone2 = []

        if results[0].boxes.xyxy is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy().astype(int)
            for idx, box in enumerate(boxes):
                x1, y1, x2, y2 = box
                cx = int((x1 + x2) / 2)
                cy = int((y1 + y2) / 2)
                track_id = f'frame_{idx}'

                _video_unique_ids["webcam"].add(track_id)

                if ZONE_X1 <= cx <= ZONE_X2 and ZONE_Y1 <= cy <= ZONE_Y2:
                    ids_in_zone.add(track_id)
                    centers_zone1.append((cx, cy))
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 255), 2)  # Cyan bounding box
                else:
                    centers_zone2.append((cx, cy))
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 255), 2)  # Magenta bounding box

                put_text_rect(frame, f'{track_id}', (x1, y1), 1, 1)

            _video_in_zone_ids["webcam"] = ids_in_zone
        else:
            # No detections in this frame, clear sets to show zero count
            _video_unique_ids["webcam"] = set()
            _video_in_zone_ids["webcam"] = set()

        # Draw zone rectangle
        cv2.rectangle(frame, (ZONE_X1, ZONE_Y1), (ZONE_X2, ZONE_Y2), (0, 0, 255), 3)  # Red zone boundary

        count_zone1 = len(ids_in_zone)
        total_unique_count = len(_video_unique_ids["webcam"])

        put_text_rect(frame, f'Zone 1: {count_zone1}', (30, 40), 2, 2)
        put_text_rect(frame, f'Total: {total_unique_count}', (30, 90), 2, 2)

        ret, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()

        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

    cap.release()


def stop_stream(source="webcam"):
    _video_stop_flags[source] = True


def get_unique_count(source="webcam"):
    return len(_video_unique_ids.get(source, set()))


def get_zone_count(source="webcam"):
    return len(_video_in_zone_ids.get(source, set()))
