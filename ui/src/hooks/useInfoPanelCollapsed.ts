import { useState } from 'react'

import { useWideScreen } from './useWideScreen'

const COLLAPSED_KEY = 'bloom-document-info-collapsed'
const PANEL_SHOWN_FROM = 1280

/** Whether the reader last hid the document information panel. */
function storedCollapsed(): boolean {
  return globalThis.localStorage?.getItem(COLLAPSED_KEY) === 'true'
}

/** Whether the document information panel is hidden and the toggle that hides or shows it and remembers the choice. On a window at least 1280 pixels wide it opens as the reader last left it; on a narrower one it opens hidden. */
export function useInfoPanelCollapsed(): [boolean, () => void] {
  const wide = useWideScreen(PANEL_SHOWN_FROM, true)
  const [choice, setChoice] = useState<boolean | null>(null)
  const collapsed = choice ?? (!wide || storedCollapsed())
  const toggle = () => {
    const next = !collapsed
    setChoice(next)
    globalThis.localStorage?.setItem(COLLAPSED_KEY, String(next))
  }
  return [collapsed, toggle]
}
