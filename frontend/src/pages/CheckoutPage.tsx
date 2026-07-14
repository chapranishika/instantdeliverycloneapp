/**
 * Checkout Page — 3 steps: Address → Payment → Confirm
 *
 * Uses useCheckoutStore which previously crashed due to require() in applyPromo.
 * Now fixed — PROMO_CODES imported at module level in store/index.ts.
 */
import { useNavigate } from "react-router-dom";
import { useCartStore, useCheckoutStore, useUIStore } from "../store";
import { PROMO_CODES } from "../lib/products";
import { useState } from "react";

const ADDRESSES = [
  {
    id: 1,
    type: "🏠 Home",
    text: "Flat 4B, Lotus Tower, Lokhandwala Complex\nAndheri West, Mumbai — 400053",
  },
  {
    id: 2,
    type: "💼 Office",
    text: "WeWork 5th Floor, One BKC\nBandra Kurla Complex, Mumbai — 400051",
  },
];

const PAY_METHODS = [
  { id: "upi"  , icon: "📱", bg: "#E6F7F0", title: "UPI / GPay / PhonePe", sub: "Pay instantly with any UPI app"  },
  { id: "card" , icon: "💳", bg: "#EEF0FF", title: "Credit / Debit Card",  sub: "Visa, Mastercard, Amex accepted" },
  { id: "cod"  , icon: "💵", bg: "#FFF0EB", title: "Cash on delivery",      sub: "Pay when your order arrives"     },
  { id: "wallet", icon: "👛", bg: "#F3EAFF", title: "Zepto Wallet",         sub: "Balance: ₹250"                  },
] as const;

type PayId = typeof PAY_METHODS[number]["id"];

export default function CheckoutPage() {
  const navigate  = useNavigate();
  const addToast  = useUIStore((s) => s.addToast);
  const { items, totalPrice, totalMRP, totalDiscount, clearCart } = useCartStore();

  // ── Checkout store (ESM-safe now) ─────────────────────────────
  const {
    step, setStep,
    selectedAddressId, setAddress,
    selectedPayment, setPayment,
    promoCode, setPromoCode,
    promoApplied, promoDiscount, deliveryFree,
    applyPromo, clearPromo,
    reset,
  } = useCheckoutStore();

  const [placing, setPlacing] = useState(false);

  // Bill calculations
  const sub      = totalPrice();
  const mrp      = totalMRP();
  const saved    = totalDiscount();
  const delivery = sub >= 199 || deliveryFree ? 0 : 25;
  const total    = sub + delivery - promoDiscount;

  const stepIdx = ["address", "payment", "confirm"].indexOf(step);

  function handleBack() {
    if (step === "address")  { navigate("/cart"); return; }
    if (step === "payment")  { setStep("address"); return; }
    if (step === "confirm")  { setStep("payment"); return; }
  }

  function handleNext() {
    if (step === "address")  { setStep("payment"); return; }
    if (step === "payment")  { setStep("confirm");  return; }

    // Place order
    setPlacing(true);
    const orderId = "ZPT" + Math.floor(10000 + Math.random() * 90000);
    setTimeout(() => {
      clearCart();
      reset();
      setPlacing(false);
      navigate(`/success?orderId=${orderId}&total=${total}`);
    }, 900);
  }

  function handleApplyPromo() {
    // applyPromo now works correctly — no require() crash
    const result = applyPromo(promoCode, sub);
    if (result.ok) {
      addToast(`${result.message} 🎉`);
    } else {
      addToast(result.message, "error");
    }
  }

  const addr = ADDRESSES.find((a) => a.id === selectedAddressId) ?? ADDRESSES[0];
  const payM = PAY_METHODS.find((m) => m.id === selectedPayment)!;

  return (
    <div className="page checkout-page">
      <header className="page-header">
        <button className="back-btn" onClick={handleBack}>‹</button>
        <h1>Checkout</h1>
      </header>

      {/* Step indicator */}
      <div className="checkout-steps">
        {(["Address", "Payment", "Confirm"] as const).map((lbl, i) => (
          <div key={lbl} className="checkout-step">
            <div className={`co-num ${i < stepIdx ? "done" : i === stepIdx ? "active" : "idle"}`}>
              {i < stepIdx ? "✓" : i + 1}
            </div>
            <div className={`co-lbl${i === stepIdx ? " active" : ""}`}>{lbl}</div>
            {i < 2 && <span className="co-arrow">›</span>}
          </div>
        ))}
      </div>

      {/* ── Step: Address ── */}
      <div className="checkout-body">
        {step === "address" && (
          <>
            <h3 className="co-section-title">📍 Select delivery address</h3>
            {ADDRESSES.map((a) => (
              <div
                key={a.id}
                className={`addr-card${selectedAddressId === a.id ? " selected" : ""}`}
                onClick={() => setAddress(a.id)}
              >
                <div className="addr-type">{a.type}</div>
                <div className="addr-text">
                  {a.text.split("\n").map((l, i) => <span key={i}>{l}<br /></span>)}
                </div>
                <div className="addr-check">✓</div>
              </div>
            ))}
            <button
              className="addr-add"
              onClick={() => addToast("Address form coming soon")}
            >
              <span>+</span> Add new address
            </button>
          </>
        )}

        {/* ── Step: Payment ── */}
        {step === "payment" && (
          <>
            <h3 className="co-section-title">💳 Payment method</h3>
            {PAY_METHODS.map((m) => (
              <div
                key={m.id}
                className={`pay-method${selectedPayment === m.id ? " selected" : ""}`}
                onClick={() => setPayment(m.id as PayId)}
              >
                <div className="pay-icon" style={{ background: m.bg }}>{m.icon}</div>
                <div className="pay-info">
                  <div className="pay-title">{m.title}</div>
                  <div className="pay-sub">{m.sub}</div>
                </div>
                <div className={`pay-radio${selectedPayment === m.id ? " on" : ""}`} />
              </div>
            ))}

            <h3 className="co-section-title" style={{ marginTop: 8 }}>🏷️ Promo code</h3>

            {promoApplied ? (
              <div className="promo-applied-box">
                <div>
                  <div className="promo-applied-code">{promoApplied}</div>
                  <div className="promo-applied-sub">
                    {PROMO_CODES[promoApplied]?.label}
                    {promoDiscount > 0 && ` — saving ₹${promoDiscount}`}
                  </div>
                </div>
                <button onClick={clearPromo}>✕ Remove</button>
              </div>
            ) : (
              <>
                <div className="promo-row">
                  <input
                    className="promo-input"
                    value={promoCode}
                    onChange={(e) => setPromoCode(e.target.value)}
                    placeholder="Enter code (ZEPTO10, FLAT50…)"
                    onKeyDown={(e) => e.key === "Enter" && handleApplyPromo()}
                  />
                  <button
                    className="promo-apply-btn"
                    onClick={handleApplyPromo}
                    disabled={!promoCode.trim()}
                  >
                    Apply
                  </button>
                </div>
                {/* Quick-fill chips */}
                <div className="promo-chips">
                  {Object.entries(PROMO_CODES).map(([code, info]) => (
                    <button
                      key={code}
                      className="promo-chip"
                      onClick={() => setPromoCode(code)}
                      title={info.label}
                    >
                      {code}
                    </button>
                  ))}
                </div>
                <p style={{ fontSize: 11, color: "var(--mu)", marginTop: 6 }}>
                  Try: ZEPTO10 · FLAT50 · FRESH20 · FIRST3
                </p>
              </>
            )}
          </>
        )}

        {/* ── Step: Confirm ── */}
        {step === "confirm" && (
          <>
            <h3 className="co-section-title">🧾 Order items</h3>
            <div className="confirm-items-box">
              {items.map(({ product: p, quantity }) => (
                <div key={p.id} className="confirm-item-row">
                  <div className="confirm-item-img">
                    <img src={p.src} alt={p.name} loading="lazy" />
                  </div>
                  <span className="confirm-item-name">{p.name}</span>
                  <span className="confirm-item-qty">×{quantity}</span>
                  <span className="confirm-item-price">₹{p.disc * quantity}</span>
                </div>
              ))}
            </div>

            <h3 className="co-section-title">📍 Delivering to</h3>
            <div className="confirm-info-box">
              <strong>{addr.type}</strong>
              <p>{addr.text.split("\n").join(", ")}</p>
            </div>

            <h3 className="co-section-title">💳 Payment</h3>
            <div className="confirm-info-box confirm-pay-row">
              <span className="confirm-pay-icon" style={{ background: payM.bg }}>
                {payM.icon}
              </span>
              <div>
                <div className="pay-title">{payM.title}</div>
                <div className="pay-sub">Paying ₹{total}</div>
              </div>
            </div>

            <h3 className="co-section-title">💰 Bill summary</h3>
            <div className="bill-summary">
              <div className="bill-row"><span>MRP total</span><span>₹{mrp}</span></div>
              <div className="bill-row green">
                <span>Product discount</span><span>−₹{saved}</span>
              </div>
              <div className="bill-row">
                <span>Delivery fee</span>
                <span>{delivery === 0
                  ? <span className="free-text">FREE ✓</span>
                  : `₹${delivery}`}
                </span>
              </div>
              {promoDiscount > 0 && (
                <div className="bill-row green">
                  <span>Promo ({promoApplied})</span>
                  <span>−₹{promoDiscount}</span>
                </div>
              )}
              {deliveryFree && (
                <div className="bill-row green">
                  <span>Promo ({promoApplied})</span>
                  <span>Free delivery ✓</span>
                </div>
              )}
              <div className="bill-row total">
                <span>Total</span><span>₹{total}</span>
              </div>
            </div>
          </>
        )}
      </div>

      {/* CTA bar — sticky at bottom */}
      <div className="checkout-bar">
        <div className="checkout-info">
          <div className="checkout-total">₹{total}</div>
          <div className="checkout-saved">
            {saved + promoDiscount > 0
              ? `Saved ₹${saved + promoDiscount}`
              : `${items.length} item${items.length !== 1 ? "s" : ""}`}
          </div>
        </div>
        <button
          className="checkout-btn"
          onClick={handleNext}
          disabled={placing || items.length === 0}
        >
          {placing ? "Placing…" : step === "confirm" ? "Place order 🎉" : "Continue →"}
        </button>
      </div>
    </div>
  );
}
