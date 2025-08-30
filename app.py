import os
import datetime as dt
from typing import List, Dict, Any, Optional
import hashlib
import secrets

import streamlit as st
import pandas as pd
import streamlit as st from st_supabase_connection import SupabaseConnection

# =====================================================
# CONFIG
# =====================================================
st.set_page_config(
    page_title="Wholesale Shop Management",
    page_icon="🧾",
    layout="wide",
)

# Supabase configuration
SUPABASE_URL = st.secrets["supabase_url"]
SUPABASE_KEY = st.secrets["supabase_key"]

# Initialize Supabase client
@st.cache_resource
def init_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase: Client = init_supabase()

# =====================================================
# AUTHENTICATION FUNCTIONS
# =====================================================

def hash_password(password: str) -> str:
    """Hash password using SHA-256 with salt"""
    salt = secrets.token_hex(32)
    password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
    return f"{salt}${password_hash}"

def verify_password(password: str, stored_hash: str) -> bool:
    """Verify password"""
    if '$' in stored_hash:
        try:
            salt, password_hash = stored_hash.split('$', 1)
            return hashlib.sha256((password + salt).encode()).hexdigest() == password_hash
        except:
            return False
    else:
        # Simple comparison for testing
        return password == stored_hash

def authenticate_user(username: str, password: str) -> Optional[Dict]:
    """Authenticate user and return user info if valid"""
    try:
        response = supabase.table("users").select("*").eq("username", username).eq("is_active", True).execute()
        
        if response.data and verify_password(password, response.data[0]['password_hash']):
            return response.data[0]
    except Exception as e:
        st.error(f"Authentication error: {e}")
    return None

def check_permissions(required_role: str = None) -> bool:
    """Check if current user has required permissions"""
    if 'user' not in st.session_state:
        return False
    
    if required_role is None:
        return True
    
    user_role = st.session_state.user['role']
    if required_role == 'Manager' and user_role != 'Manager':
        return False
    
    return True

def login_page():
    """Display login page"""
    st.title("🔐 Login")
    
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        
        if submitted and username and password:
            user = authenticate_user(username, password)
            if user:
                st.session_state.user = user
                st.success(f"Welcome, {user['name']}!")
                st.rerun()
            else:
                st.error("Invalid username or password")
    
    st.info("**Demo credentials:**\n- Manager: username=`manager`, password=`admin123`\n- Staff: username=`staff`, password=`staff123`")

def logout():
    """Logout current user"""
    if 'user' in st.session_state:
        del st.session_state.user
    st.rerun()

# =====================================================
# DATABASE FUNCTIONS
# =====================================================

def execute_query(table: str, operation: str = "select", **kwargs) -> List[Dict[str, Any]]:
    """Execute database operations using Supabase"""
    try:
        if operation == "select":
            query = supabase.table(table).select(kwargs.get("columns", "*"))
            
            # Add filters if provided
            if "eq" in kwargs:
                for col, val in kwargs["eq"].items():
                    query = query.eq(col, val)
            
            if "neq" in kwargs:
                for col, val in kwargs["neq"].items():
                    query = query.neq(col, val)
            
            if "like" in kwargs:
                for col, val in kwargs["like"].items():
                    query = query.like(col, f"%{val}%")
            
            if "limit" in kwargs:
                query = query.limit(kwargs["limit"])
            
            if "order" in kwargs:
                query = query.order(kwargs["order"], desc=kwargs.get("desc", False))
            
            response = query.execute()
            return response.data
            
        elif operation == "insert":
            response = supabase.table(table).insert(kwargs["data"]).execute()
            return response.data
            
        elif operation == "update":
            query = supabase.table(table).update(kwargs["data"])
            if "eq" in kwargs:
                for col, val in kwargs["eq"].items():
                    query = query.eq(col, val)
            response = query.execute()
            return response.data
            
        elif operation == "delete":
            query = supabase.table(table)
            if "eq" in kwargs:
                for col, val in kwargs["eq"].items():
                    query = query.eq(col, val)
            response = query.execute()
            return response.data
            
    except Exception as e:
        st.error(f"Database error: {e}")
        return []

def to_df(rows: List[Dict[str, Any]]):
    return pd.DataFrame(rows) if rows else pd.DataFrame()

@st.cache_data(ttl=60)
def cached_query(table: str, **kwargs):
    return execute_query(table, **kwargs)

def get_count(table: str, **kwargs) -> int:
    """Get count of records in a table"""
    try:
        query = supabase.table(table).select("*", count="exact")
        if "eq" in kwargs:
            for col, val in kwargs["eq"].items():
                query = query.eq(col, val)
        if "neq" in kwargs:
            for col, val in kwargs["neq"].items():
                query = query.neq(col, val)
        response = query.execute()
        return response.count
    except:
        return 0

def get_sum(table: str, column: str, **kwargs) -> float:
    """Get sum of a column in a table"""
    try:
        rows = execute_query(table, columns=column, **kwargs)
        return sum([row.get(column, 0) or 0 for row in rows])
    except:
        return 0.0

# =====================================================
# MAIN APP LOGIC
# =====================================================

# Check if user is logged in
if 'user' not in st.session_state:
    login_page()
    st.stop()

# User is logged in, show main app
user = st.session_state.user

# =====================================================
# LAYOUT HEAD WITH AUTH
# =====================================================
with st.sidebar:
    st.title("🧾 Wholesale Shop")
    
    # User info and logout
    st.info(f"👤 {user['name']} ({user['role']})")
    if st.button("🚪 Logout"):
        logout()
    
    st.divider()
    
    # Navigation based on role
    if user['role'] == 'Manager':
        page_options = [
            "Dashboard", 
            "Customers", "Suppliers", "Products", "Employees",
            "Orders", "Order Items", "Payments", "Transportation",
            "Create Order Wizard", "Bulk Import/Export", "User Management"
        ]
    else:  # Staff
        page_options = [
            "Dashboard", 
            "Customers", "Suppliers", "Products", "Employees",
            "Orders", "Order Items", "Payments", "Transportation",
            "Create Order Wizard"
        ]
    
    page = st.radio("Navigate", page_options, index=0)

# =====================================================
# DASHBOARD
# =====================================================

def page_dashboard():
    st.title("📊 Dashboard")
    
    # Get KPIs using Supabase
    kpis = {
        "Customers": get_count("customers"),
        "Suppliers": get_count("suppliers"),
        "Products": get_count("products"),
        "Employees": get_count("employees"),
        "Orders": get_count("orders"),
        "Revenue": get_sum("payments", "amount"),
        "Pending Orders": get_count("orders", neq={"status": "Delivered"}),
    }
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Customers", kpis["Customers"])
    c2.metric("Orders", kpis["Orders"])
    c3.metric("Revenue", f"₹{kpis['Revenue']:,.2f}")
    c4.metric("Pending", kpis["Pending Orders"])

    st.divider()
    colA, colB = st.columns(2)
    
    with colA:
        st.subheader("Top 10 Products (by Quantity)")
        # Get order items with product names
        order_items = cached_query("order_items")
        products = cached_query("products")
        
        if order_items and products:
            # Create product lookup
            product_lookup = {p['product_id']: p['name'] for p in products}
            
            # Calculate quantities by product
            product_qty = {}
            for item in order_items:
                pid = item['product_id']
                qty = item.get('quantity', 0)
                if pid in product_lookup:
                    pname = product_lookup[pid]
                    product_qty[pname] = product_qty.get(pname, 0) + qty
            
            if product_qty:
                # Sort and get top 10
                top_products = sorted(product_qty.items(), key=lambda x: x[1], reverse=True)[:10]
                df = pd.DataFrame(top_products, columns=['name', 'total_qty']).set_index('name')
                st.bar_chart(df['total_qty'])
            else:
                st.info("No order items yet.")
        else:
            st.info("No order items yet.")

    with colB:
        st.subheader("Transportation Status Split")
        transport_data = cached_query("transportation")
        if transport_data:
            status_count = {}
            for t in transport_data:
                status = t.get('status', 'Unknown')
                status_count[status] = status_count.get(status, 0) + 1
            
            if status_count:
                df = pd.DataFrame(list(status_count.items()), columns=['status', 'cnt']).set_index('status')
                st.bar_chart(df['cnt'])
            else:
                st.info("No transportation records yet.")
        else:
            st.info("No transportation records yet.")

    st.divider()
    st.subheader("Recent Orders")
    recent_orders = execute_query("orders", order="order_date", desc=True, limit=20)
    
    if recent_orders:
        # Get related data
        customers = {c['customer_id']: c['name'] for c in cached_query("customers")}
        employees = {e['employee_id']: e['name'] for e in cached_query("employees")}
        order_items = cached_query("order_items")
        
        # Calculate order totals
        order_totals = {}
        for item in order_items:
            oid = item['order_id']
            price = item.get('price', 0) or 0
            order_totals[oid] = order_totals.get(oid, 0) + price
        
        # Prepare display data
        display_data = []
        for order in recent_orders:
            display_data.append({
                'order_id': order['order_id'],
                'customer': customers.get(order['customer_id'], 'Unknown'),
                'employee': employees.get(order['employee_id'], 'Unknown'),
                'order_date': order['order_date'],
                'status': order['status'],
                'order_total': order_totals.get(order['order_id'], 0)
            })
        
        st.dataframe(pd.DataFrame(display_data), use_container_width=True)
    else:
        st.info("No orders found.")

# =====================================================
# TABLE CONFIGURATION
# =====================================================

TABLES = {
    "customers": {
        "pk": "customer_id",
        "cols": ["name", "shop_name", "phone", "email", "address", "city", "state", "pincode"],
        "types": ["text", "text", "text", "text", "text", "text", "text", "text"],
        "title": "👤 Customers"
    },
    "suppliers": {
        "pk": "supplier_id", 
        "cols": ["name", "company_name", "phone", "email", "address", "city", "state", "pincode"],
        "types": ["text", "text", "text", "text", "text", "text", "text", "text"],
        "title": "🏭 Suppliers"
    },
    "products": {
        "pk": "product_id",
        "cols": ["name", "category", "unit_price", "stock_quantity", "supplier_id"],
        "types": ["text", "text", "number", "int", "fk:suppliers.supplier_id"],
        "title": "📦 Products"
    },
    "employees": {
        "pk": "employee_id",
        "cols": ["name", "role", "phone", "email", "salary"],
        "types": ["text", "text", "text", "text", "number"],
        "title": "🧑‍💼 Employees"
    },
    "orders": {
        "pk": "order_id",
        "cols": ["customer_id", "employee_id", "order_date", "status"],
        "types": ["fk:customers.customer_id", "fk:employees.employee_id", "date", "choice:Pending,Dispatched,Delivered"],
        "title": "🧾 Orders"
    },
    "order_items": {
        "pk": "order_item_id",
        "cols": ["order_id", "product_id", "quantity", "price"],
        "types": ["fk:orders.order_id", "fk:products.product_id", "int", "number"],
        "title": "🧾 Order Items"
    },
    "payments": {
        "pk": "payment_id",
        "cols": ["order_id", "payment_date", "amount", "payment_mode"],
        "types": ["fk:orders.order_id", "date", "number", "choice:Cash,UPI,Online Transfer,Cheque"],
        "title": "💳 Payments"
    },
    "transportation": {
        "pk": "transport_id",
        "cols": ["order_id", "vehicle_number", "driver_name", "transport_mode", "departure_date", "arrival_date", "status"],
        "types": [
            "fk:orders.order_id", "text", "text", "choice:Truck,Van,Mini Truck,Tempo", "date", "date", "choice:In Transit,Delivered,Delayed"
        ],
        "title": "🚚 Transportation"
    },
}

FIELD_HELP = {
    "unit_price": "Decimal, price per unit",
    "stock_quantity": "Integer units in stock",
    "status": "Current status of order/transport",
}

def render_field(label: str, ftype: str, value: Any = None):
    help_txt = FIELD_HELP.get(label)
    if ftype == "text":
        return st.text_input(label, value=value or "", help=help_txt)
    if ftype == "number":
        return st.number_input(label, value=float(value) if value is not None else 0.0, step=0.01, help=help_txt)
    if ftype == "int":
        return st.number_input(label, value=int(value) if value is not None else 0, step=1, help=help_txt)
    if ftype.startswith("choice:"):
        choices = ftype.split(":", 1)[1].split(",")
        return st.selectbox(label, choices, index=(choices.index(value) if value in choices else 0), help=help_txt)
    if ftype == "date":
        default = value if isinstance(value, dt.date) else (pd.to_datetime(value).date() if value else dt.date.today())
        return st.date_input(label, value=default, help=help_txt)
    if ftype.startswith("fk:"):
        tbl, col = ftype.split(":", 1)[1].split(".")
        rows = cached_query(tbl)
        labels = []
        ids = []
        for r in rows:
            disp = str(r.get("name") or r.get("shop_name") or r.get("company_name") or r.get(col))
            labels.append(f"{disp} (ID {r[col]})")
            ids.append(r[col])
        if not ids:
            st.warning(f"No records found in {tbl}")
            return None
        idx = ids.index(value) if value in ids else 0
        choice = st.selectbox(label, labels, index=idx, help=help_txt)
        return ids[labels.index(choice)]
    return st.text_input(label, value=value or "")

def page_table(table_name: str):
    cfg = TABLES[table_name]
    pk = cfg["pk"]
    cols = cfg["cols"]
    st.title(cfg["title"])
    
    is_manager = user['role'] == 'Manager'
    
    # Search filters
    with st.expander("🔎 Search & Filters", expanded=False):
        search = st.text_input("Search")
        limit = st.slider("Rows per page", 10, 200, 50)
        order_by = st.selectbox("Order by", [pk] + cols, index=0)
        order_dir = st.radio("Direction", ["DESC", "ASC"], horizontal=True)

    # Query data with search
    kwargs = {"order": order_by, "desc": (order_dir == "DESC"), "limit": limit}
    
    if search:
        # For search, we'll get all data and filter client-side
        # In production, you'd implement server-side search
        kwargs["limit"] = 1000  # Get more data for search
    
    rows = execute_query(table_name, **kwargs)
    
    # Filter by search if provided
    if search and rows:
        search_lower = search.lower()
        filtered_rows = []
        for row in rows:
            # Search in text fields
            for key, value in row.items():
                if value and search_lower in str(value).lower():
                    filtered_rows.append(row)
                    break
        rows = filtered_rows[:limit]  # Apply limit after search
    
    df = to_df(rows)
    st.dataframe(df, use_container_width=True)

    st.divider()
    
    # Role-based UI
    if is_manager:
        c1, c2, c3 = st.columns([1, 1, 1])
    else:
        c1, c2 = st.columns([1, 1])
        c3 = None
    
    # Add functionality
    with c1:
        st.subheader("➕ Add New")
        with st.form(f"add_{table_name}"):
            values = {}
            for c, t in zip(cols, cfg["types"]):
                values[c] = render_field(c, t)
            submitted = st.form_submit_button("Create")
            if submitted:
                try:
                    execute_query(table_name, operation="insert", data=values)
                    st.success("Created successfully.")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Error creating record: {e}")
    
    # Edit functionality (Manager only)
    with c2:
        if is_manager:
            st.subheader("✏️ Edit")
            if rows:
                record_options = [f"ID {r[pk]}" for r in rows[:50]]  # Limit options
                selected_record = st.selectbox("Select Record", record_options)
                
                if selected_record:
                    record_id = int(selected_record.split()[1])
                    record = next((r for r in rows if r[pk] == record_id), None)
                    
                    if record:
                        with st.form(f"edit_{table_name}"):
                            new_vals = {}
                            for c, t in zip(cols, cfg["types"]):
                                new_vals[c] = render_field(c, t, record.get(c))
                            submitted = st.form_submit_button("Update")
                            if submitted:
                                try:
                                    execute_query(table_name, operation="update", data=new_vals, eq={pk: record_id})
                                    st.success("Updated successfully.")
                                    st.cache_data.clear()
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error updating record: {e}")
            else:
                st.info("No records available to edit.")
        else:
            st.info("🔒 Edit functionality requires Manager role")
    
    # Delete functionality (Manager only)
    if c3 and is_manager:
        with c3:
            st.subheader("🗑️ Delete")
            if rows:
                record_options = [f"ID {r[pk]}" for r in rows[:50]]
                selected_record = st.selectbox("Select Record to Delete", record_options, key=f"del_{table_name}")
                
                if selected_record and st.button("Confirm Delete", type="primary"):
                    record_id = int(selected_record.split()[1])
                    try:
                        execute_query(table_name, operation="delete", eq={pk: record_id})
                        st.success(f"Deleted {table_name} ID {record_id}")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error deleting record: {e}")
            else:
                st.info("No records to delete.")

# =====================================================
# USER MANAGEMENT
# =====================================================

def page_user_management():
    if not check_permissions('Manager'):
        st.error("🔒 Access denied. Manager role required.")
        return
    
    st.title("👥 User Management")
    
    # Display existing users
    users = cached_query("users", columns="user_id, username, role, name, email, is_active")
    st.dataframe(to_df(users), use_container_width=True)
    
    st.divider()
    
    c1, c2 = st.columns([1, 1])
    
    with c1:
        st.subheader("➕ Add New User")
        with st.form("add_user"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            name = st.text_input("Full Name")
            email = st.text_input("Email")
            role = st.selectbox("Role", ["Staff", "Manager"])
            submitted = st.form_submit_button("Create User")
            
            if submitted and username and password and name:
                try:
                    user_data = {
                        "username": username,
                        "password_hash": password,  # In production, hash this properly
                        "role": role,
                        "name": name,
                        "email": email
                    }
                    execute_query("users", operation="insert", data=user_data)
                    st.success("User created successfully.")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to create user: {e}")
    
    with c2:
        st.subheader("🔄 Manage Users")
        if users:
            user_ids = [u['user_id'] for u in users]
            selected_user_id = st.selectbox("Select User", user_ids, 
                format_func=lambda x: f"{next(u['username'] for u in users if u['user_id']==x)} - {next(u['name'] for u in users if u['user_id']==x)}")
            selected_user = next(u for u in users if u['user_id']==selected_user_id)
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔒 Deactivate" if selected_user['is_active'] else "✅ Activate"):
                    new_status = not selected_user['is_active']
                    execute_query("users", operation="update", data={"is_active": new_status}, eq={"user_id": selected_user_id})
                    st.success(f"User {'activated' if new_status else 'deactivated'}.")
                    st.cache_data.clear()
                    st.rerun()
            
            with col2:
                with st.form("reset_password"):
                    new_password = st.text_input("New Password", type="password")
                    if st.form_submit_button("Reset Password"):
                        if new_password:
                            execute_query("users", operation="update", data={"password_hash": new_password}, eq={"user_id": selected_user_id})
                            st.success("Password updated successfully.")
                        else:
                            st.error("Password cannot be empty.")

# =====================================================
# CREATE ORDER WIZARD
# =====================================================

def page_order_wizard():
    st.title("🧙 Create Order Wizard")
    st.info("Follow the steps below to create a complete order with all related information")
    
    # Initialize session state
    if 'wizard_step' not in st.session_state:
        st.session_state.wizard_step = 1
    if 'order_info' not in st.session_state:
        st.session_state.order_info = {}
    
    # Step 1: Order Basic Information
    if st.session_state.wizard_step >= 1:
        st.subheader("📋 Step 1: Order Information")
        
        customers = cached_query("customers")
        employees = cached_query("employees")
        
        if not customers or not employees:
            st.error("⚠️ Need at least one Customer and one Employee to create an order.")
            st.info("Please add customers and employees first before using the order wizard.")
            return
        
        # Create customer and employee selection lists
        cust_labels = [f"{c['name']} — {c.get('shop_name', 'N/A')} (ID {c['customer_id']})" for c in customers]
        emp_labels = [f"{e['name']} (ID {e['employee_id']})" for e in employees]
        
        if st.session_state.wizard_step == 1:
            with st.form("order_basic_info"):
                col1, col2 = st.columns(2)
                
                with col1:
                    cust_choice = st.selectbox("🏪 Select Customer", cust_labels)
                    order_date = st.date_input("📅 Order Date", dt.date.today())
                
                with col2:
                    emp_choice = st.selectbox("👤 Handled By (Employee)", emp_labels)
                    status = st.selectbox("📊 Order Status", ["Pending", "Dispatched", "Delivered"], index=0)
                
                info_submitted = st.form_submit_button("Continue to Step 2 ➡️", type="primary")
                
                if info_submitted:
                    # Save order info to session state
                    customer_id = customers[cust_labels.index(cust_choice)]["customer_id"]
                    employee_id = employees[emp_labels.index(emp_choice)]["employee_id"]
                    
                    st.session_state.order_info = {
                        'customer_id': customer_id,
                        'employee_id': employee_id,
                        'customer_name': cust_choice,
                        'employee_name': emp_choice,
                        'order_date': order_date,
                        'status': status
                    }
                    st.session_state.wizard_step = 2
                    st.rerun()
        else:
            # Show completed step 1 info
            st.success("✅ Step 1 completed")
            st.info(f"Customer: {st.session_state.order_info['customer_name']}")
            st.info(f"Employee: {st.session_state.order_info['employee_name']}")
            if st.button("🔙 Edit Step 1"):
                st.session_state.wizard_step = 1
                st.rerun()
    
    # Step 2: Add Products to Cart
    if st.session_state.wizard_step >= 2:
        st.divider()
        st.subheader("🛒 Step 2: Add Products to Cart")
        
        products = execute_query("products", eq={"stock_quantity": 0}, neq={"stock_quantity": 0})  # Products with stock > 0
        
        if not products:
            st.error("⚠️ No products available with stock. Please add products first.")
            return
        
        # Initialize cart in session state
        if 'cart' not in st.session_state:
            st.session_state.cart = []
        
        # Create product map for easy lookup
        prod_map = {f"{p['name']} — ₹{p['unit_price']} (Stock: {p['stock_quantity']}) [ID {p['product_id']}]": p for p in products if p['stock_quantity'] > 0}
        prod_options = ["—"] + list(prod_map.keys())
        
        if st.session_state.wizard_step == 2:
            # Shopping Cart Interface
            st.info("💡 Add up to 10 products to your order")
            
            # Add product form
            with st.form("add_product_form"):
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    selected_product = st.selectbox("Select Product", prod_options)
                
                with col2:
                    quantity = st.number_input("Quantity", min_value=1, value=1)
                
                with col3:
                    # Show unit price if product selected
                    if selected_product and selected_product != "—":
                        product = prod_map[selected_product]
                        unit_price = float(product['unit_price'])
                        price = st.number_input("Unit Price ₹", value=unit_price, step=0.01)
                    else:
                        price = st.number_input("Unit Price ₹", value=0.0, step=0.01)
                
                add_product = st.form_submit_button("➕ Add to Cart")
                
                if add_product and selected_product and selected_product != "—":
                    product = prod_map[selected_product]
                    max_qty = int(product['stock_quantity'])
                    
                    if quantity <= max_qty:
                        # Check if product already in cart
                        existing_item = next((item for item in st.session_state.cart if item['product_id'] == product['product_id']), None)
                        
                        if existing_item:
                            existing_item['quantity'] += quantity
                            existing_item['line_total'] = existing_item['quantity'] * existing_item['unit_price']
                            st.success(f"Updated {product['name']} quantity in cart!")
                        else:
                            line_total = quantity * price
                            cart_item = {
                                'product_id': product['product_id'],
                                'name': product['name'],
                                'quantity': quantity,
                                'unit_price': price,
                                'line_total': line_total
                            }
                            st.session_state.cart.append(cart_item)
                            st.success(f"Added {product['name']} to cart!")
                        st.rerun()
                    else:
                        st.error(f"Only {max_qty} units available in stock!")
            
            # Display current cart
            if st.session_state.cart:
                st.subheader("🧾 Current Cart")
                
                # Add remove buttons
                for i, item in enumerate(st.session_state.cart):
                    col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 1])
                    col1.write(item['name'])
                    col2.write(str(item['quantity']))
                    col3.write(f"₹{item['unit_price']:,.2f}")
                    col4.write(f"₹{item['line_total']:,.2f}")
                    if col5.button("🗑️", key=f"remove_{i}"):
                        st.session_state.cart.pop(i)
                        st.rerun()
                
                order_total = sum(item['line_total'] for item in st.session_state.cart)
                st.success(f"🎯 **Cart Total: ₹{order_total:,.2f}**")
                
                col1, col2 = st.columns([1, 1])
                with col1:
                    if st.button("🗑️ Clear Cart", type="secondary"):
                        st.session_state.cart = []
                        st.rerun()
                with col2:
                    if st.button("Continue to Step 3 ➡️", type="primary"):
                        st.session_state.wizard_step = 3
                        st.rerun()
            else:
                st.info("Cart is empty. Add products to continue.")
        else:
            # Show cart summary
            if st.session_state.cart:
                st.success("✅ Step 2 completed")
                cart_total = sum(item['line_total'] for item in st.session_state.cart)
                st.info(f"Cart Items: {len(st.session_state.cart)} products, Total: ₹{cart_total:,.2f}")
                if st.button("🔙 Edit Cart"):
                    st.session_state.wizard_step = 2
                    st.rerun()
    
    # Step 3: Payment Information (Optional)
    if st.session_state.wizard_step >= 3:
        st.divider()
        st.subheader("💳 Step 3: Payment Information (Optional)")
        
        if 'payment_info' not in st.session_state:
            st.session_state.payment_info = {}
        
        if st.session_state.wizard_step == 3:
            cart_total = sum(item['line_total'] for item in st.session_state.cart)
            
            make_payment = st.checkbox("Record Payment Now", value=True)
            
            if make_payment:
                with st.form("payment_form"):
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        pay_date = st.date_input("Payment Date", dt.date.today())
                    
                    with col2:
                        pay_amount = st.number_input("Payment Amount ₹", value=float(cart_total), step=0.01, min_value=0.0)
                    
                    with col3:
                        pay_mode = st.selectbox("Payment Mode", ["Cash", "UPI", "Online Transfer", "Cheque"])
                    
                    payment_submitted = st.form_submit_button("Continue to Step 4 ➡️", type="primary")
                    
                    if payment_submitted:
                        st.session_state.payment_info = {
                            'make_payment': True,
                            'pay_date': pay_date,
                            'pay_amount': pay_amount,
                            'pay_mode': pay_mode
                        }
                        st.session_state.wizard_step = 4
                        st.rerun()
            else:
                if st.button("Skip Payment - Continue to Step 4 ➡️", type="primary"):
                    st.session_state.payment_info = {'make_payment': False}
                    st.session_state.wizard_step = 4
                    st.rerun()
        else:
            # Show payment summary
            st.success("✅ Step 3 completed")
            if st.session_state.payment_info.get('make_payment'):
                st.info(f"Payment: ₹{st.session_state.payment_info['pay_amount']:,.2f} via {st.session_state.payment_info['pay_mode']}")
            else:
                st.info("Payment: Skipped")
            if st.button("🔙 Edit Payment"):
                st.session_state.wizard_step = 3
                st.rerun()
    
    # Step 4: Transportation (Optional)
    if st.session_state.wizard_step >= 4:
        st.divider()
        st.subheader("🚚 Step 4: Transportation Details (Optional)")
        
        if 'transport_info' not in st.session_state:
            st.session_state.transport_info = {}
        
        if st.session_state.wizard_step == 4:
            add_transport = st.checkbox("Add Transportation Details", value=False)
            
            if add_transport:
                with st.form("transport_form"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        vehicle_number = st.text_input("Vehicle Number", placeholder="e.g., MH12AB1234")
                        driver_name = st.text_input("Driver Name", placeholder="Driver's full name")
                    
                    with col2:
                        transport_mode = st.selectbox("Transport Mode", ["Truck", "Van", "Mini Truck", "Tempo"])
                        departure_date = st.date_input("Departure Date", dt.date.today())
                        arrival_date = st.date_input("Expected Arrival Date", dt.date.today() + dt.timedelta(days=1))
                        t_status = st.selectbox("Transport Status", ["In Transit", "Delivered", "Delayed"], index=0)
                    
                    transport_submitted = st.form_submit_button("Continue to Final Step ➡️", type="primary")
                    
                    if transport_submitted:
                        st.session_state.transport_info = {
                            'add_transport': True,
                            'vehicle_number': vehicle_number,
                            'driver_name': driver_name,
                            'transport_mode': transport_mode,
                            'departure_date': departure_date,
                            'arrival_date': arrival_date,
                            't_status': t_status
                        }
                        st.session_state.wizard_step = 5
                        st.rerun()
            else:
                if st.button("Skip Transportation - Continue to Final Step ➡️", type="primary"):
                    st.session_state.transport_info = {'add_transport': False}
                    st.session_state.wizard_step = 5
                    st.rerun()
        else:
            # Show transport summary
            st.success("✅ Step 4 completed")
            if st.session_state.transport_info.get('add_transport'):
                st.info(f"Transport: {st.session_state.transport_info['transport_mode']} - {st.session_state.transport_info['vehicle_number']}")
            else:
                st.info("Transportation: Skipped")
            if st.button("🔙 Edit Transportation"):
                st.session_state.wizard_step = 4
                st.rerun()
    
    # Step 5: Final Confirmation and Creation
    if st.session_state.wizard_step == 5:
        st.divider()
        st.subheader("✅ Step 5: Create Order")
        
        # Summary box
        with st.expander("📋 Complete Order Summary", expanded=True):
            st.write(f"**Customer:** {st.session_state.order_info['customer_name'].split(' —')[0]}")
            st.write(f"**Employee:** {st.session_state.order_info['employee_name'].split(' (')[0]}")
            st.write(f"**Order Date:** {st.session_state.order_info['order_date']}")
            st.write(f"**Status:** {st.session_state.order_info['status']}")
            st.write(f"**Total Items:** {len(st.session_state.cart)}")
            
            cart_total = sum(item['line_total'] for item in st.session_state.cart)
            st.write(f"**Order Total:** ₹{cart_total:,.2f}")
            
            if st.session_state.payment_info.get('make_payment'):
                st.write(f"**Payment:** ₹{st.session_state.payment_info['pay_amount']:,.2f} via {st.session_state.payment_info['pay_mode']}")
            
            if st.session_state.transport_info.get('add_transport'):
                st.write(f"**Transport:** {st.session_state.transport_info['transport_mode']} - {st.session_state.transport_info['vehicle_number']} (Driver: {st.session_state.transport_info['driver_name']})")
        
        # Final creation button
        if st.button("🎯 Create Complete Order", type="primary", use_container_width=True):
            try:
                # Step 1: Create Order
                order_data = {
                    "customer_id": st.session_state.order_info['customer_id'],
                    "employee_id": st.session_state.order_info['employee_id'],
                    "order_date": str(st.session_state.order_info['order_date']),
                    "status": st.session_state.order_info['status']
                }
                order_result = execute_query("orders", operation="insert", data=order_data)
                
                if order_result:
                    order_id = order_result[0]['order_id']
                    
                    # Step 2: Create Order Items and Update Stock
                    for item in st.session_state.cart:
                        # Insert order item
                        item_data = {
                            "order_id": order_id,
                            "product_id": item['product_id'],
                            "quantity": item['quantity'],
                            "price": item['line_total']
                        }
                        execute_query("order_items", operation="insert", data=item_data)
                        
                        # Update product stock
                        current_product = execute_query("products", eq={"product_id": item['product_id']})[0]
                        new_stock = current_product['stock_quantity'] - item['quantity']
                        execute_query("products", operation="update", 
                                    data={"stock_quantity": new_stock}, 
                                    eq={"product_id": item['product_id']})
                    
                    # Step 3: Create Payment (if selected)
                    if st.session_state.payment_info.get('make_payment') and st.session_state.payment_info.get('pay_amount', 0) > 0:
                        payment_data = {
                            "order_id": order_id,
                            "payment_date": str(st.session_state.payment_info['pay_date']),
                            "amount": float(st.session_state.payment_info['pay_amount']),
                            "payment_mode": st.session_state.payment_info['pay_mode']
                        }
                        execute_query("payments", operation="insert", data=payment_data)
                    
                    # Step 4: Create Transportation (if selected)
                    transport_info = st.session_state.transport_info
                    if (transport_info.get('add_transport') and 
                        transport_info.get('vehicle_number') and 
                        transport_info.get('driver_name')):
                        transport_data = {
                            "order_id": order_id,
                            "vehicle_number": transport_info['vehicle_number'],
                            "driver_name": transport_info['driver_name'],
                            "transport_mode": transport_info['transport_mode'],
                            "departure_date": str(transport_info['departure_date']),
                            "arrival_date": str(transport_info['arrival_date']),
                            "status": transport_info['t_status']
                        }
                        execute_query("transportation", operation="insert", data=transport_data)
                    
                    # Success message
                    st.success(f"🎉 Order #{order_id} created successfully!")
                    
                    # Show created records summary
                    with st.expander("📊 Created Records Summary", expanded=True):
                        st.write(f"✅ Order ID: {order_id}")
                        st.write(f"✅ Order Items: {len(st.session_state.cart)} products")
                        if st.session_state.payment_info.get('make_payment'):
                            st.write(f"✅ Payment Record: ₹{st.session_state.payment_info['pay_amount']:,.2f}")
                        if st.session_state.transport_info.get('add_transport'):
                            st.write(f"✅ Transportation Record: {st.session_state.transport_info['transport_mode']}")
                        st.write("✅ Stock quantities updated")
                    
                    # Clear session state for new order
                    if st.button("🆕 Create Another Order"):
                        for key in ['wizard_step', 'order_info', 'cart', 'payment_info', 'transport_info']:
                            if key in st.session_state:
                                del st.session_state[key]
                        st.rerun()
                    
                    # Clear cache to reflect changes
                    st.cache_data.clear()
                else:
                    st.error("❌ Failed to create order: No order ID returned")
                    
            except Exception as e:
                st.error(f"❌ Failed to create order: {str(e)}")
                st.error("Please check your input data and try again.")

# =====================================================
# BULK IMPORT/EXPORT
# =====================================================

def page_bulk():
    if not check_permissions('Manager'):
        st.error("🔒 Access denied. Manager role required.")
        return
    
    st.title("📦 Bulk Import / Export")
    st.info("Export table data as CSV or import CSV files to add bulk records")
    
    # Table selection
    table_name = st.selectbox("📊 Select Table", list(TABLES.keys()), index=0)
    table_config = TABLES[table_name]
    
    st.divider()
    
    # Two main sections: Export and Import
    col1, col2 = st.columns([1, 1])
    
    # ===== EXPORT SECTION =====
    with col1:
        st.subheader("⬇️ Export Data")
        st.write(f"Download **{table_name}** data as CSV file")
        
        # Preview current data
        with st.expander("👀 Preview Current Data", expanded=False):
            preview_rows = execute_query(table_name, limit=10)
            if preview_rows:
                st.dataframe(to_df(preview_rows), use_container_width=True)
                total_count = get_count(table_name)
                st.info(f"Total records in {table_name}: {total_count}")
            else:
                st.info(f"No data available in {table_name}")
        
        # Export options
        export_limit = st.slider("Max records to export", 10, 10000, 1000)
        
        if st.button(f"📥 Export {table_name}", type="primary"):
            try:
                rows = execute_query(table_name, limit=export_limit)
                if rows:
                    df = to_df(rows)
                    csv_data = df.to_csv(index=False)
                    
                    st.download_button(
                        label=f"💾 Download {table_name}.csv",
                        data=csv_data.encode('utf-8'),
                        file_name=f"{table_name}_{dt.date.today().strftime('%Y%m%d')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                    st.success(f"✅ Export ready! {len(rows)} records prepared for download.")
                else:
                    st.warning("No data available to export.")
            except Exception as e:
                st.error(f"Export failed: {str(e)}")
    
    # ===== IMPORT SECTION =====
    with col2:
        st.subheader("⬆️ Import Data")
        st.write(f"Upload CSV file to add records to **{table_name}**")
        
        # Show expected format
        with st.expander("📋 Expected CSV Format", expanded=False):
            expected_columns = [col for col in table_config["cols"]]
            st.write("**Required columns (in any order):**")
            for i, col in enumerate(expected_columns, 1):
                col_type = table_config["types"][i-1]
                if col_type.startswith("fk:"):
                    ref_table = col_type.split(":")[1].split(".")[0]
                    st.write(f"• `{col}` - Foreign key to {ref_table}")
                elif col_type.startswith("choice:"):
                    choices = col_type.split(":")[1].split(",")
                    st.write(f"• `{col}` - Choice: {', '.join(choices)}")
                else:
                    st.write(f"• `{col}` - {col_type}")
            
            st.warning("⚠️ Do NOT include the primary key column in your CSV file.")
        
        # File upload
        uploaded_file = st.file_uploader(
            "Choose CSV file",
            type=['csv'],
            help="Upload a CSV file with the correct column format"
        )
        
        if uploaded_file is not None:
            try:
                # Read and preview the uploaded file
                df = pd.read_csv(uploaded_file)
                
                st.write("📊 **Uploaded File Preview:**")
                st.dataframe(df.head(10), use_container_width=True)
                st.info(f"File contains {len(df)} rows and {len(df.columns)} columns")
                
                # Validate columns
                expected_cols = set(table_config["cols"])
                uploaded_cols = set(df.columns)
                
                missing_cols = expected_cols - uploaded_cols
                extra_cols = uploaded_cols - expected_cols
                
                if missing_cols:
                    st.error(f"❌ Missing required columns: {', '.join(missing_cols)}")
                
                if extra_cols:
                    st.warning(f"⚠️ Extra columns (will be ignored): {', '.join(extra_cols)}")
                
                # Data validation summary
                validation_ok = len(missing_cols) == 0
                
                if validation_ok:
                    st.success("✅ File format is valid!")
                    
                    # Import options
                    col_a, col_b = st.columns(2)
                    
                    with col_a:
                        skip_duplicates = st.checkbox("Skip duplicate records", value=True)
                    
                    with col_b:
                        max_import = st.number_input("Max records to import", 1, len(df), min(len(df), 1000))
                    
                    # Final import button
                    if st.button(f"🚀 Import to {table_name}", type="primary"):
                        try:
                            # Prepare data for insertion
                            cols_to_insert = [c for c in table_config["cols"] if c in df.columns]
                            df_filtered = df[cols_to_insert].head(max_import)
                            
                            # Insert data row by row
                            success_count = 0
                            for _, row in df_filtered.iterrows():
                                try:
                                    row_data = {col: row[col] for col in cols_to_insert}
                                    execute_query(table_name, operation="insert", data=row_data)
                                    success_count += 1
                                except Exception as e:
                                    if not skip_duplicates:
                                        st.error(f"Error inserting row: {e}")
                                    # If skip_duplicates is True, silently continue
                            
                            # Success feedback
                            st.success(f"🎉 Successfully imported {success_count} records to {table_name}!")
                            
                            if skip_duplicates and success_count < len(df_filtered):
                                st.info(f"ℹ️ {len(df_filtered) - success_count} duplicate records were skipped.")
                            
                            # Clear cache to show updated data
                            st.cache_data.clear()
                            
                        except Exception as e:
                            st.error(f"❌ Import failed: {str(e)}")
                            st.error("Please check your data format and try again.")
                
                else:
                    st.error("❌ Please fix the file format issues before importing.")
                    
            except Exception as e:
                st.error(f"❌ Error reading file: {str(e)}")
                st.error("Please ensure the file is a valid CSV format.")
    
    # ===== QUICK TEMPLATES SECTION =====
    st.divider()
    st.subheader("📝 CSV Templates")
    st.write("Download empty CSV templates with correct column headers")
    
    template_cols = min(4, len(TABLES))
    template_columns = st.columns(template_cols)
    
    for i, (table_key, table_cfg) in enumerate(TABLES.items()):
        with template_columns[i % template_cols]:
            if st.button(f"📄 {table_key} Template", key=f"template_{table_key}"):
                # Create empty DataFrame with correct columns
                template_df = pd.DataFrame(columns=table_cfg["cols"])
                
                # Add one sample row with example data
                sample_row = {}
                for col, col_type in zip(table_cfg["cols"], table_cfg["types"]):
                    if col_type == "text":
                        sample_row[col] = f"Sample {col}"
                    elif col_type == "number":
                        sample_row[col] = 100.00
                    elif col_type == "int":
                        sample_row[col] = 1
                    elif col_type == "date":
                        sample_row[col] = dt.date.today().strftime('%Y-%m-%d')
                    elif col_type.startswith("choice:"):
                        choices = col_type.split(":")[1].split(",")
                        sample_row[col] = choices[0]
                    elif col_type.startswith("fk:"):
                        sample_row[col] = 1
                    else:
                        sample_row[col] = "Sample"
                
                template_df.loc[0] = sample_row
                csv_template = template_df.to_csv(index=False)
                
                st.download_button(
                    label=f"💾 Download {table_key}_template.csv",
                    data=csv_template.encode('utf-8'),
                    file_name=f"{table_key}_template.csv",
                    mime="text/csv",
                    key=f"download_template_{table_key}"
                )

# =====================================================
# ROUTER
# =====================================================

if page == "Dashboard":
    page_dashboard()
elif page in ["Customers", "Suppliers", "Products", "Employees", "Orders", "Order Items", "Payments", "Transportation"]:
    page_table(page.lower().replace(" ", "_"))
elif page == "Create Order Wizard":
    page_order_wizard()
elif page == "Bulk Import/Export":
    page_bulk()
elif page == "User Management":
    page_user_management()
else:
    st.info(f"Page '{page}' is not yet implemented with Supabase API.")
