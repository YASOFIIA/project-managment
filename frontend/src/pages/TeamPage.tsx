import { Link } from 'react-router-dom';
import { Users } from 'lucide-react';
import { Avatar } from '../components/ui/Avatar';
import { Card } from '../components/ui/Card';
import { EmptyState } from '../components/ui/EmptyState';
import { useAuth } from '../hooks/useAuth';
import { useProjects } from '../hooks/useProjects';

// Everyone you collaborate with, grouped across projects
export default function TeamPage() {
  const { user } = useAuth();
  const { projects, membersByProject, loading } = useProjects();

  const people = new Map<number, { login: string; projects: { id: number; name: string }[] }>();
  for (const p of projects) {
    for (const m of membersByProject[p.id] ?? []) {
      if (m.user_id === user?.id) continue;
      const entry = people.get(m.user_id) ?? { login: m.login, projects: [] };
      entry.projects.push({ id: p.id, name: p.name });
      people.set(m.user_id, entry);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h2 className="text-2xl">Команда</h2>
        <p className="mt-1 text-sm text-ink-soft">Колеги з ваших спільних проєктів</p>
      </div>
      {!loading && people.size === 0 ? (
        <Card>
          <EmptyState icon={Users} title="Поки що ви працюєте самі" description="Запросіть колег на вкладці «Команда» у проєкті." />
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[...people.entries()].map(([id, person]) => (
            <Card key={id} className="pm-enter flex gap-3 p-4">
              <Avatar name={person.login} size={40} />
              <div className="min-w-0">
                <p className="font-medium">{person.login}</p>
                <ul className="mt-1 flex flex-wrap gap-x-2 text-xs text-ink-soft">
                  {person.projects.map((p) => (
                    <li key={p.id}>
                      <Link to={`/project/${p.id}?tab=team`} className="hover:text-accent">{p.name}</Link>
                    </li>
                  ))}
                </ul>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
