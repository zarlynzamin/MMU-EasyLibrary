from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime, timedelta
import sqlite3

app = Flask(__name__)
app.secret_key = "mini_library_secret"

def create_database():
    conn = sqlite3.connect("library.db")
    cursor = conn.cursor()

    # USERS TABLE
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        email TEXT,
        password TEXT
    )
    """)

    # ADMINS TABLE
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS admins(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        email TEXT,
        password TEXT
    )
    """)

    # BORROWED BOOKS TABLE
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS borrowed_books(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        book_title TEXT,
        borrow_date TEXT,
        due_date TEXT
    )
    """)

    conn.commit()
    conn.close()

create_database()

def load_books():
    books = []

    with open("book.txt", "r") as file:
        for line in file:
            title, category, summary = line.strip().split("|")
            books.append({
                "title": title,
                "category": category,
                "summary": summary,
            })

    return books

#INDEX#
@app.route("/")
def homepage():
    return render_template("index.html")

#PROFILE#
@app.route("/profile")
def profile():
    return render_template("profile.html")


#RULES#
@app.route("/rules")
def rules():
    return render_template("rules.html")



#CATEGORY#
@app.route("/category")
def category_page():
    selected_category = request.args.get("type")
    books = load_books()


    filtered_books = []

    for book in books:
        if book["category"].lower()== selected_category.lower():
            filtered_books.append(book)

    return render_template(
         "category.html",
         category=selected_category,
         books=filtered_books
    )



#BOOK DETAILS#
@app.route("/book/<title>")
def book_detail(title):
    books = load_books()

    selected_book = None

    for book in books:
        if book["title"].lower() == title.lower():
            selected_book = book
            
            return render_template("book_detail.html", book=selected_book)

    return "Book not found", 404



#BOOK BORROWING#
@app.route("/borrow/<title>", methods=["POST"])
def borrow_book(title):
    borrowed_books = session.get("borrowed_books", [])

    already_borrowed = False

    for book in borrowed_books:
        if isinstance(book, dict) and book["title"] == title:
            already_borrowed = True
        elif isinstance(book, str) and book == title:
            already_borrowed = True

    if not already_borrowed:
        borrowed_books.append({
            "title": title,
            "borrow_date": datetime.now().strftime("%Y-%m-%d"),
            "due_date": (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d")
        })

    session["borrowed_books"] = borrowed_books

    return redirect(url_for("my_books"))


#BOOK RETURNING#
@app.route("/return/<title>", methods=["POST"])
def return_book(title):

    borrowed_books = session.get("borrowed_books", [])

    updated_books = []

    for book in borrowed_books:

        if isinstance(book, dict):
            if book["title"] != title:
                updated_books.append(book)

        elif isinstance(book, str):
            if book != title:
                updated_books.append(book)

    session["borrowed_books"] = updated_books

    return redirect(url_for("my_books"))


#MY BOOKS#
@app.route("/mybooks")
def my_books():
    borrowed_books = session.get("borrowed_books", [])
    books = load_books()

    borrowed_book_details = []

    for borrowed in borrowed_books:
        for book in books:

            if isinstance(borrowed, dict):
                if book["title"] == borrowed["title"]:
                    book_copy = book.copy()
                    book_copy["borrow_date"] = borrowed.get("borrow_date", "Unknown")
                    book_copy["due_date"] = borrowed.get("due_date", "Unknown")
                    borrowed_book_details.append(book_copy)

            elif isinstance(borrowed, str):
                if book["title"] == borrowed:
                    book_copy = book.copy()
                    book_copy["borrow_date"] = "Unknown"
                    book_copy["due_date"] = "Unknown"
                    borrowed_book_details.append(book_copy)

    return render_template("my_books.html", books=borrowed_book_details)


# ADMIN REGSISTRATION #

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


# ADMIN LOGIN
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
            return redirect(url_for("admin_page"))

        return "Invalid admin email or password", 401

    return render_template("admin_login.html")

# ADMIN PAGE #
@app.route("/admin")
def admin_page():
    if "admin_logged_in" not in session:
        return redirect(url_for("admin_login"))

    conn = sqlite3.connect("library.db")
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM borrowed_books")
    borrowed_count = cursor.fetchone()[0]

    cursor.execute("""
    SELECT users.username, users.email, borrowed_books.book_title
    FROM borrowed_books
    JOIN users ON borrowed_books.user_id = users.id
    """)

    records = cursor.fetchall()

    conn.close()

    books = load_books()
    total_books = len(books)

    return render_template(
        "admin.html",
        books=books,
        total_users=total_users,
        total_books=total_books,
        borrowed_count=borrowed_count,
        records=records
    )


#ADMIN LOGOUT#
@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("admin_login"))

#ADD BOOK#
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

        return render_template(
            "add_book.html",
            success=True
        )

    return render_template("add_book.html")


#REGISTER#
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":

        print("REGISTER BUTTON CLICKED")
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

        return redirect("/")

    return render_template("register.html")

#SIGN IN#
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
            return redirect(url_for("homepage"))

        return "Invalid email or password", 401

    return render_template("sign_in.html")



#LOGOUT#
@app.route("/logout")
def logout():
    session.pop("user_id", None)
    return redirect(url_for("register"))

print(app.url_map)

if __name__ == "__main__":
    app.run(debug=True)
