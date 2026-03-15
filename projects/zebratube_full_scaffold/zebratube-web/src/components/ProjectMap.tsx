import { useEffect, useRef } from "react"
import * as d3 from "d3"

export default function ProjectMap({ projects }: { projects: any[] }){
  const ref = useRef<SVGSVGElement | null>(null)
  useEffect(() => {
    if (!ref.current) return
    const svg = d3.select(ref.current)
    svg.selectAll("*").remove()
    const sim = d3.forceSimulation(projects as any)
      .force("charge", d3.forceManyBody().strength(-120))
      .force("center", d3.forceCenter(420, 260))
      .force("collision", d3.forceCollide(30))
    const g = svg.append("g")
    const nodes = g.selectAll("circle").data(projects).enter().append("circle")
      .attr("r", d => 10 + ((d.open_tasks || 1) * 2))
      .attr("fill", "#111")
      .attr("stroke", "#6f6")
    const labels = g.selectAll("text").data(projects).enter().append("text")
      .text(d => d.title)
      .attr("font-size", "10px")
      .attr("fill", "#9f9")
    sim.on("tick", () => {
      nodes.attr("cx", (d:any) => d.x).attr("cy", (d:any) => d.y)
      labels.attr("x", (d:any) => d.x + 14).attr("y", (d:any) => d.y + 4)
    })
    return () => { sim.stop() }
  }, [projects])
  return <svg ref={ref} width={840} height={520} />
}
