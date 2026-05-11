import { useMemo } from 'react'
import { Link, useParams } from 'react-router-dom'
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

import { docsApi, projectsApi } from '../api/client'
import { useAuth } from '../contexts/AuthContext'
import { docRegistryListUrl } from '../lib/docRegistryParams'
import ProjectDocTopology from '../components/ProjectDocTopology'

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
  const { user } = useAuth()

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

  const specCount = useMemo(() => docs?.filter((d) => d.doc_type === 'SPEC').length ?? 0, [docs])

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
    { label: 'Requirements', icon: FileText, to: docRegistryListUrl(prefix!, 'REQ') },
    { label: 'Test Cases', icon: CheckCircle, to: docRegistryListUrl(prefix!, 'TC') },
    { label: 'Specifications', icon: BookOpen, to: docRegistryListUrl(prefix!, 'SPEC') },
    { label: 'Protocols', icon: BookOpen, to: docRegistryListUrl(prefix!, 'PROT') },
    { label: 'Reports', icon: BookOpen, to: docRegistryListUrl(prefix!, 'RPT') },
    { label: 'Standards', icon: BookOpen, to: docRegistryListUrl(prefix!, 'STD') },
    { label: 'Design', icon: PenTool, to: docRegistryListUrl(prefix!, 'DES') },
    { label: 'Risks', icon: AlertTriangle, to: docRegistryListUrl(prefix!, 'RSK') },
    { label: 'Changes', icon: GitPullRequest, to: docRegistryListUrl(prefix!, 'CHG') },
    { label: 'Test Concepts', icon: Beaker, to: docRegistryListUrl(prefix!, 'TCO') },
    { label: 'Campaigns', icon: FlaskConical, to: docRegistryListUrl(prefix!, 'CMP') },
    { label: 'Defects', icon: Bug, to: docRegistryListUrl(prefix!, 'DEF') },
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
        <SummaryTile label="Requirements" value={project.requirement_count} to={docRegistryListUrl(prefix!, 'REQ')} />
        <SummaryTile label="Test Cases" value={project.test_case_count} to={docRegistryListUrl(prefix!, 'TC')} />
        <SummaryTile label="Specifications" value={specCount} to={docRegistryListUrl(prefix!, 'SPEC')} />
        <SummaryTile label="Design" value={project.design_count} to={docRegistryListUrl(prefix!, 'DES')} />
        <SummaryTile label="Risks" value={project.risk_count} to={docRegistryListUrl(prefix!, 'RSK')} />
        <SummaryTile label="Changes" value={project.change_count} to={docRegistryListUrl(prefix!, 'CHG')} />
        <SummaryTile label="Defects" value={project.defect_count} to={docRegistryListUrl(prefix!, 'DEF')} />
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

function SummaryTile({ label, value, to }: { label: string; value: number; to?: string }) {
  const content = (
    <div
      className={`bg-card rounded-lg border border-border shadow-elegant p-3 transition-colors ${
        to ? 'hover:bg-accent/40 cursor-pointer' : ''
      }`}
    >
      <div className="text-xs uppercase tracking-wide text-muted-foreground leading-snug">{label}</div>
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
