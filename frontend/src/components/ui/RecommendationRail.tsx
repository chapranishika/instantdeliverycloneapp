import ProductCard from "./ProductCard";
import type { Product } from "../../lib/products";

interface Props {
  title: string;
  emoji?: string;
  products: Product[];
  loading?: boolean;
  tag?: string;
  onSeeAll?: () => void;
  page?: string;
}

function SkeletonCard() {
  return (
    <div className="skeleton-card">
      <div className="sk-img shimmer" />
      <div className="sk-body">
        <div className="sk-line shimmer" style={{ width: "80%" }} />
        <div className="sk-line shimmer" style={{ width: "55%", marginTop: 5 }} />
        <div className="sk-footer">
          <div className="sk-line shimmer" style={{ width: "40%" }} />
          <div className="sk-btn shimmer" />
        </div>
      </div>
    </div>
  );
}

export default function RecommendationRail({
  title, emoji, products, loading = false, tag, onSeeAll, page = "home",
}: Props) {
  return (
    <section className="rec-rail">
      <div className="rail-header">
        <h2 className="rail-title">
          {emoji && <span className="rail-emoji">{emoji}</span>}
          {title}
        </h2>
        {onSeeAll && (
          <button className="rail-see-all" onClick={onSeeAll}>See all</button>
        )}
      </div>

      {tag && <div className="rail-tag">{tag}</div>}

      <div className="rail-scroll">
        {loading
          ? Array.from({ length: 5 }).map((_, i) => <SkeletonCard key={i} />)
          : products.map((p) => (
              <div key={p.id} className="rail-item">
                <ProductCard product={p} page={page} />
              </div>
            ))}
        {!loading && products.length === 0 && (
          <p className="rail-empty">No products available.</p>
        )}
      </div>
    </section>
  );
}
