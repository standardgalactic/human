// src/pages/TaskPage.tsx

import { useState, useRef } from "react";
import { useParams, Link } from "react-router-dom";
import useSWR, { mutate } from "swr";
import { tasks as tasksApi, claims as claimsApi, submissions as submissionsApi } from "../lib/api";
import type { Task, Submission, Claim } from "../lib/api";
import { useAuth } from "../stores";

// ── Bounty display ────────────────────────────────────────────────────────────

function BountyPanel({ task }: { task: Task }) {
  const bars = Math.round(task.scarcity * 10);
  return (
    <div className="card" style={{ marginBottom: "1rem" }}>
      <div style={{ fontSize: ".72rem", textTransform: "uppercase", letterSpacing: ".1em", color: "var(--muted)", marginBottom: ".5rem" }}>
        Bounty
      </div>
      <div style={{ fontSize: "1.8rem", fontFamily: "var(--mono)", color: "var(--green)", marginBottom: ".3rem" }}>
        {task.current_bounty.toFixed(0)} <span style={{ fontSize: ".9rem", color: "var(--muted)" }}>pts</span>
      </div>
      <div style={{ display: "flex", gap: "2px", marginBottom: ".4rem" }}>
        {Array.from({ length: 10 }).map((_, i) => (
          <div key={i} style={{
            flex: 1, height: 4, borderRadius: 2,
            background: i < bars ? "var(--green)" : "var(--border)",
          }} />
        ))}
      </div>
      <div style={{ fontSize: ".75rem", color: "var(--muted)" }}>
        Scarcity {task.scarcity.toFixed(2)} · Weight {task.assembly_weight.toFixed(2)}
      </div>
    </div>
  );
}

// ── Claim panel ───────────────────────────────────────────────────────────────

function ClaimPanel({ task, activeClaim }: { task: Task; activeClaim: Claim | null }) {
  const { user } = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState("");

  async function handleClaim() {
    if (!user) { setError("Sign in to claim tasks"); return; }
    setLoading(true); setError("");
    try {
      await claimsApi.create(task.id);
      mutate("claims-mine");
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleWithdraw() {
    if (!activeClaim) return;
    setLoading(true);
    try {
      await claimsApi.withdraw(activeClaim.id);
      mutate("claims-mine");
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  if (activeClaim) {
    const expires = new Date(activeClaim.expires_at);
    const hoursLeft = Math.max(0, (expires.getTime() - Date.now()) / 3600000);
    return (
      <div className="card" style={{ borderColor: "var(--accent)", marginBottom: "1rem" }}>
        <div style={{ color: "var(--accent2)", fontWeight: 700, marginBottom: ".3rem" }}>✓ Claimed</div>
        <div style={{ fontSize: ".8rem", color: "var(--muted)", marginBottom: ".75rem" }}>
          Expires in {hoursLeft.toFixed(1)}h
        </div>
        <a href={tasksApi.bundleUrl(task.id)} download className="btn btn-primary" style={{ marginRight: ".5rem" }}>
          ↓ Download script package
        </a>
        <button className="btn btn-danger btn-sm" onClick={handleWithdraw} disabled={loading}>
          Withdraw claim
        </button>
        {error && <div style={{ color: "var(--red)", fontSize: ".8rem", marginTop: ".5rem" }}>{error}</div>}
      </div>
    );
  }

  return (
    <div className="card" style={{ marginBottom: "1rem" }}>
      <button className="btn btn-primary" style={{ width: "100%", justifyContent: "center" }}
        onClick={handleClaim} disabled={loading || task.status === "saturated"}>
        {task.status === "saturated" ? "Task saturated" : loading ? "Claiming…" : "Claim this task"}
      </button>
      <div style={{ fontSize: ".75rem", color: "var(--muted)", marginTop: ".5rem" }}>
        72-hour window · bundle downloads automatically on claim
      </div>
      {error && <div style={{ color: "var(--red)", fontSize: ".8rem", marginTop: ".5rem" }}>{error}</div>}
    </div>
  );
}

// ── Upload panel ──────────────────────────────────────────────────────────────

function UploadPanel({ task, activeClaim }: { task: Task; activeClaim: Claim | null }) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [error,     setError]     = useState("");
  const [done,      setDone]      = useState(false);
  const [branchLabel, setBranch]  = useState("");
  const [notes,       setNotes]   = useState("");

  if (!activeClaim) return null;

  async function handleUpload() {
    const file = fileRef.current?.files?.[0];
    if (!file) { setError("Select a file first"); return; }

    const form = new FormData();
    form.append("claim_id",    activeClaim!.id);
    form.append("task_id",     task.id);
    form.append("file",        file);
    if (branchLabel) form.append("branch_label", branchLabel);
    if (notes)       form.append("notes",        notes);

    setUploading(true); setError("");
    try {
      await submissionsApi.upload(form);
      setDone(true);
      mutate(`submissions-${task.id}`);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setUploading(false);
    }
  }

  if (done) {
    return (
      <div className="card" style={{ borderColor: "var(--green)", marginBottom: "1rem" }}>
        <div style={{ color: "var(--green)", fontWeight: 700 }}>✓ Submission received</div>
        <div style={{ fontSize: ".8rem", color: "var(--muted)", marginTop: ".3rem" }}>
          Under review. You'll be notified when a selector reviews it.
        </div>
      </div>
    );
  }

  const spec = task.output_spec ?? {};
  return (
    <div className="card" style={{ marginBottom: "1rem" }}>
      <div style={{ fontSize: ".72rem", textTransform: "uppercase", letterSpacing: ".1em", color: "var(--muted)", marginBottom: ".75rem" }}>
        Upload submission
      </div>

      <div style={{ fontSize: ".8rem", color: "var(--muted)", marginBottom: ".75rem" }}>
        Accepted formats: {(spec as any).accepted_types?.join(", ") ?? ".mp4 .webm .mp3 .wav .png .svg"}
      </div>

      <input ref={fileRef} type="file" style={{ display: "block", marginBottom: ".75rem", color: "var(--text)", fontSize: ".85rem" }} />

      <input
        placeholder="Branch label (optional — e.g. 'chalkboard version')"
        value={branchLabel} onChange={e => setBranch(e.target.value)}
        style={{ width: "100%", padding: ".4rem .7rem", background: "var(--surface2)", border: "1px solid var(--border)", borderRadius: "var(--r)", color: "var(--text)", marginBottom: ".5rem", fontSize: ".85rem" }}
      />
      <textarea
        placeholder="Notes to selectors (optional)"
        value={notes} onChange={e => setNotes(e.target.value)} rows={2}
        style={{ width: "100%", padding: ".4rem .7rem", background: "var(--surface2)", border: "1px solid var(--border)", borderRadius: "var(--r)", color: "var(--text)", resize: "vertical", fontSize: ".85rem", marginBottom: ".75rem" }}
      />

      <button className="btn btn-primary" onClick={handleUpload} disabled={uploading}>
        {uploading ? "Uploading…" : "Submit"}
      </button>
      {error && <div style={{ color: "var(--red)", fontSize: ".8rem", marginTop: ".5rem" }}>{error}</div>}
    </div>
  );
}

// ── Submissions list ──────────────────────────────────────────────────────────

function SubmissionsList({ taskId }: { taskId: string }) {
  const { data: subs } = useSWR(`submissions-${taskId}`, () => submissionsApi.forTask(taskId));
  if (!subs?.length) return null;
  return (
    <div style={{ marginTop: "1rem" }}>
      <div style={{ fontSize: ".72rem", textTransform: "uppercase", letterSpacing: ".1em", color: "var(--muted)", marginBottom: ".5rem" }}>
        {subs.length} submission{subs.length !== 1 ? "s" : ""}
      </div>
      {subs.map(s => (
        <div key={s.id} className="card" style={{ marginBottom: ".5rem", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <div style={{ fontSize: ".85rem", fontWeight: 600 }}>
              {s.branch_label || "default"}
            </div>
            <div style={{ fontSize: ".75rem", color: "var(--muted)" }}>
              {new Date(s.submitted_at).toLocaleDateString()}
              {s.media_metadata && (` · ${(s.media_metadata as any).duration ?? ""}s`)}
            </div>
          </div>
          <span className={`badge badge-${s.status}`}>{s.status}</span>
        </div>
      ))}
    </div>
  );
}

// ── TaskPage ──────────────────────────────────────────────────────────────────

export default function TaskPage() {
  const { taskId } = useParams<{ taskId: string }>();
  const { data: task,  error } = useSWR(taskId ? `task-${taskId}` : null, () => tasksApi.get(taskId!));
  const { data: claims }       = useSWR("claims-mine", () => claimsApi.mine());

  if (error)  return <div className="wrapper empty" style={{ paddingTop: "3rem" }}>Task not found.</div>;
  if (!task)  return <div className="wrapper empty" style={{ paddingTop: "3rem" }}>Loading…</div>;

  const activeClaim = (claims ?? []).find(c => c.task_id === task.id && c.status === "active") ?? null;
  const spec = task.output_spec ?? {};

  return (
    <div className="wrapper" style={{ padding: "1.5rem" }}>
      <div style={{ fontSize: ".8rem", color: "var(--muted)", marginBottom: "1rem" }}>
        <Link to="/">Home</Link> / <Link to={`/projects/${task.project_id}`}>Project</Link> / Task
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 320px", gap: "2rem", alignItems: "start" }}>

        {/* Left: brief */}
        <div>
          <div className="page-header" style={{ border: "none", padding: "0 0 1rem" }}>
            <div style={{ display: "flex", gap: ".5rem", marginBottom: ".5rem" }}>
              <span style={{ fontSize: ".72rem", fontFamily: "var(--mono)", color: "var(--muted)", background: "var(--surface2)", padding: ".15rem .5rem", borderRadius: "var(--r)" }}>
                {task.projection_type}
              </span>
              <span className={`badge badge-${task.difficulty}`}>{task.difficulty}</span>
              <span className={`badge badge-${task.status}`}>{task.status}</span>
            </div>
            <h1 style={{ fontSize: "1.3rem" }}>{task.label}</h1>
          </div>

          {/* Script */}
          <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--r-lg)", padding: "1.2rem", marginBottom: "1.5rem" }}>
            <div style={{ fontSize: ".72rem", textTransform: "uppercase", letterSpacing: ".1em", color: "var(--accent)", fontFamily: "var(--mono)", marginBottom: ".75rem" }}>
              Script
            </div>
            <pre style={{ whiteSpace: "pre-wrap", fontFamily: "var(--mono)", fontSize: ".82rem", color: "var(--text)", lineHeight: 1.65 }}>
              {/* Script text would be loaded from the bundle */}
              Script text available in the downloaded bundle.
            </pre>
          </div>

          {/* Style */}
          {task.style_hint && (
            <div style={{ marginBottom: "1.5rem" }}>
              <div style={{ fontSize: ".72rem", textTransform: "uppercase", letterSpacing: ".1em", color: "var(--accent)", fontFamily: "var(--mono)", marginBottom: ".4rem" }}>
                Style notes
              </div>
              <p style={{ fontSize: ".88rem", color: "var(--muted)", lineHeight: 1.7 }}>{task.style_hint}</p>
            </div>
          )}

          {/* Output spec */}
          <div style={{ marginBottom: "1.5rem" }}>
            <div style={{ fontSize: ".72rem", textTransform: "uppercase", letterSpacing: ".1em", color: "var(--accent)", fontFamily: "var(--mono)", marginBottom: ".4rem" }}>
              Output requirements
            </div>
            <div style={{ display: "flex", gap: "1.5rem", flexWrap: "wrap" }}>
              {Object.entries(spec as Record<string,string>).map(([k, v]) => (
                <div key={k} style={{ fontSize: ".82rem" }}>
                  <span style={{ color: "var(--muted)" }}>{k}: </span>
                  <span>{v}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Dependencies */}
          {task.depends_on?.length ? (
            <div style={{ marginBottom: "1.5rem" }}>
              <div style={{ fontSize: ".72rem", textTransform: "uppercase", letterSpacing: ".1em", color: "var(--muted)", fontFamily: "var(--mono)", marginBottom: ".4rem" }}>
                Depends on
              </div>
              {task.depends_on.map(depId => (
                <Link key={depId} to={`/tasks/${depId}`} style={{ display: "block", fontSize: ".82rem", marginBottom: ".2rem" }}>
                  → {depId}
                </Link>
              ))}
            </div>
          ) : null}

          {/* Graph nodes */}
          {task.graph_nodes?.length ? (
            <div>
              <div style={{ fontSize: ".72rem", textTransform: "uppercase", letterSpacing: ".1em", color: "var(--muted)", fontFamily: "var(--mono)", marginBottom: ".4rem" }}>
                Source graph nodes
              </div>
              <div style={{ display: "flex", gap: ".4rem", flexWrap: "wrap" }}>
                {task.graph_nodes.map(n => (
                  <span key={n} style={{ fontSize: ".72rem", fontFamily: "var(--mono)", background: "var(--surface2)", padding: ".15rem .4rem", borderRadius: "var(--r)", color: "var(--muted)" }}>{n}</span>
                ))}
              </div>
            </div>
          ) : null}
        </div>

        {/* Right: action panel */}
        <div>
          <BountyPanel task={task} />
          <ClaimPanel  task={task} activeClaim={activeClaim} />
          <UploadPanel task={task} activeClaim={activeClaim} />
          <SubmissionsList taskId={task.id} />
        </div>
      </div>
    </div>
  );
}
