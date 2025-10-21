from flask import Flask, render_template, request, redirect, url_for, session, flash, Response
import sqlite3, os, time
from crowd_detect import detect_crowd
from webcam import generate_frames

app = Flask(__name__)
app.secret_key = "9f8b7e6d5a4c331c2f0e9a7b1234567890abcdeffedcba9876543210fedcba123"

UPLOAD_FOLDER = 'static/uploads'
OUTPUT_FOLDER = 'static/outputs'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def init_db():
    connection = sqlite3.connect('LoginData.db')
    cursor = connection.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS USERS (
                        first_name TEXT NOT NULL,
                        last_name TEXT NOT NULL,
                        email TEXT PRIMARY KEY,
                        password TEXT NOT NULL
                      )''')
    connection.commit()
    connection.close()
init_db()

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
    first_name = request.form['first_name']
    last_name = request.form['last_name']
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
    connection.close()
    return redirect(url_for('home'))

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'username' not in session:
        return redirect(url_for('home'))

    image_url = None
    output_url = None
    count = None
    stored_filename = None
    mode = request.args.get('mode', 'upload')  # default 'upload' mode

    if request.method == 'POST' and mode == 'upload':
        if 'view_image' in request.form:
            file = request.files.get('image')
            if file and file.filename != '':
                ext = file.filename.rsplit('.', 1)[-1].lower()
                filename = f"{int(time.time()*1000)}.{ext}"
                save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(save_path)
                stored_filename = filename
                image_url = 'uploads/' + filename
                session['stored_filename'] = filename
        elif 'analyse_image' in request.form:
            stored_filename = request.form.get('stored_filename') or session.get('stored_filename')
            if stored_filename:
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], stored_filename)
                output_path = os.path.join(app.config['OUTPUT_FOLDER'], stored_filename)
                count, _ = detect_crowd(image_path, output_path)
                output_url = 'outputs/' + stored_filename
                image_url = 'uploads/' + stored_filename

    if mode == 'webcam':
        stored_filename = session.get('stored_filename')

    return render_template('dashboard.html',
                           username=session['username'],
                           image_url=image_url,
                           output_url=output_url,
                           count=count,
                           stored_filename=stored_filename,
                           mode=mode)

@app.route('/webcam_feed')
def webcam_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out successfully.")
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
