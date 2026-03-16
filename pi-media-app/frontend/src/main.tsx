import React from "react";
import ReactDOM from "react-dom/client";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import App from "./App";
import Dashboard from "./pages/Dashboard";
import Upload from "./pages/Upload";
import MediaLibrary from "./pages/MediaLibrary";
import "./styles/global.css";

const router = createBrowserRouter([
  {
    path: "/",
    element: <App />,
    children: [
      { index: true, element: <Dashboard /> },
      { path: "upload", element: <Upload /> },
      { path: "media", element: <MediaLibrary /> },
      {
        path: "profiles",
        element: (
          <div className="page">
            <h1 className="page-title">Profiles</h1>
            <div className="empty-state">Coming soon</div>
          </div>
        ),
      },
    ],
  },
]);

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>
);
