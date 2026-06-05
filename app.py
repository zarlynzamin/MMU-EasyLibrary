from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3

app = Flask(__name__)
app.secret_key = "library_secret"


# ---------- DATABASE ----------
def create_database():
    conn = sqlite3.connect("library.db")
    cursor = conn.cursor()

    #Users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        email TEXT,
        password TEXT
    )
    """)

    #Borrowed books table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS borrowed_books(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        book_title TEXT,
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


# ---------- PAGES ----------
@app.route("/")
def homepage():
    return render_template("homepage.html")


@app.route("/index")
def index():
    if "user_id" not in session:
        return redirect(url_for("sign_in"))
    return render_template("index.html")


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
    """, (session["user_id"],))

    borrowed_titles = [row[0] for row in cursor.fetchall()]

    conn.close()

    books = load_books()
    borrowed_book_details = []

    for book in books:
        if book["title"] in borrowed_titles:
            borrowed_book_details.append(book)

    return render_template("my_books.html", books=borrowed_book_details)


@app.route("/profile")
def profile():
    if "user_id" not in session:
        return redirect(url_for("sign_in"))

    conn = sqlite3.connect("library.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT * FROM users
    WHERE id=?
    """, (session["user_id"],))

    user = cursor.fetchone()
    conn.close()

    return render_template(
        "profile.html",
        username=user[1],
        email=user[2]
    )


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

    cursor.execute("""
    INSERT INTO borrowed_books(user_id, book_title)
    VALUES (?, ?)
    """, (session["user_id"], title))

    conn.commit()
    conn.close()

    return redirect(url_for("my_books"))


# ---------- REGISTER ----------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        conn = sqlite3.connect("library.db")
        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO users(username, email, password)
        VALUES (?, ?, ?)
        """, (username, email, password))

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


# ---------- UPDATE PROFILE ----------
@app.route("/update-profile", methods=["POST"])
def update_profile():
    if "user_id" not in session:
        return redirect(url_for("sign_in"))

    username = request.form["username"]
    email = request.form["email"]

    conn = sqlite3.connect("library.db")
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE users
    SET username=?, email=?
    WHERE id=?
    """, (username, email, session["user_id"]))

    conn.commit()
    conn.close()

    return redirect(url_for("profile"))

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