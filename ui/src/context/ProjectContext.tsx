'use client';
import { createContext, PropsWithChildren, useContext } from 'react';

const ProjectContext = createContext<{ projectId: string }>({ projectId: '' });

export const ProjectProvider = ({
  projectId,
  children,
}: PropsWithChildren<{ projectId: string }>) => {
  return (
    <ProjectContext.Provider value={{ projectId }}>
      {children}
    </ProjectContext.Provider>
  );
};

export const useProjectId = () => {
  const context = useContext(ProjectContext);
  if (!context) {
    throw new Error('useProjectId must be used within a ProjectProvider');
  }
  return context;
};
