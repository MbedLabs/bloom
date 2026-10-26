import type { ReactNode } from 'react'

export default function DocumentDetailColumns({ children, rightRail }: Readonly<{ children: ReactNode; rightRail: ReactNode }>) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_320px] items-start gap-6">
      <div className="min-w-0 space-y-6">{children}</div>
      <aside aria-label="Document side panel" className="order-first min-w-0 space-y-6 lg:order-last lg:sticky lg:top-4 lg:max-h-[calc(100dvh-6rem)] lg:overflow-y-auto themed-scrollbar">
        {rightRail}
      </aside>
    </div>
  )
}
