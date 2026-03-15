// src/pages/SearchPage.tsx
import { useState } from "react";
import { Link } from "react-router-dom";
import { search as searchApi } from "../lib/api";
import type { SearchResult } from "../lib/api";

export default function SearchPage() {
  const [query,   setQuery]   = useState("");
  const [mode,    setMode]    = useState("full");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);

  const TYPE_ICON: Record<string,string> = {
    entity: "◉", event: "▶", claim: "◆", theme: "◈", task: "⊞", project: "⌘",
  };

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    try {
      const res = await searchApi.query(query, mode, undefined, 20);
      setResults(res);
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="wrapper" style={{ padding: "1.5rem" }}>
      <div className="page-header">
        <h1>Search</h1>
        <p>Query the semantic structure of all indexed corpora — not just titles and tags.</p>
      </div>

      <form onSubmit={handleSearch} style={{ display: "flex", gap: ".75rem", marginBottom: "1.5rem", flexWrap: "wrap" }}>
        <input
          value={query} onChange={e => setQuery(e.target.value)}
          placeholder="Search entities, claims, themes, tasks…"
          style={{ flex: 1, minWidth: 240, padding: ".5rem .9rem", background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--r)", color: "var(--text)", fontSize: ".9rem" }}
        />
        <select value={mode} onChange={e => setMode(e.target.value)}
          style={{ padding: ".5rem .9rem", background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--r)", color: "var(--text)", fontSize: ".9rem" }}>
          {["full","entity","claim","theme","task"].map(m => <option key={m} value={m}>{m}</option>)}
        </select>
        <button type="submit" className="btn btn-primary" disabled={loading}>
          {loading ? "Searching…" : "Search"}
        </button>
      </form>

      {results.length === 0 && !loading && query && (
        <div className="empty">No results for "{query}".</div>
      )}

      {results.map(r => (
        <div key={r.id} className="card" style={{ marginBottom: ".6rem", display: "flex", gap: "1rem", alignItems: "flex-start" }}>
          <div style={{ fontSize: "1.2rem", color: "var(--accent)", minWidth: 24, marginTop: ".1rem" }}>
            {TYPE_ICON[r.type] ?? "○"}
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ display: "flex", gap: ".5rem", alignItems: "center", marginBottom: ".2rem" }}>
              <span style={{ fontWeight: 600 }}>{r.label}</span>
              <span style={{ fontSize: ".72rem", fontFamily: "var(--mono)", color: "var(--muted)" }}>{r.type}</span>
              <span style={{ fontSize: ".72rem", color: "var(--muted)", marginLeft: "auto" }}>
                score {r.score.toFixed(2)}
              </span>
            </div>
            {r.project_id && (
              <Link to={`/projects/${r.project_id}`} style={{ fontSize: ".8rem" }}>
                → project
              </Link>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
