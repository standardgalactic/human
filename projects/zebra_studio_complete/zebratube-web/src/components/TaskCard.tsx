import { Link } from "react-router-dom"
export default function TaskCard({ task }: { task: any }){
  return <div className="card"><div className="row"><strong>{task.title}</strong></div><div className="row small">{task.projection} · {task.difficulty || "Standard"}</div><div className="row small">assembly weight: {task.assembly_weight}</div><Link to={`/task/${task.id}`}>Open task</Link></div>
}
