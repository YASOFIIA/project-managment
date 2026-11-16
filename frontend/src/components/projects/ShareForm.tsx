import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import toast from 'react-hot-toast';
import { z } from 'zod';
import { shareByEmail } from '../../api/projects';
import { getErrorMessage } from '../../utils/errors';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';

const schema = z.object({ email: z.string().trim().email('Некоректний email') });

// Send an email invitation with a join link
export function ShareForm({ projectId, onDone }: { projectId: number; onDone?: () => void }) {
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<z.infer<typeof schema>>({ resolver: zodResolver(schema) });

  const submit = handleSubmit(async ({ email }) => {
    try {
      const res = await shareByEmail(projectId, email);
      toast.success(`Запрошення надіслано на ${res.email} (діє ${res.expires_in_hours} год)`);
      reset();
      onDone?.();
    } catch (error) {
      toast.error(getErrorMessage(error));
    }
  });

  return (
    <form onSubmit={submit} className="flex items-start gap-2" noValidate>
      <Input
        className="flex-1"
        type="email"
        placeholder="name@example.com"
        aria-label="Email отримувача"
        autoComplete="off"
        error={errors.email?.message}
        {...register('email')}
      />
      <Button type="submit" loading={isSubmitting}>
        Надіслати
      </Button>
    </form>
  );
}
