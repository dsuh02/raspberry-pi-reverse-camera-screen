import { Link } from "react-router-dom";

export default function Dashboard() {
  return (
    <div className="page">
      <h1 className="page-title">Dashboard</h1>

      <div className="dashboard-section">
        <h2>Active Profile</h2>
        <p style={{ color: "var(--text-muted)" }}>No active profile</p>
      </div>

      <div className="dashboard-links">
        <Link to="/upload" className="btn btn-primary">
          Upload
        </Link>
        <Link to="/media" className="btn btn-outline">
          Library
        </Link>
      </div>
    </div>
  );
}
