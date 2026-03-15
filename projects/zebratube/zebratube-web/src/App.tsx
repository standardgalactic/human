// src/App.tsx

import { BrowserRouter, Routes, Route, NavLink, Navigate } from "react-router-dom";
import { Suspense, lazy } from "react";
import "./index.css";

// Lazy pages
const HomePage      = lazy(() => import("./pages/HomePage"));
const ProjectPage   = lazy(() => import("./pages/ProjectPage"));
const TaskPage      = lazy(() => import("./pages/TaskPage"));
const ProfilePage   = lazy(() => import("./pages/ProfilePage"));
const AssemblyPage  = lazy(() => import("./pages/AssemblyPage"));
const SearchPage    = lazy(() => import("./pages/SearchPage"));
const LoginPage     = lazy(() => import("./pages/LoginPage"));

function Nav() {
  return (
    <nav style={{
      borderBottom: "1px solid var(--border)",
      padding: ".65rem 0",
      position: "sticky", top: 0, zIndex: 100,
      background: "rgba(10,10,20,.96)",
      backdropFilter: "blur(8px)",
    }}>
      <div className="wrapper flex" style={{ alignItems: "center", justifyContent: "space-between" }}>
        <NavLink to="/" style={{ color: "var(--accent2)", fontWeight: 700, fontSize: "1rem", letterSpacing: ".05em" }}>
          ⌘ ZebraTube
        </NavLink>
        <div className="flex gap-2" style={{ fontSize: ".85rem" }}>
          <NavLink to="/search" style={({ isActive }) => ({ color: isActive ? "var(--text)" : "var(--muted)" })}>
            Search
          </NavLink>
          <NavLink to="/profile/me" style={({ isActive }) => ({ color: isActive ? "var(--text)" : "var(--muted)" })}>
            Profile
          </NavLink>
          <NavLink to="/login" className="btn btn-sm btn-primary">Sign in</NavLink>
        </div>
      </div>
    </nav>
  );
}

function Loader() {
  return (
    <div className="empty" style={{ paddingTop: "4rem" }}>
      Loading…
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Nav />
      <Suspense fallback={<Loader />}>
        <Routes>
          <Route path="/"                   element={<HomePage />} />
          <Route path="/projects/:slug"     element={<ProjectPage />} />
          <Route path="/tasks/:taskId"      element={<TaskPage />} />
          <Route path="/profile/:username"  element={<ProfilePage />} />
          <Route path="/assembly/:id"       element={<AssemblyPage />} />
          <Route path="/search"             element={<SearchPage />} />
          <Route path="/login"              element={<LoginPage />} />
          <Route path="*"                   element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
}
