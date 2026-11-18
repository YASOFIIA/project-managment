import axios from 'axios';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import toast from 'react-hot-toast';
import { z } from 'zod';
import { inviteByLogin } from '../../api/projects';
import { getErrorMessage } from '../../utils/errors';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';

const schema = z.object({ login: z.string().trim().min(1, 'Please enter a username') });

// Directly invite a registered user by login
export function InviteForm({ projectId, onDone }: { projectId: number; onDone?: () => void }) {
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<z.infer<typeof schema>>({ resolver: zodResolver(schema) });

  const submit = handleSubmit(async ({ login }) => {
    try {
      await inviteByLogin(projectId, login);
      toast.success('User added as participant');
      reset();
      onDone?.();
    } catch (error) {
      if (axios.isAxiosError(error)) {
        if (error.response?.status === 404) {
          toast.error('User not found');
          return;
        }
        if (error.response?.status === 409) {
          toast.error('User is already a member of this project');
          return;
        }
      }
      toast.error(getErrorMessage(error));
    }
  });

  return (
    <form onSubmit={submit} className="flex items-start gap-2" noValidate>
      <Input
        className="flex-1"
        type="text"
        placeholder="username"
        aria-label="Username to invite"
        autoComplete="off"
        spellCheck={false}
        error={errors.login?.message}
        {...register('login')}
      />
      <Button type="submit" loading={isSubmitting}>
        Invite
      </Button>
    </form>
  );
}

