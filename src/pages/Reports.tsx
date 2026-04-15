import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { dashboardApi } from '../api/client'
import { FolderKanban, FileText, CheckCircle, FlaskConical, AlertTriangle, ArrowRight, TrendingUp, Shield } from 'lucide-react'

export default function Reports() {
  const { data: stats, isLoading } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: dashboardApi.getStats,
  })

  const s = stats || {
    total_projects: 0, active_projects: 0, total_requirements: 0,
    total_test_cases: 0, total_documents: 0, total_campaigns: 0,
    active_campaigns: 0, coverage_percent: 0, uncovered_requirements: 0,
    requirement_status_distribution: {}, test_case_status_distribution: {},
    campaign_result_distribution: {}, projects: [],
  }

  const campaignResults = s.campaign_result_distribution
  const totalExecuted = Object.values(campaignResults).reduce((a, b) => a + b, 0)
  const passRate = totalExecuted > 0 ? Math.round(((campaignResults.Passed || 0) / totalExecuted) * 100) : 0

  if (isLoading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="bg-muted/30 rounded-lg h-20" />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-muted/30 rounded-lg h-64" />
          <div className="bg-muted/30 rounded-lg h-64" />
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h2 className="text-2xl font-bold text-foreground">Reports</h2>
        <p className="text-muted-foreground">Cross-project analytics and quality metrics</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <ReportStatCard
          title="Overall Coverage"
          value={`${s.coverage_percent}%`}
          subtitle={`${s.uncovered_requirements} uncovered requirements`}
          icon={Shield}
          color={s.coverage_percent >= 80 ? 'text-emerald-600' : s.coverage_percent >= 50 ? 'text-amber-600' : 'text-red-600'}
        />
        <ReportStatCard
          title="Campaign Pass Rate"
          value={`${passRate}%`}
          subtitle={`${totalExecuted} total executions`}
          icon={TrendingUp}
          color={passRate >= 80 ? 'text-emerald-600' : passRate >= 50 ? 'text-amber-600' : 'text-red-600'}
        />
        <ReportStatCard
          title="Requirements"
          value={s.total_requirements}
          subtitle={`${Object.keys(s.requirement_status_distribution).length} statuses`}
          icon={FileText}
          color="text-primary"
        />
        <ReportStatCard
          title="Test Cases"
          value={s.total_test_cases}
          subtitle={`${s.total_campaigns} campaigns`}
          icon={CheckCircle}
          color="text-cyan-600"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-card rounded-lg border border-border shadow-elegant overflow-hidden">
          <div className="px-5 py-4 border-b border-border">
            <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
              <FileText className="h-4 w-4 text-primary" />
              Requirement Status Breakdown
            </h3>
          </div>
          <div className="p-5">
            {Object.keys(s.requirement_status_distribution).length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-8">No requirements yet</p>
            ) : (
              <div className="space-y-3">
                {Object.entries(s.requirement_status_distribution)
                  .sort(([, a], [, b]) => b - a)
                  .map(([status, count]) => (
                    <HorizontalBar key={status} label={status} value={count} max={s.total_requirements} color={reqColor(status)} />
                  ))}
              </div>
            )}
          </div>
        </div>

        <div className="bg-card rounded-lg border border-border shadow-elegant overflow-hidden">
          <div className="px-5 py-4 border-b border-border">
            <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
              <FlaskConical className="h-4 w-4 text-purple-600" />
              Campaign Results Distribution
            </h3>
          </div>
          <div className="p-5">
            {totalExecuted === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-8">No campaign executions yet</p>
            ) : (
              <div className="space-y-3">
                {Object.entries(campaignResults)
                  .sort(([, a], [, b]) => b - a)
                  .map(([result, count]) => (
                    <HorizontalBar key={result} label={result} value={count} max={totalExecuted} color={resultColor(result)} />
                  ))}
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="bg-card rounded-lg border border-border shadow-elegant overflow-hidden">
        <div className="px-5 py-4 border-b border-border">
          <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
            <FolderKanban className="h-4 w-4 text-primary" />
            Project Health Summary
          </h3>
        </div>
        {s.projects.length === 0 ? (
          <div className="p-12 text-center text-muted-foreground">
            <FolderKanban className="h-8 w-8 mx-auto mb-2 opacity-40" />
            <p className="text-sm">No projects to report on</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-border">
              <thead className="bg-muted/50">
                <tr>
                  <th className="px-5 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Project</th>
                  <th className="px-5 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Status</th>
                  <th className="px-5 py-3 text-center text-xs font-medium text-muted-foreground uppercase">Requirements</th>
                  <th className="px-5 py-3 text-center text-xs font-medium text-muted-foreground uppercase">Test Cases</th>
                  <th className="px-5 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Coverage</th>
                  <th className="px-5 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Health</th>
                  <th className="px-5 py-3 text-right text-xs font-medium text-muted-foreground uppercase"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {s.projects.map((p) => {
                  const cov = p.requirement_count > 0 ? Math.min(100, Math.round((p.test_case_count / p.requirement_count) * 100)) : 0
                  const health = getHealth(p, cov)
                  return (
                    <tr key={p.id} className="hover:bg-accent/30">
                      <td className="px-5 py-3.5">
                        <Link to={`/projects/${p.id}`} className="text-foreground font-medium text-sm hover:text-primary">{p.name}</Link>
                        <p className="text-xs text-muted-foreground">{p.prefix}</p>
                      </td>
                      <td className="px-5 py-3.5">
                        <StatusBadge status={p.status} />
                      </td>
                      <td className="px-5 py-3.5 text-center text-sm text-foreground">{p.requirement_count}</td>
                      <td className="px-5 py-3.5 text-center text-sm text-foreground">{p.test_case_count}</td>
                      <td className="px-5 py-3.5">
                        <div className="flex items-center gap-2">
                          <div className="w-20 bg-muted rounded-full h-1.5">
                            <div
                              className={`h-1.5 rounded-full ${cov >= 80 ? 'bg-emerald-500' : cov >= 50 ? 'bg-amber-500' : 'bg-red-500'}`}
                              style={{ width: `${cov}%` }}
                            />
                          </div>
                          <span className="text-xs text-muted-foreground">{cov}%</span>
                        </div>
                      </td>
                      <td className="px-5 py-3.5">
                        <HealthBadge level={health} />
                      </td>
                      <td className="px-5 py-3.5 text-right">
                        <Link to={`/traceability/${p.id}`} className="text-xs text-primary hover:text-primary/80 inline-flex items-center gap-1">
                          Traceability <ArrowRight className="h-3 w-3" />
                        </Link>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {s.uncovered_requirements > 0 && (
        <div className="bg-amber-500/5 border border-amber-500/20 rounded-lg p-5">
          <div className="flex items-start gap-3">
            <AlertTriangle className="h-5 w-5 text-amber-600 mt-0.5 flex-shrink-0" />
            <div>
              <h3 className="text-sm font-semibold text-foreground">Coverage Attention Needed</h3>
              <p className="text-sm text-muted-foreground mt-1">
                {s.uncovered_requirements} requirement{s.uncovered_requirements !== 1 ? 's' : ''} across all projects have no linked test cases.
                Consider adding test coverage to ensure full lifecycle traceability.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function ReportStatCard({ title, value, subtitle, icon: Icon, color }: {
  title: string; value: number | string; subtitle: string; icon: React.ComponentType<{ className?: string }>; color: string
}) {
  return (
    <div className="bg-card rounded-lg border border-border shadow-elegant p-5">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">{title}</p>
          <p className={`text-3xl font-bold mt-2 ${color}`}>{value}</p>
          <p className="text-xs text-muted-foreground mt-1">{subtitle}</p>
        </div>
        <Icon className={`h-8 w-8 ${color} opacity-30`} />
      </div>
    </div>
  )
}

function HorizontalBar({ label, value, max, color }: { label: string; value: number; max: number; color: string }) {
  const pct = max > 0 ? (value / max) * 100 : 0
  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs font-medium text-foreground">{label}</span>
        <span className="text-xs text-muted-foreground">{value} ({Math.round(pct)}%)</span>
      </div>
      <div className="w-full bg-muted rounded-full h-2.5">
        <div className="h-2.5 rounded-full transition-all duration-500" style={{ width: `${pct}%`, backgroundColor: color }} />
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
  return <span className={`px-2 py-0.5 rounded-md text-[11px] font-semibold ${config[status] || config.Draft}`}>{status}</span>
}

function HealthBadge({ level }: { level: string }) {
  const config: Record<string, { colors: string; icon: string }> = {
    good: { colors: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400', icon: 'Good' },
    warning: { colors: 'bg-amber-500/10 text-amber-700 dark:text-amber-400', icon: 'Warning' },
    critical: { colors: 'bg-red-500/10 text-red-700 dark:text-red-400', icon: 'Critical' },
    empty: { colors: 'bg-muted text-muted-foreground', icon: 'N/A' },
  }
  const cfg = config[level] || config.empty
  return <span className={`px-2 py-0.5 rounded-md text-[11px] font-semibold ${cfg.colors}`}>{cfg.icon}</span>
}

function getHealth(p: { requirement_count: number; test_case_count: number; status: string }, cov: number): string {
  if (p.requirement_count === 0) return 'empty'
  if (cov >= 80 && p.status === 'Active') return 'good'
  if (cov >= 50) return 'warning'
  return 'critical'
}

function reqColor(status: string): string {
  const m: Record<string, string> = { Draft: '#94a3b8', Review: '#f59e0b', Approved: '#3b82f6', Implemented: '#14b8a6', Verified: '#10b981', Rejected: '#ef4444' }
  return m[status] || '#94a3b8'
}

function resultColor(result: string): string {
  const m: Record<string, string> = { Passed: '#10b981', Failed: '#ef4444', Blocked: '#f59e0b', Skipped: '#94a3b8' }
  return m[result] || '#94a3b8'
}
