
from datetime import datetime
from typing import Optional, List, Dict, Any

class OrderNode:

    def __init__(self, order_data: Dict[str, Any]):
        self.order_id = order_data.get('orderId')
        self.customer_phone = order_data.get('customerPhone')
        self.customer_name = order_data.get('customerName')
        self.items = order_data.get('items', [])
        self.total = order_data.get('total', 0)
        self.status = order_data.get('status', 'pending')
        self.timestamp = order_data.get('timestamp', datetime.now().isoformat())
        self.delivery_address = order_data.get('deliveryAddress', '')
        
        # Store full order data for future reference
        self.full_data = order_data
        
        # Pointer to next order
        self.next: Optional['OrderNode'] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert node back to dictionary format"""
        return self.full_data
    
    def __repr__(self):
        return f"OrderNode({self.order_id}, Rs.{self.total}, {self.status})"


class TransactionNode:
    """
    Node for storing transaction/payment information.
    Each transaction represents a payment made by customer.
    
    TIME COMPLEXITY: O(1) for node creation
    SPACE COMPLEXITY: O(1) per node
    """
    def __init__(self, transaction_data: Dict[str, Any]):
        self.transaction_id = transaction_data.get('transactionId')
        self.order_id = transaction_data.get('orderId')
        self.customer_phone = transaction_data.get('customerPhone')
        self.amount = transaction_data.get('amount', 0)
        self.payment_method = transaction_data.get('paymentMethod', 'cash')
        self.status = transaction_data.get('status', 'completed')
        self.timestamp = transaction_data.get('timestamp', datetime.now().isoformat())
        
        # Store full transaction data
        self.full_data = transaction_data
        
        # Pointer to next transaction
        self.next: Optional['TransactionNode'] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert node back to dictionary format"""
        return self.full_data
    
    def __repr__(self):
        return f"TransactionNode({self.transaction_id}, Rs.{self.amount}, {self.payment_method})"


# ===========================
# LINKED LIST CLASSES
# ===========================

class OrderHistoryLinkedList:
    """
    Singly Linked List for managing customer order history.
    Orders are stored in chronological order (newest first).
    
    WHY LINKED LIST?
    - Dynamic size (no need to pre-allocate space)
    - Efficient insertion at head: O(1)
    - Memory efficient for sparse data
    - Natural for chronological history (LIFO - most recent first)
    
    OPERATIONS:
    - add_order: O(1) - insert at head
    - search: O(n) - traverse list
    - get_all: O(n) - traverse entire list
    - size: O(1) - maintain counter
    """
    
    def __init__(self, customer_phone: str):
        self.customer_phone = customer_phone
        self.head: Optional[OrderNode] = None
        self.tail: Optional[OrderNode] = None
        self.size_count = 0
    
    
    def add_order(self, order_data: Dict[str, Any]) -> OrderNode:
        """
        Add new order to the linked list (at head for most recent first).
        
        ALGORITHM:
        1. Create new OrderNode
        2. Point new node's next to current head
        3. Update head to new node
        4. Update tail if list was empty
        5. Increment size
        
        Args:
            order_data: Dictionary containing order information
            
        Returns:
            OrderNode: The created node
            
        Time Complexity: O(1) - constant time insertion at head
        Space Complexity: O(1) - single node allocation
        
        Example:
            order_data = {
                'orderId': 'ORD0001',
                'customerPhone': '03704018969',
                'total': 550,
                'status': 'delivered'
            }
            node = history.add_order(order_data)
        """
        new_node = OrderNode(order_data)
        
        # Empty list case
        if self.head is None:
            self.head = new_node
            self.tail = new_node
        else:
            # Insert at head (most recent first)
            new_node.next = self.head
            self.head = new_node
        
        self.size_count += 1
        return new_node
    
    
    def search_by_order_id(self, order_id: str) -> Optional[OrderNode]:
        """
        Search for order by order ID.
        
        ALGORITHM:
        Linear search through linked list until match found.
        
        Args:
            order_id: Order ID to search for
            
        Returns:
            OrderNode if found, None otherwise
            
        Time Complexity: O(n) where n = number of orders
        Space Complexity: O(1)
        """
        current = self.head
        
        while current:
            if current.order_id == order_id:
                return current
            current = current.next
        
        return None
    
    
    def get_recent_orders(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get most recent N orders.
        
        Since we insert at head, head contains most recent order.
        
        Args:
            limit: Number of recent orders to return
            
        Returns:
            List of order dictionaries
            
        Time Complexity: O(min(n, limit))
        Space Complexity: O(limit) for result list
        """
        orders = []
        current = self.head
        count = 0
        
        while current and count < limit:
            orders.append(current.to_dict())
            current = current.next
            count += 1
        
        return orders
    
    
    def get_all_orders(self) -> List[Dict[str, Any]]:
        """
        Get all orders in chronological order (newest first).
        
        Returns:
            List of all order dictionaries
            
        Time Complexity: O(n)
        Space Complexity: O(n) for result list
        """
        orders = []
        current = self.head
        
        while current:
            orders.append(current.to_dict())
            current = current.next
        
        return orders
    
    
    def get_orders_by_status(self, status: str) -> List[Dict[str, Any]]:
        """
        Filter orders by status.
        
        Args:
            status: Status to filter by ('delivered', 'pending', etc.)
            
        Returns:
            List of matching orders
            
        Time Complexity: O(n)
        Space Complexity: O(k) where k = matching orders
        """
        orders = []
        current = self.head
        
        while current:
            if current.status == status:
                orders.append(current.to_dict())
            current = current.next
        
        return orders
    
    
    def calculate_total_spent(self) -> float:
        """
        Calculate total amount spent across all orders.
        
        Returns:
            Total amount spent
            
        Time Complexity: O(n)
        Space Complexity: O(1)
        """
        total = 0
        current = self.head
        
        while current:
            # Only count delivered orders
            if current.status in ['delivered', 'completed']:
                total += current.total
            current = current.next
        
        return total
    
    
    def size(self) -> int:
        """
        Get number of orders in history.
        
        Returns:
            Number of orders
            
        Time Complexity: O(1) - maintained counter
        Space Complexity: O(1)
        """
        return self.size_count
    
    
    def is_empty(self) -> bool:
        """Check if order history is empty"""
        return self.head is None
    
    
    def __len__(self):
        """Allow len(history) syntax"""
        return self.size_count
    
    
    def __repr__(self):
        return f"OrderHistoryLinkedList(customer={self.customer_phone}, orders={self.size_count})"


class TransactionHistoryLinkedList:
    """
    Singly Linked List for managing customer transaction history.
    Transactions are stored in chronological order (newest first).
    
    Similar structure to OrderHistoryLinkedList but for payment records.
    """
    
    def __init__(self, customer_phone: str):
        self.customer_phone = customer_phone
        self.head: Optional[TransactionNode] = None
        self.tail: Optional[TransactionNode] = None
        self.size_count = 0
    
    
    def add_transaction(self, transaction_data: Dict[str, Any]) -> TransactionNode:
        """
        Add new transaction to the linked list.
        
        Time Complexity: O(1)
        Space Complexity: O(1)
        """
        new_node = TransactionNode(transaction_data)
        
        if self.head is None:
            self.head = new_node
            self.tail = new_node
        else:
            new_node.next = self.head
            self.head = new_node
        
        self.size_count += 1
        return new_node
    
    
    def search_by_transaction_id(self, transaction_id: str) -> Optional[TransactionNode]:
        """
        Search for transaction by ID.
        
        Time Complexity: O(n)
        Space Complexity: O(1)
        """
        current = self.head
        
        while current:
            if current.transaction_id == transaction_id:
                return current
            current = current.next
        
        return None
    
    
    def get_transactions_by_order(self, order_id: str) -> List[Dict[str, Any]]:
        """
        Get all transactions for a specific order.
        (An order might have multiple partial payments)
        
        Time Complexity: O(n)
        Space Complexity: O(k) where k = matching transactions
        """
        transactions = []
        current = self.head
        
        while current:
            if current.order_id == order_id:
                transactions.append(current.to_dict())
            current = current.next
        
        return transactions
    
    
    def get_recent_transactions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get most recent N transactions.
        
        Time Complexity: O(min(n, limit))
        Space Complexity: O(limit)
        """
        transactions = []
        current = self.head
        count = 0
        
        while current and count < limit:
            transactions.append(current.to_dict())
            current = current.next
            count += 1
        
        return transactions
    
    
    def get_all_transactions(self) -> List[Dict[str, Any]]:
        """
        Get all transactions.
        
        Time Complexity: O(n)
        Space Complexity: O(n)
        """
        transactions = []
        current = self.head
        
        while current:
            transactions.append(current.to_dict())
            current = current.next
        
        return transactions
    
    
    def calculate_total_paid(self) -> float:
        """
        Calculate total amount paid across all transactions.
        
        Time Complexity: O(n)
        Space Complexity: O(1)
        """
        total = 0
        current = self.head
        
        while current:
            if current.status == 'completed':
                total += current.amount
            current = current.next
        
        return total
    
    
    def size(self) -> int:
        """Get number of transactions"""
        return self.size_count
    
    
    def is_empty(self) -> bool:
        """Check if transaction history is empty"""
        return self.head is None
    
    
    def __len__(self):
        return self.size_count
    
    
    def __repr__(self):
        return f"TransactionHistoryLinkedList(customer={self.customer_phone}, transactions={self.size_count})"


# ===========================
# CUSTOMER HISTORY MANAGER
# ===========================

class CustomerHistoryManager:
    """
    Manager class to handle multiple customers' order and transaction histories.
    Uses dictionary to map customer phone to their linked lists.
    
    STRUCTURE:
    {
        'customer_phone': {
            'orders': OrderHistoryLinkedList,
            'transactions': TransactionHistoryLinkedList
        }
    }
    
    WHY THIS DESIGN?
    - O(1) customer lookup using dictionary
    - O(1) order insertion per customer (linked list head insert)
    - Separate linked lists per customer (isolation)
    - Easy to serialize/deserialize for persistence
    """
    
    def __init__(self):
        self.customers: Dict[str, Dict[str, Any]] = {}
    
    
    def _get_or_create_customer(self, customer_phone: str) -> Dict[str, Any]:
        """
        Get customer's history or create new one if doesn't exist.
        
        Time Complexity: O(1) - dictionary lookup
        Space Complexity: O(1)
        """
        if customer_phone not in self.customers:
            self.customers[customer_phone] = {
                'orders': OrderHistoryLinkedList(customer_phone),
                'transactions': TransactionHistoryLinkedList(customer_phone)
            }
        
        return self.customers[customer_phone]
    
    
    # =========================
    # ORDER OPERATIONS
    # =========================
    
    def add_order(self, order_data: Dict[str, Any]) -> bool:
        """
        Add order to customer's order history.
        
        Args:
            order_data: Order dictionary (must contain 'customerPhone')
            
        Returns:
            bool: True if successful
            
        Time Complexity: O(1) - dictionary lookup + head insert
        Space Complexity: O(1)
        """
        customer_phone = order_data.get('customerPhone')
        if not customer_phone:
            return False
        
        customer = self._get_or_create_customer(customer_phone)
        customer['orders'].add_order(order_data)
        
        return True
    
    
    def get_order_history(self, customer_phone: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get customer's order history.
        
        Args:
            customer_phone: Customer's phone number
            limit: Maximum number of orders to return (None = all)
            
        Returns:
            List of orders (newest first)
            
        Time Complexity: O(1) lookup + O(min(n, limit)) traversal
        Space Complexity: O(min(n, limit))
        """
        if customer_phone not in self.customers:
            return []
        
        order_list = self.customers[customer_phone]['orders']
        
        if limit:
            return order_list.get_recent_orders(limit)
        else:
            return order_list.get_all_orders()
    
    
    def search_order(self, customer_phone: str, order_id: str) -> Optional[Dict[str, Any]]:
        """
        Search for specific order in customer history.
        
        Time Complexity: O(n) where n = customer's orders
        Space Complexity: O(1)
        """
        if customer_phone not in self.customers:
            return None
        
        node = self.customers[customer_phone]['orders'].search_by_order_id(order_id)
        return node.to_dict() if node else None
    
    
    def get_customer_total_spent(self, customer_phone: str) -> float:
        """
        Calculate total amount customer has spent.
        
        Time Complexity: O(n)
        Space Complexity: O(1)
        """
        if customer_phone not in self.customers:
            return 0.0
        
        return self.customers[customer_phone]['orders'].calculate_total_spent()
    
    
    # =========================
    # TRANSACTION OPERATIONS
    # =========================
    
    def add_transaction(self, transaction_data: Dict[str, Any]) -> bool:
        """
        Add transaction to customer's payment history.
        
        Time Complexity: O(1)
        Space Complexity: O(1)
        """
        customer_phone = transaction_data.get('customerPhone')
        if not customer_phone:
            return False
        
        customer = self._get_or_create_customer(customer_phone)
        customer['transactions'].add_transaction(transaction_data)
        
        return True
    
    
    def get_transaction_history(self, customer_phone: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get customer's transaction history.
        
        Time Complexity: O(1) lookup + O(min(n, limit)) traversal
        Space Complexity: O(min(n, limit))
        """
        if customer_phone not in self.customers:
            return []
        
        transaction_list = self.customers[customer_phone]['transactions']
        
        if limit:
            return transaction_list.get_recent_transactions(limit)
        else:
            return transaction_list.get_all_transactions()
    
    
    def search_transaction(self, customer_phone: str, transaction_id: str) -> Optional[Dict[str, Any]]:
        """
        Search for specific transaction.
        
        Time Complexity: O(n)
        Space Complexity: O(1)
        """
        if customer_phone not in self.customers:
            return None
        
        node = self.customers[customer_phone]['transactions'].search_by_transaction_id(transaction_id)
        return node.to_dict() if node else None
    
    
    # =========================
    # STATISTICS & UTILITIES
    # =========================
    
    def get_customer_statistics(self, customer_phone: str) -> Dict[str, Any]:
        """
        Get comprehensive statistics for a customer.
        
        Returns:
            Dictionary with order count, transaction count, total spent, etc.
        """
        if customer_phone not in self.customers:
            return {
                'total_orders': 0,
                'total_transactions': 0,
                'total_spent': 0.0,
                'total_paid': 0.0
            }
        
        customer = self.customers[customer_phone]
        
        return {
            'total_orders': len(customer['orders']),
            'total_transactions': len(customer['transactions']),
            'total_spent': customer['orders'].calculate_total_spent(),
            'total_paid': customer['transactions'].calculate_total_paid(),
            'orders': customer['orders'].get_all_orders(),
            'transactions': customer['transactions'].get_all_transactions()
        }
    
    
    def get_all_customers(self) -> List[str]:
        """Get list of all customer phone numbers"""
        return list(self.customers.keys())
    
    
    def __len__(self):
        """Return number of customers being tracked"""
        return len(self.customers)
    
    
    def __repr__(self):
        return f"CustomerHistoryManager(customers={len(self.customers)})"


# ===========================
# COMPLEXITY ANALYSIS
# ===========================
"""
LINKED LIST TIME COMPLEXITY:

Operation                  | Time Complexity | Space Complexity
---------------------------|-----------------|------------------
add_order                  | O(1)           | O(1)
add_transaction            | O(1)           | O(1)
search_by_order_id         | O(n)           | O(1)
search_by_transaction_id   | O(n)           | O(1)
get_recent_orders(k)       | O(k)           | O(k)
get_all_orders             | O(n)           | O(n)
calculate_total_spent      | O(n)           | O(1)
size                       | O(1)           | O(1)

WHERE:
n = number of orders/transactions for a customer
k = limit parameter for recent items

WHY LINKED LIST OVER ARRAY?
✅ Dynamic size (no resize needed)
✅ O(1) insertion at head (most recent first)
✅ Memory efficient for sparse data
✅ Natural chronological ordering

TRADE-OFFS:
❌ O(n) search (vs O(log n) for BST)
❌ No random access (vs O(1) for array)
❌ Extra memory for pointers
✅ BUT: Order history is typically accessed sequentially (recent first)
✅ Search is rare compared to insertion and recent access
"""


# ===========================
# DEMO FUNCTION
# ===========================

def demonstrate_customer_history():
    """
    Demonstrate linked list operations with sample data.
    """
    print("=" * 60)
    print("CUSTOMER HISTORY - LINKED LIST DEMONSTRATION")
    print("=" * 60)
    
    # Initialize manager
    manager = CustomerHistoryManager()
    print("\n✅ CustomerHistoryManager initialized")
    
    # Sample orders
    sample_orders = [
        {
            'orderId': 'ORD0001',
            'customerPhone': '03704018969',
            'customerName': 'Yusra Shahid',
            'total': 550,
            'status': 'delivered',
            'timestamp': '2026-01-03T01:54:56'
        },
        {
            'orderId': 'ORD0002',
            'customerPhone': '03704018969',
            'customerName': 'Yusra Shahid',
            'total': 830,
            'status': 'delivered',
            'timestamp': '2026-01-03T02:15:23'
        },
        {
            'orderId': 'ORD0003',
            'customerPhone': '03015920315',
            'customerName': 'Minahil Mehmood',
            'total': 230,
            'status': 'processing',
            'timestamp': '2026-01-03T11:24:38'
        }
    ]
    
    # Add orders
    print("\n" + "=" * 60)
    print("ADDING ORDERS TO LINKED LIST")
    print("=" * 60)
    for order in sample_orders:
        manager.add_order(order)
        print(f"✅ Added {order['orderId']} for {order['customerName']}")
    
    # Get order history
    print("\n" + "=" * 60)
    print("ORDER HISTORY - Customer: 03704018969")
    print("=" * 60)
    history = manager.get_order_history('03704018969')
    for order in history:
        print(f"📦 {order['orderId']} - Rs.{order['total']} - {order['status']}")
    
    # Search order
    print("\n" + "=" * 60)
    print("SEARCH ORDER BY ID")
    print("=" * 60)
    found = manager.search_order('03704018969', 'ORD0001')
    if found:
        print(f"🔍 Found: {found['orderId']} - Rs.{found['total']}")
    
    # Statistics
    print("\n" + "=" * 60)
    print("CUSTOMER STATISTICS")
    print("=" * 60)
    stats = manager.get_customer_statistics('03704018969')
    print(f"📊 Total Orders: {stats['total_orders']}")
    print(f"💰 Total Spent: Rs.{stats['total_spent']}")
    
    print("\n" + "=" * 60)
    print("DEMONSTRATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    demonstrate_customer_history()