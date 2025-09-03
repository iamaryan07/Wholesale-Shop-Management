Wholesale Shop Management System
A modern, full-featured wholesale shop management system built with Streamlit and Supabase (PostgreSQL). Designed for wholesalers and distributors, this application streamlines customer, product, order, payment, and inventory management with a user-friendly interface and fully cloud-based workflow.


🚀 Features
Role-Based Authentication: Secure login for Managers and Staff accounts

Dashboard: Live KPIs for orders, revenue, and stocks

Customers, Suppliers, Products & Employees: Add, edit, view, and delete records in an intuitive UI

Order Management: Complete multi-step wizard for creating and managing orders

Payments & Transportation: Track payments and logistics for each order

Bulk Import and Export: Upload/download CSVs for products, customers, orders, and more

Data Analytics: Visual charts of top products, sales trends, inventory status

Cloud Native: Database hosted on Supabase (PostgreSQL) – deploy and connect from anywhere

Secure Secrets Handling: Database credentials managed securely


🏗️ Tech Stack
Frontend & App: Streamlit

Database: Supabase PostgreSQL

ORM: psycopg2

Deployment: Streamlit Community Cloud + Supabase


✨ Demo Accounts
Manager: manager / admin123

Staff: staff / staff123


⚙️ Project Structure
text
Wholesale-Shop-Management/
├── app.py                # Main Streamlit app
├── requirements.txt      # Python dependencies
├── .streamlit/
│   └── secrets.toml      # Secure database secrets (excluded from git)
├── README.md             # Project documentation


🔒 Environment Setup
Create .streamlit/secrets.toml with:

text
[default]
db_host = "host"
db_user = "postgres"
db_password = ""
db_name = "postgres"
db_port = "5432"
Never upload secrets.toml to GitHub!


💻 Local Development
bash
# Clone the repository
git clone https://github.com/iamaryan07/Wholesale-Shop-Management.git
cd wholesale-shop-management


# Install dependencies
pip install -r requirements.txt


# Run the app
streamlit run app.py
Open http://localhost:8501 in your browser.


📦 Features Overview
User Authentication: Role-based access, user management (add, change status, reset password)

CRUD Operations: For Customers, Suppliers, Products, Employees, Orders, Payments, Transportation

Order Wizard: Step-by-step process including cart, payment, and logistics info

Bulk Import/Export: CSV handling for massive data insert/export

Analytics: Real-time metrics, product trends and transportation status visualization

Secure & Cloud-Native: Managed entirely from browser, works from anywhere
