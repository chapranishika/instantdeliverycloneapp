/**
 * Global Store — Cart, Wishlist, User, UI, Checkout
 *
 * Bug fixed: CheckoutStore.applyPromo previously used CommonJS require()
 * inside a Zustand action, which crashes in ESM (Vite). Fixed by importing
 * PROMO_CODES at module level like every other import.
 */
import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import { PRODUCTS, PROMO_CODES, type Product } from "../lib/products";

// ── Cart ──────────────────────────────────────────────────────────────────────

interface CartEntry {
  product: Product;
  quantity: number;
}

interface CartStore {
  items: CartEntry[];
  addItem: (product: Product, qty?: number) => void;
  removeItem: (productId: number) => void;
  updateQty: (productId: number, qty: number) => void;
  clearCart: () => void;
  totalItems: () => number;
  totalMRP: () => number;
  totalDiscount: () => number;
  totalPrice: () => number;
  cartIds: () => number[];
}

export const useCartStore = create<CartStore>()(
  persist(
    (set, get) => ({
      items: [],

      addItem: (product, qty = 1) =>
        set((s) => {
          const ex = s.items.find((e) => e.product.id === product.id);
          if (ex) {
            return {
              items: s.items.map((e) =>
                e.product.id === product.id
                  ? { ...e, quantity: e.quantity + qty }
                  : e
              ),
            };
          }
          return { items: [...s.items, { product, quantity: qty }] };
        }),

      removeItem: (id) =>
        set((s) => ({ items: s.items.filter((e) => e.product.id !== id) })),

      updateQty: (id, qty) =>
        set((s) => {
          if (qty <= 0)
            return { items: s.items.filter((e) => e.product.id !== id) };
          return {
            items: s.items.map((e) =>
              e.product.id === id ? { ...e, quantity: qty } : e
            ),
          };
        }),

      clearCart: () => set({ items: [] }),

      totalItems: () => get().items.reduce((s, e) => s + e.quantity, 0),

      totalMRP: () =>
        get().items.reduce((s, e) => s + e.product.price * e.quantity, 0),

      totalDiscount: () =>
        get().items.reduce(
          (s, e) => s + (e.product.price - e.product.disc) * e.quantity,
          0
        ),

      totalPrice: () =>
        get().items.reduce((s, e) => s + e.product.disc * e.quantity, 0),

      cartIds: () => get().items.map((e) => e.product.id),
    }),
    {
      name: "zepto-cart",
      storage: createJSONStorage(() => localStorage),
    }
  )
);

// ── Wishlist ──────────────────────────────────────────────────────────────────

interface WishlistStore {
  ids: Set<number>;
  toggle: (id: number) => void;
  has: (id: number) => boolean;
  products: () => Product[];
}

export const useWishlistStore = create<WishlistStore>()(
  persist(
    (set, get) => ({
      ids: new Set<number>(),

      toggle: (id) =>
        set((s) => {
          const next = new Set(s.ids);
          if (next.has(id)) next.delete(id);
          else next.add(id);
          return { ids: next };
        }),

      has: (id) => get().ids.has(id),

      products: () => PRODUCTS.filter((p) => get().ids.has(p.id)),
    }),
    {
      name: "zepto-wishlist",
      storage: createJSONStorage(() => localStorage),
      // Sets are not JSON-serialisable — persist as array, rehydrate as Set
      partialize: (s) => ({ ids: [...s.ids] }),
      merge: (persisted: unknown, current) => ({
        ...current,
        ids: new Set<number>(((persisted as any).ids ?? []) as number[]),
      }),
    }
  )
);

// ── User ──────────────────────────────────────────────────────────────────────

interface User {
  name: string;
  email: string;
  phone?: string;
}

interface UserStore {
  user: User | null;
  sessionId: string;
  login: (u: User) => void;
  logout: () => void;
  isLoggedIn: () => boolean;
}

const genSession = () =>
  Math.random().toString(36).slice(2) + Date.now().toString(36);

export const useUserStore = create<UserStore>()(
  persist(
    (set, get) => ({
      user: null,
      sessionId: genSession(),
      login: (u) => set({ user: u }),
      logout: () => set({ user: null }),
      isLoggedIn: () => get().user !== null,
    }),
    { name: "zepto-user", storage: createJSONStorage(() => localStorage) }
  )
);

// ── Toast / UI ────────────────────────────────────────────────────────────────

interface Toast {
  id: string;
  message: string;
  type: "success" | "error" | "info";
}

interface UIStore {
  toasts: Toast[];
  addToast: (message: string, type?: Toast["type"]) => void;
  removeToast: (id: string) => void;
}

export const useUIStore = create<UIStore>((set) => ({
  toasts: [],
  addToast: (message, type = "success") => {
    const id = Math.random().toString(36).slice(2);
    set((s) => ({ toasts: [...s.toasts, { id, message, type }] }));
    setTimeout(() => {
      set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) }));
    }, 2800);
  },
  removeToast: (id) =>
    set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),
}));

// ── Checkout ──────────────────────────────────────────────────────────────────

type PayMethod = "upi" | "card" | "cod" | "wallet";
type CheckoutStep = "address" | "payment" | "confirm";

interface CheckoutStore {
  step: CheckoutStep;
  selectedAddressId: number;
  selectedPayment: PayMethod;
  promoCode: string;
  promoApplied: string | null;
  promoDiscount: number;         // computed and cached so components don't recalculate
  deliveryFree: boolean;
  setStep: (s: CheckoutStep) => void;
  setAddress: (id: number) => void;
  setPayment: (m: PayMethod) => void;
  setPromoCode: (c: string) => void;
  applyPromo: (c: string, subtotal: number) => { ok: boolean; message: string };
  clearPromo: () => void;
  reset: () => void;
}

export const useCheckoutStore = create<CheckoutStore>()((set) => ({
  step: "address",
  selectedAddressId: 1,
  selectedPayment: "upi",
  promoCode: "",
  promoApplied: null,
  promoDiscount: 0,
  deliveryFree: false,

  setStep: (step) => set({ step }),
  setAddress: (id) => set({ selectedAddressId: id }),
  setPayment: (m) => set({ selectedPayment: m }),
  setPromoCode: (c) => set({ promoCode: c.toUpperCase() }),

  /**
   * FIX: PROMO_CODES is now imported at module level (top of file).
   * Previously this used require("../lib/products") which is CommonJS
   * and throws "require is not defined" in Vite's ESM environment.
   *
   * The fix is a single import statement — no runtime dynamic loading needed.
   * subtotal is passed in so the store can compute the discount correctly.
   */
  applyPromo: (code, subtotal) => {
    const upper = code.trim().toUpperCase();
    const promo = PROMO_CODES[upper];

    if (!promo) {
      return { ok: false, message: `"${upper}" is not a valid promo code` };
    }

    let discount = 0;
    let deliveryFree = false;

    if (promo.type === "pct") {
      discount = Math.min(Math.round(subtotal * promo.val / 100), promo.max);
    } else if (promo.type === "flat") {
      discount = Math.min(promo.val, subtotal);
    } else if (promo.type === "free_del") {
      deliveryFree = true;
    }

    set({
      promoApplied: upper,
      promoDiscount: discount,
      deliveryFree,
    });

    return { ok: true, message: `${promo.label} applied!` };
  },

  clearPromo: () =>
    set({ promoApplied: null, promoCode: "", promoDiscount: 0, deliveryFree: false }),

  reset: () =>
    set({
      step: "address",
      selectedAddressId: 1,
      selectedPayment: "upi",
      promoCode: "",
      promoApplied: null,
      promoDiscount: 0,
      deliveryFree: false,
    }),
}));
