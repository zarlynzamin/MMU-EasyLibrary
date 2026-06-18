from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
import sqlite3
import os
import re

app = Flask(__name__)
app.secret_key = "library_secret"

UPLOAD_FOLDER = "static/profile_pictures"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ---------- DATABASE ----------
def create_database():
    conn = sqlite3.connect("library.db")
    cursor = conn.cursor()


    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        email TEXT,
        password TEXT,
        favorite_genre TEXT,
        member_since TEXT,
        profile_picture TEXT,
        is_blocked INTEGER DEFAULT 0
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

    # Add missing columns if your old database already exists
    for column in ["favorite_genre", "member_since", "profile_picture"]:
        try:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {column} TEXT")
        except:
            pass

    try:
        cursor.execute("ALTER TABLE borrowed_books ADD COLUMN status TEXT")
    except:
        pass

    try:
        cursor.execute("ALTER TABLE users ADD COLUMN is_blocked INTEGER DEFAULT 0")
    except:
        pass

    conn.commit()
    conn.close()


create_database()


# ---------- LOAD BOOKS ----------
def load_books():
    books = []

    with open("book.txt", "r") as file:
        for line in file:
            if line.strip():
                title, category, summary = line.strip().split("|")
                books.append({
                    "title": title,
                    "category": category,
                    "summary": summary
                })

    return books


# ---------- USER REGISTER ----------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]

        if len(username) < 5:
            return render_template(
                "register.html",
                error="Username must be at least 5 characters."
            )
        
        if " " in username:
            return render_template(
                "register.html",
                error="Username cannot contain spaces."
            )
        
        if not re.match(r"^[A-Za-z0-9_]+$",username):
            return render_template(
                "register.html",
                error="Username can only contain letters, numbers and underscores."
            )
        
        email = request.form["email"]
        password = request.form["password"]
        member_since = datetime.now().strftime("%Y")

        conn = sqlite3.connect("library.db")
        cursor = conn.cursor()
        
        #Username check
        cursor.execute(
                        "SELECT * FROM users WHERE username=?",
                        (username,)
         )
        
        existing_user = cursor.fetchone()

        if existing_user:
            conn.close()
            return render_template(
                "register.html",
                error="Username already exists. Please choose another username.",
            )
        
        #Email check
        cursor.execute(
                        "SELECT * FROM users WHERE email=?",
                        (email,)
         )
        
        existing_email = cursor.fetchone()

        if existing_email:
            conn.close()
            return render_template(
                "register.html",
                error="Email is already registered.",
            )
        
        #Insert new user
        cursor.execute("""
        INSERT INTO users(username, email, password, favorite_genre, member_since, profile_picture)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (username, email, password, "", member_since, ""))

        conn.commit()
        conn.close()

        return redirect(url_for("sign_in"))

    return render_template("register.html")


# ---------- USER SIGN IN ----------
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

        return "Invalid email or password", 401

    return render_template("sign_in.html")

# ---------- USER LOGOUT ----------
@app.route("/logout")
def logout():
    session.pop("user_id", None)
    return redirect(url_for("sign_in"))

# ---------- FORGOT PASSWORD ----------
@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form["email"]
        new_password = request.form["new_password"]
        confirm_password = request.form["confirm_password"]

        if new_password != confirm_password:
            return "Passwords do not match. <a href='/forgot-password'>Try again</a>"

        conn = sqlite3.connect("library.db")
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE email=?",
            (email,)
        )

        user = cursor.fetchone()

        if user:
            cursor.execute("""
            UPDATE users
            SET password=?
            WHERE email=?
            """, (new_password, email))

            conn.commit()
            conn.close()

            return render_template("password_reset_success.html")

        conn.close()
        return "Email not found."
    return render_template("forgot_password.html")

# ---------- PAGES ----------
@app.route("/")
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


# ---------- PROFILE ----------
@app.route("/profile")
def profile():
    if "user_id" not in session:
        return redirect(url_for("sign_in"))

    conn = sqlite3.connect("library.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE id=?", (session["user_id"],))
    user = cursor.fetchone()

    picture = user[6]

    if picture:
        profile_picture = url_for("static", filename=f"profile_pictures/{picture}")
    else:
        profile_picture = url_for("static", filename="default_profile.png")

    cursor.execute("""
    SELECT COUNT(*) FROM borrowed_books
    WHERE user_id=? AND status='Borrowed'
    """, (session["user_id"],))
    borrowed_count = cursor.fetchone()[0]

    cursor.execute("""
    SELECT COUNT(*) FROM borrowed_books
    WHERE user_id=? AND status='Returned'
    """, (session["user_id"],))
    returned_count = cursor.fetchone()[0]

    today = datetime.now().strftime("%Y-%m-%d")

    cursor.execute("""
    SELECT COUNT(*) FROM borrowed_books
    WHERE user_id=? AND due_date < ? AND status='Borrowed'
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
        overdue_count=overdue_count,
        error=request.args.get("error")
    )

# ---------- UPDATE PROFILE ----------
@app.route("/update-profile", methods=["POST"])
def update_profile():
    if "user_id" not in session:
        return redirect(url_for("sign_in"))

    username = request.form.get("username")
    email = request.form.get("email")
    favorite_genre = request.form.get("favorite_genre")

    conn = sqlite3.connect("library.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT * FROM users
    WHERE username=? AND id!=?
    """, (username, session["user_id"]))

    existing_username = cursor.fetchone()

    if existing_username:
        conn.close()

        return redirect(url_for("profile", error="Username already taken."))
    
    cursor.execute("""
    SELECT * FROM users
    WHERE email=? AND id!=?
    """, (email, session["user_id"]))

    existing_email = cursor.fetchone()

    if existing_email:
        conn.close()
        return redirect(url_for("profile", error="Email already registered."))

    cursor.execute("""
    UPDATE users
    SET username=?, email=?, favorite_genre=?
    WHERE id=?
    """, (username, email, favorite_genre, session["user_id"]))

    conn.commit()
    conn.close()

    return redirect(url_for("profile"))


@app.route("/upload-picture", methods=["POST"])
def upload_picture():
    if "user_id" not in session:
        return redirect(url_for("sign_in"))

    picture = request.files.get("picture")

    if picture and picture.filename:
        filename = secure_filename(picture.filename)
        picture.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

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
        if selected_category and book["category"].lower() == selected_category.lower():
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


# ---------- BORROW BOOK ----------
@app.route("/borrow/<title>", methods=["POST"])
def borrow_book(title):
    if "user_id" not in session:
        return redirect(url_for("sign_in"))

    conn = sqlite3.connect("library.db")
    cursor = conn.cursor()

    today = datetime.now().strftime("%Y-%m-%d")

    # Block users have overdue borrowed books
    cursor.execute("""
    UPDATE users
    SET is_blocked = 1
    WHERE id IN (
        SELECT user_id
        FROM borrowed_books
        WHERE due_date < ?
        AND status='Borrowed'
    )
    """, (today,))

    conn.commit()

    #Check if current user is blocked
    cursor.execute("""
    SELECT is_blocked
    FROM users
    WHERE id=?
    """, (session["user_id"],))

    blocked = cursor.fetchone()[0]

    if blocked == 1:
        conn.close()
        return render_template("penalty.html")

    #Check if user already borrowed this book
    cursor.execute("""
    SELECT *
    FROM borrowed_books
    WHERE user_id=? AND book_title=? AND status='Borrowed'
    """, (session["user_id"], title))

    already_borrowed = cursor.fetchone()

    if already_borrowed:
        conn.close()
        return """
        <script>
            alert("You already borrowed this book!");
            window.history.back();
        </script>
        """

    #how many books user currently borrowed
    cursor.execute("""
    SELECT COUNT(*)
    FROM borrowed_books
    WHERE user_id=? AND status='Borrowed'
    """, (session["user_id"],))

    borrowed_count = cursor.fetchone()[0]

    # Borrowing limit
    if borrowed_count >= 3:
        conn.close()
        return """
        <script>
            alert("Borrowing limit reached! You can only borrow 3 books at a time.");
            window.history.back();
        </script>
        """

    # Borrow book
    borrow_date = datetime.now().strftime("%Y-%m-%d")
    due_date = (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d")

    cursor.execute("""
    INSERT INTO borrowed_books(user_id, book_title, borrow_date, due_date, status)
    VALUES (?, ?, ?, ?, ?)
    """, (session["user_id"], title, borrow_date, due_date, "Borrowed"))

    conn.commit()
    conn.close()

    return redirect(url_for("my_books"))


# ---------- RETURN BOOK ----------
@app.route("/return/<title>", methods=["POST"])
def return_book(title):
    if "user_id" not in session:
        return redirect(url_for("sign_in"))

    conn = sqlite3.connect("library.db")
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE borrowed_books
    SET status='Pending Return'
    WHERE user_id=? AND book_title=? AND status='Borrowed'
    """, (session["user_id"], title))

    conn.commit()
    conn.close()

    return redirect(url_for("my_books"))


# ---------- MY BOOKS ----------
@app.route("/mybooks")
def my_books():
    if "user_id" not in session:
        return redirect(url_for("sign_in"))

    conn = sqlite3.connect("library.db")
    cursor = conn.cursor()

    # Borrowed books
    cursor.execute("""
    SELECT book_title, borrow_date, due_date
    FROM borrowed_books
    WHERE user_id=? AND status='Borrowed'
    """, (session["user_id"],))

    borrowed_books = cursor.fetchall()

    # Pending return books
    cursor.execute("""
    SELECT book_title, borrow_date, due_date
    FROM borrowed_books
    WHERE user_id=? AND status='Pending Return'
    """, (session["user_id"],))

    pending_books = cursor.fetchall()

    conn.close()

    books = load_books()

    borrowed_book_details = []
    pending_book_details = []

    # Borrowed books details
    for borrowed in borrowed_books:
        title = borrowed[0]

        for book in books:
            if book["title"] == title:
                book_copy = book.copy()
                book_copy["borrow_date"] = borrowed[1]
                book_copy["due_date"] = borrowed[2]
                borrowed_book_details.append(book_copy)

    # Pending return details
    for borrowed in pending_books:
        title = borrowed[0]

        for book in books:
            if book["title"] == title:
                book_copy = book.copy()
                book_copy["borrow_date"] = borrowed[1]
                book_copy["due_date"] = borrowed[2]
                pending_book_details.append(book_copy)

    return render_template(
        "my_books.html",
        books=borrowed_book_details,
        pending_books=pending_book_details
    )


# ---------- ADMIN REGISTER ----------
@app.route("/admin/register", methods=["GET", "POST"])
def admin_register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        conn = sqlite3.connect("library.db")
        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO admins(username, email, password)
        VALUES (?, ?, ?)
        """, (username, email, password))

        conn.commit()
        conn.close()

        session["admin_logged_in"] = True
        return redirect(url_for("admin_page"))

    return render_template("admin_register.html")


# ---------- ADMIN LOGIN ----------
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
            session["admin_logged_in"] = True
            session["admin_id"] = admin[0]
            return redirect(url_for("admin_page"))

        return "Invalid admin email or password", 401

    return render_template("admin_login.html")


# ---------- ADMIN PAGE ----------
@app.route("/admin")
def admin_page():
    if "admin_logged_in" not in session:
        return redirect(url_for("admin_login"))

    conn = sqlite3.connect("library.db")
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM borrowed_books WHERE status='Borrowed'")
    borrowed_count = cursor.fetchone()[0]

    cursor.execute("""
    SELECT users.username, users.email, borrowed_books.book_title
    FROM borrowed_books
    JOIN users ON borrowed_books.user_id = users.id
    WHERE borrowed_books.status='Borrowed'
    """)

    records = cursor.fetchall()

    cursor.execute("""
    SELECT borrowed_books.id,
           users.username,
           users.email,
           borrowed_books.book_title
    FROM borrowed_books
    JOIN users ON borrowed_books.user_id = users.id
    WHERE borrowed_books.status='Pending Return'
    """)

    pending_returns = cursor.fetchall()

    cursor.execute("""
    SELECT id, username, email
    FROM users
    WHERE is_blocked = 1
    """)

    blocked_users = cursor.fetchall()
    conn.close()

    books = load_books()
    total_books = len(books)

    return render_template(
        "admin.html",
        books=books,
        total_users=total_users,
        total_books=total_books,
        borrowed_count=borrowed_count,
        records=records,
        pending_returns = pending_returns,
        blocked_users = blocked_users
    )

#ADMIN FORGOT PASSWORD
@app.route("/admin/forgot-password", methods=["GET", "POST"])
def admin_forgot_password():
    if request.method == "POST":
        email = request.form["email"]
        new_password = request.form["new_password"]
        confirm_password = request.form["confirm_password"]

        if new_password != confirm_password:
            return "Passwords do not match. <a href='/admin/forgot-password'>Try again</a>"

        conn = sqlite3.connect("library.db")
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM admins WHERE email=?", (email,))
        admin = cursor.fetchone()

        if admin:
            cursor.execute("""
                UPDATE admins
                SET password=?
                WHERE email=?
            """, (new_password, email))

            conn.commit()
            conn.close()

            return render_template("admin_password_reset_success.html")

        conn.close()
        return "Admin email not found."

    return render_template("admin_forgot_password.html")


# ---------- ADMIN APPROVE RETURN ----------
@app.route("/approve-return/<int:borrow_id>", methods=["POST"])
def approve_return(borrow_id):

    if "admin_logged_in" not in session:
        return redirect(url_for("admin_login"))

    conn = sqlite3.connect("library.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT user_id
    FROM borrowed_books
    WHERE id=?
    """, (borrow_id,))

    user_id = cursor.fetchone()[0]

    cursor.execute("""
    UPDATE borrowed_books
    SET status='Returned'
    WHERE id=?
    """, (borrow_id,))

    cursor.execute("""
    UPDATE users
    SET is_blocked=0
    WHERE id=?
    """, (user_id,))

    conn.commit()
    conn.close()

    return redirect(url_for("admin_page"))

# ---------- ADMIN ADD BOOK ----------
@app.route("/admin/add", methods=["GET", "POST"])
def add_book():
    if "admin_logged_in" not in session:
        return redirect(url_for("admin_login"))

    if request.method == "POST":
        title = request.form["title"].strip()
        category = request.form["category"].strip()
        summary = request.form["summary"].strip()

        with open("book.txt", "a") as file:
            file.write(f"\n{title}|{category}|{summary}")

        return render_template("add_book.html", success=True)

    return render_template("add_book.html")


# ---------- ADMIN LOGOUT ----------
@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    session.pop("admin_id", None)
    return redirect(url_for("admin_login"))


if __name__ == "__main__":
    app.run(debug=True)