import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type ToolParameter = {
  id: string;
  name: string;
  description: string;
  type: 'str' | 'int' | 'bool' | 'float';
};

export type Tool = {
  id: string;
  name: string;
  description: string;
  async?: boolean;
  parameters: ToolParameter[];
  code?: string;
  assigned?: [{ agent: string; scene: 'execution' | 'llm' }];
};

export interface Project {
  id: string;
  name: string;
  description?: string;
  flow: any; // Complicated JSON object
  tools?: Tool[];
  knowledge?: any;
  settings?: any;
  created?: string;
  updated?: string;
}

interface ProjectState {
  projects: Project[];
  chatPanePinned: boolean;
  nodePanePinned: boolean;
  setProjects: (projects: Project[]) => void;
  updateProject: (id: string, project: Partial<Project>) => void;
  deleteProject: (id: string) => void;
  getProjectById: (id: string) => Project | undefined;
  pinChatPane: (pin: boolean) => void;
  pinNodePane: (pin: boolean) => void;
}

const useProjectStore = create<ProjectState>()(
  persist(
    (set, get) => ({
      projects: [],
      chatPanePinned: false,
      nodePanePinned: false,
      setProjects: projects => set({ projects }),
      updateProject: (id, newProject) =>
        set(state => {
          const projects = state.projects.map(project => {
            if (project.id === id) {
              // Merge the existing Project with the new Project data, allowing for partial updates
              return { ...project, ...newProject };
            }
            return project;
          });
          return { projects };
        }),
      deleteProject: id =>
        set(state => ({
          projects: state.projects.filter(project => project.id !== id),
        })),
      getProjectById: id => get().projects.find(project => project.id === id),
      pinChatPane: (pin: boolean) => set({ chatPanePinned: pin }),
      pinNodePane: (pin: boolean) => set({ nodePanePinned: pin }),
    }),
    {
      name: 'agentok-projects',
    }
  )
);

export default useProjectStore;
