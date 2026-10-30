/** The space between two stacked thread cards. */
export const THREAD_GAP = 8

/**
 * Where each thread card starts: level with its passage, stacked downward without overlap,
 * never above `minTop`, and the selected card level with its passage.
 */
export function stackThreads(
  items: { id: number; desired: number; height: number }[],
  selectedId: number | null,
  minTop: number,
): Record<number, number> {
  const sorted = [...items].sort((left, right) => left.desired - right.desired)
  const tops: Record<number, number> = {}
  const pivot = sorted.findIndex(item => item.id === selectedId)
  if (pivot < 0) {
    let next = minTop
    for (const item of sorted) {
      tops[item.id] = Math.max(item.desired, next)
      next = tops[item.id] + item.height + THREAD_GAP
    }
    return tops
  }
  tops[sorted[pivot].id] = Math.max(sorted[pivot].desired, minTop)
  let above = tops[sorted[pivot].id]
  for (let index = pivot - 1; index >= 0; index -= 1) {
    tops[sorted[index].id] = Math.min(sorted[index].desired, above - sorted[index].height - THREAD_GAP)
    above = tops[sorted[index].id]
  }
  let below = tops[sorted[pivot].id] + sorted[pivot].height + THREAD_GAP
  for (let index = pivot + 1; index < sorted.length; index += 1) {
    tops[sorted[index].id] = Math.max(sorted[index].desired, below)
    below = tops[sorted[index].id] + sorted[index].height + THREAD_GAP
  }
  const highest = Math.min(...Object.values(tops))
  if (highest < minTop) for (const id of Object.keys(tops)) tops[Number(id)] += minTop - highest
  return tops
}
