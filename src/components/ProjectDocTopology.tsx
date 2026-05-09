import { useCallback, useEffect, useMemo, useState, useSyncExternalStore } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  ReactFlow,
  Background,
  BackgroundVariant,
  Controls,
  Panel,
  MarkerType,
  Handle,
  Position,
  useNodesState,
  useEdgesState,
  useReactFlow,
  type Node,
  type Edge,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import dagre from 'dagre'
import {
  AlertTriangle,
  Beaker,
  BookOpen,
  CheckSquare,
  FileText,
  GitBranch,
  GitPullRequest,
  Layers,
  PenTool,
  RotateCcw,
  type LucideIcon,
} from 'lucide-react'

import { docsApi, linksApi } from '../api/client'
import { DOC_TYPE_LABELS, type DocType } from '../types/doc'

// ────────────────────────────────────────────────────────────────────────────
// Type-level visual config
// ────────────────────────────────────────────────────────────────────────────

const TYPE_ORDER: DocType[] = ['REQ', 'SPEC', 'STD', 'DES', 'RSK', 'CHG', 'TCO', 'TC', 'PROT', 'RPT']

interface TypeStyle {
  icon: LucideIcon
  borderTop: string
  surface: string
  iconChip: string
  countText: string
  /** Edge / marker stroke (SVG) */
  accent: string
}

const TYPE_STYLE: Record<DocType, TypeStyle> = {
  REQ: {
    icon: FileText,
    borderTop: 'border-t-amber-500',
    surface: 'bg-gradient-to-br from-amber-500/10 to-card ring-1 ring-amber-500/10',
    iconChip: 'bg-amber-500/15 text-amber-800 dark:text-amber-200',
    countText: 'text-amber-800 dark:text-amber-200',
    accent: '#d97706',
  },
  SPEC: {
    icon: FileText,
    borderTop: 'border-t-indigo-600',
    surface: 'bg-gradient-to-br from-indigo-500/10 to-card ring-1 ring-indigo-500/10',
    iconChip: 'bg-indigo-500/15 text-indigo-800 dark:text-indigo-200',
    countText: 'text-indigo-800 dark:text-indigo-200',
    accent: '#4f46e5',
  },
  TC: {
    icon: CheckSquare,
    borderTop: 'border-t-cyan-600',
    surface: 'bg-gradient-to-br from-cyan-500/10 to-card ring-1 ring-cyan-500/10',
    iconChip: 'bg-cyan-500/15 text-cyan-900 dark:text-cyan-200',
    countText: 'text-cyan-900 dark:text-cyan-200',
    accent: '#0891b2',
  },
  TCO: {
    icon: Beaker,
    borderTop: 'border-t-emerald-600',
    surface: 'bg-gradient-to-br from-emerald-500/10 to-card ring-1 ring-emerald-500/10',
    iconChip: 'bg-emerald-500/15 text-emerald-900 dark:text-emerald-200',
    countText: 'text-emerald-900 dark:text-emerald-200',
    accent: '#059669',
  },
  PROT: {
    icon: BookOpen,
    borderTop: 'border-t-teal-600',
    surface: 'bg-gradient-to-br from-teal-500/10 to-card ring-1 ring-teal-500/10',
    iconChip: 'bg-teal-500/15 text-teal-900 dark:text-teal-200',
    countText: 'text-teal-900 dark:text-teal-200',
    accent: '#0d9488',
  },
  DES: {
    icon: PenTool,
    borderTop: 'border-t-violet-600',
    surface: 'bg-gradient-to-br from-violet-500/10 to-card ring-1 ring-violet-500/10',
    iconChip: 'bg-violet-500/15 text-violet-900 dark:text-violet-200',
    countText: 'text-violet-900 dark:text-violet-200',
    accent: '#7c3aed',
  },
  RSK: {
    icon: AlertTriangle,
    borderTop: 'border-t-red-600',
    surface: 'bg-gradient-to-br from-red-500/10 to-card ring-1 ring-red-500/10',
    iconChip: 'bg-red-500/15 text-red-800 dark:text-red-200',
    countText: 'text-red-800 dark:text-red-200',
    accent: '#dc2626',
  },
  CHG: {
    icon: GitPullRequest,
    borderTop: 'border-t-blue-600',
    surface: 'bg-gradient-to-br from-blue-500/10 to-card ring-1 ring-blue-500/10',
    iconChip: 'bg-blue-500/15 text-blue-900 dark:text-blue-200',
    countText: 'text-blue-900 dark:text-blue-200',
    accent: '#2563eb',
  },
  RPT: {
    icon: Layers,
    borderTop: 'border-t-slate-600',
    surface: 'bg-gradient-to-br from-slate-500/10 to-card ring-1 ring-slate-500/10',
    iconChip: 'bg-slate-500/15 text-slate-800 dark:text-slate-200',
    countText: 'text-slate-800 dark:text-slate-200',
    accent: '#64748b',
  },
  STD: {
    icon: BookOpen,
    borderTop: 'border-t-orange-600',
    surface: 'bg-gradient-to-br from-orange-500/10 to-card ring-1 ring-orange-500/10',
    iconChip: 'bg-orange-500/15 text-orange-900 dark:text-orange-200',
    countText: 'text-orange-900 dark:text-orange-200',
    accent: '#ea580c',
  },
  DEF: {
    icon: AlertTriangle,
    borderTop: 'border-t-rose-600',
    surface: 'bg-gradient-to-br from-rose-500/10 to-card ring-1 ring-rose-500/10',
    iconChip: 'bg-rose-500/15 text-rose-900 dark:text-rose-200',
    countText: 'text-rose-900 dark:text-rose-200',
    accent: '#e11d48',
  },
  CMP: {
    icon: GitBranch,
    borderTop: 'border-t-sky-600',
    surface: 'bg-gradient-to-br from-sky-500/10 to-card ring-1 ring-sky-500/10',
    iconChip: 'bg-sky-500/15 text-sky-900 dark:text-sky-200',
    countText: 'text-sky-900 dark:text-sky-200',
    accent: '#0284c7',
  },
}

// Edge label / line colors (shadcn tokens are HSL channels — need full hsl() for SVG)
const EDGE_LABEL_BG = 'hsl(var(--card))'
const EDGE_LABEL_FG = 'hsl(var(--foreground))'
const EDGE_LABEL_OUTLINE = 'hsl(var(--border))'

function subscribeDarkMode(cb: () => void) {
  const root = document.documentElement
  const mo = new MutationObserver(cb)
  mo.observe(root, { attributes: true, attributeFilter: ['class'] })
  return () => mo.disconnect()
}

function darkModeSnapshot() {
  return document.documentElement.classList.contains('dark')
}

function useIsDarkMode(): boolean {
  return useSyncExternalStore(subscribeDarkMode, darkModeSnapshot, () => false)
}

/** Readable on near-white (light) and dark panes without huge hue shift. */
function linkStrokeColor(accent: string, isDark: boolean, suspect: boolean): string {
  if (suspect) return isDark ? '#f87171' : '#b91c1c'
  if (isDark) return `color-mix(in srgb, ${accent} 80%, #f8fafc)`
  return `color-mix(in srgb, ${accent} 52%, #0f172a)`
}

/** XYFlow defaults markerUnits to strokeWidth — thick edges get comically large arrowheads. */
function linkMarkerEnd(stroke: string, lineWidthPx: number) {
  return {
    type: MarkerType.ArrowClosed,
    color: stroke,
    width: 12,
    height: 12,
    markerUnits: 'userSpaceOnUse',
    strokeWidth: Math.max(1.2, Math.min(1.75, lineWidthPx * 0.4)),
  } as const
}

// Node sizing scales smoothly with doc count
const NODE_MIN_W = 180
const NODE_MAX_W = 260
const NODE_MIN_H = 110
const NODE_MAX_H = 150

function sizeForCount(count: number, maxCount: number): { width: number; height: number; scale: number } {
  if (maxCount <= 0) return { width: NODE_MIN_W, height: NODE_MIN_H, scale: 0 }
  const scale = Math.min(1, Math.sqrt(count) / Math.sqrt(Math.max(maxCount, 1)))
  return {
    width: Math.round(NODE_MIN_W + (NODE_MAX_W - NODE_MIN_W) * scale),
    height: Math.round(NODE_MIN_H + (NODE_MAX_H - NODE_MIN_H) * scale),
    scale,
  }
}

// ────────────────────────────────────────────────────────────────────────────
// Custom React Flow node
// ────────────────────────────────────────────────────────────────────────────

interface TypeNodeData {
  docType: DocType
  count: number
  suspectCount: number
  width: number
  height: number
  [key: string]: unknown
}

function formatCount(n: number): string {
  return n.toLocaleString()
}

function TypeNode({ data }: { data: TypeNodeData }) {
  const style = TYPE_STYLE[data.docType]
  const Icon = style.icon
  return (
    <div
      style={{ width: data.width, height: data.height }}
      className={`group relative overflow-hidden rounded-xl border border-border border-t-4 ${style.borderTop} ${style.surface} shadow-md ring-1 ring-black/5 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg dark:shadow-black/40 dark:ring-white/5 cursor-pointer`}
    >
      <Handle type="target" position={Position.Left} style={{ opacity: 0, pointerEvents: 'none' }} />

      <div className="flex h-full flex-col justify-between p-3">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0">
            <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${style.iconChip}`}>
              <Icon className="h-4 w-4" />
            </div>
            <div className="min-w-0">
              <div className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground leading-tight">
                {data.docType}
              </div>
              <div className="text-xs font-medium text-foreground leading-tight truncate">
                {DOC_TYPE_LABELS[data.docType]}
              </div>
            </div>
          </div>
          {data.suspectCount > 0 && (
            <span
              title={`${data.suspectCount} suspect link${data.suspectCount === 1 ? '' : 's'}`}
              className="inline-flex items-center gap-1 rounded-full bg-red-500/15 px-1.5 py-0.5 text-[10px] font-semibold text-red-600 dark:text-red-400"
            >
              <AlertTriangle className="h-2.5 w-2.5" />
              {data.suspectCount}
            </span>
          )}
        </div>

        <div className="flex items-end justify-between gap-2">
          <div className={`text-3xl font-bold leading-none tabular-nums tracking-tight ${style.countText}`}>
            {formatCount(data.count)}
          </div>
          <div className="text-[10px] uppercase tracking-wide text-muted-foreground pb-0.5">
            {data.count === 1 ? 'doc' : 'docs'}
          </div>
        </div>
      </div>

      <Handle type="source" position={Position.Right} style={{ opacity: 0, pointerEvents: 'none' }} />
    </div>
  )
}

const nodeTypes = { typeNode: TypeNode }

/** Call fitView only when layout changes — not on every ReactFlow re-render (fixes zoom +/- resetting). */
function FitViewOnLayout({ layoutToken }: { layoutToken: number }) {
  const { fitView } = useReactFlow()
  useEffect(() => {
    if (layoutToken === 0) return
    const id = requestAnimationFrame(() => {
      fitView({ padding: 0.25, duration: 0 })
    })
    return () => cancelAnimationFrame(id)
  }, [layoutToken, fitView])
  return null
}

// ────────────────────────────────────────────────────────────────────────────
// Aggregation
// ────────────────────────────────────────────────────────────────────────────

interface AggregatedEdge {
  source: DocType
  target: DocType
  count: number
  suspectCount: number
  roles: Map<string, number>
}

function aggregateEdges(
  links: { source_type: string; target_type: string; role: string; suspect: boolean }[],
  docTypesPresent: Set<DocType>,
): AggregatedEdge[] {
  const map = new Map<string, AggregatedEdge>()
  for (const link of links) {
    const src = link.source_type as DocType
    const tgt = link.target_type as DocType
    if (!docTypesPresent.has(src) || !docTypesPresent.has(tgt)) continue
    const key = `${src}->${tgt}`
    let agg = map.get(key)
    if (!agg) {
      agg = { source: src, target: tgt, count: 0, suspectCount: 0, roles: new Map() }
      map.set(key, agg)
    }
    agg.count += 1
    if (link.suspect) agg.suspectCount += 1
    agg.roles.set(link.role, (agg.roles.get(link.role) ?? 0) + 1)
  }
  return Array.from(map.values())
}

function rolesSummary(roles: Map<string, number>): string {
  const sorted = Array.from(roles.entries()).sort((a, b) => b[1] - a[1])
  return sorted.map(([role, n]) => `${n} ${role.replace(/_/g, ' ')}`).join(', ')
}

function strokeWidthForCount(count: number, maxCount: number): number {
  if (maxCount <= 0) return 1
  const scale = Math.sqrt(count) / Math.sqrt(maxCount)
  return Math.max(1.75, Math.min(4.5, scale * 4.5))
}

// ────────────────────────────────────────────────────────────────────────────
// Layout (dagre, left-to-right)
// ────────────────────────────────────────────────────────────────────────────

function applyDagreLayout(nodes: Node[], edges: Edge[]): Node[] {
  const g = new dagre.graphlib.Graph()
  g.setDefaultEdgeLabel(() => ({}))
  g.setGraph({ rankdir: 'LR', nodesep: 70, ranksep: 110, marginx: 30, marginy: 30 })
  nodes.forEach((n) => {
    const data = n.data as TypeNodeData
    g.setNode(n.id, { width: data.width, height: data.height })
  })
  // Skip self-loops in dagre to avoid layout artifacts
  edges.filter((e) => e.source !== e.target).forEach((e) => g.setEdge(e.source, e.target))
  dagre.layout(g)
  return nodes.map((n) => {
    const pos = g.node(n.id)
    const data = n.data as TypeNodeData
    return { ...n, position: { x: pos.x - data.width / 2, y: pos.y - data.height / 2 } }
  })
}

// ────────────────────────────────────────────────────────────────────────────
// Component
// ────────────────────────────────────────────────────────────────────────────

interface Props {
  projectId: number
  prefix: string
}

export default function ProjectDocTopology({ projectId, prefix }: Props) {
  const navigate = useNavigate()
  const isDark = useIsDarkMode()
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([])
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([])
  const [hoveredEdgeId, setHoveredEdgeId] = useState<string | null>(null)
  /** Incremented only in `rebuild` so we fit the viewport after layout, not on hover/zoom. */
  const [layoutToken, setLayoutToken] = useState(0)

  const { data: docs, isLoading: docsLoading } = useQuery({
    queryKey: ['project-docs-shell', prefix],
    queryFn: () => docsApi.list(prefix, { includeLinkCounts: true }),
    enabled: !!prefix,
  })

  const { data: links, isLoading: linksLoading } = useQuery({
    queryKey: ['project-links', projectId],
    queryFn: () => linksApi.list({ project_id: projectId }),
    enabled: !!projectId,
  })

  // Per-type doc counts and suspect totals
  const typeCounts = useMemo(() => {
    const counts = new Map<DocType, { count: number; suspect: number }>()
    if (!docs) return counts
    for (const d of docs) {
      const t = d.doc_type as DocType
      const cur = counts.get(t) ?? { count: 0, suspect: 0 }
      cur.count += 1
      cur.suspect += d.suspect_links
      counts.set(t, cur)
    }
    return counts
  }, [docs])

  const presentTypes = useMemo<DocType[]>(
    () => TYPE_ORDER.filter((t) => (typeCounts.get(t)?.count ?? 0) > 0),
    [typeCounts],
  )

  const aggregatedEdges = useMemo<AggregatedEdge[]>(() => {
    if (!links) return []
    return aggregateEdges(links, new Set(presentTypes))
  }, [links, presentTypes])

  const rebuild = useCallback(() => {
    if (presentTypes.length === 0) {
      setNodes([])
      setEdges([])
      return
    }

    const maxCount = Math.max(...presentTypes.map((t) => typeCounts.get(t)?.count ?? 0))

    const newNodes: Node[] = presentTypes.map((t) => {
      const stats = typeCounts.get(t)!
      const size = sizeForCount(stats.count, maxCount)
      return {
        id: t,
        type: 'typeNode' as const,
        position: { x: 0, y: 0 },
        data: {
          docType: t,
          count: stats.count,
          suspectCount: stats.suspect,
          width: size.width,
          height: size.height,
        } satisfies TypeNodeData,
      }
    })

    const maxEdgeCount = aggregatedEdges.reduce((m, e) => Math.max(m, e.count), 0)

    const newEdges: Edge[] = aggregatedEdges.map((e) => {
      const isSelfLoop = e.source === e.target
      const hasSuspect = e.suspectCount > 0
      const stroke = linkStrokeColor(TYPE_STYLE[e.source].accent, isDark, hasSuspect)
      const width = strokeWidthForCount(e.count, maxEdgeCount)
      const id = `${e.source}->${e.target}`
      return {
        id,
        source: e.source,
        target: e.target,
        type: 'smoothstep',
        animated: hasSuspect,
        label: `${e.count}${hasSuspect ? ` · ${e.suspectCount} suspect` : ''}`,
        labelStyle: { fontSize: 11, fontWeight: 600, fill: EDGE_LABEL_FG },
        labelBgStyle: {
          fill: EDGE_LABEL_BG,
          fillOpacity: 0.98,
          stroke: EDGE_LABEL_OUTLINE,
          strokeWidth: 1,
        },
        labelBgPadding: [7, 4],
        labelBgBorderRadius: 7,
        interactionWidth: 22,
        pathOptions: isSelfLoop
          ? { borderRadius: 22, offset: 32 }
          : { borderRadius: 11 },
        style: {
          stroke,
          strokeWidth: width,
          strokeLinecap: 'round',
          strokeLinejoin: 'round',
          strokeDasharray: hasSuspect ? '8 4' : isSelfLoop ? '4 3' : undefined,
        },
        markerEnd: linkMarkerEnd(stroke, width),
        data: { roles: e.roles, count: e.count, suspectCount: e.suspectCount },
      } as Edge
    })

    setNodes(applyDagreLayout(newNodes, newEdges))
    setEdges(newEdges)
    setLayoutToken((t) => t + 1)
  }, [presentTypes, typeCounts, aggregatedEdges, isDark, setNodes, setEdges])

  useEffect(() => { rebuild() }, [rebuild])

  const onNodeClick = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      const data = node.data as unknown as TypeNodeData
      navigate(`/projects/${prefix}/docs?type=${data.docType}`)
    },
    [navigate, prefix],
  )

  // ─────────── Loading / empty states ───────────

  if (docsLoading || linksLoading) {
    return (
      <div className="flex h-[60vh] min-h-[480px] items-center justify-center rounded-xl border border-border bg-card text-sm text-muted-foreground">
        Loading topology…
      </div>
    )
  }

  if (presentTypes.length === 0) {
    return (
      <div className="flex h-[60vh] min-h-[480px] flex-col items-center justify-center rounded-xl border border-border bg-card text-center">
        <Layers className="h-14 w-14 text-muted-foreground/50 mb-4" />
        <h3 className="text-lg font-semibold text-foreground">No documents yet</h3>
        <p className="mt-1 max-w-sm text-sm text-muted-foreground">
          Add requirements, specifications, or other documents to see the project topology.
        </p>
      </div>
    )
  }

  const hoveredEdge = hoveredEdgeId
    ? aggregatedEdges.find((e) => `${e.source}->${e.target}` === hoveredEdgeId)
    : null

  const totalDocs = presentTypes.reduce((s, t) => s + (typeCounts.get(t)?.count ?? 0), 0)
  const totalLinks = aggregatedEdges.reduce((s, e) => s + e.count, 0)
  const totalSuspect = aggregatedEdges.reduce((s, e) => s + e.suspectCount, 0)

  return (
    <div className="topology-canvas relative h-[60vh] min-h-[480px] overflow-hidden rounded-xl border border-border bg-card shadow-elegant">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClick}
        onEdgeMouseEnter={(_, edge) => setHoveredEdgeId(edge.id)}
        onEdgeMouseLeave={() => setHoveredEdgeId(null)}
        nodeTypes={nodeTypes}
        proOptions={{ hideAttribution: true }}
        nodesConnectable={false}
        edgesFocusable={false}
        minZoom={0.15}
        maxZoom={2.5}
        zoomOnScroll
        zoomOnPinch
        panOnScroll={false}
      >
        <FitViewOnLayout layoutToken={layoutToken} />
        <Background variant={BackgroundVariant.Dots} gap={18} size={1.2} className="opacity-50" />
        <Controls showInteractive={false} position="bottom-left" />

        {/* Top-left header / stats */}
        <Panel position="top-left" className="m-3">
          <div className="rounded-lg border border-border bg-card/95 backdrop-blur-sm shadow-sm px-3 py-2.5">
            <div className="flex items-center gap-2 text-foreground">
              <GitBranch className="h-4 w-4 text-primary" />
              <span className="text-sm font-semibold">Project Topology</span>
            </div>
            <div className="mt-1.5 flex items-center gap-3 text-[11px] text-muted-foreground">
              <span><span className="font-semibold text-foreground tabular-nums">{formatCount(totalDocs)}</span> docs</span>
              <span className="text-border">·</span>
              <span><span className="font-semibold text-foreground tabular-nums">{formatCount(totalLinks)}</span> links</span>
              {totalSuspect > 0 && (
                <>
                  <span className="text-border">·</span>
                  <span className="text-red-600 dark:text-red-400 font-semibold tabular-nums">
                    {formatCount(totalSuspect)} suspect
                  </span>
                </>
              )}
            </div>
          </div>
        </Panel>

        {/* Top-right: reset layout */}
        <Panel position="top-right" className="m-3">
          <button
            onClick={rebuild}
            className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-card/95 backdrop-blur-sm px-2.5 py-1.5 text-xs font-medium text-foreground shadow-sm hover:bg-accent transition-colors"
            title="Reset layout"
          >
            <RotateCcw className="h-3.5 w-3.5" />
            Reset layout
          </button>
        </Panel>

        {/* Hovered edge detail */}
        {hoveredEdge && (
          <Panel position="bottom-left" className="m-3">
            <div className="rounded-lg border border-border bg-card/95 backdrop-blur-sm shadow-md px-3 py-2 max-w-sm">
              <div className="flex items-center gap-2 text-xs font-semibold text-foreground">
                <span style={{ color: TYPE_STYLE[hoveredEdge.source].accent }}>
                  {DOC_TYPE_LABELS[hoveredEdge.source]}
                </span>
                <span className="text-muted-foreground">→</span>
                <span style={{ color: TYPE_STYLE[hoveredEdge.target].accent }}>
                  {DOC_TYPE_LABELS[hoveredEdge.target]}
                </span>
              </div>
              <div className="mt-1 text-[11px] text-muted-foreground">
                {rolesSummary(hoveredEdge.roles)}
                {hoveredEdge.suspectCount > 0 && (
                  <span className="ml-1.5 text-red-600 dark:text-red-400 font-medium">
                    · {hoveredEdge.suspectCount} suspect
                  </span>
                )}
              </div>
            </div>
          </Panel>
        )}

        {/* Empty-links hint */}
        {edges.length === 0 && (
          <Panel position="bottom-center" className="m-3">
            <div className="rounded-lg border border-border bg-card/95 backdrop-blur-sm shadow-sm px-3 py-2 text-xs text-muted-foreground">
              No relationships between document types yet — link documents to see them here.
            </div>
          </Panel>
        )}
      </ReactFlow>
    </div>
  )
}
