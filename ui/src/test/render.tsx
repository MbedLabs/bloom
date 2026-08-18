import type { ReactElement } from 'react'
import { renderToString } from 'react-dom/server'

import { ToastProvider } from '../components/Toast'

/**
 * Render a page the way the app mounts it.
 *
 * Pages call `useToast`, which requires the provider that `main.tsx` wraps the
 * router in. Rendering a page bare throws, so tests go through here rather than
 * calling `renderToString` directly.
 */
export function renderWithToasts(element: ReactElement): string {
  return renderToString(<ToastProvider>{element}</ToastProvider>)
}

export const renderPage = renderWithToasts
