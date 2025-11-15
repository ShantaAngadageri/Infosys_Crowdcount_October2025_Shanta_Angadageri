from flask import Flask, render_template, request, redirect, url_for, session, flash, Response, jsonify
import sqlite3
import os
import time
from crowd_detect import detect_crowd
from webcam import generate_frames
from video_analysis import stream_video, stop_stream, get_unique_count, stream_video_with_data
import visualization

from collections import deque
import numpy as np
import cv2


app = Flask(__name__)
app.secret_key = "your-secret-key"  # Replace with a secure key in production

UPLOAD_FOLDER = 'static/uploads'
OUTPUT_FOLDER = 'static/outputs'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max upload

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# For tracking population history and recent heatmap points
ZONE_HISTORY = {'Zone': []}
RECENT_POINTS = deque(maxlen=1000)


def update_heatmap_image(centers):
    """
    Updates heatmap image file by drawing circles on a blank image corresponding to recent points.
    """
    RECENT_POINTS.extend(centers)

    blank_img = np.zeros((576, 1024), dtype=np.uint8)
    for (x, y) in RECENT_POINTS:
        cv2.circle(blank_img, (int(x), int(y)), 50, 120, -1)

    heatmap_color = cv2.applyColorMap(blank_img, cv2.COLORMAP_JET)
    heatmap_path = 'static/heatmap.png'
    cv2.imwrite(heatmap_path, heatmap_color)
    return heatmap_path


@app.route('/video_analysis_stream')
def video_analysis_stream():
    """
    Streaming route for video with population data and heatmap update.
    """
    video_path = request.args.get("video_path")
    if not video_path or not os.path.exists(video_path):
        return "No video uploaded or invalid path.", 400

    def generate():
        for frame_bytes, data in stream_video_with_data(video_path):
            centers = data.get('centers_in_zone', [])
            zone_count = data.get('zone_count', 0)

            ZONE_HISTORY['Zone'].append(zone_count)
            update_heatmap_image(centers)

            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/zone_population_charts')
def zone_population_charts():
    """
    Provides bar and line population charts encoded as base64 strings.
    """
    bar_chart_img, line_chart_img = visualization.create_population_charts(ZONE_HISTORY)
    return jsonify({
        'bar_chart': bar_chart_img,
        'line_chart': line_chart_img
    })


@app.errorhandler(413)
def request_entity_too_large(error):
    flash("File is too large. Max size allowed is 500MB.")
    return redirect(request.referrer or url_for('dashboard'))


@app.route('/')
def home():
    return render_template('login.html')


@app.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    password = request.form['password']
    connection = sqlite3.connect('LoginData.db')
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM USERS WHERE email=? AND password=?", (email, password))
    user = cursor.fetchone()
    connection.close()
    if user:
        session['username'] = user[0]
        session['email'] = user[2]
        return redirect(url_for('dashboard'))
    else:
        flash("Invalid email or password. Please try again.")
        return redirect(url_for('home'))


@app.route('/registration')
def registration():
    return render_template('registration.html')


@app.route('/add_user', methods=['POST'])
def add_user():
    first_name = request.form['fname']
    last_name = request.form['lname']
    email = request.form['email']
    password = request.form['password']
    connection = sqlite3.connect('LoginData.db')
    cursor = connection.cursor()
    try:
        cursor.execute("INSERT INTO USERS (first_name, last_name, email, password) VALUES (?, ?, ?, ?)",
                       (first_name, last_name, email, password))
        connection.commit()
        flash("Registration successful! Please log in.")
    except sqlite3.IntegrityError:
        flash("Email already exists. Try logging in.")
    finally:
        connection.close()
    return redirect(url_for('home'))


@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('home'))
    mode = request.args.get('mode')
    video_path = request.args.get('video_path')

    if mode is None:
        return render_template('index.html', username=session['username'], active_page='dashboard')
    elif mode == 'upload':
        return redirect(url_for('image_analysis'))
    elif mode == 'video':
        return redirect(url_for('video_analysis', video_path=video_path))
    elif mode == 'webcam':
        return redirect(url_for('webcam_feed_page'))
    else:
        flash("Invalid mode selected.")
        return redirect(url_for('home'))


@app.route('/image-analysis', methods=['GET', 'POST'])
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

    return render_template('image_analysis.html', username=session['username'], image_url=image_url,
                           output_url=output_url, count=count, stored_filename=stored_filename,
                           active_page='image')


@app.route('/video-analysis', methods=['GET', 'POST'])
def video_analysis():
    if 'username' not in session:
        return redirect(url_for('home'))
    video_path = request.args.get('video_path')
    return render_template('video_analysis.html', username=session['username'],
                           video_path=video_path, active_page='video')


@app.route('/webcam-feed-page')
def webcam_feed_page():
    if 'username' not in session:
        return redirect(url_for('home'))
    return render_template('webcam.html', username=session['username'], active_page='webcam')


@app.route('/webcam_feed')
def webcam_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/launch_video_stream', methods=['POST'])
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
    session.clear()
    flash("You have been logged out successfully.")
    return redirect(url_for('home'))


@app.route('/get_video_count')
def get_video_count():
    video_path = request.args.get("video_path")
    count = get_unique_count(video_path)
    return jsonify({"count": count})


@app.route('/stop_video')
def stop_video():
    video_path = request.args.get("video_path")
    if video_path:
        stop_stream(video_path)
    count = get_unique_count(video_path)
    return jsonify({"count": count})


if __name__ == '__main__':
    app.run(debug=True, port=5050)
