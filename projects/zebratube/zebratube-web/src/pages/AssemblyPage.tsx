// src/pages/AssemblyPage.tsx

import { useState, useCallback } from "react";
import { useSearchParams } from "react-router-dom";
import useSWR from "swr";
import { tasks as tasksApi, assemblies as assembliesApi, submissions as submissionsApi } from "../lib/api";
import type { Task, Submission } from "../lib/api";

interface Slot {
  position:      number;
  task_id:       string;
  task_label:    string;
  submission_id: string | null;
  branch_label:  string | null;
  is_gap:        boolean;
}

// ── Slot component ────────────────────────────────────────────────────────────

function AssemblySlot({
  slot, onSelectSubmission, onClear, onMove,
}: {
  slot:                Slot;
  onSelectSubmission:  (pos: number, subId: string, branchLabel: string | null) => void;
  onClear:             (pos: number) => void;
  onMove:              (from: number, dir: -1 | 1) => void;
}) {
  const { data: subs } = useSWR(
    `submissions-slot-${slot.task_id}`,
    () => submissionsApi.forTask(slot.task_id),
  );
  const accepted = (subs ?? []).filter(s => s.status === "accepted" || s.status === "branch");

  return (
    <div style={{
      background: slot.is_gap ? "rgba(255,85,100,.05)" : "var(--surface)",
      border: `1px solid ${slot.is_gap ? "var(--red)" : slot.submission_id ? "var(--green)" : "var(--border)"}`,
      borderRadius: "var(--r-lg)",
      padding: "1rem",
      position: "relative",
    }}>
      {/* Position badge */}
      <div style={{ position: "absolute", top: ".5rem", right: ".5rem", fontSize: ".7rem", fontFamily: "var(--mono)", color: "var(--muted)" }}>
        #{slot.position + 1}
      </div>

      <div style={{ fontWeight: 600, marginBottom: ".4rem", fontSize: ".88rem", paddingRight: "2rem" }}>
        {slot.task_label}
      </div>

      {slot.is_gap
        ? <div style={{ color: "var(--red)", fontSize: ".8rem", marginBottom: ".5rem" }}>⚠ No submission selected</div>
        : <div style={{ color: "var(--green)", fontSize: ".8rem", marginBottom: ".5rem" }}>
            ✓ {slot.branch_label ?? "default"}
          </div>
      }

      {/* Submission selector */}
      {accepted.length > 0 && (
        <select
          value={slot.submission_id ?? ""}
          onChange={e => {
            const sub = accepted.find(s => s.id === e.target.value);
            if (sub) onSelectSubmission(slot.position, sub.id, sub.branch_label);
          }}
          style={{ display: "block", width: "100%", marginBottom: ".5rem", padding: ".35rem .6rem", background: "var(--surface2)", border: "1px solid var(--border)", borderRadius: "var(--r)", color: "var(--text)", fontSize: ".82rem" }}
        >
          <option value="">— select submission —</option>
          {accepted.map(s => (
            <option key={s.id} value={s.id}>
              {s.branch_label ?? "default"} · {new Date(s.submitted_at).toLocaleDateString()}
            </option>
          ))}
        </select>
      )}

      <div className="flex gap-1">
        <button className="btn btn-sm" onClick={() => onMove(slot.position, -1)}>↑</button>
        <button className="btn btn-sm" onClick={() => onMove(slot.position,  1)}>↓</button>
        {slot.submission_id && (
          <button className="btn btn-sm btn-danger" onClick={() => onClear(slot.position)}>Clear</button>
        )}
      </div>
    </div>
  );
}

// ── AssemblyPage ──────────────────────────────────────────────────────────────

export default function AssemblyPage() {
  const [searchParams] = useSearchParams();
  const versionId      = searchParams.get("version") ?? "";
  const [slots, setSlots] = useState<Slot[]>([]);
  const [exporting, setExporting] = useState(false);
  const [exported,  setExported]  = useState(false);
  const [error,     setError]     = useState("");

  const { data: taskList } = useSWR(
    versionId ? `tasks-assembly-${versionId}` : null,
    () => tasksApi.list({ status: "accepted", limit: 100 }),
    {
      onSuccess: (tasks) => {
        if (slots.length === 0) {
          setSlots(tasks.map((t, i) => ({
            position:      i,
            task_id:       t.id,
            task_label:    t.label,
            submission_id: null,
            branch_label:  null,
            is_gap:        true,
          })));
        }
      },
    }
  );

  const selectSubmission = useCallback((pos: number, subId: string, branchLabel: string | null) => {
    setSlots(prev => prev.map(s =>
      s.position === pos ? { ...s, submission_id: subId, branch_label: branchLabel, is_gap: false } : s
    ));
  }, []);

  const clearSlot = useCallback((pos: number) => {
    setSlots(prev => prev.map(s =>
      s.position === pos ? { ...s, submission_id: null, branch_label: null, is_gap: true } : s
    ));
  }, []);

  const moveSlot = useCallback((pos: number, dir: -1 | 1) => {
    setSlots(prev => {
      const next = [...prev];
      const idx  = next.findIndex(s => s.position === pos);
      const swap = idx + dir;
      if (swap < 0 || swap >= next.length) return prev;
      [next[idx], next[swap]] = [next[swap], next[idx]];
      return next.map((s, i) => ({ ...s, position: i }));
    });
  }, []);

  async function handleExport() {
    setExporting(true); setError("");
    try {
      await assembliesApi.create({
        project_version_id: versionId,
        title: "Assembly export",
        segments: slots.map(s => ({
          task_id:       s.task_id,
          submission_id: s.submission_id ?? undefined,
          position:      s.position,
          is_canonical:  true,
        })),
      });
      setExported(true);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setExporting(false);
    }
  }

  const gapCount      = slots.filter(s => s.is_gap).length;
  const filledCount   = slots.length - gapCount;
  const pct           = slots.length ? Math.round(100 * filledCount / slots.length) : 0;

  return (
    <div className="wrapper" style={{ padding: "1.5rem" }}>
      <div className="page-header">
        <h1>Assembly Workspace</h1>
        <p>Arrange accepted submissions into a final sequence. Gaps are shown in red.</p>
      </div>

      {/* Status bar */}
      <div className="stats-bar" style={{ marginBottom: "1.5rem" }}>
        <div className="stat">slots <span>{slots.length}</span></div>
        <div className="stat">filled <span>{filledCount}</span></div>
        <div className="stat">gaps <span style={{ color: gapCount > 0 ? "var(--red)" : "var(--green)" }}>{gapCount}</span></div>
        <div className="stat">complete <span>{pct}%</span></div>
      </div>

      {/* Progress bar */}
      <div style={{ height: 6, background: "var(--surface)", borderRadius: 3, marginBottom: "1.5rem", overflow: "hidden" }}>
        <div style={{ width: `${pct}%`, height: "100%", background: pct === 100 ? "var(--green)" : "var(--accent)", transition: "width .3s" }} />
      </div>

      {/* Timeline grid */}
      {slots.length === 0
        ? <div className="empty">No accepted submissions yet. Tasks need accepted submissions before assembly.</div>
        : (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(240px,1fr))", gap: "1rem", marginBottom: "2rem" }}>
            {slots.map(slot => (
              <AssemblySlot
                key={slot.task_id}
                slot={slot}
                onSelectSubmission={selectSubmission}
                onClear={clearSlot}
                onMove={moveSlot}
              />
            ))}
          </div>
        )
      }

      {/* Export */}
      {slots.length > 0 && (
        <div>
          {exported
            ? <div style={{ color: "var(--green)", fontWeight: 700 }}>✓ Assembly spec saved. Render job queued.</div>
            : (
              <>
                <button
                  className="btn btn-primary"
                  onClick={handleExport}
                  disabled={exporting || gapCount > 0}
                  style={{ marginRight: ".75rem" }}
                >
                  {exporting ? "Exporting…" : `Export assembly spec${gapCount > 0 ? ` (${gapCount} gaps)` : ""}`}
                </button>
                {gapCount > 0 && (
                  <button className="btn" onClick={handleExport} disabled={exporting}>
                    Export with gaps
                  </button>
                )}
              </>
            )
          }
          {error && <div style={{ color: "var(--red)", fontSize: ".85rem", marginTop: ".5rem" }}>{error}</div>}
        </div>
      )}
    </div>
  );
}
