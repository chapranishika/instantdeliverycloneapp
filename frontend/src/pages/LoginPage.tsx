/**
 * LoginPage — Register / Login wired to FastAPI backend
 * Uses real JWT auth — not mocked.
 */
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useUserStore, useUIStore } from "../store";

const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1";

type Mode = "login" | "register";

export default function LoginPage() {
  const navigate  = useNavigate();
  const login     = useUserStore((s) => s.login);
  const addToast  = useUIStore((s) => s.addToast);

  const [mode, setMode]         = useState<Mode>("login");
  const [email, setEmail]       = useState("");
  const [password, setPassword] = useState("");
  const [name, setName]         = useState("");
  const [phone, setPhone]       = useState("");
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState("");

  async function submit() {
    setError("");
    if (!email || !password) { setError("Email and password are required"); return; }
    if (password.length < 8)  { setError("Password must be at least 8 characters"); return; }
    if (mode === "register" && !name) { setError("Name is required"); return; }

    setLoading(true);
    try {
      const endpoint = mode === "login" ? "/auth/login" : "/auth/register";
      const body: Record<string, string> = { email, password };
      if (mode === "register") { body.name = name; body.phone = phone; }

      const res = await fetch(`${API}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      const data = await res.json();

      if (!res.ok) {
        setError(data.detail ?? "Something went wrong. Please try again.");
        return;
      }

      // Store token in localStorage for subsequent API calls
      localStorage.setItem("zepto_token", data.access_token);
      localStorage.setItem("zepto_user", JSON.stringify({
        name: data.name, email: data.email,
      }));

      // Update Zustand user store
      login({ name: data.name, email: data.email });

      addToast(mode === "login" ? `Welcome back, ${data.name}! 👋` : `Welcome to Zepto, ${data.name}! 🎉`);
      navigate(-1);
    } catch (e) {
      setError("Network error — please check your connection.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page login-page">
      <header className="page-header">
        <button className="back-btn" onClick={() => navigate(-1)}>‹</button>
        <h1>{mode === "login" ? "Sign In" : "Create Account"}</h1>
      </header>

      <div className="login-body">
        {/* Toggle */}
        <div className="login-tabs">
          <button
            className={`login-tab${mode === "login" ? " active" : ""}`}
            onClick={() => { setMode("login"); setError(""); }}
          >Sign In</button>
          <button
            className={`login-tab${mode === "register" ? " active" : ""}`}
            onClick={() => { setMode("register"); setError(""); }}
          >Register</button>
        </div>

        <div className="login-form">
          {mode === "register" && (
            <>
              <div className="form-group">
                <label className="form-label">Full Name *</label>
                <input
                  className="form-input"
                  type="text"
                  placeholder="Nish Kumar"
                  value={name}
                  onChange={e => setName(e.target.value)}
                  autoComplete="name"
                />
              </div>
              <div className="form-group">
                <label className="form-label">Phone (optional)</label>
                <input
                  className="form-input"
                  type="tel"
                  placeholder="9999999999"
                  value={phone}
                  onChange={e => setPhone(e.target.value)}
                  autoComplete="tel"
                />
              </div>
            </>
          )}

          <div className="form-group">
            <label className="form-label">Email *</label>
            <input
              className="form-input"
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={e => setEmail(e.target.value)}
              autoComplete="email"
              onKeyDown={e => e.key === "Enter" && submit()}
            />
          </div>

          <div className="form-group">
            <label className="form-label">Password *</label>
            <input
              className="form-input"
              type="password"
              placeholder={mode === "register" ? "At least 8 characters" : "Your password"}
              value={password}
              onChange={e => setPassword(e.target.value)}
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              onKeyDown={e => e.key === "Enter" && submit()}
            />
          </div>

          {error && (
            <div className="form-error">⚠️ {error}</div>
          )}

          <button
            className={`login-submit-btn${loading ? " loading" : ""}`}
            onClick={submit}
            disabled={loading}
          >
            {loading
              ? "Please wait…"
              : mode === "login" ? "Sign In →" : "Create Account →"}
          </button>

          <p className="login-note">
            {mode === "login"
              ? "Don't have an account? "
              : "Already have an account? "}
            <button
              className="login-switch-btn"
              onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(""); }}
            >
              {mode === "login" ? "Register here" : "Sign in here"}
            </button>
          </p>
        </div>

        <div className="login-promo">
          <p>🎉 New members get:</p>
          <div className="login-promo-chips">
            <span className="promo-chip">FIRST3 — Free delivery</span>
            <span className="promo-chip">ZEPTO10 — 10% off</span>
          </div>
        </div>
      </div>
    </div>
  );
}
