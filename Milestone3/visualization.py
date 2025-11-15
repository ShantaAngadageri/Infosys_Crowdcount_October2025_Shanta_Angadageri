import matplotlib.pyplot as plt
import base64
from io import BytesIO
import numpy as np
import cv2

def create_population_charts(zone_history):
    """
    zone_history: dict mapping zone name -> list of population counts over time
    Returns base64 encoded bar and line chart images as strings.
    """
    zone_names = list(zone_history.keys())
    # Fix typo: use 'zone_history' instead of 'zone_hisctory'
    time_points = list(range(len(next(iter(zone_history.values())))))

    final_counts = [
        zone_history[zone][-1] if len(zone_history[zone]) > 0 else 0
        for zone in zone_names
    ]

    fig, ax = plt.subplots()
    ax.bar(zone_names, final_counts, color=['red', 'blue'])
    ax.set_title('Population per Zone (Final)')
    # Optional: add y-label for clarity
    ax.set_ylabel('Population Count')
    buf = BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    bar_chart_img = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)

    fig, ax = plt.subplots()
    for zone in zone_names:
        ax.plot(time_points, zone_history[zone], label=zone)
    ax.legend()
    ax.set_xlabel('Time')
    ax.set_ylabel('Number of People')
    ax.set_title('Population Over Time Per Zone')
    buf = BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    line_chart_img = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)

    return bar_chart_img, line_chart_img

def generate_heatmap(frame_shape, points, radius=50, intensity=100):
    """
    frame_shape: tuple (height, width)
    points: list of (x, y) coordinates
    radius: radius of circles to add as "heat"
    intensity: intensity value for each circle
    Returns a colored heatmap image.
    """
    # Create single-channel heatmap image
    heatmap = np.zeros((frame_shape[0], frame_shape[1]), dtype=np.uint8)
    for (x, y) in points:
        cv2.circle(heatmap, (int(x), int(y)), radius, intensity, -1)
    # Normalize heatmap for better visual effect
    heatmap = np.clip(heatmap, 0, 255)
    heatmap_color = cv2.applyColorMap(heatmap, cv2.COLORMAP_JET)
    return heatmap_color

def overlay_heatmap(frame, heatmap_color, alpha=0.5):
    """
    Overlays colored heatmap on a frame.
    frame: original image (HxWx3, np.uint8)
    heatmap_color: color heatmap image (same size as frame)
    alpha: blending factor (0-1)
    """
    # Ensure input types are np.uint8 and same shape
    frame = frame.astype(np.uint8)
    heatmap_color = heatmap_color.astype(np.uint8)
    overlay = cv2.addWeighted(frame, 1 - alpha, heatmap_color, alpha, 0)
    return overlay
