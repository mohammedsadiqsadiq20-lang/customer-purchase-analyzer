# Customer Purchase Analyzer

A professional Flask web application for uploading customer purchase CSV files, viewing purchase statistics, and analyzing category-wise sales.

## Features

- Login page for existing users
- Signup page for new users
- Secure password hashing
- SQLite database
- Demo purchase data automatically loaded for new accounts
- CSV upload section
- Purchase statistics:
  - Total revenue
  - Transactions
  - Items sold
  - Unique customers
- Category-wise sales charts: bar, pie and line
- Recent purchase table
- Responsive professional dashboard
- Clear purchase data action

## CSV format

Required columns:

```csv
customer_name,product,category,quantity,price,purchase_date
Rahul,Laptop,Electronics,1,75000,2026-07-01
Asha,Headphones,Electronics,2,3500,2026-07-02
Vikram,Running Shoes,Sports,1,4200,2026-07-04
```

Only `category`, `quantity`, and `price` are required. The other columns are optional.

## Run locally

### 1. Create a virtual environment

Windows:

```bash
python -m venv venv
venv\Scripts\activate
```

macOS/Linux:

```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Start the application

```bash
python app.py
```

Open:

`http://127.0.0.1:5000`

## Production notes

Before deploying, set a strong `SECRET_KEY` environment variable and turn off Flask debug mode. For a production deployment, use PostgreSQL/MySQL and a production WSGI server such as Gunicorn or Waitress.

### Charts
The dashboard provides three visualizations from the uploaded dataset: category-wise bar chart, category-wise pie chart, and purchase-date sales trend line chart.
