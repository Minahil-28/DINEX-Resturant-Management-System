
class HashNode:

    def __init__(self, phone, customer):
        self.phone = phone           
        self.customer = customer     
        self.next = None           


class CustomerHashTable:
    """
    Custom Hash Table implementation for customer management.
    
    KEY FEATURES:
    - Hash function optimized for phone number strings
    - Separate chaining for collision resolution
    - Dynamic resizing when load factor exceeds threshold
    - O(1) average time complexity for insert, search, delete
    
    ATTRIBUTES:
    - capacity: Total number of buckets in hash table
    - size: Current number of customers stored
    - buckets: Array of linked list heads (chains)
    - load_factor_threshold: Triggers resizing (default: 0.75)
    """
    
    def __init__(self, initial_capacity=16):
        """
        Initialize hash table with given capacity.
        
        Args:
            initial_capacity (int): Starting number of buckets (power of 2 recommended)
        
        Time Complexity: O(n) where n = initial_capacity
        Space Complexity: O(n)
        """
        self.capacity = initial_capacity
        self.size = 0
        self.buckets = [None] * self.capacity  # Array of linked list heads
        self.load_factor_threshold = 0.75
        
    
    def _hash_function(self, phone):
        """
        Hash function for phone number strings.
        
        ALGORITHM:
        Uses polynomial rolling hash with prime multiplier (31).
        Formula: hash = (s[0]*31^(n-1) + s[1]*31^(n-2) + ... + s[n-1]) % capacity
        
        WHY THIS WORKS:
        - Phone numbers are numeric strings (uniform distribution)
        - Prime multiplier (31) reduces collisions
        - Modulo operation maps to valid bucket index
        - Fast computation using Horner's method
        
        Args:
            phone (str): Phone number as string
            
        Returns:
            int: Bucket index (0 to capacity-1)
            
        Time Complexity: O(k) where k = length of phone string
        Space Complexity: O(1)
        
        Example:
            phone = "03704018969"
            hash = (0*31^10 + 3*31^9 + 7*31^8 + ... + 9*31^0) % 16
        """
        hash_value = 0
        prime = 31  # Common prime for string hashing
        
        for char in phone:
            hash_value = (hash_value * prime + ord(char)) % self.capacity
            
        return hash_value
    
    
    def _get_load_factor(self):
        """
        Calculate current load factor (size/capacity).
        
        Load factor indicates how full the hash table is.
        High load factor (>0.75) increases collision probability.
        
        Returns:
            float: Current load factor
            
        Time Complexity: O(1)
        """
        return self.size / self.capacity if self.capacity > 0 else 0
    
    
    def _resize(self):
        """
        Resize hash table when load factor exceeds threshold.
        
        PROCESS:
        1. Create new table with double capacity
        2. Rehash all existing customers into new table
        3. Replace old table with new table
        
        WHY NEEDED:
        - Maintains O(1) average performance
        - Prevents long collision chains
        - Triggered when load factor > 0.75
        
        Time Complexity: O(n) where n = number of customers
        Space Complexity: O(n) for new table
        
        NOTE: Amortized O(1) insert due to infrequent resizing
        """
        print(f"🔄 Resizing hash table: {self.capacity} -> {self.capacity * 2}")
        
        old_buckets = self.buckets
        self.capacity *= 2
        self.buckets = [None] * self.capacity
        self.size = 0  # Will be recounted during rehashing
        
        # Rehash all customers
        for bucket_head in old_buckets:
            current = bucket_head
            while current:
                self.insert_customer(current.customer)
                current = current.next
    
    
    def insert_customer(self, customer):
        """
        Insert or update customer in hash table.
        
        ALGORITHM:
        1. Compute hash index from phone number
        2. Check if customer exists (update if found)
        3. Insert at head of chain if new customer
        4. Resize table if load factor exceeds threshold
        
        COLLISION HANDLING (Separate Chaining):
        - Multiple customers can map to same bucket
        - Each bucket is a linked list (chain)
        - New entries inserted at head for O(1) insertion
        
        Args:
            customer (dict): Customer object with 'phone' key
            
        Returns:
            bool: True if new insert, False if update
            
        Time Complexity: O(1) average, O(n) worst case (all collisions)
        Space Complexity: O(1)
        
        Example:
            customer = {
                'phone': '03704018969',
                'name': 'Yusra Shahid',
                'email': 'syusra841@gmail.com',
                'loyaltyPoints': 168,
                ...
            }
        """
        phone = customer.get('phone')
        if not phone:
            raise ValueError("Customer must have 'phone' field")
        
        # Check if resize needed
        if self._get_load_factor() > self.load_factor_threshold:
            self._resize()
        
        index = self._hash_function(phone)
        
        # Check if customer already exists (update case)
        current = self.buckets[index]
        while current:
            if current.phone == phone:
                current.customer = customer  # Update existing
                return False
            current = current.next
        
        # Insert new customer at head of chain
        new_node = HashNode(phone, customer)
        new_node.next = self.buckets[index]
        self.buckets[index] = new_node
        self.size += 1
        return True
    
    
    def get_customer_by_phone(self, phone):
        """
        Retrieve customer by phone number - O(1) average lookup.
        
        ALGORITHM:
        1. Compute hash index
        2. Traverse chain at that index
        3. Return customer if phone matches
        
        Args:
            phone (str): Phone number to search
            
        Returns:
            dict: Customer object if found, None otherwise
            
        Time Complexity: O(1) average, O(k) worst case
                        where k = chain length at bucket
        Space Complexity: O(1)
        
        Example:
            customer = hash_table.get_customer_by_phone("03704018969")
            if customer:
                print(customer['name'])  # "Yusra Shahid"
        """
        index = self._hash_function(phone)
        current = self.buckets[index]
        
        # Traverse chain to find matching phone
        while current:
            if current.phone == phone:
                return current.customer
            current = current.next
        
        return None  # Customer not found
    
    
    def update_customer(self, phone, updated_fields):
        """
        Update specific fields of a customer.
        
        ALGORITHM:
        1. Find customer using O(1) lookup
        2. Merge updated_fields into customer object
        3. Return updated customer
        
        Args:
            phone (str): Phone number of customer
            updated_fields (dict): Fields to update (e.g., {'loyaltyPoints': 200})
            
        Returns:
            dict: Updated customer object, or None if not found
            
        Time Complexity: O(1) average
        Space Complexity: O(1)
        
        Example:
            updated = hash_table.update_customer(
                "03704018969",
                {
                    'loyaltyPoints': 200,
                    'totalOrders': 2,
                    'totalSpent': 3000
                }
            )
        """
        customer = self.get_customer_by_phone(phone)
        if not customer:
            return None
        
        # Update fields
        customer.update(updated_fields)
        return customer
    
    
    def delete_customer(self, phone):
        """
        Delete customer from hash table.
        
        ALGORITHM:
        1. Compute hash index
        2. Traverse chain to find customer
        3. Remove node from linked list
        4. Adjust pointers to maintain chain
        
        Args:
            phone (str): Phone number of customer to delete
            
        Returns:
            bool: True if deleted, False if not found
            
        Time Complexity: O(1) average, O(k) worst case
        Space Complexity: O(1)
        """
        index = self._hash_function(phone)
        current = self.buckets[index]
        prev = None
        
        while current:
            if current.phone == phone:
                # Remove node from chain
                if prev:
                    prev.next = current.next
                else:
                    self.buckets[index] = current.next
                
                self.size -= 1
                return True
            
            prev = current
            current = current.next
        
        return False  # Customer not found
    
    
    def get_all_customers(self):
        """
        Return list of all customers in hash table.
        
        Used for bulk operations or displaying all customers.
        
        Returns:
            list: List of all customer objects
            
        Time Complexity: O(n) where n = number of customers
        Space Complexity: O(n) for result list
        """
        customers = []
        for bucket_head in self.buckets:
            current = bucket_head
            while current:
                customers.append(current.customer)
                current = current.next
        return customers
    
    
    def get_statistics(self):
        """
        Get hash table performance statistics.
        
        Returns:
            dict: Statistics including size, capacity, load factor,
                  collision chains, and distribution
        """
        # Count chains and find longest chain
        chain_lengths = []
        empty_buckets = 0
        
        for bucket_head in self.buckets:
            if bucket_head is None:
                empty_buckets += 1
                chain_lengths.append(0)
            else:
                length = 0
                current = bucket_head
                while current:
                    length += 1
                    current = current.next
                chain_lengths.append(length)
        
        return {
            'total_customers': self.size,
            'capacity': self.capacity,
            'load_factor': self._get_load_factor(),
            'empty_buckets': empty_buckets,
            'longest_chain': max(chain_lengths) if chain_lengths else 0,
            'average_chain_length': sum(chain_lengths) / len(chain_lengths) if chain_lengths else 0,
            'collision_rate': (self.size - (self.capacity - empty_buckets)) / self.size if self.size > 0 else 0
        }
    
    
    def __len__(self):
        """Return number of customers in hash table."""
        return self.size
    
    
    def __contains__(self, phone):
        """Check if customer exists using 'in' operator."""
        return self.get_customer_by_phone(phone) is not None


# ===========================
# COMPLEXITY ANALYSIS
# ===========================
"""
HASH TABLE TIME COMPLEXITY:

Operation          | Average Case | Worst Case | Notes
-------------------|--------------|------------|------------------------
Insert             | O(1)         | O(n)       | Amortized O(1) with resizing
Search (Lookup)    | O(1)         | O(k)       | k = chain length
Update             | O(1)         | O(k)       | Same as search
Delete             | O(1)         | O(k)       | Same as search
Resize             | O(n)         | O(n)       | Infrequent (amortized O(1))

SPACE COMPLEXITY:
- Hash Table: O(n) where n = number of customers
- Each Node: O(1) for phone + customer reference
- Total Space: O(n) for n customers + O(m) for m buckets

COLLISION HANDLING - SEPARATE CHAINING:
- Each bucket contains a linked list
- Multiple customers can hash to same bucket
- Average chain length = load_factor
- Good hash function keeps chains short (1-2 nodes)

LOAD FACTOR:
- α = n/m (customers/buckets)
- Target: α ≤ 0.75 for optimal performance
- When α > 0.75: resize to maintain O(1) operations

WHY O(1) AVERAGE CASE:
1. Good hash function distributes keys uniformly
2. Load factor kept low (< 0.75)
3. Short chains (1-2 nodes average)
4. Direct array access + short traversal = constant time

WORST CASE O(n):
- All keys hash to same bucket (extremely rare)
- Single long chain of n elements
- Prevented by: good hash function + dynamic resizing
"""


# ===========================
# EXAMPLE USAGE & DEMONSTRATION
# ===========================
def demonstrate_hash_table():
    """
    Demonstrate hash table operations with sample customer data.
    Shows O(1) performance for typical operations.
    """
    print("=" * 60)
    print("CUSTOMER HASH TABLE - DEMONSTRATION")
    print("=" * 60)
    
    # Initialize hash table
    customer_ht = CustomerHashTable(initial_capacity=8)
    print(f"\n✅ Hash table initialized with capacity: {customer_ht.capacity}")
    
    # Sample customers from your JSON
    customers = [
        {
            "phone": "03704018969",
            "name": "Yusra Shahid",
            "email": "syusra841@gmail.com",
            "address": "",
            "orderHistory": ["ORD0004"],
            "loyaltyPoints": 168,
            "preferences": [],
            "isVIP": False,
            "totalOrders": 1,
            "totalSpent": 1680
        },
        {
            "phone": "03230476914",
            "name": "Yusra Shahid",
            "email": "syusra84@gmail.com",
            "address": "",
            "orderHistory": [],
            "loyaltyPoints": 0,
            "preferences": [],
            "isVIP": False,
            "totalOrders": 0,
            "totalSpent": 0
        },
        {
            "phone": "03015920315",
            "name": "Minahil Mehmood",
            "email": "minahilmehmood315@gmail.com",
            "address": "",
            "orderHistory": [],
            "loyaltyPoints": 0,
            "preferences": [],
            "isVIP": False,
            "totalOrders": 0,
            "totalSpent": 0
        }
    ]
    
    # INSERT OPERATION - O(1)
    print("\n" + "="*60)
    print("OPERATION: INSERT CUSTOMERS")
    print("="*60)
    for customer in customers:
        customer_ht.insert_customer(customer)
        print(f"✅ Inserted: {customer['name']} ({customer['phone']})")
    
    print(f"\n📊 Total customers in hash table: {len(customer_ht)}")
    
    # SEARCH OPERATION - O(1)
    print("\n" + "="*60)
    print("OPERATION: O(1) CUSTOMER LOOKUP")
    print("="*60)
    search_phone = "03704018969"
    customer = customer_ht.get_customer_by_phone(search_phone)
    if customer:
        print(f"🔍 Found customer: {customer['name']}")
        print(f"   Email: {customer['email']}")
        print(f"   Loyalty Points: {customer['loyaltyPoints']}")
        print(f"   Total Orders: {customer['totalOrders']}")
    
    # UPDATE OPERATION - O(1)
    print("\n" + "="*60)
    print("OPERATION: UPDATE CUSTOMER (After Order)")
    print("="*60)
    updated = customer_ht.update_customer(
        "03704018969",
        {
            'orderHistory': ["ORD0004", "ORD0005"],
            'loyaltyPoints': 268,
            'totalOrders': 2,
            'totalSpent': 2680
        }
    )
    if updated:
        print(f"✅ Updated: {updated['name']}")
        print(f"   New Loyalty Points: {updated['loyaltyPoints']}")
        print(f"   New Total Orders: {updated['totalOrders']}")
    
    # STATISTICS
    print("\n" + "="*60)
    print("HASH TABLE STATISTICS")
    print("="*60)
    stats = customer_ht.get_statistics()
    print(f"📈 Total Customers: {stats['total_customers']}")
    print(f"📦 Capacity: {stats['capacity']}")
    print(f"⚖️  Load Factor: {stats['load_factor']:.2f}")
    print(f"🔗 Longest Chain: {stats['longest_chain']}")
    print(f"📊 Average Chain Length: {stats['average_chain_length']:.2f}")
    print(f"⚠️  Collision Rate: {stats['collision_rate']:.2%}")
    
    # DELETE OPERATION - O(1)
    print("\n" + "="*60)
    print("OPERATION: DELETE CUSTOMER")
    print("="*60)
    deleted = customer_ht.delete_customer("03230476914")
    if deleted:
        print(f"✅ Deleted customer: 03230476914")
        print(f"📊 Remaining customers: {len(customer_ht)}")
    
    print("\n" + "="*60)
    print("DEMONSTRATION COMPLETE")
    print("="*60)


if __name__ == "__main__":
    demonstrate_hash_table()