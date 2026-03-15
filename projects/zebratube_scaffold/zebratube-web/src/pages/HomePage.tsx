
import { useEffect, useState } from "react"
import { getProjects } from "../api/client"

export default function HomePage(){
 const [projects,setProjects] = useState([])

 useEffect(()=>{
  getProjects().then(setProjects)
 },[])

 return (
  <div>
   <h1>ZebraTube</h1>
   {projects.map(p => <div key={p.id}>{p.title}</div>)}
  </div>
 )
}
