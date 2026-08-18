import { useEffect, useState } from 'react'

/**
 * A value that only changes once it has stopped changing for `delay` ms.
 *
 * The registry search box writes every keystroke straight to the address bar so
 * the input stays responsive and the filter stays shareable. The server does not
 * need to hear about every one of those - typing "torque" would otherwise be six
 * queries, five of which are already stale by the time they land.
 */
export function useDebounced<T>(value: T, delay: number): T {
  const [settled, setSettled] = useState(value)

  useEffect(() => {
    const timer = setTimeout(() => setSettled(value), delay)
    return () => clearTimeout(timer)
  }, [value, delay])

  return settled
}
