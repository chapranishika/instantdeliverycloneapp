/**
 * Home Page — Real Zepto CDN images, ML-curated product rails.
 */
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import ProductCard from "../components/ui/ProductCard";
import RecommendationRail from "../components/ui/RecommendationRail";
import {
  PRODUCTS, CATEGORIES, TRENDING_IDS, FOR_YOU_IDS,
  FRESH_IDS, KITCHEN_HH_IDS, getById,
} from "../lib/products";
import { useCartStore, useUIStore } from "../store";

const HERO  = "https://images.unsplash.com/photo-1542838132-92c53300491e?auto=format&fit=crop&w=900&q=80";
const GOPI  = "/gopi_assistant.png";
const PROMOS = [
  { img: "https://images.unsplash.com/photo-1610348725531-843dff563e2c?auto=format&fit=crop&w=500&q=80", grad: "linear-gradient(to top,rgba(128,37,251,.85),rgba(128,37,251,.2))",  tag: "Free delivery", title: "First 3 orders free — FIRST3" },
  { img: "https://images.unsplash.com/photo-1465014925804-7b9ede58d0d7?auto=format&fit=crop&w=500&q=80", grad: "linear-gradient(to top,rgba(0,168,107,.85),rgba(0,168,107,.2))",   tag: "Farm fresh",    title: "Vegetables direct from farm" },
  { img: "https://images.unsplash.com/photo-1556742393-d75f468bfcb0?auto=format&fit=crop&w=500&q=80",  grad: "linear-gradient(to top,rgba(10,10,30,.9),rgba(10,10,30,.3))",       tag: "✨ Pass",       title: "Save 20% every month" },
];

const toList = (ids: number[]) => ids.map(getById).filter(Boolean) as ReturnType<typeof getById>[];

export default function HomePage() {
  const navigate   = useNavigate();
  const totalItems = useCartStore((s) => s.totalItems());
  const addToast   = useUIStore((s) => s.addToast);
  const [activeCat, setActiveCat] = useState("");

  const catProducts = activeCat
    ? PRODUCTS.filter((p) => p.type === activeCat)
    : [];

  return (
    <div className="page home-page">

      {/* ── Topbar ── */}
      <header className="topbar">
        <div className="logo">
          <img
            src="https://www.zeptonow.com/images/logo.svg"
            alt="Zepto"
            className="logo-img"
            onError={(e) => ((e.target as HTMLImageElement).style.display = "none")}
          />
          <span className="logo-text">zepto</span>
        </div>
        <button className="del-badge">
          <span className="dot-green" />
          <span>Delivering to Mumbai</span>
          <span className="chevron">▾</span>
        </button>
        <div className="topbar-right">
          <button className="icon-btn" onClick={() => navigate("/wishlist")}>♡</button>
          <button className="cart-chip" onClick={() => navigate("/cart")}>
            🛒{totalItems > 0 && <span className="cart-chip-count">{totalItems}</span>}
          </button>
        </div>
      </header>

      {/* ── Search bar ── */}
      <div className="search-bar-wrap" onClick={() => navigate("/search")}>
        <div className="search-bar">
          <span>🔍</span>
          <span className="search-ph">Search vegetables, fruits & more…</span>
          <span className="search-tag">10 min</span>
        </div>
      </div>

      <main className="home-main">

        {/* ── Hero with real grocery photo ── */}
        <section className="hero-section">
          <img src={HERO} alt="Fresh groceries" className="hero-img" loading="eager" />
          <div className="hero-overlay" />
          <div className="hero-content">
            <div className="hero-badge"><span>⚡</span><span>10-minute delivery — always</span></div>
            <h1 className="hero-title">
              Fresh groceries<br />in <em>10 minutes</em>,<br />every time.
            </h1>
            <div className="hero-stats">
              {[["10","min","Delivery"],["5k","+","Products"],["4.8","★","Rating"],["2M","+","Orders"]].map(([n,u,l]) => (
                <div className="stat" key={l}>
                  <div className="stat-num">{n}<span className="stat-unit">{u}</span></div>
                  <div className="stat-label">{l}</div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ── Category pills ── */}
        <div className="cat-scroll-wrap">
          <div className="cat-scroll">
            <button className={`cat-pill${activeCat === "" ? " active" : ""}`} onClick={() => setActiveCat("")}>
              🛒 All
            </button>
            {CATEGORIES.map(({ type, emoji }) => (
              <button
                key={type}
                className={`cat-pill${activeCat === type ? " active" : ""}`}
                onClick={() => setActiveCat(type)}
              >
                {emoji} {type.split(" ")[0]}
              </button>
            ))}
          </div>
        </div>

        {/* ── Promo banners with real photos ── */}
        <div className="promo-scroll">
          {PROMOS.map((p, i) => (
            <div key={i} className="promo-card" onClick={() => addToast("Offer noted! 🎉")}>
              <img src={p.img} alt={p.title} className="promo-card-img" loading="lazy" />
              <div className="promo-card-overlay" style={{ background: p.grad }} />
              <div className="promo-card-content">
                <span className="promo-tag">{p.tag}</span>
                <h3 className="promo-title">{p.title}</h3>
              </div>
            </div>
          ))}
        </div>

        {/* ── Trending — ML-curated ── */}
        <RecommendationRail
          title="Trending right now"
          emoji="🔥"
          products={toList(TRENDING_IDS) as any[]}
          tag="Bestsellers this week"
          onSeeAll={() => navigate("/category")}
        />

        {/* ── Gopi Bahu AI banner ── */}
        <div className="ai-banner" onClick={() => navigate("/ai")}>
          <div className="ai-avatar-img">
            <img src={GOPI} alt="Gopi Bahu"
              onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }} />
          </div>
          <div className="ai-text">
            <div className="ai-label">✨ AI POWERED</div>
            <h3>Hi, I'm Gopi Bahu!</h3>
            <p>Ask me for recipes, returns, or grocery help.</p>
          </div>
          <span className="ai-arrow">›</span>
        </div>

        {/* ── For You — personalised ML picks ── */}
        <RecommendationRail
          title="For you"
          emoji="🎯"
          products={toList(FOR_YOU_IDS) as any[]}
          tag="Personalised picks"
          onSeeAll={() => navigate("/category")}
        />

        {/* ── Category-filtered products ── */}
        {activeCat && catProducts.length > 0 && (
          <RecommendationRail
            title={CATEGORIES.find((c) => c.type === activeCat)?.type ?? "Products"}
            emoji={CATEGORIES.find((c) => c.type === activeCat)?.emoji}
            products={catProducts as any[]}
          />
        )}

        {/* ── Department grid with real product images ── */}
        <section className="dept-section">
          <div className="rail-header"><h2 className="rail-title">Shop by category</h2></div>
          <div className="dept-grid">
            {CATEGORIES.map(({ type, emoji, color }) => {
              const sample = PRODUCTS.find((p) => p.type === type);
              return (
                <button
                  key={type}
                  className="dept-item"
                  onClick={() => navigate(`/category?type=${encodeURIComponent(type)}`)}
                >
                  {sample ? (
                    <img src={sample.src} alt={type} loading="lazy" className="dept-img" />
                  ) : (
                    <div className="dept-emoji-fallback" style={{ background: color }}>{emoji}</div>
                  )}
                  <div className="dept-overlay">
                    <span className="dept-name">{type.split(" ")[0]}</span>
                  </div>
                </button>
              );
            })}
          </div>
        </section>

        {/* ── Fresh picks rail ── */}
        <RecommendationRail
          title="Fresh picks"
          emoji="🥬"
          products={toList(FRESH_IDS) as any[]}
        />

        {/* ── Kitchen & Household ── */}
        <RecommendationRail
          title="Kitchen & Household"
          emoji="🏠"
          products={toList(KITCHEN_HH_IDS) as any[]}
          onSeeAll={() => navigate("/category?type=Kitchen")}
        />

      </main>
    </div>
  );
}
