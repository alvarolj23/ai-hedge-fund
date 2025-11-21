import { ReactNode } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { BarChart3, TrendingUp, History, Activity, Settings } from 'lucide-react';
import { cn } from '@/lib/utils';

interface LayoutProps {
  children: ReactNode;
}

export default function Layout({ children }: LayoutProps) {
  const location = useLocation();

  const navigation = [
    { name: 'Portfolio', href: '/portfolio', icon: BarChart3 },
    { name: 'Analytics', href: '/analytics', icon: TrendingUp },
    { name: 'Trades', href: '/trades', icon: History },
    { name: 'Monitoring', href: '/monitoring', icon: Activity },
    { name: 'Config', href: '/config', icon: Settings },
  ];

  return (
    <div className="min-h-screen bg-slate-900">
      {/* Top Navigation Bar */}
      <nav className="bg-slate-800 border-b border-slate-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <h1 className="text-xl font-bold text-white">
                  🤖 AI Hedge Fund
                </h1>
              </div>
              <div className="ml-10 flex items-baseline space-x-4">
                {navigation.map((item) => {
                  const Icon = item.icon;
                  const isActive = location.pathname === item.href;
                  return (
                    <Link
                      key={item.name}
                      to={item.href}
                      className={cn(
                        'px-3 py-2 rounded-md text-sm font-medium flex items-center gap-2 transition-colors',
                        isActive
                          ? 'bg-slate-700 text-white'
                          : 'text-slate-300 hover:bg-slate-700 hover:text-white'
                      )}
                    >
                      <Icon className="h-4 w-4" />
                      {item.name}
                    </Link>
                  );
                })}
              </div>
            </div>
            <div className="flex items-center">
              <span className="text-sm text-slate-400">
                Trading Dashboard
              </span>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>
    </div>
  );
}
