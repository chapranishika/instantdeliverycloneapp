/**
 * ProductCard — Real Zepto CDN images, in-card qty stepper, wishlist.
 */
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useCartStore, useWishlistStore, useUIStore } from "../../store";
import { discPct, type Product } from "../../lib/products";

interface Props {
  product: Product;
  page?: string;
  wide?: boolean;
}

export default function ProductCard({ product: p, page = "home", wide = false }: Props) {
  const { items, addItem, updateQty } = useCartStore();
  const { toggle, has }   = useWishlistStore();
  const addToast          = useUIStore((s) => s.addToast);
  const navigate          = useNavigate();
  const [imgLoaded, setImgLoaded] = useState(false);

  const entry    = items.find((e) => e.product.id === p.id);
  const qty      = entry?.quantity ?? 0;
  const wishlisted = has(p.id);
  const d        = discPct(p);

  function handleAdd(e: React.MouseEvent) {
    e.stopPropagation();
    addItem(p);
    addToast(`${p.name} added to cart 🛒`);
  }

  function handleInc(e: React.MouseEvent) {
    e.stopPropagation();
    addItem(p);
  }

  function handleDec(e: React.MouseEvent) {
    e.stopPropagation();
    updateQty(p.id, qty - 1);
  }

  function handleWishlist(e: React.MouseEvent) {
    e.stopPropagation();
    toggle(p.id);
    addToast(wishlisted ? "Removed from wishlist" : "Saved to wishlist ♡");
  }

  return (
    <div
      className={`product-card${wide ? " wide" : ""}`}
      onClick={() => navigate(`/product/${p.id}`)}
    >
      {/* Image */}
      <div className="pc-img-wrap">
        {!imgLoaded && <div className="pc-img-sk shimmer" />}
        <img
          src={p.src}
          alt={p.name}
          loading="lazy"
          className={`pc-img${imgLoaded ? " loaded" : ""}`}
          onLoad={() => setImgLoaded(true)}
          onError={(e) => {
            (e.target as HTMLImageElement).style.opacity = "0";
          }}
        />
        <div className="pc-del-badge">
          <span className="bolt">⚡</span>{p.type === "Fresh Fruits" || p.type === "Fresh Vegetables" ? "8" : "10"} min
        </div>
        {d > 0 && <div className="pc-disc-badge">{d}% OFF</div>}
        <button
          className={`pc-wl${wishlisted ? " active" : ""}`}
          onClick={handleWishlist}
          aria-label="Wishlist"
        >
          {wishlisted ? "❤️" : "♡"}
        </button>
      </div>

      {/* Body */}
      <div className="pc-body">
        <p className="pc-unit">{p.unit}</p>
        <h3 className="pc-name">{p.name}</h3>
        <div className="pc-rating">
          <span className="star">★</span>
          <span>{p.rating.toFixed(1)}</span>
        </div>
        <div className="pc-footer">
          <div className="pc-prices">
            <span className="pc-price">₹{p.disc}</span>
            {p.price > p.disc && <span className="pc-mrp">₹{p.price}</span>}
          </div>

          {qty === 0 ? (
            <button className="pc-add-btn" onClick={handleAdd} aria-label="Add">
              +
            </button>
          ) : (
            <div className="pc-qty-ctrl">
              <button onClick={handleDec}>−</button>
              <span>{qty}</span>
              <button onClick={handleInc}>+</button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
