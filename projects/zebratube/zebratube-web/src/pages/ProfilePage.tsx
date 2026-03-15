// src/pages/ProfilePage.tsx
import { useParams } from "react-router-dom";
import useSWR from "swr";
import { users } from "../lib/api";

export default function ProfilePage() {
  const { username } = useParams<{ username: string }>();
  const { data: profile, error } = useSWR(
    username ? `user-${username}` : null,
    () => username === "me" ? users.me() : users.get(username!),
  );

  if (error)    return <div className="wrapper empty" style={{ paddingTop: "3rem" }}>User not found.</div>;
  if (!profile) return <div className="wrapper empty" style={{ paddingTop: "3rem" }}>Loading…</div>;

  const tier = profile.role;

  return (
    <div className="wrapper" style={{ padding: "1.5rem" }}>
      <div className="page-header">
        <h1>{profile.username}</h1>
        <div className="flex gap-2" style={{ marginTop: ".5rem" }}>
          <span className="badge" style={{ background: "var(--surface2)", color: "var(--accent2)" }}>{tier}</span>
          <span className="stat">Points <span>{profile.point_balance}</span></span>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem" }}>
        {/* Contributions */}
        <div>
          <h3 style={{ fontSize: ".8rem", textTransform: "uppercase", letterSpacing: ".1em", color: "var(--muted)", marginBottom: ".75rem" }}>
            Contributions by type
          </h3>
          {Object.entries(profile.contributions ?? {}).length === 0
            ? <div className="empty" style={{ padding: "1rem" }}>No contributions yet.</div>
            : Object.entries(profile.contributions).map(([type, count]) => (
              <div key={type} style={{ display: "flex", justifyContent: "space-between", padding: ".4rem 0", borderBottom: "1px solid var(--border)", fontSize: ".85rem" }}>
                <span style={{ fontFamily: "var(--mono)", color: "var(--muted)" }}>{type}</span>
                <span style={{ color: "var(--accent2)" }}>{count}</span>
              </div>
            ))
          }
        </div>

        {/* Specialisations */}
        <div>
          <h3 style={{ fontSize: ".8rem", textTransform: "uppercase", letterSpacing: ".1em", color: "var(--muted)", marginBottom: ".75rem" }}>
            Specialisations
          </h3>
          <div className="flex gap-1" style={{ flexWrap: "wrap" }}>
            {(profile.specialisations ?? []).length === 0
              ? <div style={{ fontSize: ".85rem", color: "var(--muted)" }}>Derived from completed tasks.</div>
              : (profile.specialisations ?? []).map(s => (
                <span key={s} className="badge" style={{ background: "var(--surface2)", color: "var(--text)" }}>{s}</span>
              ))
            }
          </div>
        </div>
      </div>

      {/* Person graph */}
      {profile.person_graph_public && profile.person_graph && (
        <div style={{ marginTop: "2rem" }}>
          <h3 style={{ fontSize: ".8rem", textTransform: "uppercase", letterSpacing: ".1em", color: "var(--muted)", marginBottom: ".75rem" }}>
            Semantic portrait
          </h3>
          <div className="card">
            <div style={{ fontSize: ".85rem", color: "var(--muted)" }}>
              Person graph visible — concept network, intellectual trajectory, and open questions derived from this contributor's public corpus.
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
