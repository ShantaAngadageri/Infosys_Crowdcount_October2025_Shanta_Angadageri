import os
import time
import sqlite3
from datetime import datetime, timedelta
from functools import wraps
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, jsonify, Response,
    make_response, send_file
)
import jwt  # PyJWT
from collections import deque
from crowd_detect import detect_crowd
from video_analysis import stream_video_with_data, stop_stream, get_unique_count, generate_live_frames
import visualization
import numpy as np
import cv2

app = Flask(__name__)
app.secret_key = "your-secret-key"

JWT_SECRET_KEY = "your-jwt-secret-key"
JWT_ALGORITHM = "HS256"
JWT_EXP_DELTA_SECONDS = 3600

UPLOAD_FOLDER = 'static/uploads'
OUTPUT_FOLDER = 'static/outputs'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024    #max:500mb
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

ZONE_HISTORY = {'Zone 1': [], 'Zone 2': []}
RECENT_POINTS_ZONE1 = deque(maxlen=1000)
RECENT_POINTS_ZONE2 = deque(maxlen=1000)
ZONE_TIMESTAMPS = []

# Initialize DB with STUDENT table and default user
def init_db():
    connection = sqlite3.connect('LoginData.db')
    cursor = connection.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS STUDENT (
                      first_name TEXT NOT NULL,
                      last_name TEXT NOT NULL,
                      email TEXT PRIMARY KEY,
                      password TEXT NOT NULL,
                      role TEXT DEFAULT 'user')''')
    cursor.execute("""
        INSERT OR IGNORE INTO STUDENT (first_name, last_name, email, password, role)
        VALUES ('tester', 'test', 'tester@gmail.com', 'tester123', 'admin')
    """)
    connection.commit()
    connection.close()

init_db()


# JWT token creation
def create_jwt_token(username):
    payload = {
        'sub': username,
        'iat': datetime.utcnow(),
        'exp': datetime.utcnow() + timedelta(seconds=JWT_EXP_DELTA_SECONDS)
    }
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token


# Token-required decorator
def token_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.cookies.get('access_token')
        if not token:
            flash("Authentication required, please log in.")
            return redirect(url_for('home'))
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            session['username'] = payload['sub']
        except jwt.ExpiredSignatureError:
            flash("Session expired, please log in again.")
            return redirect(url_for('home'))
        except jwt.InvalidTokenError:
            flash("Invalid token, please log in.")
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function



@app.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    password = request.form['password']
    print(f"Login attempt with email={email}, password={password}")  # Debug
    conn = sqlite3.connect('LoginData.db')
    cursor = conn.cursor()
    cursor.execute("SELECT first_name, email, role FROM STUDENT WHERE email=? AND password=?", (email, password))
    user = cursor.fetchone()

    print(f"User found: {user}")  # Debug
    conn.close()
    if user:
        token = create_jwt_token(user[0])
        response = make_response(redirect(url_for('dashboard')))
        response.set_cookie('access_token', token, httponly=True, max_age=JWT_EXP_DELTA_SECONDS)
        session['username'] = user[0]
        session['email'] = user[1]
        session['role'] = user[2]
        return response
    else:
        flash("Invalid email or password. Please try again.")
        return redirect(url_for('home'))
    
@app.route('/registration')
def registration():
    return render_template('registration.html')

@app.route('/add_user', methods=['POST'])
@token_required
def add_user():
    first_name = request.form['fname']
    last_name = request.form['lname']
    email = request.form['email'].strip().lower()  # normalize email
    password = request.form['password'].strip()

    role = request.form.get('role', 'user')
    conn = sqlite3.connect('LoginData.db')
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO STUDENT (first_name, last_name, email, password, role) VALUES (?, ?, ?, ?, ?)",
                       (first_name, last_name, email, password, role))
        conn.commit()
        flash("Registration successful! Please log in.")
    except sqlite3.IntegrityError:
        flash("Email already exists. Try logging in.")
    finally:
        conn.close()
    return redirect(url_for('home'))

@app.route('/users_data')
@token_required
def users_data():
    try:
        connection = sqlite3.connect('LoginData.db')
        cursor = connection.cursor()
        cursor.execute("SELECT first_name, last_name, email, role FROM STUDENT")
        rows = cursor.fetchall()
        connection.close()

        users = [{"first_name": r[0], "last_name": r[1], "email": r[2], "role": r[3], "status": "Active"} for r in rows]
        return jsonify({'users': users})

    except Exception as e:
        return jsonify({"error": str(e)}), 500



@app.route('/dashboard')
@token_required
def dashboard():
    mode = request.args.get('mode')
    video_path = request.args.get('video_path')

    if mode is None:
        return render_template('index.html', username=session.get('username'), active_page='dashboard')
    elif mode == 'upload':
        return redirect(url_for('image_analysis'))
    elif mode == 'video':
        return redirect(url_for('video_analysis', video_path=video_path))
    elif mode == 'webcam':
        return redirect(url_for('webcam_feed_page'))
    elif mode == 'user':
        if session.get('role', '').lower() == 'admin':
            return render_template('user_management.html', username=session.get('username'), active_page='user')
        else:
            flash("You do not have permission to access the user management page.")
            return redirect(url_for('dashboard'))
    else:
        flash("Invalid mode selected.")
        return redirect(url_for('home'))



def update_heatmap_image(points_zone1, points_zone2):
    visualization.save_heatmap_image(points_zone1, points_zone2)


@app.route('/video_analysis_stream')
@token_required
def video_analysis_stream():
    video_path = request.args.get("video_path")
    if not video_path or not os.path.exists(video_path):
        return "No video uploaded or invalid path.", 400
    def generate():
        for frame_bytes, data in stream_video_with_data(video_path):
            centers_zone1 = data.get('centers_zone1', [])
            centers_zone2 = data.get('centers_zone2', [])
            zone_counts = data.get('zone_counts', {})
            zone1_count = zone_counts.get('Zone 1', 0)
            zone2_count = zone_counts.get('Zone 2', 0)
            print(f"[VIDEO] Appending Zone Counts: Zone1: {zone1_count}, Zone2: {zone2_count}")
            ZONE_HISTORY['Zone 1'].append(zone1_count)
            ZONE_HISTORY['Zone 2'].append(zone2_count)
            ZONE_TIMESTAMPS.append(datetime.utcnow().isoformat())
            print(f"[VIDEO] Total ZONE_HISTORY Zone 1: {ZONE_HISTORY['Zone 1']}")
            print(f"[VIDEO] Total ZONE_HISTORY Zone 2: {ZONE_HISTORY['Zone 2']}")
            update_heatmap_image(centers_zone1, centers_zone2)
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/zone_population_charts')
@token_required
def zone_population_charts():
    bar_chart_img, line_chart_img = visualization.create_population_charts(ZONE_HISTORY, ZONE_TIMESTAMPS)
    return jsonify({'bar_chart': bar_chart_img, 'line_chart': line_chart_img})

@app.route('/download_zone_counts_csv')
@token_required
def download_zone_counts_csv():
    _, csv_path = visualization.create_zone_barchart_and_csv(ZONE_HISTORY, ZONE_TIMESTAMPS)
    return send_file(csv_path, mimetype='text/csv', as_attachment=True, download_name='zone_counts.csv')

@app.errorhandler(413)
def request_entity_too_large(error):
    flash("File is too large. Max size allowed is 500MB.")
    return redirect(request.referrer or url_for('dashboard'))

@app.route('/')
def home():
    return render_template('login.html')






@app.route('/image-analysis', methods=['GET', 'POST'])
@token_required
def image_analysis():
    if 'username' not in session:
        return redirect(url_for('home'))
    image_url = None
    output_url = None
    count = None
    stored_filename = None
    if request.method == 'POST':
        if 'view_image' in request.form:
            file = request.files.get('image')
            if file and file.filename != '':
                ext = file.filename.rsplit('.', 1)[-1].lower()
                filename = f"{int(time.time()*1000)}.{ext}"
                save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(save_path)
                stored_filename = filename
                session['stored_filename'] = filename
                image_url = 'uploads/' + filename
        elif 'analyse_image' in request.form:
            stored_filename = request.form.get('stored_filename') or session.get('stored_filename')
            if stored_filename:
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], stored_filename)
                output_path = os.path.join(app.config['OUTPUT_FOLDER'], stored_filename)
                count, _ = detect_crowd(image_path, output_path)
                output_url = 'outputs/' + stored_filename
                image_url = 'uploads/' + stored_filename
    else:
        stored_filename = session.get('stored_filename')
    return render_template('image_analysis.html', username=session.get('username'), image_url=image_url, output_url=output_url, count=count, stored_filename=stored_filename, active_page='image')

@app.route('/video-analysis', methods=['GET', 'POST'])
@token_required
def video_analysis():
    video_path = request.args.get('video_path')
    return render_template('video_analysis.html', username=session.get('username'), video_path=video_path, active_page='video')



@app.route('/launch_video_stream', methods=['POST'])
@token_required
def launch_video_stream():
    file = request.files.get('video')
    if not file or file.filename == '':
        flash("No video selected.")
        return redirect(url_for('video_analysis'))
    filename = f"{int(time.time() * 1000)}.mp4"
    input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(input_path)
    return redirect(url_for('video_analysis', video_path=input_path))

@app.route('/logout')
def logout():
    response = make_response(redirect(url_for('home')))
    response.delete_cookie('access_token')
    session.clear()
    flash("You have been logged out successfully.")
    return response

@app.route('/get_video_count')
@token_required
def get_video_count():
    video_path = request.args.get("video_path")
    count = get_unique_count(video_path)
    return jsonify({"count": count})

@app.route('/stop_video')
@token_required
def stop_video():
    video_path = request.args.get("video_path")
    if video_path:
        stop_stream(video_path)
    count = get_unique_count(video_path)
    return jsonify({"count": count})

@app.route('/generate_charts', methods=['POST'])
@token_required
def generate_charts():
    print(f"[CHART] Zone 1 History Before Chart: {ZONE_HISTORY['Zone 1']}")
    print(f"[CHART] Zone 2 History Before Chart: {ZONE_HISTORY['Zone 2']}")
    bar_chart_img, line_chart_img = visualization.create_population_charts(ZONE_HISTORY, ZONE_TIMESTAMPS)
    heatmap_path = "static/heatmap.png"
    heatmap_url = "heatmap.png" if os.path.exists(heatmap_path) else None
    return render_template('image_analysis.html', username=session.get('username'), image_url=session.get('stored_filename'), stored_filename=session.get('stored_filename'), bar_chart_img=bar_chart_img, line_chart_img=line_chart_img, heatmap_url=heatmap_url, active_page='image')



@app.route('/webcam-feed-page')
@token_required
def webcam_feed_page():
    return render_template('webcam.html', username=session.get('username'), active_page='webcam')

@app.route('/webcam_feed')
@token_required
def webcam_feed():
    # Simple raw webcam stream with video frames only (no zone counts)
    return Response(generate_live_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/webcam_stream')
@token_required
def webcam_stream():
    # Webcam stream with detection data yielding frames + zone counts for charting
    def generate():
        for frame_bytes, data in generate_live_frames():
            centers_zone1 = data.get('centers_zone1', [])
            centers_zone2 = data.get('centers_zone2', [])
            zone_counts = data.get('zone_counts', {})
            zone1_count = zone_counts.get('Zone 1', 0)
            zone2_count = zone_counts.get('Zone 2', 0)
            print(f"[WEBCAM] Appending Zone Counts: Zone1: {zone1_count}, Zone2: {zone2_count}")
            ZONE_HISTORY['Zone 1'].append(zone1_count)
            ZONE_HISTORY['Zone 2'].append(zone2_count)
            ZONE_TIMESTAMPS.append(datetime.utcnow().isoformat())
            update_heatmap_image(centers_zone1, centers_zone2)
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')


if __name__ == '__main__':
    app.run(debug=True, port=5550)
