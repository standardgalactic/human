import { BrowserRouter, Routes, Route } from "react-router-dom"
import HomePage from "./pages/HomePage"
import ProjectPage from "./pages/ProjectPage"
import TaskPage from "./pages/TaskPage"
import ProfilePage from "./pages/ProfilePage"
import AssemblyPage from "./pages/AssemblyPage"

export default function App(){
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/project/:id" element={<ProjectPage />} />
        <Route path="/task/:id" element={<TaskPage />} />
        <Route path="/user/:id" element={<ProfilePage />} />
        <Route path="/assembly/:id" element={<AssemblyPage />} />
      </Routes>
    </BrowserRouter>
  )
}
