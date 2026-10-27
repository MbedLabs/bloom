import { Extension, type Editor } from '@tiptap/core'

/** The line spacings a paragraph or heading takes besides Single, as multiples of its normal line height. */
export const LINE_SPACINGS = ['1.5', '2'] as const

const TYPES = ['paragraph', 'heading']

declare module '@tiptap/core' {
  interface Commands<ReturnType> {
    lineHeight: {
      setLineHeight: (lineHeight: string) => ReturnType
      unsetLineHeight: () => ReturnType
    }
  }
}

/** A stored line spacing, or null for Single and for any value the editor does not offer. */
function knownSpacing(value: string | null | undefined): string | null {
  return value && (LINE_SPACINGS as readonly string[]).includes(value) ? value : null
}

/** Line spacing of each paragraph and heading, stored in the document as `lineSpacing` and rendered as `data-line-spacing`. */
export const LineHeight = Extension.create({
  name: 'lineHeight',

  addGlobalAttributes() {
    return [
      {
        types: TYPES,
        attributes: {
          lineSpacing: {
            default: null,
            parseHTML: (element) => knownSpacing(element.getAttribute('data-line-spacing')),
            renderHTML: (attributes) =>
              attributes.lineSpacing ? { 'data-line-spacing': attributes.lineSpacing } : {},
          },
        },
      },
    ]
  },

  addCommands() {
    return {
      setLineHeight:
        (lineHeight: string) =>
        ({ commands }) => {
          if (!knownSpacing(lineHeight)) return false
          return TYPES.map((type) => commands.updateAttributes(type, { lineSpacing: lineHeight })).some(Boolean)
        },
      unsetLineHeight:
        () =>
        ({ commands }) =>
          TYPES.map((type) => commands.resetAttributes(type, 'lineSpacing')).some(Boolean),
    }
  },
})

/** The line spacing of the paragraph or heading at the cursor, or null for Single. */
export function currentLineSpacing(editor: Editor): string | null {
  const type = editor.isActive('heading') ? 'heading' : 'paragraph'
  return knownSpacing(editor.getAttributes(type).lineSpacing as string | undefined)
}
