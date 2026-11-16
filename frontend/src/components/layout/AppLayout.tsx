import { useEffect, useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { ProjectsProvider } from '../../context/ProjectsContext';
import { Sidebar } from './Sidebar';
import { TopBar } from './TopBar';

export function AppLayout() {
  const [menuOpen, setMenuOpen] = useState(false);
  const { pathname } = useLocation();

  useEffect(() => setMenuOpen(false), [pathname]);

  return (
    <ProjectsProvider>
      <div className="min-h-screen">
        <aside className="fixed inset-y-0 left-0 z-30 hidden md:block">
          <Sidebar />
        </aside>

        {menuOpen && (
          <div className="fixed inset-0 z-40 md:hidden">
            <button
              type="button"
              aria-label="Close menu"
              className="absolute inset-0 bg-black/30 backdrop-blur-sm"
              onClick={() => setMenuOpen(false)}
            />
            <div className="relative h-full w-60">
              <Sidebar onNavigate={() => setMenuOpen(false)} onClose={() => setMenuOpen(false)} />
            </div>
          </div>
        )}

        <div className="md:pl-60">
          <TopBar onMenu={() => setMenuOpen(true)} />
          <main className="mx-auto max-w-6xl px-4 py-6 md:px-8">
            <Outlet />
          </main>
        </div>
      </div>
    </ProjectsProvider>
  );
}
