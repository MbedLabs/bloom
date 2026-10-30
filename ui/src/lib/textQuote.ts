import type { Node as ProseMirrorNode } from '@tiptap/pm/model'

import type { CommentAnchor } from '../api/client'

/** How many characters of the text before and after a passage a quote keeps. */
export const QUOTE_CONTEXT = 64

/** A document's plain text and, for each character, its position in the document. */
export interface PlainText {
  text: string
  positions: number[]
}

/** The label a leaf node such as a mention, a parameter or an artefact tag shows. */
function leafLabel(node: ProseMirrorNode): string {
  const attrs = node.attrs as { label?: unknown; id?: unknown }
  if (typeof attrs.label === 'string' && attrs.label) return attrs.label
  if (typeof attrs.id === 'string' || typeof attrs.id === 'number') return String(attrs.id)
  return ''
}

/**
 * The plain text of a document: the text of every text node, leaf nodes as their label,
 * and one line break between text blocks.
 */
export function plainText(doc: ProseMirrorNode): PlainText {
  let text = ''
  const positions: number[] = []
  let started = false
  doc.descendants((node, pos) => {
    if (node.isTextblock) {
      if (started) {
        text += '\n'
        positions.push(pos)
      }
      started = true
      return true
    }
    if (node.isText) {
      const value = node.text ?? ''
      for (let index = 0; index < value.length; index += 1) {
        text += value[index]
        positions.push(pos + index)
      }
      return false
    }
    if (node.isLeaf) {
      for (const character of leafLabel(node)) {
        text += character
        positions.push(pos)
      }
      return false
    }
    return true
  })
  return { text, positions }
}

/** The quote of the document range from `from` to `to`, or null for an empty range. */
export function quoteFor(doc: ProseMirrorNode, from: number, to: number): CommentAnchor | null {
  const { text, positions } = plainText(doc)
  const start = positions.findIndex((position) => position >= from)
  if (start < 0) return null
  let end = start
  while (end < positions.length && positions[end] < to) end += 1
  const exact = text.slice(start, end)
  if (!exact.trim()) return null
  return {
    exact,
    prefix: text.slice(Math.max(0, start - QUOTE_CONTEXT), start),
    suffix: text.slice(end, end + QUOTE_CONTEXT),
  }
}

/** The length of the common end of two strings. */
function commonEnd(left: string, right: string): number {
  let length = 0
  while (
    length < left.length &&
    length < right.length &&
    left[left.length - 1 - length] === right[right.length - 1 - length]
  ) {
    length += 1
  }
  return length
}

/** The length of the common start of two strings. */
function commonStart(left: string, right: string): number {
  let length = 0
  while (length < left.length && length < right.length && left[length] === right[length]) {
    length += 1
  }
  return length
}

/**
 * Where a quote lies in the text: the occurrence of its passage whose surroundings best
 * match its prefix and suffix, the first one on a tie; null when the passage is gone.
 */
export function findQuote(text: string, anchor: CommentAnchor): { start: number; end: number } | null {
  if (!anchor.exact) return null
  let best: { start: number; score: number } | null = null
  let index = text.indexOf(anchor.exact)
  while (index >= 0) {
    const before = text.slice(Math.max(0, index - anchor.prefix.length), index)
    const after = text.slice(index + anchor.exact.length, index + anchor.exact.length + anchor.suffix.length)
    const score = commonEnd(before, anchor.prefix) + commonStart(after, anchor.suffix)
    if (!best || score > best.score) best = { start: index, score }
    index = text.indexOf(anchor.exact, index + 1)
  }
  return best ? { start: best.start, end: best.start + anchor.exact.length } : null
}

/** The document range a quote covers now, or null when its passage is gone. */
export function rangeFor(doc: ProseMirrorNode, anchor: CommentAnchor): { from: number; to: number } | null {
  const { text, positions } = plainText(doc)
  const found = findQuote(text, anchor)
  if (!found || found.end <= found.start) return null
  return { from: positions[found.start], to: positions[found.end - 1] + 1 }
}
