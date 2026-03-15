import { useEffect, useState } from "react"
import { useParams } from "react-router-dom"
import { api } from "../api/client"
export default function TaskPage(){
  const { id } = useParams(); const [task, setTask] = useState<any>(null); const [msg, setMsg] = useState("")
  useEffect(() => { if (id) api.getTask(id).then(setTask) }, [id])
  async function onClaim(){ if (!id) return; const x = await api.claimTask(id); setMsg(`Claimed: ${x.id}`) }
  async function onUpload(ev: React.ChangeEvent<HTMLInputElement>){ const f = ev.target.files?.[0]; if (!f || !id) return; const x = await api.uploadSubmission(id, f); setMsg(`Uploaded submission: ${x.id}`) }
  return <div className="page"><h1>{task?.title || "Task"}</h1><div className="task-grid"><div className="card"><h3>Brief</h3><p>Projection: {task?.projection}</p><p>Difficulty: {task?.difficulty}</p><p>Assembly weight: {task?.assembly_weight}</p></div><div className="card"><h3>Status</h3><button onClick={onClaim}>Claim task</button><div className="row"><input type="file" onChange={onUpload} /></div>{msg && <p className="muted">{msg}</p>}</div></div></div>
}
