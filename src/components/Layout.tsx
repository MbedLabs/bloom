import { useState, useEffect, useMemo, useRef } from 'react'
import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { APP_VERSION, projectsApi } from '../api/client'
import { useAuth } from '../contexts/AuthContext'
import {
  LayoutDashboard, FolderKanban, FileText, CheckSquare,
  GitBranch, BarChart3, Sun, Moon,
  ExternalLink, ChevronDown, Search, Flower2,
  BookOpen, Bug, Layers, FlaskConical, LogOut, Users, PenTool, AlertTriangle, GitPullRequest, Settings, SlidersHorizontal
} from 'lucide-react'

const getBudUrl = () => {
  const runtimeUrl = window.runtimeConfig?.BUD_APP_URL
  const buildTimeUrl = import.meta.env.VITE_TESTSTATION_APP_URL
  const rawUrl = runtimeUrl || buildTimeUrl || 'http://localhost:3000'
  // Strip trailing /api if present in the URL for navigation purposes
  return rawUrl.replace(/\/api\/?$/, '')
}

const TESTSTATION_APP_URL = getBudUrl()

function useDarkMode() {
  const [dark, setDark] = useState(() => {
    const stored = localStorage.getItem('bloom-theme')
    if (stored) return stored === 'dark'
    return window.matchMedia('(prefers-color-scheme: dark)').matches
  })

  useEffect(() => {
    const root = document.documentElement
    if (dark) {
      root.classList.add('dark')
    } else {
      root.classList.remove('dark')
    }
    localStorage.setItem('bloom-theme', dark ? 'dark' : 'light')
  }, [dark])

  return [dark, setDark] as const
}

const mainNav = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Projects', href: '/projects', icon: FolderKanban },
]

const projectNav = [
  { name: 'Documents', icon: BookOpen, tab: '', href: 'docs' as const },
  { name: 'Requirements', icon: FileText, tab: '', href: 'docs' as const, filter: 'type:REQ' },
  { name: 'Test Cases', icon: CheckSquare, tab: '', href: 'docs' as const, filter: 'type:TC' },
  { name: 'Specifications', icon: FileText, tab: '', href: 'docs' as const, filter: 'type:SPEC' },
  { name: 'Protocols', icon: BookOpen, tab: '', href: 'docs' as const, filter: 'type:PROT' },
  { name: 'Reports', icon: Layers, tab: '', href: 'docs' as const, filter: 'type:RPT' },
  { name: 'Standards', icon: BookOpen, tab: '', href: 'docs' as const, filter: 'type:STD' },
  { name: 'Design', icon: PenTool, tab: '', href: 'docs' as const, filter: 'type:DES' },
  { name: 'Risks', icon: AlertTriangle, tab: '', href: 'docs' as const, filter: 'type:RSK' },
  { name: 'Changes', icon: GitPullRequest, tab: '', href: 'docs' as const, filter: 'type:CHG' },
  { name: 'Test Concepts', icon: Beaker, tab: '', href: 'docs' as const, filter: 'type:TCO' },
  { name: 'Defects', icon: Bug, tab: '', href: 'defects' as const },
  { name: 'Test Campaigns', icon: FlaskConical, tab: '', href: 'campaigns' as const },
  { name: 'Traceability', icon: GitBranch, tab: '', href: 'traceability' as const },
  { name: 'Parameters', icon: SlidersHorizontal, tab: '', href: 'parameters' as const },
]

function Beaker(props: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={props.className}>
      <path d="M4.5 3h15" /><path d="M6 3v16a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V3" /><path d="M6 14h12" />
    </svg>
  )
}

export default function Layout() {
  const location = useLocation()
  const navigate = useNavigate()
  const { user, logout } = useAuth()
  const [dark, setDark] = useDarkMode()
  const [projectDropdownOpen, setProjectDropdownOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchOpen, setSearchOpen] = useState(false)
  const [userMenuOpen, setUserMenuOpen] = useState(false)
  const userMenuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target as Node)) {
        setUserMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const { data: projects } = useQuery({
    queryKey: ['projects'],
    queryFn: projectsApi.list,
  })

  const isInProject = location.pathname.startsWith('/projects/')
  const currentProjectSlug = isInProject ? location.pathname.split('/')[2] : null
  const currentProjectName = currentProjectSlug
    ? projects?.find((p) => p.prefix === currentProjectSlug || String(p.id) === currentProjectSlug)?.name || currentProjectSlug
    : null

  const breadcrumbs = useMemo(() => getBreadcrumbs(location, projects || []), [location, projects])

  const roleBadgeColor = user?.role === 'admin'
    ? 'bg-red-500/10 text-red-400'
    : user?.role === 'maintainer'
    ? 'bg-blue-500/10 text-blue-400'
    : 'bg-green-500/10 text-green-400'

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const userInitials = user?.full_name
    ? user.full_name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)
    : 'U'

  return (
    <div className="min-h-screen flex">
      {/* Sidebar */}
      <aside className="w-64 bg-gradient-sidebar text-white flex flex-col fixed inset-y-0 left-0 z-30 overflow-y-auto">
        {/* Logo */}
        <div className="px-5 pt-6 pb-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-white/15 flex items-center justify-center">
              <Flower2 className="h-5 w-5 text-teal-200" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-teal-100 tracking-tight">Bloom</h1>
              <p className="text-[11px] text-teal-300/60 font-medium uppercase tracking-wider">Product Lifecycle Management</p>
            </div>
          </div>
        </div>

        {/* Main Navigation */}
        <nav className="px-3 space-y-1">
          {mainNav.map((item) => {
            const isActive = location.pathname === item.href ||
              (item.href !== '/' && location.pathname.startsWith(item.href))
            return (
              <Link
                key={item.name}
                to={item.href}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 group ${
                  isActive && !isInProject
                    ? 'bg-[var(--sidebar-active)] text-white shadow-sm'
                    : 'text-teal-100/70 hover:bg-[var(--sidebar-hover)] hover:text-white'
                }`}
              >
                <item.icon className={`h-[18px] w-[18px] transition-colors ${
                  isActive && !isInProject ? 'text-teal-300' : 'text-teal-400/50 group-hover:text-teal-300'
                }`} />
                {item.name}
                {isActive && !isInProject && (
                  <div className="ml-auto w-1.5 h-1.5 rounded-full bg-teal-400" />
                )}
              </Link>
            )
          })}
          {user?.role === 'admin' && (
            <Link
              to="/users"
              className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-teal-100/70 hover:bg-[var(--sidebar-hover)] hover:text-white transition-all duration-200 group"
            >
              <Users className="h-[18px] w-[18px] text-teal-400/50 group-hover:text-teal-300" />
              Users
            </Link>
          )}
        </nav>

        {/* Project Section */}
        <div className="mt-6 px-3">
          <div className="h-px bg-white/10 mb-3" />
          <p className="px-3 text-[10px] font-semibold text-teal-300/40 uppercase tracking-widest mb-2">Project</p>

          {/* Project Selector */}
          {projects && projects.length > 0 && (
            <div className="relative mb-2">
              <button
                onClick={() => setProjectDropdownOpen(!projectDropdownOpen)}
                className="w-full flex items-center justify-between px-3 py-2 rounded-lg bg-white/5 hover:bg-white/10 text-sm text-teal-100 transition-colors"
              >
                <span className="truncate">
                  {isInProject ? currentProjectName : 'Select Project'}
                </span>
                <ChevronDown className={`h-4 w-4 text-teal-400/50 transition-transform ${projectDropdownOpen ? 'rotate-180' : ''}`} />
              </button>

              {projectDropdownOpen && (
                <div className="absolute top-full left-0 right-0 mt-1 bg-[#0a3d3a] border border-teal-700/30 rounded-lg shadow-lg overflow-hidden z-50 max-h-48 overflow-y-auto sidebar-scrollbar">
                  {projects.map((p) => (
                    <Link
                      key={p.id}
                      to={`/projects/${p.prefix}`}
                      onClick={() => setProjectDropdownOpen(false)}
                      className="block px-3 py-2 text-sm text-teal-100 hover:bg-white/10 truncate transition-colors"
                    >
                      {p.name}
                    </Link>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Project Context Nav (shown when inside a project) */}
          {isInProject && (
            <div className="space-y-0.5 mt-2">
              {projectNav.map((item) => {
                const projSlug = location.pathname.split('/')[2]
                let to = ''
                if (item.tab) {
                  to = `/projects/${projSlug}?tab=${item.tab}`
                } else if ('filter' in item && item.filter) {
                  const typeVal = item.filter.replace('type:', '')
                  to = `/projects/${projSlug}/${item.href}?type=${encodeURIComponent(typeVal)}`
                } else if ('href' in item) {
                  to = `/projects/${projSlug}/${item.href}`
                }
                return (
                  <Link
                    key={item.name}
                    to={to}
                    className="flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-medium text-teal-200/60 hover:bg-[var(--sidebar-hover)] hover:text-teal-100 transition-all duration-200 group"
                  >
                    <item.icon className="h-4 w-4 text-teal-400/40 group-hover:text-teal-300" />
                    {item.name}
                  </Link>
                )
              })}
            </div>
          )}
        </div>

        {/* Reports & Settings */}
        <div className="px-3 mt-6 space-y-0.5">
          <Link
            to="/reports"
            className="flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-medium text-teal-200/60 hover:bg-[var(--sidebar-hover)] hover:text-teal-100 transition-all duration-200 group"
          >
            <BarChart3 className="h-4 w-4 text-teal-400/40 group-hover:text-teal-300" />
            Reports
          </Link>
          <Link
            to="/baselines"
            className="flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-medium text-teal-200/60 hover:bg-[var(--sidebar-hover)] hover:text-teal-100 transition-all duration-200 group"
          >
            <Layers className="h-4 w-4 text-teal-400/40 group-hover:text-teal-300" />
            Baselines
          </Link>
        </div>

        {/* Bottom section */}
        <div className="mt-auto px-3 pb-6 pt-2 space-y-1" style={{ paddingBottom: 'max(1.5rem, env(safe-area-inset-bottom))' }}>
          <div className="h-px bg-white/10 mx-2 mb-3" />
          <a
            href={TESTSTATION_APP_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-medium text-teal-100/70 hover:bg-[var(--sidebar-hover)] hover:text-white transition-all duration-200 group"
          >
            <ExternalLink className="h-[18px] w-[18px] text-teal-400/50 group-hover:text-teal-300" />
            Bud TMP
          </a>
          <Link
            to="/settings"
            className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-medium text-teal-100/70 hover:bg-[var(--sidebar-hover)] hover:text-white transition-all duration-200 group"
          >
            <Settings className="h-[18px] w-[18px] text-teal-400/50 group-hover:text-teal-300" />
            Settings
          </Link>
          <div className="pt-2 pb-1 px-3 text-center">
            <a href="https://www.embedlabs.de/en" target="_blank" rel="noopener noreferrer" className="text-[10px] text-teal-300/50 hover:text-teal-200 transition-colors">
              by EmbedLabs
            </a>
            <p className="text-[10px] text-teal-300/30 mt-1">v{APP_VERSION}</p>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col ml-64">
        {/* Header */}
        <header className="glass border-b border-border sticky top-0 z-20">
          <div className="px-6 py-3 flex items-center justify-between">
            {/* Breadcrumbs */}
            <div className="flex items-center gap-2 text-sm">
              {breadcrumbs.map((crumb, i) => (
                <div key={i} className="flex items-center gap-2">
                  {i > 0 && <span className="text-muted-foreground/40">/</span>}
                  {crumb.href ? (
                    <Link to={crumb.href} className="text-muted-foreground hover:text-foreground transition-colors">
                      {crumb.label}
                    </Link>
                  ) : (
                    <span className="text-foreground font-medium">{crumb.label}</span>
                  )}
                </div>
              ))}
            </div>

            {/* Right side */}
            <div className="flex items-center gap-3">
              {/* Search */}
              <div className="relative">
                <button
                  onClick={() => setSearchOpen(!searchOpen)}
                  className="p-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
                >
                  <Search className="h-4 w-4" />
                </button>
                {searchOpen && (
                  <div className="absolute right-0 top-full mt-2 w-80 bg-card border border-border rounded-lg shadow-elegant p-2 z-50">
                    <input
                      type="text"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      placeholder="Search requirements, test cases..."
                      className="w-full px-3 py-2 bg-background border border-input rounded-md text-sm text-foreground placeholder:text-muted-foreground focus:ring-2 focus:ring-ring focus:border-ring"
                      autoFocus
                    />
                  </div>
                )}
              </div>

              {/* Dark mode toggle */}
              <button
                onClick={() => setDark(!dark)}
                className="p-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
              >
                {dark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
              </button>

              {/* User menu */}
              <div className="relative" ref={userMenuRef}>
                <button
                  onClick={() => setUserMenuOpen(!userMenuOpen)}
                  className="flex items-center gap-2 p-1 rounded-lg hover:bg-accent transition-colors"
                >
                  <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary to-teal-700 flex items-center justify-center text-white text-xs font-bold">
                    {userInitials}
                  </div>
                  <span className="text-sm text-foreground font-medium hidden sm:block max-w-[120px] truncate">
                    {user?.full_name}
                  </span>
                  <ChevronDown className="h-3 w-3 text-muted-foreground" />
                </button>

                {userMenuOpen && (
                  <div className="absolute right-0 top-full mt-2 w-64 bg-card border border-border rounded-lg shadow-elegant overflow-hidden z-50">
                    <div className="px-4 py-3 border-b border-border">
                      <p className="text-sm font-medium text-foreground">{user?.full_name}</p>
                      <p className="text-xs text-muted-foreground">{user?.email}</p>
                      <span className={`inline-block mt-1.5 px-2 py-0.5 rounded text-[10px] font-semibold uppercase ${roleBadgeColor}`}>
                        {user?.role}
                      </span>
                    </div>
                    <div className="py-1">
                      <button
                        onClick={handleLogout}
                        className="w-full flex items-center gap-2 px-4 py-2 text-sm text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
                      >
                        <LogOut className="h-4 w-4" />
                        Sign out
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </header>

        <main className="flex-1 p-6 bg-background overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

function getBreadcrumbs(location: ReturnType<typeof useLocation>, projects: Array<{ id: number; name: string; prefix: string }>) {
  const TYPE_PAGE_TITLE: Record<string, string> = {
    REQ: 'Requirements', SPEC: 'Specifications', TC: 'Test Cases',
    DES: 'Design Items', RSK: 'Risks', CHG: 'Changes', TCO: 'Test Concepts',
    PROT: 'Protocols', RPT: 'Reports', STD: 'Standards',
  }
  const path = location.pathname
  const crumbs: { label: string; href?: string }[] = [{ label: 'Home', href: '/' }]
  const parts = path.split('/')
  const slug = parts[2]
  const projectName = slug
    ? (projects.find((p) => p.prefix === slug || String(p.id) === slug)?.name || slug)
    : undefined

  if (path === '/') return [{ label: 'Dashboard' }]
  if (path === '/reports') return [{ label: 'Home', href: '/' }, { label: 'Reports' }]
  if (path === '/baselines') return [{ label: 'Home', href: '/' }, { label: 'Baselines' }]
  if (path === '/settings') return [{ label: 'Home', href: '/' }, { label: 'Settings' }]

  if (path.startsWith('/projects')) {
    crumbs.push({ label: 'Projects', href: '/projects' })
    if (!slug) return crumbs

    const sub = parts[3]
    const projCrumb = { label: projectName!, href: `/projects/${slug}` }

    if (!sub) {
      crumbs.push({ label: projectName! })
      return crumbs
    }

    crumbs.push(projCrumb)

    const subMap: Record<string, string> = {
      docs: 'Documents',
      campaigns: 'Campaigns',
      suites: 'Suites',
      traceability: 'Traceability Matrix',
      'impact-analysis': 'Impact Analysis',
      parameters: 'Parameters',
      baselines: 'Baselines',
    }

    if (sub === 'docs') {
      const typeParam = new URLSearchParams(location.search).get('type')
      const docLabel = typeParam ? (TYPE_PAGE_TITLE[typeParam] || 'Documents') : 'Documents'
      if (parts[4] === 'new') {
        crumbs.push({ label: docLabel, href: `/projects/${slug}/docs${typeParam ? '?type=' + typeParam : ''}` })
        crumbs.push({ label: 'New' })
      } else if (parts[4] && parts[5]) {
        crumbs.push({ label: docLabel, href: `/projects/${slug}/docs${typeParam ? '?type=' + typeParam : ''}` })
        if (parts[6] === 'edit') {
          crumbs.push({ label: parts[5], href: `/projects/${slug}/docs/${parts[4]}/${parts[5]}` })
          crumbs.push({ label: 'Edit' })
        } else {
          crumbs.push({ label: parts[5] })
        }
      } else {
        crumbs.push({ label: docLabel })
      }
    } else if (sub === 'campaigns' && parts[4]) {
      crumbs.push({ label: 'Campaigns', href: `/projects/${slug}/campaigns` })
      crumbs.push({ label: 'Campaign Detail' })
    } else if (sub === 'suites' && parts[4]) {
      crumbs.push({ label: 'Suites', href: `/projects/${slug}/campaigns` })
      crumbs.push({ label: 'Suite Detail' })
    } else if (subMap[sub]) {
      crumbs.push({ label: subMap[sub] })
    }
  }

  return crumbs
}
