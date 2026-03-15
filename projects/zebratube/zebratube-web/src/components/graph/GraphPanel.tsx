// src/components/graph/GraphPanel.tsx

import { useEffect, useRef } from "react";
import useSWR from "swr";
import * as d3 from "d3";
import { projects as projectsApi } from "../../lib/api";

interface GraphNode extends d3.SimulationNodeDatum {
  id:    string;
  label: string;
  type:  string;
}
interface GraphLink extends d3.SimulationLinkDatum<GraphNode> {
  label: string;
}

const TYPE_COLOR: Record<string, string> = {
  entity:         "#4A90D9",
  event:          "#E8A838",
  claim:          "#7BC67E",
  ambiguity:      "#E05C5C",
  theme:          "#B07BE8",
  transformation: "#88BBFF",
};

export default function GraphPanel({ slug, versionId }: { slug: string; versionId: string }) {
  const svgRef = useRef<SVGSVGElement>(null);
  const { data: graph } = useSWR(
    versionId ? `graph-${slug}-${versionId}` : null,
    () => projectsApi.graph(slug, versionId),
  );

  useEffect(() => {
    if (!svgRef.current || !graph) return;
    const el = svgRef.current;
    const W = el.clientWidth  || 900;
    const H = el.clientHeight || 560;

    d3.select(el).selectAll("*").remove();

    const rawNodes = [
      ...((graph.entities as any[]) ?? []).map((n: any) => ({ id: n.id, label: n.name?.slice(0,28) ?? n.id, type: "entity" })),
      ...((graph.events as any[])   ?? []).map((n: any) => ({ id: n.id, label: n.label?.slice(0,28) ?? n.id, type: "event" })),
      ...((graph.claims as any[])   ?? []).slice(0, 40).map((n: any) => ({ id: n.id, label: n.text?.slice(0,28) ?? n.id, type: "claim" })),
      ...((graph.ambiguities as any[]) ?? []).map((n: any) => ({ id: n.id, label: n.label?.slice(0,28) ?? n.id, type: "ambiguity" })),
    ].slice(0, 200) as GraphNode[];

    const nodeIds = new Set(rawNodes.map(n => n.id));
    const rawLinks = ((graph.relations as any[]) ?? [])
      .filter((r: any) => nodeIds.has(r.source) && nodeIds.has(r.target))
      .slice(0, 300)
      .map((r: any) => ({ source: r.source, target: r.target, label: r.relation ?? r.type ?? "" })) as GraphLink[];

    const svg  = d3.select(el);
    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([.2, 4])
      .on("zoom", e => g.attr("transform", e.transform));
    svg.call(zoom);

    const g = svg.append("g");

    // Arrow marker
    svg.append("defs").append("marker")
      .attr("id", "arrow")
      .attr("viewBox", "0 -4 8 8")
      .attr("refX", 14).attr("refY", 0)
      .attr("markerWidth", 6).attr("markerHeight", 6)
      .attr("orient", "auto")
      .append("path").attr("d", "M0,-4L8,0L0,4").attr("fill", "#334466");

    const sim = d3.forceSimulation<GraphNode>(rawNodes)
      .force("link",   d3.forceLink<GraphNode,GraphLink>(rawLinks).id(d => d.id).distance(80))
      .force("charge", d3.forceManyBody().strength(-80))
      .force("center", d3.forceCenter(W / 2, H / 2))
      .force("collide", d3.forceCollide(20));

    const link = g.append("g").selectAll("line")
      .data(rawLinks).enter().append("line")
      .attr("stroke", "#223")
      .attr("stroke-width", 1.2)
      .attr("marker-end", "url(#arrow)");

    const node = g.append("g").selectAll<SVGCircleElement, GraphNode>("circle")
      .data(rawNodes).enter().append("circle")
      .attr("r", 7)
      .attr("fill", d => TYPE_COLOR[d.type] ?? "#888")
      .attr("fill-opacity", .85)
      .attr("stroke", "#0a0a14").attr("stroke-width", 1.5)
      .call(
        d3.drag<SVGCircleElement, GraphNode>()
          .on("start", (e, d) => { if (!e.active) sim.alphaTarget(.3).restart(); d.fx = d.x; d.fy = d.y; })
          .on("drag",  (e, d) => { d.fx = e.x; d.fy = e.y; })
          .on("end",   (e, d) => { if (!e.active) sim.alphaTarget(0); d.fx = null; d.fy = null; })
      );

    node.append("title").text(d => `[${d.type}] ${d.label}`);

    const label = g.append("g").selectAll("text")
      .data(rawNodes).enter().append("text")
      .text(d => d.label)
      .attr("font-size", "8px")
      .attr("fill", "#9090c0")
      .attr("dy", "-.6em")
      .attr("text-anchor", "middle")
      .style("pointer-events", "none");

    sim.on("tick", () => {
      link
        .attr("x1", (d: any) => d.source.x).attr("y1", (d: any) => d.source.y)
        .attr("x2", (d: any) => d.target.x).attr("y2", (d: any) => d.target.y);
      node.attr("cx", d => d.x ?? 0).attr("cy", d => d.y ?? 0);
      label.attr("x", d => d.x ?? 0).attr("y", d => d.y ?? 0);
    });

    return () => sim.stop();
  }, [graph, slug, versionId]);

  // Legend
  const legendItems = Object.entries(TYPE_COLOR);

  return (
    <div>
      <div className="flex gap-2" style={{ marginBottom: ".75rem", flexWrap: "wrap" }}>
        {legendItems.map(([type, color]) => (
          <div key={type} className="flex gap-1" style={{ alignItems: "center", fontSize: ".75rem", color: "var(--muted)" }}>
            <div style={{ width: 10, height: 10, borderRadius: "50%", background: color }} />
            {type}
          </div>
        ))}
        <span style={{ fontSize: ".75rem", color: "var(--muted)", marginLeft: "auto" }}>
          Drag to explore · Scroll to zoom
        </span>
      </div>
      <svg
        ref={svgRef}
        style={{
          width: "100%",
          height: 560,
          background: "var(--surface)",
          borderRadius: 8,
          border: "1px solid var(--border)",
        }}
      />
      {!graph && <div className="empty">Loading graph…</div>}
    </div>
  );
}
