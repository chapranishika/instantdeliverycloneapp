import { useLocation, useNavigate } from "react-router-dom";
import { useCartStore } from "../../store";

const NAV = [
  { path: "/home",     icon: "🏠", label: "Home"       },
  { path: "/category", icon: "🗂️", label: "Categories"  },
  { path: "/cart",     icon: "🛒", label: "Cart",  badge: true },
  { path: "/ai",       icon: "✨", label: "AI"          },
  { path: "/profile",  icon: "👤", label: "Profile"     },
];

export default function BottomNav() {
  const navigate   = useNavigate();
  const { pathname } = useLocation();
  const totalItems = useCartStore((s) => s.totalItems());

  return (
    <nav className="bottom-nav">
      {NAV.map(({ path, icon, label, badge }) => {
        const active = pathname.startsWith(path);
        return (
          <button
            key={path}
            className={`nav-item${active ? " active" : ""}`}
            onClick={() => navigate(path)}
            aria-label={label}
          >
            <span className="nav-icon">
              {icon}
              {badge && totalItems > 0 && (
                <span className="nav-badge">
                  {totalItems > 9 ? "9+" : totalItems}
                </span>
              )}
            </span>
            <span className="nav-label">{label}</span>
          </button>
        );
      })}
    </nav>
  );
}
