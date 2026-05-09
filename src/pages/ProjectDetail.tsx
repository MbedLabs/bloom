import { useEffect, useMemo } from 'react'
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
} from 'lucide-react'

import { defectsApi, docsApi, projectsApi } from '../api/client'
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
    { label: 'Defects', icon: Bug, to: `/projects/${prefix}/defects` },
    { label: 'Traceability', icon: GitBranch, to: `/projects/${prefix}/traceability` },
  ]

  return (
    <div className="animate-fade-in space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center space-x-4">
          <Link to="/projects" className="p-2 hover:bg-accent/50 rounded-md">
            <ArrowLeft className="h-5 w-5 text-muted-foreground" />
          </Link>
          <div>
            <h2 className="text-2xl font-bold text-foreground">{project.name}</h2>
            <p className="text-muted-foreground">{project.prefix}{project.description ? ` - ${project.description}` : ''}</p>
          </div>
        </div>
        <ProjectStatusBadge status={project.status} />
      </div>

      {/* Summary tiles */}
      <div className="grid grid-cols-2 lg:grid-cols-7 gap-4">
        <SummaryTile label="Requirements" value={project.requirement_count} />
        <SummaryTile label="Test Cases" value={project.test_case_count} />
        <SummaryTile label="Specifications" value={specCount} />
        <SummaryTile label="Design" value={project.design_count} />
        <SummaryTile label="Risks" value={project.risk_count} />
        <SummaryTile label="Changes" value={project.change_count} />
        <SummaryTile
          label="Defects"
          value={project.defect_count}
          to={`/projects/${prefix}/defects`}
          accent={openDefectCount > 0 ? 'warning' : undefined}
          subValue={openDefectCount > 0 ? `${openDefectCount} open` : undefined}
        />
      </div>

      {/* Tab / navigation strip */}
      <div className="border-b border-border overflow-x-auto">
        <nav className="flex space-x-6 min-w-max">
          {/* Overview is always the active tab on this page */}
          <span className="flex items-center py-3 px-1 border-b-2 border-primary text-sm font-medium text-primary">
            <Map className="h-4 w-4 mr-2" />
            Overview
          </span>

          {navItems.map((item) => (
            <Link
              key={item.label}
              to={item.to}
              className="flex items-center py-3 px-1 border-b-2 border-transparent text-sm font-medium text-muted-foreground hover:text-foreground hover:border-border transition-colors"
            >
              <item.icon className="h-4 w-4 mr-2" />
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
  subValue,
}: {
  label: string
  value: number
  to?: string
  accent?: 'warning'
  subValue?: string
}) {
  const accentClass =
    accent === 'warning' ? 'border-amber-400/60 bg-amber-50/40 dark:bg-amber-500/5' : ''
  const content = (
    <div
      className={`bg-card rounded-lg border border-border shadow-elegant p-4 transition-colors ${accentClass} ${
        to ? 'hover:bg-accent/40 cursor-pointer' : ''
      }`}
    >
      <div className="text-xs uppercase tracking-wide text-muted-foreground">{label}</div>
      <div className="text-2xl font-bold text-foreground mt-2">{value}</div>
      {subValue && (
        <div className="mt-1 text-xs font-medium text-amber-700 dark:text-amber-400">
          {subValue}
        </div>
      )}
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
