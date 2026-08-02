import { createContext } from 'react'

export type ToastVariant = 'success' | 'error' | 'info'

export interface ToastMessage {
  id: number
  message: string
  variant: ToastVariant
}

export interface ToastApi {
  notify: (message: string, variant?: ToastVariant) => void
  /** `saved('Requirement')` reads "Requirement saved". */
  saved: (subject: string) => void
  deleted: (subject: string) => void
  /** Reports the API's own reason rather than a generic failure. */
  failed: (action: string, error: unknown) => void
  dismiss: (id: number) => void
}

export const ToastContext = createContext<ToastApi | null>(null)
