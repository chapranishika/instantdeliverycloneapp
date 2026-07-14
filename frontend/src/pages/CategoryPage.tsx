import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { PRODUCTS, CATEGORIES, getCatConf } from "../lib/products";
import ProductCard from "../components/ui/ProductCard";

export default function CategoryPage() {
  const navigate      = useNavigate();
  const [params]      = useSearchParams();
  const [selType, setSelType] = useState(params.get("type") ?? "");

  const activeCat = CATEGORIES.find((c) => c.type === selType);
  const products  = selType ? PRODUCTS.filter((p) => p.type === selType) : PRODUCTS;

  return (
    <div className="page category-page">
      <header className="page-header">
        <button className="back-btn" onClick={() => navigate(-1)}>‹</button>
        <h1>{activeCat?.type ?? "All Categories"}</h1>
      </header>

      <div className="cat-page-body">
        {/* ── Sidebar with real product thumbnails ── */}
        <div className="cat-sidebar">
          <button
            className={`sidebar-item${selType === "" ? " active" : ""}`}
            onClick={() => setSelType("")}
          >
            <div className="sidebar-thumb">
              <img src={PRODUCTS[0].src} alt="All" loading="lazy" />
            </div>
            <span>All</span>
          </button>

          {CATEGORIES.map(({ type, emoji }) => {
            const sample = PRODUCTS.find((p) => p.type === type);
            return (
              <button
                key={type}
                className={`sidebar-item${selType === type ? " active" : ""}`}
                onClick={() => setSelType(type)}
              >
                <div className="sidebar-thumb">
                  {sample ? (
                    <img src={sample.src} alt={type} loading="lazy" />
                  ) : (
                    <span style={{ fontSize: 22 }}>{emoji}</span>
                  )}
                </div>
                <span>{type.split(" ")[0]}</span>
              </button>
            );
          })}
        </div>

        {/* ── Product grid ── */}
        <div className="cat-product-area">
          {activeCat && (
            <div
              className="cat-dept-banner"
              style={{ background: `linear-gradient(135deg, ${activeCat.color ?? "#8025FB"}, ${activeCat.color ?? "#4C1D95"}88)` }}
            >
              <h2>{activeCat.emoji} {activeCat.type}</h2>
              <p>{products.length} products available</p>
            </div>
          )}

          {products.length === 0 ? (
            <div className="empty-state" style={{ gridColumn: "1/-1", marginTop: 40 }}>
              <div className="empty-icon">📦</div>
              <h2>No products yet</h2>
              <p>Check back soon!</p>
            </div>
          ) : (
            <div className="cat-product-grid">
              {products.map((p) => (
                <ProductCard key={p.id} product={p} page="category" wide />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
