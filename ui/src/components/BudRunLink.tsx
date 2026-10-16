import ReportRequestAction from './ReportRequestAction'
import type { ReportSource } from './ReportRequestAction'
import { ExternalLink } from 'lucide-react'

import { buildBudRunUrl } from '../lib/budLinks'

type BudRunLinkProps = {
  runId: number | string | null | undefined
  className?: string
  label?: string
  source?: Omit<ReportSource, 'run_id'>
}

export default function BudRunLink({ runId, className, label, source }: Readonly<BudRunLinkProps>) {
  if (!runId) {
    return <span className={className || 'text-muted-foreground'}>Not recorded</span>
  }

  const runUrl = buildBudRunUrl(runId)
  return (
    <span className="inline-flex flex-wrap items-center gap-2">
      {runUrl ? <a href={runUrl} target="_blank" rel="noopener noreferrer"
        className={className || 'inline-flex items-center gap-1 text-primary hover:text-primary/80'}>
        <span>{label || `Bud run #${runId}`}</span><ExternalLink className="h-3 w-3" />
      </a> : <span className={className || 'text-muted-foreground'}>{label || `Bud run #${runId}`}</span>}
      {source && <ReportRequestAction source={{ ...source, run_id: Number(runId) }} />}
    </span>
  )
}
