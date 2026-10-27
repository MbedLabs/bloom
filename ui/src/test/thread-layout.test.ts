import { describe, expect, it } from 'vitest'

import { THREAD_GAP, stackThreads } from '../lib/threadLayout'

type Item = { id: number; desired: number; height: number }

/** Whether any two cards overlap or sit closer than the gap. */
function overlaps(items: Item[], tops: Record<number, number>) {
  const placed = [...items].sort((left, right) => tops[left.id] - tops[right.id])
  return placed.some((item, index) => index > 0 && tops[item.id] < tops[placed[index - 1].id] + placed[index - 1].height + THREAD_GAP)
}

describe('stackThreads', () => {
  it('places each card level with its passage when there is room', () => {
    const items = [{ id: 1, desired: 100, height: 50 }, { id: 2, desired: 300, height: 50 }]
    expect(stackThreads(items, null, 0)).toEqual({ 1: 100, 2: 300 })
  })

  it('stacks overlapping cards downward in text order without overlap', () => {
    const items = [{ id: 3, desired: 400, height: 30 }, { id: 2, desired: 110, height: 40 }, { id: 1, desired: 100, height: 50 }]
    const tops = stackThreads(items, null, 0)
    expect(tops).toEqual({ 1: 100, 2: 100 + 50 + THREAD_GAP, 3: 400 })
    expect(overlaps(items, tops)).toBe(false)
  })

  it('pushes a later card down past a stacked one', () => {
    const items = [{ id: 1, desired: 100, height: 80 }, { id: 2, desired: 120, height: 80 }, { id: 3, desired: 200, height: 20 }]
    const tops = stackThreads(items, null, 0)
    expect(tops[3]).toBe(tops[2] + 80 + THREAD_GAP)
    expect(overlaps(items, tops)).toBe(false)
  })

  it('never places a card above minTop', () => {
    const items = [{ id: 1, desired: 10, height: 50 }, { id: 2, desired: 20, height: 50 }]
    const tops = stackThreads(items, null, 80)
    expect(tops[1]).toBe(80)
    expect(tops[2]).toBe(80 + 50 + THREAD_GAP)
  })

  it('keeps the selected card level with its passage and moves earlier cards up', () => {
    const items = [{ id: 1, desired: 100, height: 50 }, { id: 2, desired: 110, height: 40 }, { id: 3, desired: 120, height: 30 }]
    const tops = stackThreads(items, 2, 0)
    expect(tops[2]).toBe(110)
    expect(tops[1]).toBe(110 - 50 - THREAD_GAP)
    expect(tops[3]).toBe(110 + 40 + THREAD_GAP)
    expect(overlaps(items, tops)).toBe(false)
  })

  it('moves the selected card level with its passage although it would otherwise stack lower', () => {
    const items = [{ id: 1, desired: 200, height: 100 }, { id: 2, desired: 210, height: 40 }]
    expect(stackThreads(items, null, 0)[2]).toBe(200 + 100 + THREAD_GAP)
    expect(stackThreads(items, 2, 0)[2]).toBe(210)
  })

  it('shifts the whole stack down when moving earlier cards up would cross minTop', () => {
    const items = [{ id: 1, desired: 20, height: 50 }, { id: 2, desired: 30, height: 40 }]
    const tops = stackThreads(items, 2, 10)
    expect(Math.min(...Object.values(tops))).toBe(10)
    expect(tops).toEqual({ 1: 10, 2: 10 + 50 + THREAD_GAP })
    expect(overlaps(items, tops)).toBe(false)
  })

  it('ignores a selected id that is not among the cards', () => {
    const items = [{ id: 1, desired: 100, height: 50 }, { id: 2, desired: 110, height: 40 }]
    expect(stackThreads(items, 99, 0)).toEqual(stackThreads(items, null, 0))
  })
})
