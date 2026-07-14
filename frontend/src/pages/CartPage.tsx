import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useCartStore, useUIStore } from "../store";
import { PROMO_CODES } from "../lib/products";
import RecommendationRail from "../components/ui/RecommendationRail";
import { PRODUCTS, TRENDING_IDS, getById } from "../lib/products";

export default function CartPage() {
  const navigate   = useNavigate();
  const { items, updateQty, removeItem, clearCart, totalPrice, totalMRP, totalDiscount } = useCartStore();
  const addToast   = useUIStore((s) => s.addToast);

  const [promoInput, setPromoInput]   = useState("");
  const [promoApplied, setPromoApplied] = useState<string | null>(null);
  const [address, setAddress]         = useState("Flat 4B, Lotus Tower, Andheri West, Mumbai - 400053");

  const sub      = totalPrice();
  const mrp      = totalMRP();
  const saved    = totalDiscount();
  const del      = sub >= 199 ? 0 : 25;

  let promoDiscount = 0;
  if (promoApplied && PROMO_CODES[promoApplied]) {
    const pc = PROMO_CODES[promoApplied];
    if (pc.type === "pct")      promoDiscount = Math.min(Math.round(sub * pc.val / 100), pc.max);
    else if (pc.type === "flat") promoDiscount = Math.min(pc.val, sub);
  }
  const freeDelivery = promoApplied && PROMO_CODES[promoApplied]?.type === "free_del";
  const total = sub + (freeDelivery ? 0 : del) - promoDiscount;

  function handleApplyPromo() {
    const code = promoInput.trim().toUpperCase();
    if (PROMO_CODES[code]) {
      setPromoApplied(code);
      addToast(`${PROMO_CODES[code].label} applied! 🎉`);
    } else {
      addToast("Invalid promo code", "error");
    }
  }

  function handleCheckout() {
    clearCart();
    const orderId = "ZPT" + Math.floor(10000 + Math.random() * 90000);
    addToast(`Order #${orderId} confirmed! Arriving in 10 min 🛵`);
    navigate("/home");
  }

  const upsell = TRENDING_IDS
    .map(getById)
    .filter((p) => p && !items.find((e) => e.product.id === p!.id))
    .slice(0, 8) as ReturnType<typeof getById>[];

  if (!items.length) {
    return (
      <div className="page cart-page">
        <header className="page-header">
          <button className="back-btn" onClick={() => navigate(-1)}>‹</button>
          <h1>My Cart</h1>
        </header>
        <div className="empty-state">
          <div className="empty-icon">🛒</div>
          <h2>Your cart is empty</h2>
          <p>Add items to get started</p>
          <button className="btn-primary" onClick={() => navigate("/home")}>
            Start shopping
          </button>
        </div>
        {upsell.length > 0 && (
          <RecommendationRail
            title="You might like"
            emoji="💡"
            products={upsell as any[]}
            page="cart"
          />
        )}
      </div>
    );
  }

  return (
    <div className="page cart-page">
      <header className="page-header">
        <button className="back-btn" onClick={() => navigate(-1)}>‹</button>
        <h1>My Cart</h1>
        <button className="clear-cart-btn" onClick={clearCart}>Clear</button>
      </header>

      {/* Delivery strip */}
      <div className="delivery-strip">
        <span>⚡</span>
        <span>Delivery in <strong>10 minutes</strong> to Andheri West</span>
      </div>

      <div className="cart-content">

        {/* Cart items with real Zepto CDN images */}
        <div className="cart-items">
          {items.map(({ product: p, quantity }) => (
            <div key={p.id} className="cart-item">
              <div className="ci-img">
                <img src={p.src} alt={p.name} loading="lazy"
                  onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }} />
              </div>
              <div className="ci-info">
                <p className="ci-name">{p.name}</p>
                <p className="ci-unit">{p.unit}</p>
                <div className="ci-prices">
                  <span className="ci-price">₹{p.disc}</span>
                  {p.price > p.disc && <span className="ci-mrp">₹{p.price}</span>}
                </div>
              </div>
              <div className="ci-controls">
                <div className="qty-ctrl">
                  <button onClick={() => updateQty(p.id, quantity - 1)}>−</button>
                  <span>{quantity}</span>
                  <button onClick={() => updateQty(p.id, quantity + 1)}>+</button>
                </div>
                <p className="ci-total">₹{p.disc * quantity}</p>
                <button className="ci-remove" onClick={() => removeItem(p.id)}>✕</button>
              </div>
            </div>
          ))}
        </div>

        {/* Upsell rail */}
        {upsell.length > 0 && (
          <RecommendationRail
            title="Add more items"
            emoji="🛍️"
            products={upsell as any[]}
            page="cart"
          />
        )}

        {/* Delivery address */}
        <div className="cart-section">
          <h3>📍 Delivery address</h3>
          <input
            className="address-input"
            value={address}
            onChange={(e) => setAddress(e.target.value)}
            placeholder="Enter delivery address"
          />
        </div>

        {/* Promo code */}
        <div className="cart-section">
          <h3>🏷️ Promo code</h3>
          {promoApplied ? (
            <div className="promo-applied-row">
              <div>
                <p className="promo-code-label">{promoApplied}</p>
                <p className="promo-code-sub">{PROMO_CODES[promoApplied]?.label}</p>
              </div>
              <button onClick={() => { setPromoApplied(null); setPromoInput(""); }}>
                ✕ Remove
              </button>
            </div>
          ) : (
            <>
              <div className="promo-row">
                <input
                  className="promo-input"
                  value={promoInput}
                  onChange={(e) => setPromoInput(e.target.value.toUpperCase())}
                  placeholder="Enter code (ZEPTO10, FLAT50, FRESH20)"
                />
                <button className="promo-apply-btn" onClick={handleApplyPromo}
                  disabled={!promoInput}>Apply</button>
              </div>
              <div className="promo-chips">
                {Object.keys(PROMO_CODES).map((code) => (
                  <button key={code} className="promo-chip"
                    onClick={() => { setPromoInput(code); }}>
                    {code}
                  </button>
                ))}
              </div>
            </>
          )}
        </div>

        {/* Bill summary */}
        <div className="bill-summary">
          <h3>💳 Bill summary</h3>
          <div className="bill-row"><span>MRP total</span><span>₹{mrp}</span></div>
          <div className="bill-row green"><span>Product discount</span><span>−₹{saved}</span></div>
          <div className="bill-row"><span>Delivery fee</span>
            <span>{(del === 0 || freeDelivery) ? <span className="free-text">FREE ✓</span> : `₹${del}`}</span>
          </div>
          {promoDiscount > 0 && (
            <div className="bill-row green"><span>Promo ({promoApplied})</span><span>−₹{promoDiscount}</span></div>
          )}
          {del > 0 && !freeDelivery && (
            <p className="free-delivery-hint">Add ₹{199 - sub} more for free delivery</p>
          )}
          <div className="bill-row total"><span>Total</span><span>₹{total}</span></div>
        </div>

      </div>

      {/* Checkout bar */}
      <div className="checkout-bar">
        <div className="checkout-info">
          <span className="checkout-total">₹{total}</span>
          <span className="checkout-saved">
            {saved + promoDiscount > 0 ? `Saved ₹${saved + promoDiscount}` : `${items.length} item${items.length > 1 ? "s" : ""}`}
          </span>
        </div>
        <button className="checkout-btn" onClick={handleCheckout}>
          Place order →
        </button>
      </div>
    </div>
  );
}
