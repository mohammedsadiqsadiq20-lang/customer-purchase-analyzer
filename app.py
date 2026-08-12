import csv
import os
import sqlite3
from datetime import datetime
from functools import wraps

from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "customer_analyzer.db")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
ALLOWED_EXTENSIONS = {"csv"}

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key-in-production")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            customer_name TEXT,
            product TEXT,
            category TEXT NOT NULL,
            quantity REAL DEFAULT 1,
            price REAL DEFAULT 0,
            purchase_date TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)
    conn.commit()
    conn.close()


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped_view


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def seed_demo_data(user_id):
    conn = get_db()
    count = conn.execute(
        "SELECT COUNT(*) FROM purchases WHERE user_id = ?", (user_id,)
    ).fetchone()[0]
    if count == 0:
        demo = [
            ("Rahul", "Laptop", "Electronics", 1, 75000, "2026-07-01"),
            ("Asha", "Headphones", "Electronics", 2, 3500, "2026-07-02"),
            ("Vikram", "Running Shoes", "Sports", 1, 4200, "2026-07-04"),
            ("Neha", "T-Shirt", "Fashion", 3, 900, "2026-07-05"),
            ("Arjun", "Coffee Maker", "Home & Kitchen", 1, 6800, "2026-07-07"),
            ("Meera", "Smartphone", "Electronics", 1, 32000, "2026-07-10"),
            ("Ravi", "Backpack", "Fashion", 2, 1600, "2026-07-11"),
            ("Priya", "Yoga Mat", "Sports", 2, 1200, "2026-07-13"),
            ("Kiran", "Desk Lamp", "Home & Kitchen", 2, 1800, "2026-07-15"),
            ("Anil", "Watch", "Accessories", 1, 5600, "2026-07-18"),
        ]
        conn.executemany("""
            INSERT INTO purchases
            (user_id, customer_name, product, category, quantity, price, purchase_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [(user_id, *row) for row in demo])
        conn.commit()
    conn.close()


@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            seed_demo_data(user["id"])
            return redirect(url_for("dashboard"))

        flash("Invalid email or password.", "error")

    return render_template("login.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if not name or not email or not password:
            flash("Please complete all required fields.", "error")
        elif password != confirm:
            flash("Passwords do not match.", "error")
        elif len(password) < 6:
            flash("Password must contain at least 6 characters.", "error")
        else:
            conn = get_db()
            try:
                cur = conn.execute("""
                    INSERT INTO users (name, email, password_hash, created_at)
                    VALUES (?, ?, ?, ?)
                """, (
                    name,
                    email,
                    generate_password_hash(password),
                    datetime.utcnow().isoformat()
                ))
                conn.commit()
                user_id = cur.lastrowid
                conn.close()

                session.clear()
                session["user_id"] = user_id
                session["user_name"] = name
                seed_demo_data(user_id)
                return redirect(url_for("dashboard"))
            except sqlite3.IntegrityError:
                conn.close()
                flash("An account with that email already exists.", "error")

    return render_template("signup.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    conn = get_db()
    rows = conn.execute("""
        SELECT * FROM purchases
        WHERE user_id = ?
        ORDER BY id DESC
    """, (session["user_id"],)).fetchall()

    stats = conn.execute("""
        SELECT
            COUNT(*) AS transactions,
            COALESCE(SUM(quantity), 0) AS items,
            COALESCE(SUM(quantity * price), 0) AS revenue,
            COUNT(DISTINCT customer_name) AS customers,
            COALESCE(AVG(quantity * price), 0) AS avg_order_value
        FROM purchases
        WHERE user_id = ?
    """, (session["user_id"],)).fetchone()

    category_rows = conn.execute("""
        SELECT category, ROUND(SUM(quantity * price), 2) AS sales
        FROM purchases
        WHERE user_id = ?
        GROUP BY category
        ORDER BY sales DESC
    """, (session["user_id"],)).fetchall()

    daily_rows = conn.execute("""
        SELECT purchase_date, ROUND(SUM(quantity * price), 2) AS sales
        FROM purchases
        WHERE user_id = ? AND purchase_date IS NOT NULL AND purchase_date != ''
        GROUP BY purchase_date
        ORDER BY purchase_date
    """, (session["user_id"],)).fetchall()

    conn.close()

    return render_template(
        "dashboard.html",
        rows=rows,
        stats=stats,
        categories=[r["category"] for r in category_rows],
        sales=[r["sales"] for r in category_rows],
        dates=[r["purchase_date"] for r in daily_rows],
        daily_sales=[r["sales"] for r in daily_rows],
        user_name=session.get("user_name", "User")
    )


@app.route("/upload", methods=["POST"])
@login_required
def upload_csv():
    file = request.files.get("csv_file")

    if not file or not file.filename:
        flash("Please select a CSV file.", "error")
        return redirect(url_for("dashboard"))

    if not allowed_file(file.filename):
        flash("Only CSV files are supported.", "error")
        return redirect(url_for("dashboard"))

    filename = secure_filename(file.filename)
    path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(path)

    required = {"category", "quantity", "price"}
    inserted = 0
    conn = get_db()

    try:
        with open(path, newline="", encoding="utf-8-sig") as csvfile:
            reader = csv.DictReader(csvfile)
            headers = {h.strip().lower() for h in (reader.fieldnames or [])}

            if not required.issubset(headers):
                flash(
                    "CSV must contain category, quantity and price columns. "
                    "Optional columns: customer_name, product, purchase_date.",
                    "error"
                )
                conn.close()
                return redirect(url_for("dashboard"))

            for raw in reader:
                data = {k.strip().lower(): (v or "").strip() for k, v in raw.items()}
                try:
                    category = data["category"] or "Uncategorized"
                    quantity = float(data["quantity"] or 1)
                    price = float(data["price"] or 0)
                except ValueError:
                    continue

                conn.execute("""
                    INSERT INTO purchases
                    (user_id, customer_name, product, category, quantity, price, purchase_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    session["user_id"],
                    data.get("customer_name", ""),
                    data.get("product", ""),
                    category,
                    quantity,
                    price,
                    data.get("purchase_date", "")
                ))
                inserted += 1

        conn.commit()
        flash(f"{inserted} purchase records imported successfully.", "success")
    except Exception as exc:
        conn.rollback()
        flash(f"Could not import the file: {exc}", "error")
    finally:
        conn.close()

    return redirect(url_for("dashboard"))


@app.route("/clear-data", methods=["POST"])
@login_required
def clear_data():
    conn = get_db()
    conn.execute("DELETE FROM purchases WHERE user_id = ?", (session["user_id"],))
    conn.commit()
    conn.close()
    flash("Your purchase data has been cleared.", "success")
    return redirect(url_for("dashboard"))


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
