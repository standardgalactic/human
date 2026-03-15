// src/pages/LoginPage.tsx
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { users } from "../lib/api";
import { useAuth } from "../stores";

export default function LoginPage() {
  const navigate    = useNavigate();
  const { setAuth } = useAuth();
  const [tab,      setTab]      = useState<"login"|"register">("login");
  const [username, setUsername] = useState("");
  const [email,    setEmail]    = useState("");
  const [password, setPassword] = useState("");
  const [error,    setError]    = useState("");
  const [loading,  setLoading]  = useState(false);

  async function handleRegister(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true); setError("");
    try {
      const user = await users.register(username, email, password);
      // In real impl: also get token from /auth/token
      setAuth("placeholder_token", user);
      navigate("/");
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  const inputStyle = {
    display: "block", width: "100%", padding: ".5rem .9rem",
    background: "var(--surface2)", border: "1px solid var(--border)",
    borderRadius: "var(--r)", color: "var(--text)", fontSize: ".9rem",
    marginBottom: ".75rem",
  };

  return (
    <div style={{ maxWidth: 400, margin: "4rem auto", padding: "0 1.5rem" }}>
      <div className="card">
        <div style={{ textAlign: "center", marginBottom: "1.5rem" }}>
          <div style={{ fontSize: "1.3rem", color: "var(--accent2)", fontWeight: 700 }}>⌘ ZebraTube</div>
          <div style={{ fontSize: ".85rem", color: "var(--muted)", marginTop: ".3rem" }}>
            Download the script. Make the missing scene.
          </div>
        </div>

        <div className="tabs" style={{ marginBottom: "1.5rem" }}>
          <div className={`tab${tab === "login" ? " active" : ""}`} onClick={() => setTab("login")}>Sign in</div>
          <div className={`tab${tab === "register" ? " active" : ""}`} onClick={() => setTab("register")}>Register</div>
        </div>

        <form onSubmit={tab === "register" ? handleRegister : handleRegister}>
          {tab === "register" && (
            <>
              <input value={username} onChange={e => setUsername(e.target.value)}
                placeholder="Username" required style={inputStyle} />
              <input value={email} onChange={e => setEmail(e.target.value)}
                placeholder="Email" type="email" required style={inputStyle} />
            </>
          )}
          {tab === "login" && (
            <input value={email} onChange={e => setEmail(e.target.value)}
              placeholder="Email or username" required style={inputStyle} />
          )}
          <input value={password} onChange={e => setPassword(e.target.value)}
            placeholder="Password" type="password" required style={inputStyle} />

          {error && <div style={{ color: "var(--red)", fontSize: ".85rem", marginBottom: ".75rem" }}>{error}</div>}

          <button type="submit" className="btn btn-primary" style={{ width: "100%", justifyContent: "center" }} disabled={loading}>
            {loading ? "…" : tab === "register" ? "Create account" : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}
