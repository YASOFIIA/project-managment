import toast from 'react-hot-toast';
import { createProject, updateProject } from '../../api/projects';
import { useProjects } from '../../hooks/useProjects';
import type { Project } from '../../types';
import { getErrorMessage } from '../../utils/errors';
import { Modal } from '../ui/Modal';
import { ProjectForm, type ProjectFormValues } from './ProjectForm';

interface Props {
  open: boolean;
  project?: Project | null; // when set -> edit mode
  onClose: () => void;
  onSaved?: (project: Project) => void;
}

export function ProjectFormModal({ open, project, onClose, onSaved }: Props) {
  const { reload } = useProjects();

  const submit = async (values: ProjectFormValues) => {
    const payload = { name: values.name.trim(), description: values.description?.trim() || null };
    try {
      const saved = project ? await updateProject(project.id, payload) : await createProject(payload);
      toast.success(project ? 'Проєкт оновлено' : 'Проєкт створено');
      await reload();
      onSaved?.(saved);
      onClose();
    } catch (error) {
      toast.error(getErrorMessage(error));
    }
  };

  return (
    <Modal open={open} onClose={onClose} title={project ? 'Редагувати проєкт' : 'Новий проєкт'}>
      <ProjectForm
        initial={project ?? undefined}
        submitLabel={project ? 'Зберегти' : 'Створити'}
        onSubmit={submit}
        onCancel={onClose}
      />
    </Modal>
  );
}
