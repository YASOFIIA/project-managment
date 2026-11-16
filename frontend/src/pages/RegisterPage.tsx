import { Link, Navigate, useNavigate, useSearchParams } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import toast from 'react-hot-toast';
import { z } from 'zod';
import { AuthShell } from '../components/layout/AuthShell';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { useAuth } from '../hooks/useAuth';
import { getErrorMessage } from '../utils/errors';
import { safeRedirect } from '../utils/redirect';

const schema = z
  .object({
    login: z.string().trim().min(3, 'Мінімум 3 символи').max(64, 'Максимум 64 символи'),
    password: z.string().min(6, 'Мінімум 6 символів'),
    confirm: z.string(),
  })
  .refine((v) => v.password === v.confirm, { path: ['confirm'], message: 'Паролі не збігаються' });
type Values = z.infer<typeof schema>;

export default function RegisterPage() {
  const { register: signUp, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const redirect = safeRedirect(params.get('redirect'));
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<Values>({ resolver: zodResolver(schema) });

  if (isAuthenticated) return <Navigate to={redirect} replace />;

  const submit = handleSubmit(async (values) => {
    try {
      await signUp(values.login, values.password);
      toast.success('Акаунт створено');
      navigate(redirect, { replace: true });
    } catch (error) {
      toast.error(getErrorMessage(error));
    }
  });

  return (
    <AuthShell title="Створити акаунт" subtitle="Це займе менше хвилини">
      <form onSubmit={submit} className="flex flex-col gap-4" noValidate>
        <Input label="Логін" autoComplete="username" autoFocus error={errors.login?.message} {...register('login')} />
        <Input label="Пароль" type="password" autoComplete="new-password" error={errors.password?.message} {...register('password')} />
        <Input label="Підтвердити пароль" type="password" autoComplete="new-password" error={errors.confirm?.message} {...register('confirm')} />
        <Button type="submit" fullWidth loading={isSubmitting}>
          Зареєструватися
        </Button>
      </form>
      <p className="mt-6 text-center text-sm text-ink-soft">
        Вже є акаунт?{' '}
        <Link
          to={`/login${params.get('redirect') ? `?redirect=${encodeURIComponent(redirect)}` : ''}`}
          className="font-medium text-accent hover:text-accent-hover"
        >
          Увійти
        </Link>
      </p>
    </AuthShell>
  );
}
