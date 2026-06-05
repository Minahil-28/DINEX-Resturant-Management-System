\# DineX - Food Delivery Management System



A full-stack food delivery platform built with advanced data structures and algorithms to optimize order processing, delivery routing, and customer management.



\## Overview



DineX is an educational project demonstrating practical applications of computer science concepts including priority queues, AVL trees, binary search trees, hash tables, stacks, graphs, and linked lists. The system manages the complete lifecycle of food delivery operations from menu browsing to order completion.



\## Features



\### Core Functionality



\- \*\*User Management\*\*: Registration, authentication, and role-based access control (customer, admin, kitchen staff, rider)

\- \*\*Menu Management\*\*: Dynamic menu with category filtering and search using BST and AVL tree implementations

\- \*\*Shopping Cart\*\*: Full cart functionality with quantity management and persistence

\- \*\*Order Placement\*\*: Multi-tier order system with priority levels (regular, express, VIP)

\- \*\*Real-time Tracking\*\*: Live order status tracking through kitchen and delivery pipelines

\- \*\*Delivery Management\*\*: Optimized route calculation and rider assignment



\### Advanced Features



\- \*\*Undo/Redo System\*\*: Stack-based cart modification recovery for deleted or changed items

\- \*\*Customer Analytics\*\*: Hash table-based customer lookup and statistics

\- \*\*Order History\*\*: Linked list implementation for efficient order tracking per customer

\- \*\*Priority Queue System\*\*: Intelligent delivery order prioritization

\- \*\*FIFO Kitchen Queue\*\*: Sequential order processing in kitchen



\## Technology Stack



\### Backend

\- Python 3.8+

\- Flask 2.0+

\- JSON-based persistence



\### Frontend

\- HTML5, CSS3, JavaScript (ES6+)

\- Responsive design with glassmorphism UI



\### Data Structures



\- \*\*Priority Queue\*\*: Order delivery optimization

\- \*\*AVL Tree\*\*: Menu item indexing and sorting

\- \*\*Binary Search Tree\*\*: Category-based menu filtering

\- \*\*Hash Table\*\*: Customer lookup (O(1) access)

\- \*\*FIFO Queue\*\*: Kitchen order processing

\- \*\*Stack\*\*: Cart undo/redo functionality

\- \*\*Linked List\*\*: Customer order history

\- \*\*Graph\*\*: Delivery route optimization (Dijkstra's algorithm foundation)



\## Installation



\### Prerequisites



\- Python 3.8 or higher

\- pip (Python package manager)

\- Modern web browser



\### Setup



1\. Clone the repository:

```bash

git clone https://github.com/yourusername/dinex.git

cd dinex

```



2\. Create a virtual environment:

```bash

python -m venv venv

source venv/bin/activate  # On Windows: venv\\Scripts\\activate

```



3\. Install dependencies:

```bash

pip install flask werkzeug

```



4\. Run the application:

```bash

python app.py

```



The application will be available at `http://localhost:5000`



\## Project Structure



```

dinex/

├── app/

│   ├── \_\_init\_\_.py

│   ├── routes.py                    # Main route handlers

│   ├── cart\_undo\_redo\_stack.py      # Undo/redo stack implementation

│   ├── priority\_queue.py            # Priority queue for delivery orders

│   ├── kitchen\_queue.py             # FIFO queue for kitchen

│   ├── avl\_tree.py                  # AVL tree menu management

│   ├── bst\_tree.py                  # BST category filtering

│   ├── customer\_hash\_table.py       # Hash table customer lookup

│   ├── customer\_history.py          # Linked list order history

│   └── data/

│       ├── users.json               # User accounts

│       ├── menu.json                # Menu items

│       ├── customers.json           # Customer profiles

│       ├── orders.json              # Order records

│       ├── carts.json               # Active shopping carts

│       └── delivery\_graph.json       # Delivery network

├── templates/

│   ├── index.html                   # Main page

│   ├── menu.html                    # Menu page

│   ├── admin.html                   # Admin dashboard

│   ├── kitchen.html                 # Kitchen dashboard

│   ├── rider.html                   # Rider dashboard

│   └── login.html                   # Login page

├── static/

│   ├── css/

│   │   └── style.css                # Main stylesheet

│   └── js/

│       └── script.js                # Frontend logic

└── README.md

```



\## Usage



\### Customer Workflow



1\. \*\*Browse Menu\*\*: Navigate to menu section with real-time filtering by category or price

2\. \*\*Add to Cart\*\*: Add items with automatic quantity management

3\. \*\*Checkout\*\*: Complete order with delivery address and priority selection

4\. \*\*Track Order\*\*: Monitor order status from kitchen to delivery



\### Admin Workflow



1\. \*\*View Dashboard\*\*: Monitor all pending and processing orders

2\. \*\*Priority Queue\*\*: Orders automatically sorted by tier (VIP > Express > Regular)

3\. \*\*Assign Deliveries\*\*: Select orders ready for delivery assignment



\### Kitchen Workflow



1\. \*\*Order Queue\*\*: View orders in FIFO sequence

2\. \*\*Start Cooking\*\*: Begin preparation of next order

3\. \*\*Mark Complete\*\*: Indicate food is ready for delivery



\### Rider Workflow



1\. \*\*View Assignments\*\*: See orders ready for delivery

2\. \*\*Navigation\*\*: View delivery route and customer details

3\. \*\*Delivery Confirmation\*\*: Mark orders as delivered



\## API Endpoints



\### Cart Operations

\- `GET /api/cart` - Retrieve user cart

\- `POST /api/cart/add` - Add item to cart

\- `PUT /api/cart/update/<item\_id>` - Update item quantity

\- `DELETE /api/cart/remove/<item\_id>` - Remove item from cart

\- `POST /api/cart/undo` - Undo last cart action

\- `POST /api/cart/redo` - Redo last undone action



\### Orders

\- `POST /api/orders/place` - Place new order

\- `GET /api/orders/<order\_id>` - Get order status

\- `GET /api/orders/queue/ready` - Get orders ready for delivery

\- `POST /api/orders/queue/assign-next` - Assign next priority order



\### Menu

\- `GET /api/menu` - Get all menu items

\- `GET /api/menu/filter` - Filter menu by category and price

\- `GET /api/menu/search` - Search menu items



\### Customers

\- `GET /api/customer/<phone>` - Get customer details

\- `POST /api/customer/register` - Register new customer

\- `GET /api/customer/<phone>/order-history` - Get customer order history



\## Data Structure Details



\### Priority Queue (Delivery Orders)

Maintains orders sorted by priority level. VIP orders process before express, which process before regular orders. Implemented with binary heap for O(log n) insertion and extraction.



\### AVL Tree (Menu Management)

Self-balancing binary search tree maintaining menu items sorted by various criteria. Enables O(log n) search and filtering operations with automatic rebalancing.



\### Hash Table (Customer Lookup)

Provides O(1) average-case lookup for customer records by phone number. Includes collision handling and load factor management.



\### FIFO Queue (Kitchen)

Processes orders in strict first-in-first-out sequence to maintain kitchen workflow fairness and predictability.



\### Stack (Undo/Redo)

Maintains action history for cart modifications. Supports both deletion recovery and quantity change reversal with automatic redo stack management.



\### Linked List (Order History)

Efficient sequential storage of customer order history. Each customer has a linked list node with order references for quick traversal.



\## Authentication



The system supports multiple user roles:



\- \*\*Customer\*\*: Can browse menu, place orders, track delivery

\- \*\*Admin\*\*: Full system access, order management, priority assignment

\- \*\*Kitchen Manager\*\*: Kitchen queue management and order status updates

\- \*\*Delivery Rider\*\*: View and complete delivery orders



Default admin credentials are hardcoded for demonstration:

\- admin@dinex.com / admin123



For production, replace with proper credential management.



\## Performance Characteristics



| Operation | Data Structure | Time Complexity |

|-----------|---|---|

| Customer lookup | Hash Table | O(1) |

| Menu search | AVL Tree | O(log n) |

| Category filter | BST | O(log n) |

| Order assignment | Priority Queue | O(log n) |

| Kitchen processing | FIFO Queue | O(1) |

| Cart undo/redo | Stack | O(1) |

| Order history | Linked List | O(n) |



\## Testing



Run the diagnostic test in browser console after making changes:



```javascript

// Test stack status

console.log('Stack status:', stackStatus);



// Test cart operations

await updateQuantity(itemId, 1);

console.log('Stack after quantity change:', stackStatus);



// Test undo

await undoCartDelete();

console.log('Cart after undo:', cart);

```



\## Contributing



This is an educational project created for learning data structures and algorithms. Contributions are welcome.



\## Authors



\- Minahil Mehmood (2024-CS-86)

\- Yusra Shahid (2024-CS-110)



UET Lahore - Data Structures Lab Project 2024



\## License



This project is provided as-is for educational purposes.



\## Acknowledgments



This project demonstrates practical implementations of fundamental computer science concepts covered in introductory data structures and algorithms courses. The architecture prioritizes educational clarity while maintaining functional completeness.



\## Notes



\- The system uses JSON file persistence for simplicity. Production environments should use a proper database (PostgreSQL, MongoDB, etc.)

\- Admin credentials should be moved to environment variables

\- API endpoints should include comprehensive error handling and validation

\- Frontend code could be refactored into modular components

\- Performance optimization opportunities exist in several data structures

