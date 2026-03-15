import { useEffect, useState } from "react"
import { useParams } from "react-router-dom"
import { api } from "../api/client"
import TaskCard from "../components/TaskCard"
import TabBar from "../components/TabBar"
import GraphView from "../components/GraphView"
import SubmissionCompare from "../components/SubmissionCompare"
import AssemblyTimeline from "../components/AssemblyTimeline"

export default function ProjectPage(){
  const { id } = useParams()
  const [project, setProject] = useState<any>(null)
  const [tasks, setTasks] = useState<any[]>([])
  const [tab, setTab] = useState("Overview")
  useEffect(() => {
    if (!id) return
    api.getProject(id).then(setProject).catch(()=>setProject(null))
    api.getTasks().then((rows:any[]) => setTasks(rows)).catch(()=>setTasks([]))
  }, [id])
  return (
    <div className="page">
      <h1>{project?.title || "Project"}</h1>
      <TabBar tabs={["Overview","Graph","Scripts","Submissions","Assembly","Alternatives","History"]} active={tab} setActive={setTab} />
      {tab === "Overview" && <div className="card">Zebrapedia article and project stats go here.</div>}
      {tab === "Graph" && <GraphView />}
      {tab === "Scripts" && <div>{tasks.map(t => <TaskCard key={t.id} task={t} />)}</div>}
      {tab === "Submissions" && <div className="card">Submission grid placeholder.</div>}
      {tab === "Assembly" && <AssemblyTimeline />}
      {tab === "Alternatives" && <SubmissionCompare />}
      {tab === "History" && <div className="card">Version and diff history placeholder.</div>}
    </div>
  )
}
