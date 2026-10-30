import { Extension, type Editor } from '@tiptap/core'
import { Plugin, PluginKey } from '@tiptap/pm/state'
import type { Node as ProseMirrorNode } from '@tiptap/pm/model'
import { Decoration, DecorationSet } from '@tiptap/pm/view'

import type { CommentAnchor } from '../../api/client'
import { rangeFor } from '../../lib/textQuote'

/** A thread whose quoted passage is highlighted in the text. */
export interface HighlightedThread {
  id: number
  anchor: CommentAnchor
  selected: boolean
}

export const commentHighlightsKey = new PluginKey<DecorationSet>('commentHighlights')

/** The decorations over each thread's passage found in the document. */
function decorate(doc: ProseMirrorNode, threads: HighlightedThread[]): DecorationSet {
  const decorations: Decoration[] = []
  for (const thread of threads) {
    const range = rangeFor(doc, thread.anchor)
    if (!range) continue
    decorations.push(
      Decoration.inline(range.from, range.to, {
        class: thread.selected ? 'comment-highlight comment-highlight-selected' : 'comment-highlight',
        'data-comment-id': String(thread.id),
      }),
    )
  }
  return DecorationSet.create(doc, decorations)
}

/** Highlights the passages comment threads quote, without changing the content. */
export const CommentHighlights = Extension.create({
  name: 'commentHighlights',
  addProseMirrorPlugins() {
    let threads: HighlightedThread[] = []
    return [
      new Plugin<DecorationSet>({
        key: commentHighlightsKey,
        state: {
          init: () => DecorationSet.empty,
          apply(transaction, current, _previous, state) {
            const next = transaction.getMeta(commentHighlightsKey) as HighlightedThread[] | undefined
            if (next) {
              threads = next
              return decorate(state.doc, threads)
            }
            return transaction.docChanged ? decorate(state.doc, threads) : current
          },
        },
        props: {
          decorations(state) {
            return commentHighlightsKey.getState(state)
          },
        },
      }),
    ]
  },
})

/** Replace the highlighted threads of an editor. */
export function setHighlightedThreads(editor: Editor, threads: HighlightedThread[]): void {
  editor.view.dispatch(editor.state.tr.setMeta(commentHighlightsKey, threads))
}
