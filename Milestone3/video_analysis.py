import cv2
from ultralytics import YOLO

model = YOLO('yolov8n.pt')

# Initialize global dictionaries
_video_unique_ids = {}      # video_path -> set of unique detected IDs
_video_in_zone_ids = {}     # video_path -> set of IDs currently in the zone
_video_stop_flags = {}      # video_path -> bool flag to stop streaming

ZONE_X1, ZONE_Y1 = 700, 0
ZONE_X2, ZONE_Y2 = 1024, 576

ZONE_THRESHOLD = 10

def put_text_rect(frame, text, pos, scale=1, thickness=2, color=(255,255,255), bg_color=(0,0,0)):
    """
    Draws a background rectangle with text on the frame.
    """
    font = cv2.FONT_HERSHEY_SIMPLEX
    text_size, _ = cv2.getTextSize(text, font, scale, thickness)
    x, y = pos
    rect_pt1 = (x, y - text_size[1] - 10)
    rect_pt2 = (x + text_size[0] + 10, y + 5)
    cv2.rectangle(frame, rect_pt1, rect_pt2, bg_color, cv2.FILLED)
    cv2.putText(frame, text, (x + 5, y - 5), font, scale, color, thickness)

def stream_video_with_data(video_path):
    """
    Generator that streams video frames with detection and count data.
    """
    # Ensure dicts are initialized
    _video_unique_ids.setdefault(video_path, set())
    _video_in_zone_ids.setdefault(video_path, set())
    _video_stop_flags.setdefault(video_path, False)

    cap = cv2.VideoCapture(video_path)

    while True:
        if _video_stop_flags.get(video_path, False):
            break

        ret, frame = cap.read()
        if not ret:
            break

        # Resize to match zone box size
        frame = cv2.resize(frame, (1024, 576))

        # Run object detection and tracking
        results = model.track(frame, persist=True, classes=[0], tracker="bytetrack.yaml", conf=0.25)

        ids_in_zone = set()
        centers_in_zone = []

        if results[0].boxes.id is not None:
            ids = results[0].boxes.id.cpu().numpy().astype(int)
            boxes = results[0].boxes.xyxy.cpu().numpy().astype(int)

            for track_id, box in zip(ids, boxes):
                x1, y1, x2, y2 = box
                cx = int((x1 + x2) / 2)
                cy = int((y1 + y2) / 2)

                # Add to unique IDs
                _video_unique_ids[video_path].add(track_id)

                # Check if inside zone
                if ZONE_X1 <= cx <= ZONE_X2 and ZONE_Y1 <= cy <= ZONE_Y2:
                    ids_in_zone.add(track_id)
                    centers_in_zone.append((cx, cy))
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 255), 2)
                else:
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 255), 2)

                # Add ID label
                put_text_rect(frame, f'{track_id}', (x1, y1), 1, 1)

        # Update in-zone IDs
        _video_in_zone_ids[video_path] = ids_in_zone

        # Draw zone rectangle
        cv2.rectangle(frame, (ZONE_X1, ZONE_Y1), (ZONE_X2, ZONE_Y2), (0, 0, 255), 3)

        # Count in-zone and total
        people_in_zone_count = len(_video_in_zone_ids.get(video_path, set()))
        total_unique_count = len(_video_unique_ids.get(video_path, set()))

        # Draw counts
        put_text_rect(frame, f'People in Zone: {people_in_zone_count}', (30, 40), 2, 2)
        put_text_rect(frame, f'Total People: {total_unique_count}', (30, 90), 2, 2)

        # Alert if threshold exceeded
        if people_in_zone_count > ZONE_THRESHOLD:
            out_h, out_w = frame.shape[:2]
            put_text_rect(frame, "ALERT: Count Exceeded!", (int(out_w*0.3), out_h - 30), 2, 2, color=(0,0,255), bg_color=(255,255,255))

        # Encode frame as JPEG
        ret, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()

        yield frame_bytes, {
            'centers_in_zone': centers_in_zone,
            'zone_count': people_in_zone_count,
            'total_count': total_unique_count
        }

    cap.release()

def stream_video(video_path):
    """
    Simple stream generator yielding raw frames.
    """
    for frame_bytes, _ in stream_video_with_data(video_path):
        yield frame_bytes

def stop_stream(video_path):
    """
    Signal to stop streaming
    """
    _video_stop_flags[video_path] = True

def get_unique_count(video_path):
    """
    Get total unique detected IDs
    """
    return len(_video_unique_ids.get(video_path, set()))

def get_zone_count(video_path):
    """
    Get current count of IDs in zone
    """
    return len(_video_in_zone_ids.get(video_path, set()))
