/**
 * Order Tracking Page — live animated map, progress steps, rider info
 */
import { useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useCartStore } from "../store";
import { getById } from "../lib/products";

const GOPI = "https://images.unsplash.com/photo-1607746882042-944635dfe10e?auto=format&fit=crop&w=200&q=80";

const STEPS = [
  { title: "Order confirmed",     sub: "We received your order",              icon: "📋" },
  { title: "Picking your items",  sub: "Packing fresh from our dark store",   icon: "📦" },
  { title: "Out for delivery",    sub: "Raju is riding to you now",           icon: "🛵" },
  { title: "Delivered",          sub: "Enjoy your fresh groceries!",          icon: "✅" },
];

const RIDER = {
  name:      "Raju Kumar",
  rating:    4.9,
  deliveries: 2341,
  vehicle:   "Hero Splendor · MH-04-AB-1234",
};

export default function OrderTrackingPage() {
  const navigate    = useNavigate();
  const [params]    = useSearchParams();
  const { items }   = useCartStore();

  const orderId     = params.get("orderId") ?? "ZPT12345";
  const [step, setStep]   = useState(1);   // 0-3
  const [mins, setMins]   = useState(10);
  const [riderPos, setRiderPos] = useState(15); // % from left
  const timerRef    = useRef<ReturnType<typeof setInterval>>();
  const riderRef    = useRef<ReturnType<typeof setInterval>>();

  // Countdown timer
  useEffect(() => {
    timerRef.current = setInterval(() => {
      setMins((m) => (m > 0 ? m - 1 : 0));
    }, 60_000);
    return () => clearInterval(timerRef.current);
  }, []);

  // Rider animation
  useEffect(() => {
    riderRef.current = setInterval(() => {
      setRiderPos((p) => {
        if (p >= 75) return 75;
        return p + 1;
      });
    }, 300);
    return () => clearInterval(riderRef.current);
  }, []);

  // Auto advance steps (demo)
  useEffect(() => {
    const t = setTimeout(() => {
      setStep((s) => Math.min(s + 1, 3));
    }, 6000);
    return () => clearTimeout(t);
  }, [step]);

  const eta = new Date(Date.now() + mins * 60_000).toLocaleTimeString([], {
    hour: "2-digit", minute: "2-digit",
  });

  // Use cart items or fallback to sample IDs
  const orderItems = items.length > 0
    ? items.map(({ product: p, quantity }) => ({ product: p, quantity }))
    : [0, 9, 23, 10].map((id) => ({ product: getById(id)!, quantity: 1 })).filter((x) => x.product);

  return (
    <div className="page track-page">
      <header className="page-header track-header">
        <button className="back-btn" onClick={() => navigate("/home")}>‹</button>
        <h1>Live Tracking</h1>
        <span className="track-order-id">#{orderId}</span>
      </header>

      <div className="track-body">

        {/* ── ETA Banner ── */}
        <div className="track-banner">
          <div className="track-eta-big">
            <span className="track-mins">{mins}</span>
            <span className="track-mins-label">min{mins !== 1 ? "s" : ""}</span>
          </div>
          <div className="track-banner-right">
            <p className="track-arriving">Arriving by {eta}</p>
            <div className="track-live-badge">
              <span className="dot-green" /> Live tracking
            </div>
          </div>
        </div>

        {/* ── Map ── */}
        <div className="track-map">
          {/* Road */}
          <div className="track-road" />
          {/* Route fill */}
          <div className="track-route-fill" style={{ width: `${riderPos}%` }} />
          {/* Store */}
          <div className="track-store-pin">🏪</div>
          {/* Rider */}
          <div className="track-rider-pin" style={{ left: `${riderPos}%` }}>🛵</div>
          {/* Home */}
          <div className="track-home-pin">🏠</div>
          {/* ETA bubble */}
          <div className="track-eta-bubble">{mins} min</div>
        </div>

        {/* ── Rider Card ── */}
        <div className="track-rider-card">
          <div className="rider-avatar">RK</div>
          <div className="rider-info">
            <p className="rider-name">{RIDER.name}</p>
            <p className="rider-meta">⭐ {RIDER.rating} · {RIDER.deliveries.toLocaleString()} deliveries</p>
            <p className="rider-vehicle">{RIDER.vehicle}</p>
          </div>
          <div className="rider-actions">
            <a href="tel:+919876543210" className="rider-btn rider-call">📞</a>
            <button className="rider-btn rider-chat" onClick={() => {}}>💬</button>
          </div>
        </div>

        {/* ── Progress Steps ── */}
        <div className="track-steps-section">
          <h3>Order progress</h3>
          <div className="track-steps-list">
            {STEPS.map((s, i) => (
              <div key={i} className="track-step">
                <div className={`step-dot${i < step ? " done" : i === step ? " active" : ""}`}>
                  {i < step ? "✓" : i === step ? "⚡" : "○"}
                </div>
                {i < STEPS.length - 1 && (
                  <div className={`step-line${i < step ? " done" : ""}`} />
                )}
                <div className="step-content">
                  <p className={`step-title${i < step ? " done" : i === step ? " active" : ""}`}>
                    {s.title}
                  </p>
                  <p className="step-sub">{s.sub}</p>
                  {i === step && (
                    <div className="step-progress-bar">
                      <div className="step-progress-fill" />
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* ── Order Items ── */}
        <div className="track-order-items">
          <h3>Your order</h3>
          {orderItems.slice(0, 5).map(({ product: p, quantity }, i) => (
            p && (
              <div key={i} className="track-item-row">
                <div className="track-item-img">
                  <img
                    src={p.src}
                    alt={p.name}
                    loading="lazy"
                    onError={(e) => { (e.target as HTMLImageElement).style.opacity = "0"; }}
                  />
                </div>
                <div className="track-item-name">{p.name}</div>
                <div className="track-item-qty">×{quantity}</div>
                <div className="track-item-price">₹{p.disc * quantity}</div>
              </div>
            )
          ))}
          {orderItems.length > 5 && (
            <p className="track-more-items">+{orderItems.length - 5} more items</p>
          )}
        </div>

        {/* ── Help section ── */}
        <div className="track-help-row">
          <button className="track-help-btn" onClick={() => navigate("/ai")}>
            <span>💬</span> Chat with Gopi Bahu
          </button>
          <button className="track-help-btn" onClick={() => {}}>
            <span>📞</span> Call support
          </button>
        </div>

      </div>
    </div>
  );
}
