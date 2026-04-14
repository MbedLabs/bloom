import { Outlet, Link, useLocation } from 'react-router-dom'
import { LayoutDashboard, FolderKanban, GitBranch, ExternalLink } from 'lucide-react'

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Projects', href: '/projects', icon: FolderKanban },
  { name: 'Traceability', href: '', icon: GitBranch, disabled: true },
]

const TESTSTATION_APP_URL = import.meta.env.VITE_TESTSTATION_APP_URL || 'http://localhost:5173'

export default function Layout() {
  const location = useLocation()

  const activeNav = navigation.find(n =>
    n.href === location.pathname ||
    (n.href !== '/' && n.href !== '' && location.pathname.startsWith(n.href))
  )

  return (
    <div className="min-h-screen flex">
      <div className="w-64 bg-gray-900 text-white">
        <div className="p-4">
          <h1 className="text-2xl font-bold text-teal-400">EmbedLabs</h1>
          <p className="text-sm text-gray-400">Lifecycle Manager</p>
        </div>

        <nav className="mt-8">
          {navigation.map((item) => {
            const isActive = item.href !== '' && (
              location.pathname === item.href ||
              (item.href !== '/' && location.pathname.startsWith(item.href))
            )

            if (item.disabled) {
              return (
                <div
                  key={item.name}
                  className="flex items-center px-4 py-3 text-sm font-medium text-gray-600 cursor-not-allowed"
                >
                  <item.icon className="mr-3 h-5 w-5" />
                  {item.name}
                  <span className="ml-auto text-xs text-gray-600">select project</span>
                </div>
              )
            }

            return (
              <Link
                key={item.name}
                to={item.href}
                className={`flex items-center px-4 py-3 text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-teal-600 text-white'
                    : 'text-gray-300 hover:bg-gray-800 hover:text-white'
                }`}
              >
                <item.icon className="mr-3 h-5 w-5" />
                {item.name}
              </Link>
            )
          })}
        </nav>

        <div className="absolute bottom-0 left-0 w-64 p-4 border-t border-gray-800">
          <a
            href={TESTSTATION_APP_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center text-sm text-gray-400 hover:text-teal-400 transition-colors"
          >
            <ExternalLink className="mr-3 h-5 w-5" />
            Test Station App
          </a>
        </div>
      </div>

      <div className="flex-1 flex flex-col">
        <header className="bg-white shadow-sm border-b border-gray-200">
          <div className="px-6 py-4">
            <h2 className="text-lg font-semibold text-gray-900">
              {activeNav?.name || 'Dashboard'}
            </h2>
          </div>
        </header>

        <main className="flex-1 p-6 bg-gray-50 overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
