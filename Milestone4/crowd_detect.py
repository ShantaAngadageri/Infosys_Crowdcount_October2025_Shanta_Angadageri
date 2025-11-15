import torch
import cv2
from ultralytics import YOLO
import ultralytics.nn.tasks as tasks

# Allow saving/loading model safely with custom DetectionModel class
torch.serialization.add_safe_globals([tasks.DetectionModel])

# Load the YOLOv8 model (pretrained)
model = YOLO("yolov8n.pt")

def detect_crowd(image_path, output_path):
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Image not found or unable to load: {image_path}")
    
    height, width, _ = img.shape
    
    # Define zone1 boundary - left one-third of image width
    zone1_boundary = width // 3
    
    # Draw vertical line to separate zones (blue line)
    cv2.line(img, (zone1_boundary, 0), (zone1_boundary, height), (255, 0, 0), 2)
    
    # Detect only persons (class 0)
    results = model(img, classes=[0])
    
    total_count = 0
    zone1_count = 0
    zone2_count = 0
    
    for box in results[0].boxes:
        cls = int(box.cls[0])
        if results[0].names[cls] == 'person':
            total_count += 1
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            
            # Calculate center x coordinate of bounding box
            center_x = (x1 + x2) // 2
            
            # Determine zone based on center_x
            if center_x <= zone1_boundary:
                zone1_count += 1
                box_color = (0, 255, 0)  # Green for Zone 1
            else:
                zone2_count += 1
                box_color = (0, 165, 255)  # Orange for Zone 2
            
            # Draw bounding box with zone-specific color
            cv2.rectangle(img, (x1, y1), (x2, y2), box_color, 3)
    
    # Add text for total people and zone counts
    cv2.putText(img, f"Total People: {total_count}", (40, 40), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
    cv2.putText(img, f"Zone 1: {zone1_count}", (40, 80), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    cv2.putText(img, f"Zone 2: {zone2_count}", (40, 120), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 165, 255), 2)
    
    # Save the annotated image to output_path
    cv2.imwrite(output_path, img)
    
    # Return total count and zone-wise counts as dict
    return total_count, {'zone1': zone1_count, 'zone2': zone2_count, 'output_path': output_path}
