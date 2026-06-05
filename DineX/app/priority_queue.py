class MinHeap:
    
    def __init__(self):
        self.heap = []
        self.size = 0
    
    def parent(self, i):
        """Get parent index"""
        return (i - 1) // 2
    
    def left_child(self, i):
        """Get left child index"""
        return 2 * i + 1
    
    def right_child(self, i):
        """Get right child index"""
        return 2 * i + 2
    
    def swap(self, i, j):
        """Swap two elements in heap"""
        self.heap[i], self.heap[j] = self.heap[j], self.heap[i]
    
    def insert(self, order):
        """
        Insert order into priority queue
        Time Complexity: O(log n)
        """
        self.heap.append(order)
        self.size += 1
        self._heapify_up(self.size - 1)
    
    def _heapify_up(self, index):
        """
        Maintain heap property by moving element up
        """
        while index > 0:
            parent_idx = self.parent(index)
            
            # Compare based on priority, then timestamp
            if self._has_higher_priority(index, parent_idx):
                self.swap(index, parent_idx)
                index = parent_idx
            else:
                break
    
    def extract_min(self):
        """
        Remove and return highest priority order
        Time Complexity: O(log n)
        """
        if self.size == 0:
            return None
        
        if self.size == 1:
            self.size = 0
            return self.heap.pop()
        
        # Store min element
        min_order = self.heap[0]
        
        # Move last element to root
        self.heap[0] = self.heap.pop()
        self.size -= 1
        
        # Heapify down from root
        self._heapify_down(0)
        
        return min_order
    
    def _heapify_down(self, index):
        """
        Maintain heap property by moving element down
        """
        while True:
            smallest = index
            left = self.left_child(index)
            right = self.right_child(index)
            
            # Check if left child has higher priority
            if left < self.size and self._has_higher_priority(left, smallest):
                smallest = left
            
            # Check if right child has higher priority
            if right < self.size and self._has_higher_priority(right, smallest):
                smallest = right
            
            # If smallest is not current index, swap and continue
            if smallest != index:
                self.swap(index, smallest)
                index = smallest
            else:
                break
    
    def _has_higher_priority(self, i, j):
        """
        Check if element at index i has higher priority than j
        Priority: Lower number = Higher priority
        If same priority, earlier timestamp = Higher priority
        """
        order_i = self.heap[i]
        order_j = self.heap[j]
        
        # Compare priority levels
        if order_i['priority'] != order_j['priority']:
            return order_i['priority'] < order_j['priority']
        
        # If same priority, compare timestamps (earlier = higher priority)
        return order_i['timestamp'] < order_j['timestamp']
    
    def peek(self):
        """
        View highest priority order without removing
        Time Complexity: O(1)
        """
        return self.heap[0] if self.size > 0 else None
    
    def is_empty(self):
        """Check if queue is empty"""
        return self.size == 0
    
    def get_all_orders(self):
        """Return all orders in queue (not in sorted order)"""
        return self.heap.copy()
    
    def get_orders_by_priority(self):
        """
        Return all orders sorted by priority
        Time Complexity: O(n log n)
        """
        sorted_orders = []
        temp_heap = MinHeap()
        temp_heap.heap = self.heap.copy()
        temp_heap.size = self.size
        
        while not temp_heap.is_empty():
            sorted_orders.append(temp_heap.extract_min())
        
        return sorted_orders
    
    def remove_order(self, order_id):
        """
        Remove specific order by ID
        Time Complexity: O(n)
        """
        for i, order in enumerate(self.heap):
            if order['orderId'] == order_id:
                # Replace with last element
                self.heap[i] = self.heap[-1]
                self.heap.pop()
                self.size -= 1
                
                # Restore heap property
                if i < self.size:
                    self._heapify_down(i)
                    self._heapify_up(i)
                
                return True
        return False
    
    def update_order_status(self, order_id, new_status):
        """
        Update order status in queue
        """
        for order in self.heap:
            if order['orderId'] == order_id:
                order['status'] = new_status
                return True
        return False
    
    def get_order(self, order_id):
        """
        Get specific order by ID
        Time Complexity: O(n)
        """
        for order in self.heap:
            if order['orderId'] == order_id:
                return order
        return None
    
    def __len__(self):
        """Return size of queue"""
        return self.size
    
    def __repr__(self):
        """String representation for debugging"""
        return f"MinHeap(size={self.size}, orders={len(self.heap)})"


class OrderPriorityQueue:
    """
    High-level Order Management System using MinHeap
    Manages pending, processing, and completed orders
    """
    
    def __init__(self):
        self.pending_queue = MinHeap()
        self.processing_orders = []
        self.completed_orders = []
    
    def add_order(self, order):
        """
        Add new order to pending queue
        """
        order['status'] = 'pending'
        self.pending_queue.insert(order)
        return order
    
    def process_next_order(self):
        """
        Move highest priority order to processing
        """
        if self.pending_queue.is_empty():
            return None
        
        order = self.pending_queue.extract_min()
        order['status'] = 'processing'
        self.processing_orders.append(order)
        
        return order
    
    def complete_order(self, order_id):
        """
        Move order from processing to completed
        """
        for i, order in enumerate(self.processing_orders):
            if order['orderId'] == order_id:
                order['status'] = 'completed'
                self.completed_orders.append(order)
                self.processing_orders.pop(i)
                return order
        return None
    
    def cancel_order(self, order_id):
        """
        Cancel order (remove from pending or processing)
        """
        # Try to remove from pending queue
        if self.pending_queue.remove_order(order_id):
            return True
        
        # Try to remove from processing
        for i, order in enumerate(self.processing_orders):
            if order['orderId'] == order_id:
                order['status'] = 'cancelled'
                self.processing_orders.pop(i)
                return True
        
        return False
    
    def get_all_pending_orders(self):
        """Get all pending orders sorted by priority"""
        return self.pending_queue.get_orders_by_priority()
    
    def get_processing_orders(self):
        """Get all orders currently being processed"""
        return self.processing_orders.copy()
    
    def get_completed_orders(self):
        """Get all completed orders"""
        return self.completed_orders.copy()
    
    def get_order_status(self, order_id):
        """
        Get order and its current status
        """
        # Check pending
        order = self.pending_queue.get_order(order_id)
        if order:
            return order
        
        # Check processing
        for order in self.processing_orders:
            if order['orderId'] == order_id:
                return order
        
        # Check completed
        for order in self.completed_orders:
            if order['orderId'] == order_id:
                return order
        
        return None
    
    def get_queue_statistics(self):
        """
        Get statistics about order queue
        """
        return {
            'pending': len(self.pending_queue),
            'processing': len(self.processing_orders),
            'completed': len(self.completed_orders),
            'total': len(self.pending_queue) + len(self.processing_orders) + len(self.completed_orders)
        }
    
    def __repr__(self):
        stats = self.get_queue_statistics()
        return f"OrderQueue(pending={stats['pending']}, processing={stats['processing']}, completed={stats['completed']})"