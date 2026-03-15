// src/pages/SelectorPage.tsx
// Side-by-side comparison interface for reviewing alternative submissions.

import { useState } from "react"
import { useParams, Link } from "react-router-dom"
import useSWR from "swr"
import { tasks as tasksApi, submissions as submissionsApi, reviews } from "../lib/api"
import type { Submission, Task } from "../lib/api"

// ── Media player ───────────────────────────────────────────────────────────

function MediaPlayer({ sub }: { sub: Submission }) {
  const url = sub.preview_url

  if (!url) {
    return (
      <div style={{
        width: "100%", aspectRatio: "16/9",
        background: "var(--surface)", border: "1px solid var(--border)",
        borderRadius: 4, display: "flex", alignItems: "center",
        justifyContent: "center", color: "var(--muted)", fontSize: ".8rem",
      }}>
        Processing…
      </div>
    )
  }

  const ext = url.split(".").pop()?.toLowerCase()

  if (ext === "mp3" || ext === "wav" || ext === "ogg") {
    return (
      <div style={{ padding: "1rem 0" }}>
        {sub.thumbnail_url && (
          <img src={sub.thumbnail_url} alt="waveform"
               style={{ width: "100%", borderRadius: 4, marginBottom: ".5rem", opacity: .7 }} />
        )}
        <audio controls style={{ width: "100%" }}>
          <source src={url} />
        </audio>
      </div>
    )
  }

  if (ext === "png" || ext === "svg" || ext === "jpg") {
    return (
      <img src={url} alt="submission"
           style={{ width: "100%", borderRadius: 4, border: "1px solid var(--border)" }} />
    )
  }

  return (
    <video controls style={{ width: "100%", borderRadius: 4, background: "#000" }}>
      <source src={url} />
    </video>
  )
}

// ── Verdict buttons ────────────────────────────────────────────────────────

type Verdict = "approve" | "reject" | "request_revision" | "preserve_branch"

interface VerdictPanelProps {
  submission:  Submission
  onVerdict:   (verdict: Verdict, notes?: string) => void
  chosen?:     Verdict | null
  disabled?:   boolean
}

function VerdictPanel({ submission, onVerdict, chosen, disabled }: VerdictPanelProps) {
  const [notes, setNotes] = useState("")

  const buttons: Array<{ verdict: Verdict; label: string; color: string }> = [
    { verdict: "approve",          label: "✓ Approve",       color: "var(--green)"  },
    { verdict: "preserve_branch",  label: "⎇ Keep as branch", color: "var(--accent)" },
    { verdict: "request_revision", label: "↩ Request revision", color: "var(--orange)" },
    { verdict: "reject",           label: "✗ Reject",        color: "var(--red)"    },
  ]

  return (
    <div style={{ marginTop: "1rem" }}>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: ".4rem", marginBottom: ".6rem" }}>
        {buttons.map(b => (
          <button
            key={b.verdict}
            disabled={disabled}
            onClick={() => onVerdict(b.verdict, notes || undefined)}
            style={{
              padding: ".35rem .5rem",
              background: chosen === b.verdict ? b.color : "var(--surface)",
              border: `1px solid ${b.color}`,
              color: chosen === b.verdict ? "#000" : b.color,
              borderRadius: 4, fontSize: ".78rem", cursor: disabled ? "not-allowed" : "pointer",
              fontFamily: "var(--sans)", transition: "background .12s",
            }}
          >
            {b.label}
          </button>
        ))}
      </div>

      <textarea
        value={notes}
        onChange={e => setNotes(e.target.value)}
        placeholder="Optional notes for contributor…"
        rows={2}
        style={{ fontSize: ".8rem", resize: "vertical" }}
      />

      <div style={{ fontSize: ".72rem", color: "var(--muted)", marginTop: ".3rem" }}>
        <span style={{ marginRight: ".8rem" }}>
          Submitted: {new Date(submission.submitted_at).toLocaleDateString()}
        </span>
        {submission.branch_label && (
          <span>Branch: <code>{submission.branch_label}</code></span>
        )}
        {submission.media_metadata && (
          <span style={{ marginLeft: ".8rem" }}>
            {(submission.media_metadata as any).duration_s
              ? `${Math.ceil((submission.media_metadata as any).duration_s)}s`
              : ""}
          </span>
        )}
      </div>
    </div>
  )
}

// ── Submission column ──────────────────────────────────────────────────────

interface SubmissionColProps {
  sub:      Submission
  index:    number
  verdict?: Verdict | null
  onVerdict: (verdict: Verdict, notes?: string) => void
  submitting: boolean
}

function SubmissionCol({ sub, index, verdict, onVerdict, submitting }: SubmissionColProps) {
  const letters = ["A", "B", "C", "D"]

  return (
    <div style={{
      flex: 1, minWidth: 0,
      background: verdict === "approve" ? "rgba(68,255,136,.04)"
                : verdict === "reject"  ? "rgba(255,85,85,.04)"
                : "var(--surface)",
      border: `1px solid ${
        verdict === "approve" ? "var(--green)"
        : verdict === "reject" ? "var(--red)"
        : "var(--border)"
      }`,
      borderRadius: 4, padding: "1rem",
      transition: "border-color .15s, background .15s",
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: ".75rem" }}>
        <span style={{ fontFamily: "var(--mono)", color: "var(--accent2)", fontWeight: 700 }}>
          Submission {letters[index]}
        </span>
        <span style={{
          fontSize: ".72rem", fontFamily: "var(--mono)",
          color: sub.status === "accepted" ? "var(--green)"
               : sub.status === "rejected" ? "var(--red)"
               : "var(--muted)",
        }}>
          {sub.status}
        </span>
      </div>

      <MediaPlayer sub={sub} />

      {sub.notes && (
        <p style={{ fontSize: ".8rem", color: "var(--muted)", marginTop: ".75rem",
                    borderLeft: "2px solid var(--border)", paddingLeft: ".6rem" }}>
          {sub.notes}
        </p>
      )}

      <VerdictPanel
        submission={sub}
        onVerdict={onVerdict}
        chosen={verdict}
        disabled={submitting}
      />
    </div>
  )
}

// ── SelectorPage ───────────────────────────────────────────────────────────

export default function SelectorPage() {
  const { id: taskId } = useParams<{ id: string }>()

  const { data: task }    = useSWR(`task-${taskId}`, () => tasksApi.get(taskId!))
  const { data: subs, mutate: mutateSubs }
                          = useSWR(`subs-${taskId}`, () => submissionsApi.forTask(taskId!))

  const [verdicts, setVerdicts]     = useState<Record<string, Verdict>>({})
  const [submitting, setSubmitting] = useState(false)
  const [done, setDone]             = useState<Set<string>>(new Set())
  const [error, setError]           = useState<string | null>(null)

  const pendingSubs = (subs ?? []).filter(
    s => s.status === "pending" || s.status === "in_review"
  )
  const reviewedSubs = (subs ?? []).filter(s => done.has(s.id))

  const handleVerdict = async (subId: string, verdict: Verdict, notes?: string) => {
    setVerdicts(v => ({ ...v, [subId]: verdict }))
    setSubmitting(true)
    setError(null)
    try {
      await reviews.create(subId, verdict, notes)
      setDone(d => new Set([...d, subId]))
      mutateSubs()
    } catch (e: any) {
      setError(e.message)
    } finally {
      setSubmitting(false)
    }
  }

  if (!task) return <div className="wrapper"><div className="empty">Loading…</div></div>

  return (
    <div className="wrapper" style={{ padding: "1.5rem" }}>

      {/* Header */}
      <div style={{ marginBottom: "1.5rem" }}>
        <Link to={`/tasks/${taskId}`}
              style={{ fontSize: ".8rem", color: "var(--muted)", display: "block", marginBottom: ".4rem" }}>
          ← Back to task
        </Link>
        <h1 style={{ fontSize: "1.3rem", color: "var(--accent2)", marginBottom: ".3rem" }}>
          Select: {task.label}
        </h1>
        <div style={{ display: "flex", gap: "1rem", fontSize: ".8rem", color: "var(--muted)" }}>
          <span>{task.projection_type}</span>
          <span>{pendingSubs.length} pending review</span>
          <span style={{ color: "var(--accent2)" }}>
            {task.current_bounty.toFixed(0)} pts bounty
          </span>
        </div>
      </div>

      {error && (
        <div style={{ background: "rgba(255,85,85,.1)", border: "1px solid var(--red)",
                      borderRadius: 4, padding: ".75rem 1rem", marginBottom: "1rem",
                      fontSize: ".85rem", color: "var(--red)" }}>
          {error}
        </div>
      )}

      {/* Instruction */}
      <div style={{ background: "var(--surface)", border: "1px solid var(--border)",
                    borderRadius: 4, padding: ".75rem 1rem", marginBottom: "1.5rem",
                    fontSize: ".85rem", color: "var(--muted)" }}>
        Review each submission independently.
        <strong style={{ color: "var(--text)" }}> Approve</strong> to advance to assembly.
        <strong style={{ color: "var(--text)" }}> Keep as branch</strong> to preserve without setting as canonical.
        <strong style={{ color: "var(--text)" }}> Request revision</strong> to send back with notes.
        <strong style={{ color: "var(--text)" }}> Reject</strong> if not usable.
      </div>

      {/* Submission grid */}
      {pendingSubs.length === 0 ? (
        <div className="empty">
          No submissions pending review for this task.
          {(subs ?? []).length > 0 && " All submissions have been reviewed."}
        </div>
      ) : (
        <div style={{ display: "flex", gap: "1rem", alignItems: "flex-start", flexWrap: "wrap" }}>
          {pendingSubs.map((sub, i) => (
            <SubmissionCol
              key={sub.id}
              sub={sub}
              index={i}
              verdict={verdicts[sub.id] ?? null}
              onVerdict={(v, n) => handleVerdict(sub.id, v, n)}
              submitting={submitting}
            />
          ))}
        </div>
      )}

      {/* Already reviewed */}
      {reviewedSubs.length > 0 && (
        <div style={{ marginTop: "2rem" }}>
          <h3 style={{ fontSize: ".8rem", textTransform: "uppercase", letterSpacing: ".1em",
                       color: "var(--muted)", marginBottom: ".75rem" }}>
            Reviewed this session
          </h3>
          <div style={{ display: "flex", gap: ".5rem", flexWrap: "wrap" }}>
            {reviewedSubs.map(s => (
              <span key={s.id} style={{
                fontSize: ".75rem", fontFamily: "var(--mono)",
                padding: ".2rem .5rem", borderRadius: 3,
                background: "var(--surface)", border: "1px solid var(--border)",
                color: verdicts[s.id] === "approve" ? "var(--green)"
                     : verdicts[s.id] === "reject"  ? "var(--red)"
                     : "var(--muted)",
              }}>
                {s.id.slice(-6)} → {verdicts[s.id]}
              </span>
            ))}
          </div>
        </div>
      )}

    </div>
  )
}
