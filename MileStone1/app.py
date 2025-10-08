from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
app.secret_key = "mysecretkey"   # needed for sessions

users = {}

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        if email in users and users[email]['password'] == password:
            session['username'] = users[email]['username']
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid credentials. Try again.")
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        if email in users:
            flash("Email already registered!")
        else:
            users[email] = {"username": username, "password": password}
            flash("Registration successful! Please login.")
            return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    if "username" in session:
        return render_template('dashboard.html', username=session['username'])
    else:
        return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.pop("username", None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
