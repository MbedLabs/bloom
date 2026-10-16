import { isTextSelection } from '@tiptap/core'
import type { BubbleMenuPluginProps } from '@tiptap/extension-bubble-menu'

export const bubbleMenuVisibility: NonNullable<BubbleMenuPluginProps['shouldShow']> = ({
  editor, element, view, state, from, to,
}) => {
  if (editor.isDestroyed || view.isDestroyed) return false
  const emptyText = !state.doc.textBetween(from, to).length && isTextSelection(state.selection)
  const focused = view.hasFocus() || element.contains(element.ownerDocument.activeElement)
  return focused && !state.selection.empty && !emptyText && editor.isEditable
}
