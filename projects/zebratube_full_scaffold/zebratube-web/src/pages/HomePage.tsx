import { useEffect, useState } from "react"
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
      <div className="strips">
        <div className="card"><h3>New projects</h3><p>Add project creation or ingestion status here.</p></div>
        <div className="card"><h3>Assembly ready</h3><p>Show projects with enough accepted segments.</p></div>
        <div className="card"><h3>Bottlenecks</h3><p>Show high-bounty, zero-submission tasks.</p></div>
      </div>
    </div>
  )
}
