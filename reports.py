from database import get_db
import pandas as pd

def get_dashboard_data():
    db = get_db()
    products = pd.read_sql_query("SELECT * FROM products", db)
    bills = pd.read_sql_query("SELECT * FROM bills", db)
    items = pd.read_sql_query("SELECT * FROM bill_items", db)
    revenue = float(bills["total"].sum()) if not bills.empty else 0.0
    bill_count = int(len(bills))
    low_stock = int((products["stock"] <= products["reorder_level"]).sum()) if not products.empty else 0
    avg_bill = revenue / bill_count if bill_count else 0.0
    return {"revenue": revenue, "bill_count": bill_count, "avg_bill": avg_bill,
            "product_count": int(len(products)), "low_stock": low_stock}

def get_sales_report(start, end):
    db = get_db()
    df = pd.read_sql_query(
        "SELECT bill_date, total FROM bills WHERE bill_date BETWEEN ? AND ?",
        db, params=(start, end))
    if df.empty:
        return []
    df["bill_date"] = pd.to_datetime(df["bill_date"], errors="coerce")
    df = df.dropna(subset=["bill_date"])
    df["period"] = df["bill_date"].dt.strftime("%Y-%m-%d")
    grouped = df.groupby("period", as_index=False).agg(revenue=("total", "sum"), bill_count=("total", "count"))
    return grouped.to_dict("records")

def get_top_products(start, end):
    db = get_db()
    df = pd.read_sql_query("""SELECT p.name, SUM(bi.quantity) AS quantity,
        SUM(bi.line_total) AS revenue FROM bill_items bi
        JOIN bills b ON b.id=bi.bill_id JOIN products p ON p.id=bi.product_id
        WHERE b.bill_date BETWEEN ? AND ? GROUP BY p.id, p.name
        ORDER BY quantity DESC LIMIT 10""", db, params=(start, end))
    return df.to_dict("records")

def get_category_share(start, end):
    db = get_db()
    df = pd.read_sql_query("""SELECT p.category, SUM(bi.line_total) AS revenue
        FROM bill_items bi JOIN bills b ON b.id=bi.bill_id
        JOIN products p ON p.id=bi.product_id WHERE b.bill_date BETWEEN ? AND ?
        GROUP BY p.category ORDER BY revenue DESC""", db, params=(start, end))
    total = float(df["revenue"].sum()) if not df.empty else 0
    if total:
        df["share"] = (df["revenue"] / total * 100).round(2)
    else:
        df["share"] = 0
    return df.to_dict("records")


def get_monthly_sales_report(start, end):
    db = get_db()
    df = pd.read_sql_query(
        "SELECT bill_date, total FROM bills WHERE bill_date BETWEEN ? AND ?",
        db, params=(start, end))
    if df.empty:
        return []
    df["bill_date"] = pd.to_datetime(df["bill_date"], errors="coerce")
    df = df.dropna(subset=["bill_date"])
    df["period"] = df["bill_date"].dt.strftime("%Y-%m")
    grouped = df.groupby("period", as_index=False).agg(revenue=("total", "sum"), bill_count=("total", "count"))
    return grouped.to_dict("records")
