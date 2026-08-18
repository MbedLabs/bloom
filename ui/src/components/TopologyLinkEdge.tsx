import {
  BaseEdge,
  EdgeLabelRenderer,
  getBezierPath,
  type EdgeProps,
} from '@xyflow/react'

export interface RoleEntry {
  role: string
  displayLabel: string
  count: number
  suspectCount: number
}

export interface TopologyLinkData {
  totalCount: number
  totalSuspect: number
  roles: RoleEntry[]
  isSyntheticInverse: boolean
  curvature: number
  [key: string]: unknown
}

export default function TopologyLinkEdge({
  id,
  sourceX,
  sourceY,
  sourcePosition,
  targetX,
  targetY,
  targetPosition,
  style,
  markerEnd,
  markerStart,
  data,
}: EdgeProps) {
  const d = data as unknown as TopologyLinkData

  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
    curvature: d.curvature ?? 0.25,
  })

  return (
    <>
      <BaseEdge id={id} path={edgePath} style={style} markerEnd={markerEnd} markerStart={markerStart} />
      <EdgeLabelRenderer>
        <div
          style={{
            position: 'absolute',
            transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
            pointerEvents: 'all',
          }}
          className="nodrag nopan"
        >
          <span
            className={`
              inline-flex items-center rounded-full px-1.5 py-0.5 text-[10px] font-semibold
              tabular-nums select-none shadow-sm
              bg-card/90 backdrop-blur-sm border border-border/50
              ${d.totalSuspect > 0 ? 'text-red-600 dark:text-red-400' : 'text-foreground'}
            `}
          >
            {d.totalCount}
          </span>
        </div>
      </EdgeLabelRenderer>
    </>
  )
}
