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

const registerSchema = z
  .object({
    login: z
      .string()
      .trim()
      .min(3, 'Username must be at least 3 characters')
      .max(64, 'Maximum 64 characters'),
    email: z.string().trim().email('Please enter a valid email address'),
    password: z.string().min(6, 'Password must be at least 6 characters'),
    repeat_password: z.string().min(6, 'Please confirm your password'),
  })
  .refine((data) => data.password === data.repeat_password, {
    message: 'Passwords do not match',
    path: ['repeat_password'],
  });
type Values = z.infer<typeof registerSchema>;

export default function RegisterPage() {
  const { register: signUp, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const redirect = safeRedirect(params.get('redirect'));
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<Values>({ resolver: zodResolver(registerSchema) });

  if (isAuthenticated) return <Navigate to={redirect} replace />;

  const submit = handleSubmit(async (values) => {
    try {
      await signUp(values.login, values.email, values.password);
      toast.success('Account created');
      navigate(redirect, { replace: true });
    } catch (error) {
      toast.error(getErrorMessage(error));
    }
  });

  return (
    <AuthShell title="Create Account" subtitle="It takes less than a minute">
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
          label="Email"
          type="email"
          placeholder="name@example.com"
          autoComplete="email"
          spellCheck={false}
          error={errors.email?.message}
          {...register('email')}
        />
        <Input
          label="Password"
          type={showPassword ? 'text' : 'password'}
          autoComplete="new-password"
          error={errors.password?.message}
          trailing={
            <button
              type="button"
              onClick={() => setShowPassword((v) => !v)}
              aria-label={showPassword ? 'Hide password' : 'Show password'}
              title={showPassword ? 'Hide password' : 'Show password'}
              className="rounded p-1 text-ink-soft hover:text-ink"
            >
              {showPassword ? (
                <EyeOff size={18} strokeWidth={1.5} />
              ) : (
                <Eye size={18} strokeWidth={1.5} />
              )}
            </button>
          }
          {...register('password')}
        />
        <Input
          label="Confirm Password"
          type={showConfirm ? 'text' : 'password'}
          autoComplete="new-password"
          error={errors.repeat_password?.message}
          trailing={
            <button
              type="button"
              onClick={() => setShowConfirm((v) => !v)}
              aria-label={showConfirm ? 'Hide password' : 'Show password'}
              title={showConfirm ? 'Hide password' : 'Show password'}
              className="rounded p-1 text-ink-soft hover:text-ink"
            >
              {showConfirm ? (
                <EyeOff size={18} strokeWidth={1.5} />
              ) : (
                <Eye size={18} strokeWidth={1.5} />
              )}
            </button>
          }
          {...register('repeat_password')}
        />
        <Button type="submit" fullWidth loading={isSubmitting}>
          Sign Up
        </Button>
      </form>
      <p className="mt-6 text-center text-sm text-ink-soft">
        Already have an account?{' '}
        <Link
          to={`/login${params.get('redirect') ? `?redirect=${encodeURIComponent(redirect)}` : ''}`}
          className="font-medium text-accent hover:text-accent-hover"
        >
          Sign In
        </Link>
      </p>
    </AuthShell>
  );
}
