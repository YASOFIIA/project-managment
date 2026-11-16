import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';

const schema = z.object({
  name: z.string().trim().min(1, 'Project name is required').max(255, 'Maximum 255 characters'),
  description: z.string().optional(),
});

export type ProjectFormValues = z.infer<typeof schema>;

interface Props {
  initial?: { name: string; description: string | null };
  submitLabel: string;
  onSubmit: (values: ProjectFormValues) => Promise<void>;
  onCancel?: () => void;
  disabled?: boolean;
}

// Create / edit project form
export function ProjectForm({ initial, submitLabel, onSubmit, onCancel, disabled }: Props) {
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ProjectFormValues>({
    resolver: zodResolver(schema),
    defaultValues: { name: initial?.name ?? '', description: initial?.description ?? '' },
  });

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4" noValidate>
      <Input
        label="Name"
        placeholder="e.g., Website Redesign"
        autoFocus
        disabled={disabled}
        error={errors.name?.message}
        {...register('name')}
      />
      <div>
        <label htmlFor="project-description" className="mb-1.5 block text-[13px] font-medium">
          Description
        </label>
        <textarea
          id="project-description"
          rows={3}
          disabled={disabled}
          placeholder="Brief description of the project (optional)"
          className="w-full resize-none rounded-input border border-black/10 bg-white/80 px-3 py-2 text-sm placeholder:text-ink-soft/70 focus:border-accent focus:bg-white focus:outline-none focus:ring-2 focus:ring-accent/20"
          {...register('description')}
        />
      </div>
      <div className="flex justify-end gap-2">
        {onCancel && (
          <Button variant="secondary" onClick={onCancel}>
            Cancel
          </Button>
        )}
        <Button type="submit" loading={isSubmitting} disabled={disabled}>
          {submitLabel}
        </Button>
      </div>
    </form>
  );
}
