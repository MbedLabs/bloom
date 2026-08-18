import { Extension } from '@tiptap/core'

export interface LineHeightOptions {
  defaultLineHeight: string
}

declare module '@tiptap/core' {
  interface Commands<ReturnType> {
    lineHeight: {
      setLineHeight: (lineHeight: string) => ReturnType
      unsetLineHeight: () => ReturnType
    }
  }
  interface Storage {
    lineHeight: string | null
  }
}

const CLASS_PREFIX = 'line-height-'
const CLASSES = ['line-height-1', 'line-height-1_5', 'line-height-2']

export const LineHeight = Extension.create<LineHeightOptions>({
  name: 'lineHeight',

  addOptions() {
    return {
      defaultLineHeight: '1',
    }
  },

  addCommands() {
    return {
      setLineHeight:
        (lh: string) =>
        ({ editor }) => {
          const el = (editor.view as { dom: HTMLElement }).dom
          CLASSES.forEach((c) => el.classList.remove(c))
          const cls = CLASS_PREFIX + lh.replace('.', '_')
          el.classList.add(cls)
          editor.storage.lineHeight = lh
          return true
        },
      unsetLineHeight:
        () =>
        ({ editor }) => {
          const el = (editor.view as { dom: HTMLElement }).dom
          CLASSES.forEach((c) => el.classList.remove(c))
          editor.storage.lineHeight = null
          return true
        },
    }
  },

  addStorage() {
    return { lineHeight: null as string | null }
  },
})
