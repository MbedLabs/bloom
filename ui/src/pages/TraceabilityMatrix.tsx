import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router'
import { useQuery, keepPreviousData } from '@tanstack/react-query'
import { traceabilityApi, projectsApi, exportApi } from '../api/client'
import { docUrl } from '../types/doc'
import { ArrowLeft, CheckCircle, AlertCircle, XCircle, ExternalLink, Shield, Filter, GitBranch, AlertTriangle, X, Download } from 'lucide-react'

const COVERAGE_OPTIONS = ['Covered', 'Partial', 'Uncovered'] as const
const PRIORITY_OPTIONS = ['Low', 'Medium', 'High', 'Critical']
const TRACEABILITY_SORT_OPTIONS = [
  { value: 'req_id', label: 'ID' },
  { value: 'priority', label: 'Priority' },
  { value: 'coverage', label: 'Coverage' },
] as const

export default function TraceabilityMatrix() {
  const { prefix } = useParams<{ prefix: string }>()
  const [coverageFilter, setCoverageFilter] = useState('')
  const [coverageDefaultApplied, setCoverageDefaultApplied] = useState(false)
  const [priorityFilter, setPriorityFilter] = useState('')
  const [sortBy, setSortBy] = useState('req_id')
  const [showGaps, setShowGaps] = useState(false)
  const [filtersOpen, setFiltersOpen] = useState(false)

  const { data: project } = useQuery({
    queryKey: ['project-by-prefix', prefix],
    queryFn: () => projectsApi.getByPrefix(prefix!),
    enabled: !!prefix,
  })

  const projId = project?.id || 0

  useEffect(() => {
    setCoverageFilter('')
    setPriorityFilter('')
    setSortBy('req_id')
    setCoverageDefaultApplied(false)
    setShowGaps(false)
    setFiltersOpen(false)
  }, [projId])

  const { data: coverageReport } = useQuery({
    queryKey: ['coverage-gaps', projId],
    queryFn: () => traceabilityApi.getCoverageGaps(projId),
    enabled: !!projId,
  })

  useEffect(() => {
    if (!projId || coverageDefaultApplied || coverageReport === undefined) return
    setCoverageFilter(coverageReport.uncovered > 0 ? 'Uncovered' : '')
    setCoverageDefaultApplied(true)
  }, [projId, coverageReport, coverageDefaultApplied])

  const { data: matrix, isLoading, error } = useQuery({
    queryKey: ['traceability', projId, coverageFilter, priorityFilter, sortBy],
    queryFn: () => traceabilityApi.getMatrix(projId, {
      coverage_filter: coverageFilter || undefined,
      priority_filter: priorityFilter || undefined,
      sort_by: sortBy,
    }),
    enabled: !!projId && coverageDefaultApplied,
    placeholderData: keepPreviousData,
  })

  const totalRequirements = coverageReport?.total_requirements ?? project?.requirement_count ?? 0
  const covered = coverageReport?.covered ?? 0
  const partial = coverageReport?.partial ?? 0
  const uncovered = coverageReport?.uncovered ?? 0
  const coveragePercent = coverageReport?.coverage_percent ?? 0
  const totalTestCases = project?.test_case_count ?? 0
  const hasActiveFilters = coverageFilter !== '' || priorityFilter !== ''
  const hasSortOverride = sortBy !== 'req_id'
  const showFilterSummary = hasActiveFilters || hasSortOverride
  const sortLabel = TRACEABILITY_SORT_OPTIONS.find((option) => option.value === sortBy)?.label ?? 'ID'

  const clearFilters = () => {
    setCoverageFilter('')
    setPriorityFilter('')
  }

  const toggleCoverage = (status: string) => {
    setCoverageFilter((current) => (current === status ? '' : status))
  }

  if ((isLoading || !coverageDefaultApplied) && !matrix) {
    return <div className="flex items-center justify-center h-64 text-muted-foreground">Loading...</div>
  }

  if (error && !matrix) {
    return (
      <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-6 text-center">
        <h3 className="text-lg font-medium text-destructive">Traceability Data Not Found</h3>
        <Link to="/projects" className="mt-4 inline-block text-primary hover:text-primary/80">
          &larr; Back to Projects
        </Link>
      </div>
    )
  }

  const rows = matrix ?? []

  return (
    <div className="animate-fade-in space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Link to={`/projects/${prefix}`} className="p-2 hover:bg-accent/50 rounded-md">
            <ArrowLeft className="h-5 w-5 text-muted-foreground" />
          </Link>
          <div>
            <h2 className="text-2xl font-bold text-foreground">Traceability Matrix</h2>
            <p className="text-muted-foreground">
              {coverageFilter === 'Uncovered'
                ? 'Requirements without a verifying test case.'
                : 'Requirement to test case links for this project.'}
            </p>
            <p className="text-sm text-muted-foreground">{project?.name || `Project #${projId}`}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => projId && exportApi.download(projId, 'traceability')}
            disabled={!projId}
            title="Export the requirement-to-test-case matrix as CSV"
            className="inline-flex items-center gap-1.5 px-3 py-2 border border-input text-foreground rounded-md text-sm font-medium hover:bg-accent/50 disabled:opacity-50"
          >
            <Download className="h-4 w-4" />
            Matrix CSV
          </button>
          <button
            onClick={() => projId && exportApi.download(projId, 'requirements', 'csv')}
            disabled={!projId}
            title="Export all requirements as CSV"
            className="inline-flex items-center gap-1.5 px-3 py-2 border border-input text-foreground rounded-md text-sm font-medium hover:bg-accent/50 disabled:opacity-50"
          >
            <Download className="h-4 w-4" />
            Reqs CSV
          </button>
          <button
            onClick={() => projId && exportApi.download(projId, 'requirements', 'pdf')}
            disabled={!projId}
            title="Export the requirements specification as PDF"
            className="inline-flex items-center gap-1.5 px-3 py-2 border border-input text-foreground rounded-md text-sm font-medium hover:bg-accent/50 disabled:opacity-50"
          >
            <Download className="h-4 w-4" />
            Spec PDF
          </button>
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

      {showGaps && coverageReport && (
        <div className="bg-card rounded-lg shadow-elegant border border-amber-500/30 overflow-hidden">
          <div className="px-6 py-4 bg-amber-500/5 border-b border-amber-500/20">
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <AlertTriangle className="h-5 w-5 text-amber-600 mr-2" />
                <h3 className="text-lg font-semibold text-foreground">Coverage Gap Report</h3>
              </div>
              <div className="flex items-center space-x-4 text-sm">
                <span className="text-muted-foreground">
                  {coverageReport.coverage_percent}% covered
                </span>
                <span className="text-red-600 font-medium">{coverageReport.uncovered} uncovered</span>
                <span className="text-amber-600 font-medium">{coverageReport.partial} partial</span>
              </div>
            </div>
          </div>
          {coverageReport.gaps.length === 0 ? (
            <div className="p-8 text-center text-muted-foreground">
              <CheckCircle className="h-8 w-8 text-emerald-500 mx-auto mb-2" />
              <p className="font-medium text-foreground">No coverage gaps detected</p>
              <p className="text-sm mt-1">All requirements have adequate test coverage.</p>
            </div>
          ) : (
            <div className="divide-y divide-border">
              {coverageReport.gaps.map((gap) => (
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

      <section className="rounded-lg border border-border bg-card">
        <div className="grid grid-cols-1 gap-2 border-b border-border p-3 md:grid-cols-[minmax(180px,1fr)_auto]">
          <label className="space-y-1">
            <span className="sr-only">Sort traceability rows</span>
            <select
              value={sortBy}
              onChange={(event) => setSortBy(event.target.value)}
              className="w-full rounded-md border border-input bg-background px-2.5 py-1.5 text-sm"
            >
              {TRACEABILITY_SORT_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  Sort by {option.label}
                </option>
              ))}
            </select>
          </label>
          <button
            type="button"
            onClick={() => setFiltersOpen((open) => !open)}
            className={`inline-flex items-center justify-center gap-2 rounded-md border px-2.5 py-1.5 text-sm font-medium transition-colors ${
              filtersOpen || hasActiveFilters
                ? 'border-primary bg-primary/10 text-primary'
                : 'border-input bg-background text-foreground hover:bg-accent'
            }`}
            aria-expanded={filtersOpen}
            aria-controls="traceability-filter-panel"
          >
            <Filter className="h-4 w-4" />
            Filters
            {hasActiveFilters && (
              <span className="rounded bg-primary px-1.5 py-0.5 text-[10px] font-semibold text-primary-foreground">On</span>
            )}
          </button>
        </div>

        {showFilterSummary && (
          <div className="flex flex-wrap items-center gap-2 border-b border-border px-3 py-2">
            <FilterChip label={`Sort: ${sortLabel}`} muted={!hasSortOverride} />
            {coverageFilter && <FilterChip label={`Coverage: ${coverageFilter}`} />}
            {priorityFilter && <FilterChip label={`Priority: ${priorityFilter}`} />}
            {hasActiveFilters && (
              <button
                type="button"
                onClick={clearFilters}
                className="inline-flex items-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-foreground"
              >
                <X className="h-3.5 w-3.5" />
                Clear all
              </button>
            )}
          </div>
        )}

        {filtersOpen && (
          <div id="traceability-filter-panel" className="space-y-3 border-t border-border p-3">
            <div className="flex items-center gap-2 text-sm font-semibold text-foreground">
              <Filter className="h-4 w-4 text-primary" />
              Filters
            </div>

            <div className="space-y-2">
              <div className="text-xs font-medium uppercase text-muted-foreground">Coverage</div>
              <div className="flex flex-wrap gap-2">
                {COVERAGE_OPTIONS.map((status) => (
                  <button
                    key={status}
                    type="button"
                    onClick={() => toggleCoverage(status)}
                    className={`rounded-md border px-2.5 py-1 text-xs font-medium transition-colors ${
                      coverageFilter === status
                        ? 'border-primary bg-primary/10 text-primary'
                        : 'border-border bg-background text-muted-foreground hover:text-foreground'
                    }`}
                  >
                    {status}
                  </button>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-1 gap-2 md:grid-cols-2 xl:grid-cols-4">
              <label className="space-y-1">
                <span className="text-xs font-medium uppercase text-muted-foreground">Priority</span>
                <select
                  value={priorityFilter}
                  onChange={(event) => setPriorityFilter(event.target.value)}
                  className="w-full rounded-md border border-input bg-background px-2.5 py-1.5 text-sm"
                >
                  <option value="">Any priority</option>
                  {PRIORITY_OPTIONS.map((priority) => (
                    <option key={priority} value={priority}>
                      {priority}
                    </option>
                  ))}
                </select>
              </label>
            </div>
          </div>
        )}

        {rows.length === 0 ? (
          <div className="p-12 text-center">
            <Shield className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg font-medium text-foreground mb-2">
              {totalRequirements > 0 ? 'No Matching Requirements' : 'No Requirements'}
            </h3>
            <p className="text-muted-foreground">
              {totalRequirements > 0
                ? 'No requirements match the current coverage and priority filters.'
                : 'Add requirements to this project to see traceability data.'}
            </p>
          </div>
        ) : (
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
                {rows.map((item) => (
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
        )}
      </section>
    </div>
  )
}

function FilterChip({ label, muted = false }: { label: string; muted?: boolean }) {
  return (
    <span className={`inline-flex items-center rounded-md border px-2 py-0.5 text-xs ${muted ? 'border-border text-muted-foreground' : 'border-primary/20 bg-primary/10 text-primary'}`}>
      {label}
    </span>
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
    Implemented: 'bg-violet-500/10 text-violet-700 dark:text-violet-400',
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
