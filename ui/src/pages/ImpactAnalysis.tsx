import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { traceabilityApi, docsApi } from '../api/client'
import { ArrowLeft, ArrowUpCircle, ArrowDownCircle, ChevronRight, ChevronDown, CheckCircle } from 'lucide-react'
import { useState } from 'react'
import type { ImpactNode } from '../api/client'
import { docUrl } from '../types/doc'

export default function ImpactAnalysis() {
  const { prefix, requirementId } = useParams<{ prefix: string; requirementId: string }>()

  const { data: resolvedDoc } = useQuery({
    queryKey: ['resolve-doc', prefix, requirementId],
    queryFn: () => docsApi.get(prefix!, 'requirements', requirementId!),
    enabled: !!prefix && !!requirementId,
  })

  const numericId = resolvedDoc?.id || 0

  const { data: analysis, isLoading, error } = useQuery({
    queryKey: ['impact-analysis', numericId],
    queryFn: () => traceabilityApi.getImpactAnalysis(numericId, 5),
    enabled: !!numericId,
  })

  const totalUpstream = analysis ? countNodes(analysis.upstream) : 0
  const totalDownstream = analysis ? countNodes(analysis.downstream) : 0

  if (isLoading) {
    return <div className="flex items-center justify-center h-64 text-muted-foreground">Loading impact analysis...</div>
  }

  if (error || !analysis) {
    return (
      <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-6 text-center">
        <h3 className="text-lg font-medium text-destructive">Impact Analysis Not Available</h3>
        <Link to="/projects" className="mt-4 inline-block text-primary hover:text-primary/80">
          &larr; Back to Projects
        </Link>
      </div>
    )
  }

  return (
    <div className="animate-fade-in space-y-6">
      <div className="flex items-center space-x-4">
        <Link to={docUrl(prefix!, 'REQ', requirementId!)} className="p-2 hover:bg-accent/50 rounded-md">
          <ArrowLeft className="h-5 w-5 text-muted-foreground" />
        </Link>
        <div>
          <h2 className="text-2xl font-bold text-foreground">Impact Analysis</h2>
          <p className="text-muted-foreground">
            <span className="font-mono text-primary">{analysis.root_requirement.req_id}</span>
            {' '}&mdash; {analysis.root_requirement.title}
          </p>
        </div>
      </div>

      <div className="bg-card rounded-lg shadow-elegant p-5">
        <div className="flex items-center space-x-6">
          <div>
            <span className="text-sm text-muted-foreground">Status</span>
            <p className="font-medium text-foreground">{analysis.root_requirement.status}</p>
          </div>
          <div>
            <span className="text-sm text-muted-foreground">Priority</span>
            <p className="font-medium text-foreground">{analysis.root_requirement.priority}</p>
          </div>
          <div>
            <span className="text-sm text-muted-foreground">Type</span>
            <p className="font-medium text-foreground">{analysis.root_requirement.req_type}</p>
          </div>
          <div>
            <span className="text-sm text-muted-foreground">Origin</span>
            <p className="font-medium text-foreground">{analysis.root_requirement.req_origin}</p>
          </div>
          <div className="ml-auto flex items-center space-x-6">
            <div className="text-center">
              <p className="text-2xl font-bold text-blue-600">{totalUpstream}</p>
              <p className="text-xs text-muted-foreground">Upstream</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-orange-600">{totalDownstream}</p>
              <p className="text-xs text-muted-foreground">Downstream</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-foreground">{totalUpstream + totalDownstream}</p>
              <p className="text-xs text-muted-foreground">Total Impacts</p>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-card rounded-lg shadow-elegant overflow-hidden">
          <div className="px-6 py-4 border-b border-border bg-blue-500/5">
            <div className="flex items-center">
              <ArrowUpCircle className="h-5 w-5 text-blue-600 mr-2" />
              <h3 className="text-lg font-semibold text-foreground">Upstream Dependencies</h3>
            </div>
            <p className="text-sm text-muted-foreground mt-0.5">Items this requirement depends on</p>
          </div>
          <div className="p-4">
            {analysis.upstream.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <ArrowUpCircle className="h-8 w-8 text-muted-foreground/40 mx-auto mb-2" />
                <p className="text-sm">No upstream dependencies found</p>
              </div>
            ) : (
              <ImpactTree nodes={analysis.upstream} direction="upstream" prefix={prefix!} />
            )}
          </div>
        </div>

        <div className="bg-card rounded-lg shadow-elegant overflow-hidden">
          <div className="px-6 py-4 border-b border-border bg-orange-500/5">
            <div className="flex items-center">
              <ArrowDownCircle className="h-5 w-5 text-orange-600 mr-2" />
              <h3 className="text-lg font-semibold text-foreground">Downstream Impact</h3>
            </div>
            <p className="text-sm text-muted-foreground mt-0.5">Items affected by changes to this requirement</p>
          </div>
          <div className="p-4">
            {analysis.downstream.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <ArrowDownCircle className="h-8 w-8 text-muted-foreground/40 mx-auto mb-2" />
                <p className="text-sm">No downstream impacts found</p>
              </div>
            ) : (
              <ImpactTree nodes={analysis.downstream} direction="downstream" prefix={prefix!} />
            )}
          </div>
        </div>
      </div>

      {analysis.root_requirement.req_type === 'test_case' && (
        <div className="bg-muted/30 rounded-lg p-4 text-sm text-muted-foreground flex items-center">
          <CheckCircle className="h-4 w-4 mr-2" />
          Test cases appear in downstream impact as leaf nodes.
        </div>
      )}
    </div>
  )
}

function countNodes(nodes: ImpactNode[]): number {
  let count = 0
  for (const node of nodes) {
    count += 1 + countNodes(node.children)
  }
  return count
}

function ImpactTree({ nodes, direction, prefix }: { nodes: ImpactNode[]; direction: string; prefix: string }) {
  return (
    <div className="space-y-1">
      {nodes.map((node) => (
        <ImpactTreeNode key={`${node.direction}-${node.requirement.id}`} node={node} direction={direction} depth={0} prefix={prefix} />
      ))}
    </div>
  )
}

function ImpactTreeNode({ node, direction, depth, prefix }: { node: ImpactNode; direction: string; depth: number; prefix: string }) {
  const [expanded, setExpanded] = useState(depth < 1)
  const hasChildren = node.children.length > 0
  const borderColor = direction === 'upstream' ? 'border-l-blue-400' : 'border-l-orange-400'

  return (
    <div style={{ marginLeft: `${depth * 20}px` }}>
      <div
        className={`flex items-center justify-between px-3 py-2 rounded-md border-l-2 ${borderColor} hover:bg-accent/30 transition-colors`}
      >
        <div className="flex items-center space-x-2 min-w-0">
          {hasChildren ? (
            <button onClick={() => setExpanded(!expanded)} className="flex-shrink-0 p-0.5 hover:bg-accent/50 rounded">
              {expanded ? <ChevronDown className="h-4 w-4 text-muted-foreground" /> : <ChevronRight className="h-4 w-4 text-muted-foreground" />}
            </button>
          ) : (
            <div className="w-5 flex-shrink-0" />
          )}
          <Link
            to={docUrl(prefix, 'REQ', node.requirement.req_id)}
            className="font-mono text-xs text-primary hover:text-primary/80 font-medium flex-shrink-0"
          >
            {node.requirement.req_id}
          </Link>
          <Link
            to={docUrl(prefix, 'REQ', node.requirement.req_id)}
            className="text-sm text-foreground truncate hover:text-primary/80"
          >
            {node.requirement.title}
          </Link>
        </div>
        <div className="flex items-center space-x-2 flex-shrink-0 ml-2">
          <LinkTypeBadge linkType={node.link_type} />
          <span className="text-xs text-muted-foreground">depth {node.depth}</span>
        </div>
      </div>
      {expanded && hasChildren && (
        <div className="mt-0.5">
          {node.children.map((child) => (
            <ImpactTreeNode
              key={`${child.direction}-${child.requirement.id}`}
              node={child}
              direction={direction}
              depth={depth + 1}
              prefix={prefix}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function LinkTypeBadge({ linkType }: { linkType: string }) {
  const config: Record<string, { colors: string; label: string }> = {
    verifies: { colors: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400', label: 'verifies' },
    traces_to: { colors: 'bg-blue-500/10 text-blue-700 dark:text-blue-400', label: 'traces to' },
    exercises: { colors: 'bg-violet-500/10 text-violet-700 dark:text-violet-400', label: 'exercises' },
    depends_on: { colors: 'bg-amber-500/10 text-amber-700 dark:text-amber-400', label: 'depends on' },
    derived_from: { colors: 'bg-indigo-500/10 text-indigo-700 dark:text-indigo-400', label: 'derived from' },
    refines: { colors: 'bg-sky-500/10 text-sky-700 dark:text-sky-400', label: 'refines' },
    satisfies: { colors: 'bg-green-500/10 text-green-700 dark:text-green-400', label: 'satisfies' },
    copies: { colors: 'bg-gray-500/10 text-gray-700 dark:text-gray-400', label: 'copies' },
  }
  const cfg = config[linkType] || { colors: 'bg-gray-500/10 text-gray-700 dark:text-gray-400', label: linkType }
  return (
    <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${cfg.colors}`}>
      {cfg.label}
    </span>
  )
}
