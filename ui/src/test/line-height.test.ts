// @vitest-environment jsdom
import { Editor } from '@tiptap/core'
import StarterKit from '@tiptap/starter-kit'
import { afterEach, describe, expect, it } from 'vitest'

import { LineHeight, currentLineSpacing } from '../components/editor/LineHeight'

let editor: Editor | null = null

function editorWith(content: string): Editor {
  editor = new Editor({ extensions: [StarterKit, LineHeight], content })
  return editor
}

afterEach(() => {
  editor?.destroy()
  editor = null
})

describe('line spacing', () => {
  it('reads an offered spacing from HTML and writes it back', () => {
    const current = editorWith('<p data-line-spacing="1.5">Spaced</p><h2 data-line-spacing="2">Title</h2>')

    const json = current.getJSON()
    expect(json.content?.[0].attrs?.lineSpacing).toBe('1.5')
    expect(json.content?.[1].attrs?.lineSpacing).toBe('2')
    expect(current.getHTML()).toContain('<p data-line-spacing="1.5">Spaced</p>')
  })

  it('drops a spacing the editor does not offer when reading HTML', () => {
    const current = editorWith('<p data-line-spacing="7">Odd</p>')

    expect(current.getJSON().content?.[0].attrs?.lineSpacing).toBeNull()
    expect(current.getHTML()).not.toContain('data-line-spacing')
  })

  it('refuses a spacing the editor does not offer', () => {
    const current = editorWith('<p>Plain</p>')

    expect(current.commands.setLineHeight('3')).toBe(false)
    expect(current.getHTML()).not.toContain('data-line-spacing')
  })

  it('sets the spacing of a quoted paragraph and reports it at the cursor', () => {
    const current = editorWith('<blockquote><p>Quoted</p></blockquote>')
    current.commands.setTextSelection(3)

    current.commands.setLineHeight('2')

    expect(current.getHTML()).toContain('<blockquote><p data-line-spacing="2">Quoted</p></blockquote>')
    expect(currentLineSpacing(current)).toBe('2')
    current.commands.unsetLineHeight()
    expect(currentLineSpacing(current)).toBeNull()
  })
})
