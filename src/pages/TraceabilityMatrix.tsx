import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { traceabilityApi, projectsApi } from '../api/client'
import { docUrl } from '../types/doc'
import { ArrowLeft, CheckCircle, AlertCircle, XCircle, ExternalLink, Shield, Filter, ArrowUpDown, GitBranch, AlertTriangle } from 'lucide-react'

export default function TraceabilityMatrix() {
  const { prefix } = useParams<{ prefix: string }>()
  const [coverageFilter, setCoverageFilter] = useState('')
  const [priorityFilter, setPriorityFilter] = useState('')
  const [sortBy, setSortBy] = useState('req_id')
  const [showGaps, setShowGaps] = useState(false)

  const { data: project } = useQuery({
    queryKey: ['project-by-prefix', prefix],
    queryFn: () => projectsApi.getByPrefix(prefix!),
    enabled: !!prefix,
  })

  const projId = project?.id || 0

  const { data: matrix, isLoading, error } = useQuery({
    queryKey: ['traceability', projId, coverageFilter, priorityFilter, sortBy],
    queryFn: () => traceabilityApi.getMatrix(projId, {
      coverage_filter: coverageFilter || undefined,
      priority_filter: priorityFilter || undefined,
      sort_by: sortBy,
    }),
    enabled: !!projId,
  })

  const { data: gapReport } = useQuery({
    queryKey: ['coverage-gaps', projId],
    queryFn: () => traceabilityApi.getCoverageGaps(projId),
    enabled: !!projId && showGaps,
  })

  const totalRequirements = matrix?.length || 0
  const covered = matrix?.filter(m => m.coverage_status === 'Covered').length || 0
  const partial = matrix?.filter(m => m.coverage_status === 'Partial').length || 0
  const uncovered = matrix?.filter(m => m.coverage_status === 'Uncovered').length || 0
  const coveragePercent = totalRequirements > 0
    ? Math.round(((covered + partial) / totalRequirements) * 100)
    : 0
  const totalTestCases = matrix?.reduce((sum, m) => sum + m.linked_test_cases.length, 0) || 0

  if (isLoading) {
    return <div className="flex items-center justify-center h-64 text-muted-foreground">Loading...</div>
  }

  if (error || !matrix) {
    return (
      <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-6 text-center">
        <h3 className="text-lg font-medium text-destructive">Traceability Data Not Found</h3>
        <Link to="/projects" className="mt-4 inline-block text-primary hover:text-primary/80">
          &larr; Back to Projects
        </Link>
      </div>
    )
  }

  return (
    <div className="animate-fade-in space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Link to={`/projects/${prefix}`} className="p-2 hover:bg-accent/50 rounded-md">
            <ArrowLeft className="h-5 w-5 text-muted-foreground" />
          </Link>
          <div>
            <h2 className="text-2xl font-bold text-foreground">Traceability Matrix</h2>
            <p className="text-muted-foreground">{project?.name || `Project #${projId}`}</p>
          </div>
        </div>
        <button
          onClick={() => setShowGaps(!showGaps)}
          className={`inline-flex items-center px-4 py-2 rounded-md text-sm font-medium transition-all duration-200 ${
            showGaps
              ? 'bg-primary text-primary-foreground shadow-glow'
              : 'border border-input text-foreground hover:bg-accent/50'
          }`}
        >
          <AlertTriangle className="h-4 w-4 mr-2" />
          {showGaps ? 'Hide Gap Report' : 'Coverage Gaps'}
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <SummaryCard label="Requirements" value={totalRequirements} icon={Shield} color="text-primary" />
        <SummaryCard label="Test Cases" value={totalTestCases} icon={CheckCircle} color="text-emerald-600" />
        <SummaryCard
          label="Coverage"
          value={`${coveragePercent}%`}
          icon={Shield}
          color={coveragePercent >= 80 ? 'text-emerald-600' : coveragePercent >= 50 ? 'text-amber-600' : 'text-red-600'}
        />
        <SummaryCard
          label="Uncovered"
          value={uncovered}
          icon={XCircle}
          color={uncovered > 0 ? 'text-red-600' : 'text-emerald-600'}
        />
      </div>

      {showGaps && gapReport && (
        <div className="bg-card rounded-lg shadow-elegant border border-amber-500/30 overflow-hidden">
          <div className="px-6 py-4 bg-amber-500/5 border-b border-amber-500/20">
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <AlertTriangle className="h-5 w-5 text-amber-600 mr-2" />
                <h3 className="text-lg font-semibold text-foreground">Coverage Gap Report</h3>
              </div>
              <div className="flex items-center space-x-4 text-sm">
                <span className="text-muted-foreground">
                  {gapReport.coverage_percent}% covered
                </span>
                <span className="text-red-600 font-medium">{gapReport.uncovered} uncovered</span>
                <span className="text-amber-600 font-medium">{gapReport.partial} partial</span>
              </div>
            </div>
          </div>
          {gapReport.gaps.length === 0 ? (
            <div className="p-8 text-center text-muted-foreground">
              <CheckCircle className="h-8 w-8 text-emerald-500 mx-auto mb-2" />
              <p className="font-medium text-foreground">No coverage gaps detected</p>
              <p className="text-sm mt-1">All requirements have adequate test coverage.</p>
            </div>
          ) : (
            <div className="divide-y divide-border">
              {gapReport.gaps.map((gap) => (
                <div key={gap.requirement.id} className="px-6 py-4 hover:bg-accent/30">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <Link
                        to={docUrl(prefix!, 'REQ', gap.requirement.req_id)}
                        className="font-mono text-sm text-primary hover:text-primary/80 font-medium"
                      >
                        {gap.requirement.req_id}
                      </Link>
                      <Link to={docUrl(prefix!, 'REQ', gap.requirement.req_id)} className="text-foreground hover:text-primary/80">
                        {gap.requirement.title}
                      </Link>
                    </div>
                    <div className="flex items-center space-x-3">
                      <GapTypeBadge gapType={gap.gap_type} />
                      {gap.missing_link_types.length > 0 && (
                        <div className="flex items-center space-x-1">
                          {gap.missing_link_types.map((lt) => (
                            <span key={lt} className="px-1.5 py-0.5 bg-red-500/10 text-red-700 dark:text-red-400 rounded text-xs">
                              missing: {lt}
                            </span>
                          ))}
                        </div>
                      )}
                      <ImpactLink prefix={prefix!} reqId={gap.requirement.req_id} />
                    </div>
                  </div>
                  {gap.linked_test_cases.length > 0 && (
                    <div className="mt-2 flex items-center space-x-2">
                      <span className="text-xs text-muted-foreground">Linked:</span>
                      {gap.linked_test_cases.map((tc) => (
                        <Link
                          key={tc.id}
                          to={docUrl(prefix!, 'TC', tc.tc_id)}
                          className="inline-flex items-center px-1.5 py-0.5 bg-muted rounded text-xs font-mono text-muted-foreground hover:text-primary"
                        >
                          {tc.tc_id}
                        </Link>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-6 text-sm">
          <div className="flex items-center">
            <div className="w-3 h-3 rounded-full bg-emerald-500 mr-2" />
            <span className="text-muted-foreground">Covered: {covered}</span>
          </div>
          <div className="flex items-center">
            <div className="w-3 h-3 rounded-full bg-amber-500 mr-2" />
            <span className="text-muted-foreground">Partial: {partial}</span>
          </div>
          <div className="flex items-center">
            <div className="w-3 h-3 rounded-full bg-red-500 mr-2" />
            <span className="text-muted-foreground">Uncovered: {uncovered}</span>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-1 text-xs text-muted-foreground">
            <Filter className="h-3.5 w-3.5" />
            <select
              value={coverageFilter}
              onChange={(e) => setCoverageFilter(e.target.value)}
              className="px-2 py-1.5 bg-background border border-input rounded-md text-sm focus:ring-2 focus:ring-ring"
            >
              <option value="">All Coverage</option>
              <option value="Covered">Covered</option>
              <option value="Partial">Partial</option>
              <option value="Uncovered">Uncovered</option>
            </select>
          </div>
          <div className="flex items-center space-x-1 text-xs text-muted-foreground">
            <select
              value={priorityFilter}
              onChange={(e) => setPriorityFilter(e.target.value)}
              className="px-2 py-1.5 bg-background border border-input rounded-md text-sm focus:ring-2 focus:ring-ring"
            >
              <option value="">All Priorities</option>
              <option value="Critical">Critical</option>
              <option value="High">High</option>
              <option value="Medium">Medium</option>
              <option value="Low">Low</option>
            </select>
          </div>
          <div className="flex items-center space-x-1 text-xs text-muted-foreground">
            <ArrowUpDown className="h-3.5 w-3.5" />
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="px-2 py-1.5 bg-background border border-input rounded-md text-sm focus:ring-2 focus:ring-ring"
            >
              <option value="req_id">Sort: ID</option>
              <option value="priority">Sort: Priority</option>
              <option value="coverage">Sort: Coverage</option>
            </select>
          </div>
        </div>
      </div>

      {matrix.length === 0 ? (
        <div className="bg-card rounded-lg shadow-elegant p-12 text-center">
          <Shield className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
          <h3 className="text-lg font-medium text-foreground mb-2">No Requirements</h3>
          <p className="text-muted-foreground">Add requirements to this project to see traceability data.</p>
        </div>
      ) : (
        <div className="bg-card rounded-lg shadow-elegant overflow-hidden">
          <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-border">
            <thead className="bg-muted/50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Req ID</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Title</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Priority</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Status</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Coverage</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Test Cases</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Test Runs</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Impact</th>
              </tr>
            </thead>
            <tbody className="bg-card divide-y divide-border">
              {matrix.map((item) => (
                <tr key={item.requirement.id} className="hover:bg-accent/50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <Link
                      to={docUrl(prefix!, 'REQ', item.requirement.req_id)}
                      className="font-mono text-sm text-primary hover:text-primary/80 font-medium"
                    >
                      {item.requirement.req_id}
                    </Link>
                  </td>
                  <td className="px-6 py-4">
                    <Link to={docUrl(prefix!, 'REQ', item.requirement.req_id)} className="text-foreground hover:text-primary/80">
                      {item.requirement.title}
                    </Link>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <PriorityBadge priority={item.requirement.priority} />
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <RequirementStatusBadge status={item.requirement.status} />
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <CoverageBadge status={item.coverage_status} />
                  </td>
                  <td className="px-6 py-4 text-sm">
                    {item.linked_test_cases.length > 0 ? (
                      <div className="flex flex-wrap gap-1">
                        {item.linked_test_cases.map((tc) => (
                          <Link
                            key={tc.id}
                            to={docUrl(prefix!, 'TC', tc.tc_id)}
                            className="inline-flex items-center px-2 py-0.5 bg-primary/10 text-primary rounded text-xs font-mono hover:bg-primary/20"
                          >
                            {tc.tc_id}
                          </Link>
                        ))}
                      </div>
                    ) : (
                      <span className="text-muted-foreground">&mdash;</span>
                    )}
                  </td>
                  <td className="px-6 py-4 text-sm">
                    {item.linked_test_runs.length > 0 ? (
                      <div className="space-y-1">
                        {item.linked_test_runs.map((tr) => (
                          <div key={tr.id} className="flex items-center">
                            {tr.teststation_url ? (
                              <a
                                href={tr.teststation_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-primary hover:text-primary/80 inline-flex items-center"
                              >
                                <ExternalLink className="h-3 w-3 mr-1" />
                                {tr.test_run_name || `#${tr.test_run_id}`}
                              </a>
                            ) : (
                              <span className="text-muted-foreground">{tr.test_run_name || `#${tr.test_run_id}`}</span>
                            )}
                          </div>
                        ))}
                      </div>
                    ) : (
                      <span className="text-muted-foreground">&mdash;</span>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <ImpactLink prefix={prefix!} reqId={item.requirement.req_id} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        </div>
      )}
    </div>
  )
}

function SummaryCard({ label, value, icon: Icon, color }: {
  label: string
  value: number | string
  icon: React.ComponentType<{ className?: string }>
  color: string
}) {
  return (
    <div className="bg-card rounded-lg shadow-elegant p-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-muted-foreground">{label}</p>
          <p className="text-2xl font-bold text-foreground">{value}</p>
        </div>
        <Icon className={`h-8 w-8 ${color}`} />
      </div>
    </div>
  )
}

function CoverageBadge({ status }: { status: string }) {
  const config: Record<string, { colors: string; icon: React.ComponentType<{ className?: string }> }> = {
    Covered: { colors: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400', icon: CheckCircle },
    Partial: { colors: 'bg-amber-500/10 text-amber-700 dark:text-amber-400', icon: AlertCircle },
    Uncovered: { colors: 'bg-red-500/10 text-red-700 dark:text-red-400', icon: XCircle },
  }
  const cfg = config[status] || config.Uncovered
  const CIcon = cfg.icon
  return (
    <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${cfg.colors}`}>
      <CIcon className="h-3 w-3 mr-1" />
      {status}
    </span>
  )
}

function GapTypeBadge({ gapType }: { gapType: string }) {
  const config: Record<string, { colors: string; label: string }> = {
    no_test_cases: { colors: 'bg-red-500/10 text-red-700 dark:text-red-400', label: 'No Test Cases' },
    all_draft: { colors: 'bg-amber-500/10 text-amber-700 dark:text-amber-400', label: 'All Draft' },
    missing_link_types: { colors: 'bg-orange-500/10 text-orange-700 dark:text-orange-400', label: 'Missing Links' },
  }
  const cfg = config[gapType] || { colors: 'bg-gray-500/10 text-gray-700', label: gapType }
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${cfg.colors}`}>
      {cfg.label}
    </span>
  )
}

function ImpactLink({ prefix, reqId }: { prefix: string; reqId: string }) {
  return (
    <Link
      to={`/projects/${prefix}/impact-analysis/${reqId}`}
      className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium text-primary hover:bg-primary/10 transition-colors"
    >
      <GitBranch className="h-3.5 w-3.5 mr-1" />
      Analyze
    </Link>
  )
}

function RequirementStatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    Draft: 'bg-gray-500/10 text-gray-700 dark:text-gray-400',
    Review: 'bg-amber-500/10 text-amber-700 dark:text-amber-400',
    Approved: 'bg-blue-500/10 text-blue-700 dark:text-blue-400',
    Implemented: 'bg-teal-500/10 text-teal-700 dark:text-teal-400',
    Verified: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400',
    Rejected: 'bg-red-500/10 text-red-700 dark:text-red-400',
  }
  return (
    <span className={`px-2 py-1 rounded-full text-xs font-medium ${colors[status] || 'bg-gray-500/10 text-gray-700 dark:text-gray-400'}`}>
      {status}
    </span>
  )
}

function PriorityBadge({ priority }: { priority: string }) {
  const colors: Record<string, string> = {
    Low: 'bg-gray-500/10 text-gray-700 dark:text-gray-400',
    Medium: 'bg-blue-500/10 text-blue-700 dark:text-blue-400',
    High: 'bg-orange-500/10 text-orange-700 dark:text-orange-400',
    Critical: 'bg-red-500/10 text-red-700 dark:text-red-400',
  }
  return (
    <span className={`px-2 py-1 rounded-full text-xs font-medium ${colors[priority] || 'bg-gray-500/10 text-gray-700 dark:text-gray-400'}`}>
      {priority}
    </span>
  )
}
