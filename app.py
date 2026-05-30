from flask import Flask,render_template,request,redirect,session
import sqlite3

app = Flask(__name__)
app.secret_key="library_secret"


# CREATE DATABASE

def create_database():
    conn = sqlite3.connect("library.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        email TEXT,
        password TEXT
    )
    """)

    conn.commit()
    conn.close()

create_database()

# HOME
@app.route('/')
def home():
    return render_template('register.html')

@app.route('/index')
def index():

    if 'user_id' not in session:
        return redirect('/sign_in')
    return render_template('index.html')

# REGISTER
@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':

        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        conn = sqlite3.connect("library.db")
        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO users(username, email, password)
        VALUES (?, ?, ?)
        """, (username, email, password))

        conn.commit()
        conn.close()

        return redirect('/sign_in')

    return render_template('register.html')

# SIGN IN
@app.route('/sign_in', methods=['GET', 'POST'])
def sign_in():

    if request.method == 'POST':

        email = request.form['email']
        password = request.form['password']

        conn = sqlite3.connect("library.db")
        cursor = conn.cursor()

        cursor.execute("""
        SELECT * FROM users
        WHERE email=? AND password=?
        """, (email, password))

        user = cursor.fetchone()

        conn.close()

        if user:
            session['user_id'] = user[0]
            return redirect('/index')

    return render_template('sign_in.html')

# PROFILE
@app.route('/profile')
def profile():

    if 'user_id' not in session:
        return redirect('/sign_in')

    conn = sqlite3.connect("library.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT * FROM users
    WHERE id=?
    """, (session['user_id'],))

    user = cursor.fetchone()

    conn.close()

    return render_template(
        'profile.html',
        username=user[1],
        email=user[2]
    )

@app.route('/update-profile', methods=['POST'])
def update_profile():
    if 'user_id' not in session:
        return redirect ('/sign_in')
    
    username = request.form['username']
    email = request.form['email']

    conn = sqlite3.connect("library.db")
    cursor = conn.cursor()

    cursor.execute("""
                   UPDATE users
                   SET username=?, email=?
                   WHERE id=?
    """, (username, email, session['user_id']))

    conn.commit
    conn.close()

    return redirect('/profile')

# LOGOUT
@app.route('/logout')
def logout():

    session.clear()
    return redirect('/sign_in')

if __name__ == '__main__':
    app.run(debug=True)