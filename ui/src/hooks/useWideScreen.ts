import { useLayoutEffect, useState } from 'react'

/** True while the window is at least as wide as the given number of pixels; the fallback value without window.matchMedia. */
export function useWideScreen(width: number, fallback = false): boolean {
  const query = `(min-width: ${width}px)`
  const [wide, setWide] = useState(() => typeof window !== 'undefined' && typeof window.matchMedia === 'function' ? window.matchMedia(query).matches : fallback)
  useLayoutEffect(() => {
    if (typeof window.matchMedia !== 'function') return
    const media = window.matchMedia(query)
    const update = () => setWide(media.matches)
    update()
    media.addEventListener('change', update)
    return () => media.removeEventListener('change', update)
  }, [query])
  return wide
}
