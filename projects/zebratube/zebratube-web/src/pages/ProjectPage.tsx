// src/pages/ProjectPage.tsx

import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import useSWR from "swr";
import { projects as projectsApi, tasks as tasksApi } from "../lib/api";
import type { Task } from "../lib/api";
import GraphPanel from "../components/graph/GraphPanel";

// ── Tab definitions ───────────────────────────────────────────────────────────

const TABS = ["Overview", "Graph", "Scripts", "Submissions", "Assembly", "Alternatives", "History"] as const;
type Tab = typeof TABS[number];

// ── Overview tab ──────────────────────────────────────────────────────────────

function OverviewTab({ slug }: { slug: string }) {
  const [style, setStyle] = useState("science");
  const { data: wiki } = useSWR(`wiki-${slug}-${style}`, () => projectsApi.wiki(slug, style));

  const styles = ["science", "mathematical", "artistic", "construction"];

  return (
    <div>
      <div className="tabs" style={{ marginBottom: "1.2rem" }}>
        {styles.map(s => (
          <div key={s} className={`tab${style === s ? " active" : ""}`} onClick={() => setStyle(s)}>
            {s.charAt(0).toUpperCase() + s.slice(1)}
          </div>
        ))}
      </div>
      {wiki
        ? <WikiArticle article={wiki as Record<string,unknown>} />
        : <div className="empty">No article yet. Run <code>zebra wiki</code> to generate.</div>
      }
    </div>
  );
}

function WikiArticle({ article }: { article: Record<string,unknown> }) {
  const sections = (article.sections ?? []) as Array<{ heading: string; body: string }>;
  return (
    <div>
      <h2 style={{ fontSize: "1.3rem", color: "var(--accent2)", marginBottom: ".5rem" }}>
        {article.title as string}
      </h2>
      <p style={{ color: "var(--muted)", marginBottom: "1.5rem", borderLeft: "3px solid var(--border)", paddingLeft: "1rem" }}>
        {article.summary as string}
      </p>
      {sections.map(sec => (
        <div key={sec.heading} style={{ marginBottom: "1.5rem" }}>
          <div style={{ fontSize: ".72rem", textTransform: "uppercase", letterSpacing: ".12em", color: "var(--accent)", fontFamily: "var(--mono)", marginBottom: ".4rem" }}>
            {sec.heading}
          </div>
          <p style={{ lineHeight: 1.75 }}>{sec.body}</p>
        </div>
      ))}
    </div>
  );
}

// ── Scripts tab ───────────────────────────────────────────────────────────────

const PROJ_TYPE_COLOR: Record<string, string> = {
  narrative_film:         "var(--node-entity)",
  diagrammatic_structure: "var(--node-event)",
  ambiguity_diffusion:    "var(--node-ambig)",
  rhetorical_voice:       "var(--node-claim)",
  sonic_mapping:          "var(--node-theme)",
  timeline_causality:     "var(--accent)",
  structural_summary:     "var(--muted)",
};

function ScriptsTab({ slug }: { slug: string }) {
  const { data: project }  = useSWR(`project-${slug}`, () => projectsApi.get(slug));
  const [filter, setFilter] = useState<string>("all");

  const { data: taskList } = useSWR(
    project?.latest_version_id ? `tasks-${project.latest_version_id}` : null,
    () => tasksApi.list({ project_id: project!.id, limit: 100 }),
  );

  const projTypes = [...new Set((taskList ?? []).map(t => t.projection_type))];
  const filtered  = filter === "all" ? (taskList ?? []) : (taskList ?? []).filter(t => t.projection_type === filter);

  return (
    <div>
      {/* Filter pills */}
      <div className="flex gap-1" style={{ flexWrap: "wrap", marginBottom: "1rem" }}>
        {["all", ...projTypes].map(pt => (
          <button
            key={pt}
            className={`btn btn-sm${filter === pt ? " btn-primary" : ""}`}
            onClick={() => setFilter(pt)}
          >
            {pt}
          </button>
        ))}
      </div>

      {filtered.length === 0
        ? <div className="empty">No tasks yet.</div>
        : (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px,1fr))", gap: ".8rem" }}>
            {filtered.map(task => <TaskCard key={task.id} task={task} />)}
          </div>
        )
      }
    </div>
  );
}

function TaskCard({ task }: { task: Task }) {
  const color = PROJ_TYPE_COLOR[task.projection_type] ?? "var(--accent)";
  return (
    <Link to={`/tasks/${task.id}`} className="card" style={{ display: "block", borderLeft: `3px solid ${color}` }}>
      <div className="flex" style={{ justifyContent: "space-between", marginBottom: ".4rem" }}>
        <span style={{ fontSize: ".72rem", color: "var(--muted)", fontFamily: "var(--mono)" }}>
          {task.projection_type}
        </span>
        <span className="bounty">{task.current_bounty.toFixed(0)} pts</span>
      </div>
      <div style={{ fontWeight: 600, marginBottom: ".4rem", fontSize: ".9rem" }}>{task.label}</div>
      <div className="flex gap-1" style={{ flexWrap: "wrap" }}>
        <span className={`badge badge-${task.difficulty}`}>{task.difficulty}</span>
        <span className={`badge badge-${task.status}`}>{task.status}</span>
        {task.duration_estimate_s && (
          <span style={{ fontSize: ".72rem", color: "var(--muted)" }}>~{Math.round(task.duration_estimate_s / 60)}min</span>
        )}
      </div>
    </Link>
  );
}

// ── Corpus stats bar ──────────────────────────────────────────────────────────

function StatsBar({ stats }: { stats: Record<string, number> | null | undefined }) {
  if (!stats) return null;
  const fields = [["entities","entities"],["events","events"],["claims","claims"],
                  ["ambiguities","ambiguities"],["themes","themes"],["source_documents","docs"]] as const;
  return (
    <div className="stats-bar">
      {fields.map(([k, label]) => (
        <div key={k} className="stat">{label} <span>{stats[k] ?? 0}</span></div>
      ))}
    </div>
  );
}

// ── ProjectPage ───────────────────────────────────────────────────────────────

export default function ProjectPage() {
  const { slug }  = useParams<{ slug: string }>();
  const [tab, setTab] = useState<Tab>("Overview");

  const { data: project, error } = useSWR(
    slug ? `project-${slug}` : null,
    () => projectsApi.get(slug!),
  );

  if (error)   return <div className="wrapper empty" style={{paddingTop:"3rem"}}>Project not found.</div>;
  if (!project) return <div className="wrapper empty" style={{paddingTop:"3rem"}}>Loading…</div>;

  return (
    <div className="wrapper" style={{ padding: "1.5rem" }}>
      {/* Header */}
      <div className="page-header">
        <div style={{ fontSize: ".8rem", color: "var(--muted)", marginBottom: ".3rem" }}>
          <Link to="/">Home</Link> / {project.project_type}
        </div>
        <h1>{project.title}</h1>
        {project.description && <p>{project.description}</p>}
        <StatsBar stats={project.corpus_stats} />
      </div>

      {/* Tabs */}
      <div className="tabs">
        {TABS.map(t => (
          <div key={t} className={`tab${tab === t ? " active" : ""}`} onClick={() => setTab(t)}>{t}</div>
        ))}
      </div>

      {/* Tab content */}
      {tab === "Overview"      && <OverviewTab slug={slug!} />}
      {tab === "Graph"         && <GraphPanel slug={slug!} versionId={project.latest_version_id ?? ""} />}
      {tab === "Scripts"       && <ScriptsTab  slug={slug!} />}
      {tab === "Submissions"   && <SubmissionsTab projectId={project.id} />}
      {tab === "Assembly"      && <AssemblyTabStub versionId={project.latest_version_id ?? ""} />}
      {tab === "Alternatives"  && <AlternativesTab projectId={project.id} />}
      {tab === "History"       && <HistoryTab slug={slug!} />}
    </div>
  );
}

function SubmissionsTab({ projectId }: { projectId: string }) {
  return <div className="empty">Submissions grid — shows all uploaded media for this project grouped by task.</div>;
}
function AssemblyTabStub({ versionId }: { versionId: string }) {
  return (
    <div className="empty">
      Assembly workspace — drag accepted segments into a timeline, resolve branches, export compiled preview.{" "}
      <Link to={`/assembly/new?version=${versionId}`}>Open workspace →</Link>
    </div>
  );
}
function AlternativesTab({ projectId }: { projectId: string }) {
  return <div className="empty">Alternatives — side-by-side comparison of competing submissions for each task slot.</div>;
}
function HistoryTab({ slug }: { slug: string }) {
  return <div className="empty">History — version log, graph diffs, task regeneration events.</div>;
}
