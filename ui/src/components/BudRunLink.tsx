import { ExternalLink } from 'lucide-react'

import { buildBudRunUrl } from '../lib/budLinks'

type BudRunLinkProps = {
  runId: number | string | null | undefined
  className?: string
  label?: string
}

export default function BudRunLink({ runId, className, label }: BudRunLinkProps) {
  if (!runId) {
    return <span className={className || 'text-muted-foreground'}>Not recorded</span>
  }

  return (
    <a
      href={buildBudRunUrl(runId)}
      target="_blank"
      rel="noopener noreferrer"
      className={className || 'inline-flex items-center gap-1 text-primary hover:text-primary/80'}
    >
      <span>{label || `Bud run #${runId}`}</span>
      <ExternalLink className="h-3 w-3" />
    </a>
  )
}
