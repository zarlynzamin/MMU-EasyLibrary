from flask import Flask, render_template, request

app = Flask(__name__)

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


if __name__ == "__main__":
    app.run(debug=True)
