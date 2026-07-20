import type { ReactNode } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { DOC_TYPE_LABELS, DOC_TYPE_COLORS, type DocType } from '../types/doc'
import { docRegistryListUrl } from '../lib/docRegistryParams'

const STATUS_COLORS: Record<string, string> = {
  Draft: 'bg-slate-500/10 text-slate-700 dark:text-slate-400',
  Review: 'bg-amber-500/10 text-amber-700 dark:text-amber-400',
  Approved: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400',
  Rejected: 'bg-red-500/10 text-red-700 dark:text-red-400',
  Obsolete: 'bg-gray-500/10 text-gray-500',
  Open: 'bg-red-500/10 text-red-700 dark:text-red-400',
  Monitoring: 'bg-amber-500/10 text-amber-700 dark:text-amber-400',
  Mitigated: 'bg-violet-500/10 text-violet-700 dark:text-violet-400',
  Accepted: 'bg-blue-500/10 text-blue-700 dark:text-blue-400',
  Closed: 'bg-slate-500/10 text-slate-700 dark:text-slate-400',
  Submitted: 'bg-blue-500/10 text-blue-700 dark:text-blue-400',
  'Under Review': 'bg-violet-500/10 text-violet-700 dark:text-violet-400',
  Analysis: 'bg-violet-500/10 text-violet-700 dark:text-violet-400',
  Implemented: 'bg-violet-500/10 text-violet-700 dark:text-violet-400',
  Active: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400',
  Deprecated: 'bg-red-500/10 text-red-700 dark:text-red-400',
  Final: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400',
  Superseded: 'bg-gray-500/10 text-gray-500',
  Verified: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400',
}

const PRIORITY_COLORS: Record<string, string> = {
  Low: 'bg-gray-500/10 text-gray-700 dark:text-gray-400',
  Medium: 'bg-blue-500/10 text-blue-700 dark:text-blue-400',
  High: 'bg-orange-500/10 text-orange-700 dark:text-orange-400',
  Critical: 'bg-red-500/10 text-red-700 dark:text-red-400',
}

export function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`px-2 py-1 rounded-full text-xs font-medium ${STATUS_COLORS[status] || 'bg-muted text-muted-foreground'}`}>
      {status}
    </span>
  )
}

export function PriorityBadge({ priority }: { priority: string | null | undefined }) {
  if (!priority) return null
  return (
    <span className={`px-2 py-1 rounded-full text-xs font-medium ${PRIORITY_COLORS[priority] || 'bg-muted text-muted-foreground'}`}>
      {priority}
    </span>
  )
}

export function DocTypeBadge({ docType }: { docType: DocType }) {
  const label = DOC_TYPE_LABELS[docType] || docType
  const color = DOC_TYPE_COLORS[docType] || 'bg-muted text-muted-foreground'
  return (
    <span className={`px-2 py-0.5 rounded-md text-[11px] font-semibold ${color}`}>
      {label}
    </span>
  )
}

export function MetaItem({ label, value, mono = false }: { label: string; value: ReactNode; mono?: boolean }) {
  return (
    <div>
      <div className="text-xs uppercase tracking-wide text-muted-foreground mb-1">{label}</div>
      <div className={`${mono ? 'font-mono' : ''} text-foreground text-sm`}>{value}</div>
    </div>
  )
}

export function SectionCard({ title, children, actions }: { title: string; children: ReactNode; actions?: ReactNode }) {
  return (
    <div className="bg-card rounded-lg shadow-elegant p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-foreground">{title}</h3>
        {actions}
      </div>
      {children}
    </div>
  )
}

interface DocDetailShellProps {
  projectPrefix: string
  docType: DocType
  docCode: string
  title: string
  status: string
  priority?: string | null
  actions?: ReactNode
  rightRail?: ReactNode
  children: ReactNode
  backTo?: string
}

export default function DocDetailShell({
  projectPrefix,
  docType,
  docCode,
  title,
  status,
  priority,
  actions,
  rightRail,
  children,
  backTo,
}: DocDetailShellProps) {
  const location = useLocation()
  const navigate = useNavigate()
  const returnTo = backTo
    || (location.state as { returnTo?: string } | null)?.returnTo
    || docRegistryListUrl(projectPrefix, docType)

  const handleBack = () => {
    if (window.history.length > 1) {
      navigate(-1)
    } else {
      navigate(returnTo)
    }
  }

  return (
    <div className="animate-fade-in space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-4">
          <button onClick={handleBack} className="p-2 hover:bg-accent/50 rounded-md" aria-label="Go back">
            <ArrowLeft className="h-5 w-5 text-muted-foreground" />
          </button>
          <div>
            <div className="flex items-center gap-3 flex-wrap mb-1">
              <span className="font-mono text-sm text-primary font-semibold">{docCode}</span>
              <DocTypeBadge docType={docType} />
              <StatusBadge status={status} />
              {priority && <PriorityBadge priority={priority} />}
            </div>
            <h2 className="text-2xl font-bold text-foreground">{title}</h2>
          </div>
        </div>
        {actions && (
          <div className="flex items-center gap-2 shrink-0">
            {actions}
          </div>
        )}
      </div>

      {rightRail ? (
        <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_320px] gap-6">
          <div className="space-y-6">{children}</div>
          <div className="space-y-6">{rightRail}</div>
        </div>
      ) : (
        <div className="space-y-6">{children}</div>
      )}
    </div>
  )
}
