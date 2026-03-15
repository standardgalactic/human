
const API = "http://localhost:8000"

export async function getProjects(){
 const r = await fetch(`${API}/projects`)
 return r.json()
}
