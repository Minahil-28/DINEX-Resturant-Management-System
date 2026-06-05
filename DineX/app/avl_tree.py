
class AVLNode:
    """Node for AVL Tree"""
    def __init__(self, item, key_func):
        self.item = item
        self.key = key_func(item)
        self.left = None
        self.right = None
        self.height = 1

class AVLTree:
    """Self-balancing AVL Tree for menu items"""
    def __init__(self, key_func, reverse=False):
        self.root = None
        self.key_func = key_func
        self.reverse = reverse  # For descending order
    
    def _get_height(self, node):
        if not node:
            return 0
        return node.height
    
    def _get_balance(self, node):
        if not node:
            return 0
        return self._get_height(node.left) - self._get_height(node.right)
    
    def _update_height(self, node):
        if node:
            node.height = 1 + max(self._get_height(node.left), 
                                  self._get_height(node.right))
    
    def _rotate_right(self, z):
        """Right rotation"""
        y = z.left
        T3 = y.right
        
        # Perform rotation
        y.right = z
        z.left = T3
        
        # Update heights
        self._update_height(z)
        self._update_height(y)
        
        return y
    
    def _rotate_left(self, z):
        """Left rotation"""
        y = z.right
        T2 = y.left
        
        # Perform rotation
        y.left = z
        z.right = T2
        
        # Update heights
        self._update_height(z)
        self._update_height(y)
        
        return y
    
    def _compare(self, key1, key2):
        """Compare keys based on reverse flag"""
        if self.reverse:
            return key1 > key2
        return key1 < key2
    
    def insert(self, item):
        """Insert item and rebalance tree"""
        self.root = self._insert_recursive(self.root, item)
    
    def _insert_recursive(self, node, item):
        # Standard BST insertion
        if not node:
            return AVLNode(item, self.key_func)
        
        key = self.key_func(item)
        
        if self._compare(key, node.key):
            node.left = self._insert_recursive(node.left, item)
        else:
            node.right = self._insert_recursive(node.right, item)
        
        # Update height
        self._update_height(node)
        
        # Get balance factor
        balance = self._get_balance(node)
        
        # Left Left Case
        if balance > 1 and self._compare(key, node.left.key):
            return self._rotate_right(node)
        
        # Right Right Case
        if balance < -1 and not self._compare(key, node.right.key):
            return self._rotate_left(node)
        
        # Left Right Case
        if balance > 1 and not self._compare(key, node.left.key):
            node.left = self._rotate_left(node.left)
            return self._rotate_right(node)
        
        # Right Left Case
        if balance < -1 and self._compare(key, node.right.key):
            node.right = self._rotate_right(node.right)
            return self._rotate_left(node)
        
        return node
    
    def inorder_traversal(self):
        """Return items in sorted order"""
        result = []
        self._inorder_recursive(self.root, result)
        return result
    
    def _inorder_recursive(self, node, result):
        if node:
            self._inorder_recursive(node.left, result)
            result.append(node.item)
            self._inorder_recursive(node.right, result)
    
    def search_range(self, min_val=None, max_val=None):
        """Search items within a range"""
        result = []
        self._range_search(self.root, min_val, max_val, result)
        return result
    
    def _range_search(self, node, min_val, max_val, result):
        if not node:
            return
        
        # Check if current node is in range
        in_range = True
        if min_val is not None and node.key < min_val:
            in_range = False
        if max_val is not None and node.key > max_val:
            in_range = False
        
        # Traverse left if possible
        if min_val is None or node.key > min_val:
            self._range_search(node.left, min_val, max_val, result)
        
        # Add current if in range
        if in_range:
            result.append(node.item)
        
        # Traverse right if possible
        if max_val is None or node.key < max_val:
            self._range_search(node.right, min_val, max_val, result)


class MenuManager:
    """Manages multiple AVL trees for different sorting strategies"""
    
    def __init__(self):
        # Tree sorted by name (alphabetical)
        self.name_tree = AVLTree(lambda item: item['name'].lower())
        
        # Tree sorted by price (ascending)
        self.price_low_tree = AVLTree(lambda item: item['price'])
        
        # Tree sorted by price (descending)
        self.price_high_tree = AVLTree(lambda item: item['price'], reverse=True)
        
        # Tree sorted by rating (descending - popular first)
        self.popular_tree = AVLTree(lambda item: item.get('rating', 0), reverse=True)
        
        self.items_loaded = False
    
    def load_items(self, items):
        """Load menu items into all AVL trees"""
        for item in items:
            self.name_tree.insert(item)
            self.price_low_tree.insert(item)
            self.price_high_tree.insert(item)
            self.popular_tree.insert(item)
        
        self.items_loaded = True
        print(f"✅ Loaded {len(items)} items into 4 AVL trees")
    
    def get_sorted_items(self, sort_by='name'):
        """Get items sorted by specified criteria"""
        if not self.items_loaded:
            return []
        
        if sort_by == 'name':
            return self.name_tree.inorder_traversal()
        elif sort_by == 'price-low':
            return self.price_low_tree.inorder_traversal()
        elif sort_by == 'price-high':
            return self.price_high_tree.inorder_traversal()
        elif sort_by == 'popular':
            return self.popular_tree.inorder_traversal()
        else:
            return self.name_tree.inorder_traversal()
    
    def search_items(self, query='', category='all', min_price=None, 
                     max_price=None, sort_by='name'):
        """Search and filter menu items"""
        # Get sorted items
        items = self.get_sorted_items(sort_by)
        
        # Filter by search query
        if query:
            query_lower = query.lower()
            items = [item for item in items 
                    if query_lower in item['name'].lower() 
                    or query_lower in item.get('description', '').lower()]
        
        # Filter by category
        if category != 'all':
            items = [item for item in items 
                    if item.get('category', '') == category]
        
        # Filter by price range
        if min_price is not None:
            items = [item for item in items if item['price'] >= min_price]
        if max_price is not None:
            items = [item for item in items if item['price'] <= max_price]
        
        return items
    
    def get_statistics(self):
        """Get menu statistics"""
        if not self.items_loaded:
            return None
        
        items = self.name_tree.inorder_traversal()
        
        if not items:
            return None
        
        prices = [item['price'] for item in items]
        ratings = [item.get('rating', 0) for item in items]
        
        # Count by category
        categories = {}
        for item in items:
            cat = item.get('category', 'other')
            categories[cat] = categories.get(cat, 0) + 1
        
        return {
            'total_items': len(items),
            'min_price': min(prices),
            'max_price': max(prices),
            'avg_price': sum(prices) / len(prices),
            'avg_rating': sum(ratings) / len(ratings) if ratings else 0,
            'categories': categories
        }
    
    def get_items_by_price_range(self, min_price, max_price):
        """Get items within price range (optimized using AVL tree)"""
        return self.price_low_tree.search_range(min_price, max_price)
    
    def get_top_rated(self, limit=10):
        """Get top rated items"""
        items = self.popular_tree.inorder_traversal()
        return items[:limit]