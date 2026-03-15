import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { api } from "../api/client"
import ProjectMap from "../components/ProjectMap"

export default function HomePage(){
  const [projects, setProjects] = useState<any[]>([])
  useEffect(() => { api.getProjects().then(setProjects).catch(()=>setProjects([])) }, [])
  return (
    <div className="page">
      <h1>ZebraTube</h1>
      <p className="muted">A living map of texts being turned into films.</p>
      <ProjectMap projects={projects} />
      <div className="card">
        <h3>Projects</h3>
        {projects.length === 0 && <p className="muted">No projects yet. Import one through the API helper script.</p>}
        {projects.map(p => (
          <div key={p.id} className="row">
            <Link to={`/project/${p.id}`}>{p.title}</Link>
            <span className="small"> · open tasks: {p.open_tasks ?? 0}</span>
          </div>
        ))}
      </div>
      <div className="strips">
        <div className="card"><h3>New projects</h3><p>Use this strip for newly imported corpora.</p></div>
        <div className="card"><h3>Assembly ready</h3><p>Show projects with enough accepted segments.</p></div>
        <div className="card"><h3>Bottlenecks</h3><p>Show high-bounty, zero-submission tasks.</p></div>
      </div>
    </div>
  )
}
