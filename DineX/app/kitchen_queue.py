
from collections import deque
from datetime import datetime


class KitchenQueue:
    
    def __init__(self):
        """Initialize empty FIFO queue using deque for O(1) operations"""
        self.queue = deque()  
        self.cooking_orders = []  
        self.completed_orders = []  
    
    def enqueue(self, order):
        order['kitchenStatus'] = 'waiting'
        self.queue.append(order)
        return order
    
    def dequeue(self):
        """
        Remove and return order from front of queue (start cooking)
        
        Time Complexity: O(1)
        
        Returns:
            dict: Order at front of queue, or None if empty
        """
        if self.is_empty():
            return None
        
        order = self.queue.popleft()  # O(1) operation with deque
        order['kitchenStatus'] = 'cooking'
        order['cookingStartedAt'] = datetime.now().isoformat()
        self.cooking_orders.append(order)
        
        return order
    
    def peek(self):
        """
        View order at front of queue without removing
        
        Time Complexity: O(1)
        
        Returns:
            dict: Order at front, or None if empty
        """
        if self.is_empty():
            return None
        return self.queue[0]
    
    def is_empty(self):
        """
        Check if kitchen queue is empty
        
        Time Complexity: O(1)
        
        Returns:
            bool: True if empty, False otherwise
        """
        return len(self.queue) == 0
    
    def size(self):
        """
        Get number of orders waiting in queue
        
        Time Complexity: O(1)
        
        Returns:
            int: Number of orders in queue
        """
        return len(self.queue)
    
    def get_all_waiting(self):
        """
        Get all orders waiting in queue (in FIFO order)
        
        Time Complexity: O(n)
        
        Returns:
            list: All orders in queue, front to back
        """
        return list(self.queue)
    
    def get_cooking_orders(self):
        """
        Get all orders currently being cooked
        
        Time Complexity: O(1)
        
        Returns:
            list: Orders with kitchenStatus='cooking'
        """
        return self.cooking_orders.copy()
    
    def complete_cooking(self, order_id):
        """
        Mark order as finished cooking
        
        Time Complexity: O(n) where n = number of cooking orders
        
        Args:
            order_id (str): Order ID to complete
        
        Returns:
            dict: Completed order, or None if not found
        """
        for i, order in enumerate(self.cooking_orders):
            if order['orderId'] == order_id:
                order['kitchenStatus'] = 'completed'
                order['cookingCompletedAt'] = datetime.now().isoformat()
                self.completed_orders.append(order)
                self.cooking_orders.pop(i)
                return order
        
        return None
    
    def get_completed_orders(self):
        """
        Get all orders that finished cooking
        
        Time Complexity: O(1)
        
        Returns:
            list: Orders with kitchenStatus='completed'
        """
        return self.completed_orders.copy()
    
    def find_order(self, order_id):
        """
        Find order in any kitchen stage
        
        Time Complexity: O(n)
        
        Args:
            order_id (str): Order ID to find
        
        Returns:
            dict: Order object with 'order' and 'stage' keys, or None
        """
        # Check waiting queue
        for order in self.queue:
            if order['orderId'] == order_id:
                return {'order': order, 'stage': 'waiting'}
        
        # Check cooking
        for order in self.cooking_orders:
            if order['orderId'] == order_id:
                return {'order': order, 'stage': 'cooking'}
        
        # Check completed
        for order in self.completed_orders:
            if order['orderId'] == order_id:
                return {'order': order, 'stage': 'completed'}
        
        return None
    
    def remove_order(self, order_id):
        """
        Remove order from queue (e.g., cancellation)
        
        Time Complexity: O(n)
        
        Args:
            order_id (str): Order ID to remove
        
        Returns:
            bool: True if removed, False if not found
        """
        # Try to remove from waiting queue
        for i, order in enumerate(self.queue):
            if order['orderId'] == order_id:
                del self.queue[i]
                return True
        
        # Try to remove from cooking
        for i, order in enumerate(self.cooking_orders):
            if order['orderId'] == order_id:
                self.cooking_orders.pop(i)
                return True
        
        return False
    
    def get_statistics(self):
        """
        Get kitchen queue statistics
        
        Time Complexity: O(1)
        
        Returns:
            dict: Statistics about queue state
        """
        return {
            'waiting': len(self.queue),
            'cooking': len(self.cooking_orders),
            'completed': len(self.completed_orders),
            'total': len(self.queue) + len(self.cooking_orders) + len(self.completed_orders),
            'nextOrder': self.peek()['orderId'] if not self.is_empty() else None
        }
    
    def get_queue_position(self, order_id):
        """
        Get position of order in waiting queue
        
        Time Complexity: O(n)
        
        Args:
            order_id (str): Order ID to find
        
        Returns:
            int: Position (1-indexed), or None if not in queue
        """
        for position, order in enumerate(self.queue, start=1):
            if order['orderId'] == order_id:
                return position
        return None
    
    def __len__(self):
        """Return total orders in kitchen pipeline"""
        return len(self.queue) + len(self.cooking_orders)
    
    def __repr__(self):
        """String representation for debugging"""
        stats = self.get_statistics()
        return f"KitchenQueue(waiting={stats['waiting']}, cooking={stats['cooking']}, completed={stats['completed']})"


# =============================================================================
# USAGE EXAMPLE
# =============================================================================

if __name__ == "__main__":
    # Create kitchen queue
    kitchen = KitchenQueue()
    
    # Simulate orders arriving
    orders = [
        {'orderId': 'ORD0001', 'customerName': 'Alice', 'timestamp': '2026-01-03T10:00:00'},
        {'orderId': 'ORD0002', 'customerName': 'Bob', 'timestamp': '2026-01-03T10:05:00'},
        {'orderId': 'ORD0003', 'customerName': 'Charlie', 'timestamp': '2026-01-03T10:10:00'},
    ]
    
    # Add orders to kitchen queue (FIFO)
    for order in orders:
        kitchen.enqueue(order)
        print(f"✅ Added {order['orderId']} to kitchen queue")
    
    print(f"\n📊 Queue Stats: {kitchen.get_statistics()}")
    
    # Start cooking first order (FIFO)
    next_order = kitchen.dequeue()
    print(f"\n👨‍🍳 Started cooking: {next_order['orderId']}")
    
    # Complete cooking
    kitchen.complete_cooking(next_order['orderId'])
    print(f"✅ Finished cooking: {next_order['orderId']}")
    
    print(f"\n📊 Final Stats: {kitchen.get_statistics()}")