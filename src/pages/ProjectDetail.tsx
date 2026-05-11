import { useEffect, useMemo, type ReactNode } from 'react'
import { Link, useParams, useSearchParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  ArrowLeft,
  BookOpen,
  Bug,
  CheckCircle,
  FileText,
  FlaskConical,
  GitBranch,
  GitPullRequest,
  Map,
  PenTool,
  AlertTriangle,
  Pencil,
} from 'lucide-react'

import { defectsApi, docsApi, projectsApi } from '../api/client'
import { useAuth } from '../contexts/AuthContext'
import ProjectDocTopology from '../components/ProjectDocTopology'

const OPEN_DEFECT_STATUSES = new Set(['Open', 'Triaged', 'In Progress', 'Resolved', 'Verified'])

// Legacy ?tab= values → modern route within the project
const LEGACY_TAB_ROUTES: Record<string, string> = {
  'requirements': 'docs?type=REQ',
  'test-cases': 'docs?type=TC',
  'specifications': 'docs?type=SPEC',
  'protocols': 'docs?type=PROT',
  'reports': 'docs?type=RPT',
  'standards': 'docs?type=STD',
  'design': 'docs?type=DES',
  'risks': 'docs?type=RSK',
  'changes': 'docs?type=CHG',
  'test-concepts': 'docs?type=TCO',
  'traceability': 'traceability',
  'defects': 'defects',
  'campaigns': 'campaigns',
}

function Beaker(props: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={props.className}>
      <path d="M4.5 3h15" /><path d="M6 3v16a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V3" /><path d="M6 14h12" />
    </svg>
  )
}

type NavItem = {
  label: string
  icon: React.ComponentType<{ className?: string }>
  to: string
}

export default function ProjectDetail() {
  const { prefix } = useParams<{ prefix: string }>()
  const navigate = useNavigate()
  const { user } = useAuth()
  const [searchParams] = useSearchParams()

  // Redirect legacy ?tab= URLs to the equivalent sidebar route
  useEffect(() => {
    const tab = searchParams.get('tab')
    if (tab && tab !== 'overview') {
      const route = LEGACY_TAB_ROUTES[tab]
      if (route) navigate(`/projects/${prefix}/${route}`, { replace: true })
    }
  }, [searchParams, prefix, navigate])

  const { data: project, isLoading: projectLoading } = useQuery({
    queryKey: ['project-by-prefix', prefix],
    queryFn: () => projectsApi.getByPrefix(prefix!),
    enabled: !!prefix,
  })

  const projectId = project?.id || 0

  const { data: docs } = useQuery({
    queryKey: ['project-docs-shell', prefix],
    queryFn: () => docsApi.list(prefix!, { includeLinkCounts: true }),
    enabled: !!prefix,
  })

  const { data: defects } = useQuery({
    queryKey: ['defects', projectId],
    queryFn: () => defectsApi.list(projectId),
    enabled: !!projectId,
  })

  const specCount = useMemo(() => docs?.filter((d) => d.doc_type === 'SPEC').length ?? 0, [docs])
  const openDefectCount = useMemo(
    () => defects?.filter((d) => OPEN_DEFECT_STATUSES.has(d.status)).length ?? 0,
    [defects]
  )
  const closedDefectCount = useMemo(() => {
    if (!defects) return null
    return defects.length - openDefectCount
  }, [defects, openDefectCount])

  if (projectLoading) {
    return <div className="flex items-center justify-center h-64 text-muted-foreground">Loading...</div>
  }

  if (!project) {
    return (
      <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-6 text-center">
        <h3 className="text-lg font-medium text-destructive">Project Not Found</h3>
        <Link to="/projects" className="mt-4 inline-block text-primary hover:text-primary/80">
          &larr; Back to Projects
        </Link>
      </div>
    )
  }

  const navItems: NavItem[] = [
    { label: 'Requirements', icon: FileText, to: `/projects/${prefix}/docs?type=REQ` },
    { label: 'Test Cases', icon: CheckCircle, to: `/projects/${prefix}/docs?type=TC` },
    { label: 'Specifications', icon: BookOpen, to: `/projects/${prefix}/docs?type=SPEC` },
    { label: 'Protocols', icon: BookOpen, to: `/projects/${prefix}/docs?type=PROT` },
    { label: 'Reports', icon: BookOpen, to: `/projects/${prefix}/docs?type=RPT` },
    { label: 'Standards', icon: BookOpen, to: `/projects/${prefix}/docs?type=STD` },
    { label: 'Design', icon: PenTool, to: `/projects/${prefix}/docs?type=DES` },
    { label: 'Risks', icon: AlertTriangle, to: `/projects/${prefix}/docs?type=RSK` },
    { label: 'Changes', icon: GitPullRequest, to: `/projects/${prefix}/docs?type=CHG` },
    { label: 'Test Concepts', icon: Beaker, to: `/projects/${prefix}/docs?type=TCO` },
    { label: 'Campaigns', icon: FlaskConical, to: `/projects/${prefix}/campaigns` },
    { label: 'Defects', icon: Bug, to: `/projects/${prefix}/docs?type=DEF` },
    { label: 'Traceability', icon: GitBranch, to: `/projects/${prefix}/traceability` },
  ]

  return (
    <div className="animate-fade-in space-y-3.5">
      {/* Header */}
      <div className="flex items-center justify-between gap-2.5">
        <div className="flex items-center space-x-2.5">
          <Link to="/projects" className="p-1 hover:bg-accent/50 rounded-md">
            <ArrowLeft className="h-5 w-5 text-muted-foreground" />
          </Link>
          <div>
            <h2 className="text-lg font-bold text-foreground">{project.name}</h2>
            <p className="text-muted-foreground">{project.prefix}{project.description ? ` - ${project.description}` : ''}</p>
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {user?.role === 'admin' && (
            <Link
              to={`/projects/${prefix}/edit`}
              className="inline-flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-xs font-medium text-foreground hover:bg-accent/50 transition-colors"
            >
              <Pencil className="h-3.5 w-3.5" />
              Edit project
            </Link>
          )}
          <ProjectStatusBadge status={project.status} />
        </div>
      </div>

      {/* Summary tiles */}
      <div className="grid grid-cols-2 lg:grid-cols-4 xl:grid-cols-7 gap-2.5">
        <SummaryTile label="Requirements" value={project.requirement_count} to={`/projects/${prefix}/docs?type=REQ`} />
        <SummaryTile label="Test Cases" value={project.test_case_count} to={`/projects/${prefix}/docs?type=TC`} />
        <SummaryTile label="Specifications" value={specCount} to={`/projects/${prefix}/docs?type=SPEC`} />
        <SummaryTile label="Design" value={project.design_count} to={`/projects/${prefix}/docs?type=DES`} />
        <SummaryTile label="Risks" value={project.risk_count} to={`/projects/${prefix}/docs?type=RSK`} />
        <SummaryTile label="Changes" value={project.change_count} to={`/projects/${prefix}/docs?type=CHG`} />
          <SummaryTile
            label="Defects"
            value={defects?.length ?? project.defect_count}
            to={`/projects/${prefix}/docs?type=DEF`}
            accent={openDefectCount > 0 ? 'warning' : undefined}
            labelMeta={
              closedDefectCount != null ? (
                <span className="inline-flex flex-wrap items-center justify-end gap-x-1 text-[10px] font-semibold tabular-nums leading-snug">
                  <span
                    className={
                      openDefectCount > 0
                        ? 'text-amber-700 dark:text-amber-400'
                        : 'text-muted-foreground'
                    }
                  >
                    {openDefectCount} open
                  </span>
                  <span className="text-muted-foreground">·</span>
                  <span className="text-muted-foreground">{closedDefectCount} closed</span>
                </span>
              ) : undefined
            }
          />
      </div>

      {/* Tab / navigation strip */}
      <div className="border-b border-border">
        <nav className="flex flex-wrap gap-1">
          <span className="flex items-center py-2.5 px-2 border-b-2 border-primary text-sm font-medium text-primary whitespace-nowrap">
            <Map className="h-4 w-4 mr-1.5" />
            Overview
          </span>

          {navItems.map((item) => (
            <Link
              key={item.label}
              to={item.to}
              className="flex items-center py-2.5 px-2 border-b-2 border-transparent text-sm font-medium text-muted-foreground hover:text-foreground hover:border-border transition-colors whitespace-nowrap"
            >
              <item.icon className="h-4 w-4 mr-1.5" />
              {item.label}
            </Link>
          ))}
        </nav>
      </div>

      {/* Topology map */}
      <ProjectDocTopology projectId={projectId} prefix={prefix || ''} />
    </div>
  )
}

function SummaryTile({
  label,
  value,
  to,
  accent,
  labelMeta,
}: {
  label: string
  value: number
  to?: string
  accent?: 'warning'
  /** Shown on the label row (not under the total) so tile height stays uniform */
  labelMeta?: ReactNode
}) {
  const accentClass =
    accent === 'warning' ? 'border-amber-400/60 bg-amber-50/40 dark:bg-amber-500/5' : ''
  const content = (
      <div
        className={`bg-card rounded-lg border border-border shadow-elegant p-3 transition-colors ${accentClass} ${
          to ? 'hover:bg-accent/40 cursor-pointer' : ''
        }`}
      >
      <div className="flex items-start justify-between gap-2">
        <div className="text-xs uppercase tracking-wide text-muted-foreground leading-snug">{label}</div>
        {labelMeta ? (
          <div className="shrink-0 pt-0.5 text-right">{labelMeta}</div>
        ) : null}
      </div>
      <div className="text-xl font-bold text-foreground mt-1.5 tabular-nums">{value}</div>
    </div>
  )
  return to ? <Link to={to}>{content}</Link> : content
}

function ProjectStatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    Active: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400',
    Archived: 'bg-gray-500/10 text-gray-700 dark:text-gray-400',
    Draft: 'bg-amber-500/10 text-amber-700 dark:text-amber-400',
  }
  return <span className={`px-2 py-1 rounded-full text-xs font-medium ${colors[status] || colors.Draft}`}>{status}</span>
}
