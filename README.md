Infosys_Crowdcount_October2025









### 1️⃣ Clone the Repository
```bash
git clone https://github.com/<your-username>/Infosys_Crowdcount_October2025_Shanta_Angadageri.git
cd Infosys_Crowdcount_October2025_Shanta_Angadageri





CrowdCount-App/
│
├── static/
│ ├── uploads/ # Uploaded images/videos
│ ├── outputs/ # Processed images
│ ├── heatmap.png # Updated heatmap
│ └── css/ & js/ (optional)
│
├── templates/
│ ├── login.html
│ ├── index.html
│ ├── registration.html
│ ├── user_management.html
│ ├── image_analysis.html
│ ├── video_analysis.html
│ ├── webcam.html
│
│── crowd_detect.py # Image detection logic
│── video_analysis.py # Video processing + streaming
│── visualization.py # Chart + heatmap generation
├── app.py # Main Flask Application
├── LoginData.db # SQLite database




Run Flask App
python app.py


App Runs On:
http://127.0.0.1:5550/



🎥 Video Analysis Workflow

Upload video

Live detection starts

Backend generates:

Live frame stream

Zone-wise population tracking

Charts and CSV available for download




📡 Webcam Workflow

Click "Webcam Mode"

Real-time detection starts

Heatmap & population trends update live




📊 Visualization Outputs
✔ Zone Bar Chart

Shows people count per zone

✔ Line Chart

Trend of crowd density over time

✔ Heatmap

Zone-based intensity visualization

✔ CSV Report

Exports zone counts with timestamps

  


🧩 Tech Stack
Component	Technology
Backend	Flask
Detection	YOLO / OpenCV
Visualization	Matplotlib
Authentication	JWT
Database	SQLite
Frontend	HTML, CSS, JS




