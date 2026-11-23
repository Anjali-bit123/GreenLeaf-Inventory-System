# GreenLeaf Grocers — Inventory & Sales Management System

A Flask + SQLite + Pandas web application built around the supplied Unified Mentor project requirements.

## Features
- Admin and Staff login; passwords stored as hashes.
- Product management, search and category filtering.
- Billing with quantity/date validation and automatic stock deduction.
- Dashboard KPIs: revenue, average bill value, bill count, products and low-stock count.
- Date-filtered daily sales report, top 10 products and category revenue share.
- Low-stock, expiry-within-15-days and no-sales-in-30-days lists.
- CSV export for sales reports; browser print support for bills/pages.
- Separate SQLite database in tests; 10 unit tests.

## Setup (Python 3.10+)
```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000/seed-demo once to create sample users and products.
Then open http://127.0.0.1:5000/login.

Demo credentials:
- Admin: `admin` / `Admin@123`
- Staff: `staff` / `Staff@123`

These are demo-only credentials. Change them and set a strong random `SECRET_KEY` before deployment. Remove or disable `/seed-demo` before public deployment. Do not upload a real database or real customer data to GitHub.

## Run tests
```bash
python -m unittest discover -s tests -v
```

## GitHub upload
Create a new **public or private** repository on GitHub, then from this folder:
```bash
git init
git add .
git commit -m "Initial GreenLeaf inventory management project"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/greenleaf-inventory-management.git
git push -u origin main
```
Replace `YOUR-USERNAME` with your own GitHub username. Never put passwords, personal details, or API keys in the repository.

## Deployment
This app can be deployed on a Python-compatible host (for example Render). Configure a persistent disk for SQLite, set a secure `SECRET_KEY`, install from `requirements.txt`, and use a production WSGI server such as Gunicorn. Add `gunicorn` to requirements and use `gunicorn app:app` as the start command. The demo seed route should be disabled before deployment.

## Notes and scope
- Sales charts are displayed using the tabular report data in this starter version; a chart library can be added for graphical charts.
- PDF billing is available through the browser's Print → Save as PDF; sales data can be downloaded as CSV.
- Stock turnover KPI is not calculated because a reliable cost-of-goods-sold/opening-stock dataset was not supplied. No fabricated metric is shown.
- The application uses generated demo grocery data only. No personal information is included.
