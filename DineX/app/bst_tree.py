
import json
import os

class MenuItem:
    """Menu item wrapper for BST storage"""
    def __init__(self, item_dict):
        self.id = item_dict['id']
        self.name = item_dict['name']
        self.price = item_dict['price']
        self.category = item_dict['category']
        self.description = item_dict.get('description', '')
        self.image = item_dict.get('image', '')
        self.stock = item_dict.get('stock', 0)
        self.rating = item_dict.get('rating', 0)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'price': self.price,
            'category': self.category,
            'description': self.description,
            'image': self.image,
            'stock': self.stock,
            'rating': self.rating
        }


class BSTNode:
    """Binary Search Tree Node"""
    def __init__(self, item):
        self.item = item
        self.left = None
        self.right = None
        self.height = 1


class MenuBST:
    """
    Self-balancing BST (AVL Tree)
    
    PERFORMANCE:
    - Insert: O(log n)
    - Price range search: O(k + log n) where k = results
    - Get all sorted: O(n)
    """
    
    def __init__(self):
        self.root = None
        self.size = 0
    
    def get_height(self, node):
        return node.height if node else 0
    
    def get_balance(self, node):
        if not node:
            return 0
        return self.get_height(node.left) - self.get_height(node.right)
    
    def rotate_right(self, y):
        x = y.left
        T2 = x.right
        x.right = y
        y.left = T2
        y.height = 1 + max(self.get_height(y.left), self.get_height(y.right))
        x.height = 1 + max(self.get_height(x.left), self.get_height(x.right))
        return x
    
    def rotate_left(self, x):
        y = x.right
        T2 = y.left
        y.left = x
        x.right = T2
        x.height = 1 + max(self.get_height(x.left), self.get_height(x.right))
        y.height = 1 + max(self.get_height(y.left), self.get_height(y.right))
        return y
    
    def insert(self, item):
        """Insert item - O(log n)"""
        self.root = self._insert_recursive(self.root, item)
        self.size += 1
    
    def _insert_recursive(self, node, item):
        if not node:
            return BSTNode(item)
        
        if item.price < node.item.price:
            node.left = self._insert_recursive(node.left, item)
        else:
            node.right = self._insert_recursive(node.right, item)
        
        node.height = 1 + max(self.get_height(node.left), self.get_height(node.right))
        balance = self.get_balance(node)
        
        # AVL Balancing
        if balance > 1 and item.price < node.left.item.price:
            return self.rotate_right(node)
        if balance < -1 and item.price >= node.right.item.price:
            return self.rotate_left(node)
        if balance > 1 and item.price >= node.left.item.price:
            node.left = self.rotate_left(node.left)
            return self.rotate_right(node)
        if balance < -1 and item.price < node.right.item.price:
            node.right = self.rotate_right(node.right)
            return self.rotate_left(node)
        
        return node
    
    def search_by_price_range(self, min_price=0, max_price=float('inf')):
        """
        Efficient price range search - O(k + log n)
        
        Example: 1000 items, 50 in range
        - Linear: 1000 checks
        - BST: 60 checks (16x faster!)
        """
        results = []
        self._range_search(self.root, min_price, max_price, results)
        return results
    
    def _range_search(self, node, min_price, max_price, results):
        if not node:
            return
        
        if min_price <= node.item.price <= max_price:
            results.append(node.item)
        
        if node.item.price > min_price:
            self._range_search(node.left, min_price, max_price, results)
        
        if node.item.price < max_price:
            self._range_search(node.right, min_price, max_price, results)
    
    def get_all_sorted(self):
        """Get all items sorted by price - O(n)"""
        items = []
        self._inorder(self.root, items)
        return items
    
    def _inorder(self, node, items):
        if not node:
            return
        self._inorder(node.left, items)
        items.append(node.item)
        self._inorder(node.right, items)
    
    def get_statistics(self):
        """Get BST statistics"""
        return {
            'total_items': self.size,
            'tree_height': self.get_height(self.root),
            'is_balanced': abs(self.get_balance(self.root)) <= 1
        }


class CategoryMenuManager:
    """
    Main menu manager with category-wise BSTs
    
    STRUCTURE:
    - Hash table for O(1) category lookup
    - Each category has its own BST for price filtering
    
    FEATURES:
    ✅ Filter by category + price range
    ✅ Sort by price or name
    ✅ Efficient search
    """
    
    def __init__(self):
        self.categories = {
            'main': MenuBST(),
            'beverage': MenuBST(),
            'dessert': MenuBST(),
            'appetizer': MenuBST()
        }
    
    def load_items_from_json(self, json_file_path):
        """
        Load menu items directly from JSON file
        Handles both formats: [items...] and {"items": [items...]}
        """
        if not os.path.exists(json_file_path):
            raise FileNotFoundError(f"JSON file not found: {json_file_path}")

        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Handle both JSON formats
        if isinstance(data, dict) and 'items' in data:
            items_list = data['items']
        elif isinstance(data, list):
            items_list = data
        else:
            raise ValueError("Invalid JSON format. Expected list or {'items': [...]}")
        
        self.load_items(items_list)
    
    def load_items(self, items_list):
        """Load items from a list into category BSTs"""
        for item_dict in items_list:
            item = MenuItem(item_dict)
            category = item.category.lower()
            
            # Insert into appropriate category BST
            if category in self.categories:
                self.categories[category].insert(item)
            else:
                # Default to 'main' if category not recognized
                print(f"⚠️ Unknown category '{category}' for item '{item.name}'. Adding to 'main'.")
                self.categories['main'].insert(item)
    
    def search_by_category_and_price(self, category='all', min_price=0, max_price=float('inf')):
        """
        CORE FEATURE: Category + Price filter
        
        Time Complexity:
        - Single category: O(k + log n)
        - All categories: O(k + 4*log n)
        
        Usage:
        - "Beverages under Rs. 312" → Instant!
        - "Main course Rs. 200-300" → Super fast!
        """
        results = []
        
        if category == 'all':
            for cat_bst in self.categories.values():
                results.extend(cat_bst.search_by_price_range(min_price, max_price))
        elif category in self.categories:
            results = self.categories[category].search_by_price_range(min_price, max_price)
        else:
            print(f"⚠️ Category '{category}' not found")
        
        return [item.to_dict() for item in results]
    
    def get_category_items(self, category='all', sort_by='price'):
        """
        ✅ FIXED: Get all items from specific category, sorted
        
        Ab yeh properly category filter kar raha hai!
        """
        items = []
        
        if category == 'all':
            # Get from all categories
            for cat_bst in self.categories.values():
                items.extend(cat_bst.get_all_sorted())
            
            if sort_by == 'name':
                items.sort(key=lambda x: x.name)
            # 'price' sorting already done by BST
        
        elif category in self.categories:
            # ✅ FIX: Get ONLY from specific category
            items = self.categories[category].get_all_sorted()
            
            if sort_by == 'name':
                items.sort(key=lambda x: x.name)
            # Items already sorted by price from BST
        else:
            print(f"⚠️ Category '{category}' not found")
            return []
        
        return [item.to_dict() for item in items]
    
    def get_statistics(self):
        """Get statistics for all BSTs"""
        stats = {}
        total_items = 0
        total_height = 0
        
        for cat_name, cat_bst in self.categories.items():
            cat_stats = cat_bst.get_statistics()
            stats[cat_name] = cat_stats
            total_items += cat_stats['total_items']
            total_height += cat_stats['tree_height']
        
        stats['total_items'] = total_items
        stats['average_tree_height'] = total_height / len(self.categories) if self.categories else 0
        
        return stats


# ===========================
# TESTING FUNCTION
# ===========================
def test_bst_system():
    print("="*60)
    print("BST MENU SYSTEM TEST")
    print("="*60)

    manager = CategoryMenuManager()

    # Test with your JSON format
    json_path = "data/menu.json"
    
    try:
        manager.load_items_from_json(json_path)
        print(f"✅ Loaded {manager.get_statistics()['total_items']} items")
    except Exception as e:
        print(f"❌ Error: {e}")
        return

    print("\n" + "="*60)
    print("Test 1: All Main Course Items (NO PRICE FILTER)")
    print("="*60)
    results = manager.get_category_items('main')
    print(f"Found {len(results)} main course items:")
    for item in results[:5]:  # Show first 5
        print(f"  {item['name']}: Rs. {item['price']}")

    print("\n" + "="*60)
    print("Test 2: All Beverage Items (NO PRICE FILTER)")
    print("="*60)
    results = manager.get_category_items('beverage')
    print(f"Found {len(results)} beverage items:")
    for item in results[:5]:
        print(f"  {item['name']}: Rs. {item['price']}")

    print("\n" + "="*60)
    print("Test 3: Items under Rs. 300 (ALL CATEGORIES)")
    print("="*60)
    results = manager.search_by_category_and_price('all', 0, 300)
    for item in results[:5]:
        print(f"  [{item['category']}] {item['name']}: Rs. {item['price']}")

    print("\n" + "="*60)
    print("Test 4: Main course Rs. 200-300")
    print("="*60)
    results = manager.search_by_category_and_price('main', 200, 300)
    for item in results:
        print(f"  {item['name']}: Rs. {item['price']}")

    print("\n" + "="*60)
    print("Test 5: Statistics")
    print("="*60)
    stats = manager.get_statistics()
    print(f"  Total Items: {stats['total_items']}")
    print(f"  Average Tree Height: {stats['average_tree_height']:.2f}")
    print(f"\n  Category Breakdown:")
    for cat in ['main', 'beverage', 'dessert', 'appetizer']:
        if cat in stats:
            print(f"    {cat.capitalize()}: {stats[cat]['total_items']} items (height: {stats[cat]['tree_height']})")

    print("="*60)


if __name__ == "__main__":
    test_bst_system()