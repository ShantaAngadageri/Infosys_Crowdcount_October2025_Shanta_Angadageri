import matplotlib
matplotlib.use('Agg')     #Agg' is a raster backend (Anti-Grain Geometry) that generates image files 
import matplotlib.pyplot as plt
import base64
from io import BytesIO      #For encoding binary image data as string (great for HTML embedding).
import pandas as pd

def create_zone_barchart_and_csv(zone_history, timestamps, csv_filename="static/zone_counts.csv"):
    area1 = [v for v in zone_history.get('Zone 1', [])]
    area2 = [v for v in zone_history.get('Zone 2', [])]
    zone_labels = ['Zone1', 'Zone2']
    total_counts = [
        area1[-1] if area1 else 0,
        area2[-1] if area2 else 0
    ]
    fig, ax = plt.subplots(figsize=(7, 4))
    bars = ax.bar(zone_labels, total_counts, color=['#1976d2', '#00bfae'], width=0.5)
    ax.set_ylabel('Count')
    ax.set_xlabel('Area')
    ax.set_title('Zone Occupancy')
    for bar in bars:
        height = bar.get_height()
        ax.annotate(f'{int(height)}', xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 5), textcoords="offset points",
                    ha='center', va='bottom', color='white', fontsize=13, fontweight='bold')
    plt.tight_layout()
    buf = BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    bar_chart_img = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)

    df = pd.DataFrame({
        'area1count': area1,
        'area2count': area2,
        'timestamp': timestamps
    })
    df.to_csv(csv_filename, index=False)
    return bar_chart_img, csv_filename

def create_population_line_chart(zone_history):
    zone_names = list(zone_history.keys())
    time_points = list(range(len(next(iter(zone_history.values())))))
    fig, ax = plt.subplots(figsize=(8, 4))
    for idx, zone in enumerate(zone_names):
        ax.plot(time_points, zone_history[zone], label=zone, linewidth=2)
    ax.legend()
    ax.set_xlabel('Time')
    ax.set_ylabel('Number of People')
    ax.set_title('Population Over Time Per Zone')
    plt.tight_layout()
    buf = BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    line_chart_img = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)
    return line_chart_img

def save_heatmap_image(points_zone1, points_zone2, filename="static/heatmap.png"):
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.set_facecolor('#151e3f')
    fig.patch.set_facecolor('#151e3f')
    sizes_zone1 = [350 for _ in points_zone1]
    sizes_zone2 = [220 for _ in points_zone2]
    if points_zone1:
        xs1 = [p[0] for p in points_zone1]
        ys1 = [p[1] for p in points_zone1]
        ax.scatter(xs1, ys1, s=sizes_zone1, c='#1976d2', alpha=0.65, edgecolors='white', linewidths=2, label='Zone 1')
    if points_zone2:
        xs2 = [p[0] for p in points_zone2]
        ys2 = [p[1] for p in points_zone2]
        ax.scatter(xs2, ys2, s=sizes_zone2, c='#00bfae', alpha=0.65, edgecolors='white', linewidths=2, label='Zone 2')
    ax.set_title("Heatmap", color='white', fontsize=18, pad=12)
    ax.set_xlabel("X", color='white', fontsize=13)
    ax.set_ylabel("Y", color='white', fontsize=13)
    ax.tick_params(colors='white')
    ax.legend(frameon=False, fontsize=13)
    plt.tight_layout()
    plt.savefig(filename, bbox_inches='tight', transparent=False)
    plt.close(fig)

def create_population_charts(zone_history, timestamps):
    bar_chart_img, _ = create_zone_barchart_and_csv(zone_history, timestamps)
    line_chart_img = create_population_line_chart(zone_history)
    return bar_chart_img, line_chart_img
