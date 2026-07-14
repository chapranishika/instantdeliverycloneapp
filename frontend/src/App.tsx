import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import BottomNav         from "./components/layout/BottomNav";
import HomePage          from "./pages/HomePage";
import CategoryPage      from "./pages/CategoryPage";
import ProductPage       from "./pages/ProductPage";
import CartPage          from "./pages/CartPage";
import CheckoutPage      from "./pages/CheckoutPage";
import OrderSuccessPage  from "./pages/OrderSuccessPage";
import OrderTrackingPage from "./pages/OrderTrackingPage";
import AIPage            from "./pages/AIPage";
import SearchPage        from "./pages/SearchPage";
import ProfilePage       from "./pages/ProfilePage";
import LoginPage         from "./pages/LoginPage";
import { useUIStore }    from "./store";
import "./styles.css";

function ToastStack() {
  const { toasts, removeToast } = useUIStore();
  return (
    <div className="toast-stack">
      {toasts.map((t) => (
        <div key={t.id} className={`toast toast-${t.type}`} onClick={() => removeToast(t.id)}>
          {t.message}
        </div>
      ))}
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="app-shell">
        <div className="app-content">
          <Routes>
            <Route path="/"              element={<Navigate to="/home" replace />} />
            <Route path="/home"          element={<HomePage />}          />
            <Route path="/category"      element={<CategoryPage />}      />
            <Route path="/product/:id"   element={<ProductPage />}       />
            <Route path="/cart"          element={<CartPage />}          />
            <Route path="/checkout"      element={<CheckoutPage />}      />
            <Route path="/success"       element={<OrderSuccessPage />}  />
            <Route path="/track"         element={<OrderTrackingPage />} />
            <Route path="/ai"            element={<AIPage />}            />
            <Route path="/search"        element={<SearchPage />}        />
            <Route path="/profile"       element={<ProfilePage />}       />
            <Route path="/login"         element={<LoginPage />}         />
          </Routes>
        </div>
        <BottomNav />
        <ToastStack />
      </div>
    </BrowserRouter>
  );
}
