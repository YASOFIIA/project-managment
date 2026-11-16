import { forwardRef, useId, type InputHTMLAttributes, type ReactNode } from 'react';

interface Props extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  trailing?: ReactNode;
}

export const Input = forwardRef<HTMLInputElement, Props>(function Input(
  { label, error, trailing, className = '', id, ...rest },
  ref,
) {
  const autoId = useId();
  const inputId = id ?? autoId;
  return (
    <div className={className}>
      {label && (
        <label htmlFor={inputId} className="mb-1.5 block text-[13px] font-medium text-ink">
          {label}
        </label>
      )}
      <div className="relative">
        <input
          ref={ref}
          id={inputId}
          aria-invalid={!!error}
          aria-describedby={error ? `${inputId}-err` : undefined}
          className={`h-10 w-full rounded-input border bg-white/80 px-3 text-sm placeholder:text-ink-soft/70 transition-colors duration-150 focus:border-accent focus:bg-white focus:outline-none focus:ring-2 focus:ring-accent/20 ${
            error ? 'border-danger' : 'border-black/10'
          } ${trailing ? 'pr-10' : ''}`}
          {...rest}
        />
        {trailing && <div className="absolute inset-y-0 right-2 flex items-center">{trailing}</div>}
      </div>
      {error && (
        <p id={`${inputId}-err`} className="mt-1 text-xs text-danger">
          {error}
        </p>
      )}
    </div>
  );
});
