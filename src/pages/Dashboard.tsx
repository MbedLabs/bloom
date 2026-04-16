import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { dashboardApi } from '../api/client'
import { FolderKanban, FileText, CheckCircle, TrendingUp, Flower2, ArrowRight, FlaskConical, BookOpen } from 'lucide-react'

export default function Dashboard() {
  const { data: stats, isLoading } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: dashboardApi.getStats,
  })

  if (isLoading) {
    return <DashboardSkeleton />
  }

  const s = stats || {
    total_projects: 0, active_projects: 0, total_requirements: 0,
    total_test_cases: 0, total_documents: 0, total_campaigns: 0,
    active_campaigns: 0, coverage_percent: 0, uncovered_requirements: 0,
    requirement_status_distribution: {}, test_case_status_distribution: {},
    campaign_result_distribution: {}, projects: [],
  }

  const coverage = s.coverage_percent
  const coverageColor = coverage >= 80 ? 'text-emerald-600 dark:text-emerald-400' : coverage >= 50 ? 'text-amber-600 dark:text-amber-400' : 'text-red-600 dark:text-red-400'
  const coverageBar = coverage >= 80 ? 'from-emerald-500 to-teal-400' : coverage >= 50 ? 'from-amber-500 to-amber-400' : 'from-red-500 to-red-400'

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="bg-gradient-hero rounded-xl p-6 text-white relative overflow-hidden">
        <div className="relative z-10">
          <div className="flex items-center gap-2 mb-2">
            <Flower2 className="h-6 w-6 text-teal-100" />
            <h2 className="text-xl font-bold">Bloom ALM</h2>
          </div>
          <p className="text-teal-100/80 text-sm max-w-lg">
            Manage your requirements, test cases, and traceability across projects. Full lifecycle coverage from specification to verification.
          </p>
        </div>
        <div className="absolute top-0 right-0 w-64 h-full opacity-10">
          <svg viewBox="0 0 200 200" className="w-full h-full">
            <circle cx="150" cy="50" r="80" fill="white" />
            <circle cx="100" cy="150" r="60" fill="white" />
          </svg>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
        <StatCard title="Projects" value={s.total_projects} subtitle={`${s.active_projects} active`} icon={FolderKanban} gradient="from-primary to-teal-700" />
        <StatCard title="Requirements" value={s.total_requirements} subtitle="Total" icon={FileText} gradient="from-emerald-500 to-emerald-700" />
        <StatCard title="Test Cases" value={s.total_test_cases} subtitle="Defined" icon={CheckCircle} gradient="from-cyan-500 to-teal-700" />
        <StatCard title="Documents" value={s.total_documents} subtitle="Created" icon={BookOpen} gradient="from-indigo-500 to-indigo-700" />
        <StatCard title="Campaigns" value={s.total_campaigns} subtitle={`${s.active_campaigns} active`} icon={FlaskConical} gradient="from-purple-500 to-purple-700" />
        <div className="bg-card rounded-lg border border-border shadow-elegant hover:shadow-glow transition-shadow duration-300 p-5 col-span-2 md:col-span-2 lg:col-span-2">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Coverage</p>
              <p className={`text-3xl font-bold mt-2 ${coverageColor}`}>{coverage}%</p>
              <p className="text-xs text-muted-foreground mt-1">{s.uncovered_requirements} uncovered requirements</p>
            </div>
            <div className="p-2.5 rounded-lg bg-gradient-to-br from-primary/10 to-cyan-500/10">
              <TrendingUp className="h-5 w-5 text-primary" />
            </div>
          </div>
          <div className="h-1.5 bg-muted rounded-full overflow-hidden mt-3">
            <div className={`h-full rounded-full bg-gradient-to-r ${coverageBar} transition-all duration-1000`} style={{ width: `${coverage}%` }} />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <DonutChart
          title="Requirement Status"
          data={s.requirement_status_distribution}
          total={s.total_requirements}
          colorMap={{
            Draft: '#94a3b8', Review: '#f59e0b', Approved: '#3b82f6',
            Implemented: '#14b8a6', Verified: '#10b981', Rejected: '#ef4444',
          }}
          emptyMessage="No requirements yet"
        />

        <DonutChart
          title="Test Case Status"
          data={s.test_case_status_distribution}
          total={s.total_test_cases}
          colorMap={{
            Draft: '#94a3b8', Active: '#10b981', Deprecated: '#ef4444',
          }}
          emptyMessage="No test cases yet"
        />

        <DonutChart
          title="Campaign Results"
          data={s.campaign_result_distribution}
          total={Object.values(s.campaign_result_distribution).reduce((a, b) => a + b, 0)}
          colorMap={{
            Passed: '#10b981', Failed: '#ef4444', Blocked: '#f59e0b', Skipped: '#94a3b8',
          }}
          emptyMessage="No campaign results yet"
        />
      </div>

      <div className="bg-card rounded-lg border border-border shadow-elegant overflow-hidden">
        <div className="px-5 py-4 border-b border-border flex justify-between items-center">
          <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
            <FolderKanban className="h-4 w-4 text-primary" />
            Project Overview
          </h3>
          <Link to="/projects" className="text-xs font-medium text-primary hover:text-primary/80 transition-colors inline-flex items-center gap-1">
            View all <ArrowRight className="h-3 w-3" />
          </Link>
        </div>
        {s.projects.length === 0 ? (
          <div className="p-12 text-center">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary/10 to-cyan-500/10 flex items-center justify-center mx-auto mb-4">
              <FolderKanban className="h-8 w-8 text-primary/40" />
            </div>
            <h3 className="text-sm font-semibold text-foreground mb-1">No Projects Yet</h3>
            <p className="text-xs text-muted-foreground mb-4">Create your first project to start managing requirements.</p>
            <Link to="/projects" className="inline-flex items-center px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 transition-colors">
              Create Project
            </Link>
          </div>
        ) : (
          <div className="divide-y divide-border">
            {s.projects.slice(0, 5).map((project) => (
              <Link key={project.id} to={`/projects/${project.prefix}`} className="block px-5 py-3.5 hover:bg-accent/50 transition-colors group">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3 min-w-0 flex-1">
                    <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                      <FolderKanban className="h-4 w-4 text-primary" />
                    </div>
                    <div className="min-w-0">
                      <p className="font-medium text-foreground text-sm group-hover:text-primary transition-colors truncate">{project.name}</p>
                      <p className="text-xs text-muted-foreground">{project.prefix}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4 ml-4 flex-shrink-0">
                    <div className="flex items-center gap-3 text-xs text-muted-foreground">
                      <span className="flex items-center gap-1"><FileText className="h-3 w-3" />{project.requirement_count}</span>
                      <span className="flex items-center gap-1"><CheckCircle className="h-3 w-3" />{project.test_case_count}</span>
                    </div>
                    <StatusBadge status={project.status} />
                    <MiniCoverage reqs={project.requirement_count} tcs={project.test_case_count} />
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function StatCard({ title, value, subtitle, icon: Icon, gradient }: {
  title: string; value: number | string; subtitle?: string; icon: React.ComponentType<{ className?: string }>; gradient: string
}) {
  return (
    <div className="bg-card rounded-lg border border-border shadow-elegant hover:shadow-glow transition-shadow duration-300 p-5">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">{title}</p>
          <p className="text-3xl font-bold text-foreground mt-2">{value}</p>
          {subtitle && <p className="text-xs text-muted-foreground mt-1">{subtitle}</p>}
        </div>
        <div className={`p-2.5 rounded-lg bg-gradient-to-br ${gradient}`}>
          <Icon className="h-5 w-5 text-white" />
        </div>
      </div>
    </div>
  )
}

function DonutChart({ title, data, total, colorMap, emptyMessage }: {
  title: string; data: Record<string, number>; total: number; colorMap: Record<string, string>; emptyMessage: string
}) {
  const entries = Object.entries(data).filter(([, v]) => v > 0)

  if (entries.length === 0) {
    return (
      <div className="bg-card rounded-lg border border-border shadow-elegant p-5">
        <h3 className="text-sm font-semibold text-foreground mb-4">{title}</h3>
        <div className="flex items-center justify-center h-32 text-muted-foreground text-sm">{emptyMessage}</div>
      </div>
    )
  }

  let cumulativePercent = 0
  const segments = entries.map(([label, value]) => {
    const percent = (value / total) * 100
    const start = cumulativePercent
    cumulativePercent += percent
    return { label, value, percent, color: colorMap[label] || '#94a3b8', strokeDasharray: `${percent} ${100 - percent}`, strokeDashoffset: -start }
  })

  return (
    <div className="bg-card rounded-lg border border-border shadow-elegant p-5">
      <h3 className="text-sm font-semibold text-foreground mb-4">{title}</h3>
      <div className="flex items-center gap-4">
        <div className="relative w-24 h-24 flex-shrink-0">
          <svg viewBox="0 0 36 36" className="w-full h-full -rotate-90">
            <circle cx="18" cy="18" r="15.9" fill="none" stroke="currentColor" className="text-muted/30" strokeWidth="3" />
            {segments.map((seg, i) => (
              <circle key={i} cx="18" cy="18" r="15.9" fill="none" stroke={seg.color} strokeWidth="3"
                strokeDasharray={`${seg.percent} ${100 - seg.percent}`} strokeDashoffset={seg.strokeDashoffset}
                className="transition-all duration-700" />
            ))}
          </svg>
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="text-lg font-bold text-foreground">{total}</span>
          </div>
        </div>
        <div className="flex-1 space-y-1.5">
          {entries.map(([label, value]) => (
            <div key={label} className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: colorMap[label] || '#94a3b8' }} />
                <span className="text-xs text-muted-foreground">{label}</span>
              </div>
              <span className="text-xs font-medium text-foreground">{value}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function MiniCoverage({ reqs, tcs }: { reqs: number; tcs: number }) {
  const pct = reqs > 0 ? Math.min(100, Math.round((tcs / reqs) * 100)) : 0
  const color = pct >= 80 ? 'bg-emerald-500' : pct >= 50 ? 'bg-amber-500' : 'bg-red-500'
  return (
    <div className="w-16">
      <div className="w-full bg-muted rounded-full h-1.5">
        <div className={`h-1.5 rounded-full ${color} transition-all duration-500`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

function StatusBadge({ status }: { status: string }) {
  const config: Record<string, string> = {
    Active: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400',
    Archived: 'bg-muted text-muted-foreground',
    Draft: 'bg-amber-500/10 text-amber-700 dark:text-amber-400',
  }
  return (
    <span className={`px-2 py-0.5 rounded-md text-[11px] font-semibold ${config[status] || config.Draft}`}>
      {status}
    </span>
  )
}

function DashboardSkeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      <div className="bg-muted/30 rounded-xl h-28" />
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="bg-muted/30 rounded-lg h-28" />
        ))}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="bg-muted/30 rounded-lg h-48" />
        ))}
      </div>
      <div className="bg-muted/30 rounded-lg h-64" />
    </div>
  )
}
