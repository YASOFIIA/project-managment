import { forwardRef, type ButtonHTMLAttributes } from 'react';
import { Loader2 } from 'lucide-react';

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger';

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  loading?: boolean;
  fullWidth?: boolean;
  size?: 'sm' | 'md';
}

const variants: Record<Variant, string> = {
  primary: 'bg-accent text-white shadow-card hover:bg-accent-hover',
  secondary: 'bg-white/80 text-ink border border-line shadow-card hover:bg-white',
  ghost: 'text-ink-soft hover:bg-black/5 hover:text-ink',
  danger: 'bg-danger text-white shadow-card hover:bg-red-600',
};

export const Button = forwardRef<HTMLButtonElement, Props>(function Button(
  { variant = 'primary', loading, fullWidth, size = 'md', className = '', disabled, children, ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      type="button"
      disabled={disabled || loading}
      className={`inline-flex items-center justify-center gap-2 rounded-btn font-medium transition-colors duration-150 disabled:cursor-not-allowed disabled:opacity-60 ${
        size === 'sm' ? 'h-8 px-3 text-[13px]' : 'h-10 px-4 text-sm'
      } ${fullWidth ? 'w-full' : ''} ${variants[variant]} ${className}`}
      {...rest}
    >
      {loading && <Loader2 size={16} className="animate-spin" aria-hidden />}
      {children}
    </button>
  );
});
