import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { PRODUCTS } from "../lib/products";
import ProductCard from "../components/ui/ProductCard";

const POPULAR = ["tomato", "banana", "spinach", "milk", "onion", "mushroom", "masala", "soap"];

export default function SearchPage() {
  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<typeof PRODUCTS | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>();

  useEffect(() => { inputRef.current?.focus(); }, []);

  function doSearch(q: string) {
    if (!q.trim()) { setResults(null); return; }
    setLoading(true);
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      const q_lower = q.toLowerCase();
      const res = PRODUCTS.filter(
        (p) =>
          p.name.toLowerCase().includes(q_lower) ||
          p.type.toLowerCase().includes(q_lower) ||
          p.description.toLowerCase().includes(q_lower)
      );
      setResults(res);
      setLoading(false);
    }, 400);
  }

  function handleChange(v: string) {
    setQuery(v);
    doSearch(v);
  }

  return (
    <div className="page search-page">
      <header className="search-header">
        <button className="back-btn search-back" onClick={() => navigate(-1)}>‹</button>
        <div className="search-input-wrap">
          <span className="search-icon-dark">🔍</span>
          <input
            ref={inputRef}
            className="search-input-field"
            value={query}
            onChange={(e) => handleChange(e.target.value)}
            placeholder="Search vegetables, fruits & more…"
          />
          {query && (
            <button className="search-clear" onClick={() => { setQuery(""); setResults(null); }}>
              ✕
            </button>
          )}
        </div>
      </header>

      <div className="search-body">
        {/* Loading skeletons */}
        {loading && (
          <div className="search-grid">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="skeleton-card">
                <div className="sk-img shimmer" />
                <div className="sk-body">
                  <div className="sk-line shimmer" style={{ width: "80%" }} />
                  <div className="sk-line shimmer" style={{ width: "55%", marginTop: 5 }} />
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Results */}
        {!loading && results !== null && (
          <>
            <p className="search-result-count">
              {results.length} result{results.length !== 1 ? "s" : ""} for &ldquo;{query}&rdquo;
            </p>
            {results.length === 0 ? (
              <div className="empty-state">
                <div className="empty-icon">🔍</div>
                <h2>No results found</h2>
                <p>Try: tomato, banana, milk, mushroom…</p>
              </div>
            ) : (
              <div className="search-grid">
                {results.map((p) => (
                  <ProductCard key={p.id} product={p} page="search" wide />
                ))}
              </div>
            )}
          </>
        )}

        {/* Empty state before searching */}
        {!loading && results === null && (
          <div className="search-empty-start">
            <h3>What are you looking for?</h3>
            <div className="popular-searches">
              {POPULAR.map((term) => (
                <button
                  key={term}
                  className="popular-chip"
                  onClick={() => { setQuery(term); doSearch(term); }}
                >
                  🔍 {term}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
