/**
 * supabase.ts — Supabase JS client for the Zepto Clone
 *
 * Project:  zepto-clone (lqvldpojrcokvfmlfuhe)
 * Region:   ap-south-1
 * URL:      https://lqvldpojrcokvfmlfuhe.supabase.co
 *
 * This client provides:
 *  - Auth  — sign up, sign in, sign out, session management
 *  - DB    — direct queries via supabase.from() (RLS-protected)
 *  - Realtime — subscribe to order status changes
 *
 * The FastAPI backend also connects to the same Supabase PostgreSQL DB
 * via asyncpg (Transaction Pooler). The two clients co-exist safely:
 *  - Frontend supabase-js → public schema with RLS enforced
 *  - Backend FastAPI/asyncpg → same tables, bypasses RLS via service role
 */
import { createClient } from "@supabase/supabase-js";

const SUPABASE_URL  = import.meta.env.VITE_SUPABASE_URL  as string;
const SUPABASE_ANON = import.meta.env.VITE_SUPABASE_ANON_KEY as string;

if (!SUPABASE_URL || !SUPABASE_ANON) {
  console.warn(
    "[Supabase] VITE_SUPABASE_URL or VITE_SUPABASE_ANON_KEY not set. " +
    "Add them to frontend/.env.local — see .env.example"
  );
}

export const supabase = createClient(SUPABASE_URL ?? "", SUPABASE_ANON ?? "", {
  auth: {
    persistSession:     true,
    autoRefreshToken:   true,
    detectSessionInUrl: true,
    storageKey:         "zepto-auth",
  },
});

// ── Types matching the database schema ───────────────────────────────────────

export interface DBProduct {
  id:                 number;
  name:               string;
  price:              number;      // discounted price
  mrp:                number | null;
  quantity_label:     string | null;
  image_url:          string | null;
  department_id:      number | null;
  aisle:              string | null;
  rating:             number;
  rating_count:       number;
  delivery_time_mins: number;
  is_available:       boolean;
  stock_count:        number;
}

export interface DBOrder {
  id:               number;
  user_id:          number | null;
  status:           string;
  total_amount:     number | null;
  delivery_address: string | null;
  payment_method:   string | null;
  promo_code:       string | null;
  discount_amount:  number;
  eta_minutes:      number;
  placed_at:        string;
  delivered_at:     string | null;
}

export interface DBPromoCode {
  id:              number;
  code:            string;
  description:     string | null;
  discount_type:   string | null;
  discount_value:  number | null;
  min_order_value: number;
  max_discount:    number | null;
  usage_limit:     number | null;
  usage_count:     number;
  is_active:       boolean;
}

// ── Auth helpers ──────────────────────────────────────────────────────────────

export const signUp = async (email: string, password: string, name: string) => {
  const { data, error } = await supabase.auth.signUp({
    email,
    password,
    options: { data: { name } },
  });
  return { data, error };
};

export const signIn = async (email: string, password: string) => {
  const { data, error } = await supabase.auth.signInWithPassword({ email, password });
  return { data, error };
};

export const signOut = async () => {
  const { error } = await supabase.auth.signOut();
  return { error };
};

export const getSession = async () => {
  const { data: { session } } = await supabase.auth.getSession();
  return session;
};

// ── Product queries ───────────────────────────────────────────────────────────

export const fetchProducts = async (departmentId?: number) => {
  let q = supabase
    .from("products")
    .select("*, departments(name)")
    .eq("is_available", true)
    .order("rating_count", { ascending: false });

  if (departmentId !== undefined) {
    q = q.eq("department_id", departmentId);
  }
  const { data, error } = await q;
  return { data: data as (DBProduct & { departments: { name: string } })[], error };
};

export const fetchProductById = async (id: number) => {
  const { data, error } = await supabase
    .from("products")
    .select("*, departments(name)")
    .eq("id", id)
    .single();
  return { data: data as DBProduct & { departments: { name: string } }, error };
};

export const searchProducts = async (query: string) => {
  const { data, error } = await supabase
    .from("products")
    .select("*")
    .ilike("name", `%${query}%`)
    .eq("is_available", true)
    .limit(20);
  return { data: data as DBProduct[], error };
};

// ── Promo code validation ─────────────────────────────────────────────────────

export const validatePromo = async (code: string) => {
  const { data, error } = await supabase
    .from("promo_codes")
    .select("*")
    .eq("code", code.toUpperCase())
    .eq("is_active", true)
    .single();
  return { data: data as DBPromoCode | null, error };
};

// ── Order helpers ─────────────────────────────────────────────────────────────

export const placeOrder = async (order: Omit<DBOrder, "id" | "placed_at" | "delivered_at">) => {
  const { data, error } = await supabase
    .from("orders")
    .insert(order)
    .select()
    .single();
  return { data: data as DBOrder, error };
};

export const fetchUserOrders = async (userId: number) => {
  const { data, error } = await supabase
    .from("orders")
    .select("*, order_items(*, products(name, image_url, quantity_label))")
    .eq("user_id", userId)
    .order("placed_at", { ascending: false });
  return { data, error };
};

// ── Realtime — subscribe to order status updates ──────────────────────────────

export const subscribeToOrder = (
  orderId: number,
  onUpdate: (status: string, eta: number) => void
) => {
  const channel = supabase
    .channel(`order-${orderId}`)
    .on(
      "postgres_changes",
      {
        event:  "UPDATE",
        schema: "public",
        table:  "orders",
        filter: `id=eq.${orderId}`,
      },
      (payload) => {
        const updated = payload.new as DBOrder;
        onUpdate(updated.status, updated.eta_minutes);
      }
    )
    .subscribe();

  return () => supabase.removeChannel(channel);
};

// ── Event tracking (direct to Supabase, bypasses FastAPI for perf) ────────────

export const trackEvent = async (
  eventType: string,
  productId: number | null,
  sessionId: string,
  userId?: number | null
) => {
  await supabase.from("user_events").insert({
    event_type: eventType,
    product_id: productId,
    session_id: sessionId,
    user_id:    userId ?? null,
    page:       window.location.pathname,
  });
  // Fire-and-forget — errors are silently swallowed (tracking should never break UX)
};
