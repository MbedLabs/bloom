/** The value for a percentage: the high one from 80, the middle one from 50, the low one below 50. */
export function percentTone<T>(percent: number, high: T, middle: T, low: T): T {
  if (percent >= 80) return high
  return percent >= 50 ? middle : low
}
