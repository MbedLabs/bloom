import { useState } from 'react'

const COLLAPSED_KEY = 'bloom-document-info-collapsed'

/** Whether the reader last hid the document information panel. */
function storedCollapsed(): boolean {
  return globalThis.localStorage?.getItem(COLLAPSED_KEY) === 'true'
}

/** Whether the document information panel is hidden, opening as the reader last left it, and the toggle that hides or shows it and remembers the choice. */
export function useInfoPanelCollapsed(): [boolean, () => void] {
  const [collapsed, setCollapsed] = useState(storedCollapsed)
  const toggle = () => {
    const next = !collapsed
    setCollapsed(next)
    globalThis.localStorage?.setItem(COLLAPSED_KEY, String(next))
  }
  return [collapsed, toggle]
}
