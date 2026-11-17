import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import toast from 'react-hot-toast';
import { z } from 'zod';
import { shareByEmail } from '../../api/projects';
import { getErrorMessage } from '../../utils/errors';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';

const schema = z.object({ email: z.string().trim().email('Please enter a valid email address') });

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
      if (res.email_sent) {
        toast.success('Invitation sent to email');
      } else {
        toast.success("Invitation sent to user's account");
      }
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
        aria-label="Recipient email"
        autoComplete="off"
        spellCheck={false}
        error={errors.email?.message}
        {...register('email')}
      />
      <Button type="submit" loading={isSubmitting}>
        Send
      </Button>
    </form>
  );
}
