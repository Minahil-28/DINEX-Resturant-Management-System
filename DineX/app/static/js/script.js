// Global Variables
let cart = [];
let menuItems = [];
let currentCategory = 'all';
let currentUser = JSON.parse(localStorage.getItem('dinex_user'));
let currentSortBy = 'name';
let currentMaxPrice = null;
let currentMinPrice = null;
let currentSearchQuery = '';
let isProcessingOrder = false;
let stackStatus = {
    can_undo: false,
    can_redo: false,
    undo_count: 0,
    redo_count: 0
};

document.addEventListener('DOMContentLoaded', async function() {

    checkUserSession();

    await loadCart();
    await fetchStackStatus();

    initializeApp();
    setupMenuEventListeners();
    loadMenuItems();
    initializeAnimations();
    updateNavbar();
    updateOrderFormCart();
    
    console.log('✅ App initialized');
});


// ===========================
// CART BACKEND INTEGRATION
// ===========================
async function loadCartFromBackend() {
    try {
        const response = await fetch('/api/cart');
        const data = await response.json();
        
        if (data.success) {
            cart = data.cart || [];
            updateCartCount();
            console.log('✅ Cart loaded from backend:', cart);
        }
    } catch (error) {
        console.error('❌ Failed to load cart:', error);
    }
}

function updateUndoRedoButtons() {
    const undoBtn = document.getElementById('undoBtn');
    const redoBtn = document.getElementById('redoBtn');
    
    console.log('🔄 Updating undo/redo buttons:', stackStatus);
    
    if (undoBtn) {
        undoBtn.disabled = !stackStatus.can_undo;
        undoBtn.classList.toggle('disabled', !stackStatus.can_undo);
  
        if (stackStatus.can_undo && stackStatus.last_undo_action) {
            undoBtn.title = `Undo: ${stackStatus.last_undo_action}`;
        } else {
            undoBtn.title = 'Nothing to undo';
        }
        
        if (stackStatus.can_undo) {
            undoBtn.style.opacity = '1';
            undoBtn.style.cursor = 'pointer';
        } else {
            undoBtn.style.opacity = '0.5';
            undoBtn.style.cursor = 'not-allowed';
        }
    }
    
    if (redoBtn) {
        redoBtn.disabled = !stackStatus.can_redo;
        redoBtn.classList.toggle('disabled', !stackStatus.can_redo);
        
        if (stackStatus.can_redo && stackStatus.last_redo_action) {
            redoBtn.title = `Redo: ${stackStatus.last_redo_action}`;
        } else {
            redoBtn.title = 'Nothing to redo';
        }

        if (stackStatus.can_redo) {
            redoBtn.style.opacity = '1';
            redoBtn.style.cursor = 'pointer';
        } else {
            redoBtn.style.opacity = '0.5';
            redoBtn.style.cursor = 'not-allowed';
        }
    }
}

async function fetchStackStatus() {
    try {
        const response = await fetch('/api/cart/stack-status');
        const data = await response.json();
        
        if (data.success) {
            stackStatus = data.stack_status;
            updateUndoRedoButtons();
        }
    } catch (error) {
        console.error('Failed to fetch stack status:', error);
    }
}

async function refreshStackStatus() {
    try {
        const response = await fetch('/api/cart/stack-status');
        const data = await response.json();
        
        if (data.success) {
            stackStatus = data.stack_status;
            updateUndoRedoButtons();
            console.log('✅ Stack status refreshed');
        }
    } catch (error) {
        console.error('Failed to fetch stack status:', error);
    }
}

async function undoCartDelete() {
    if (!stackStatus.can_undo) {
        showToast('Nothing to undo', 'error');
        return;
    }
    
    try {
        const undoBtn = document.getElementById('undoBtn');
        if (undoBtn) {
            undoBtn.disabled = true;
            undoBtn.innerHTML = '<span class="btn-icon">⏳</span><span>Undoing...</span>';
        }
        
        const response = await fetch('/api/cart/undo', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        const data = await response.json();
        
        if (data.success) {
           
            cart = data.cart || [];
            localStorage.setItem('dinex_cart', JSON.stringify(cart));
            
            
            stackStatus = data.stack_status;
            
        
            updateCartCount();
            updateCartDisplay();
            updateOrderFormCart();
            updateUndoRedoButtons();
            

            let message = '✅ Undo successful';
            if (data.restored_item) {
                message = `✅ ${data.restored_item} restored`;
            } else if (data.reverted_quantity !== undefined) {
                message = `✅ Quantity reverted to ${data.reverted_quantity}`;
            }
            
            showToast(message, 'success');
        } else {
            showToast(data.message || 'Undo failed', 'error');
        }
        
    } catch (error) {
        console.error('❌ Undo error:', error);
        showToast('Failed to undo', 'error');
    } finally {
        const undoBtn = document.getElementById('undoBtn');
        if (undoBtn) {
            undoBtn.innerHTML = '<span class="btn-icon">↩️</span><span>Undo</span>';
        }
     
        await fetchStackStatus();
    }
}



async function redoCartDelete() {
    if (!stackStatus.can_redo) {
        showToast('Nothing to redo', 'error');
        return;
    }
    
    try {
        const redoBtn = document.getElementById('redoBtn');
        if (redoBtn) {
            redoBtn.disabled = true;
            redoBtn.innerHTML = '<span class="btn-icon">⏳</span><span>Redoing...</span>';
        }
        
        const response = await fetch('/api/cart/redo', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        const data = await response.json();
        
        if (data.success) {
      
            cart = data.cart || [];
            localStorage.setItem('dinex_cart', JSON.stringify(cart));
            
        
            stackStatus = data.stack_status;
            
  
            updateCartCount();
            updateCartDisplay();
            updateOrderFormCart();
            updateUndoRedoButtons();
            
          
            let message = '✅ Redo successful';
            if (data.deleted_item) {
                message = `🗑️ ${data.deleted_item} removed again`;
            } else if (data.new_quantity !== undefined) {
                message = `✅ Quantity changed to ${data.new_quantity}`;
            }
            
            showToast(message, 'success');
        } else {
            showToast(data.message || 'Redo failed', 'error');
        }
        
    } catch (error) {
        console.error('❌ Redo error:', error);
        showToast('Failed to redo', 'error');
    } finally {
        const redoBtn = document.getElementById('redoBtn');
        if (redoBtn) {
            redoBtn.innerHTML = '<span class="btn-icon">↪️</span><span>Redo</span>';
        }
  
        await fetchStackStatus();
    }
}


function addUndoRedoButtons() {
    
    if (document.getElementById('undoRedoControls')) {
        return;
    }
    
    const cartHeader = document.querySelector('#cartSidebar .cart-header');
    if (!cartHeader) {
        console.error('Cart header not found');
        return;
    }
    
    const controls = document.createElement('div');
    controls.id = 'undoRedoControls';
    controls.className = 'undo-redo-controls';
    controls.innerHTML = `
        <button id="undoBtn" class="undo-redo-btn undo-btn glass-btn" onclick="undoCartDelete()" disabled>
            <span class="btn-icon">↩️</span>
            <span>Undo</span>
        </button>
        <button id="redoBtn" class="undo-redo-btn redo-btn glass-btn" onclick="redoCartDelete()" disabled>
            <span class="btn-icon">↪️</span>
            <span>Redo</span>
        </button>
    `;
    
   
    const closeBtn = cartHeader.querySelector('#closeCartBtn');
    if (closeBtn) {
        cartHeader.insertBefore(controls, closeBtn);
    } else {
        cartHeader.appendChild(controls);
    }
    
    console.log('✅ Undo/Redo buttons added to cart');
}

function initUndoRedo() {
    console.log('🚀 Initializing undo/redo system...');
    
    
    addUndoRedoButtons();

    fetchStackStatus();
  
    setInterval(() => {
        const cartSidebar = document.getElementById('cartSidebar');
        if (cartSidebar && cartSidebar.classList.contains('open')) {
            refreshStackStatus();
        }
    }, 2000);
    
    console.log('✅ Undo/Redo system initialized');
}


if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
        
        setTimeout(initUndoRedo, 500);
    });
} else {
 
    setTimeout(initUndoRedo, 500);
}


// ===========================
// USER SESSION MANAGEMENT
// ===========================

function openProfilePanel() {
    const panel = document.getElementById('profilePanel');
    if (panel) panel.classList.add('show');
}

function closeProfile() {
    const panel = document.getElementById('profilePanel');
    if (panel) panel.classList.remove('show');
}


// ===========================
// CLOSE PROFILE PANEL
// ===========================
function closeProfile() {
    const panel = document.getElementById('profilePanel');
    if (panel) {
        panel.classList.remove('show');
    }
}

function toggleProfile() {
    const box = document.getElementById('profileBox');
    if (!box) return;
    box.classList.toggle('show');
}

function logout() {
    localStorage.removeItem('dinex_user');
    currentUser = null;

    const box = document.getElementById('profileBox');
    if (box) box.remove();

    showToast('Logged out successfully! 👋', 'success');
    setTimeout(() => window.location.reload(), 1000);
}
function handleLogout() {

    cart = [];
    localStorage.removeItem('dinex_cart');
    localStorage.removeItem('dinex_user');
    currentUser = null;
    
    updateCartCount();
    
    showToast('Logged out successfully! 👋', 'success');
    setTimeout(() => window.location.reload(), 1000);
}


// ===========================
// INITIALIZATION
// ===========================
function initializeApp() {
    window.addEventListener('scroll', handleNavbarScroll);
    
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', smoothScrollTo);
    });
    
    setupScrollAnimations();
}

// ===========================
// NAVBAR FUNCTIONS
// ===========================
function handleNavbarScroll() {
    const navbar = document.getElementById('navbar');
    if (window.scrollY > 50) {
        navbar.classList.add('scrolled');
    } else {
        navbar.classList.remove('scrolled');
    }
}

function smoothScrollTo(e) {
    e.preventDefault();
    const targetId = this.getAttribute('href');
    const targetSection = document.querySelector(targetId);
    
    if (targetSection) {
        const offsetTop = targetSection.offsetTop - 80;
        window.scrollTo({
            top: offsetTop,
            behavior: 'smooth'
        });
    }
}

// ===========================
// EVENT LISTENERS SETUP
// ===========================

function setupMenuEventListeners() {
 
    const filterBtns = document.querySelectorAll('.filter-btn');
    filterBtns.forEach(btn => {
        btn.addEventListener('click', async function() {
           
            filterBtns.forEach(b => b.classList.remove('active'));
           
            this.classList.add('active');
            
            currentCategory = this.dataset.category;
            
            console.log(`🔍 Category selected: ${currentCategory}`);
          
            await loadMenuItemsFiltered();
        });
    });

    const searchInput = document.getElementById('menuSearch');
    if (searchInput) {
        searchInput.addEventListener('input', debounce(async (e) => {
            currentSearchQuery = e.target.value.trim();
            if (currentSearchQuery.length === 0) {
                await loadMenuItemsFiltered();
            } else {
                searchInCurrentMenu(currentSearchQuery);
            }
        }, 300));
    }

    document.addEventListener('click', function (e) {
        if (e.target.closest('.btn-cart')) {
            e.preventDefault();
            openCartModal();
        }
    });

    const viewMenuBtn = document.querySelector('.btn-secondary');
    if (viewMenuBtn) {
        viewMenuBtn.addEventListener('click', function(e) {
            e.preventDefault();
            scrollToMenu();
        });
    }

    const orderNowBtn = document.querySelector('.btn-primary');
    if (orderNowBtn) {
        orderNowBtn.addEventListener('click', function(e) {
            e.preventDefault();
            scrollToMenu();
        });
    }

    const sortSelect = document.getElementById('sortMenu');
    if (sortSelect) {
        sortSelect.addEventListener('change', async (e) => {
            currentSortBy = e.target.value;
            sortCurrentMenu(currentSortBy);
        });
    }

    const priceFilter = document.getElementById('priceFilter');
    const priceValue = document.getElementById('priceValue');
    if (priceFilter) {
        priceFilter.addEventListener('input', (e) => {
            const value = e.target.value;
            if (priceValue) {
                priceValue.textContent = `Rs. ${value}`;
            }
        });
        
        priceFilter.addEventListener('change', debounce(async (e) => {
            currentMaxPrice = parseInt(e.target.value);
            console.log(`💰 Price filter: Max Rs. ${currentMaxPrice}`);
            await loadMenuItemsFiltered();
        }, 500));
    }
}


// ===========================
// MENU DATA & DISPLAY
// ===========================
async function loadMenuByCategory(category = 'all') {
    try {
        const menuGrid = document.getElementById('menuGrid');
        if (!menuGrid) return;
        
        menuGrid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 2rem;">Loading...</div>';
        
        let url = `/menu?category=${category}`;
        
        if (currentMaxPrice && currentMaxPrice < 1000) {
            url += `&max_price=${currentMaxPrice}`;
        }
        
        console.log(`📡 Fetching: ${url}`);
        
        const response = await fetch(url);
        
        if (!response.ok) {
            throw new Error('Failed to load menu');
        }
        
        const html = await response.text();
        
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        const newMenuGrid = doc.getElementById('menuGrid');
        
        if (newMenuGrid && newMenuGrid.children.length > 0) {
            menuGrid.innerHTML = newMenuGrid.innerHTML;
            console.log(`✅ Loaded ${menuGrid.children.length} items for category: ${category}`);
            
            attachAddToCartListeners();
        } else {
            menuGrid.innerHTML = `
                <div style="grid-column: 1/-1; text-align: center; padding: 3rem; color: var(--text-secondary);">
                    <span style="font-size: 3rem; display: block; margin-bottom: 1rem;">🍽️</span>
                    <p style="font-size: 1.2rem;">No items found in ${category === 'all' ? 'menu' : category}</p>
                </div>
            `;
        }
        
    } catch (error) {
        console.error('❌ Menu load error:', error);
        const menuGrid = document.getElementById('menuGrid');
        if (menuGrid) {
            menuGrid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 2rem; color: red;">Failed to load menu</div>';
        }
    }
}
async function loadMenuItemsFiltered() {
    try {
        const params = new URLSearchParams();
        
        if (currentCategory && currentCategory !== 'all') {
            params.append('category', currentCategory);
        }
        
        if (currentMaxPrice && currentMaxPrice < 1000) {
            params.append('max_price', currentMaxPrice);
        }
        
        if (currentSortBy) {
            params.append('sort', currentSortBy);
        }
        
        const url = `/api/menu/filter?${params.toString()}`;
        console.log(`📡 Fetching filtered menu: ${url}`);
        
        const menuGrid = document.getElementById('menuGrid');
        if (menuGrid) {
            menuGrid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 2rem;">Loading...</div>';
        }
        
        const response = await fetch(url);
        
        if (!response.ok) {
            throw new Error('Failed to load menu');
        }
        
        const data = await response.json();
        
        if (data.success) {
            menuItems = data.items;
            console.log(`✅ Loaded ${data.items.length} items for category: ${currentCategory}`);
            
            displayMenuItems(menuItems);
        } else {
            throw new Error(data.message || 'Failed to load menu');
        }
        
    } catch (err) {
        console.error('❌ Error loading filtered menu:', err);
        const menuGrid = document.getElementById('menuGrid');
        if (menuGrid) {
            menuGrid.innerHTML = `
                <div style="grid-column: 1/-1; text-align: center; padding: 3rem; color: red;">
                    <p>Failed to load menu items</p>
                    <small>${err.message}</small>
                </div>
            `;
        }
    }
}

function searchInCurrentMenu(query) {
    const menuGrid = document.getElementById('menuGrid');
    if (!menuGrid) return;
    
    query = query.toLowerCase();
    const menuCards = menuGrid.querySelectorAll('.menu-item');
    let visibleCount = 0;
    
    menuCards.forEach(card => {
        const itemName = card.querySelector('.menu-item-name')?.textContent.toLowerCase() || '';
        const itemDesc = card.querySelector('.menu-item-description')?.textContent.toLowerCase() || '';
        
        if (itemName.includes(query) || itemDesc.includes(query)) {
            card.style.display = 'flex';
            visibleCount++;
        } else {
            card.style.display = 'none';
        }
    });
    
    console.log(`🔍 Search "${query}": ${visibleCount} items found`);
    
    if (visibleCount === 0) {
        menuGrid.innerHTML = `
            <div style="grid-column: 1/-1; text-align: center; padding: 3rem;">
                <span style="font-size: 3rem;">🔍</span>
                <p>No items found for "${query}"</p>
                <small>Try a different search term</small>
            </div>
        `;
    }
}

function sortCurrentMenu(sortBy) {
    const menuGrid = document.getElementById('menuGrid');
    if (!menuGrid) return;
    
    const menuCards = Array.from(menuGrid.querySelectorAll('.menu-item'));
    
    menuCards.sort((a, b) => {
        if (sortBy === 'price-low') {
            const priceA = parseFloat(a.querySelector('.menu-item-price')?.textContent.replace('Rs. ', '') || 0);
            const priceB = parseFloat(b.querySelector('.menu-item-price')?.textContent.replace('Rs. ', '') || 0);
            return priceA - priceB;
        } else if (sortBy === 'price-high') {
            const priceA = parseFloat(a.querySelector('.menu-item-price')?.textContent.replace('Rs. ', '') || 0);
            const priceB = parseFloat(b.querySelector('.menu-item-price')?.textContent.replace('Rs. ', '') || 0);
            return priceB - priceA;
        } else if (sortBy === 'name') {
            const nameA = a.querySelector('.menu-item-name')?.textContent || '';
            const nameB = b.querySelector('.menu-item-name')?.textContent || '';
            return nameA.localeCompare(nameB);
        } else if (sortBy === 'popular') {
            const ratingA = parseFloat(a.dataset.rating || 0);
            const ratingB = parseFloat(b.dataset.rating || 0);
            return ratingB - ratingA;
        }
        return 0;
    });
    
    menuGrid.innerHTML = '';
    menuCards.forEach(card => menuGrid.appendChild(card));
    
    console.log(`📊 Sorted by: ${sortBy}`);
}

function attachAddToCartListeners() {
    const addToCartButtons = document.querySelectorAll('.add-to-cart-btn');
    
    addToCartButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            const onclickAttr = this.getAttribute('onclick');
            if (onclickAttr) {
                const match = onclickAttr.match(/addToCart\((\d+)\)/);
                if (match) {
                    const itemId = parseInt(match[1]);
                    addToCart(itemId);
                }
            }
        });
    });
}
async function loadMenuItems() {
    await loadMenuItemsFiltered();
}

function displayMenuItems(items) {
    const menuGrid = document.getElementById('menuGrid');
    if (!menuGrid) return;

    menuGrid.innerHTML = '';

    if (items.length === 0) {
        menuGrid.innerHTML = `
            <div style="grid-column: 1/-1; text-align: center; padding: 3rem; color: var(--text-secondary);">
                <span style="font-size: 3rem; display: block; margin-bottom: 1rem;">🍽️</span>
                <p style="font-size: 1.2rem;">No items found</p>
            </div>
        `;
        return;
    }

    items.forEach((item, index) => {
        const menuCard = createMenuCard(item);
        menuCard.style.opacity = '0';
        menuCard.style.transform = 'translateY(20px)';
        menuGrid.appendChild(menuCard);
        
        setTimeout(() => {
            menuCard.style.transition = 'all 0.5s ease';
            menuCard.style.opacity = '1';
            menuCard.style.transform = 'translateY(0)';
        }, index * 50);
    });
}

function createMenuCard(item) {
    const card = document.createElement('div');
    card.className = 'menu-item glass-card';
    card.dataset.category = item.category;
    card.dataset.price = item.price;

    const isOutOfStock = item.stock === 0;

    card.innerHTML = `
        <img src="${item.image}" alt="${item.name}" class="menu-item-image" loading="lazy">
        <div class="menu-item-content">
            <div class="menu-item-header">
                <h3 class="menu-item-name">${item.name}</h3>
                <span class="menu-item-price gradient-text">Rs. ${item.price}</span>
            </div>
            <span class="menu-item-category">${getCategoryName(item.category)}</span>
            <p class="menu-item-description">${item.description}</p>
            <div class="menu-item-footer">
                <span class="stock-status ${isOutOfStock ? 'out-of-stock' : ''}">
                    ${isOutOfStock ? '❌ Out of Stock' : `✓ ${item.stock} available`}
                </span>
                <button class="add-to-cart-btn gradient-btn" ${isOutOfStock ? 'disabled' : ''} 
                    onclick="addToCart(${item.id})">
                    ${isOutOfStock ? 'Unavailable' : '+ Add'}
                </button>
            </div>
        </div>
    `;

    return card;
}

function getCategoryName(category) {
    const names = {
        'main': 'Main Course',
        'beverage': 'Beverage',
        'dessert': 'Dessert',
        'appetizer': 'Appetizer'
    };
    return names[category] || category;
}

// ===========================
// FILTERING & SEARCHING
// ===========================
async function filterMenuItems() {
    await loadMenuItems();
}
async function searchMenuItems(query) {
    currentSearchQuery = query.trim();
    await loadMenuItems();
}
async function sortMenuItems(sortBy) {
    currentSortBy = sortBy;
    
    try {
        const menuGrid = document.getElementById('menuGrid');
        if (menuGrid) {
            menuGrid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 2rem;">Loading...</div>';
        }
        
        await loadMenuItems();
        
    } catch (err) {
        console.error('Error sorting menu:', err);
        showToast('Failed to sort menu', 'error');
    }
}

async function filterByPrice(maxPrice) {
    currentMaxPrice = parseFloat(maxPrice);
    console.log(`💰 Price filter updated: Max Rs. ${currentMaxPrice}`);
    
    await loadMenuItemsFiltered();
}


// ===========================
// CART MANAGEMENT
// ===========================
function saveCart() {
    localStorage.setItem('dinex_cart', JSON.stringify(cart));
    console.log('Cart saved:', cart); // Debug
}

async function loadCart() {

    if (!currentUser) {
        cart = [];
        updateCartCount();
        return;
    }

    try {
        const response = await fetch('/api/cart');
        
        if (response.ok) {
            const data = await response.json();
            
            if (data.success) {
                cart = data.cart || [];
                
                localStorage.setItem('dinex_cart', JSON.stringify(cart));
                
                console.log('✅ Cart loaded from backend:', cart.length, 'items');
            } else {
                cart = [];
            }
        } else {
            const saved = localStorage.getItem('dinex_cart');
            cart = saved ? JSON.parse(saved) : [];
            console.log('⚠️ Loaded cart from localStorage (backend failed)');
        }
    } catch (error) {
        console.error('❌ Cart load error:', error);
        const saved = localStorage.getItem('dinex_cart');
        cart = saved ? JSON.parse(saved) : [];
    }
    
    updateCartCount();
    return cart;
}


async function addToCart(itemId) {
    if (!currentUser) {
        showToast('Please login to add items to cart! 🔐', 'error');
        setTimeout(() => window.location.href = '/login', 1500);
        return;
    }

    const item = menuItems.find(i => i.id === itemId);
    if (!item) return;

    try {
        const response = await fetch('/api/cart/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                id: item.id,
                name: item.name,
                price: item.price,
                image: item.image,
                quantity: 1
            })
        });

        const data = await response.json();

        if (data.success) {
            cart = data.cart || [];
            localStorage.setItem('dinex_cart', JSON.stringify(cart));
            
            await fetchStackStatus();
            
            updateCartCount();
            updateCartDisplay();
            updateOrderFormCart();
            
            showToast(`${item.name} added to cart! 🎉`, 'success');
        } else {
            showToast('❌ ' + data.message, 'error');
        }
    } catch (error) {
        console.error('❌ Add to cart error:', error);
        showToast('❌ Failed to add item', 'error');
    }
}

function updateCartCount() {
    const cartCount = document.querySelector('.cart-count');
    if (!cartCount) return; 
    const totalItems = cart.reduce((sum, item) => sum + item.quantity, 0);
    cartCount.textContent = totalItems;
}

async function updateQuantity(itemId, change) {
    const item = cart.find(i => i.id === itemId);
    if (!item) return;

    const newQuantity = item.quantity + change;

    if (newQuantity <= 0) {
        await removeFromCart(itemId);
        return;
    }

    try {
        console.log(`📊 Updating: ${item.name} ${item.quantity} → ${newQuantity}`);
        
        const response = await fetch(`/api/cart/update/${itemId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ quantity: newQuantity })
        });

        const data = await response.json();

        if (data.success) {
            cart = data.cart || [];
            localStorage.setItem('dinex_cart', JSON.stringify(cart));
            
            if (data.stack_status) {
                stackStatus = data.stack_status;
                updateUndoRedoButtons();
            }
            
            updateCartCount();
            updateCartDisplay();
            updateOrderFormCart();
        }
    } catch (error) {
        console.error('❌ Update error:', error);
        showToast('Failed to update cart', 'error');
    }
}

async function removeFromCart(itemId) {
    try {
        console.log(`🗑️ Removing item ${itemId}`);
        
        const response = await fetch(`/api/cart/remove/${itemId}`, {
            method: 'DELETE'
        });

        const data = await response.json();

        if (data.success) {
            cart = data.cart || [];
            localStorage.setItem('dinex_cart', JSON.stringify(cart));
            
            if (data.stack_status) {
                stackStatus = data.stack_status;
                updateUndoRedoButtons();
                console.log('✅ Stack status updated after delete:', stackStatus);
            }
            
            updateCartCount();
            updateCartDisplay();
            updateOrderFormCart();
            
            showToast('Item removed from cart', 'success');
        }
    } catch (error) {
        console.error('❌ Remove error:', error);
        showToast('Failed to remove item', 'error');
    }
}




async function clearCart() {
    if (cart.length === 0) {
        showToast('Cart is already empty', 'error');
        return;
    }
    
    if (confirm('Are you sure you want to clear your cart?')) {
        try {
        
            const response = await fetch('/api/cart/clear', {
                method: 'DELETE'
            });

            const data = await response.json();
            
            if (data.success) {
                cart = [];
                localStorage.setItem('dinex_cart', JSON.stringify(cart));
                
                if (data.stack_status) {
                    stackStatus = data.stack_status;
                    updateUndoRedoButtons();
                }

                updateCartDisplay();
                updateCartCount();
                updateOrderFormCart();

                showToast('Cart cleared successfully! 🗑️', 'success');
            } else {
                showToast('Failed to clear cart', 'error');
            }
        } catch (error) {
            console.error('Clear cart error:', error);
            showToast('Failed to clear cart', 'error');
        }
    }
}

// ===========================
// ENHANCED CART MODAL
// ===========================

function openCartModal() {
  const sidebar = document.getElementById('cartSidebar');
  const overlay = document.getElementById('cartOverlay');
  const itemsContainer = document.getElementById('cartItemsContainer');
  
  if (!sidebar || !overlay || !itemsContainer) return;

  itemsContainer.innerHTML = '';

  if (!cart || cart.length === 0) {
    itemsContainer.innerHTML = `
      <div class="cart-empty-state">
        <div class="cart-empty-icon">🛒</div>
        <p>Your cart is empty</p>
        <small>Add items from the menu to get started</small>
      </div>
    `;
  } else {
    cart.forEach((item, index) => {
      const row = document.createElement('div');
      row.className = 'cart-item-row';
      row.style.animationDelay = `${index * 0.05}s`;
      row.innerHTML = `
        <div class="cart-item-top">
          <span class="cart-item-name">${item.name}</span>
          <span class="cart-item-price">Rs. ${item.price * item.quantity}</span>
        </div>
        <div class="cart-item-bottom">
          <div class="cart-quantity-controls">
            <button class="cart-qty-btn" onclick="updateCartQuantity(${item.id}, -1)">−</button>
            <span class="cart-qty-display">${item.quantity}</span>
            <button class="cart-qty-btn" onclick="updateCartQuantity(${item.id}, 1)">+</button>
          </div>
          <button class="cart-remove-btn" onclick="removeFromCartSidebar(${item.id})">
            🗑️ Remove
          </button>
        </div>
      `;
      itemsContainer.appendChild(row);
    });
  }

  updateCartFooter();

  sidebar.classList.add('open');
  overlay.classList.add('show');
  document.body.style.overflow = 'hidden';
}

function closeCartModal() {
  const sidebar = document.getElementById('cartSidebar');
  const overlay = document.getElementById('cartOverlay');
  
  if (!sidebar || !overlay) return;
  
  sidebar.classList.remove('open');
  overlay.classList.remove('show');
  document.body.style.overflow = '';
}

function updateCartFooter() {
  const footer = document.querySelector('.cart-footer');
  if (!footer) return;

  const total = cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
  
  footer.innerHTML = `
    <div class="cart-footer-content">
      <div class="cart-total-row">
        <span>Total:</span>
        <span>Rs. ${total}</span>
      </div>
      ${cart.length > 0 ? `
        <div class="cart-actions">
          <button class="btn-clear-cart-sidebar" onclick="clearCart()">
            🗑️ Clear
          </button>
          <button class="btn-checkout-sidebar" onclick="handleCheckoutClick()">
            <span>Checkout</span>
            <span class="btn-icon">→</span>
          </button>
        </div>
      ` : ''}
    </div>
  `;
}

function updateCartDisplay() {
    if (document.getElementById('cartSidebar')?.classList.contains('open')) {
        const itemsContainer = document.getElementById('cartItemsContainer');
        if (!itemsContainer) return;

        itemsContainer.innerHTML = '';

        if (!cart || cart.length === 0) {
            itemsContainer.innerHTML = `
                <div class="cart-empty-state">
                    <div class="cart-empty-icon">🛒</div>
                    <p>Your cart is empty</p>
                    <small>Add items from the menu to get started</small>
                </div>
            `;
        } else {
            cart.forEach((item, index) => {
                const row = document.createElement('div');
                row.className = 'cart-item-row';
                row.innerHTML = `
                    <div class="cart-item-top">
                        <span class="cart-item-name">${item.name}</span>
                        <span class="cart-item-price">Rs. ${item.price * item.quantity}</span>
                    </div>
                    <div class="cart-item-bottom">
                        <div class="cart-quantity-controls">
                            <button class="cart-qty-btn" onclick="updateQuantity(${item.id}, -1)">−</button>
                            <span class="cart-qty-display">${item.quantity}</span>
                            <button class="cart-qty-btn" onclick="updateQuantity(${item.id}, 1)">+</button>
                        </div>
                        <button class="cart-remove-btn" onclick="removeFromCart(${item.id})">🗑️ Remove</button>
                    </div>
                `;
                itemsContainer.appendChild(row);
            });
        }

        updateCartFooter();
    }
}

const originalAddToCart = window.addToCart;
if (originalAddToCart) {
  window.addToCart = function(itemId) {
    originalAddToCart(itemId);
    updateCartDisplay();
  };
}

const originalUpdateQuantity = window.updateQuantity;
if (originalUpdateQuantity) {
  window.updateQuantity = function(itemId, change) {
    originalUpdateQuantity(itemId, change);
    updateCartDisplay();
    updateOrderFormCart();
  };
}

const originalRemoveFromCart = window.removeFromCart;
if (originalRemoveFromCart) {
  window.removeFromCart = function(itemId) {
    originalRemoveFromCart(itemId);
    updateCartDisplay();
    updateOrderFormCart();
  };
}

window.clearCart = function() {
  if (cart.length === 0) {
    showToast('Cart is already empty', 'error');
    return;
  }
  
  if (confirm('Are you sure you want to clear your cart?')) {
    cart = [];
    updateCartDisplay();
    updateCartCount();
    updateOrderFormCart();
    showToast('Cart cleared successfully! 🗑️', 'success');
  }
};

window.removeFromCartSidebar = async function(itemId) {
    const item = cart.find(i => i.id === itemId);
    if (!item) return;

    if (!confirm(`Remove ${item.name} from cart?`)) return;

    try {
        
        await removeFromCart(itemId);
    } catch (err) {
        console.error('Failed to remove item via backend:', err);
        
        cart = cart.filter(i => i.id !== itemId);
        updateCartDisplay();
        updateCartCount();
        updateOrderFormCart();
        showToast('Item removed locally (offline)', 'warning');
    }
};


window.updateCartQuantity = async function(itemId, change) {
  const item = cart.find(i => i.id === itemId);
  if (!item) return;

  const newQuantity = item.quantity + change;

  
  if (newQuantity <= 0) {
    await removeFromCartSidebar(itemId);
  } else {
    await updateQuantity(itemId, change);  
  }
};

window.handleCheckoutClick = function() {
  if (cart.length === 0) {
    showToast('Cart is empty! Add items first 🛒', 'error');
    return;
  }

  if (!currentUser) {
    showToast('Please login to continue ⚠️', 'error');
    setTimeout(() => {
      window.location.href = '/login';
    }, 1500);
    return;
  }

  closeCartModal();

  setTimeout(() => {
    const ordersSection = document.getElementById('orders');
    if (ordersSection) {
      ordersSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
      
      setTimeout(() => {
        
        const tabBtns = document.querySelectorAll('.tab-btn');
        const tabContents = document.querySelectorAll('.tab-content');
        
        tabBtns.forEach(btn => btn.classList.remove('active'));
        tabContents.forEach(content => content.classList.remove('active'));
        
        const newOrderBtn = document.querySelector('[data-tab="new-order"]');
        const newOrderContent = document.getElementById('new-order');
        
        if (newOrderBtn) newOrderBtn.classList.add('active');
        if (newOrderContent) newOrderContent.classList.add('active');
       
        if (currentUser) {
          const nameInput = document.getElementById('customerName');
          const phoneInput = document.getElementById('customerPhone');
          
          if (nameInput) {
            nameInput.value = `${currentUser.firstName} ${currentUser.lastName}`;
          }
          if (phoneInput && currentUser.phone) {
            phoneInput.value = currentUser.phone;
          }
        }
        
        updateOrderFormCart();
        
        showToast('Complete your order details below 📝', 'success');
      }, 800);
    }
  }, 300);
};

function updateOrderFormCart() {
  const cartItemsContainer = document.getElementById('cartItems');
  const subtotalEl = document.getElementById('subtotal');
  const deliveryFeeEl = document.getElementById('deliveryFee');
  const totalAmountEl = document.getElementById('totalAmount');
  
  if (!cartItemsContainer) return;
  
  if (cart.length === 0) {
    cartItemsContainer.innerHTML = `
      <div class="empty-cart">
        <span class="empty-icon">🛒</span>
        <p>Your cart is empty</p>
        <small>Add items from menu</small>
      </div>
    `;
    if (subtotalEl) subtotalEl.textContent = 'Rs. 0';
    if (totalAmountEl) totalAmountEl.textContent = 'Rs. 0';
    return;
  }
  
  cartItemsContainer.innerHTML = '';
  let subtotal = 0;
  
  cart.forEach(item => {
    const cartItem = document.createElement('div');
    cartItem.className = 'cart-item';
    cartItem.innerHTML = `
      <div class="cart-item-info">
        <span class="cart-item-name">${item.name}</span>
        <span class="cart-item-price">Rs. ${item.price} × ${item.quantity}</span>
      </div>
      <div class="cart-item-actions">
        <div class="quantity-control">
          <button class="quantity-btn" onclick="window.updateQuantity(${item.id}, -1)">-</button>
          <span>${item.quantity}</span>
          <button class="quantity-btn" onclick="window.updateQuantity(${item.id}, 1)">+</button>
        </div>
        <button class="remove-item-btn" onclick="window.removeFromCart(${item.id})">🗑️</button>
      </div>
    `;
    cartItemsContainer.appendChild(cartItem);
    subtotal += item.price * item.quantity;
  });
  
  const deliveryFee = 50;
  const total = subtotal + deliveryFee;
  
  if (subtotalEl) subtotalEl.textContent = `Rs. ${subtotal}`;
  if (deliveryFeeEl) deliveryFeeEl.textContent = `Rs. ${deliveryFee}`;
  if (totalAmountEl) totalAmountEl.textContent = `Rs. ${total}`;
}

document.addEventListener('DOMContentLoaded', () => {
  const closeBtn = document.getElementById('closeCartBtn');
  const overlay = document.getElementById('cartOverlay');
  
  if (closeBtn) {
    closeBtn.addEventListener('click', closeCartModal);
  }
  
  if (overlay) {
    overlay.addEventListener('click', closeCartModal);
  }

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && document.getElementById('cartSidebar')?.classList.contains('open')) {
      closeCartModal();
    }
  });
  
  setTimeout(() => {
    updateOrderFormCart();
  }, 500);
});

function createCartModal() {
    const modal = document.createElement('div');
    modal.id = 'cartModal';
    modal.className = 'cart-modal';
    modal.innerHTML = `
        <div class="cart-modal-overlay" onclick="close
        CartModal()"></div>
        <div class="cart-modal-content glass-card">
            <div class="cart-modal-header">
                <h2>🛒 Your Cart</h2>
                <button class="close-modal-btn" onclick="closeCartModal()">✕</button>
            </div>
            <div class="cart-modal-body" id="cartModalBody">
                <!-- Cart items will be inserted here -->
            </div>
            <div class="cart-modal-footer">
                <button class="btn-clear-cart" onclick="clearCart()">Clear Cart</button>
                <button class="btn-checkout gradient-btn" onclick="proceedToCheckout()">
                    <span>Proceed to Checkout</span>
                    <span class="btn-icon">→</span>
                </button>
            </div>
        </div>
    `;
    return modal;
}

function updateCartModal() {
    const cartBody = document.getElementById('cartModalBody');
    if (!cartBody) return;

    if (cart.length === 0) {
        cartBody.innerHTML = `
            <div class="empty-cart-modal">
                <span class="empty-icon">🛒</span>
                <p>Your cart is empty</p>
                <small>Add items from menu to get started</small>
            </div>
        `;
        return;
    }

    const subtotal = cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
    const deliveryFee = 50;
    const total = subtotal + deliveryFee;

    let cartHTML = '<div class="cart-items-list">';
    cart.forEach(item => {
        cartHTML += `
            <div class="cart-item-card glass-card">
                <img src="${item.image}" alt="${item.name}" class="cart-item-img">
                <div class="cart-item-details">
                    <h4>${item.name}</h4>
                    <p class="cart-item-price-unit">Rs. ${item.price} each</p>
                    <div class="cart-item-actions">
                        <div class="quantity-control">
                            <button class="quantity-btn" onclick="updateQuantity(${item.id}, -1)">-</button>
                            <span class="quantity-display">${item.quantity}</span>
                            <button class="quantity-btn" onclick="updateQuantity(${item.id}, 1)">+</button>
                        </div>
                        <button class="remove-item-btn" onclick="removeFromCart(${item.id})">
                            <span>🗑️</span>
                        </button>
                    </div>
                </div>
                <div class="cart-item-total">
                    <span class="gradient-text">Rs. ${item.price * item.quantity}</span>
                </div>
            </div>
        `;
    });
    cartHTML += '</div>';

    cartHTML += `
        <div class="cart-summary glass-card">
            <h3>Order Summary</h3>
            <div class="summary-row">
                <span>Subtotal:</span>
                <span>Rs. ${subtotal}</span>
            </div>
            <div class="summary-row">
                <span>Delivery Fee:</span>
                <span>Rs. ${deliveryFee}</span>
            </div>
            <div class="summary-divider"></div>
            <div class="summary-row summary-total">
                <span>Total:</span>
                <span class="gradient-text">Rs. ${total}</span>
            </div>
        </div>
    `;

    cartBody.innerHTML = cartHTML;
}

// ===========================
// CHECKOUT PROCESS
// ===========================
function proceedToCheckout() {
    if (cart.length === 0) {
        showToast('Cart is empty! Add items first 🛒', 'error');
        return;
    }

    if (!currentUser) {
        showToast('Please login to continue ⚠️', 'error');
        setTimeout(() => {
            window.location.href = '/login';
        }, 1500);
        return;
    }

    closeCartModal();
    openCheckoutModal();
}

function openCheckoutModal() {
    let modal = document.getElementById('checkoutModal');
    if (!modal) {
        modal = createCheckoutModal();
        document.body.appendChild(modal);
    }
    
    modal.classList.add('show');
    document.body.style.overflow = 'hidden';
}

function closeCheckoutModal() {
    const modal = document.getElementById('checkoutModal');
    modal?.classList.remove('show');
    document.body.style.overflow = '';
}

function createCheckoutModal() {
    const modal = document.createElement('div');
    modal.id = 'checkoutModal';
    modal.className = 'checkout-modal';
    
    const subtotal = cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
    const deliveryFee = 50;
    const total = subtotal + deliveryFee;

    modal.innerHTML = `
        <div class="checkout-modal-overlay" onclick="closeCheckoutModal()"></div>
        <div class="checkout-modal-content glass-card">
            <div class="checkout-modal-header">
                <h2>🛍️ Checkout</h2>
                <button class="close-modal-btn" onclick="closeCheckoutModal()">✕</button>
            </div>
            <div class="checkout-modal-body">
                <div class="checkout-section">
                    <h3 class="checkout-title">📍 Delivery Information</h3>
                    <div class="form-group">
                        <label class="form-label">Full Name</label>
                        <input type="text" id="checkoutName" class="form-input glass-input" 
                            value="${currentUser ? currentUser.firstName + ' ' + currentUser.lastName : ''}" 
                            placeholder="Enter your name">
                    </div>
                    <div class="form-group">
                        <label class="form-label">Phone Number</label>
                        <input type="tel" id="checkoutPhone" class="form-input glass-input" 
                            value="${currentUser ? currentUser.phone : ''}"
                            placeholder="03XX-XXXXXXX">
                    </div>
                    <div class="form-group">
                        <label class="form-label">Delivery Address</label>
                        <textarea id="checkoutAddress" class="form-input glass-input" rows="3" 
                            placeholder="Enter complete delivery address"></textarea>
                    </div>
                </div>

                <div class="checkout-section">
                    <h3 class="checkout-title">🚀 Delivery Type</h3>
                    <div class="delivery-type-selection">
                        <label class="delivery-type-card glass-card">
                            <input type="radio" name="deliveryType" value="regular" checked>
                            <div class="delivery-icon">🚴</div>
                            <span class="delivery-title">Regular</span>
                            <small class="delivery-desc">Standard delivery</small>
                            <span class="delivery-time">30-45 mins</span>
                        </label>
                        <label class="delivery-type-card glass-card">
                            <input type="radio" name="deliveryType" value="express">
                            <div class="delivery-icon">⚡</div>
                            <span class="delivery-title">Express</span>
                            <small class="delivery-desc">Higher priority</small>
                            <span class="delivery-time">20-30 mins</span>
                        </label>
                        <label class="delivery-type-card glass-card">
                            <input type="radio" name="deliveryType" value="vip">
                            <div class="delivery-icon">👑</div>
                            <span class="delivery-title">VIP</span>
                            <small class="delivery-desc">Highest priority</small>
                            <span class="delivery-time">15-20 mins</span>
                        </label>
                    </div>
                </div>

                <div class="checkout-section">
                    <h3 class="checkout-title">📦 Order Summary</h3>
                    <div class="checkout-order-summary glass-card">
                        <div class="summary-items">
                            ${cart.map(item => `
                                <div class="summary-item">
                                    <span>${item.name} × ${item.quantity}</span>
                                    <span>Rs. ${item.price * item.quantity}</span>
                                </div>
                            `).join('')}
                        </div>
                        <div class="summary-divider"></div>
                        <div class="summary-row">
                            <span>Subtotal:</span>
                            <span>Rs. ${subtotal}</span>
                        </div>
                        <div class="summary-row">
                            <span>Delivery Fee:</span>
                            <span>Rs. ${deliveryFee}</span>
                        </div>
                        <div class="summary-divider"></div>
                        <div class="summary-row summary-total">
                            <span>Total Amount:</span>
                            <span class="gradient-text">Rs. ${total}</span>
                        </div>
                    </div>
                </div>
            </div>
            <div class="checkout-modal-footer">
                <button class="btn-back" onclick="closeCheckoutModal()">← Back to Cart</button>
                <button class="btn-place-order gradient-btn" onclick="placeOrder()">
                    <span>Confirm Order</span>
                    <span class="btn-icon">✓</span>
                </button>
            </div>
        </div>
    `;
    return modal;
}

// ===========================
// ORDER PLACEMENT - BACKEND INTEGRATED ✅
// ===========================
async function placeOrder() {
    console.log('📦 Place order called');
    
    if (isProcessingOrder) {
        console.log('⚠️ Order already processing, ignoring click');
        showToast('Order is being processed... Please wait', 'warning');
        return;
    }

    try {
        const cartResponse = await fetch('/api/cart');
        const cartData = await cartResponse.json();
        
        if (cartData.success) {
            cart = cartData.cart || [];
            console.log('✅ Fresh cart loaded:', cart.length, 'items');
        }
    } catch (error) {
        console.error('❌ Failed to fetch cart:', error);
    }
    

    if (!cart || cart.length === 0) {
        showToast('Cart is empty! Add items first 🛒', 'error');
        return;
    }


    if (!currentUser) {
        showToast('Please login to continue ⚠️', 'error');
        setTimeout(() => window.location.href = '/login', 1500);
        return;
    }


    let name = document.getElementById('customerName')?.value.trim();
    let phone = document.getElementById('customerPhone')?.value.trim();
    let address = document.getElementById('customerAddress')?.value.trim();
    let orderTypeInput = document.querySelector('input[name="orderType"]:checked');
    

    if (!name || !phone || !address) {
        name = document.getElementById('checkoutName')?.value.trim();
        phone = document.getElementById('checkoutPhone')?.value.trim();
        address = document.getElementById('checkoutAddress')?.value.trim();
        orderTypeInput = document.querySelector('input[name="deliveryType"]:checked');
    }

    const deliveryType = orderTypeInput?.value || 'regular';

    if (!name || !phone || !address) {
        showToast('Please fill all delivery information ⚠️', 'error');
        return;
    }


    const cleanPhone = phone.replace(/[-\s]/g, '');
    if (!/^[0-9]{10,11}$/.test(cleanPhone)) {
        showToast('Please enter a valid phone number (10-11 digits) 📱', 'error');
        return;
    }

    if (address.length < 10) {
        showToast('Please enter a complete delivery address 📍', 'error');
        return;
    }

    const orderData = {
        customerPhone: phone,
        customerName: name,
        customerAddress: address,
        orderType: deliveryType
    };

    console.log('📤 Placing order:', orderData);
    console.log('   Cart items:', cart.length);
    console.log('   Total:', cart.reduce((sum, item) => sum + (item.price * item.quantity), 0));


    const submitButtons = [
        document.querySelector('.btn-place-order'),
        document.querySelector('.btn-primary.gradient-btn.btn-large'),
        document.querySelector('button[onclick*="placeOrder"]'),
        ...document.querySelectorAll('button[type="submit"]')
    ].filter(btn => btn !== null);

    const originalButtonStates = [];
    
    submitButtons.forEach(btn => {
        originalButtonStates.push({
            btn: btn,
            html: btn.innerHTML,
            disabled: btn.disabled,
            cursor: btn.style.cursor,
            opacity: btn.style.opacity
        });
        
        btn.innerHTML = '<span>⏳ Processing Order...</span>';
        btn.disabled = true;
        btn.style.cursor = 'not-allowed';
        btn.style.opacity = '0.6';
    });


    isProcessingOrder = true;

    try {
       
        console.log('📡 Sending to backend...');
        
        const response = await fetch('/api/orders/place', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(orderData)
        });

        const result = await response.json();
        
        console.log('📥 Backend response:', result);

   
        if (!result.success) {
            throw new Error(result.message || 'Order placement failed');
        }

      
        console.log('✅ Order placed successfully!');
        console.log('   Order ID:', result.orderId);
        
        showToast('🎉 Order placed successfully!', 'success');
        
     
        cart = [];
        localStorage.setItem('dinex_cart', JSON.stringify(cart));
        updateCartCount();
        updateOrderFormCart();
        

        closeCheckoutModal();
        closeCartModal();
      
        showToast(`Order ${result.orderId} confirmed! Redirecting to tracking... 📦`, 'success');
        
  
        setTimeout(() => {
            window.location.href = `/track?orderId=${result.orderId}`;
        }, 2000);
        
    } catch (error) {
       
        console.error('❌ Order placement error:', error);
        showToast('❌ ' + (error.message || 'Order failed! Please try again'), 'error');
        
        originalButtonStates.forEach(state => {
            state.btn.innerHTML = state.html;
            state.btn.disabled = state.disabled;
            state.btn.style.cursor = state.cursor;
            state.btn.style.opacity = state.opacity;
        });
        
        isProcessingOrder = false;
        
    } finally {
       
        setTimeout(() => {
            isProcessingOrder = false;
            console.log('🔓 Order processing flag reset');
        }, 5000);
    }
}
window.placeOrder = placeOrder;

console.log('✅ Order placement system loaded');

//===========================
// ORDER CONFIRMATION MODAL
// ===========================

function showOrderConfirmation(orderId, email) {
    const confirmModal = document.createElement('div');
    confirmModal.className = 'order-confirmation-modal';
    confirmModal.innerHTML = `
        <div class="confirmation-overlay"></div>
        <div class="confirmation-content glass-card">
            <div class="confirmation-icon">✅</div>
            <h2 class="confirmation-title">Order Confirmed!</h2>
            <p class="confirmation-message">
                Your order has been placed successfully.<br>
                A confirmation email has been sent to <strong>${email}</strong>
            </p>
            <div class="order-id-display glass-card">
                <span class="order-id-label">Order ID</span>
                <span class="order-id gradient-text">#${orderId}</span>
            </div>
            <div class="confirmation-actions">
                <button class="btn-track-order gradient-btn" onclick="showOrderTracking('${orderId}')">
                    <span>Track Order</span>
                    <span class="btn-icon">🚚</span>
                </button>
                <button class="btn-continue-shopping" onclick="closeOrderConfirmation()">
                    Continue Shopping
                </button>
            </div>
        </div>
    `;
    
    document.body.appendChild(confirmModal);
    setTimeout(() => confirmModal.classList.add('show'), 10);
}

function closeOrderConfirmation() {
    const modal = document.querySelector('.order-confirmation-modal');
    modal?.remove();
    document.body.style.overflow = '';
}

function showOrderTracking(orderId) {
    closeOrderConfirmation();
    
    const trackingSection = document.getElementById('tracking');
    if (trackingSection) {
        trackingSection.scrollIntoView({ behavior: 'smooth' });
        
        setTimeout(() => {
            updateTrackingDisplay(orderId);
        }, 1000);
    }
}

function updateTrackingDisplay(orderId) {
    const timelineTitle = document.querySelector('.timeline-title');
    if (timelineTitle) {
        timelineTitle.textContent = `Order Progress - #${orderId}`;
    }
}

// ===========================
// SCROLL ANIMATIONS
// ===========================
function setupScrollAnimations() {
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -100px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, observerOptions);

    setTimeout(() => {
        document.querySelectorAll('.feature-card, .menu-item').forEach(el => {
            el.style.opacity = '0';
            el.style.transform = 'translateY(30px)';
            el.style.transition = 'all 0.6s ease';
            observer.observe(el);
        });
    }, 100);
}

function initializeAnimations() {
    const heroText = document.querySelector('.hero-text');
    const heroImage = document.querySelector('.hero-image');
    
    if (heroText) {
        heroText.style.opacity = '0';
        heroText.style.transform = 'translateX(-30px)';
        setTimeout(() => {
            heroText.style.transition = 'all 1s ease';
            heroText.style.opacity = '1';
            heroText.style.transform = 'translateX(0)';
        }, 100);
    }
    
    if (heroImage) {
        heroImage.style.opacity = '0';
        heroImage.style.transform = 'translateX(30px)';
        setTimeout(() => {
            heroImage.style.transition = 'all 1s ease';
            heroImage.style.opacity = '1';
            heroImage.style.transform = 'translateX(0)';
        }, 300);
    }
}

// ===========================
// TOAST NOTIFICATIONS
// ===========================
function showToast(message, type = 'success') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    const icon = type === 'success' ? '✓' : '⚠';
    
    toast.innerHTML = `
        <span class="toast-icon">${icon}</span>
        <span>${message}</span>
    `;

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'slideInRight 0.3s ease reverse';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// ===========================
// UTILITY FUNCTIONS
// ===========================
function scrollToMenu() {
    const menuSection = document.getElementById('menu');
    if (menuSection) {
        const offsetTop = menuSection.offsetTop - 80;
        window.scrollTo({
            top: offsetTop,
            behavior: 'smooth'
        });
    }
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// ===========================
// ✅ USER SESSION 
// ===========================
function checkUserSession() {
    if (!window.location.pathname.includes('index') && 
        !window.location.pathname.endsWith('/')) return;

    const userData = localStorage.getItem('dinex_user');
    if (userData) {
        currentUser = JSON.parse(userData);
        console.log('✅ User session found:', currentUser);
        updateNavbar(); 
    } else {
        console.log('❌ No user session');
    }
}

function onLoginSuccess(userData) {
    localStorage.setItem('dinex_user', JSON.stringify(userData));
    currentUser = userData;
    
    console.log('✅ Login successful, updating navbar...', userData);
  
    updateNavbar();
    
    showToast('Login successful! 🎉', 'success');
    
   
    setTimeout(() => {
        if (userData.role === 'admin' || userData.role === 'super_admin') {
            if (confirm('Go to Admin Panel? (Cancel to stay on main site)')) {
                window.location.href = '/admin';
            }
        }
    }, 1500);
}

function createProfileBox() {
    if (document.getElementById('profileBox')) return;

    const box = document.createElement('div');
    box.id = 'profileBox';
    box.className = 'profile-box';

    box.innerHTML = `
        <div class="profile-header">
            <span>👤 Profile</span>
            <button onclick="toggleProfile()">✖</button>
        </div>

        <p><strong>Name:</strong> ${currentUser.firstName} ${currentUser.lastName}</p>
        <p><strong>Email:</strong> ${currentUser.email}</p>

        <button class="logout-btn" onclick="logout()">Logout</button>
    `;

    document.body.appendChild(box);
}

function updateNavbar() {
    const nav = document.getElementById('navButtons');
    if (!nav) {
        console.error('❌ navButtons container not found!');
        return;
    }

    currentUser = JSON.parse(localStorage.getItem('dinex_user'));
    
    console.log('🔍 Current user:', currentUser); 

    nav.innerHTML = '';

    if (!currentUser) {
   
        const loginBtn = document.createElement('button');
        loginBtn.className = 'btn-login glass-btn';
        loginBtn.onclick = function() {
            window.location.href = '/login';
        };
        loginBtn.innerHTML = '<span>Login</span>';
        nav.appendChild(loginBtn);
        
        console.log('➡️ Added login button (user not logged in)');
    } else {
        console.log('✅ User logged in with role:', currentUser.role);

        if (currentUser.role === 'rider') {
            const riderBtn = document.createElement('a');
            riderBtn.href = '/rider';
            riderBtn.className = 'glass-rider-btn';
            riderBtn.innerHTML = '<span class="rider-icon">🚴</span><span>Rider Dashboard</span>';

            nav.appendChild(riderBtn);
            console.log('🚴 ✅ Rider Dashboard button added!');
        }

        if (currentUser.role === 'kitchen') {
            const kitchenBtn = document.createElement('a');
            kitchenBtn.href = '/kitchen';
            kitchenBtn.className = 'glass-kitchen-btn';
            kitchenBtn.innerHTML = '<span class="kitchen-icon">🍳</span><span>Kitchen</span>';

            nav.appendChild(kitchenBtn);
            console.log('🍳 ✅ Kitchen Dashboard button added!');
        }
        
        if (currentUser.role === 'admin' || currentUser.role === 'super_admin') {
            const adminBtn = document.createElement('a');
            adminBtn.href = '/admin';
            adminBtn.className = 'glass-admin-btn';
            adminBtn.innerHTML = '<span class="admin-icon">🎛️</span><span>Admin Panel</span>';

            nav.appendChild(adminBtn);
            console.log('🎛️ ✅ Admin Panel button added!');
        }

        const profileBtn = document.createElement('button');
        profileBtn.className = 'profile-emoji-btn glass-btn';
        profileBtn.textContent = '👤';
        profileBtn.onclick = toggleProfile;
        
        profileBtn.style.cssText = `
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
            color: white;
            font-size: 1.5rem;
            width: 45px;
            height: 45px;
            border-radius: 50%;
            cursor: pointer;
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 0;
        `;
        
        profileBtn.addEventListener('mouseenter', function() {
            this.style.background = 'rgba(255, 255, 255, 0.2)';
            this.style.transform = 'scale(1.1)';
        });
        
        profileBtn.addEventListener('mouseleave', function() {
            this.style.background = 'rgba(255, 255, 255, 0.1)';
            this.style.transform = 'scale(1)';
        });
        
        nav.appendChild(profileBtn);
        console.log('👤 Profile button added');
        
        createProfileBox();
    }

    const cartBtn = document.createElement('button');
    cartBtn.className = 'btn-cart glass-btn';
    cartBtn.type = 'button';
    cartBtn.innerHTML = `
        <span class="cart-icon">🛒</span>
        <span class="cart-count">0</span>
    `;
    
    nav.appendChild(cartBtn);
    console.log('🛒 Cart button added');
    
    updateCartCount();
}

// ===========================
// PROFILE PANEL
// ===========================
function createProfilePanel() {
    if (!currentUser) return;

    const existing = document.getElementById('profilePanel');
    if (existing) existing.remove();

    const panel = document.createElement('div');
    panel.id = 'profilePanel';
    panel.className = 'profile-panel';
    
    let roleBadge = '';
    if (currentUser.role === 'super_admin') {
        roleBadge = '<span class="role-badge super-admin">👑 SUPER ADMIN</span>';
    } else if (currentUser.role === 'admin') {
        roleBadge = '<span class="role-badge admin">👨‍💼 ADMIN</span>';
    } else {
        roleBadge = '<span class="role-badge customer">👤 Customer</span>';
    }
    
    panel.innerHTML = `
        <div class="profile-panel-header">
            <h3>Profile</h3>
            <button class="close-profile-btn" onclick="closeProfile()">✕</button>
        </div>
        
        <div class="profile-panel-body">
            ${roleBadge}
            
            <div class="profile-info-group">
                <label>Name</label>
                <p>${currentUser.firstName} ${currentUser.lastName}</p>
            </div>
            
            <div class="profile-info-group">
                <label>Email</label>
                <p>${currentUser.email}</p>
            </div>
            
            <div class="profile-info-group">
                <label>Phone</label>
                <p>${currentUser.phone || 'Not provided'}</p>
            </div>
            
            ${currentUser.role === 'admin' || currentUser.role === 'super_admin' ? `
                <a href="/admin" class="admin-panel-link">
                    <span>👨‍💼</span>
                    <span>Open Admin Panel</span>
                    <span>→</span>
                </a>
            ` : ''}
        </div>
        
        <div class="profile-panel-footer">
            <button class="logout-btn" onclick="handleLogout()">
                <span>🚪</span>
                <span>Logout</span>
            </button>
        </div>
    `;

    document.body.appendChild(panel);
}

// ===========================
// LOGIN HANDLER
// ===========================

async function handleLogin(event) {
    event.preventDefault();
    
    const emailPhone = document.getElementById('emailPhone').value.trim();
    const password = document.getElementById('password').value.trim();

    if (!emailPhone || !password) {
        showToast('Email/Phone and password are required', 'error');
        return;
    }

    const isEmail = emailPhone.includes('@');
    const isPhone = /^[0-9]{10,15}$/.test(emailPhone);

    if (!isEmail && !isPhone) {
        showToast('Please enter a valid email or phone number', 'error');
        return;
    }

    console.log("LOGIN INPUT:", emailPhone);
    console.log("PASSWORD SENT TO BACKEND:", password);

    try {
        const response = await fetch('/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ emailPhone, password })
        });
        
        const data = await response.json();
        
        if (data.success) {
            localStorage.setItem('dinex_user', JSON.stringify(data.user));
            currentUser = data.user;
            
            showToast('Login successful! 🎉', 'success');
            
            setTimeout(() => {
                if (data.user.role === 'admin' || data.user.role === 'super_admin') {
                    if (confirm('Go to Admin Panel? (Cancel to go to main site)')) {
                        window.location.href = '/admin';
                    } else {
                        window.location.href = '/';
                    }
                } else {
                    window.location.href = '/';
                }
            }, 1500);
        } else {
            showToast(data.message || 'Login failed', 'error');
        }
    } catch (error) {
        console.error('Login error:', error);
        showToast('Login failed. Please try again.', 'error');
    }
}


document.addEventListener('click', function (e) {
    const panel = document.getElementById('profilePanel');
    const btn = document.querySelector('.profile-emoji-btn');

    if (!panel || !btn) return;

    if (!panel.contains(e.target) && !btn.contains(e.target)) {
        panel.classList.remove('show');
    }
});

function clearOrderForm() {
    const nameInput = document.getElementById('customerName');
    const phoneInput = document.getElementById('customerPhone');
    const addressInput = document.getElementById('customerAddress');
    
    if (nameInput) nameInput.value = currentUser ? `${currentUser.firstName} ${currentUser.lastName}` : '';
    if (phoneInput) phoneInput.value = currentUser?.phone || '';
    if (addressInput) addressInput.value = '';
    
    const regularRadio = document.querySelector('input[name="orderType"][value="regular"]');
    if (regularRadio) {
        regularRadio.checked = true;
    }
    
    console.log('✅ Order form cleared');
}

window.clearOrderForm = clearOrderForm;
window.addToCart = addToCart;
window.updateQuantity = updateQuantity;
window.removeFromCart = removeFromCart;
window.clearCart = clearCart;
window.scrollToMenu = scrollToMenu;
window.openCartModal = openCartModal;
window.closeCartModal = closeCartModal;
window.proceedToCheckout = proceedToCheckout;
window.closeCheckoutModal = closeCheckoutModal;
window.placeOrder = placeOrder;
window.closeOrderConfirmation = closeOrderConfirmation;
window.showOrderTracking = showOrderTracking;
window.handleLogout = handleLogout;
window.openProfilePanel = openProfilePanel;
window.closeProfilePanel = closeProfilePanel;
window.loadCartFromBackend = loadCartFromBackend;
document.addEventListener('DOMContentLoaded', () => {
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetTab = btn.dataset.tab;
            
            tabBtns.forEach(b => b.classList.remove('active'));
            tabContents.forEach(content => content.classList.remove('active'));
            
            btn.classList.add('active');
            document.getElementById(targetTab)?.classList.add('active');
        });
    });
});

window.toggleProfile = toggleProfile;
window.closeProfile = closeProfile;
window.handleLogout = handleLogout;
window.undoCartDelete = undoCartDelete;
window.redoCartDelete = redoCartDelete;
window.fetchStackStatus = fetchStackStatus;
window.refreshStackStatus = refreshStackStatus;
window.updateCartDisplay = updateCartDisplay;