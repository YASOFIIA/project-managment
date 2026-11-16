import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import toast from 'react-hot-toast';
import { z } from 'zod';
import { inviteByLogin } from '../../api/projects';
import { getErrorMessage } from '../../utils/errors';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';

const schema = z.object({ login: z.string().trim().min(1, 'Вкажіть логін') });

// Invite an existing user by login
export function InviteForm({ projectId, onDone }: { projectId: number; onDone: () => void }) {
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<z.infer<typeof schema>>({ resolver: zodResolver(schema) });

  const submit = handleSubmit(async ({ login }) => {
    try {
      await inviteByLogin(projectId, login);
      toast.success(`Користувача ${login} додано до проєкту`);
      reset();
      onDone();
    } catch (error) {
      toast.error(getErrorMessage(error));
    }
  });

  return (
    <form onSubmit={submit} className="flex items-start gap-2" noValidate>
      <Input
        className="flex-1"
        placeholder="Логін користувача"
        aria-label="Логін користувача"
        autoComplete="off"
        error={errors.login?.message}
        {...register('login')}
      />
      <Button type="submit" loading={isSubmitting}>
        Запросити
      </Button>
    </form>
  );
}
