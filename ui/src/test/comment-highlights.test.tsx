// @vitest-environment jsdom
import { cleanup, fireEvent, render, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { CommentAnchor } from '../api/client'

const DocEditor = (await import('../components/editor/DocEditor')).default

const EMPTY_RECT = { x: 0, y: 0, top: 0, left: 0, right: 0, bottom: 0, width: 0, height: 0, toJSON: () => ({}) } as DOMRect

const content = {
  type: 'doc',
  content: [
    { type: 'paragraph', content: [{ type: 'text', text: 'The brake shall engage.' }] },
    { type: 'paragraph', content: [{ type: 'text', text: 'The brake shall release.' }] },
  ],
}
const secondBrake: CommentAnchor = { exact: 'brake', prefix: 'engage.\nThe ', suffix: ' shall release.' }
const gone: CommentAnchor = { exact: 'accelerator', prefix: 'The ', suffix: '.' }

/** The read-only surface ProseMirror manages. */
async function surface(container: HTMLElement): Promise<HTMLElement> {
  await waitFor(() => expect(container.querySelector('.ProseMirror')).toBeTruthy())
  return container.querySelector('.ProseMirror') as HTMLElement
}

/** Select a range of a text node in the page the way a pointer does. */
function selectText(node: Node, from: number, to: number) {
  const range = document.createRange()
  range.setStart(node, from)
  range.setEnd(node, to)
  const selection = window.getSelection()!
  selection.removeAllRanges()
  selection.addRange(range)
}

beforeEach(() => {
  if (typeof globalThis.CSS?.escape !== 'function') {
    globalThis.CSS = { ...(globalThis.CSS ?? {}), escape: (value: string) => value } as never
  }
  Element.prototype.scrollIntoView = vi.fn()
  Element.prototype.getClientRects = (() => Object.assign([], { item: () => null })) as never
  Element.prototype.getBoundingClientRect = () => EMPTY_RECT
  Range.prototype.getClientRects = (() => Object.assign([], { item: () => null })) as never
  Range.prototype.getBoundingClientRect = () => EMPTY_RECT
})

afterEach(() => {
  window.getSelection()?.removeAllRanges()
  cleanup()
})

describe('comment highlights in the document text', () => {
  it('highlights the passage whose context matches, and the selected thread more strongly', async () => {
    const { container, rerender } = render(<DocEditor content={content} editable={false} commentThreads={[{ id: 7, anchor: secondBrake, selected: false }, { id: 8, anchor: gone, selected: false }]} />)
    const text = await surface(container)
    await waitFor(() => expect(text.querySelector('[data-comment-id="7"]')).toBeTruthy())
    const mark = text.querySelector('[data-comment-id="7"]')!
    expect(mark.textContent).toBe('brake')
    expect(mark.closest('p')?.textContent).toBe('The brake shall release.')
    expect(mark.classList.contains('comment-highlight')).toBe(true)
    expect(mark.classList.contains('comment-highlight-selected')).toBe(false)
    expect(text.querySelector('[data-comment-id="8"]')).toBeNull()
    expect(text.querySelectorAll('.comment-highlight')).toHaveLength(1)

    rerender(<DocEditor content={content} editable={false} commentThreads={[{ id: 7, anchor: secondBrake, selected: true }]} />)
    await waitFor(() => expect(text.querySelector('[data-comment-id="7"]')?.classList.contains('comment-highlight-selected')).toBe(true))
    expect(text.getAttribute('contenteditable')).toBe('false')
  })

  it('removes a highlight when its thread leaves the list', async () => {
    const { container, rerender } = render(<DocEditor content={content} editable={false} commentThreads={[{ id: 7, anchor: secondBrake, selected: false }]} />)
    const text = await surface(container)
    await waitFor(() => expect(text.querySelector('[data-comment-id="7"]')).toBeTruthy())
    rerender(<DocEditor content={content} editable={false} commentThreads={[]} />)
    await waitFor(() => expect(text.querySelector('.comment-highlight')).toBeNull())
  })

  it('reports the thread of a clicked highlight', async () => {
    const onThreadClick = vi.fn()
    const { container } = render(<DocEditor content={content} editable={false} commentThreads={[{ id: 7, anchor: secondBrake, selected: false }]} onThreadClick={onThreadClick} />)
    const text = await surface(container)
    await waitFor(() => expect(text.querySelector('[data-comment-id="7"]')).toBeTruthy())
    fireEvent.click(text.querySelector('[data-comment-id="7"]')!)
    expect(onThreadClick).toHaveBeenCalledWith(7)
    onThreadClick.mockClear()
    fireEvent.click(text.querySelector('p')!)
    expect(onThreadClick).not.toHaveBeenCalled()
  })

  it('reports a text selection as a quote with its context, and its end as null', async () => {
    const onCommentSelection = vi.fn()
    const { container } = render(<DocEditor content={content} editable={false} onCommentSelection={onCommentSelection} />)
    const text = await surface(container)
    const second = text.querySelectorAll('p')[1].firstChild!
    selectText(second, 4, 9)
    fireEvent.mouseUp(text)
    expect(onCommentSelection).toHaveBeenLastCalledWith({ anchor: { exact: 'brake', prefix: 'The brake shall engage.\nThe ', suffix: ' shall release.' }, rect: EMPTY_RECT })
    window.getSelection()!.collapseToEnd()
    fireEvent.keyUp(text)
    expect(onCommentSelection).toHaveBeenLastCalledWith(null)
  })

  it('ignores a selection outside the document text', async () => {
    const onCommentSelection = vi.fn()
    const outside = document.createElement('p')
    outside.textContent = 'Elsewhere on the page'
    document.body.appendChild(outside)
    try {
      const { container } = render(<DocEditor content={content} editable={false} onCommentSelection={onCommentSelection} />)
      const text = await surface(container)
      selectText(outside.firstChild!, 0, 9)
      fireEvent.mouseUp(text)
      expect(onCommentSelection).toHaveBeenLastCalledWith(null)
    } finally {
      outside.remove()
    }
  })
})
