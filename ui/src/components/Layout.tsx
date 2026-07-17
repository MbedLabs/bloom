import { useState, useEffect, useMemo, useRef } from 'react'
import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { APP_VERSION, notificationsApi, projectsApi, searchApi } from '../api/client'
import { docRegistryListUrl, syncRegistryProjectContext } from '../lib/docRegistryParams'
import { searchResultUrl } from '../lib/searchLinks'
import { getBreadcrumbs } from '../lib/breadcrumbs'
import { useAuth } from '../contexts/AuthContext'
import { PageMetaProvider, usePageMeta } from '../contexts/PageMetaContext'
import {
  LayoutDashboard, FolderKanban, FileText, CheckSquare,
  GitBranch, BarChart3, Sun, Moon, Bell,
  ExternalLink, ChevronDown, ChevronLeft, ChevronRight, Search, Flower2,
  BookOpen, Bug, Layers, FlaskConical, LogOut, Users, PenTool, AlertTriangle, GitPullRequest, Settings, SlidersHorizontal,
} from 'lucide-react'

/** Must match Tailwind `w-60` / `w-14` and main `ml-*` — also positions the seam toggle. */
const SIDEBAR_EDGE = { expanded: '15rem', collapsed: '3.5rem' } as const

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
  { name: 'Protocols', icon: BookOpen, tab: '', href: 'docs' as const, filter: 'type:PRT' },
  { name: 'Reports', icon: Layers, tab: '', href: 'docs' as const, filter: 'type:RPT' },
  { name: 'Standards', icon: BookOpen, tab: '', href: 'docs' as const, filter: 'type:STD' },
  { name: 'Design', icon: PenTool, tab: '', href: 'docs' as const, filter: 'type:DES' },
  { name: 'Risks', icon: AlertTriangle, tab: '', href: 'docs' as const, filter: 'type:RSK' },
  { name: 'Changes', icon: GitPullRequest, tab: '', href: 'docs' as const, filter: 'type:CHG' },
  { name: 'Test Concepts', icon: Beaker, tab: '', href: 'docs' as const, filter: 'type:CPT' },
  { name: 'Defects', icon: Bug, tab: '', href: 'docs' as const, filter: 'type:DEF' },
  { name: 'Test Campaigns', icon: FlaskConical, tab: '', href: 'docs' as const, filter: 'type:CMP' },
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
  return (
    <PageMetaProvider>
      <LayoutInner />
    </PageMetaProvider>
  )
}

function LayoutInner() {
  const location = useLocation()
  const navigate = useNavigate()
  const { user, logout } = useAuth()
  const [dark, setDark] = useDarkMode()
  const [projectDropdownOpen, setProjectDropdownOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [debouncedQuery, setDebouncedQuery] = useState('')
  const [searchOpen, setSearchOpen] = useState(false)
  const [searchActiveIndex, setSearchActiveIndex] = useState(0)
  const searchBoxRef = useRef<HTMLDivElement>(null)
  const [userMenuOpen, setUserMenuOpen] = useState(false)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => {
    const stored = localStorage.getItem('bloom-sidebar-collapsed')
    return stored ? stored === 'true' : false
  })
  const userMenuRef = useRef<HTMLDivElement>(null)
  const searchInputRef = useRef<HTMLInputElement>(null)

  const searchShortcutLabel = useMemo(() => {
    if (typeof navigator === 'undefined') return 'Ctrl K'
    return /Mac|iPhone|iPad|iPod/.test(navigator.userAgent) ? '⌘K' : 'Ctrl K'
  }, [])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (!e.metaKey && !e.ctrlKey) return
      if (e.key !== 'k' && e.key !== 'K') return
      const el = e.target as HTMLElement | null
      if (el?.closest('[contenteditable="true"]')) return
      if (el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') && el !== searchInputRef.current) return
      e.preventDefault()
      searchInputRef.current?.focus()
      searchInputRef.current?.select()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target as Node)) {
        setUserMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  useEffect(() => {
    localStorage.setItem('bloom-sidebar-collapsed', String(sidebarCollapsed))
  }, [sidebarCollapsed])

  const { data: projects } = useQuery({
    queryKey: ['projects'],
    queryFn: projectsApi.list,
  })

  // Debounce global search keystrokes so we query at most ~4x/second.
  useEffect(() => {
    const handle = window.setTimeout(() => setDebouncedQuery(searchQuery.trim()), 250)
    return () => window.clearTimeout(handle)
  }, [searchQuery])

  const { data: searchResults, isFetching: searchLoading } = useQuery({
    queryKey: ['global-search', debouncedQuery],
    queryFn: () => searchApi.global(debouncedQuery),
    enabled: debouncedQuery.length >= 2,
    staleTime: 30_000,
  })
  const searchItems = debouncedQuery.length >= 2 ? searchResults?.items ?? [] : []

  useEffect(() => {
    setSearchActiveIndex(0)
  }, [debouncedQuery])

  useEffect(() => {
    function closeOnOutsideClick(e: MouseEvent) {
      if (searchBoxRef.current && !searchBoxRef.current.contains(e.target as Node)) {
        setSearchOpen(false)
      }
    }
    document.addEventListener('mousedown', closeOnOutsideClick)
    return () => document.removeEventListener('mousedown', closeOnOutsideClick)
  }, [])

  const openSearchResult = (index: number) => {
    const item = searchItems[index]
    if (!item) return
    setSearchOpen(false)
    setSearchQuery('')
    searchInputRef.current?.blur()
    navigate(searchResultUrl(item))
  }

  // Notifications: unread badge polls every 60s; list loads when the panel opens.
  const queryClient = useQueryClient()
  const [notifOpen, setNotifOpen] = useState(false)
  const notifRef = useRef<HTMLDivElement>(null)
  const { data: unreadCount = 0 } = useQuery({
    queryKey: ['notifications-unread'],
    queryFn: notificationsApi.unreadCount,
    refetchInterval: 60_000,
  })
  const { data: notifications } = useQuery({
    queryKey: ['notifications-list'],
    queryFn: () => notificationsApi.list({ limit: 15 }),
    enabled: notifOpen,
  })
  const invalidateNotifications = () => {
    queryClient.invalidateQueries({ queryKey: ['notifications-unread'] })
    queryClient.invalidateQueries({ queryKey: ['notifications-list'] })
  }
  const markReadMutation = useMutation({
    mutationFn: notificationsApi.markRead,
    onSuccess: invalidateNotifications,
  })
  const markAllReadMutation = useMutation({
    mutationFn: notificationsApi.markAllRead,
    onSuccess: invalidateNotifications,
  })

  useEffect(() => {
    function closeNotifOnOutsideClick(e: MouseEvent) {
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) {
        setNotifOpen(false)
      }
    }
    document.addEventListener('mousedown', closeNotifOnOutsideClick)
    return () => document.removeEventListener('mousedown', closeNotifOnOutsideClick)
  }, [])

  const openNotification = (id: number, linkPath: string | null, alreadyRead: boolean) => {
    if (!alreadyRead) markReadMutation.mutate(id)
    setNotifOpen(false)
    if (linkPath) navigate(linkPath)
  }

  const onSearchKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Escape') {
      setSearchOpen(false)
      searchInputRef.current?.blur()
      return
    }
    if (!searchItems.length) return
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setSearchActiveIndex((i) => Math.min(i + 1, searchItems.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setSearchActiveIndex((i) => Math.max(i - 1, 0))
    } else if (e.key === 'Enter') {
      e.preventDefault()
      openSearchResult(searchActiveIndex)
    }
  }

  const isInProject = location.pathname.startsWith('/projects/')
  const currentProjectSlug = isInProject ? location.pathname.split('/')[2] : null

  useEffect(() => {
    syncRegistryProjectContext(currentProjectSlug)
  }, [currentProjectSlug])
  const currentProjectName = currentProjectSlug
    ? projects?.find((p) => p.prefix === currentProjectSlug || String(p.id) === currentProjectSlug)?.name || currentProjectSlug
    : null

  const { crumbLabel: pageCrumbLabel } = usePageMeta()
  const breadcrumbs = useMemo(
    () => getBreadcrumbs(location.pathname, location.search, projects || [], pageCrumbLabel),
    [location.pathname, location.search, projects, pageCrumbLabel],
  )

  const roleBadgeColor = user?.role === 'admin'
    ? 'bg-red-500/10 text-red-400'
    : user?.role === 'maintainer'
    ? 'bg-blue-500/10 text-blue-400'
    : 'bg-green-500/10 text-green-400'
  const canEditProjectParameters = user?.role === 'admin' || user?.role === 'maintainer'

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const userInitials = user?.full_name
    ? user.full_name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)
    : 'U'

  return (
    <div className="h-screen flex overflow-hidden">
      {/* Sidebar */}
      <aside className={`${sidebarCollapsed ? 'w-14' : 'w-60'} sidebar-scrollbar bg-gradient-sidebar text-white flex flex-col fixed inset-y-0 left-0 z-30 overflow-y-auto transition-all duration-200`}>
        {/* Logo */}
        <div className={`${sidebarCollapsed ? 'px-2 pt-4 pb-2.5' : 'px-3 pt-4 pb-2.5'}`}>
          <div className={`flex items-center ${sidebarCollapsed ? 'justify-center' : 'gap-2.5'}`}>
            <div className="w-9 h-9 rounded-lg bg-white/15 flex items-center justify-center shrink-0">
              <Flower2 className="h-5 w-5 text-teal-200" />
            </div>
            {!sidebarCollapsed && (
              <div className="min-w-0">
                <h1 className="text-base font-bold text-teal-100 tracking-tight">Bloom</h1>
                <p className="text-[10px] text-teal-300/60 font-medium uppercase tracking-wider leading-snug">Product Lifecycle Management</p>
              </div>
            )}
          </div>
        </div>

        {/* Main Navigation */}
        <nav className={`${sidebarCollapsed ? 'px-2' : 'px-3'} space-y-1`}>
          {mainNav.map((item) => {
            const isActive = location.pathname === item.href ||
              (item.href !== '/' && location.pathname.startsWith(item.href))
            return (
              <Link
                key={item.name}
                to={item.href}
                className={`flex items-center ${sidebarCollapsed ? 'justify-center px-2' : 'gap-2.5 px-3'} py-2 rounded-lg text-sm font-medium transition-all duration-200 group ${
                  isActive && !isInProject
                    ? 'bg-[var(--sidebar-active)] text-white shadow-sm'
                    : 'text-teal-100/70 hover:bg-[var(--sidebar-hover)] hover:text-white'
                }`}
                title={sidebarCollapsed ? item.name : undefined}
                onClick={() => {
                  if (sidebarCollapsed && location.pathname !== item.href) {
                    setSidebarCollapsed(false)
                  }
                }}
              >
                <item.icon className={`h-[18px] w-[18px] shrink-0 transition-colors ${
                  isActive && !isInProject ? 'text-teal-300' : 'text-teal-400/50 group-hover:text-teal-300'
                }`} />
                {!sidebarCollapsed && item.name}
                {isActive && !isInProject && !sidebarCollapsed && (
                  <div className="ml-auto w-1.5 h-1.5 rounded-full bg-teal-400" />
                )}
              </Link>
            )
          })}
          {user?.role === 'admin' && (
            <Link
              to="/users"
              className={`flex items-center ${sidebarCollapsed ? 'justify-center px-2' : 'gap-2.5 px-3'} py-2 rounded-lg text-sm font-medium text-teal-100/70 hover:bg-[var(--sidebar-hover)] hover:text-white transition-all duration-200 group`}
              title={sidebarCollapsed ? 'Users' : undefined}
              onClick={() => {
                if (sidebarCollapsed && location.pathname !== '/users') {
                  setSidebarCollapsed(false)
                }
              }}
            >
              <Users className="h-[18px] w-[18px] shrink-0 text-teal-400/50 group-hover:text-teal-300" />
              {!sidebarCollapsed && 'Users'}
            </Link>
          )}
        </nav>

        {/* Project Section */}
        <div className={`mt-4 ${sidebarCollapsed ? 'px-2' : 'px-3'}`}>
          <div className="h-px bg-white/10 mb-2" />
          {!sidebarCollapsed && <p className="px-3 text-xs font-semibold text-teal-300/40 uppercase tracking-widest mb-2">Project</p>}

          {/* Project Selector */}
          {projects && projects.length > 0 && !sidebarCollapsed && (
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
              {projectNav
                .filter((item) => item.href !== 'parameters' || canEditProjectParameters)
                .map((item) => {
                const projSlug = location.pathname.split('/')[2]
                let to = ''
                if (item.tab) {
                  to = `/projects/${projSlug}?tab=${item.tab}`
                } else if ('filter' in item && item.filter) {
                  const typeVal = item.filter.replace('type:', '')
                  to = docRegistryListUrl(projSlug, typeVal as import('../types/doc').DocType)
                } else if ('href' in item && item.href === 'docs') {
                  to = docRegistryListUrl(projSlug)
                } else if ('href' in item) {
                  to = `/projects/${projSlug}/${item.href}`
                }
                return (
                  <Link
                    key={item.name}
                    to={to}
                    className={`flex items-center ${sidebarCollapsed ? 'justify-center px-2' : 'gap-2.5 px-3'} py-1.5 rounded-lg text-[13px] font-medium text-teal-200/60 hover:bg-[var(--sidebar-hover)] hover:text-teal-100 transition-all duration-200 group`}
                    title={sidebarCollapsed ? item.name : undefined}
                    onClick={() => {
                      if (sidebarCollapsed && location.pathname !== to) {
                        setSidebarCollapsed(false)
                      }
                    }}
                  >
                    <item.icon className="h-4 w-4 shrink-0 text-teal-400/40 group-hover:text-teal-300" />
                    {!sidebarCollapsed && item.name}
                  </Link>
                )
              })}
            </div>
          )}
        </div>

        {/* Reports & Settings */}
        <div className={`${sidebarCollapsed ? 'px-2' : 'px-3'} mt-4 space-y-0.5`}>
          <Link
            to="/reports"
            className={`flex items-center ${sidebarCollapsed ? 'justify-center px-2' : 'gap-2.5 px-3'} py-1.5 rounded-lg text-[13px] font-medium text-teal-200/60 hover:bg-[var(--sidebar-hover)] hover:text-teal-100 transition-all duration-200 group`}
            title={sidebarCollapsed ? 'Reports' : undefined}
            onClick={() => {
              if (sidebarCollapsed && location.pathname !== '/reports') {
                setSidebarCollapsed(false)
              }
            }}
          >
            <BarChart3 className="h-4 w-4 shrink-0 text-teal-400/40 group-hover:text-teal-300" />
            {!sidebarCollapsed && 'Reports'}
          </Link>
          <Link
            to="/baselines"
            className={`flex items-center ${sidebarCollapsed ? 'justify-center px-2' : 'gap-2.5 px-3'} py-1.5 rounded-lg text-[13px] font-medium text-teal-200/60 hover:bg-[var(--sidebar-hover)] hover:text-teal-100 transition-all duration-200 group`}
            title={sidebarCollapsed ? 'Baselines' : undefined}
            onClick={() => {
              if (sidebarCollapsed && location.pathname !== '/baselines') {
                setSidebarCollapsed(false)
              }
            }}
          >
            <Layers className="h-4 w-4 shrink-0 text-teal-400/40 group-hover:text-teal-300" />
            {!sidebarCollapsed && 'Baselines'}
          </Link>
        </div>

        {/* Bottom section */}
        <div className={`mt-auto ${sidebarCollapsed ? 'px-2' : 'px-3'} pb-4 pt-2 space-y-1`} style={{ paddingBottom: 'max(1rem, env(safe-area-inset-bottom))' }}>
          <div className="h-px bg-white/10 mx-2 mb-2" />
          <a
            href={TESTSTATION_APP_URL}
            target="_blank"
            rel="noopener noreferrer"
            className={`flex items-center ${sidebarCollapsed ? 'justify-center px-2' : 'gap-2.5 px-3'} py-1.5 rounded-lg text-[13px] font-medium text-teal-100/70 hover:bg-[var(--sidebar-hover)] hover:text-white transition-all duration-200 group`}
            title={sidebarCollapsed ? 'Bud TMP' : undefined}
          >
            <ExternalLink className="h-4 w-4 shrink-0 text-teal-400/50 group-hover:text-teal-300" />
            {!sidebarCollapsed && 'Bud TMP'}
          </a>
          <Link
            to="/settings"
            className={`flex items-center ${sidebarCollapsed ? 'justify-center px-2' : 'gap-2.5 px-3'} py-1.5 rounded-lg text-[13px] font-medium text-teal-100/70 hover:bg-[var(--sidebar-hover)] hover:text-white transition-all duration-200 group`}
            title={sidebarCollapsed ? 'Settings' : undefined}
            onClick={() => {
              if (sidebarCollapsed && location.pathname !== '/settings') {
                setSidebarCollapsed(false)
              }
            }}
          >
            <Settings className="h-4 w-4 shrink-0 text-teal-400/50 group-hover:text-teal-300" />
            {!sidebarCollapsed && 'Settings'}
          </Link>
          {!sidebarCollapsed && (
            <div className="pt-2 pb-1 px-3 text-center">
              <a href="https://www.embedlabs.net" target="_blank" rel="noopener noreferrer" className="text-xs text-teal-300/50 hover:text-teal-200 transition-colors">
                by EmbedLabs
              </a>
              <p className="text-xs text-teal-300/30 mt-1">v{APP_VERSION}</p>
            </div>
          )}
        </div>
      </aside>

      <button
        type="button"
        onClick={() => setSidebarCollapsed((c) => !c)}
        className="fixed z-[35] top-4 flex h-8 w-8 -translate-x-1/2 items-center justify-center rounded-full border border-border bg-background text-muted-foreground shadow-md transition-[left,background-color,color,box-shadow] duration-200 hover:bg-accent hover:text-foreground dark:bg-card dark:hover:bg-accent"
        style={{ left: sidebarCollapsed ? SIDEBAR_EDGE.collapsed : SIDEBAR_EDGE.expanded }}
        aria-label={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        title={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
      >
        {sidebarCollapsed ? <ChevronRight className="h-4 w-4" strokeWidth={2.25} /> : <ChevronLeft className="h-4 w-4" strokeWidth={2.25} />}
      </button>

      {/* Main content */}
      <div className={`flex-1 flex flex-col min-w-0 min-h-0 ${sidebarCollapsed ? 'ml-14' : 'ml-60'} transition-all duration-200`}>
        {/* Header */}
        <header className="glass border-b border-border sticky top-0 z-20">
          <div className="px-3 py-2 flex items-center gap-3 min-w-0">
            {/* Breadcrumbs — extra left inset so seam toggle does not cover “Home” */}
            <div className="flex min-w-0 shrink-0 items-center gap-2 overflow-x-auto overflow-y-hidden pl-6 text-sm">
              {breadcrumbs.map((crumb, i) => (
                <div key={i} className="flex items-center gap-2 shrink-0">
                  {i > 0 && <span className="text-muted-foreground/40">/</span>}
                  {crumb.href ? (
                    <Link
                      to={crumb.href}
                      className="whitespace-nowrap text-muted-foreground transition-colors hover:text-foreground"
                    >
                      {crumb.label}
                    </Link>
                  ) : (
                    <span className="whitespace-nowrap font-medium text-foreground">
                      {crumb.label}
                    </span>
                  )}
                </div>
              ))}
            </div>

            {/* Inline search */}
            <div className="flex-1 min-w-0 flex justify-center">
              <div className="relative w-full max-w-sm" ref={searchBoxRef}>
                <Search className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
                <input
                  ref={searchInputRef}
                  type="search"
                  value={searchQuery}
                  onChange={(e) => { setSearchQuery(e.target.value); setSearchOpen(true) }}
                  onFocus={() => setSearchOpen(true)}
                  onKeyDown={onSearchKeyDown}
                  placeholder="Search requirements, test cases..."
                  title={`Focus search (${searchShortcutLabel})`}
                  role="combobox"
                  aria-expanded={searchOpen && searchItems.length > 0}
                  aria-controls="global-search-results"
                  className="w-full rounded-md border border-input bg-background py-1.5 pl-9 pr-[5.25rem] text-sm text-foreground placeholder:text-muted-foreground focus:border-ring focus:outline-none focus:ring-2 focus:ring-ring"
                />
                <span className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 select-none text-[10px] font-medium text-muted-foreground" aria-hidden>
                  <kbd className="inline-flex h-5 min-w-[2.75rem] items-center justify-center rounded border border-border bg-muted px-1.5 font-sans shadow-sm">
                    {searchShortcutLabel}
                  </kbd>
                </span>

                {searchOpen && debouncedQuery.length >= 2 && (
                  <div
                    id="global-search-results"
                    className="absolute left-0 right-0 top-full z-50 mt-1 max-h-96 overflow-y-auto rounded-md border border-border bg-card shadow-elegant"
                  >
                    {searchItems.length === 0 && (
                      <div className="px-3 py-2.5 text-sm text-muted-foreground">
                        {searchLoading ? 'Searching…' : `No results for “${debouncedQuery}”`}
                      </div>
                    )}
                    {searchItems.map((item, index) => (
                      <button
                        key={`${item.type}-${item.id}`}
                        type="button"
                        onMouseDown={(e) => e.preventDefault()}
                        onClick={() => openSearchResult(index)}
                        onMouseEnter={() => setSearchActiveIndex(index)}
                        className={`flex w-full items-center gap-2.5 px-3 py-2 text-left text-sm transition-colors ${
                          index === searchActiveIndex ? 'bg-accent text-foreground' : 'text-muted-foreground hover:bg-accent/50'
                        }`}
                      >
                        <span className="inline-flex h-5 min-w-[2.5rem] shrink-0 items-center justify-center rounded border border-border bg-muted px-1 text-[10px] font-semibold uppercase text-muted-foreground">
                          {item.type}
                        </span>
                        <span className="shrink-0 font-mono text-xs text-primary">{item.doc_id}</span>
                        <span className="min-w-0 flex-1 truncate text-foreground">{item.title}</span>
                        <span className="shrink-0 text-[10px] uppercase text-muted-foreground">{item.project_prefix}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Right side */}
            <div className="flex shrink-0 items-center gap-1.5">
              {/* Notifications */}
              <div className="relative" ref={notifRef}>
                <button
                  onClick={() => setNotifOpen((open) => !open)}
                  className="relative p-1 rounded-lg text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
                  aria-label={`Notifications${unreadCount ? ` (${unreadCount} unread)` : ''}`}
                >
                  <Bell className="h-4 w-4" />
                  {unreadCount > 0 && (
                    <span className="absolute -top-0.5 -right-0.5 flex h-4 min-w-[1rem] items-center justify-center rounded-full bg-primary px-1 text-[9px] font-bold text-primary-foreground">
                      {unreadCount > 99 ? '99+' : unreadCount}
                    </span>
                  )}
                </button>

                {notifOpen && (
                  <div className="absolute right-0 top-full z-50 mt-2 w-96 max-w-[90vw] overflow-hidden rounded-lg border border-border bg-card shadow-elegant">
                    <div className="flex items-center justify-between border-b border-border px-4 py-2.5">
                      <span className="text-sm font-medium text-foreground">Notifications</span>
                      {unreadCount > 0 && (
                        <button
                          onClick={() => markAllReadMutation.mutate()}
                          className="text-xs text-primary hover:underline"
                        >
                          Mark all read
                        </button>
                      )}
                    </div>
                    <div className="max-h-96 overflow-y-auto">
                      {(notifications?.items?.length ?? 0) === 0 && (
                        <div className="px-4 py-6 text-center text-sm text-muted-foreground">
                          No notifications yet
                        </div>
                      )}
                      {notifications?.items?.map((n) => (
                        <button
                          key={n.id}
                          onClick={() => openNotification(n.id, n.link_path, n.read_at !== null)}
                          className={`block w-full border-b border-border px-4 py-2.5 text-left transition-colors last:border-b-0 hover:bg-accent/50 ${
                            n.read_at === null ? 'bg-primary/5' : ''
                          }`}
                        >
                          <div className="flex items-start gap-2">
                            {n.read_at === null && (
                              <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" aria-hidden />
                            )}
                            <div className="min-w-0">
                              <div className="truncate text-sm text-foreground">{n.title}</div>
                              {n.body && (
                                <div className="truncate text-xs text-muted-foreground">{n.body}</div>
                              )}
                              <div className="mt-0.5 text-[10px] uppercase text-muted-foreground">
                                {new Date(n.created_at + 'Z').toLocaleString()}
                              </div>
                            </div>
                          </div>
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Dark mode toggle */}
              <button
                onClick={() => setDark(!dark)}
                className="p-1 rounded-lg text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
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

        <main className="p-4 bg-background flex flex-col flex-1 min-h-0 overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
