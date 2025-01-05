import { useProject } from '@/hooks';
import { ScrollArea } from '@radix-ui/react-scroll-area';
import { GenericOption } from '../flow/option/option';

export const ProjectConfig = ({ projectId }: { projectId: number }) => {
  const { project, updateProject } = useProject(projectId);
  const handleChange = (name: string, value: any) => {
    updateProject({ [name]: value }).catch(console.error);
  };
  console.log('ProjectConfig', project);
  return (
    <ScrollArea className="h-full p-2">
      <div className="flex flex-col gap-4">
        <GenericOption
          nodeId={projectId.toString()}
          type="text"
          name="name"
          label="Name"
          data={{ name: project?.name }}
          onValueChange={handleChange}
        />
        <GenericOption
          nodeId={projectId.toString()}
          type="text"
          rows={5}
          name="description"
          label="Description"
          data={{ description: project?.description }}
          onValueChange={handleChange}
        />
      </div>
    </ScrollArea>
  );
};
