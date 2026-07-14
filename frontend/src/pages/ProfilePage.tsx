import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useUserStore, useCartStore, useWishlistStore, useUIStore } from "../store";
import { MOCK_ORDERS, getById } from "../lib/products";
import ProductCard from "../components/ui/ProductCard";

export default function ProfilePage() {
  const navigate  = useNavigate();
  const { user, logout, isLoggedIn } = useUserStore();
  const addItem   = useCartStore((s) => s.addItem);
  const { products: wlProducts, toggle } = useWishlistStore();
  const addToast  = useUIStore((s) => s.addToast);
  const [tab, setTab] = useState<"orders" | "wishlist" | "settings">("orders");

  const initials = user?.name
    ? user.name.split(" ").map((w) => w[0]).join("").toUpperCase().slice(0, 2)
    : "G";

  function reorder(itemIds: number[]) {
    itemIds.forEach((id) => {
      const p = getById(id);
      if (p) addItem(p);
    });
    addToast("Items added to cart 🛒");
    navigate("/cart");
  }

  return (
    <div className="page profile-page">
      <header className="page-header">
        <button className="back-btn" onClick={() => navigate(-1)}>‹</button>
        <h1>Profile</h1>
        {!isLoggedIn() && (
          <button
            className="sign-in-btn"
            onClick={() => navigate("/login")}
          >
            Sign in
          </button>
        )}
      </header>

      {/* ── Hero ── */}
      <div className="profile-hero">
        <div className="profile-avatar">{initials}</div>
        <div className="profile-info">
          <h2 className="profile-name">{user?.name ?? "Guest User"}</h2>
          <p className="profile-email">
            {user?.email ?? "Sign in for a personalised experience"}
          </p>
          {isLoggedIn() && (
            <div className="profile-badge">⚡ Zepto Member</div>
          )}
        </div>
      </div>

      {/* ── Stats ── */}
      <div className="profile-stats">
        {[["23", "Orders"], ["₹1.2k", "Saved"], ["4.9★", "Rating"]].map(([v, l]) => (
          <div key={l} className="profile-stat">
            <div className="ps-value">{v}</div>
            <div className="ps-label">{l}</div>
          </div>
        ))}
      </div>

      {/* ── Tabs ── */}
      <div className="profile-tabs">
        {(["orders", "wishlist", "settings"] as const).map((t) => (
          <button
            key={t}
            className={`profile-tab${tab === t ? " active" : ""}`}
            onClick={() => setTab(t)}
          >
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      {/* ── Orders ── */}
      {tab === "orders" && (
        <div className="orders-list">
          {MOCK_ORDERS.map((order) => (
            <div key={order.id} className="order-card">
              <div className="order-header">
                <div>
                  <p className="order-id">#{order.id}</p>
                  <p className="order-date">{order.date}</p>
                </div>
                <span className="order-status">{order.status}</span>
              </div>

              {/* Real product thumbnails from Zepto CDN */}
              <div className="order-items-row">
                {order.items.map((id) => {
                  const p = getById(id);
                  return p ? (
                    <img
                      key={id}
                      src={p.src}
                      alt={p.name}
                      className="order-thumb"
                      loading="lazy"
                      onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
                    />
                  ) : null;
                })}
                <span className="order-total">₹{order.total}</span>
              </div>

              <button
                className="order-reorder-btn"
                onClick={() => reorder(order.items)}
              >
                🔄 Reorder
              </button>
            </div>
          ))}
        </div>
      )}

      {/* ── Wishlist ── */}
      {tab === "wishlist" && (
        <>
          {wlProducts().length === 0 ? (
            <div className="empty-state" style={{ marginTop: 40 }}>
              <div className="empty-icon">♡</div>
              <h2>Nothing saved yet</h2>
              <p>Tap the heart on any product to save it here</p>
              <button className="btn-primary" onClick={() => navigate("/home")}>
                Explore products
              </button>
            </div>
          ) : (
            <div className="wishlist-grid">
              {wlProducts().map((p) => (
                <div key={p.id} className="wishlist-card">
                  <div className="wl-img-wrap">
                    <img
                      src={p.src}
                      alt={p.name}
                      loading="lazy"
                      onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
                    />
                    <button
                      className="wl-remove-btn"
                      onClick={() => { toggle(p.id); addToast("Removed from wishlist"); }}
                    >
                      ❤️
                    </button>
                    <div className="wl-del-badge">
                      <span className="bolt">⚡</span>10 min
                    </div>
                  </div>
                  <div className="wl-info">
                    <p className="wl-unit">{p.unit}</p>
                    <p className="wl-name">{p.name}</p>
                    <div className="wl-footer">
                      <div className="wl-prices">
                        <span className="wl-price">₹{p.disc}</span>
                        {p.price > p.disc && <span className="wl-mrp">₹{p.price}</span>}
                      </div>
                      <button
                        className="wl-add-btn"
                        onClick={() => { addItem(p); addToast(`${p.name} added 🛒`); }}
                      >
                        +
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {/* ── Settings ── */}
      {tab === "settings" && (
        <div className="settings-list">
          {[
            ["📍", "Saved Addresses",    "Andheri West, Mumbai"],
            ["💳", "Payment Methods",    "GPay · 2 cards saved"],
            ["🔔", "Notifications",      "Push & Email on"],
            ["🛡️", "Privacy & Security", "Data & permissions"],
            ["❓", "Help & Support",     "FAQ, chat, call centre"],
            ["🌙", "Dark Mode",          "System default"],
          ].map(([icon, title, sub]) => (
            <button
              key={title}
              className="settings-row"
              onClick={() => addToast(`Opening ${title}…`)}
            >
              <span className="settings-icon">{icon}</span>
              <div className="settings-text">
                <span className="settings-title">{title}</span>
                <span className="settings-sub">{sub}</span>
              </div>
              <span className="settings-chevron">›</span>
            </button>
          ))}

          {isLoggedIn() && (
            <button
              className="logout-btn"
              onClick={() => {
                logout();
                addToast("Signed out — see you soon!");
              }}
            >
              Sign out
            </button>
          )}
        </div>
      )}
    </div>
  );
}
