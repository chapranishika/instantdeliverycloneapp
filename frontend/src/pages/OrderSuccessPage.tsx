/**
 * Order Success Page — animated checkmark, ETA, order summary, track CTA
 */
import { useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useUIStore } from "../store";

export default function OrderSuccessPage() {
  const navigate   = useNavigate();
  const addToast   = useUIStore((s) => s.addToast);
  const [params]   = useSearchParams();

  const orderId = params.get("orderId") ?? "ZPT" + Math.floor(10000 + Math.random() * 90000);
  const total   = params.get("total") ?? "0";
  const eta     = new Date(Date.now() + 10 * 60 * 1000).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });

  useEffect(() => {
    // Vibrate on success if supported
    if (navigator.vibrate) navigator.vibrate([100, 50, 100]);
    addToast(`Order #${orderId} confirmed! 🎉`);
  }, []);

  return (
    <div className="page success-page">
      <div className="success-content">

        {/* Animated checkmark */}
        <div className="success-anim">✓</div>
        <h1 className="success-title">Order placed! 🎉</h1>
        <p className="success-sub">
          Your groceries are being picked<br />
          from our Andheri dark store
        </p>

        {/* ETA card */}
        <div className="eta-card">
          <div className="eta-left">
            <div className="eta-num">10</div>
            <div className="eta-unit">min</div>
          </div>
          <div className="eta-right">
            <p className="eta-order-id">#{orderId}</p>
            <p className="eta-rider">🛵 Raju Kumar ⭐ 4.9</p>
            <div className="eta-live">
              <span className="eta-dot" />
              <span>Live tracking active · ETA {eta}</span>
            </div>
          </div>
        </div>

        {/* Order info */}
        <div className="success-card">
          <h3>Order details</h3>
          <div className="success-row"><span>Order ID</span><span>#{orderId}</span></div>
          <div className="success-row"><span>Amount paid</span><span>₹{total}</span></div>
          <div className="success-row"><span>Delivery to</span><span>Andheri West</span></div>
          <div className="success-row"><span>Estimated ETA</span><span>{eta}</span></div>
          <div className="success-row"><span>Dark store</span><span>Andheri West Hub</span></div>
        </div>

        {/* Trust badges */}
        <div className="success-badges">
          <div className="success-badge">✓ Payment confirmed</div>
          <div className="success-badge">⚡ Rider assigned</div>
          <div className="success-badge">🌡️ Fresh & chilled</div>
        </div>

        {/* CTAs */}
        <div className="success-btns">
          <button
            className="btn-track"
            onClick={() => navigate(`/track?orderId=${orderId}`)}
          >
            🛵 Track live
          </button>
          <button
            className="btn-home"
            onClick={() => navigate("/home")}
          >
            🏠 Back to home
          </button>
        </div>

        {/* Reorder prompt */}
        <p className="success-hint">
          We'll notify you when your order is nearby 🔔
        </p>
      </div>
    </div>
  );
}
