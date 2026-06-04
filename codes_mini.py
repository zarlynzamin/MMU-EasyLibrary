from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "mini_library_secret"

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


if __name__ == "__main__":
    app.run(debug=True)
