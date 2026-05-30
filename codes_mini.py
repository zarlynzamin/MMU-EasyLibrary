from flask import Flask, render_template, request, redirect, url_for, session

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


@app.route("/")
def homepage():
    return render_template("index.html")


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

@app.route("/book/<title>")
def book_detail(title):
    books = load_books()

    selected_book = None

    for book in books:
        if book["title"].lower() == title.lower():
            selected_book = book
            
            return render_template("book_detail.html", book=selected_book)

    return "Book not found", 404

@app.route("/borrow/<title>", methods=["POST"])
def borrow_book(title):
    borrowed_books = session.get("borrowed_books", [])

    if title not in borrowed_books:
        borrowed_books.append(title)
    
    session["borrowed_books"] = borrowed_books
    return redirect(url_for("book_detail", title=title))


@app.route("/mybooks")
def my_books():
    borrowed_books = session.get("borrowed_books", [])
    books = load_books()

    borrowed_book_details = []

    for book in books:
        if book["title"] in borrowed_books:
            borrowed_book_details.append(book)

    return render_template("my_books.html", books=borrowed_book_details)
if __name__ == "__main__":
    app.run(debug=True)
