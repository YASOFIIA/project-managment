import { LogOut } from 'lucide-react';
import { Avatar } from '../components/ui/Avatar';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { useAuth } from '../hooks/useAuth';
import { formatDate } from '../utils/formatDate';

export default function SettingsPage() {
  const { user, logout } = useAuth();
  if (!user) return null;

  return (
    <div className="flex max-w-xl flex-col gap-6">
      <div>
        <h2 className="text-2xl">Settings</h2>
        <p className="mt-1 text-sm text-ink-soft">Your account profile</p>
      </div>
      <Card className="p-6">
        <h3 className="mb-4 border-b border-line pb-2 text-base font-semibold">Profile</h3>
        <div className="mb-6 flex items-center gap-4">
          <Avatar name={user.login} size={56} />
          <div>
            <p className="text-lg font-semibold tracking-tight">{user.login}</p>
            <p className="text-sm text-ink-soft">{user.email}</p>
          </div>
        </div>
        <dl className="grid gap-4 text-sm sm:grid-cols-3">
          <div>
            <dt className="text-xs text-ink-soft">Username</dt>
            <dd className="mt-0.5 font-medium">{user.login}</dd>
          </div>
          <div>
            <dt className="text-xs text-ink-soft">Email</dt>
            <dd className="mt-0.5 truncate font-medium" title={user.email}>{user.email}</dd>
          </div>
          <div>
            <dt className="text-xs text-ink-soft">Joined</dt>
            <dd className="mt-0.5 font-medium">{formatDate(user.created_at)}</dd>
          </div>
        </dl>
      </Card>
      <div>
        <Button variant="secondary" onClick={logout}>
          <LogOut size={16} strokeWidth={1.5} aria-hidden /> Sign Out
        </Button>
      </div>
    </div>
  );
}
