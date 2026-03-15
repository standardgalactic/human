// src/pages/HomePage.tsx

import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import useSWR from "swr";
import * as d3 from "d3";
import { projects as projectsApi, tasks as tasksApi } from "../lib/api";
import type { Project, Task } from "../lib/api";

// ── Project map (D3 force) ────────────────────────────────────────────────────

interface MapNode extends d3.SimulationNodeDatum {
  id:      string;
  slug:    string;
  title:   string;
  pct:     number;    // completion percentage
  tasks:   number;
  bounty:  number;
}

function ProjectMap({ nodes }: { nodes: MapNode[] }) {
  const ref = useRef<SVGSVGElement>(null);

  useEffect(() => {
    if (!ref.current || nodes.length === 0) return;
    const el = ref.current;
    const W = el.clientWidth || 900;
    const H = el.clientHeight || 480;

    d3.select(el).selectAll("*").remove();
    const svg = d3.select(el);

    const sim = d3.forceSimulation(nodes)
      .force("charge", d3.forceManyBody().strength(-120))
      .force("center",  d3.forceCenter(W / 2, H / 2))
      .force("collide",  d3.forceCollide<MapNode>(d => Math.sqrt(d.tasks) * 8 + 30));

    const colorScale = d3.scaleSequential(d3.interpolatePlasma).domain([0, 1]);

    const node = svg.append("g")
      .selectAll("g")
      .data(nodes)
      .enter().append("g")
      .style("cursor", "pointer")
      .on("click", (_, d) => { window.location.href = `/projects/${d.slug}`; });

    node.append("circle")
      .attr("r", d => Math.sqrt(d.tasks) * 6 + 18)
      .attr("fill", d => colorScale(d.pct))
      .attr("fill-opacity", .75)
      .attr("stroke", "var(--border)")
      .attr("stroke-width", 1.5);

    node.append("text")
      .text(d => d.title.slice(0, 22))
      .attr("text-anchor", "middle")
      .attr("dy", "0.35em")
      .attr("fill", "#fff")
      .attr("font-size", "11px")
      .style("pointer-events", "none");

    sim.on("tick", () => {
      node.attr("transform", d => `translate(${d.x ?? W/2},${d.y ?? H/2})`);
    });

    return () => { sim.stop(); };
  }, [nodes]);

  return (
    <svg
      ref={ref}
      style={{ width: "100%", height: 480, background: "var(--surface)", borderRadius: 8, border: "1px solid var(--border)" }}
    />
  );
}

// ── Task strip ────────────────────────────────────────────────────────────────

function TaskStrip({ title, tasks, color }: { title: string; tasks: Task[]; color: string }) {
  if (tasks.length === 0) return null;
  return (
    <section style={{ marginBottom: "2rem" }}>
      <h3 style={{ fontSize: ".8rem", textTransform: "uppercase", letterSpacing: ".1em", color, marginBottom: ".75rem" }}>
        {title}
      </h3>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px,1fr))", gap: ".75rem" }}>
        {tasks.slice(0, 6).map(t => (
          <Link key={t.id} to={`/tasks/${t.id}`} className="card" style={{ display: "block" }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: ".4rem" }}>
              <span style={{ fontSize: ".75rem", color: "var(--muted)", fontFamily: "var(--mono)" }}>
                {t.projection_type}
              </span>
              <span className="bounty">{t.current_bounty.toFixed(0)} pts</span>
            </div>
            <div style={{ fontWeight: 600, fontSize: ".9rem", marginBottom: ".3rem" }}>{t.label}</div>
            <div style={{ display: "flex", gap: ".5rem" }}>
              <span className={`badge badge-${t.difficulty}`}>{t.difficulty}</span>
              <span style={{ fontSize: ".75rem", color: "var(--muted)" }}>
                {t.submission_count} submissions
              </span>
            </div>
          </Link>
        ))}
      </div>
    </section>
  );
}

// ── HomePage ──────────────────────────────────────────────────────────────────

export default function HomePage() {
  const { data: projectList } = useSWR("projects", () => projectsApi.list({ limit: 30 }));
  const { data: bottlenecks } = useSWR("bottlenecks", () => tasksApi.bottlenecks(6));
  const { data: newTasks }    = useSWR("tasks-open", () => tasksApi.list({ status: "open", sort_by: "created", limit: 6 }));
  const { data: readyTasks }  = useSWR("tasks-assembly", () => tasksApi.list({ status: "accepted", sort_by: "weight", limit: 6 }));

  const mapNodes: MapNode[] = (projectList ?? []).map(p => ({
    id:    p.id,
    slug:  p.slug,
    title: p.title,
    pct:   0,  // TODO: derive from task completion ratio
    tasks: p.corpus_stats?.entities ?? 10,
    bounty: 0,
  }));

  return (
    <div className="wrapper" style={{ padding: "1.5rem 1.5rem" }}>

      {/* Hero */}
      <div style={{ marginBottom: "1.5rem" }}>
        <h1 style={{ fontSize: "1.5rem", color: "var(--accent2)", marginBottom: ".4rem" }}>
          Living project map
        </h1>
        <p style={{ color: "var(--muted)", fontSize: ".9rem", maxWidth: 600 }}>
          Texts and repositories being turned into films. Each node is a project.
          Size reflects open task count. Colour reflects completion.
        </p>
      </div>

      {/* D3 map */}
      {mapNodes.length > 0
        ? <ProjectMap nodes={mapNodes} />
        : <div className="empty" style={{ height: 480, display: "flex", alignItems: "center", justifyContent: "center" }}>
            No projects yet. Run <code style={{ margin: "0 .3rem", fontFamily: "var(--mono)" }}>zebra crawl</code> to add one.
          </div>
      }

      {/* Status strips */}
      <div style={{ marginTop: "2.5rem" }}>
        <TaskStrip title="⚠  Bottlenecks — high bounty, zero submissions" tasks={bottlenecks ?? []} color="var(--red)" />
        <TaskStrip title="✦  New projects — first tasks open"               tasks={newTasks ?? []}    color="var(--accent)" />
        <TaskStrip title="✓  Assembly ready — accepted segments waiting"    tasks={readyTasks ?? []}  color="var(--green)" />
      </div>

    </div>
  );
}
