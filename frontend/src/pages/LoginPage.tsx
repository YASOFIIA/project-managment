import { useState } from 'react';
import { Link, Navigate, useNavigate, useSearchParams } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import toast from 'react-hot-toast';
import { Eye, EyeOff } from 'lucide-react';
import { z } from 'zod';
import { AuthShell } from '../components/layout/AuthShell';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { useAuth } from '../hooks/useAuth';
import { getErrorMessage } from '../utils/errors';
import { safeRedirect } from '../utils/redirect';

const schema = z.object({
  login: z.string().trim().min(1, 'Please enter your username'),
  password: z.string().min(1, 'Please enter your password'),
});
type Values = z.infer<typeof schema>;

export default function LoginPage() {
  const { login, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const redirect = safeRedirect(params.get('redirect'));
  const [show, setShow] = useState(false);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<Values>({ resolver: zodResolver(schema) });

  if (isAuthenticated) return <Navigate to={redirect} replace />;

  const submit = handleSubmit(async (values) => {
    try {
      await login(values.login, values.password);
      navigate(redirect, { replace: true });
    } catch (error) {
      toast.error(getErrorMessage(error));
    }
  });

  return (
    <AuthShell title="Welcome back" subtitle="Sign in to manage your projects">
      <form onSubmit={submit} className="flex flex-col gap-4" noValidate>
        <Input
          label="Username"
          autoComplete="username"
          spellCheck={false}
          autoCorrect="off"
          autoCapitalize="none"
          autoFocus
          error={errors.login?.message}
          {...register('login')}
        />
        <Input
          label="Password"
          type={show ? 'text' : 'password'}
          autoComplete="current-password"
          error={errors.password?.message}
          trailing={
            <button
              type="button"
              onClick={() => setShow((v) => !v)}
              aria-label={show ? 'Hide password' : 'Show password'}
              title={show ? 'Hide password' : 'Show password'}
              className="rounded p-1 text-ink-soft hover:text-ink"
            >
              {show ? <EyeOff size={18} strokeWidth={1.5} /> : <Eye size={18} strokeWidth={1.5} />}
            </button>
          }
          {...register('password')}
        />
        <div className="-mt-1 text-right">
          <button
            type="button"
            onClick={() => toast('Password recovery is not implemented yet')}
            className="text-xs text-ink-soft hover:text-accent"
          >
            Forgot password?
          </button>
        </div>
        <Button type="submit" fullWidth loading={isSubmitting}>
          Sign In
        </Button>
      </form>
      <p className="mt-6 text-center text-sm text-ink-soft">
        Don&apos;t have an account?{' '}
        <Link
          to={`/register${params.get('redirect') ? `?redirect=${encodeURIComponent(redirect)}` : ''}`}
          className="font-medium text-accent hover:text-accent-hover"
        >
          Sign Up
        </Link>
      </p>
    </AuthShell>
  );
}
