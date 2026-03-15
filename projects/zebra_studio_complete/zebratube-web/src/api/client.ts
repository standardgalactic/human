const API = "http://localhost:8000"
async function j(url: string, init?: RequestInit){ const r = await fetch(url, init); return r.json() }
export const api = {
  getProjects: () => j(`${API}/projects`),
  getProject: (id: string) => j(`${API}/projects/${id}`),
  getTasks: (projectVersionId?: string) => j(`${API}/tasks` + (projectVersionId ? `?project_version_id=${projectVersionId}` : "")),
  getTask: (id: string) => j(`${API}/tasks/${id}`),
  claimTask: (task_id: string, user_id = "demo-user") => j(`${API}/claims`, {method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({task_id, user_id})}),
  uploadSubmission: async (task_id: string, file: File, user_id = "demo-user") => {
    const form = new FormData(); form.append("task_id", task_id); form.append("user_id", user_id); form.append("file", file)
    const r = await fetch(`${API}/submissions`, {method:"POST", body: form}); return r.json()
  }
}
