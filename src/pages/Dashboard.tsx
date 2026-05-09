import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import {
  AlertTriangle,
  ArrowRight,
  BarChart3,
  Bug,
  CheckCircle,
  CircleDot,
  FileText,
  FlaskConical,
  FolderKanban,
  GitBranch,
  Plus,
} from 'lucide-react'

import { dashboardApi, docsApi, projectsApi, type DocShell, type Project } from '../api/client'
import { DOC_TYPE_COLORS, DOC_TYPE_LABELS, type DocType } from '../types/doc'

const CONTROLLED_DOC_TYPES: DocType[] = ['REQ', 'SPEC', 'TC', 'TCO', 'PROT', 'DES', 'RSK', 'CHG', 'RPT', 'STD']

type ProjectDocBundle = {
  project: Project
  docs: DocShell[]
}

export default function Dashboard() {
  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: dashboardApi.getStats,
  })

  const { data: projects, isLoading: projectsLoading } = useQuery({
    queryKey: ['projects'],
    queryFn: projectsApi.list,
  })

  const projectPrefixes = useMemo(() => projects?.map((project) => project.prefix).sort().join('|') ?? '', [projects])

  const { data: projectDocBundles, isLoading: docsLoading } = useQuery({
    queryKey: ['dashboard-controlled-docs', projectPrefixes],
    queryFn: async (): Promise<ProjectDocBundle[]> => {
      if (!projects || projects.length === 0) return []
      return Promise.all(
        projects.map(async (project) => ({
          project,
          docs: await docsApi.list(project.prefix, { includeLinkCounts: true }),
        }))
      )
    },
    enabled: !!projects,
  })

  if (statsLoading || projectsLoading || docsLoading) {
    return <DashboardSkeleton />
  }

  const s = stats || {
    total_projects: 0,
    active_projects: 0,
    total_requirements: 0,
    total_test_cases: 0,
    total_campaigns: 0,
    active_campaigns: 0,
    coverage_percent: 0,
    uncovered_requirements: 0,
    requirement_status_distribution: {},
    test_case_status_distribution: {},
    campaign_result_distribution: {},
    total_defects: 0,
    open_defects: 0,
    defect_severity_distribution: {},
    defect_status_distribution: {},
    projects: [],
  }

  const portfolioProjects = projects ?? []
  const docBundles = projectDocBundles ?? []
  const docsByProject = new Map(docBundles.map((bundle) => [bundle.project.id, bundle.docs]))
  const allDocs = docBundles.flatMap((bundle) => bundle.docs)

  const fallbackKindCounts = buildFallbackKindCounts(portfolioProjects, s.total_requirements, s.total_test_cases)
  const kindCounts = allDocs.length > 0 ? countByDocType(allDocs) : fallbackKindCounts
  const statusDistribution = allDocs.length > 0 ? countByStatus(allDocs) : mergeDistributions(s.requirement_status_distribution, s.test_case_status_distribution)
  const totalControlledDocs = sumRecord(kindCounts)
  const activeProjects = portfolioProjects.filter((project) => project.status === 'Active').length || s.active_projects
  const coveredRequirements = Math.max(0, s.total_requirements - s.uncovered_requirements)
  const coverageTone = getCoverageTone(s.coverage_percent)
  const suspectLinks = allDocs.reduce((total, doc) => total + doc.suspect_links, 0)
  const linkedDocs = allDocs.filter((doc) => doc.incoming_links + doc.outgoing_links > 0).length
  const usedKindCount = CONTROLLED_DOC_TYPES.filter((type) => (kindCounts[type] ?? 0) > 0).length

  return (
    <div className="animate-fade-in space-y-5">
      <header className="flex flex-col gap-4 border-b border-border pb-5 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            <CircleDot className="h-3.5 w-3.5 text-primary" />
            Bloom PLM
          </div>
          <h2 className="mt-2 text-2xl font-semibold tracking-tight text-foreground">Bloom Dashboard</h2>
          <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
            Portfolio health across requirements, specifications, protocols, test assets, designs, risks, changes, reports, and standards.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Link
            to="/projects"
            className="inline-flex items-center gap-2 rounded-md border border-input bg-background px-3 py-2 text-sm font-medium text-foreground transition-colors hover:bg-accent"
          >
            <FolderKanban className="h-4 w-4" />
            Projects
          </Link>
          <Link
            to="/projects"
            className="inline-flex items-center gap-2 rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
          >
            <Plus className="h-4 w-4" />
            New Project
          </Link>
        </div>
      </header>

      <section className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-5">
        <MetricCard title="Projects" value={portfolioProjects.length || s.total_projects} detail={`${activeProjects} active`} icon={FolderKanban} />
        <MetricCard title="Docs" value={totalControlledDocs} detail={`${usedKindCount} of ${CONTROLLED_DOC_TYPES.length} kinds in use`} icon={FileText} />
        <MetricCard title="Links" value={linkedDocs} detail={`${suspectLinks} suspect links`} icon={GitBranch} />
        <MetricCard title="Campaigns" value={s.total_campaigns} detail={`${s.active_campaigns} active`} icon={FlaskConical} />
        <MetricCard
          title="Defects"
          value={s.total_defects}
          detail={`${s.open_defects} open`}
          icon={Bug}
          tone={s.open_defects > 0 ? 'warning' : 'default'}
        />
      </section>

      <section className="grid grid-cols-1 gap-5 xl:grid-cols-[minmax(0,2fr)_minmax(360px,1fr)]">
        <div className="rounded-lg border border-border bg-card">
          <div className="flex flex-col gap-3 border-b border-border px-5 py-4 md:flex-row md:items-center md:justify-between">
            <div>
              <h3 className="text-sm font-semibold text-foreground">Project Document Scope</h3>
              <p className="mt-1 text-xs text-muted-foreground">Counts come from the canonical project docs registry.</p>
            </div>
            <Link to="/projects" className="inline-flex items-center gap-1 text-sm font-medium text-primary hover:text-primary/80">
              View projects
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>

          {portfolioProjects.length === 0 ? (
            <EmptyState />
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-border">
                <thead className="bg-muted/40">
                  <tr>
                    <Th>Project</Th>
                    <Th>Status</Th>
                    <Th>Docs</Th>
                    <Th>REQ</Th>
                    <Th>SPEC/PROT</Th>
                    <Th>RSK/CHG</Th>
                    <Th>Suspect</Th>
                    <Th />
                  </tr>
                </thead>
                <tbody className="divide-y divide-border bg-card">
                  {portfolioProjects.slice(0, 8).map((project) => {
                    const projectDocs = docsByProject.get(project.id) ?? []
                    const projectKindCounts = projectDocs.length > 0 ? countByDocType(projectDocs) : countProjectFallbackKinds(project)
                    const projectSuspectLinks = projectDocs.reduce((total, doc) => total + doc.suspect_links, 0)
                    const projectDocCount = sumRecord(projectKindCounts)
                    return (
                      <tr key={project.id} className="transition-colors hover:bg-accent/50">
                        <Td>
                          <div className="min-w-0">
                            <Link to={`/projects/${project.prefix}/docs`} className="font-medium text-foreground hover:text-primary">
                              {project.name}
                            </Link>
                            <div className="mt-0.5 font-mono text-xs text-muted-foreground">{project.prefix}</div>
                          </div>
                        </Td>
                        <Td><StatusBadge status={project.status} /></Td>
                        <Td>{projectDocCount}</Td>
                        <Td>{projectKindCounts.REQ}</Td>
                        <Td>{projectKindCounts.SPEC + projectKindCounts.PROT}</Td>
                        <Td>{projectKindCounts.RSK + projectKindCounts.CHG}</Td>
                        <Td>
                          <span className={projectSuspectLinks > 0 ? 'font-medium text-red-600 dark:text-red-400' : 'text-muted-foreground'}>
                            {projectSuspectLinks}
                          </span>
                        </Td>
                        <Td>
                          <Link
                            to={`/projects/${project.prefix}/docs`}
                            aria-label={`Open ${project.name} documents`}
                            className="inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
                          >
                            <ArrowRight className="h-4 w-4" />
                          </Link>
                        </Td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <aside className="space-y-5">
          <div className="rounded-lg border border-border bg-card p-5">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h3 className="text-sm font-semibold text-foreground">Verification Coverage</h3>
                <p className="mt-1 text-xs text-muted-foreground">
                  {coveredRequirements} covered · {s.uncovered_requirements} uncovered requirements
                </p>
              </div>
              <div className={`rounded-md px-2.5 py-1 text-sm font-semibold ${coverageTone.badge}`}>{s.coverage_percent}%</div>
            </div>
            <div className="mt-5 h-2 overflow-hidden rounded-full bg-muted">
              <div className={`h-full rounded-full ${coverageTone.bar}`} style={{ width: `${s.coverage_percent}%` }} />
            </div>
            <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
              <SignalStat label="Covered" value={coveredRequirements} icon={CheckCircle} />
              <SignalStat label="At risk" value={s.uncovered_requirements} icon={AlertTriangle} />
            </div>
          </div>

          <DocKindPanel kindCounts={kindCounts} total={totalControlledDocs} />

          <DistributionPanel
            title="Document Status"
            icon={BarChart3}
            data={statusDistribution}
            total={sumRecord(statusDistribution)}
            emptyMessage="No controlled documents yet"
            colorMap={{
              Draft: 'bg-slate-400',
              Review: 'bg-amber-500',
              Approved: 'bg-emerald-500',
              Active: 'bg-emerald-500',
              Final: 'bg-blue-500',
              Implemented: 'bg-teal-500',
              Verified: 'bg-emerald-600',
              Rejected: 'bg-red-500',
              Obsolete: 'bg-slate-500',
              Deprecated: 'bg-red-500',
              Superseded: 'bg-orange-500',
            }}
          />
        </aside>
      </section>

      <section className="grid grid-cols-1 gap-5 lg:grid-cols-3">
        <DistributionPanel
          title="Campaign Results"
          icon={FlaskConical}
          data={s.campaign_result_distribution}
          total={Object.values(s.campaign_result_distribution).reduce((a, b) => a + b, 0)}
          emptyMessage="No campaign results yet"
          colorMap={{
            Passed: 'bg-emerald-500',
            Failed: 'bg-red-500',
            Blocked: 'bg-amber-500',
            Skipped: 'bg-slate-400',
          }}
        />

        <DistributionPanel
          title="Open Defects by Severity"
          icon={Bug}
          data={s.defect_severity_distribution}
          total={Object.values(s.defect_severity_distribution).reduce((a, b) => a + b, 0)}
          emptyMessage="No open defects"
          colorMap={{
            Critical: 'bg-red-600',
            High: 'bg-red-500',
            Medium: 'bg-amber-500',
            Low: 'bg-emerald-500',
          }}
        />

        <div className="rounded-lg border border-border bg-card p-5">
          <div className="flex items-center gap-2">
            <GitBranch className="h-4 w-4 text-primary" />
            <h3 className="text-sm font-semibold text-foreground">Traceability Focus</h3>
          </div>
          <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
            <TraceabilityTile label="Coverage" value={`${s.coverage_percent}%`} tone={coverageTone.text} />
            <TraceabilityTile label="Suspect links" value={suspectLinks} tone={suspectLinks > 0 ? 'text-red-600 dark:text-red-400' : 'text-foreground'} />
            <TraceabilityTile label="Linked docs" value={linkedDocs} tone="text-foreground" />
          </div>
        </div>
      </section>
    </div>
  )
}

function MetricCard({ title, value, detail, icon: Icon, tone = 'default' }: {
  title: string
  value: number | string
  detail: string
  icon: React.ComponentType<{ className?: string }>
  tone?: 'default' | 'warning'
}) {
  const isWarning = tone === 'warning'
  const cardClass = isWarning
    ? 'rounded-lg border border-amber-400/60 bg-amber-50/40 p-4 dark:bg-amber-500/5'
    : 'rounded-lg border border-border bg-card p-4'
  const iconClass = isWarning
    ? 'rounded-md bg-amber-500/10 p-2 text-amber-700 dark:text-amber-400'
    : 'rounded-md bg-primary/10 p-2 text-primary'
  const detailClass = isWarning
    ? 'mt-1 text-xs font-medium text-amber-700 dark:text-amber-400'
    : 'mt-1 text-xs text-muted-foreground'
  return (
    <div className={cardClass}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{title}</p>
          <p className="mt-2 text-2xl font-semibold text-foreground">{value}</p>
          <p className={detailClass}>{detail}</p>
        </div>
        <div className={iconClass}>
          <Icon className="h-4 w-4" />
        </div>
      </div>
    </div>
  )
}

function DocKindPanel({ kindCounts, total }: { kindCounts: Record<DocType, number>; total: number }) {
  return (
    <div className="rounded-lg border border-border bg-card p-5">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <FileText className="h-4 w-4 text-primary" />
          <h3 className="text-sm font-semibold text-foreground">Controlled Document Kinds</h3>
        </div>
        <span className="text-xs text-muted-foreground">{total} total</span>
      </div>
      <div className="mt-5 grid grid-cols-2 gap-2">
        {CONTROLLED_DOC_TYPES.map((type) => (
          <div
            key={type}
            className="rounded-md border border-border bg-background/60 p-3"
          >
            <div className="flex items-center justify-between gap-2">
              <span className={`rounded px-1.5 py-0.5 text-[11px] font-semibold ${DOC_TYPE_COLORS[type]}`}>{type}</span>
              <span className="text-sm font-semibold text-foreground">{kindCounts[type] ?? 0}</span>
            </div>
            <div className="mt-2 truncate text-xs text-muted-foreground">{DOC_TYPE_LABELS[type]}</div>
          </div>
        ))}
      </div>
    </div>
  )
}

function DistributionPanel({ title, icon: Icon, data, total, emptyMessage, colorMap }: {
  title: string
  icon: React.ComponentType<{ className?: string }>
  data: Record<string, number>
  total: number
  emptyMessage: string
  colorMap: Record<string, string>
}) {
  const entries = Object.entries(data).filter(([, value]) => value > 0)

  return (
    <div className="rounded-lg border border-border bg-card p-5">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Icon className="h-4 w-4 text-primary" />
          <h3 className="text-sm font-semibold text-foreground">{title}</h3>
        </div>
        <span className="text-xs text-muted-foreground">{total} total</span>
      </div>

      {entries.length === 0 ? (
        <div className="mt-5 rounded-md border border-dashed border-border p-5 text-center text-sm text-muted-foreground">{emptyMessage}</div>
      ) : (
        <div className="mt-5 space-y-3">
          {entries.map(([label, value]) => {
            const percent = total > 0 ? Math.round((value / total) * 100) : 0
            return (
              <div key={label}>
                <div className="mb-1 flex items-center justify-between gap-3 text-xs">
                  <span className="font-medium text-foreground">{label}</span>
                  <span className="text-muted-foreground">{value} · {percent}%</span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-muted">
                  <div className={`h-full rounded-full ${colorMap[label] || 'bg-slate-400'}`} style={{ width: `${percent}%` }} />
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

function SignalStat({ label, value, icon: Icon }: { label: string; value: number; icon: React.ComponentType<{ className?: string }> }) {
  return (
    <div className="rounded-md border border-border bg-background/60 p-3">
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <Icon className="h-3.5 w-3.5" />
        {label}
      </div>
      <div className="mt-2 text-lg font-semibold text-foreground">{value}</div>
    </div>
  )
}

function TraceabilityTile({ label, value, tone }: { label: string; value: number | string; tone: string }) {
  return (
    <div className="rounded-md border border-border bg-background/60 p-4">
      <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</div>
      <div className={`mt-2 text-xl font-semibold ${tone}`}>{value}</div>
    </div>
  )
}

function StatusBadge({ status }: { status: string }) {
  const config: Record<string, string> = {
    Active: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300',
    Archived: 'border-border bg-muted text-muted-foreground',
    Draft: 'border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-300',
  }
  return (
    <span className={`inline-flex rounded-md border px-2 py-0.5 text-xs font-medium ${config[status] || config.Draft}`}>
      {status}
    </span>
  )
}

function EmptyState() {
  return (
    <div className="p-12 text-center">
      <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10 text-primary">
        <FolderKanban className="h-6 w-6" />
      </div>
      <h3 className="mt-4 text-sm font-semibold text-foreground">No Projects Yet</h3>
      <p className="mt-1 text-sm text-muted-foreground">Create a project to start managing controlled documents.</p>
      <Link
        to="/projects"
        className="mt-4 inline-flex items-center gap-2 rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
      >
        <Plus className="h-4 w-4" />
        Create Project
      </Link>
    </div>
  )
}

function Th({ children }: { children?: React.ReactNode }) {
  return <th className="px-5 py-3 text-left text-xs font-medium uppercase tracking-wide text-muted-foreground">{children}</th>
}

function Td({ children }: { children: React.ReactNode }) {
  return <td className="whitespace-nowrap px-5 py-3.5 text-sm text-muted-foreground">{children}</td>
}

function DashboardSkeleton() {
  return (
    <div className="animate-pulse space-y-5">
      <div className="h-24 rounded-lg bg-muted/50" />
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-28 rounded-lg bg-muted/50" />
        ))}
      </div>
      <div className="grid grid-cols-1 gap-5 xl:grid-cols-[minmax(0,2fr)_minmax(360px,1fr)]">
        <div className="h-96 rounded-lg bg-muted/50" />
        <div className="space-y-5">
          <div className="h-40 rounded-lg bg-muted/50" />
          <div className="h-48 rounded-lg bg-muted/50" />
        </div>
      </div>
    </div>
  )
}

function isDocType(value: string): value is DocType {
  return CONTROLLED_DOC_TYPES.includes(value as DocType)
}

function emptyKindCounts(): Record<DocType, number> {
  return CONTROLLED_DOC_TYPES.reduce((acc, type) => {
    acc[type] = 0
    return acc
  }, {} as Record<DocType, number>)
}

function countByDocType(docs: DocShell[]): Record<DocType, number> {
  const counts = emptyKindCounts()
  docs.forEach((doc) => {
    if (isDocType(doc.doc_type)) {
      counts[doc.doc_type] += 1
    }
  })
  return counts
}

function countByStatus(docs: DocShell[]): Record<string, number> {
  return docs.reduce((acc, doc) => {
    acc[doc.status] = (acc[doc.status] ?? 0) + 1
    return acc
  }, {} as Record<string, number>)
}

function countProjectFallbackKinds(project: Project): Record<DocType, number> {
  const counts = emptyKindCounts()
  counts.REQ = project.requirement_count
  counts.TC = project.test_case_count
  counts.DES = project.design_count
  counts.RSK = project.risk_count
  counts.CHG = project.change_count
  counts.TCO = project.test_concept_count
  return counts
}

function buildFallbackKindCounts(projects: Project[], requirementTotal: number, testCaseTotal: number): Record<DocType, number> {
  const counts = emptyKindCounts()
  counts.REQ = requirementTotal
  counts.TC = testCaseTotal
  projects.forEach((project) => {
    counts.DES += project.design_count
    counts.RSK += project.risk_count
    counts.CHG += project.change_count
    counts.TCO += project.test_concept_count
  })
  return counts
}

function mergeDistributions(...distributions: Record<string, number>[]): Record<string, number> {
  return distributions.reduce((acc, distribution) => {
    Object.entries(distribution).forEach(([status, count]) => {
      acc[status] = (acc[status] ?? 0) + count
    })
    return acc
  }, {} as Record<string, number>)
}

function sumRecord(record: Record<string, number>) {
  return Object.values(record).reduce((total, value) => total + value, 0)
}

function getCoverageTone(coverage: number) {
  if (coverage >= 80) {
    return {
      badge: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300',
      bar: 'bg-emerald-500',
      text: 'text-emerald-700 dark:text-emerald-300',
    }
  }

  if (coverage >= 50) {
    return {
      badge: 'bg-amber-500/10 text-amber-700 dark:text-amber-300',
      bar: 'bg-amber-500',
      text: 'text-amber-700 dark:text-amber-300',
    }
  }

  return {
    badge: 'bg-red-500/10 text-red-700 dark:text-red-300',
    bar: 'bg-red-500',
    text: 'text-red-700 dark:text-red-300',
  }
}
