import React, { useState, useEffect } from 'react';
import { AppShell } from '../../components/AppShell/AppShell';
import { PageHeader } from '../../components/PageHeader/PageHeader';
import { useAuth } from '../../context/AuthContext';
import { useRouter } from '../../router/Router';
import {
  ShoppingBag,
  ShoppingCart,
  Search,
  Filter,
  CheckCircle2,
  Star,
  ShieldCheck,
  Truck,
  Plus,
  Minus,
  Trash2,
  X,
  CreditCard,
  Zap,
  Tag,
  ArrowRight,
  ExternalLink,
} from 'lucide-react';
import './SolarStore.css';

const PRODUCTS = [
  {
    id: 'prod-1',
    name: 'Waaree 540W Mono-PERC Bifacial Solar Panel',
    category: 'panels',
    brand: 'Waaree Energies',
    rating: 4.9,
    reviews: 128,
    specs: '540W · 21.3% Efficiency · 144 Half-Cut Cells · IP68 MC4',
    warranty: '25-Year Linear Performance Warranty',
    price: 13500,
    mrp: 16800,
    subsidyEligible: true,
    inStock: 42,
    badge: 'Best Seller',
    imageBg: 'linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%)',
    iconText: '540W PV',
  },
  {
    id: 'prod-2',
    name: 'Adani Solar 580W N-Type TopCon Bifacial Module',
    category: 'panels',
    brand: 'Adani Solar',
    rating: 4.95,
    reviews: 94,
    specs: '580W · 22.5% TopCon Tech · Dual Glass · Low LID/PID',
    warranty: '30-Year Linear Warranty',
    price: 15200,
    mrp: 18500,
    subsidyEligible: true,
    inStock: 28,
    badge: 'Top Efficiency',
    imageBg: 'linear-gradient(135deg, #065f46 0%, #10b981 100%)',
    iconText: '580W TOPCON',
  },
  {
    id: 'prod-3',
    name: 'Solis 5kW Hybrid Grid-Tie Inverter (WiFi Integrated)',
    category: 'inverters',
    brand: 'Ginlong Solis',
    rating: 4.85,
    reviews: 156,
    specs: '5kW Single Phase · Dual MPPT · 97.8% Efficiency · Smart App Telemetry',
    warranty: '10-Year Comprehensive Replacement Warranty',
    price: 68000,
    mrp: 79000,
    subsidyEligible: true,
    inStock: 12,
    badge: 'MNRE Certified',
    imageBg: 'linear-gradient(135deg, #4338ca 0%, #6366f1 100%)',
    iconText: '5kW INVERTER',
  },
  {
    id: 'prod-4',
    name: 'Growatt 10kW 3-Phase Commercial Solar Inverter',
    category: 'inverters',
    brand: 'Growatt New Energy',
    rating: 4.9,
    reviews: 73,
    specs: '10kW 3-Phase 415V · Dual MPPT · Integrated AFCI Arc Fault · IP66',
    warranty: '10-Year Factory Warranty',
    price: 118000,
    mrp: 135000,
    subsidyEligible: false,
    inStock: 6,
    badge: 'Commercial Grade',
    imageBg: 'linear-gradient(135deg, #312e81 0%, #4f46e5 100%)',
    iconText: '10kW 3-PHASE',
  },
  {
    id: 'prod-5',
    name: 'SolarFlow PowerWall 5.12 kWh LiFePO4 Battery Storage',
    category: 'batteries',
    brand: 'SolarFlow Energy',
    rating: 4.95,
    reviews: 82,
    specs: '51.2V 100Ah · 6,000 Cycles @ 80% DOD · Built-in Smart BMS with CAN/RS485',
    warranty: '10-Year Battery Warranty',
    price: 124000,
    mrp: 145000,
    subsidyEligible: false,
    inStock: 8,
    badge: 'Lithium Safe',
    imageBg: 'linear-gradient(135deg, #701a75 0%, #c026d3 100%)',
    iconText: '5.12kWh LiFePO4',
  },
  {
    id: 'prod-6',
    name: 'SolarFlow Stackable 10.24 kWh High-Voltage Battery Pack',
    category: 'batteries',
    brand: 'SolarFlow Energy',
    rating: 5.0,
    reviews: 41,
    specs: '102.4V 100Ah · Modular Expansion up to 40kWh · Off-Grid UPS Instant Backup',
    warranty: '10-Year Battery Warranty',
    price: 235000,
    mrp: 265000,
    subsidyEligible: false,
    inStock: 4,
    badge: 'Whole Home Backup',
    imageBg: 'linear-gradient(135deg, #831843 0%, #db2777 100%)',
    iconText: '10.24kWh HIGH-VOLT',
  },
  {
    id: 'prod-7',
    name: 'Automatic Solar Rooftop Sprinkler Cleaning Kit',
    category: 'accessories',
    brand: 'SolarClean Pro',
    rating: 4.8,
    reviews: 215,
    specs: '10-Nozzle High Pressure · 0.5 HP Booster Pump · WiFi Timer Automation',
    warranty: '2-Year Anti-Clog Warranty',
    price: 4999,
    mrp: 6500,
    subsidyEligible: false,
    inStock: 35,
    badge: 'Restores +18% Yield',
    imageBg: 'linear-gradient(135deg, #0284c7 0%, #38bdf8 100%)',
    iconText: 'SPRINKLER KIT',
  },
  {
    id: 'prod-8',
    name: 'BESCOM Approved 3-Phase Bi-directional Net Meter',
    category: 'accessories',
    brand: 'Secure Meters',
    rating: 4.9,
    reviews: 164,
    specs: '3-Phase 4-Wire · Class 1.0 Accuracy · DLMS Compliant with NABL Test Certificate',
    warranty: '5-Year Utility Replacement Warranty',
    price: 6800,
    mrp: 8200,
    subsidyEligible: true,
    inStock: 19,
    badge: 'DISCOM Certified',
    imageBg: 'linear-gradient(135deg, #0f766e 0%, #14b8a6 100%)',
    iconText: 'NET METER',
  },
  {
    id: 'prod-9',
    name: 'AC & DC Protection Distribution Box (with Type 2 SPD)',
    category: 'accessories',
    brand: 'Hensel Solar',
    rating: 4.75,
    reviews: 88,
    specs: '1000V DC SPD + 415V AC SPD · 32A MCB/MCCB · IP65 Weatherproof Enclosure',
    warranty: '5-Year Anti-Surge Warranty',
    price: 8500,
    mrp: 10500,
    subsidyEligible: false,
    inStock: 25,
    badge: 'Surge Safe',
    imageBg: 'linear-gradient(135deg, #b45309 0%, #f59e0b 100%)',
    iconText: 'AC/DC DB BOX',
  },
  {
    id: 'prod-10',
    name: '1-Year Annual Maintenance Contract (AMC) - 4 Inspections',
    category: 'services',
    brand: 'SolarOps Field Engineering',
    rating: 4.95,
    reviews: 310,
    specs: 'Quarterly Deep Panel Wash · Thermographic Drone Scan · Firmware Update · Priority Dispatch',
    warranty: 'Zero Breakdown Guarantee',
    price: 3999,
    mrp: 5500,
    subsidyEligible: false,
    inStock: 999,
    badge: 'Popular Add-On',
    imageBg: 'linear-gradient(135deg, #15803d 0%, #22c55e 100%)',
    iconText: 'AMC 4-VISITS',
  },
];

export function SolarStore() {
  const { user, showToast } = useAuth();
  const { navigate } = useRouter();

  const [selectedCategory, setSelectedCategory] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState('featured');
  const [cart, setCart] = useState({});
  const [isCartOpen, setIsCartOpen] = useState(false);
  const [paymentMethod, setPaymentMethod] = useState('upi');
  const [deliveryAddress, setDeliveryAddress] = useState(
    '#42, 4th Cross, 100ft Road, Indiranagar, Bengaluru - 560038'
  );
  const [orderPlaced, setOrderPlaced] = useState(null);

  // Load existing cart or orders from localStorage
  useEffect(() => {
    try {
      const savedCart = localStorage.getItem('solarops_cart');
      if (savedCart) {
        setCart(JSON.parse(savedCart));
      }
    } catch (e) {
      // ignore
    }
  }, []);

  const saveCart = (newCart) => {
    setCart(newCart);
    try {
      localStorage.setItem('solarops_cart', JSON.stringify(newCart));
    } catch (e) {
      // ignore
    }
  };

  const handleAddToCart = (product, quantity = 1) => {
    const newCart = { ...cart };
    const currentQty = newCart[product.id]?.quantity || 0;
    newCart[product.id] = {
      product,
      quantity: currentQty + quantity,
    };
    saveCart(newCart);

    if (showToast) {
      showToast({
        type: 'success',
        title: 'Added to Cart',
        message: `${product.name} (x${quantity}) added to your solar cart.`,
      });
    }
  };

  const handleUpdateQuantity = (productId, delta) => {
    const newCart = { ...cart };
    if (!newCart[productId]) return;

    const newQty = newCart[productId].quantity + delta;
    if (newQty <= 0) {
      delete newCart[productId];
    } else {
      newCart[productId].quantity = newQty;
    }
    saveCart(newCart);
  };

  const handleRemoveFromCart = (productId) => {
    const newCart = { ...cart };
    delete newCart[productId];
    saveCart(newCart);
  };

  const cartItems = Object.values(cart);
  const cartCount = cartItems.reduce((acc, item) => acc + item.quantity, 0);
  const subtotal = cartItems.reduce(
    (acc, item) => acc + item.product.price * item.quantity,
    0
  );
  const gstRate = 0.12; // 12% GST on solar equipment
  const gstAmount = Math.round(subtotal * gstRate);
  const deliveryCharge = subtotal > 5000 || subtotal === 0 ? 0 : 499;
  const grandTotal = subtotal + gstAmount + deliveryCharge;

  // Filter & Sort
  const filteredProducts = PRODUCTS.filter((p) => {
    const matchesCategory =
      selectedCategory === 'all' || p.category === selectedCategory;
    const matchesSearch =
      p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.brand.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.specs.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCategory && matchesSearch;
  }).sort((a, b) => {
    if (sortBy === 'price_low') return a.price - b.price;
    if (sortBy === 'price_high') return b.price - a.price;
    if (sortBy === 'rating') return b.rating - a.rating;
    return 0; // featured
  });

  const handleCheckout = (e) => {
    e.preventDefault();
    if (cartItems.length === 0) return;

    const orderId = 'ORD-2026-' + Math.floor(1000 + Math.random() * 9000);
    const orderData = {
      orderId,
      items: cartItems.map((item) => ({
        id: item.product.id,
        name: item.product.name,
        price: item.product.price,
        quantity: item.quantity,
      })),
      subtotal,
      gstAmount,
      grandTotal,
      customerName: user?.name || 'Arun Kumar',
      address: deliveryAddress,
      paymentMethod,
      orderDate: new Date().toLocaleDateString('en-IN'),
      status: 'Confirmed · Staged at Bengaluru Warehouse',
    };

    // Save order in localStorage
    try {
      const existing = JSON.parse(localStorage.getItem('solarops_orders') || '[]');
      existing.unshift(orderData);
      localStorage.setItem('solarops_orders', JSON.stringify(existing));
    } catch (err) {
      // ignore
    }

    // Clear cart
    saveCart({});
    setOrderPlaced(orderData);

    if (showToast) {
      showToast({
        type: 'success',
        title: 'Order Confirmed!',
        message: `Order #${orderId} booked successfully. Dispatched within 24h.`,
      });
    }
  };

  return (
    <AppShell requiredRole="customer">
      <div className="solar-store-page">
        {/* Page Top Banner */}
        <div className="solar-store-hero">
          <div className="hero-content-col">
            <div className="hero-badge-tag">
              <Zap size={14} color="#fbbf24" />
              <span>Official SolarFlow Hardware Marketplace</span>
            </div>
            <h1 className="hero-title">
              Tier-1 Solar Panels, Inverters & Storage
            </h1>
            <p className="hero-subtitle">
              Order direct-from-warehouse solar hardware, automated sprinkler
              washers, LiFePO4 batteries, and genuine BOS spares with free delivery
              across Bengaluru.
            </p>
            <div className="hero-trust-chips">
              <span>✓ 25-Year Manufacturer Warranty</span>
              <span>✓ Free 24h Bengaluru Staging</span>
              <span>✓ PM Surya Ghar Subsidy Approved</span>
            </div>
          </div>

          <div className="hero-cart-col">
            <button
              type="button"
              className="store-cart-toggle-btn"
              onClick={() => setIsCartOpen(true)}
            >
              <ShoppingCart size={20} />
              <span>Solar Cart</span>
              <span className="cart-badge-count">{cartCount}</span>
            </button>
          </div>
        </div>

        {/* Filter & Search Bar */}
        <div className="store-controls-row">
          {/* Category Tabs */}
          <div className="category-chips-group">
            {[
              { id: 'all', label: 'All Hardware' },
              { id: 'panels', label: 'Solar Panels (PV)' },
              { id: 'inverters', label: 'Inverters & MPPT' },
              { id: 'batteries', label: 'Battery Storage' },
              { id: 'accessories', label: 'BOS & Accessories' },
              { id: 'services', label: 'AMC & Services' },
            ].map((cat) => (
              <button
                key={cat.id}
                type="button"
                className={`category-pill ${selectedCategory === cat.id ? 'active' : ''}`}
                onClick={() => setSelectedCategory(cat.id)}
              >
                {cat.label}
              </button>
            ))}
          </div>

          {/* Search & Sort */}
          <div className="store-search-sort-group">
            <div className="store-search-box">
              <Search size={16} color="#64748b" />
              <input
                type="text"
                placeholder="Search panels, inverters, batteries…"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
              {searchQuery && (
                <button
                  type="button"
                  className="clear-search-btn"
                  onClick={() => setSearchQuery('')}
                >
                  <X size={14} />
                </button>
              )}
            </div>

            <select
              className="store-sort-select"
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
            >
              <option value="featured">Featured Hardware</option>
              <option value="price_low">Price: Low to High</option>
              <option value="price_high">Price: High to Low</option>
              <option value="rating">Highest Rated</option>
            </select>
          </div>
        </div>

        {/* Product Catalog Grid */}
        <div className="store-products-grid">
          {filteredProducts.map((product) => {
            const inCartQty = cart[product.id]?.quantity || 0;

            return (
              <div key={product.id} className="store-product-card">
                {/* Visual Banner Thumbnail */}
                <div
                  className="product-thumbnail-box"
                  style={{ background: product.imageBg }}
                >
                  <span className="product-category-tag">{product.category}</span>
                  <span className="product-icon-text">{product.iconText}</span>
                  {product.badge && (
                    <span className="product-ribbon-badge">{product.badge}</span>
                  )}
                </div>

                {/* Body */}
                <div className="product-card-body">
                  <div className="product-meta-row">
                    <span className="product-brand">{product.brand}</span>
                    <div className="product-rating">
                      <Star size={13} fill="#f59e0b" color="#f59e0b" />
                      <span>{product.rating}</span>
                      <span className="review-count">({product.reviews})</span>
                    </div>
                  </div>

                  <h3 className="product-title">{product.name}</h3>

                  <p className="product-specs-desc">{product.specs}</p>

                  <div className="product-perks-row">
                    <span className="product-warranty-chip">
                      <ShieldCheck size={12} color="#10b981" />
                      <span>{product.warranty}</span>
                    </span>
                    {product.subsidyEligible && (
                      <span className="subsidy-tag">
                        <Tag size={11} />
                        <span>Subsidy Eligible</span>
                      </span>
                    )}
                  </div>

                  {/* Pricing Row */}
                  <div className="product-pricing-row">
                    <div>
                      <div className="product-price">
                        ₹{product.price.toLocaleString('en-IN')}
                      </div>
                      <div className="product-mrp-box">
                        <span className="mrp-strikethrough">
                          ₹{product.mrp.toLocaleString('en-IN')}
                        </span>
                        <span className="discount-chip">
                          {Math.round(
                            ((product.mrp - product.price) / product.mrp) * 100
                          )}
                          % OFF
                        </span>
                      </div>
                    </div>

                    <div className="stock-indicator">
                      <span className="stock-dot" />
                      <span>{product.inStock} in stock</span>
                    </div>
                  </div>

                  {/* Add to Cart Actions */}
                  <div className="product-card-actions">
                    {inCartQty > 0 ? (
                      <div className="qty-counter-group">
                        <button
                          type="button"
                          className="qty-btn"
                          onClick={() => handleUpdateQuantity(product.id, -1)}
                        >
                          <Minus size={14} />
                        </button>
                        <span className="qty-number">{inCartQty} in cart</span>
                        <button
                          type="button"
                          className="qty-btn"
                          onClick={() => handleUpdateQuantity(product.id, 1)}
                        >
                          <Plus size={14} />
                        </button>
                      </div>
                    ) : (
                      <button
                        type="button"
                        className="btn-add-cart"
                        onClick={() => handleAddToCart(product, 1)}
                      >
                        <ShoppingCart size={15} />
                        <span>Add to Cart</span>
                      </button>
                    )}

                    <button
                      type="button"
                      className="btn-buy-instant"
                      onClick={() => {
                        handleAddToCart(product, 1);
                        setIsCartOpen(true);
                      }}
                    >
                      <span>Buy Now</span>
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Shopping Cart Drawer / Modal */}
        {isCartOpen && (
          <div className="cart-drawer-overlay" onClick={() => setIsCartOpen(false)}>
            <div
              className="cart-drawer-panel"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Drawer Header */}
              <div className="cart-drawer-header">
                <div className="cart-header-title">
                  <ShoppingBag size={20} color="#4f46e5" />
                  <h3>Solar Order Cart ({cartCount})</h3>
                </div>
                <button
                  type="button"
                  className="cart-close-btn"
                  onClick={() => setIsCartOpen(false)}
                >
                  <X size={18} />
                </button>
              </div>

              {/* Drawer Content */}
              {cartItems.length === 0 ? (
                <div className="cart-empty-box">
                  <ShoppingCart size={48} color="#cbd5e1" />
                  <h4>Your Solar Cart is Empty</h4>
                  <p>
                    Browse high-efficiency modules, hybrid inverters, and BOS
                    accessories to add to your installation.
                  </p>
                  <button
                    type="button"
                    className="btn-add-cart"
                    style={{ margin: '14px auto 0 auto', width: 'auto' }}
                    onClick={() => setIsCartOpen(false)}
                  >
                    Start Shopping
                  </button>
                </div>
              ) : (
                <form onSubmit={handleCheckout} className="cart-drawer-body">
                  {/* Cart Item List */}
                  <div className="cart-items-list">
                    {cartItems.map(({ product, quantity }) => (
                      <div key={product.id} className="cart-item-row">
                        <div
                          className="cart-item-thumb"
                          style={{ background: product.imageBg }}
                        >
                          <span>{product.iconText}</span>
                        </div>
                        <div className="cart-item-info">
                          <h4 className="cart-item-name">{product.name}</h4>
                          <div className="cart-item-price">
                            ₹{product.price.toLocaleString('en-IN')} × {quantity}
                          </div>
                          <div className="cart-item-actions">
                            <div className="cart-item-stepper">
                              <button
                                type="button"
                                onClick={() =>
                                  handleUpdateQuantity(product.id, -1)
                                }
                              >
                                <Minus size={12} />
                              </button>
                              <span>{quantity}</span>
                              <button
                                type="button"
                                onClick={() => handleUpdateQuantity(product.id, 1)}
                              >
                                <Plus size={12} />
                              </button>
                            </div>
                            <button
                              type="button"
                              className="cart-item-remove"
                              onClick={() => handleRemoveFromCart(product.id)}
                            >
                              <Trash2 size={13} />
                              <span>Remove</span>
                            </button>
                          </div>
                        </div>
                        <div className="cart-item-subtotal">
                          ₹{(product.price * quantity).toLocaleString('en-IN')}
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Delivery Address */}
                  <div className="cart-address-box">
                    <label>Bengaluru Delivery Address</label>
                    <textarea
                      rows={2}
                      value={deliveryAddress}
                      onChange={(e) => setDeliveryAddress(e.target.value)}
                      required
                    />
                  </div>

                  {/* Payment Options */}
                  <div className="cart-payment-options">
                    <label>Select Payment Option</label>
                    <div className="payment-radios">
                      <label
                        className={`payment-radio-pill ${paymentMethod === 'upi' ? 'selected' : ''}`}
                      >
                        <input
                          type="radio"
                          name="paymentMethod"
                          value="upi"
                          checked={paymentMethod === 'upi'}
                          onChange={() => setPaymentMethod('upi')}
                        />
                        <span>⚡ UPI / Instant QR / Cards (Razorpay)</span>
                      </label>
                      <label
                        className={`payment-radio-pill ${paymentMethod === 'subsidy' ? 'selected' : ''}`}
                      >
                        <input
                          type="radio"
                          name="paymentMethod"
                          value="subsidy"
                          checked={paymentMethod === 'subsidy'}
                          onChange={() => setPaymentMethod('subsidy')}
                        />
                        <span>🏛️ Offset with PM Surya Ghar Subsidy Balance</span>
                      </label>
                      <label
                        className={`payment-radio-pill ${paymentMethod === 'cod' ? 'selected' : ''}`}
                      >
                        <input
                          type="radio"
                          name="paymentMethod"
                          value="cod"
                          checked={paymentMethod === 'cod'}
                          onChange={() => setPaymentMethod('cod')}
                        />
                        <span>🚚 Pay on Delivery & Inspection</span>
                      </label>
                    </div>
                  </div>

                  {/* Bill Breakdown */}
                  <div className="cart-bill-summary">
                    <div className="bill-line">
                      <span>Subtotal ({cartCount} items)</span>
                      <span>₹{subtotal.toLocaleString('en-IN')}</span>
                    </div>
                    <div className="bill-line">
                      <span>Solar GST (12%)</span>
                      <span>₹{gstAmount.toLocaleString('en-IN')}</span>
                    </div>
                    <div className="bill-line">
                      <span>Bengaluru Warehouse Delivery</span>
                      <span>{deliveryCharge === 0 ? 'FREE' : `₹${deliveryCharge}`}</span>
                    </div>
                    <div className="bill-line grand-total">
                      <span>Grand Total</span>
                      <span>₹{grandTotal.toLocaleString('en-IN')}</span>
                    </div>
                  </div>

                  {/* Checkout Button */}
                  <button type="submit" className="btn-confirm-checkout">
                    <CreditCard size={17} />
                    <span>
                      Place Order · ₹{grandTotal.toLocaleString('en-IN')}
                    </span>
                    <ArrowRight size={16} />
                  </button>
                </form>
              )}
            </div>
          </div>
        )}

        {/* Order Confirmed Success Modal */}
        {orderPlaced && (
          <div className="order-modal-backdrop">
            <div className="order-modal-card">
              <div className="order-modal-icon">
                <CheckCircle2 size={46} color="#10b981" />
              </div>
              <h2 className="order-modal-title">Solar Order Confirmed!</h2>
              <p className="order-modal-ref">
                Reference ID: <strong>{orderPlaced.orderId}</strong>
              </p>
              <p className="order-modal-sub">
                Your hardware order has been queued at the Bengaluru warehouse.
                Our logistics dispatch team will verify and deliver within 24-48 hours.
              </p>

              <div className="order-summary-box">
                <div className="order-summary-row">
                  <span>Customer:</span>
                  <strong>{orderPlaced.customerName}</strong>
                </div>
                <div className="order-summary-row">
                  <span>Total Settled:</span>
                  <strong>₹{orderPlaced.grandTotal.toLocaleString('en-IN')}</strong>
                </div>
                <div className="order-summary-row">
                  <span>Delivery To:</span>
                  <span>{orderPlaced.address}</span>
                </div>
                <div className="order-summary-row">
                  <span>Est. Delivery:</span>
                  <strong>Tomorrow by 5:00 PM IST</strong>
                </div>
              </div>

              <div className="order-modal-actions">
                <button
                  type="button"
                  className="btn-add-cart"
                  onClick={() => setOrderPlaced(null)}
                >
                  Continue Browsing Store
                </button>
                <button
                  type="button"
                  className="btn-buy-instant"
                  onClick={() => {
                    setOrderPlaced(null);
                    navigate('/customer');
                  }}
                >
                  Back to Dashboard
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}

export default SolarStore;
