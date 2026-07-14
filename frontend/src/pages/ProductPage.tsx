import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { getById, PRODUCTS, discPct } from "../lib/products";
import { useCartStore, useWishlistStore, useUIStore } from "../store";
import { useSimilarProducts } from "../hooks";
import RecommendationRail from "../components/ui/RecommendationRail";

export default function ProductPage() {
  const { id }   = useParams<{ id: string }>();
  const navigate = useNavigate();
  const p        = getById(Number(id)) as ReturnType<typeof getById>;

  const { addItem, items } = useCartStore();
  const { toggle, has }    = useWishlistStore();
  const addToast           = useUIStore((s) => s.addToast);

  const [imgLoaded, setImgLoaded] = useState(false);
  const [qty, setQty]             = useState(1);

  // Hook must be called unconditionally (rules of hooks) — pass -1 if no product,
  // the hook itself no-ops for negative ids.
  const { data: similarFromAPI, fromAPI: similarFromAPIFlag } =
    useSimilarProducts(p?.id ?? -1, 8);

  if (!p) {
    return (
      <div className="page">
        <header className="page-header">
          <button className="back-btn" onClick={() => navigate(-1)}>‹</button>
          <h1>Product not found</h1>
        </header>
        <div className="empty-state">
          <div className="empty-icon">🔍</div>
          <h2>Oops!</h2>
          <p>This product doesn't exist.</p>
          <button className="btn-primary" onClick={() => navigate("/home")}>Go home</button>
        </div>
      </div>
    );
  }

  const wishlisted = has(p.id);
  const d          = discPct(p);
  const inCart = items.find((e) => e.product.id === p.id)?.quantity ?? 0;

  // Use real FAISS content-based recommendations when the backend is running;
  // otherwise fall back to a simple same-category match from the local catalogue.
  const localFallback = PRODUCTS.filter((x) => x.type === p.type && x.id !== p.id).slice(0, 8);
  const similar = similarFromAPIFlag && similarFromAPI.length > 0
    ? similarFromAPI
    : localFallback;
  const similarSource = similarFromAPIFlag ? "FAISS (content-based)" : `${p.type} category`;

  // p is guaranteed non-null here — the !p guard above returns early
  const product = p!;

  function handleAdd() {
    for (let i = 0; i < qty; i++) addItem(product);
    addToast(`${product.name} ×${qty} added to cart 🛒`);
  }

  return (
    <div className="page product-page">
      <header className="page-header">
        <button className="back-btn" onClick={() => navigate(-1)}>‹</button>
        <h1 className="page-header-title">{p.name}</h1>
        <button
          className={`wl-header-btn${wishlisted ? " active" : ""}`}
          onClick={() => { toggle(p.id); addToast(wishlisted ? "Removed" : "Saved ♡"); }}
        >
          {wishlisted ? "❤️" : "♡"}
        </button>
      </header>

      <div className="pdtl">

        {/* ── Hero image ── */}
        <div className="pd-hero">
          {!imgLoaded && <div className="pd-hero-sk shimmer" />}
          <img
            src={p.src}
            alt={p.name}
            className={`pd-hero-img${imgLoaded ? " loaded" : ""}`}
            onLoad={() => setImgLoaded(true)}
            onError={(e) => ((e.target as HTMLImageElement).style.opacity = "0")}
            loading="eager"
          />
          {d > 0 && <div className="pd-disc-badge">{d}% OFF</div>}
          <div className="pd-del-badge">
            <span className="bolt">⚡</span>
            {p.type.includes("Fresh") ? "8" : "10"} min delivery
          </div>
        </div>

        {/* ── Info ── */}
        <div className="pd-info">
          <p className="pd-category">{p.type}</p>
          <h2 className="pd-name">{p.name}</h2>
          <p className="pd-unit">{p.unit}</p>

          <div className="pd-rating-row">
            <span className="star">★</span>
            <span className="pd-rating-val">{p.rating.toFixed(1)}</span>
            <span className="pd-rating-count">(9.2k ratings)</span>
          </div>

          <div className="pd-prices">
            <span className="pd-price">₹{p.disc}</span>
            {p.price > p.disc && <span className="pd-mrp">₹{p.price}</span>}
            {d > 0 && <span className="pd-save">Save ₹{p.price - p.disc}</span>}
          </div>
        </div>

        {/* ── CTA ── */}
        <div className="pd-cta">
          <div className="pd-qty-ctrl">
            <button onClick={() => setQty((q) => Math.max(1, q - 1))}>−</button>
            <span>{qty}</span>
            <button onClick={() => setQty((q) => q + 1)}>+</button>
          </div>
          <button className="pd-add-btn" onClick={handleAdd}>
            Add to cart — ₹{p.disc * qty}
          </button>
        </div>

        {/* ── Product details box ── */}
        <div className="pd-details-box">
          <h3>Product details</h3>
          <div className="pd-detail-row">
            <span>Category</span><span>{p.type}</span>
          </div>
          <div className="pd-detail-row">
            <span>Weight / Size</span><span>{p.unit}</span>
          </div>
          <div className="pd-detail-row">
            <span>Country of Origin</span><span>{p.country} 🇮🇳</span>
          </div>
          <div className="pd-detail-row">
            <span>Delivery</span>
            <span className="green-text">⚡ {p.type.includes("Fresh") ? "8" : "10"} minutes</span>
          </div>
          {inCart > 0 && (
            <div className="pd-detail-row">
              <span>In your cart</span><span className="purple-text">{inCart} item{inCart > 1 ? "s" : ""}</span>
            </div>
          )}
        </div>

        {/* ── Description ── */}
        <div className="pd-desc-box">
          <h3>About this product</h3>
          <p>{p.description}</p>
          <div className="pd-tags">
            <span className="pd-tag">✓ Zepto guaranteed</span>
            <span className="pd-tag">⚡ Express delivery</span>
            <span className="pd-tag">↩ Easy returns</span>
            <span className="pd-tag">🇮🇳 Made in India</span>
          </div>
        </div>

        {/* ── Similar products — FAISS content-based when backend is live ── */}
        {similar.length > 0 && (
          <RecommendationRail
            title={similarFromAPIFlag ? "Similar products" : `More from ${p.type}`}
            products={similar}
            page="product"
            tag={similarFromAPIFlag ? `🤖 ${similarSource}` : undefined}
          />
        )}

      </div>
    </div>
  );
}
