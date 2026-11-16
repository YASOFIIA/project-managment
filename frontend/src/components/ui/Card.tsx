import type { HTMLAttributes } from 'react';

export function Card({ className = '', ...rest }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={`glass rounded-card border border-line shadow-card ${className}`}
      {...rest}
    />
  );
}
