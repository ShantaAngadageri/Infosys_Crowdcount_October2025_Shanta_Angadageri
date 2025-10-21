import torch
import cv2
from ultralytics import YOLO
import ultralytics.nn.tasks as tasks

torch.serialization.add_safe_globals([tasks.DetectionModel])
model = YOLO("yolov8n.pt")

def detect_crowd(image_path, output_path):
    img = cv2.imread(image_path)
    results = model(img, classes=[0])
    person_count = 0
    for box in results[0].boxes:
        cls = int(box.cls[0])
        if results[0].names[cls] == 'person':
            person_count += 1
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 3)
    cv2.putText(img, f"People: {person_count}", (40, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
    cv2.imwrite(output_path, img)
    return person_count, output_path
