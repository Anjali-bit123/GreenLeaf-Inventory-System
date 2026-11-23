from flask import Flask, render_template, request, redirect, url_for, session, flash, make_response
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import date, datetime, timedelta
import csv, io
from database import get_db, init_db
from reports import get_dashboard_data, get_sales_report, get_monthly_sales_report, get_top_products, get_category_share

app = Flask(__name__)
app.config["SECRET_KEY"] = "change-this-demo-secret-before-deployment"
app.config["DATABASE"] = "greenleaf.db"

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped

def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if session.get("role") != "Admin":
            flash("Only an Admin can perform this action.", "error")
            return redirect(url_for("dashboard"))
        return view(*args, **kwargs)
    return wrapped

@app.context_processor
def inject_today():
    return {"today": date.today().isoformat()}

@app.route("/")
def index():
    return redirect(url_for("dashboard") if "user_id" in session else url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session.update(user_id=user["id"], username=user["username"], role=user["role"])
            return redirect(url_for("dashboard"))
        flash("Invalid username or password.", "error")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/dashboard")
@login_required
def dashboard():
    data = get_dashboard_data()
    return render_template("dashboard.html", data=data)

@app.route("/products", methods=["GET", "POST"])
@login_required
def products():
    db = get_db()
    if request.method == "POST":
        try:
            name = request.form.get("name", "").strip()
            category = request.form.get("category", "").strip()
            price = float(request.form.get("price", ""))
            stock = int(request.form.get("stock", ""))
            reorder = int(request.form.get("reorder_level", "5"))
            expiry = request.form.get("expiry_date") or None
            if not name or not category:
                raise ValueError("Product name and category are required.")
            if price < 0 or stock < 0 or reorder < 0:
                raise ValueError("Price, stock and reorder level cannot be negative.")
            if expiry:
                datetime.strptime(expiry, "%Y-%m-%d")
            db.execute("""INSERT INTO products(name, category, price, stock, reorder_level, expiry_date)
                          VALUES(?,?,?,?,?,?)""", (name, category, price, stock, reorder, expiry))
            db.commit()
            flash("Product added successfully.", "success")
        except (ValueError, TypeError):
            flash("Enter valid product details. Price and stock must be non-negative.", "error")
        return redirect(url_for("products"))
    q = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    sql = "SELECT * FROM products WHERE (name LIKE ? OR category LIKE ?)"
    params = [f"%{q}%", f"%{q}%"]
    if category:
        sql += " AND category=?"
        params.append(category)
    sql += " ORDER BY name"
    rows = db.execute(sql, params).fetchall()
    categories = db.execute("SELECT DISTINCT category FROM products ORDER BY category").fetchall()
    return render_template("products.html", products=rows, categories=categories, q=q, selected_category=category)

@app.route("/products/<int:product_id>/update", methods=["POST"])
@login_required
@admin_required
def update_product(product_id):
    try:
        price = float(request.form["price"])
        stock = int(request.form["stock"])
        reorder = int(request.form["reorder_level"])
        if min(price, stock, reorder) < 0:
            raise ValueError
        get_db().execute("UPDATE products SET price=?, stock=?, reorder_level=? WHERE id=?",
                         (price, stock, reorder, product_id))
        get_db().commit()
        flash("Product updated.", "success")
    except (ValueError, KeyError):
        flash("Invalid product values.", "error")
    return redirect(url_for("products"))

@app.route("/billing", methods=["GET", "POST"])
@login_required
def billing():
    db = get_db()
    if request.method == "POST":
        try:
            product_id = int(request.form["product_id"])
            quantity = int(request.form["quantity"])
            if quantity <= 0:
                raise ValueError("Quantity must be greater than zero.")
            product = db.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
            if not product:
                raise ValueError("Product not found.")
            if quantity > product["stock"]:
                raise ValueError("Not enough stock available.")
            bill_date = request.form.get("bill_date", date.today().isoformat())
            datetime.strptime(bill_date, "%Y-%m-%d")
            total = product["price"] * quantity
            cur = db.execute("INSERT INTO bills(bill_date, total, created_by) VALUES(?,?,?)",
                             (bill_date, total, session["user_id"]))
            bill_id = cur.lastrowid
            db.execute("""INSERT INTO bill_items(bill_id, product_id, quantity, unit_price, line_total)
                          VALUES(?,?,?,?,?)""", (bill_id, product_id, quantity, product["price"], total))
            db.execute("UPDATE products SET stock=stock-? WHERE id=?", (quantity, product_id))
            db.commit()
            flash(f"Bill #{bill_id} created. Total: ₹{total:.2f}", "success")
        except (ValueError, KeyError):
            db.rollback()
            flash("Invalid bill. Check date, quantity and available stock.", "error")
        return redirect(url_for("billing"))
    products = db.execute("SELECT * FROM products WHERE stock > 0 ORDER BY name").fetchall()
    bills = db.execute("""SELECT b.*, u.username FROM bills b JOIN users u ON b.created_by=u.id
                          ORDER BY b.id DESC LIMIT 20""").fetchall()
    return render_template("billing.html", products=products, bills=bills)

@app.route("/reports")
@login_required
def reports():
    start = request.args.get("start", (date.today()-timedelta(days=29)).isoformat())
    end = request.args.get("end", date.today().isoformat())
    try:
        datetime.strptime(start, "%Y-%m-%d")
        datetime.strptime(end, "%Y-%m-%d")
        if start > end:
            raise ValueError
    except ValueError:
        flash("Please select a valid date range.", "error")
        start, end = (date.today()-timedelta(days=29)).isoformat(), date.today().isoformat()
    sales = get_sales_report(start, end)
    monthly_sales = get_monthly_sales_report(start, end)
    top = get_top_products(start, end)
    category = get_category_share(start, end)
    low_stock = get_db().execute("SELECT * FROM products WHERE stock <= reorder_level ORDER BY stock").fetchall()
    expiry = get_db().execute("""SELECT * FROM products WHERE expiry_date IS NOT NULL
        AND expiry_date BETWEEN ? AND ? ORDER BY expiry_date""",
        (date.today().isoformat(), (date.today()+timedelta(days=15)).isoformat())).fetchall()
    slow = get_db().execute("""SELECT p.* FROM products p WHERE NOT EXISTS
        (SELECT 1 FROM bill_items bi JOIN bills b ON b.id=bi.bill_id
         WHERE bi.product_id=p.id AND b.bill_date >= ?) ORDER BY p.name""",
        ((date.today()-timedelta(days=30)).isoformat(),)).fetchall()
    return render_template("reports.html", start=start, end=end, sales=sales, monthly_sales=monthly_sales, top=top,
                           category=category, low_stock=low_stock, expiry=expiry, slow=slow)

@app.route("/reports/export")
@login_required
def export_report():
    start = request.args.get("start", (date.today()-timedelta(days=29)).isoformat())
    end = request.args.get("end", date.today().isoformat())
    rows = get_sales_report(start, end)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Bills", "Revenue"])
    for row in rows:
        writer.writerow([row["period"], row["bill_count"], f'{row["revenue"]:.2f}'])
    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=sales_report.csv"
    response.headers["Content-Type"] = "text/csv"
    return response

@app.route("/seed-demo")
def seed_demo():
    # Convenient first-run setup. Remove/disable this route before public deployment.
    db = get_db()
    if not db.execute("SELECT id FROM users LIMIT 1").fetchone():
        db.execute("INSERT INTO users(username,password_hash,role) VALUES(?,?,?)",
                   ("admin", generate_password_hash("Admin@123"), "Admin"))
        db.execute("INSERT INTO users(username,password_hash,role) VALUES(?,?,?)",
                   ("staff", generate_password_hash("Staff@123"), "Staff"))
        sample = [
            ("Rice 5kg", "Grains", 320, 25, 5, (date.today()+timedelta(days=180)).isoformat()),
            ("Wheat Flour 5kg", "Grains", 250, 18, 5, (date.today()+timedelta(days=120)).isoformat()),
            ("Milk 1L", "Dairy", 60, 4, 8, (date.today()+timedelta(days=7)).isoformat()),
            ("Tea 500g", "Beverages", 210, 12, 4, (date.today()+timedelta(days=240)).isoformat()),
            ("Cooking Oil 1L", "Essentials", 145, 20, 5, (date.today()+timedelta(days=300)).isoformat()),
            ("Biscuits Pack", "Snacks", 30, 40, 10, (date.today()+timedelta(days=90)).isoformat()),
        ]
        db.executemany("""INSERT INTO products(name,category,price,stock,reorder_level,expiry_date)
                          VALUES(?,?,?,?,?,?)""", sample)
        db.commit()
        return "Demo data created. Admin: admin / Admin@123 | Staff: staff / Staff@123. Delete/disable /seed-demo before deployment."
    return "Demo users/data already exist."

if __name__ == "__main__":
    with app.app_context():
        init_db()
    app.run(debug=True)
gunicorn
