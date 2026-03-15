
export async function getTasks(){
  const r = await fetch("http://localhost:8000/tasks")
  return r.json()
}
