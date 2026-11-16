import { useEffect, useRef, useState } from 'react';
import { Link, Navigate, useSearchParams } from 'react-router-dom';
import { CheckCircle2, Loader2, XCircle } from 'lucide-react';
import { joinByToken } from '../api/projects';
import { AuthShell } from '../components/layout/AuthShell';
import { Button } from '../components/ui/Button';
import { useAuth } from '../hooks/useAuth';
import { getErrorMessage } from '../utils/errors';

type State =
  | { kind: 'loading' }
  | { kind: 'ok'; projectId: number }
  | { kind: 'error'; message: string };

export default function JoinPage() {
  const { isAuthenticated, loading } = useAuth();
  const [params] = useSearchParams();
  const token = params.get('token');
  const [state, setState] = useState<State>({ kind: 'loading' });
  const started = useRef(false);

  // The token is single-use: make sure we call the API only once
  useEffect(() => {
    if (loading || !isAuthenticated || !token || started.current) return;
    started.current = true;
    joinByToken(token)
      .then((m) => setState({ kind: 'ok', projectId: m.project_id }))
      .catch((error) => setState({ kind: 'error', message: getErrorMessage(error) }));
  }, [loading, isAuthenticated, token]);

  if (loading) return null;
  if (!isAuthenticated) {
    const back = encodeURIComponent(`/join?token=${token ?? ''}`);
    return <Navigate to={`/login?redirect=${back}`} replace />;
  }

  return (
    <AuthShell title="Запрошення в проєкт" subtitle="Перевіряємо ваше запрошення">
      {!token && <Result icon="error" text="У посиланні немає токена запрошення." />}
      {token && state.kind === 'loading' && (
        <div className="flex justify-center py-4" role="status" aria-label="Завантаження">
          <Loader2 className="animate-spin text-accent" size={28} />
        </div>
      )}
      {state.kind === 'ok' && (
        <>
          <Result icon="ok" text="Ви приєдналися до проєкту!" />
          <Link to={`/project/${state.projectId}`}>
            <Button fullWidth className="mt-5">Перейти до проєкту</Button>
          </Link>
        </>
      )}
      {state.kind === 'error' && (
        <>
          <Result icon="error" text={state.message} />
          <Link to="/dashboard">
            <Button variant="secondary" fullWidth className="mt-5">До дашборду</Button>
          </Link>
        </>
      )}
    </AuthShell>
  );
}

function Result({ icon, text }: { icon: 'ok' | 'error'; text: string }) {
  const Icon = icon === 'ok' ? CheckCircle2 : XCircle;
  return (
    <div className="flex flex-col items-center gap-2 text-center" role={icon === 'error' ? 'alert' : 'status'}>
      <Icon size={36} strokeWidth={1.5} className={icon === 'ok' ? 'text-success' : 'text-danger'} aria-hidden />
      <p className="text-sm">{text}</p>
    </div>
  );
}
