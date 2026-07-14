/**
 * AIPage — Gopi Bahu AI Kitchen Assistant
 * 1420 recipes from real Kaggle datasets + handcrafted dishes
 * All ingredients mapped to real Zepto product IDs
 */
import { useRef, useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useCartStore, useUIStore } from "../store";
import { PRODUCTS, type Product } from "../lib/products";
import { RECIPES } from "../lib/recipes";

const GOPI = "/gopi_assistant.png";

type Msg = {
  id: string;
  role: "user" | "assistant";
  content: string;
  products?: Product[];
  allIngredients?: string[];
  isRecipe?: boolean;
  category?: string;
};

// ── Smart keyword matcher ─────────────────────────────────────────────────────
// Build an index at startup: every word/phrase in recipe titles → recipe key
let _idx: Array<[string, string]> | null = null;

function buildIndex(): Array<[string, string]> {
  const entries: Array<[string, string]> = [];
  const allKeys = Object.keys(RECIPES);

  // Sort by title length descending — longer (more specific) matches first
  const sorted = allKeys.sort((a, b) =>
    (RECIPES[b]?.title?.length ?? 0) - (RECIPES[a]?.title?.length ?? 0)
  );

  for (const key of sorted) {
    const title = (RECIPES[key]?.title ?? "").toLowerCase().trim();
    if (title.length > 2) entries.push([title, key]);
    // Also index individual significant words for partial matching
    const words = title.split(/\s+/).filter(w => w.length > 3);
    for (const word of words) {
      if (!entries.find(([k]) => k === word)) {
        entries.push([word, key]);
      }
    }
  }
  return entries;
}

function findRecipe(query: string): { key: string; recipe: (typeof RECIPES)[string] } | null {
  const q = query.toLowerCase().trim();
  if (!q) return null;
  if (!_idx) _idx = buildIndex();

  // 1. Direct key match
  if (RECIPES[q.replace(/\s+/g,"_")]) {
    const k = q.replace(/\s+/g,"_");
    return { key: k, recipe: RECIPES[k] };
  }

  // 2. Full title match (longest phrase first)
  for (const [phrase, key] of _idx) {
    if (phrase.length > 4 && q.includes(phrase)) {
      return { key, recipe: RECIPES[key] };
    }
  }

  // 3. Word overlap scoring — find recipe whose title words overlap most
  const qWords = new Set(q.split(/\s+/).filter(w => w.length > 3));
  if (qWords.size === 0) return null;

  let bestKey = "";
  let bestScore = 0;

  for (const key of Object.keys(RECIPES)) {
    const titleWords = (RECIPES[key]?.title ?? "").toLowerCase().split(/\s+/).filter(w => w.length > 3);
    let overlap = 0;
    for (const w of titleWords) {
      if (qWords.has(w)) overlap++;
      for (const qw of qWords) {
        if (qw.includes(w) || w.includes(qw)) overlap += 0.5;
      }
    }
    const score = overlap / Math.max(titleWords.length, 1);
    if (score > bestScore && score >= 0.4) {
      bestScore = score;
      bestKey = key;
    }
  }

  if (bestKey) return { key: bestKey, recipe: RECIPES[bestKey] };
  return null;
}

// ── Static non-recipe responses ───────────────────────────────────────────────
const STATIC: Record<string, { text: string; product_ids?: number[] }> = {
  return: {
    text: "🔄 **Return Process**\n\n1. Go to **Profile → Orders**\n2. Tap **Report an issue**\n3. Select **Damaged / Expired**\n4. Upload a photo\n5. Refund within 24 hours ✅\n\n*48-hr window for fresh items, 7 days for others.*",
  },
  fresh: {
    text: "🥬 **Today's Fresh Picks**\n\nJust stocked at our dark store:\n• Tomatoes — peak ripeness\n• Spinach — freshly sourced\n• Bananas — perfectly ripe\n• Broccoli — imported quality\n• Mushroom — just arrived",
    product_ids: [545, 931, 27, 1843, 1850],
  },
  deal: {
    text: "💰 **Best Deals Right Now**\n\nUse **ZEPTO10** — 10% off ₹99+\nUse **FLAT50** — ₹50 off ₹199+\nUse **FRESH20** — 20% off fresh produce 🎉",
    product_ids: [27, 1, 0, 4152],
  },
  help: {
    text: "✨ I'm **Gopi Bahu** 👩‍🍳, your Zepto kitchen assistant!\n\nI know **1,420+ real dishes** from Indian, World and regional cuisines!\n\nTell me any dish → I'll show:\n📋 Full ingredient list\n🛒 Available on Zepto (add all in one tap!)\n👨‍🍳 Step-by-step cooking instructions\n\nTry: *dal tadka, chole bhature, banana bread, gulab jamun, pasta, pad thai, biryani, rasam...*",
  },
};

function renderContent(text: string) {
  return text
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.*?)\*/g, "<em>$1</em>")
    .replace(/\n/g, "<br/>");
}

const QUICK_PROMPTS = [
  { label: "🍝 Pasta white sauce", text: "pasta white sauce" },
  { label: "🥔 Aloo sabzi",        text: "aloo sabzi" },
  { label: "🍛 Dal tadka",         text: "dal tadka" },
  { label: "🍛 Palak paneer",      text: "palak paneer" },
  { label: "🫘 Chole bhature",     text: "chole bhature" },
  { label: "🍚 Veg biryani",       text: "veg biryani" },
  { label: "🥟 Samosa",            text: "samosa" },
  { label: "🥤 Mango lassi",       text: "mango lassi" },
  { label: "☕ Masala chai",        text: "masala chai" },
  { label: "🍮 Gulab jamun",       text: "gulab jamun" },
  { label: "🌅 Poha",             text: "poha" },
  { label: "🍮 Gajar halwa",       text: "gajar halwa" },
  { label: "🌍 Pad Thai",          text: "pad thai" },
  { label: "🌍 Pasta carbonara",   text: "pasta carbonara" },
  { label: "🔄 Return item",       text: "return damaged item" },
  { label: "💰 Best deals",        text: "best deals today" },
];

export default function AIPage() {
  const navigate = useNavigate();
  const { addItem, items } = useCartStore();
  const addToast = useUIStore((s) => s.addToast);
  const inputRef  = useRef<HTMLInputElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  const [messages, setMessages] = useState<Msg[]>([{
    id: "intro", role: "assistant",
    content: `Hi! I'm **Gopi Bahu** 👩‍🍳!\n\nI know **1,420+ dishes** — Indian, World, Regional cuisines!\n\nTell me any dish → full ingredients + add to cart! 🛒`,
  }]);
  const [input, setInput]     = useState("");
  const [loading, setLoading] = useState(false);
  const [totalRecipes]        = useState(Object.keys(RECIPES).length);

  // Pre-build index on mount
  useEffect(() => { _idx = buildIndex(); }, []);

  function scrollDown() {
    setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 60);
  }

  function addAllToCart(products: Product[]) {
    products.forEach(p => addItem(p));
    addToast(`${products.length} ingredients added to cart 🛒`);
  }

  async function sendMessage(text: string) {
    if (!text.trim() || loading) return;
    setInput("");
    setLoading(true);
    const userMsg: Msg = { id: Date.now().toString(), role: "user", content: text };
    const asstId = (Date.now() + 1).toString();
    setMessages(p => [...p, userMsg, { id: asstId, role: "assistant", content: "" }]);
    scrollDown();
    await new Promise(r => setTimeout(r, 800));

    let responseText = "";
    let products: Product[] = [];
    let allIngredients: string[] | undefined;
    let isRecipe = false;
    let category = "";

    const q = text.toLowerCase();
    const recipeMatch = findRecipe(q);

    if (recipeMatch) {
      const { recipe } = recipeMatch;
      const matched = (recipe.product_ids || [])
        .map(id => PRODUCTS.find(p => p.id === id))
        .filter(Boolean) as Product[];

      responseText =
        `${recipe.category}  **${recipe.title}**\n` +
        `⏱ ${recipe.time}  ·  👥 ${recipe.serves}\n\n` +
        `**All ingredients you need:**\n` +
        (recipe.all_ingredients || []).map(i => `• ${i}`).join("\n") +
        `\n\n**Steps:**\n` +
        (recipe.steps || []).map((s, i) => `${i+1}. ${s}`).join("\n");

      products      = matched;
      allIngredients = recipe.all_ingredients;
      isRecipe      = true;
      category      = recipe.category;
    } else {
      const key = Object.keys(STATIC).find(k => q.includes(k)) ?? "help";
      const resp = STATIC[key];
      responseText = resp.text;
      products = (resp.product_ids ?? [])
        .map(id => PRODUCTS.find(p => p.id === id))
        .filter(Boolean) as Product[];
    }

    // Streaming effect
    let shown = "";
    for (let i = 0; i < responseText.length; i += 6) {
      shown += responseText.slice(i, i + 6);
      const snap = shown;
      setMessages(p => p.map(m => m.id === asstId ? { ...m, content: snap } : m));
      await new Promise(r => setTimeout(r, 8));
    }

    setMessages(p => p.map(m =>
      m.id === asstId ? { ...m, content: responseText, products, allIngredients, isRecipe, category } : m
    ));
    setLoading(false);
    scrollDown();
  }

  return (
    <div className="page ai-page">
      <header className="ai-header">
        <button className="back-btn ai-back" onClick={() => navigate(-1)}>‹</button>
        <div className="ai-header-info">
          <div className="ai-header-avatar">
            <img src={GOPI} alt="Gopi Bahu"
              onError={e => { (e.target as HTMLImageElement).style.display = "none"; }} />
          </div>
          <div>
            <h1>Gopi Bahu</h1>
            <p className="ai-status">
              <span className="dot-green" /> {totalRecipes.toLocaleString()} dishes · Any cuisine!
            </p>
          </div>
        </div>
      </header>

      <div className="chat-messages">
        {messages.map(msg => (
          <div key={msg.id} className={`chat-msg ${msg.role}`}>
            {msg.role === "assistant" && (
              <div className="msg-avatar">
                <img src={GOPI} alt="Gopi"
                  onError={e => { (e.target as HTMLImageElement).style.display = "none"; }} />
              </div>
            )}
            <div className={`msg-bubble ${msg.role}`}>
              <div className="msg-text"
                dangerouslySetInnerHTML={{ __html: renderContent(msg.content) }} />

              {/* Recipe cart section */}
              {msg.isRecipe && msg.products && msg.products.length > 0 && (
                <div className="recipe-cart-section">
                  <div className="recipe-available-header">
                    <span className="recipe-available-label">
                      ✅ Available on Zepto ({msg.products.length} of {msg.allIngredients?.length ?? 0})
                    </span>
                    <button className="recipe-add-all-btn" onClick={() => addAllToCart(msg.products!)}>
                      🛒 Add all to cart
                    </button>
                  </div>
                  <div className="recipe-products-grid">
                    {msg.products.map(p => {
                      const inCart = items.find(e => e.product.id === p.id)?.quantity ?? 0;
                      return (
                        <div key={p.id} className="recipe-product-chip">
                          <div className="rpc-img-wrap">
                            <img src={p.src} alt={p.name} className="rpc-img"
                              onError={e => { (e.target as HTMLImageElement).style.display = "none"; }} />
                          </div>
                          <div className="rpc-info">
                            <span className="rpc-name">{p.name}</span>
                            <span className="rpc-unit">{p.unit}</span>
                          </div>
                          <div className="rpc-right">
                            <span className="rpc-price">₹{p.disc}</span>
                            {inCart > 0
                              ? <span className="rpc-in-cart">✓ {inCart}</span>
                              : <button className="rpc-add"
                                  onClick={() => { addItem(p); addToast(`${p.name} added 🛒`); }}>+</button>}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                  <p className="recipe-not-available">
                    💡 Other ingredients available at your local kirana store.
                  </p>
                </div>
              )}

              {/* Non-recipe product chips */}
              {!msg.isRecipe && msg.products && msg.products.length > 0 && (
                <div className="msg-products">
                  <p className="msg-products-label">🛒 Quick add:</p>
                  {msg.products.slice(0, 5).map(p => (
                    <div key={p.id} className="msg-product-chip">
                      <img src={p.src} alt={p.name} className="mpc-img"
                        onError={e => { (e.target as HTMLImageElement).style.display = "none"; }} />
                      <div className="mpc-info">
                        <span className="mpc-name">{p.name}</span>
                        <span className="mpc-unit">{p.unit}</span>
                      </div>
                      <span className="mpc-price">₹{p.disc}</span>
                      <button className="mpc-add"
                        onClick={() => { addItem(p); addToast(`${p.name} added 🛒`); }}>+</button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="chat-msg assistant">
            <div className="msg-avatar">
              <img src={GOPI} alt="Gopi"
                onError={e => { (e.target as HTMLImageElement).style.display = "none"; }} />
            </div>
            <div className="msg-bubble assistant">
              <span className="typing-dot">●</span>
              <span className="typing-dot">●</span>
              <span className="typing-dot">●</span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {messages.length <= 2 && (
        <div className="quick-prompts">
          {QUICK_PROMPTS.map(q => (
            <button key={q.label} className="quick-prompt-btn"
              onClick={() => sendMessage(q.text)}>{q.label}</button>
          ))}
        </div>
      )}

      <div className="chat-input-bar">
        <input ref={inputRef} className="chat-input" value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === "Enter" && sendMessage(input)}
          placeholder={`Search ${totalRecipes}+ dishes… biryani, chole, pasta, pad thai…`}
          disabled={loading} autoFocus />
        <button className={`chat-send-btn${loading ? " loading" : ""}`}
          onClick={() => sendMessage(input)}
          disabled={loading || !input.trim()}>↑</button>
      </div>
    </div>
  );
}
