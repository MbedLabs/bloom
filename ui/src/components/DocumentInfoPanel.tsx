import type { ReactNode } from 'react'
import { Info, X } from 'lucide-react'

/** One section of the document information panel, with a visible heading when it has a title. */
export function InfoSection({ title, label, children }: Readonly<{ title?: string; label?: string; children: ReactNode }>) {
  return (
    <section aria-label={title ?? label} className="space-y-3 px-4 py-4">
      {title && <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{title}</h3>}
      {children}
    </section>
  )
}

/** The document's workflow, details and metadata beside the document, hidden and shown with a button like the outline. */
export default function DocumentInfoPanel({ collapsed, onToggle: toggle, children }: Readonly<{ collapsed: boolean; onToggle: () => void; children: ReactNode }>) {
  if (collapsed) {
    return (
      <aside aria-label="Document information">
        <button
          type="button"
          onClick={toggle}
          aria-expanded={false}
          title="Show document information"
          className="inline-flex items-center gap-1.5 rounded-md border border-border bg-card px-3 py-1.5 text-sm text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
        >
          <Info className="h-4 w-4" aria-hidden="true" />
          Show document information
        </button>
      </aside>
    )
  }

  return (
    <aside aria-label="Document information" className="bg-card rounded-lg shadow-elegant border border-border">
      <div className="flex items-center justify-between border-b border-border px-4 py-2">
        <span className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          <Info className="h-3.5 w-3.5" aria-hidden="true" />
          Document information
        </span>
        <button
          type="button"
          onClick={toggle}
          aria-expanded={true}
          aria-label="Hide document information"
          title="Hide document information"
          className="p-1 rounded text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
        >
          <X className="h-3.5 w-3.5" aria-hidden="true" />
        </button>
      </div>
      <div className="divide-y divide-border">{children}</div>
    </aside>
  )
}
