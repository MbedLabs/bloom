/**
 * @vitest-environment jsdom
 */
import { describe, expect, it } from 'vitest'
import type { Editor } from '@tiptap/react'

import outlineSource from '../components/editor/OutlineSidebar.tsx?raw'
import {
  ACTIVE_HEADING_OFFSET,
  activeHeadingAt,
  headingElement,
  sameHeadings,
  type HeadingItem,
} from '../components/editor/outlineNavigation'

/**
 * Clicking an outline entry jumped to the top of the document every time.
 *
 * `domAtPos(pos)` resolves the position *before* a node; for a top-level
 * heading that is the editor's own content element, so `scrollIntoView` scrolled
 * the whole editor rather than the heading. `nodeDOM(pos)` addresses the heading
 * itself.
 */

function fakeEditor(nodes: Record<number, unknown>, contentRoot: unknown): Editor {
  return {
    view: {
      nodeDOM: (pos: number) => nodes[pos],
      domAtPos: () => ({ node: contentRoot, offset: 0 }),
    },
  } as unknown as Editor
}

function elementAt(top: number): HTMLElement {
  const el = document.createElement('h2')
  el.getBoundingClientRect = () => ({ top }) as DOMRect
  return el
}

describe('headingElement', () => {
  it('resolves the heading node itself', () => {
    const heading = elementAt(0)
    const editor = fakeEditor({ 12: heading }, null)
    expect(headingElement(editor, 12)).toBe(heading)
  })

  it('falls back to the element after the position when the node has no DOM', () => {
    const heading = elementAt(0)
    const text = document.createTextNode('Scope')
    heading.appendChild(text)
    const editor = fakeEditor({}, text)
    expect(headingElement(editor, 12)).toBe(heading)
  })

  it('returns null without an editor', () => {
    expect(headingElement(null, 0)).toBeNull()
  })
})

describe('activeHeadingAt', () => {
  const headings: HeadingItem[] = [
    { id: 'a', level: 1, text: 'A', pos: 0 },
    { id: 'b', level: 1, text: 'B', pos: 10 },
    { id: 'c', level: 1, text: 'C', pos: 20 },
  ]

  function editorWithTops(tops: number[]): Editor {
    const nodes: Record<number, unknown> = {}
    headings.forEach((h, i) => {
      nodes[h.pos] = elementAt(tops[i])
    })
    return fakeEditor(nodes, null)
  }

  it('picks the last heading scrolled past', () => {
    // A and B are above the fold, C is still below it.
    const editor = editorWithTops([-200, ACTIVE_HEADING_OFFSET - 1, 600])
    expect(activeHeadingAt(editor, headings, 0)).toBe('b')
  })

  it('falls back to the first heading at the top of the document', () => {
    const editor = editorWithTops([400, 800, 1200])
    expect(activeHeadingAt(editor, headings, 0)).toBe('a')
  })

  it('measures relative to the scroll container, not the window', () => {
    // Container starts 300px down the page, so a heading at 320 is barely past it.
    const editor = editorWithTops([320, 900, 1400])
    expect(activeHeadingAt(editor, headings, 300)).toBe('a')
  })

  it('has nothing to highlight without headings', () => {
    expect(activeHeadingAt(editorWithTops([0, 0, 0]), [], 0)).toBeNull()
  })
})

describe('sameHeadings', () => {
  const base: HeadingItem[] = [{ id: 'a', level: 1, text: 'Intro', pos: 0 }]

  it('treats an identical outline as unchanged', () => {
    expect(sameHeadings(base, [{ id: 'a', level: 1, text: 'Intro', pos: 0 }])).toBe(true)
  })

  it('notices a retitled heading', () => {
    expect(sameHeadings(base, [{ id: 'a', level: 1, text: 'Scope', pos: 0 }])).toBe(false)
  })

  it('notices a moved heading', () => {
    expect(sameHeadings(base, [{ id: 'a', level: 1, text: 'Intro', pos: 9 }])).toBe(false)
  })

  it('notices an added heading', () => {
    expect(sameHeadings(base, [...base, { id: 'b', level: 2, text: 'More', pos: 8 }])).toBe(false)
  })
})

describe('OutlineSidebar wiring', () => {
  it('scrolls the resolved heading into view', () => {
    expect(outlineSource).toContain('headingElement(editor, heading.pos)')
    expect(outlineSource).toContain("scrollIntoView({ behavior: 'smooth', block: 'start' })")
  })

  it('places the caret inside the heading rather than before it', () => {
    expect(outlineSource).toContain('setTextSelection(heading.pos + 1)')
  })

  it('tracks scrolling, not only the caret', () => {
    expect(outlineSource).toContain("addEventListener('scroll'")
    expect(outlineSource).toContain('scrollParentOf')
    expect(outlineSource).toContain("removeEventListener('scroll', onScroll)")
  })

  it('keeps the active entry visible in a long outline', () => {
    expect(outlineSource).toContain("scrollIntoView({ block: 'nearest' })")
  })

  it('does not rebuild the list on every keystroke', () => {
    expect(outlineSource).toContain('sameHeadings(current, next) ? current : next')
  })
})
