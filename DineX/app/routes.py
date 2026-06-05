from app.customer_history import CustomerHistoryManager
from app.kitchen_queue import KitchenQueue
from app.customer_hash_table import CustomerHashTable
from flask import Blueprint, app, render_template, redirect, url_for, request, jsonify, session
from functools import wraps
import secrets
import json
import os
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash      
from app.priority_queue import OrderPriorityQueue
from app.avl_tree import MenuManager 
from app.bst_tree import CategoryMenuManager

from app.delivery_route import DeliveryGraph, OrderTimeCalculator 
from app.cart_undo_redo_stack import (
    cart_stack,
    handle_cart_delete,
    handle_undo,
    handle_redo,
    clear_stack_on_checkout
)

main = Blueprint('main', __name__)

# Initialize Order Priority Queue (in-memory)
order_queue = OrderPriorityQueue()
# Initialize Kitchen Queue (FIFO for cooking)
kitchen_queue = KitchenQueue()
menu_manager = MenuManager()
bst_manager = CategoryMenuManager()
delivery_graph = DeliveryGraph()
time_calculator = OrderTimeCalculator(delivery_graph)
customer_hash_table = CustomerHashTable(initial_capacity=16)
history_manager = CustomerHistoryManager()
# ===========================
# 🔐 HARDCODED ADMIN CREDENTIALS
# ===========================
HARDCODED_ADMINS = {
    'admin@dinex.com': {
        'password': 'admin123',
        'firstName': 'Admin',
        'lastName': 'User',
        'phone': '03000000000',
        'role': 'super_admin',
        'id': 999999
    },
    'kitchen@dinex.com': {
        'password': 'kitchen123',
        'firstName': 'Kitchen',
        'lastName': 'Manager',
        'phone': '03000000001',
        'role': 'kitchen',
        'id': 999998
    },
    'rider@dinex.com': {
        'password': 'rider123',
        'firstName': 'Delivery',
        'lastName': 'Rider',
        'phone': '03000000002',
        'role': 'rider',
        'id': 999997
    }
}

# Path to JSON files
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
USERS_FILE = os.path.join(DATA_DIR, 'users.json')
MENU_FILE = os.path.join(DATA_DIR, 'menu.json')
CUSTOMERS_FILE = os.path.join(DATA_DIR, 'customers.json')
ORDERS_FILE = os.path.join(DATA_DIR, 'orders.json')
DELIVERY_GRAPH_FILE = os.path.join(DATA_DIR, 'delivery_graph.json')
CART_FILE = os.path.join(DATA_DIR, 'cart.json')

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

# Initialize files
def init_json_file(filepath, default_data):
    if not os.path.exists(filepath):
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(default_data, f, indent=4, ensure_ascii=False)

init_json_file(USERS_FILE, [])
init_json_file(MENU_FILE, {"items": []})
init_json_file(CUSTOMERS_FILE, {"customers": []})
init_json_file(ORDERS_FILE, {"orders": [], "nextOrderId": 1})
init_json_file(DELIVERY_GRAPH_FILE, {"nodes": [], "edges": []})
init_json_file(CART_FILE, {"carts": {}})


# ===========================
# LOAD CUSTOMERS INTO HASH TABLE ON STARTUP
# ===========================
# ===========================
# KITCHEN REQUIRED DECORATOR
# ===========================
def kitchen_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_email' not in session:
            return redirect(url_for('main.login', next=request.url))
        
        user_email = session.get('user_email')
        user_role = session.get('user_role')
        
        # ✅ Allow hardcoded admins and kitchen staff
        if user_email in HARDCODED_ADMINS:
            return f(*args, **kwargs)
        
        # ✅ Allow kitchen role
        if user_role == 'kitchen':
            return f(*args, **kwargs)
        
        # ❌ Block everyone else
        return render_template(
            'error.html',
            message='Access Denied: Kitchen staff privileges required',
            error_code=403
        ), 403
    
    return decorated_function

def load_customers_into_hash_table():
    """
    Load all customers from JSON file into hash table for O(1) lookup.
    Call this function on application startup.
    
    Time Complexity: O(n) where n = number of customers (one-time cost)
    """
    try:
        customers_data = load_customers()
        customers = customers_data.get('customers', [])
        
        if customers:
            for customer in customers:
                customer_hash_table.insert_customer(customer)
            
            stats = customer_hash_table.get_statistics()
            print(f"✅ Loaded {len(customer_hash_table)} customers into Hash Table")
            print(f"   Load Factor: {stats['load_factor']:.2f}")
            print(f"   Average Chain Length: {stats['average_chain_length']:.2f}")
        else:
            print("⚠️ No customers found in customers.json")
    except Exception as e:
        print(f"❌ Error loading customers into hash table: {e}")

def load_orders_into_history():
    """
    Load all completed orders into customer history linked lists.
    Call this function on application startup.
    
    Time Complexity: O(n) where n = number of orders (one-time cost)
    """
    try:
        orders_data = load_orders()
        orders = orders_data.get('orders', [])
        
        # Only load completed/delivered orders into history
        completed_orders = [
            o for o in orders 
            if o.get('status') in ['delivered', 'completed']
        ]
        
        if completed_orders:
            for order in completed_orders:
                history_manager.add_order(order)
            
            print(f"✅ Loaded {len(completed_orders)} orders into customer history")
            print(f"   Tracking {len(history_manager)} customers")
        else:
            print("⚠️ No completed orders found")
    except Exception as e:
        print(f"❌ Error loading order history: {e}")


# ===========================
# HELPER FUNCTION: Sync Hash Table to File
# ===========================
def sync_customers_to_file():
    """
    Save all customers from hash table back to JSON file.
    Maintains data persistence while using in-memory hash table.
    
    NOTE: File remains the single source of truth.
    Hash table is just an in-memory index for fast lookups.
    """
    customers_data = {
        'customers': customer_hash_table.get_all_customers()
    }
    save_customers(customers_data)



def load_menu_into_trees():
    json_path = os.path.join(os.path.dirname(__file__), 'data', 'menu.json')
    
    try:
        # Load JSON file once
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Handle both JSON formats
        if isinstance(data, dict) and 'items' in data:
            items_list = data['items']
        elif isinstance(data, list):
            items_list = data
        else:
            raise ValueError("Invalid JSON format")
        
        # Load into AVL tree (original - takes list)
        menu_manager.load_items(items_list)
        
        # Load into BST (new - takes JSON path)
        bst_manager.load_items_from_json(json_path)
        
        # Get stats
        bst_stats = bst_manager.get_statistics()
        
        print(f"✅ Menu loaded successfully!")
        print(f"   AVL Trees: {len(items_list)} items")
        print(f"   BST Trees: {bst_stats['total_items']} items")
        print(f"   BST Categories: {list(bst_manager.categories.keys())}")
        
    except Exception as e:
        print(f"❌ Error loading menu: {e}")
        import traceback
        traceback.print_exc()
    
# ===========================
# LOAD EXISTING ORDERS INTO PRIORITY QUEUE ON STARTUP
# ===========================
def load_orders_into_queue():
    """
    ✅ FIXED: Load orders from file into priority queue on startup
    """
    try:
        orders_data = load_orders()
        orders = orders_data.get('orders', [])
        
        print(f"\n{'='*60}")
        print(f"📂 LOADING ORDERS FROM FILE")
        print(f"{'='*60}")
        print(f"Total orders in file: {len(orders)}")
        
        pending_count = 0
        processing_count = 0
        completed_count = 0
        
        for order in orders:
            status = order.get('status', 'pending')
            
            if status == 'pending':
                order_queue.pending_queue.insert(order)
                pending_count += 1
            elif status == 'processing':
                order_queue.processing_orders.append(order)
                processing_count += 1
            elif status in ['completed', 'delivered']:
                order_queue.completed_orders.append(order)
                completed_count += 1
        
        print(f"✅ Loaded into priority queue:")
        print(f"   Pending: {pending_count}")
        print(f"   Processing: {processing_count}")
        print(f"   Completed: {completed_count}")
        print(f"{'='*60}\n")
        
    except Exception as e:
        print(f"❌ Error loading orders: {e}")
        import traceback
        traceback.print_exc()

def load_orders_into_kitchen():
    """
    Load orders from file into kitchen FIFO queue on startup
    
    LOGIC:
    - Only 'pending' orders go to kitchen waiting queue
    - 'cooking' orders go to cooking_orders list
    - 'completed' orders (cooked) go to completed_orders list
    """
    try:
        orders_data = load_orders()
        orders = orders_data.get('orders', [])
        
        print(f"\n{'='*60}")
        print(f"👨‍🍳 LOADING ORDERS INTO KITCHEN QUEUE")
        print(f"{'='*60}")
        print(f"Total orders in file: {len(orders)}")
        
        waiting_count = 0
        cooking_count = 0
        completed_count = 0
        
        for order in orders:
            # Check kitchen status (if it exists)
            kitchen_status = order.get('kitchenStatus', 'waiting')
            
            if kitchen_status == 'waiting':
                kitchen_queue.enqueue(order)
                waiting_count += 1
            elif kitchen_status == 'cooking':
                kitchen_queue.cooking_orders.append(order)
                cooking_count += 1
            elif kitchen_status == 'completed':
                kitchen_queue.completed_orders.append(order)
                completed_count += 1
        
        print(f"✅ Loaded into kitchen queue:")
        print(f"   Waiting: {waiting_count}")
        print(f"   Cooking: {cooking_count}")
        print(f"   Completed: {completed_count}")
        print(f"{'='*60}\n")
        
    except Exception as e:
        print(f"❌ Error loading kitchen orders: {e}")
        import traceback
        traceback.print_exc()

# =============================================================================
# SYNC FUNCTION FOR KITCHEN QUEUE
# =============================================================================

def sync_kitchen_to_file():
    """
    Save all orders from kitchen queue back to JSON file
    
    IMPORTANT: This updates the kitchenStatus field for each order
    """
    try:
        orders_data = load_orders()
        
        # Get all orders from both kitchen and delivery queues
        all_orders = []
        
        # Method 1: Update orders with kitchen status
        for order in orders_data.get('orders', []):
            order_id = order['orderId']
            
            # Check if order is in kitchen queue
            kitchen_order = kitchen_queue.find_order(order_id)
            
            if kitchen_order:
                # Update kitchen status
                order['kitchenStatus'] = kitchen_order['stage']
                if 'cookingStartedAt' in kitchen_order['order']:
                    order['cookingStartedAt'] = kitchen_order['order']['cookingStartedAt']
                if 'cookingCompletedAt' in kitchen_order['order']:
                    order['cookingCompletedAt'] = kitchen_order['order']['cookingCompletedAt']
            
            all_orders.append(order)
        
        # Save back to file
        orders_data['orders'] = all_orders
        save_orders(orders_data)
        
        stats = kitchen_queue.get_statistics()
        print(f"✅ Kitchen queue synced to file")
        print(f"   Waiting: {stats['waiting']}")
        print(f"   Cooking: {stats['cooking']}")
        print(f"   Completed: {stats['completed']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Kitchen sync error: {e}")
        import traceback
        traceback.print_exc()
        return False


# ===========================
# LOGIN REQUIRED DECORATOR
# ===========================
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_email' not in session:
            return jsonify({
                'success': False, 
                'message': 'Please login first',
                'login_required': True
            }), 401
        return f(*args, **kwargs)
    return decorated_function

# ===========================
# ADMIN REQUIRED DECORATOR
# ===========================
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_email' not in session:
            return redirect(url_for('main.login', next=request.url))
        
        user_role = session.get('user_role', 'customer')
        if user_role not in ['admin', 'super_admin']:
            return render_template('error.html', 
                                 message='Access Denied: Admin privileges required',
                                 error_code=403), 403
        
        return f(*args, **kwargs)
    return decorated_function

def rider_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user_email = session.get('user_email')
        user_role = session.get('user_role')

        # ✅ Allow hardcoded admins
        if user_email in HARDCODED_ADMINS:
            return f(*args, **kwargs)

        # ✅ Allow riders
        if user_role == 'rider':
            return f(*args, **kwargs)

        # ❌ Block everyone else
        return render_template(
            'error.html',
            message='Access Denied: Rider or Admin privileges required',
            error_code=403
        ), 403

    return decorated




# Helper Functions
def load_json(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {} if 'menu' in filepath or 'customers' in filepath or 'orders' in filepath or 'cart' in filepath else []
            return json.loads(content)
    except (FileNotFoundError, json.JSONDecodeError):
        return {} if 'menu' in filepath or 'customers' in filepath or 'orders' in filepath or 'cart' in filepath else []

def save_json(filepath, data):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def load_users():
    return load_json(USERS_FILE)

def save_users(users):
    save_json(USERS_FILE, users)

def load_menu():
    return load_json(MENU_FILE)

def save_menu(menu):
    save_json(MENU_FILE, menu)

def load_customers():
    return load_json(CUSTOMERS_FILE)

def save_customers(customers):
    save_json(CUSTOMERS_FILE, customers)

def load_orders():
    return load_json(ORDERS_FILE)

def save_orders(orders):
    save_json(ORDERS_FILE, orders)

def load_carts():
    return load_json(CART_FILE)

def save_carts(carts):
    save_json(CART_FILE, carts)

def get_cart_key():
    if 'user_phone' in session:
        return session['user_phone']
    if 'cart_id' not in session:
        session['cart_id'] = secrets.token_hex(16)
    return session['cart_id']

def find_user_by_email_or_phone(email_phone):
    """Find user in database OR hardcoded admins"""
    # First check hardcoded admins
    if email_phone in HARDCODED_ADMINS:
        return HARDCODED_ADMINS[email_phone]
    
    # Then check regular users
    users = load_users()
    for user in users:
        if user['email'].lower() == email_phone.lower() or user.get('phone') == email_phone:
            return user
    return None

# ===========================
# SYNC FUNCTION: Save queue state to file
# ===========================
def sync_queue_to_file():
    orders_data = load_orders()
    orders = orders_data.get('orders', [])

    order_map = {o['orderId']: o for o in orders}

    queue_orders = (
        order_queue.get_all_pending_orders() +
        order_queue.get_processing_orders() +
        order_queue.get_completed_orders()
    )

    for q in queue_orders:
        oid = q['orderId']

        # 🚫 DO NOT overwrite delivered orders
        if oid in order_map and order_map[oid].get('status') == 'delivered':
            continue

        if oid in order_map:
            order_map[oid].update(q)
        else:
            order_map[oid] = q

    orders_data['orders'] = list(order_map.values())
    save_orders(orders_data)


# ===========================
# PAGE ROUTES
# ===========================
@main.route('/')
@main.route('/index')
@main.route('/home')
def index():
    return render_template('index.html')

@main.route('/about')
def about():
    return render_template('about.html')

# ===========================
# FIXED /menu ROUTE
# Copy this ENTIRE function and REPLACE your existing /menu route
# ===========================

@main.route('/menu')
def menu():
    """
    Menu page with BST-based filtering
    
    FEATURES:
    ✅ Category filtering (main, beverage, dessert, appetizer)
    ✅ Price range filtering
    ✅ Sorted by price (BST se)
    """
    
    # Get parameters from URL
    category = request.args.get('category', 'all')
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    
    # ✅ FIX 1: Convert category to lowercase (case-insensitive matching)
    category = category.lower().strip()
    
    # ✅ FIX 2: Debug print (optional - remove in production)
    print(f"🔍 Menu Filter Request:")
    print(f"   Category: {category}")
    print(f"   Min Price: {min_price}")
    print(f"   Max Price: {max_price}")
    
    # ✅ FIX 3: Use BST for filtering
    try:
        # If price filters are provided, use price range search
        if min_price is not None or max_price is not None:
            min_p = min_price if min_price is not None else 0
            max_p = max_price if max_price is not None else float('inf')
            
            menu_items = bst_manager.search_by_category_and_price(
                category=category,
                min_price=min_p,
                max_price=max_p
            )
            print(f"✅ Price filter applied: Found {len(menu_items)} items")
        
        # No price filter - just get category items
        else:
            menu_items = bst_manager.get_category_items(
                category=category,
                sort_by='price'  # Sorted by price (default)
            )
            print(f"✅ Category filter applied: Found {len(menu_items)} items")
        
        # ✅ FIX 4: Show what we got
        if menu_items:
            print(f"   First item: {menu_items[0]['name']} - Rs.{menu_items[0]['price']}")
        else:
            print(f"   ⚠️ No items found for category '{category}'")
    
    except Exception as e:
        print(f"❌ Menu filter error: {e}")
        menu_items = []
    
    return render_template('menu.html', menu_items=menu_items)

@main.route('/orders')
def orders():
    return redirect(url_for('main.index') + '#orders')

@main.route('/tracking')
def tracking():
    return redirect(url_for('main.index') + '#tracking')

# ===========================
# AUTH ROUTES WITH HARDCODED ADMIN CHECK
# ===========================
@main.route('/api/check-session')
def check_session():
    if 'user_email' not in session:
        return jsonify({'logged_in': False}), 200
    
    user_email = session['user_email']
    
    # Check if hardcoded admin
    if user_email in HARDCODED_ADMINS:
        admin = HARDCODED_ADMINS[user_email]
        return jsonify({
            'logged_in': True,
            'user': {
                'email': user_email,
                'firstName': admin['firstName'],
                'lastName': admin['lastName'],
                'phone': admin['phone'],
                'role': admin['role']
            }
        }), 200
    
    # Check regular user
    user = find_user_by_email_or_phone(user_email)
    if user:
        return jsonify({
            'logged_in': True,
            'user': {
                'email': user['email'],
                'firstName': user['firstName'],
                'lastName': user['lastName'],
                'phone': user.get('phone', ''),
                'role': user.get('role', 'customer')
            }
        }), 200
    
    return jsonify({'logged_in': False}), 200
@main.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        email_phone = data.get('emailPhone', '').strip()
        password = data.get('password', '').strip()
        
        if not email_phone or not password:
            return jsonify({'success': False, 'message': 'Email/Phone and password are required'}), 400
        
        # 🔍 CHECK HARDCODED ADMINS FIRST
        if email_phone in HARDCODED_ADMINS:
            admin = HARDCODED_ADMINS[email_phone]
            
            # Direct password comparison (not hashed)
            if password == admin['password']:
                # Set session
                session.permanent = True
                session['user_email'] = email_phone
                session['user_id'] = admin['id']
                session['user_phone'] = admin['phone']
                session['user_role'] = admin['role']
                session['name'] = f"{admin['firstName']} {admin['lastName']}"
                
                # ✅ FIXED: Dynamic success message based on role
                role_messages = {
                    'super_admin': 'Super Admin login successful!',
                    'admin': 'Admin login successful!',
                    'kitchen': 'Kitchen login successful!',
                    'rider': 'Rider login successful!'
                }
                success_message = role_messages.get(admin['role'], 'Login successful!')
                
                return jsonify({
                    'success': True,
                    'message': success_message,
                    'user': {
                        'email': email_phone,
                        'firstName': admin['firstName'],
                        'lastName': admin['lastName'],
                        'phone': admin['phone'],
                        'role': admin['role']
                    }
                }), 200
            else:
                return jsonify({'success': False, 'message': 'Invalid credentials'}), 401
        
        # Check regular users
        user = find_user_by_email_or_phone(email_phone)
        if not user:
            return jsonify({'success': False, 'message': 'Invalid email/phone or password'}), 401
        
        stored_password = user['password']

        try:
            result = check_password_hash(stored_password, password)

            if not result:
                return jsonify({'success': False, 'message': 'Invalid email/phone or password'}), 401
        except Exception as e:
            print("HASH ERROR:", e)
            if stored_password != password:
                return jsonify({'success': False, 'message': 'Invalid email/phone or password'}), 401
                
        # Update last login for regular users
        users = load_users()
        for u in users:
            if u['email'] == user['email']:
                u['lastLogin'] = datetime.now().isoformat()
                break
        save_users(users)
        
        # Set session for regular user
        session.permanent = True
        session['user_email'] = user['email']
        session['user_id'] = user['id']
        session['user_phone'] = user.get('phone', '')
        session['user_role'] = user.get('role', 'customer')
        session['name'] = f"{user['firstName']} {user['lastName']}"
        
        return jsonify({
            'success': True,
            'message': 'Login successful!',  # ✅ Regular users get generic message
            'user': {
                'email': user['email'], 
                'firstName': user['firstName'], 
                'lastName': user['lastName'], 
                'phone': user.get('phone', ''),
                'role': user.get('role', 'customer')
            }
        }), 200
    
    return render_template('login.html')

@main.route('/signup', methods=['POST'])
def signup():
    try:
        data = request.get_json()
        first_name = data.get('firstName', '').strip()
        last_name = data.get('lastName', '').strip()
        email = data.get('email', '').strip().lower()
        phone = data.get('phone', '').strip()
        password = data.get('password', '')
        
        # 🔒 PREVENT USING ADMIN EMAILS
        if email in HARDCODED_ADMINS:
            return jsonify({'success': False, 'message': 'This email is reserved'}), 400
        
        if not all([first_name, last_name, email, phone, password]):
            return jsonify({'success': False, 'message': 'All fields are required'}), 400
        
        users = load_users()
        if any(user['email'] == email for user in users):
            return jsonify({'success': False, 'message': 'Email already registered'}), 400
        if any(user.get('phone') == phone for user in users):
            return jsonify({'success': False, 'message': 'Phone number already registered'}), 400
        
        # Create new customer (only customers can signup)
        new_user = {
            'id': len(users) + 1,
            'firstName': first_name,
            'lastName': last_name,
            'email': email,
            'phone': phone,
            'password': generate_password_hash(password),
            'role': 'customer',  # Always customer
            'createdAt': datetime.now().isoformat(),
            'lastLogin': None
        }
        users.append(new_user)
        save_users(users)
        
        # Create customer record
        customers_data = load_customers()
        new_customer = {
            'phone': phone,
            'name': f"{first_name} {last_name}",
            'email': email,
            'address': '',
            'orderHistory': [],
            'loyaltyPoints': 0,
            'preferences': [],
            'isVIP': False,
            'registeredAt': datetime.now().isoformat(),
            'totalOrders': 0,
            'totalSpent': 0
        }
        if 'customers' not in customers_data:
            customers_data['customers'] = []
        customers_data['customers'].append(new_customer)
        save_customers(customers_data)
        
        # Set session
        session.permanent = True
        session['user_email'] = email
        session['user_id'] = new_user['id']
        session['user_phone'] = phone
        session['user_role'] = 'customer'
        session['name'] = f"{first_name} {last_name}"
        
        return jsonify({'success': True, 'message': 'Account created successfully!', 'role': 'customer'}), 201
    except Exception as e:
        print(f"Signup error: {e}")
        return jsonify({'success': False, 'message': 'Signup failed. Please try again.'}), 500

@main.route('/logout')
def logout():
    clear_stack_on_checkout()
    session.clear()
    return redirect(url_for('main.login'))

# ===========================
# 🌳 MENU ROUTES WITH AVL TREE
# ===========================
@main.route('/api/menu', methods=['GET'])
def get_menu():
    try:
        sort_by = request.args.get('sort', 'name')
        sort_mapping = {
            'name': 'name',
            'price-low': 'price-low',
            'price-high': 'price-high',
            'popular': 'popular'
        }
        sort_key = sort_mapping.get(sort_by, 'name')
        items = menu_manager.get_sorted_items(sort_key)
        
        return jsonify({
            'success': True, 
            'items': items,
            'sortedBy': sort_by
        }), 200
    except Exception as e:
        print(f"Menu load error: {e}")
        return jsonify({'success': False, 'message': 'Failed to load menu'}), 500
    
@main.route('/search')
def search():
    query = request.args.get('q', '')
    
    # ✅ Original manager for name search
    results = menu_manager.search_by_name(query)
    
    return jsonify(results)

@main.route('/api/menu/search', methods=['GET'])
def search_menu():
    try:
        query = request.args.get('q', '').strip()
        category = request.args.get('category', 'all')
        max_price = request.args.get('max_price', None)
        sort_by = request.args.get('sort', 'name')
        
        max_price_val = float(max_price) if max_price else None
        
        sort_mapping = {
            'name': 'name',
            'price-low': 'price-low',
            'price-high': 'price-high',
            'popular': 'popular'
        }
        sort_key = sort_mapping.get(sort_by, 'name')
        
        items = menu_manager.search_items(
            query=query,
            category=category,
            min_price=None,
            max_price=max_price_val,
            sort_by=sort_key
        )
        
        return jsonify({
            'success': True, 
            'items': items,
            'count': len(items)
        }), 200
    except Exception as e:
        print(f"Menu search error: {e}")
        return jsonify({'success': False, 'message': 'Search failed'}), 500

@main.route('/api/menu/stats', methods=['GET'])
def get_menu_stats():
    """Get menu statistics from AVL trees"""
    try:
        stats = menu_manager.get_statistics()
        
        return jsonify({
            'success': True,
            'stats': stats
        }), 200
    except Exception as e:
        print(f"Stats error: {e}")
        return jsonify({'success': False, 'message': 'Failed to get statistics'}), 500

# ===========================
# CUSTOMER ROUTES
# ===========================
@main.route('/api/customer/<phone>', methods=['GET'])
def get_customer(phone):
    """
    Get customer by phone number using O(1) hash table lookup.
    
    BEFORE: O(n) linear search through JSON array
    AFTER: O(1) hash table lookup
    
    Performance Improvement: 
    - 1000 customers: 1000x faster
    - 10000 customers: 10000x faster
    """
    try:
        # O(1) lookup using hash table
        customer = customer_hash_table.get_customer_by_phone(phone)
        
        if customer:
            return jsonify({'success': True, 'customer': customer}), 200
        else:
            return jsonify({'success': False, 'message': 'Customer not found'}), 404
    except Exception as e:
        print(f"Customer lookup error: {e}")
        return jsonify({'success': False, 'message': 'Failed to find customer'}), 500



@main.route('/api/customer/register', methods=['POST'])
def register_customer():
    """
    Register new customer with hash table integration.
    
    PROCESS:
    1. Validate input data
    2. Check if customer exists using O(1) hash table lookup
    3. Insert into hash table (O(1))
    4. Save to JSON file for persistence
    """
    try:
        data = request.get_json()
        phone = data.get('phone', '').strip()
        name = data.get('name', '').strip()
        email = data.get('email', '').strip()
        address = data.get('address', '').strip()
        
        if not phone or not name:
            return jsonify({'success': False, 'message': 'Phone and name are required'}), 400
        
        # O(1) check if customer already exists
        existing = customer_hash_table.get_customer_by_phone(phone)
        if existing:
            # Update address if provided
            if address:
                customer_hash_table.update_customer(phone, {'address': address})
                sync_customers_to_file()
            
            return jsonify({
                'success': True, 
                'message': 'Customer already exists', 
                'customer': existing
            }), 200
        
        # Create new customer
        new_customer = {
            'phone': phone,
            'name': name,
            'email': email,
            'address': address,
            'orderHistory': [],
            'loyaltyPoints': 0,
            'preferences': [],
            'isVIP': False,
            'registeredAt': datetime.now().isoformat(),
            'totalOrders': 0,
            'totalSpent': 0
        }
        
        # O(1) insert into hash table
        customer_hash_table.insert_customer(new_customer)
        
        # Persist to file
        sync_customers_to_file()
        
        return jsonify({
            'success': True, 
            'message': 'Customer registered successfully', 
            'customer': new_customer
        }), 201
    except Exception as e:
        print(f"Customer registration error: {e}")
        return jsonify({'success': False, 'message': 'Registration failed'}), 500


# ===========================
# CART ROUTES
# ===========================
@main.route('/api/cart', methods=['GET'])
@login_required
def get_cart():
    try:
        cart_key = get_cart_key()
        carts_data = load_carts()
        if 'carts' not in carts_data:
            carts_data['carts'] = {}
        
        user_cart = carts_data['carts'].get(cart_key, {'items': []})
        items = user_cart.get('items', [])
        
        subtotal = sum(item['price'] * item['quantity'] for item in items)
        delivery_fee = 50 if items else 0
        total = subtotal + delivery_fee
        
        return jsonify({
            'success': True,
            'cart': items,
            'subtotal': subtotal,
            'deliveryFee': delivery_fee,
            'total': total,
            'itemCount': len(items)
        }), 200
    except Exception as e:
        print(f"Cart load error: {e}")
        return jsonify({'success': False, 'message': 'Failed to load cart'}), 500

@main.route('/api/cart/add', methods=['POST'])
@login_required
def add_to_cart():
    try:
        data = request.get_json()
        item_id = data.get('id')
        name = data.get('name')
        price = data.get('price')
        quantity = data.get('quantity', 1)
        image = data.get('image', '')
        
        if not all([item_id, name, price]):
            return jsonify({'success': False, 'message': 'Item details are required'}), 400
        
        cart_key = get_cart_key()
        carts_data = load_carts()
        if 'carts' not in carts_data:
            carts_data['carts'] = {}
        
        if cart_key not in carts_data['carts']:
            carts_data['carts'][cart_key] = {'items': [], 'createdAt': datetime.now().isoformat()}
        
        cart_items = carts_data['carts'][cart_key]['items']
        existing = next((item for item in cart_items if item['id'] == item_id), None)
        
        if existing:
            # Track old/new quantities for undo
            old_quantity = existing.get('quantity', 0)
            new_quantity = old_quantity + quantity
            # Create snapshot
            item_snapshot = existing.copy()
            item_snapshot['old_quantity'] = old_quantity
            item_snapshot['new_quantity'] = new_quantity
            # Update quantity
            existing['quantity'] = new_quantity
            # Push increase action
            from app.cart_undo_redo_stack import cart_stack
            cart_stack.push_action('increase', item_snapshot, old_quantity, new_quantity)
        else:
            # New item added
            position = len(cart_items)
            new_item = {'id': item_id, 'name': name, 'price': price, 'quantity': quantity, 'image': image, 'position_in_cart': position}
            cart_items.append(new_item)
            from app.cart_undo_redo_stack import cart_stack
            cart_stack.push_action('add', new_item)

        carts_data['carts'][cart_key]['lastUpdated'] = datetime.now().isoformat()
        save_carts(carts_data)
        
        # Calculate totals
        subtotal = sum(item['price'] * item['quantity'] for item in cart_items)
        delivery_fee = 50
        total = subtotal + delivery_fee
        
        # Get stack status
        stack_status = cart_stack.get_stack_status()
        
        return jsonify({
            'success': True,
            'message': 'Item added to cart',
            'cart': cart_items,
            'subtotal': subtotal,
            'deliveryFee': delivery_fee,
            'total': total,
            'itemCount': len(cart_items),
            'stack_status': stack_status
        }), 200
        
    except Exception as e:
        print(f'Add to cart error: {e}')
        return jsonify({'success': False, 'message': 'Failed to add item'}), 500

@main.route('/api/cart/update/<int:item_id>', methods=['PUT'])
@login_required
def update_cart_item(item_id):
    try:
        data = request.get_json()
        quantity = data.get('quantity', 1)
        
        if quantity < 1:
            return jsonify({'success': False, 'message': 'Quantity must be at least 1'}), 400
        
        cart_key = get_cart_key()
        carts_data = load_carts()
        
        if 'carts' not in carts_data or cart_key not in carts_data['carts']:
            return jsonify({'success': False, 'message': 'Cart not found'}), 404
        
        cart_items = carts_data['carts'][cart_key]['items']
        
        # Find item
        target_item = None
        for item in cart_items:
            if item['id'] == item_id:
                target_item = item
                break
        
        if not target_item:
            return jsonify({'success': False, 'message': 'Item not found'}), 404
        
        old_quantity = target_item['quantity']
        
        # ✅ Only track if quantity actually changed
        if old_quantity != quantity:
            from app.cart_undo_redo_stack import cart_stack
            
            # Create item snapshot
            item_snapshot = {
                'id': target_item['id'],
                'name': target_item['name'],
                'price': target_item['price'],
                'quantity': old_quantity,
                'image': target_item.get('image', ''),
                'old_quantity': old_quantity,
                'new_quantity': quantity
            }
            
            # Determine action type
            action_type = 'increase' if quantity > old_quantity else 'decrease'
            
            # ✅ Push to stack
            cart_stack.push_action(action_type, item_snapshot, old_quantity, quantity)
        
        # Update quantity
        target_item['quantity'] = quantity
        
        # Save changes
        carts_data['carts'][cart_key]['lastUpdated'] = datetime.now().isoformat()
        save_carts(carts_data)
        
        # Calculate totals
        subtotal = sum(item['price'] * item['quantity'] for item in cart_items)
        delivery_fee = 50 if cart_items else 0
        total = subtotal + delivery_fee
        
        # ✅ Get stack status
        from app.cart_undo_redo_stack import cart_stack
        stack_status = cart_stack.get_stack_status()
        
        return jsonify({
            'success': True,
            'message': 'Cart updated',
            'cart': cart_items,
            'subtotal': subtotal,
            'deliveryFee': delivery_fee,
            'total': total,
            'itemCount': len(cart_items),
            'stack_status': stack_status  # ← Always return this!
        }), 200
        
    except Exception as e:
        print(f"Update cart error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': 'Failed to update cart'}), 500

@main.route('/api/cart/remove/<int:item_id>', methods=['DELETE'])
@login_required
def remove_from_cart(item_id):
    try:
        cart_key = get_cart_key()
        carts_data = load_carts()
        
        if 'carts' not in carts_data or cart_key not in carts_data['carts']:
            return jsonify({'success': False, 'message': 'Cart not found'}), 404
        
        cart = carts_data['carts'][cart_key].get('items', [])
        
        if not cart:
            return jsonify({'success': False, 'message': 'Cart is empty'}), 400
        
        # Find item
        item_position = None
        deleted_item = None
        
        for i, item in enumerate(cart):
            if item['id'] == item_id:
                item_position = i
                deleted_item = item.copy()
                deleted_item['position_in_cart'] = i
                break
        
        if deleted_item is None:
            return jsonify({'success': False, 'message': 'Item not found in cart'}), 404
        
        # ✅ Push to stack BEFORE deleting
        from app.cart_undo_redo_stack import cart_stack
        cart_stack.push_action('delete', deleted_item)
        
        # Remove from cart
        cart.pop(item_position)
        
        # Save
        carts_data['carts'][cart_key]['items'] = cart
        carts_data['carts'][cart_key]['lastUpdated'] = datetime.now().isoformat()
        save_carts(carts_data)
        
        # ✅ Get fresh stack status
        stack_status = cart_stack.get_stack_status()
        
        return jsonify({
            'success': True,
            'message': f'{deleted_item["name"]} removed from cart',
            'cart': cart,
            'stack_status': stack_status  # ← CRITICAL: Always return this!
        }), 200
        
    except Exception as e:
        print(f"Remove error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': 'Failed to remove item'}), 500

@main.route('/api/cart/clear', methods=['DELETE'])
@login_required
def clear_cart():
    try:
        cart_key = get_cart_key()
        carts_data = load_carts()
        if 'carts' not in carts_data:
            carts_data['carts'] = {}
        
        # Remove the entire cart entry to avoid accidental repopulation
        if cart_key in carts_data.get('carts', {}):
            try:
                del carts_data['carts'][cart_key]
            except KeyError:
                carts_data['carts'][cart_key] = {'items': []}
        
        save_carts(carts_data)
        # Also clear undo/redo stacks to avoid restoring cleared items
        try:
            clear_stack_on_checkout()
            stack_status = cart_stack.get_stack_status()
        except Exception:
            stack_status = {'can_undo': False, 'can_redo': False, 'undo_count': 0, 'redo_count': 0}

        return jsonify({'success': True, 'message': 'Cart cleared', 'cart': [], 'subtotal': 0, 'deliveryFee': 0, 'total': 0, 'itemCount': 0, 'stack_status': stack_status}), 200
    except Exception as e:
        print(f"Clear cart error: {e}")
        return jsonify({'success': False, 'message': 'Failed to clear cart'}), 500
    
@main.route('/track')
def track_order():
    return render_template('track.html')

# ===========================
# ORDER ROUTES - WITH PRIORITY QUEUE
# ===========================
@main.route('/api/orders/place', methods=['POST'])
@login_required
def place_order():
    """
    Place order with DUAL PIPELINE integration + DELIVERY ETA:
    1. Add to KITCHEN QUEUE (FIFO for cooking)
    2. Add to DELIVERY QUEUE (Priority for delivery)
    3. Calculate delivery route and ETA  # ✅ ADDED
    """
    try:
        data = request.get_json()
        customer_phone = data.get('customerPhone', '').strip()
        customer_name = data.get('customerName', '').strip()
        customer_address = data.get('customerAddress', '').strip()
        order_type = data.get('orderType', 'regular')
        
        if not customer_phone or not customer_name or not customer_address:
            return jsonify({'success': False, 'message': 'All customer info is required'}), 400
        
        # Get cart items
        cart_key = get_cart_key()
        carts_data = load_carts()
        if 'carts' not in carts_data or cart_key not in carts_data['carts']:
            return jsonify({'success': False, 'message': 'Cart is empty'}), 400
        
        items = carts_data['carts'][cart_key].get('items', [])
        if not items:
            return jsonify({'success': False, 'message': 'Cart is empty'}), 400
        
        # Calculate totals
        subtotal = sum(item['price'] * item['quantity'] for item in items)
        delivery_fee = 50
        total = subtotal + delivery_fee
        
        # Generate order ID
        orders_data = load_orders()
        if 'orders' not in orders_data:
            orders_data['orders'] = []
        if 'nextOrderId' not in orders_data:
            orders_data['nextOrderId'] = 1
        
        order_id = f"ORD{orders_data['nextOrderId']:04d}"
        orders_data['nextOrderId'] += 1
        save_orders(orders_data)
        
        # Priority mapping for DELIVERY
        priority_map = {'vip': 1, 'express': 2, 'regular': 3}
        priority = priority_map.get(order_type, 3)
        estimated_time = 20 if order_type == 'vip' else 25 if order_type == 'express' else 30
        
        # Create order
        new_order = {
            'orderId': order_id,
            'customerPhone': customer_phone,
            'customerName': customer_name,
            'customerEmail': session.get('user_email', ''),
            'deliveryAddress': customer_address,
            'items': items,
            'subtotal': subtotal,
            'deliveryFee': delivery_fee,
            'total': total,
            'priority': priority,
            'orderType': order_type,
            'status': 'pending',
            'kitchenStatus': 'waiting',
            'timestamp': datetime.now().isoformat(),
            'estimatedTime': estimated_time,
            'completedAt': None,
            'route': {
                'from': 'Restaurant', 
                'to': customer_address, 
                'distance': 5.0, 
                'path': ['Restaurant', customer_address]
            }
        }
        
        # ✅ ADDED: Calculate real delivery ETA and route
        eta_info = time_calculator.calculate_total_eta(new_order)
        new_order['estimatedTime'] = eta_info['total_eta_minutes']
        new_order['route'] = eta_info['route']
        
        print(f"\n{'='*60}")
        print(f"🍽️ CREATING ORDER {order_id}")
        print(f"{'='*60}")
        print(f"Customer: {customer_name} ({customer_phone})")
        print(f"Items: {len(items)}")
        print(f"Total: Rs. {total}")
        print(f"Delivery Priority: {order_type} ({priority})")
        print(f"📍 Route: {eta_info.get('route', {}).get('from', 'Restaurant')} → {eta_info.get('route', {}).get('to', customer_address)}")
        print(f"⏱️ Total ETA: {eta_info['total_eta_minutes']} mins")
        
        # ✅ DUAL PIPELINE: Add to BOTH queues
        
        # 1. Add to KITCHEN QUEUE (FIFO - cooking order)
        kitchen_queue.enqueue(new_order.copy())
        queue_position = kitchen_queue.get_queue_position(order_id)
        print(f"👨‍🍳 Added to kitchen queue (Position: {queue_position})")
        
        # 2. Add to DELIVERY QUEUE (Priority - delivery optimization)
        order_queue.add_order(new_order.copy())
        print(f"🚚 Added to delivery priority queue")
        
        # Sync both queues to file
        sync_kitchen_to_file()
        sync_queue_to_file()
        
        print(f"✅ Order {order_id} saved to orders.json")
        
        # Update customer
        customer = customer_hash_table.get_customer_by_phone(customer_phone)
        
        if customer:
            new_loyalty_points = customer.get('loyaltyPoints', 0) + int(total / 10)
            
            customer_hash_table.update_customer(customer_phone, {
                'orderHistory': customer.get('orderHistory', []) + [order_id],
                'totalOrders': customer.get('totalOrders', 0) + 1,
                'totalSpent': customer.get('totalSpent', 0) + total,
                'loyaltyPoints': new_loyalty_points,
                'address': customer_address if customer_address else customer.get('address', '')
            })
            
            print(f"✅ Updated customer {customer_phone}")
        else:
            new_customer = {
                'phone': customer_phone,
                'name': customer_name,
                'email': session.get('user_email', ''),
                'address': customer_address,
                'orderHistory': [order_id],
                'loyaltyPoints': int(total / 10),
                'preferences': [],
                'isVIP': False,
                'registeredAt': datetime.now().isoformat(),
                'totalOrders': 1,
                'totalSpent': total
            }
            customer_hash_table.insert_customer(new_customer)
            print(f"✅ Created new customer {customer_phone}")
        
        sync_customers_to_file()
        
        # Clear cart
        carts_data['carts'][cart_key]['items'] = []
        save_carts(carts_data)
        clear_stack_on_checkout()
        print(f"{'='*60}\n")
        
        return jsonify({
            'success': True, 
            'message': 'Order placed successfully!', 
            'orderId': order_id, 
            'order': new_order,
            'kitchenPosition': queue_position,
            'deliveryQueuePosition': len(order_queue.pending_queue),
            'loyaltyPointsEarned': int(total / 10),
            'estimatedDeliveryTime': eta_info['total_eta_minutes']  # ✅ ADDED
        }), 201
        
    except Exception as e:
        print(f"\n{'='*60}")
        print(f"❌ ORDER PLACEMENT ERROR")
        print(f"{'='*60}")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        print(f"{'='*60}\n")
        
        return jsonify({'success': False, 'message': 'Failed to place order'}), 500


@main.route('/api/orders/<order_id>/complete-delivery', methods=['POST'])
@admin_required
def complete_delivery(order_id):
    """
    ✅ Mark order as DELIVERED (final step)
    """
    try:
        orders_data = load_orders()
        orders = orders_data.get('orders', [])
        
        order = None
        for o in orders:
            if o['orderId'] == order_id:
                order = o
                break
        
        if not order:
            return jsonify({'success': False, 'message': 'Order not found'}), 404
        
        # Allow completion from out_for_delivery OR processing
        if order.get('status') not in ['out_for_delivery', 'processing']:
            return jsonify({
                'success': False,
                'message': f'Cannot complete order with status: {order.get("status")}'
            }), 400
        
        # Must be cooked first
        if order.get('kitchenStatus') != 'completed':
            return jsonify({
                'success': False,
                'message': 'Order must be cooked first!'
            }), 400
        
        # Mark as delivered
        order['status'] = 'delivered'
        order['deliveredAt'] = datetime.now().isoformat()
        order['deliveredBy'] = session.get('user_email', 'admin@dinex.com')
        
        save_orders(orders_data)
        
        # ✅ Update priority queue
        order_queue.complete_order(order_id)
        sync_queue_to_file()
        
        return jsonify({
            'success': True,
            'message': f'Order {order_id} marked as delivered',
            'order': order
        }), 200
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({'success': False, 'message': 'Failed'}), 500
    
@main.route('/api/cart/undo', methods=['POST'])
@login_required
def undo_cart_delete():
    """
    ✅ UPDATED: Now handles quantity changes too
    """
    try:
        cart_key = get_cart_key()
        carts_data = load_carts()
        
        if 'carts' not in carts_data or cart_key not in carts_data['carts']:
            return jsonify({
                'success': False,
                'message': 'Cart not found'
            }), 404
        
        cart = carts_data['carts'][cart_key].get('items', [])
        
        print(f"\n↩️ UNDO requested")
        print(f"   Current cart size: {len(cart)}")
        
        # ✅ Use enhanced handle_undo
        from app.cart_undo_redo_stack import handle_undo
        result = handle_undo(cart)
        
        if not result['success']:
            print(f"   ⚠️ {result['message']}")
            return jsonify(result), 400
        
        # Save updated cart
        carts_data['carts'][cart_key]['items'] = result['cart']
        carts_data['carts'][cart_key]['lastUpdated'] = datetime.now().isoformat()
        
        save_carts(carts_data)
        
        # Determine what was undone
        if 'restored_item' in result:
            print(f"   ✅ Item restored: {result['restored_item']}")
        elif 'reverted_quantity' in result:
            print(f"   ✅ Quantity reverted to: {result['reverted_quantity']}")
        
        print(f"   New cart size: {len(result['cart'])}")
        print(f"   Stack status: {result['stack_status']}")
        
        return jsonify(result), 200
        
    except Exception as e:
        print(f"❌ Undo error: {e}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            'success': False,
            'message': 'Failed to undo',
            'error': str(e)
        }), 500

# ===========================
# ENDPOINT 2: REDO
# ===========================
@main.route('/api/cart/redo', methods=['POST'])
@login_required
def redo_cart_delete():
    """
    ✅ UPDATED: Now handles quantity changes too
    """
    try:
        cart_key = get_cart_key()
        carts_data = load_carts()
        
        if 'carts' not in carts_data or cart_key not in carts_data['carts']:
            return jsonify({
                'success': False,
                'message': 'Cart not found'
            }), 404
        
        cart = carts_data['carts'][cart_key].get('items', [])
        
        print(f"\n↪️ REDO requested")
        print(f"   Current cart size: {len(cart)}")
        
        # ✅ Use enhanced handle_redo
        from app.cart_undo_redo_stack import handle_redo
        result = handle_redo(cart)
        
        if not result['success']:
            print(f"   ⚠️ {result['message']}")
            return jsonify(result), 400
        
        # Save updated cart
        carts_data['carts'][cart_key]['items'] = result['cart']
        carts_data['carts'][cart_key]['lastUpdated'] = datetime.now().isoformat()
        
        save_carts(carts_data)
        
        # Determine what was redone
        if 'deleted_item' in result:
            print(f"   ✅ Item removed again: {result['deleted_item']}")
        elif 'new_quantity' in result:
            print(f"   ✅ Quantity changed to: {result['new_quantity']}")
        
        print(f"   New cart size: {len(result['cart'])}")
        print(f"   Stack status: {result['stack_status']}")
        
        return jsonify(result), 200
        
    except Exception as e:
        print(f"❌ Redo error: {e}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            'success': False,
            'message': 'Failed to redo',
            'error': str(e)
        }), 500

# ===========================
# ENDPOINT 3: STACK STATUS
# ===========================
@main.route('/api/cart/stack-status', methods=['GET'])
@login_required
def get_stack_status():
    """
    Get current undo/redo stack status
    (Keep existing - already correct)
    """
    try:
        from app.cart_undo_redo_stack import cart_stack
        status = cart_stack.get_stack_status()
        
        return jsonify({
            'success': True,
            'stack_status': status
        }), 200
        
    except Exception as e:
        print(f"❌ Stack status error: {e}")
        
        return jsonify({
            'success': False,
            'message': 'Failed to get stack status',
            'error': str(e)
        }), 500


# =============================================================================
# NEW KITCHEN QUEUE API ROUTES
# Add these routes to your routes.py
# =============================================================================

@main.route('/api/kitchen/next', methods=['POST'])
@kitchen_required
def start_cooking_next():
    """
    Start cooking next order in FIFO queue
    Kitchen staff clicks "Start Cooking" button
    """
    try:
        order = kitchen_queue.dequeue()
        
        if order:
            sync_kitchen_to_file()
            
            return jsonify({
                'success': True,
                'message': f"Started cooking {order['orderId']}",
                'order': order
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'No orders waiting in kitchen queue'
            }), 404
            
    except Exception as e:
        print(f"Kitchen start error: {e}")
        return jsonify({'success': False, 'message': 'Failed to start cooking'}), 500


def debug_order_status(order_id):
    """Debug helper - prints order status"""
    orders_data = load_orders()
    orders = orders_data.get('orders', [])
    
    for o in orders:
        if o['orderId'] == order_id:
            print(f"\n{'='*60}")
            print(f"🔍 DEBUG ORDER {order_id}")
            print(f"{'='*60}")
            print(f"Status: {o.get('status')}")
            print(f"Kitchen Status: {o.get('kitchenStatus')}")
            print(f"Assigned At: {o.get('assignedAt', 'Not assigned')}")
            print(f"{'='*60}\n")
            return
    
    print(f"❌ Order {order_id} not found")

@main.route('/api/kitchen/complete/<order_id>', methods=['POST'])
@kitchen_required
def complete_cooking(order_id):
    """
    ✅ FIXED: When kitchen finishes cooking, set correct status
    
    CRITICAL FLOW:
    1. Kitchen marks as completed (kitchenStatus = 'completed')
    2. Set status to 'processing' (ready for admin to assign)
    3. Order should appear in admin dashboard
    """
    try:
        print(f"\n{'='*60}")
        print(f"🍳 COMPLETING COOKING FOR {order_id}")
        print(f"{'='*60}")
        
        # Complete in kitchen queue
        order = kitchen_queue.complete_cooking(order_id)
        
        if not order:
            print(f"❌ Order {order_id} not found in cooking")
            return jsonify({'success': False, 'message': 'Order not in cooking'}), 404
        
        print(f"✅ Kitchen queue updated")
        print(f"   Order: {order['orderId']}")
        print(f"   Customer: {order['customerName']}")
        
        # ✅ UPDATE: Load fresh orders from file
        orders_data = load_orders()
        orders = orders_data.get('orders', [])
        
        print(f"\n📂 Loading orders.json")
        print(f"   Total orders: {len(orders)}")
        
        # Find and update the order
        order_found = False
        for o in orders:
            if o['orderId'] == order_id:
                order_found = True
                
                print(f"\n🔍 BEFORE UPDATE:")
                print(f"   status: {o.get('status')}")
                print(f"   kitchenStatus: {o.get('kitchenStatus')}")
                
                # ✅ SET CORRECT STATUS
                o['status'] = 'processing'  # ← ADMIN LOOKS FOR THIS!
                o['kitchenStatus'] = 'completed'  # ← KITCHEN DONE!
                o['cookingCompletedAt'] = datetime.now().isoformat()
                
                print(f"\n✅ AFTER UPDATE:")
                print(f"   status: {o['status']}")
                print(f"   kitchenStatus: {o['kitchenStatus']}")
                print(f"   completedAt: {o['cookingCompletedAt']}")
                
                break
        
        if not order_found:
            print(f"❌ Order {order_id} NOT FOUND in orders.json!")
            return jsonify({'success': False, 'message': 'Order not found in file'}), 404
        
        # Save to file
        save_orders(orders_data)
        print(f"\n💾 Saved to orders.json")
        
        # Sync kitchen queue
        sync_kitchen_to_file()
        print(f"✅ Kitchen queue synced")
        
        print(f"\n{'='*60}")
        print(f"✅ ORDER {order_id} READY FOR DELIVERY")
        print(f"   Admin should see this in Priority Queue!")
        print(f"{'='*60}\n")
        
        return jsonify({
            'success': True,
            'message': f'Cooking completed for {order_id}',
            'order': order,
            'debug': {
                'status': 'processing',
                'kitchenStatus': 'completed',
                'orderId': order_id
            }
        }), 200
        
    except Exception as e:
        print(f"\n{'='*60}")
        print(f"❌ KITCHEN COMPLETE ERROR")
        print(f"{'='*60}")
        print(f"Order: {order_id}")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        print(f"{'='*60}\n")
        
        return jsonify({'success': False, 'message': 'Failed to complete cooking'}), 500


@main.route('/api/orders/queue/assign-next', methods=['POST'])
@admin_required
def assign_next_priority_order():
    """
    ✅ NEW: Assign HIGHEST PRIORITY order to rider
    
    This is the KEY function that uses your priority queue!
    
    LOGIC:
    1. Get next order from priority queue (VIP → Express → Regular)
    2. Assign to rider (status: processing → out_for_delivery)
    3. Order is now in delivery pipeline
    """
    try:
        # ✅ Get all orders that are ready for delivery (cooked + processing)
        orders_data = load_orders()
        orders = orders_data.get('orders', [])
        
        # Find orders that are cooked and ready
        ready_orders = [
            o for o in orders 
            if o.get('status') == 'processing' and 
               o.get('kitchenStatus') == 'completed'
        ]
        
        if not ready_orders:
            return jsonify({
                'success': False,
                'message': 'No orders ready for delivery'
            }), 404
        
        # ✅ Sort by priority (VIP=1, Express=2, Regular=3)
        # Then by timestamp (earlier first)
        ready_orders.sort(key=lambda x: (x['priority'], x['timestamp']))
        
        # Get highest priority order
        next_order = ready_orders[0]
        
        # Assign to rider
        for o in orders:
            if o['orderId'] == next_order['orderId']:
                o['status'] = 'out_for_delivery'
                o['assignedAt'] = datetime.now().isoformat()
                break
        
        save_orders(orders_data)
        
        priority_label = next_order['orderType'].upper()
        
        return jsonify({
            'success': True,
            'message': f'{priority_label} order {next_order["orderId"]} assigned to rider',
            'order': next_order,
            'priorityInfo': {
                'orderType': next_order['orderType'],
                'priority': next_order['priority'],
                'customername': next_order['customerName']
            }
        }), 200
        
    except Exception as e:
        print(f"❌ Assign priority order error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': 'Failed to assign order'}), 500

@main.route('/api/orders/queue/ready', methods=['GET'])
def get_ready_for_delivery():
    """
    ✅ FIXED: Get all orders ready for delivery with detailed logging
    """
    try:
        print(f"\n{'='*60}")
        print(f"📊 ADMIN CHECKING READY ORDERS")
        print(f"{'='*60}")
        
        # Load fresh data from file
        orders_data = load_orders()
        orders = orders_data.get('orders', [])
        
        print(f"Total orders in file: {len(orders)}")
        
        # Get ready orders
        ready_orders = []
        
        print(f"\n🔍 Scanning orders:")
        for o in orders:
            order_id = o.get('orderId')
            status = o.get('status', 'unknown')
            kitchen_status = o.get('kitchenStatus', 'unknown')
            
            print(f"  {order_id}: status={status}, kitchen={kitchen_status}")
            
            # ✅ LOGIC: Ready if cooked + processing
            if kitchen_status == 'completed' and status == 'processing':
                ready_orders.append(o)
                print(f"    ✅ READY FOR DELIVERY!")
            elif kitchen_status == 'completed':
                print(f"    ⚠️  Cooked but status is '{status}' (not 'processing')")
            elif status == 'processing':
                print(f"    ⚠️  Processing but kitchen is '{kitchen_status}' (not 'completed')")
        
        print(f"\n📦 Ready orders count: {len(ready_orders)}")
        
        if ready_orders:
            print(f"Ready order IDs: {[o['orderId'] for o in ready_orders]}")
        else:
            print(f"⚠️  NO ORDERS READY!")
            print(f"\nPossible reasons:")
            print(f"  1. Kitchen hasn't finished cooking (kitchenStatus != 'completed')")
            print(f"  2. Order already assigned (status != 'processing')")
            print(f"  3. Order status is 'out_for_delivery' or 'delivered'")
        
        print(f"{'='*60}\n")
        
        # Sort by priority
        ready_orders.sort(key=lambda x: (x['priority'], x['timestamp']))
        
        # Count by priority
        vip_count = sum(1 for o in ready_orders if o['priority'] == 1)
        express_count = sum(1 for o in ready_orders if o['priority'] == 2)
        regular_count = sum(1 for o in ready_orders if o['priority'] == 3)
        
        return jsonify({
            'success': True,
            'readyOrders': ready_orders,
            'count': len(ready_orders),
            'priorityBreakdown': {
                'vip': vip_count,
                'express': express_count,
                'regular': regular_count
            },
            'nextOrder': ready_orders[0] if ready_orders else None
        }), 200
        
    except Exception as e:
        print(f"❌ Get ready orders error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': 'Failed to load orders'}), 500

# just for debug
@main.route('/api/orders/debug/<order_id>', methods=['GET'])
def debug_order_status(order_id):
    """
    🔍 DEBUG: Check the exact status of an order
    Use this to see why an order isn't showing up
    """
    try:
        orders_data = load_orders()
        orders = orders_data.get('orders', [])
        
        order = None
        for o in orders:
            if o['orderId'] == order_id:
                order = o
                break
        
        if not order:
            return jsonify({
                'success': False,
                'message': f'Order {order_id} not found'
            }), 404
        
        # Check status
        status = order.get('status', 'unknown')
        kitchen_status = order.get('kitchenStatus', 'unknown')
        
        # Determine where order should appear
        location = "UNKNOWN"
        if kitchen_status == 'waiting':
            location = "Kitchen: Waiting Queue"
        elif kitchen_status == 'cooking':
            location = "Kitchen: Currently Cooking"
        elif kitchen_status == 'completed' and status == 'processing':
            location = "Admin: Ready for Delivery (Priority Queue) ✅"
        elif status == 'out_for_delivery':
            location = "Rider: Out for Delivery"
        elif status == 'delivered':
            location = "Admin: Delivered"
        
        return jsonify({
            'success': True,
            'orderId': order_id,
            'status': status,
            'kitchenStatus': kitchen_status,
            'location': location,
            'isReadyForDelivery': kitchen_status == 'completed' and status == 'processing',
            'fullOrder': order
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@main.route('/api/orders/delivery/stats', methods=['GET'])
def get_delivery_stats():
    """
    ✅ NEW: Get complete delivery pipeline statistics
    
    Returns counts for:
    - Ready for delivery (cooked + processing)
    - Out for delivery (assigned to rider)
    - Delivered (completed)
    """
    try:
        orders_data = load_orders()
        orders = orders_data.get('orders', [])
        
        # Count orders in each stage
        ready_count = 0
        out_for_delivery_count = 0
        delivered_count = 0
        
        ready_orders = []
        out_for_delivery_orders = []
        delivered_orders = []
        
        for o in orders:
            status = o.get('status', '')
            kitchen_status = o.get('kitchenStatus', '')
            
            # Ready for delivery
            if kitchen_status == 'completed' and status == 'processing':
                ready_count += 1
                ready_orders.append(o)
            
            # Out for delivery
            elif status == 'out_for_delivery':
                out_for_delivery_count += 1
                out_for_delivery_orders.append(o)
            
            # Delivered
            elif status == 'delivered':
                delivered_count += 1
                delivered_orders.append(o)
        
        # Sort ready orders by priority
        ready_orders.sort(key=lambda x: (x['priority'], x['timestamp']))
        
        # Sort delivered by most recent
        delivered_orders.sort(key=lambda x: x.get('deliveredAt', ''), reverse=True)
        
        return jsonify({
            'success': True,
            'stats': {
                'ready': ready_count,
                'outForDelivery': out_for_delivery_count,
                'delivered': delivered_count
            },
            'orders': {
                'ready': ready_orders,
                'outForDelivery': out_for_delivery_orders,
                'delivered': delivered_orders[:20]  # Last 20 delivered
            }
        }), 200
        
    except Exception as e:
        print(f"❌ Delivery stats error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': 'Failed to load stats'}), 500

@main.route('/api/kitchen/stats', methods=['GET'])
@kitchen_required
def get_kitchen_stats():
    """
    Get kitchen queue statistics
    """
    try:
        stats = kitchen_queue.get_statistics()
        
        # Get all orders for detailed view
        waiting = kitchen_queue.get_all_waiting()
        cooking = kitchen_queue.get_cooking_orders()
        completed = kitchen_queue.get_completed_orders()
        
        return jsonify({
            'success': True,
            'stats': stats,
            'orders': {
                'waiting': waiting,
                'cooking': cooking,
                'completed': completed
            }
        }), 200
        
    except Exception as e:
        print(f"Kitchen stats error: {e}")
        return jsonify({'success': False, 'message': 'Failed to get stats'}), 500


@main.route('/api/kitchen/order/<order_id>', methods=['GET'])
def get_kitchen_order_status(order_id):
    """
    Get order status in kitchen pipeline
    Can be called by customers to check cooking status
    """
    try:
        result = kitchen_queue.find_order(order_id)
        
        if result:
            queue_position = None
            if result['stage'] == 'waiting':
                queue_position = kitchen_queue.get_queue_position(order_id)
            
            return jsonify({
                'success': True,
                'orderId': order_id,
                'kitchenStatus': result['stage'],
                'queuePosition': queue_position,
                'order': result['order']
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Order not found in kitchen'
            }), 404
            
    except Exception as e:
        print(f"Kitchen order lookup error: {e}")
        return jsonify({'success': False, 'message': 'Failed to get order status'}), 500

# Rider Dashboard route
@main.route('/rider')
@rider_required
def rider_dashboard():
    """Rider dashboard for delivery management"""
    user_email = session.get('user_email')
    
    if user_email in HARDCODED_ADMINS:
        user = HARDCODED_ADMINS[user_email]
    else:
        user = find_user_by_email_or_phone(user_email)
    
    return render_template('rider.html', user=user)


# 4. ADD RIDER API ENDPOINTS

@main.route('/api/orders/rider', methods=['GET'])
@rider_required
def get_rider_orders():
    """
    Get all orders ready for delivery
    """
    try:
        orders_data = load_orders()
        orders = orders_data.get('orders', [])
        
        # ✅ Filter orders that are ready for delivery
        out_for_delivery = []
        completed_ready = []
        
        for o in orders:
            # Check if order is explicitly out_for_delivery
            if o.get('status') == 'out_for_delivery':
                out_for_delivery.append(o)
            # OR if kitchen is done but status not updated yet
            elif o.get('status') == 'completed' and o.get('kitchenStatus') == 'completed':
                # Auto-assign to rider
                o['status'] = 'out_for_delivery'
                o['assignedAt'] = datetime.now().isoformat()
                completed_ready.append(o)
        
        # Combine both lists
        out_for_delivery.extend(completed_ready)
        
        # Get delivered orders
        delivered = [o for o in orders if o.get('status') == 'delivered']
        
        # Save if we auto-assigned any orders
        if completed_ready:
            save_orders(orders_data)
            print(f"✅ Auto-assigned {len(completed_ready)} completed orders to rider")
        
        return jsonify({
            'success': True,
            'outForDelivery': out_for_delivery,
            'delivered': delivered,
            'stats': {
                'outForDelivery': len(out_for_delivery),
                'delivered': len(delivered),
                'total': len(out_for_delivery) + len(delivered)
            }
        }), 200
        
    except Exception as e:
        print(f"❌ Rider orders error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': 'Failed to load orders'}), 500


@main.route('/api/orders/<order_id>/deliver', methods=['PUT'])
@rider_required
def mark_as_delivered(order_id):
    """
    Mark order as delivered by rider
    Status: 'out_for_delivery' → 'delivered'
    
    ✅ NEW: Also adds order to customer's linked list history
    """
    try:
        orders_data = load_orders()
        orders = orders_data.get('orders', [])
        
        # Find the order
        order = None
        for o in orders:
            if o['orderId'] == order_id:
                order = o
                break
        
        if not order:
            return jsonify({'success': False, 'message': 'Order not found'}), 404
        
        # Validate current status
        if order.get('status') != 'out_for_delivery':
            return jsonify({
                'success': False, 
                'message': f'Cannot deliver order with status: {order.get("status")}'
            }), 400
        
        # Update order status
        order['status'] = 'delivered'
        order['deliveredAt'] = datetime.now().isoformat()
        order['deliveredBy'] = session.get('user_email', 'rider@dinex.com')
        
        # Save orders
        save_orders(orders_data)
        
        # ✅ NEW: Add to customer's order history linked list
        history_manager.add_order(order.copy())
        print(f"✅ Order {order_id} added to customer history linked list")
        
        return jsonify({
            'success': True,
            'message': 'Order delivered successfully',
            'order': order
        }), 200
        
    except Exception as e:
        print(f"❌ Deliver error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': 'Failed to mark as delivered'}), 500
    

@main.route('/api/orders/<order_id>/complete-cooking', methods=['POST'])
@admin_required
def complete_cooking_and_assign(order_id):
    """
    Complete cooking and auto-assign to rider
    Admin marks order as ready → automatically goes to rider queue
    """
    try:
        # Complete in kitchen queue
        order = kitchen_queue.complete_cooking(order_id)
        
        if not order:
            return jsonify({'success': False, 'message': 'Order not in cooking'}), 404
        
        # Update status in orders.json
        orders_data = load_orders()
        orders = orders_data.get('orders', [])
        
        for o in orders:
            if o['orderId'] == order_id:
                o['status'] = 'out_for_delivery'  # Auto-assign to rider
                o['assignedAt'] = datetime.now().isoformat()
                break
        
        save_orders(orders_data)
        sync_kitchen_to_file()
        
        return jsonify({
            'success': True,
            'message': f'Order {order_id} completed and assigned to rider',
            'order': order
        }), 200
        
    except Exception as e:
        print(f"❌ Complete and assign error: {e}")
        return jsonify({'success': False, 'message': 'Failed to complete order'}), 500


@main.route('/api/orders/rider/stats', methods=['GET'])
@rider_required
def get_rider_stats():
    """
    Get rider delivery statistics
    """
    try:
        orders_data = load_orders()
        orders = orders_data.get('orders', [])
        
        out_for_delivery = [o for o in orders if o.get('status') == 'out_for_delivery']
        delivered_today = [
            o for o in orders 
            if o.get('status') == 'delivered' and 
            o.get('deliveredAt', '').startswith(datetime.now().strftime('%Y-%m-%d'))
        ]
        
        total_delivered = [o for o in orders if o.get('status') == 'delivered']
        
        return jsonify({
            'success': True,
            'stats': {
                'outForDelivery': len(out_for_delivery),
                'deliveredToday': len(delivered_today),
                'totalDelivered': len(total_delivered),
                'total': len(out_for_delivery) + len(total_delivered)
            }
        }), 200
        
    except Exception as e:
        print(f"❌ Rider stats error: {e}")
        return jsonify({'success': False, 'message': 'Failed to get stats'}), 500


# ===========================
# NEW ROUTES: CUSTOMER ANALYTICS WITH HASH TABLE
# ===========================

@main.route('/api/customer/stats', methods=['GET'])
def get_customer_stats():
    """
    Get customer statistics from hash table.
    Fast analytics without scanning entire JSON file.
    """
    try:
        stats = customer_hash_table.get_statistics()
        all_customers = customer_hash_table.get_all_customers()
        
        # Calculate aggregate metrics
        total_loyalty_points = sum(c.get('loyaltyPoints', 0) for c in all_customers)
        total_orders = sum(c.get('totalOrders', 0) for c in all_customers)
        total_revenue = sum(c.get('totalSpent', 0) for c in all_customers)
        vip_count = sum(1 for c in all_customers if c.get('isVIP', False))
        
        # Top customers by loyalty points
        top_customers = sorted(
            all_customers, 
            key=lambda c: c.get('loyaltyPoints', 0), 
            reverse=True
        )[:10]
        
        return jsonify({
            'success': True,
            'hashTableStats': stats,
            'customerMetrics': {
                'totalCustomers': len(customer_hash_table),
                'totalLoyaltyPoints': total_loyalty_points,
                'totalOrders': total_orders,
                'totalRevenue': total_revenue,
                'vipCustomers': vip_count,
                'averageOrderValue': total_revenue / total_orders if total_orders > 0 else 0
            },
            'topCustomers': [
                {
                    'phone': c['phone'],
                    'name': c['name'],
                    'loyaltyPoints': c.get('loyaltyPoints', 0),
                    'totalOrders': c.get('totalOrders', 0),
                    'totalSpent': c.get('totalSpent', 0)
                }
                for c in top_customers
            ]
        }), 200
    except Exception as e:
        print(f"Customer stats error: {e}")
        return jsonify({'success': False, 'message': 'Failed to get stats'}), 500

@main.route('/api/customer/search', methods=['GET'])
def search_customers():
    """
    Search customers by name or phone.
    Uses hash table for phone lookup, linear search for name.
    """
    try:
        query = request.args.get('q', '').strip().lower()
        search_type = request.args.get('type', 'all')  # 'phone' or 'name' or 'all'
        
        if not query:
            return jsonify({'success': False, 'message': 'Search query required'}), 400
        
        results = []
        
        # If searching by phone, use O(1) hash table lookup
        if search_type in ['phone', 'all']:
            customer = customer_hash_table.get_customer_by_phone(query)
            if customer:
                results.append(customer)
        
        # If searching by name, scan all customers (unavoidable O(n))
        if search_type in ['name', 'all'] and not results:
            all_customers = customer_hash_table.get_all_customers()
            results = [
                c for c in all_customers 
                if query in c.get('name', '').lower()
            ]
        
        return jsonify({
            'success': True,
            'results': results,
            'count': len(results)
        }), 200
    except Exception as e:
        print(f"Customer search error: {e}")
        return jsonify({'success': False, 'message': 'Search failed'}), 500



# ===========================
# ADD THIS TO THE END OF YOUR routes.py
# (After the place_order function)
# ===========================

@main.route('/api/orders/<order_id>', methods=['GET'])
def get_order(order_id):
    try:
        order = order_queue.get_order_status(order_id)
        
        if order:
            return jsonify({'success': True, 'order': order}), 200
        else:
            return jsonify({'success': False, 'message': 'Order not found'}), 404
    except Exception as e:
        print(f"Order lookup error: {e}")
        return jsonify({'success': False, 'message': 'Failed to find order'}), 500

@main.route('/api/orders/history/<phone>', methods=['GET'])
def get_order_history(phone):
    try:
        orders_data = load_orders()
        orders = orders_data.get('orders', [])
        customer_orders = [o for o in orders if o['customerPhone'] == phone]
        
        return jsonify({'success': True, 'orders': customer_orders}), 200
    except Exception as e:
        print(f"Order history error: {e}")
        return jsonify({'success': False, 'message': 'Failed to load order history'}), 500

@main.route('/api/orders/<order_id>/status', methods=['PUT'])
def update_order_status(order_id):
    try:
        data = request.get_json()
        new_status = data.get('status')
        if not new_status:
            return jsonify({'success': False, 'message': 'Status is required'}), 400
        
        # Update in priority queue
        if new_status == 'processing':
            order = order_queue.process_next_order()
        elif new_status in ['completed', 'delivered']:
            order = order_queue.complete_order(order_id)
        else:
            # For other statuses, just update in queue
            order_queue.pending_queue.update_order_status(order_id, new_status)
            order = order_queue.get_order_status(order_id)
        
        # Sync to file
        sync_queue_to_file()
        
        return jsonify({'success': True, 'message': 'Order status updated', 'order': order}), 200
    except Exception as e:
        print(f"Status update error: {e}")
        return jsonify({'success': False, 'message': 'Failed to update status'}), 500

# ===========================
# PRIORITY QUEUE ADMIN ROUTES (Protected)
# ===========================

@main.route('/api/orders/queue/next', methods=['POST'])
@admin_required
def process_next_order():
    """Process next highest priority order"""
    try:
        order = order_queue.process_next_order()
        if order:
            sync_queue_to_file()
            return jsonify({
                'success': True, 
                'message': 'Order moved to processing',
                'order': order
            }), 200
        else:
            return jsonify({'success': False, 'message': 'No pending orders'}), 404
    except Exception as e:
        print(f"Process order error: {e}")
        return jsonify({'success': False, 'message': 'Failed to process order'}), 500

@main.route('/api/orders/queue/stats', methods=['GET'])
@admin_required
def get_queue_stats():
    """Get queue statistics"""
    try:
        stats = order_queue.get_queue_statistics()
        
        # Add priority breakdown
        pending = order_queue.get_all_pending_orders()
        priority_count = {'vip': 0, 'express': 0, 'regular': 0}
        for order in pending:
            order_type = order.get('orderType', 'regular')
            priority_count[order_type] = priority_count.get(order_type, 0) + 1
        
        return jsonify({
            'success': True,
            'stats': stats,
            'priorityBreakdown': priority_count,
            'nextOrder': order_queue.pending_queue.peek()
        }), 200
    except Exception as e:
        print(f"Queue stats error: {e}")
        return jsonify({'success': False, 'message': 'Failed to get stats'}), 500

@main.route('/api/orders/queue/all', methods=['GET'])
@admin_required
def get_all_queue_orders():
    """Get all orders from queue sorted by priority"""
    try:
        pending = order_queue.get_all_pending_orders()
        processing = order_queue.get_processing_orders()
        completed = order_queue.get_completed_orders()
        
        return jsonify({
            'success': True,
            'pending': pending,
            'processing': processing,
            'completed': completed
        }), 200
    except Exception as e:
        print(f"Get queue orders error: {e}")
        return jsonify({'success': False, 'message': 'Failed to get orders'}), 500

@main.route('/admin')
@admin_required
def admin_dashboard():
    """Admin dashboard for managing order queue"""
    user_email = session.get('user_email')
    
    # Get user info (check hardcoded admins first)
    if user_email in HARDCODED_ADMINS:
        user = HARDCODED_ADMINS[user_email]
    else:
        user = find_user_by_email_or_phone(user_email)
    
    return render_template('admin.html', user=user)

@main.route('/error')
def error_page():
    """Error page template"""
    return render_template('error.html', 
                         message='An error occurred',
                         error_code=500)

# ===========================
# INITIALIZE ON FIRST REQUEST
# ===========================

@main.before_app_request
def initialize_app():
    if not hasattr(initialize_app, 'initialized'):
        initialize_app.initialized = True
        
        print("\n" + "="*60)
        print("INITIALIZING DINEX APPLICATION")
        print("="*60)
        
        # Load delivery orders (priority queue)
        load_orders_into_queue()
        print(f"✅ Delivery queue loaded")
        
        # Load kitchen orders (FIFO queue)
        load_orders_into_kitchen()
        print(f"✅ Kitchen queue loaded")
        
        # Load menu
        load_menu_into_trees()
        
        # Load customers
        load_customers_into_hash_table()
        customer_stats = customer_hash_table.get_statistics()
        print(f"✅ Customers loaded into hash table")
        print(f"   Total: {customer_stats['total_customers']}")
        print(f"   Load Factor: {customer_stats['load_factor']:.2f}")
        
        # ✅ NEW: Load order history
        load_orders_into_history()
        print(f"✅ Customer order history loaded into linked lists")
        print(f"   Tracking: {len(history_manager)} customers")
        
        print("="*60 + "\n")

@main.route('/kitchen')
@kitchen_required
def kitchen_dashboard():
    """Kitchen dashboard for FIFO queue management"""
    user_email = session.get('user_email')
    
    if user_email in HARDCODED_ADMINS:
        user = HARDCODED_ADMINS[user_email]
    else:
        user = find_user_by_email_or_phone(user_email)
    
    return render_template('kitchen.html', user=user)  # ← kitchen.html (different!)

# ===========================
# ADD THIS NEW ROUTE IN routes.py
# Put it after your existing /api/menu route
# ===========================

@main.route('/api/menu/filter', methods=['GET'])
def filter_menu():
    """
    ✅ NEW ROUTE: Filter menu by category and price using BST
    
    Query Parameters:
    - category: 'all', 'main', 'beverage', 'dessert', 'appetizer'
    - max_price: Maximum price filter
    - sort: 'name', 'price-low', 'price-high', 'popular'
    
    Example: /api/menu/filter?category=main&max_price=400
    """
    try:
        # Get query parameters
        category = request.args.get('category', 'all').lower()
        max_price = request.args.get('max_price', type=float)
        sort_by = request.args.get('sort', 'name')
        
        print(f"🔍 Filter request:")
        print(f"   Category: {category}")
        print(f"   Max Price: {max_price}")
        print(f"   Sort: {sort_by}")
        
        # Use BST manager for filtering
        if max_price:
            # Filter by category AND price range
            items = bst_manager.search_by_category_and_price(
                category=category,
                min_price=0,
                max_price=max_price
            )
            print(f"✅ BST price filter: Found {len(items)} items")
        else:
            # Just filter by category
            items = bst_manager.get_category_items(
                category=category,
                sort_by='price'  # BST sorts by price by default
            )
            print(f"✅ BST category filter: Found {len(items)} items")
        
        # Apply additional sorting if needed
        if sort_by == 'name':
            items.sort(key=lambda x: x['name'])
        elif sort_by == 'price-high':
            items.sort(key=lambda x: x['price'], reverse=True)
        elif sort_by == 'popular':
            items.sort(key=lambda x: x.get('rating', 0), reverse=True)
        # 'price-low' is default from BST
        
        return jsonify({
            'success': True,
            'items': items,
            'count': len(items),
            'category': category,
            'max_price': max_price
        }), 200
        
    except Exception as e:
        print(f"❌ Filter error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': 'Failed to filter menu',
            'error': str(e)
        }), 500
    
# ===========================
# CUSTOMER HISTORY API ROUTES
# ===========================

@main.route('/api/customer/<phone>/order-history', methods=['GET'])
def get_customer_order_history(phone):
    """
    Get customer's order history from linked list.
    
    Query Params:
    - limit: Number of recent orders (optional)
    
    Example: /api/customer/03704018969/order-history?limit=5
    """
    try:
        limit = request.args.get('limit', type=int)
        
        # Get orders from linked list (O(1) lookup + O(n) traversal)
        orders = history_manager.get_order_history(phone, limit)
        
        return jsonify({
            'success': True,
            'customerPhone': phone,
            'orderCount': len(orders),
            'orders': orders
        }), 200
    except Exception as e:
        print(f"Order history error: {e}")
        return jsonify({'success': False, 'message': 'Failed to load order history'}), 500


@main.route('/api/customer/<phone>/stats', methods=['GET'])
def get_customer_history_stats(phone):
    """
    Get customer statistics from linked list.
    
    Returns:
    - Total orders
    - Total spent
    - Recent orders
    """
    try:
        stats = history_manager.get_customer_statistics(phone)
        
        return jsonify({
            'success': True,
            'customerPhone': phone,
            'statistics': stats
        }), 200
    except Exception as e:
        print(f"Stats error: {e}")
        return jsonify({'success': False, 'message': 'Failed to get statistics'}), 500


@main.route('/api/customer/<phone>/order/<order_id>', methods=['GET'])
def search_customer_order(phone, order_id):
    """
    Search for specific order in customer's history.
    
    Time Complexity: O(n) where n = customer's orders
    """
    try:
        order = history_manager.search_order(phone, order_id)
        
        if order:
            return jsonify({
                'success': True,
                'order': order
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Order not found in customer history'
            }), 404
    except Exception as e:
        print(f"Order search error: {e}")
        return jsonify({'success': False, 'message': 'Search failed'}), 500


@main.route('/api/customer/<phone>/transaction-history', methods=['GET'])
def get_customer_transaction_history(phone):
    """
    Get customer's transaction/payment history from linked list.
    
    Query Params:
    - limit: Number of recent transactions (optional)
    """
    try:
        limit = request.args.get('limit', type=int)
        
        transactions = history_manager.get_transaction_history(phone, limit)
        
        return jsonify({
            'success': True,
            'customerPhone': phone,
            'transactionCount': len(transactions),
            'transactions': transactions
        }), 200
    except Exception as e:
        print(f"Transaction history error: {e}")
        return jsonify({'success': False, 'message': 'Failed to load transaction history'}), 500


@main.route('/api/payment/record', methods=['POST'])
@login_required
def record_payment():
    """
    ✅ NEW: Record payment transaction to customer's linked list.
    
    Request Body:
    {
        "orderId": "ORD0001",
        "customerPhone": "03704018969",
        "amount": 550,
        "paymentMethod": "card",
        "status": "completed"
    }
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        required = ['orderId', 'customerPhone', 'amount', 'paymentMethod']
        if not all(field in data for field in required):
            return jsonify({
                'success': False,
                'message': 'Missing required fields'
            }), 400
        
        # Generate transaction ID
        transaction_id = f"TXN{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Create transaction record
        transaction = {
            'transactionId': transaction_id,
            'orderId': data['orderId'],
            'customerPhone': data['customerPhone'],
            'amount': data['amount'],
            'paymentMethod': data['paymentMethod'],
            'status': data.get('status', 'completed'),
            'timestamp': datetime.now().isoformat()
        }
        
        # Add to linked list (O(1))
        history_manager.add_transaction(transaction)
        
        print(f"✅ Transaction {transaction_id} recorded for {data['customerPhone']}")
        
        return jsonify({
            'success': True,
            'message': 'Payment recorded successfully',
            'transaction': transaction
        }), 201
        
    except Exception as e:
        print(f"Payment recording error: {e}")
        return jsonify({'success': False, 'message': 'Failed to record payment'}), 500


@main.route('/api/orders/<order_id>/tracking', methods=['GET'])
def get_order_tracking(order_id):
    """
    Get complete tracking info with real coordinates
    Used by track.html
    """
    try:
        # Read fresh order state from file to avoid stale in-memory queues
        orders_data = load_orders()
        orders = orders_data.get('orders', [])

        order = None
        for o in orders:
            if o.get('orderId') == order_id:
                order = o
                break

        if not order:
            return jsonify({'success': False, 'message': 'Order not found'}), 404

        # Derive a timeline-friendly status for frontend
        # Map combinations of 'status' and 'kitchenStatus' to one of:
        # 'pending', 'processing', 'ready', 'out_for_delivery', 'completed'
        status = (order.get('status') or '').lower()
        kitchen_status = (order.get('kitchenStatus') or '').lower()

        if status == 'delivered':
            timeline_status = 'completed'
        elif status == 'out_for_delivery':
            timeline_status = 'out_for_delivery'
        elif kitchen_status == 'completed' and status in ('processing', 'pending', ''):
            # Cooked and waiting/processing → ready for delivery
            timeline_status = 'ready'
        elif kitchen_status == 'cooking' or status == 'processing':
            timeline_status = 'processing'
        else:
            timeline_status = 'pending'

        # Attach the derived timeline status to the returned order copy
        order_for_client = order.copy()
        order_for_client['timelineStatus'] = timeline_status

        # Debug log for easier frontend troubleshooting
        print(f"🔁 Tracking: order={order_id}, status={status}, kitchenStatus={kitchen_status}, timelineStatus={timeline_status}")

        # Calculate fresh ETA
        eta_info = time_calculator.calculate_total_eta(order_for_client)
        
        # Get restaurant coordinates
        restaurant_coords = {
            'lat': delivery_graph.RESTAURANT_INFO['lat'],
            'lng': delivery_graph.RESTAURANT_INFO['lng'],
            'name': delivery_graph.RESTAURANT_INFO['name'],
            'address': delivery_graph.RESTAURANT_INFO['address']
        }
        
        # Get delivery coordinates
        delivery_coords = time_calculator._extract_coordinates(order.get('deliveryAddress', ''))
        
        return jsonify({
            'success': True,
            'order': order_for_client,
            'tracking': {
                'restaurant': restaurant_coords,
                'delivery': {
                    'lat': delivery_coords.get('lat'),
                    'lng': delivery_coords.get('lng'),
                    'address': order.get('deliveryAddress')
                },
                'route': eta_info.get('route'),
                'eta': eta_info.get('total_eta_minutes'),
                'estimatedDeliveryTime': eta_info.get('estimated_delivery_time'),
                'breakdown': eta_info.get('breakdown')
            }
        }), 200
        
    except Exception as e:
        print(f"Tracking error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': 'Failed to get tracking info'}), 500
    

@main.route('/api/cart/test-stack', methods=['GET'])
@login_required
def test_stack():
    """Debug route to test stack functionality"""
    from app.cart_undo_redo_stack import cart_stack
    
    # Push a test action
    test_item = {
        'id': 999,
        'name': 'Test Item',
        'price': 100,
        'quantity': 1,
        'image': 'test.jpg'
    }
    
    cart_stack.push_action('increase', test_item, 1, 2)
    
    status = cart_stack.get_stack_status()
    
    return jsonify({
        'success': True,
        'message': 'Stack test completed',
        'stack_status': status,
        'undo_stack_raw': [str(a) for a in cart_stack.undo_stack],
        'redo_stack_raw': [str(a) for a in cart_stack.redo_stack]
    }), 200