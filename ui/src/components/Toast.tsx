import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { AlertTriangle, CheckCircle2, Info, X } from 'lucide-react'

import { extractApiErrorMessage } from '../api/client'
import { ToastContext, type ToastApi, type ToastMessage, type ToastVariant } from './toastContext'

/** Errors stay until dismissed - they usually say something worth reading. */
const DISMISS_AFTER: Record<ToastVariant, number | null> = {
  success: 4000,
  info: 4000,
  error: null,
}

const VARIANT_STYLES: Record<ToastVariant, { wrapper: string; icon: string }> = {
  success: {
    wrapper:
      'border-emerald-300 bg-emerald-50 text-emerald-900 dark:border-emerald-500/40 dark:bg-emerald-500/10 dark:text-emerald-200',
    icon: 'text-emerald-600 dark:text-emerald-400',
  },
  error: {
    wrapper:
      'border-red-300 bg-red-50 text-red-900 dark:border-red-500/40 dark:bg-red-500/10 dark:text-red-200',
    icon: 'text-red-600 dark:text-red-400',
  },
  info: {
    wrapper:
      'border-blue-300 bg-blue-50 text-blue-900 dark:border-blue-500/40 dark:bg-blue-500/10 dark:text-blue-200',
    icon: 'text-blue-600 dark:text-blue-400',
  },
}

const ICONS: Record<ToastVariant, typeof CheckCircle2> = {
  success: CheckCircle2,
  error: AlertTriangle,
  info: Info,
}


/**
 * Save and delete feedback, in one place.
 *
 * Six detail pages each carried their own copy of a toast; every other mutation
 * in the app - the document editor's save and delete included - reported
 * nothing at all, or an inline banner that scrolled out of view. Deleting from
 * the editor just navigated away, which is indistinguishable from a misclick.
 */
export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastMessage[]>([])
  const nextId = useRef(1)

  const dismiss = useCallback((id: number) => {
    setToasts((current) => current.filter((toast) => toast.id !== id))
  }, [])

  const notify = useCallback((message: string, variant: ToastVariant = 'success') => {
    const id = nextId.current++
    setToasts((current) => [...current.slice(-2), { id, message, variant }])
  }, [])

  const api = useMemo<ToastApi>(
    () => ({
      notify,
      dismiss,
      saved: (subject: string) => notify(`${subject} saved`, 'success'),
      deleted: (subject: string) => notify(`${subject} deleted`, 'success'),
      failed: (action: string, error: unknown) =>
        notify(extractApiErrorMessage(error, `${action} failed`), 'error'),
    }),
    [dismiss, notify],
  )

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div
        className="fixed bottom-4 right-4 z-[60] flex flex-col gap-2"
        role="status"
        aria-live="polite"
      >
        {toasts.map((toast) => (
          <ToastItem key={toast.id} toast={toast} onDismiss={dismiss} />
        ))}
      </div>
    </ToastContext.Provider>
  )
}

function ToastItem({
  toast,
  onDismiss,
}: {
  toast: ToastMessage
  onDismiss: (id: number) => void
}) {
  const styles = VARIANT_STYLES[toast.variant]
  const Icon = ICONS[toast.variant]

  useEffect(() => {
    const after = DISMISS_AFTER[toast.variant]
    if (after == null) return
    const timer = setTimeout(() => onDismiss(toast.id), after)
    return () => clearTimeout(timer)
  }, [onDismiss, toast.id, toast.variant])

  return (
    <div
      className={`flex max-w-md items-start gap-2 rounded-md border px-4 py-3 text-sm shadow-lg animate-slide-in-left ${styles.wrapper}`}
    >
      <Icon className={`mt-0.5 h-4 w-4 shrink-0 ${styles.icon}`} />
      <span className="flex-1 break-words">{toast.message}</span>
      <button
        type="button"
        onClick={() => onDismiss(toast.id)}
        className="shrink-0 rounded p-0.5 opacity-60 transition-opacity hover:opacity-100"
        aria-label="Dismiss"
      >
        <X className="h-3.5 w-3.5" />
      </button>
    </div>
  )
}
