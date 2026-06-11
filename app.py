from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
import sqlite3
import os 

app = Flask(__name__)
app.secret_key = "library_secret"

UPLOAD_FOLDER = "static/profile_pictures"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


# ---------- DATABASE ----------
def create_database():
    conn = sqlite3.connect("library.db")
    cursor = conn.cursor()

    try:
        cursor.execute("""
        ALTER TABLE users
        ADD COLUMN profile_picture TEXT
        """)
    except:
        pass

    #Users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        email TEXT,
        password TEXT,
        favorite_genre TEXT,
        member_since TEXT,
        profile_picture TEXT
    )
    """)

    #Borrowed books table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS borrowed_books(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        book_title TEXT,
        borrow_date TEXT,
        due_date TEXT,
        status TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)

    cursor.execute("""
CREATE TABLE IF NOT EXISTS admins(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    email TEXT,
    password TEXT
)
""")

    conn.commit()
    conn.close()

create_database()

# ---------- LOAD BOOKS ----------
def load_books():
    books = []

    with open("book.txt", "r") as file:
        for line in file:
            title, category, summary = line.strip().split("|")
            books.append({
                "title": title,
                "category": category,
                "summary": summary
            })

    return books

# ---------- REGISTER ----------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        conn = sqlite3.connect("library.db")
        cursor = conn.cursor()

        member_since = datetime.now() .strftime("%Y")

        cursor.execute("""
        INSERT INTO users(
            username, 
            email,
            password, 
            favorite_genre, 
            member_since
        )
        VALUES (?, ?, ?, ?, ?)
        """, (
            username,
            email, 
            password, 
            "", 
            member_since
        ))

        conn.commit()
        conn.close()

        return redirect(url_for("sign_in"))

    return render_template("register.html")


# ---------- SIGN IN ----------
@app.route("/sign_in", methods=["GET", "POST"])
def sign_in():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = sqlite3.connect("library.db")
        cursor = conn.cursor()

        cursor.execute("""
        SELECT * FROM users
        WHERE email=? AND password=?
        """, (email, password))

        user = cursor.fetchone()
        conn.close()

        if user:
            session["user_id"] = user[0]
            return redirect(url_for("index"))

    return render_template("sign_in.html")

# ---------- PAGES ----------
@app.route("/")
def homepage():
    return render_template("homepage.html")

@app.route("/index")
def index():
    if "user_id" not in session:
        return redirect(url_for("sign_in"))
    return render_template("index.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/rules")
def rules():
    return render_template("rules.html")

@app.route("/mybooks")
def my_books():

    if "user_id" not in session:
        return redirect(url_for("sign_in"))

    conn = sqlite3.connect("library.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT book_title
    FROM borrowed_books
    WHERE user_id=?
    AND status='Borrowed'
    """, (session["user_id"],))

    borrowed_titles = [row[0] for row in cursor.fetchall()]

    conn.close()

    books = load_books()
    borrowed_book_details = []

    for book in books:
        if book["title"] in borrowed_titles:
            borrowed_book_details.append(book)

    return render_template("my_books.html", books=borrowed_book_details)

# ---------- PROFILE ----------
@app.route("/profile")
def profile():
    if "user_id" not in session:
        return redirect(url_for("sign_in"))

    conn = sqlite3.connect("library.db")
    cursor = conn.cursor()

    # Get user info
    cursor.execute("""
    SELECT * FROM users
    WHERE id=?
    """, (session["user_id"],))

    user = cursor.fetchone()
    print(user)

    # Profile picture
    picture = user[6]

    if picture:
        profile_picture = url_for(
            "static",
            filename=f"profile_pictures/{picture}"
        )
    else:
        profile_picture = url_for(
            "static",
            filename="default_profile.png"
        )

    # Count borrowed books
    cursor.execute("""
    SELECT COUNT(*)
    FROM borrowed_books
    WHERE user_id=?
    """, (session["user_id"],))

    borrowed_count = cursor.fetchone()[0]

    # Count returned books
    cursor.execute("""
    SELECT COUNT(*)
    FROM borrowed_books
    WHERE user_id=?
    AND status='Returned'
    """, (session["user_id"],))

    returned_count = cursor.fetchone()[0]

    # Count overdue books
    today = datetime.now().strftime("%Y-%m-%d")

    cursor.execute("""
    SELECT COUNT(*)
    FROM borrowed_books
    WHERE user_id=?
    AND due_date < ?
    AND status='Borrowed'
    """, (session["user_id"], today))

    overdue_count = cursor.fetchone()[0]

    conn.close()

    return render_template(
        "profile.html",
        username=user[1],
        email=user[2],
        favorite_genre=user[4],
        member_since=user[5],
        profile_picture=profile_picture,
        borrowed_count=borrowed_count,
        returned_count=returned_count,
        overdue_count=overdue_count
    )

# ---------- UPDATE PICTURE ----------
@app.route("/upload-picture", methods=["POST"])
def upload_picture():

    if "user_id" not in session:
        return redirect(url_for("sign_in"))

    picture = request.files["picture"]

    if picture:
        filename = secure_filename(picture.filename)

        picture.save(
            os.path.join(
                app.config["UPLOAD_FOLDER"],
                filename
            )
        )

        conn = sqlite3.connect("library.db")
        cursor = conn.cursor()

        cursor.execute("""
        UPDATE users
        SET profile_picture=?
        WHERE id=?
        """, (filename, session["user_id"]))

        conn.commit()
        conn.close()

    return redirect(url_for("profile"))

# ---------- BOOK CATEGORY ----------
@app.route("/category")
def category_page():
    selected_category = request.args.get("type")
    books = load_books()

    filtered_books = []

    for book in books:
        if book["category"].lower() == selected_category.lower():
            filtered_books.append(book)

    return render_template(
        "category.html",
        category=selected_category,
        books=filtered_books
    )


@app.route("/book/<title>")
def book_detail(title):
    books = load_books()

    for book in books:
        if book["title"].lower() == title.lower():
            return render_template("book_detail.html", book=book)

    return "Book not found", 404

@app.route("/borrow/<title>", methods=["POST"])
def borrow_book(title):

    if "user_id" not in session:
        return redirect(url_for("sign_in"))

    conn = sqlite3.connect("library.db")
    cursor = conn.cursor()

    borrow_date = datetime.now() .strftime("%Y-%m-%d")
    due_date = (datetime.now() + timedelta(days=14)) .strftime("%Y-%m-%d")

    cursor.execute("""
    INSERT INTO borrowed_books(
        user_id, 
        book_title,
        borrow_date,
        due_date,
        status
    )
    VALUES (?, ?, ?, ?, ?)
    """, (session["user_id"], 
          title,
          borrow_date,
          due_date,
          "Borrowed"
    ))

    conn.commit()
    conn.close()

    return redirect(url_for("my_books"))

@app.route("/return/<title>", methods=["POST"])
def return_book(title):
    conn = sqlite3.connect("library.db")
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE borrowed_books
    SET status='Returned'
    WHERE user_id=?
    AND book_title=?
    """, (session["user_id"], title))

    conn.commit()
    conn.close()

    return redirect(url_for("my_books"))

# ---------- ADMIN ----------
@app.route("/admin")
def admin():

    conn = sqlite3.connect("library.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        users.username,
        users.email,
        borrowed_books.book_title
    FROM borrowed_books
    JOIN users
    ON borrowed_books.user_id = users.id
    """)

    records = cursor.fetchall()

    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM borrowed_books")
    borrowed_count = cursor.fetchone()[0]

    total_books = len(load_books())

    conn.close()

    return render_template(
        "admin.html",
        records=records,
        total_users=total_users,
        total_books=total_books,
        borrowed_count=borrowed_count
    )

# ---------- ADMIN REGISTER ----------
@app.route("/admin/register", methods=["GET", "POST"])
def admin_register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        # For now, admin is stored in session only
        session["admin_logged_in"] = True
        session["admin_username"] = username

        return redirect(url_for("admin"))

    return render_template("admin_register.html")

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        conn = sqlite3.connect("library.db")
        cursor = conn.cursor()

        cursor.execute("""
        SELECT * FROM admins
        WHERE email=? AND password=?
        """, (email, password))

        admin = cursor.fetchone()

        conn.close()

        if admin:
            session["admin_id"] = admin[0]
            return redirect(url_for("admin"))

        return "Invalid admin login"

    return render_template("admin_login.html")

# ---------- LOGOUT ----------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("sign_in"))


if __name__ == "__main__":
    app.run(debug=True)