from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3

app = Flask(__name__)
app.secret_key = "library_secret"


# ---------- DATABASE ----------
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
    borrowed_books = session.get("borrowed_books", [])
    books = load_books()

    borrowed_book_details = []

    for book in books:
        if book["title"] in borrowed_books:
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
    borrowed_books = session.get("borrowed_books", [])

    if title not in borrowed_books:
        borrowed_books.append(title)

    session["borrowed_books"] = borrowed_books

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


# ---------- LOGOUT ----------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("sign_in"))


if __name__ == "__main__":
    app.run(debug=True)