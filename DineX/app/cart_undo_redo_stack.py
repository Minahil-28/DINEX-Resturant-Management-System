
from datetime import datetime
from typing import Dict, List, Optional, Any

class CartActionStack:
    """Enhanced stack implementation for all cart modifications"""
    
    def __init__(self):
        self.undo_stack: List[Dict[str, Any]] = []
        self.redo_stack: List[Dict[str, Any]] = []
        print("✅ CartActionStack initialized")
    
    def push_action(self, action_type: str, item_data: Dict[str, Any], 
                old_quantity: int = None, new_quantity: int = None) -> None:
        """Push any cart modification action to undo stack"""
        
        action = {
            'type': action_type,
            'item_id': item_data['id'],
            'item_name': item_data['name'],
            'quantity': item_data.get('quantity', 1),
            'price': item_data['price'],
            'image': item_data.get('image', ''),
            'position_in_cart': item_data.get('position_in_cart', 0),
            'timestamp': datetime.now().isoformat()
        }
        
        # Add quantity change info
        if action_type in ['increase', 'decrease']:
            action['old_quantity'] = old_quantity
            action['new_quantity'] = new_quantity
        
        self.undo_stack.append(action)
        self.redo_stack.clear()  # Clear redo on new action ← CRITICAL!
        
        print(f"✅ ACTION PUSHED: {action_type.upper()} - {action['item_name']}")
        print(f"   Undo stack: {len(self.undo_stack)}, Redo stack: {len(self.redo_stack)}")
    

    
    def undo(self) -> Optional[Dict[str, Any]]:
        """Pop from undo stack and push to redo stack"""
        if not self.undo_stack:
            print("⚠️ Undo stack is empty")
            return None
        
        action = self.undo_stack.pop()
        self.redo_stack.append(action)
        
        print(f"↩️ Undo: {action['type']} on {action['item_name']}")
        print(f"   Undo stack: {len(self.undo_stack)}, Redo stack: {len(self.redo_stack)}")
        
        return action
    
    def redo(self) -> Optional[Dict[str, Any]]:
        """Pop from redo stack and push to undo stack"""
        if not self.redo_stack:
            print("⚠️ Redo stack is empty")
            return None
        
        action = self.redo_stack.pop()
        self.undo_stack.append(action)
        
        print(f"↪️ Redo: {action['type']} on {action['item_name']}")
        print(f"   Undo stack: {len(self.undo_stack)}, Redo stack: {len(self.redo_stack)}")
        
        return action
    
    def clear(self) -> None:
        """Clear both stacks (call after checkout)"""
        self.undo_stack.clear()
        self.redo_stack.clear()
        print("🗑️ Stacks cleared (checkout completed)")
    
    def push_delete_action(self, item_data: Dict[str, Any]) -> None:
        """Legacy method - calls push_action with 'delete' type"""
        self.push_action('delete', item_data)
    
    def can_undo(self) -> bool:
        """Check if undo is available"""
        return len(self.undo_stack) > 0
    
    def can_redo(self) -> bool:
        """Check if redo is available"""
        return len(self.redo_stack) > 0
    
    def get_stack_status(self) -> Dict[str, Any]:
        """Get current stack status for UI"""
        last_undo = self.undo_stack[-1] if self.undo_stack else None
        last_redo = self.redo_stack[-1] if self.redo_stack else None
        
        status = {
            'can_undo': self.can_undo(),
            'can_redo': self.can_redo(),
            'undo_count': len(self.undo_stack),
            'redo_count': len(self.redo_stack),
            'last_undo_action': f"{last_undo['type']}: {last_undo['item_name']}" if last_undo else None,
            'last_redo_action': f"{last_redo['type']}: {last_redo['item_name']}" if last_redo else None
        }
        
        print(f"\n📊 STACK STATUS:")
        print(f"   Can Undo: {status['can_undo']} (Stack: {status['undo_count']})")
        print(f"   Can Redo: {status['can_redo']} (Stack: {status['redo_count']})")
        if last_undo:
            print(f"   Last Action: {status['last_undo_action']}")
        
        return status


# Global stack instance (in-memory)
cart_stack = CartActionStack()


def handle_cart_delete(cart: List[Dict], item_id: int) -> Dict[str, Any]:
    """
    Handle cart item deletion with undo tracking
    """
    # Find item and its position
    item_position = None
    deleted_item = None
    
    for i, item in enumerate(cart):
        if item['id'] == item_id:
            item_position = i
            deleted_item = item.copy()
            deleted_item['position_in_cart'] = i
            break
    
    if deleted_item is None:
        return {
            'success': False,
            'message': 'Item not found in cart'
        }
    
    # Push to undo stack BEFORE deleting
    cart_stack.push_action('delete', deleted_item)
    
    # Remove from cart
    cart.pop(item_position)
    
    return {
        'success': True,
        'message': f'{deleted_item["name"]} removed from cart',
        'cart': cart,
        'stack_status': cart_stack.get_stack_status()
    }


def handle_quantity_change(cart: List[Dict], item_id: int, change: int) -> Dict[str, Any]:
    """
    Handle quantity increase/decrease with undo tracking
    
    Args:
        cart: Current cart
        item_id: Item ID
        change: +1 for increase, -1 for decrease
    """
    # Find item
    item = None
    for i in cart:
        if i['id'] == item_id:
            item = i
            break
    
    if not item:
        return {
            'success': False,
            'message': 'Item not found'
        }
    
    old_quantity = item['quantity']
    new_quantity = old_quantity + change
    
    # Can't go below 1
    if new_quantity < 1:
        return {
            'success': False,
            'message': 'Quantity cannot be less than 1'
        }
    
    # Determine action type
    action_type = 'increase' if change > 0 else 'decrease'
    
    # Create snapshot for undo
    item_snapshot = item.copy()
    item_snapshot['old_quantity'] = old_quantity
    item_snapshot['new_quantity'] = new_quantity
    
    # Push to undo stack
    cart_stack.push_action(action_type, item_snapshot, old_quantity, new_quantity)
    
    # Update quantity
    item['quantity'] = new_quantity
    
    return {
        'success': True,
        'message': f'Quantity updated: {old_quantity} → {new_quantity}',
        'cart': cart,
        'stack_status': cart_stack.get_stack_status()
    }


def handle_undo(cart: List[Dict]) -> Dict[str, Any]:
    """
    Restore/reverse last action
    """
    action = cart_stack.undo()
    
    if action is None:
        return {
            'success': False,
            'message': 'Nothing to undo',
            'cart': cart,
            'stack_status': cart_stack.get_stack_status()
        }
    
    action_type = action['type']
    
    # UNDO DELETE: Restore item
    if action_type == 'delete':
        restored_item = {
            'id': action['item_id'],
            'name': action['item_name'],
            'quantity': action['quantity'],
            'price': action['price'],
            'image': action['image']
        }
        
        position = min(action['position_in_cart'], len(cart))
        cart.insert(position, restored_item)
        
        return {
            'success': True,
            'message': f'{action["item_name"]} restored to cart',
            'cart': cart,
            'restored_item': action['item_name'],
            'stack_status': cart_stack.get_stack_status()
        }
    # UNDO ADD: Remove the item that was last added
    if action_type == 'add':
        for i, item in enumerate(cart):
            if item['id'] == action['item_id']:
                # If quantities differ, reduce by action quantity, else remove
                if item.get('quantity', 1) > action.get('quantity', 1):
                    item['quantity'] = item.get('quantity', 1) - action.get('quantity', 1)
                else:
                    cart.pop(i)
                break

        return {
            'success': True,
            'message': f'{action["item_name"]} add undone',
            'cart': cart,
            'stack_status': cart_stack.get_stack_status()
        }
    
    # UNDO QUANTITY CHANGE: Revert to old quantity
    elif action_type in ['increase', 'decrease']:
        for item in cart:
            if item['id'] == action['item_id']:
                item['quantity'] = action['old_quantity']
                break
        
        return {
            'success': True,
            'message': f'{action["item_name"]} quantity reverted to {action["old_quantity"]}',
            'cart': cart,
            'reverted_quantity': action['old_quantity'],
            'stack_status': cart_stack.get_stack_status()
        }
    
    return {
        'success': False,
        'message': 'Unknown action type',
        'cart': cart,
        'stack_status': cart_stack.get_stack_status()
    }


def handle_redo(cart: List[Dict]) -> Dict[str, Any]:
    """
    Re-apply last undone action
    """
    action = cart_stack.redo()
    
    if action is None:
        return {
            'success': False,
            'message': 'Nothing to redo',
            'cart': cart,
            'stack_status': cart_stack.get_stack_status()
        }
    
    action_type = action['type']
    
    # REDO DELETE: Remove item again
    if action_type == 'delete':
        for i, item in enumerate(cart):
            if item['id'] == action['item_id']:
                cart.pop(i)
                break
        
        return {
            'success': True,
            'message': f'{action["item_name"]} removed again',
            'cart': cart,
            'deleted_item': action['item_name'],
            'stack_status': cart_stack.get_stack_status()
        }
    # REDO ADD: Re-insert or increase quantity
    if action_type == 'add':
        # If item exists, increase quantity, else insert at recorded position
        found = False
        for item in cart:
            if item['id'] == action['item_id']:
                item['quantity'] = item.get('quantity', 1) + action.get('quantity', 1)
                found = True
                break

        if not found:
            restored_item = {
                'id': action['item_id'],
                'name': action['item_name'],
                'quantity': action.get('quantity', 1),
                'price': action['price'],
                'image': action['image']
            }
            position = min(action.get('position_in_cart', len(cart)), len(cart))
            cart.insert(position, restored_item)

        return {
            'success': True,
            'message': f'{action["item_name"]} re-added',
            'cart': cart,
            'stack_status': cart_stack.get_stack_status()
        }
    
    # REDO QUANTITY CHANGE: Re-apply new quantity
    elif action_type in ['increase', 'decrease']:
        for item in cart:
            if item['id'] == action['item_id']:
                item['quantity'] = action['new_quantity']
                break
        
        return {
            'success': True,
            'message': f'{action["item_name"]} quantity changed to {action["new_quantity"]}',
            'cart': cart,
            'new_quantity': action['new_quantity'],
            'stack_status': cart_stack.get_stack_status()
        }
    
    return {
        'success': False,
        'message': 'Unknown action type',
        'cart': cart,
        'stack_status': cart_stack.get_stack_status()
    }


def clear_stack_on_checkout():
    """Clear undo/redo stacks after order is placed"""
    cart_stack.clear()


# Test cases
if __name__ == "__main__":
    print("=== Testing Enhanced Cart Undo/Redo Stack ===\n")
    
    # Sample cart
    test_cart = [
        {'id': 1, 'name': 'Burger', 'quantity': 2, 'price': 500, 'image': 'burger.jpg'},
        {'id': 2, 'name': 'Pizza', 'quantity': 1, 'price': 800, 'image': 'pizza.jpg'}
    ]
    
    print(f"Initial cart: {[(i['name'], i['quantity']) for i in test_cart]}\n")
    
    # Test 1: Increase quantity
    print("Test 1: Increase Burger quantity (2 → 3)")
    result = handle_quantity_change(test_cart, 1, 1)
    # Ensure we always keep a valid cart reference even if handler returns failure
    test_cart = result.get('cart', test_cart)
    print(f"Cart: {[(i['name'], i['quantity']) for i in test_cart]}")
    print(f"Stack: {result.get('stack_status')}\n")
    
    # Test 2: Decrease quantity
    print("Test 2: Decrease Pizza quantity (1 → 0... should fail)")
    result = handle_quantity_change(test_cart, 2, -1)
    test_cart = result.get('cart', test_cart)
    print(f"Success: {result['success']}, Message: {result['message']}\n")
    
    # Test 3: Delete item
    print("Test 3: Delete Pizza")
    result = handle_cart_delete(test_cart, 2)
    test_cart = result.get('cart', test_cart)
    print(f"Cart: {[(i['name'], i['quantity']) for i in test_cart]}")
    print(f"Stack: {result.get('stack_status')}\n")
    
    # Test 4: Undo delete
    print("Test 4: Undo (restore Pizza)")
    result = handle_undo(test_cart)
    test_cart = result.get('cart', test_cart)
    print(f"Cart: {[(i['name'], i['quantity']) for i in test_cart]}")
    print(f"Stack: {result.get('stack_status')}\n")
    
    # Test 5: Undo quantity change
    print("Test 5: Undo (revert Burger quantity 3 → 2)")
    result = handle_undo(test_cart)
    test_cart = result.get('cart', test_cart)
    print(f"Cart: {[(i['name'], i['quantity']) for i in test_cart]}")
    print(f"Stack: {result.get('stack_status')}\n")
    
    # Test 6: Redo quantity change
    print("Test 6: Redo (re-apply Burger quantity 2 → 3)")
    result = handle_redo(test_cart)
    test_cart = result.get('cart', test_cart)
    print(f"Cart: {[(i['name'], i['quantity']) for i in test_cart]}")
    print(f"Stack: {result.get('stack_status')}\n")
    
    print("=== Tests Complete ===")