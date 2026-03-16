import { NavLink, Outlet } from "react-router-dom";

export default function App() {
  return (
    <>
      <Outlet />
      <nav className="bottom-nav">
        <NavLink to="/" end>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M3 12l9-9 9 9" />
            <path d="M5 10v10h5v-6h4v6h5V10" />
          </svg>
          Home
        </NavLink>
        <NavLink to="/upload">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12 5v14M5 12h14" />
          </svg>
          Upload
        </NavLink>
        <NavLink to="/media">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="3" y="3" width="7" height="7" rx="1" />
            <rect x="14" y="3" width="7" height="7" rx="1" />
            <rect x="3" y="14" width="7" height="7" rx="1" />
            <rect x="14" y="14" width="7" height="7" rx="1" />
          </svg>
          Library
        </NavLink>
        <NavLink to="/profiles">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="4" y="4" width="16" height="16" rx="2" />
            <path d="M9 9h6M9 13h4" />
          </svg>
          Profiles
        </NavLink>
      </nav>
    </>
  );
}
