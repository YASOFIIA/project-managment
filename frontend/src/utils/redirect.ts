// Only allow same-origin relative paths as post-login redirect targets
export function safeRedirect(value: string | null): string {
  return value && value.startsWith('/') && !value.startsWith('//') ? value : '/dashboard';
}
