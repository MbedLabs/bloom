import type { Editor } from '@tiptap/react'

export interface HeadingItem {
  id: string
  level: number
  text: string
  pos: number
}

/** A heading counts as reached once its top is within this many px of the top. */
export const ACTIVE_HEADING_OFFSET = 96

export function extractHeadings(editor: Editor | null): HeadingItem[] {
  if (!editor) return []
  const headings: HeadingItem[] = []
  editor.state.doc.descendants((node, pos) => {
    if (node.type.name.startsWith('heading')) {
      headings.push({
        id: `heading-${pos}`,
        level: parseInt(node.attrs.level, 10),
        text: node.textContent || 'Untitled',
        pos,
      })
    }
  })
  return headings
}

/**
 * The DOM element rendering the heading at `pos`.
 *
 * `domAtPos(pos)` resolves the position *before* the node, which for a
 * top-level heading is the editor's own content element - so scrolling it into
 * view jumped to the top of the document no matter which entry was clicked.
 * `nodeDOM(pos)` addresses the node itself; the `domAtPos(pos + 1)` fallback
 * covers node views that do not expose a DOM node directly.
 */
export function headingElement(editor: Editor | null, pos: number): HTMLElement | null {
  if (!editor) return null
  const direct = editor.view.nodeDOM(pos)
  if (direct instanceof HTMLElement) return direct
  const { node } = editor.view.domAtPos(pos + 1)
  const el = node instanceof HTMLElement ? node : node.parentElement
  return el?.closest('h1, h2, h3, h4, h5, h6') ?? el
}

/**
 * The nearest ancestor that actually scrolls the document, so the outline can
 * follow the reader. The editor has no scroll box of its own - it grows and the
 * page scrolls around it - so this is usually the page's <main>.
 */
export function scrollParentOf(el: HTMLElement | null): HTMLElement | null {
  let node = el?.parentElement ?? null
  while (node) {
    const overflowY = getComputedStyle(node).overflowY
    if (overflowY === 'auto' || overflowY === 'scroll') return node
    node = node.parentElement
  }
  return null
}

/** Heading whose element sits at or just above the top of the viewport. */
export function activeHeadingAt(
  editor: Editor | null,
  headings: HeadingItem[],
  viewportTop: number,
): string | null {
  if (headings.length === 0) return null
  let active = headings[0].id
  for (const heading of headings) {
    const el = headingElement(editor, heading.pos)
    if (!el) continue
    if (el.getBoundingClientRect().top - viewportTop <= ACTIVE_HEADING_OFFSET) {
      active = heading.id
    } else {
      break
    }
  }
  return active
}

export function sameHeadings(a: HeadingItem[], b: HeadingItem[]): boolean {
  return (
    a.length === b.length &&
    a.every((h, i) => h.pos === b[i].pos && h.text === b[i].text && h.level === b[i].level)
  )
}

export function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^\w\s-]/g, '')
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-')
    .trim()
}
