// src/stores/index.ts — global state stores

import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { User, Task, Project } from "../lib/api";

// ── Auth store ────────────────────────────────────────────────────────────────

interface AuthState {
  token:   string | null;
  user:    User   | null;
  setAuth: (token: string, user: User) => void;
  logout:  () => void;
}

export const useAuth = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user:  null,
      setAuth: (token, user) => {
        localStorage.setItem("zt_token", token);
        set({ token, user });
      },
      logout: () => {
        localStorage.removeItem("zt_token");
        set({ token: null, user: null });
      },
    }),
    { name: "zt-auth" }
  )
);

// ── Task market store ─────────────────────────────────────────────────────────

interface TaskMarketState {
  tasks:       Task[];
  bottlenecks: Task[];
  filters: {
    projection_type?: string;
    difficulty?:      string;
    status:           string;
    sort_by:          string;
  };
  setTasks:       (tasks: Task[]) => void;
  setBottlenecks: (tasks: Task[]) => void;
  setFilter:      (key: string, value: string | undefined) => void;
}

export const useTaskMarket = create<TaskMarketState>((set) => ({
  tasks:       [],
  bottlenecks: [],
  filters:     { status: "open", sort_by: "bounty" },
  setTasks:       (tasks)       => set({ tasks }),
  setBottlenecks: (bottlenecks) => set({ bottlenecks }),
  setFilter: (key, value) =>
    set((s) => ({ filters: { ...s.filters, [key]: value } })),
}));

// ── Project store ─────────────────────────────────────────────────────────────

interface ProjectState {
  projects:       Project[];
  activeProject:  Project | null;
  setProjects:    (projects: Project[]) => void;
  setActive:      (project: Project | null) => void;
}

export const useProjects = create<ProjectState>((set) => ({
  projects:      [],
  activeProject: null,
  setProjects:   (projects) => set({ projects }),
  setActive:     (activeProject) => set({ activeProject }),
}));
