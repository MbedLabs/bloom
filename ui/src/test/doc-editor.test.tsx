// @vitest-environment jsdom
/**
 * The document editor, driven as a real editor.
 *
 * The other tests stub it out, because it pulls in ProseMirror; the result was
 * that the editor, its toolbar and its outline - the three components a user
 * spends the most time in - had almost no coverage between them. ProseMirror
 * does run in jsdom, so these mount the real thing and act on it: type, format,
 * add headings, and navigate by the outline.
 */
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { BubbleMenuView } from '@tiptap/extension-bubble-menu'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const DocEditor = (await import('../components/editor/DocEditor')).default

/** A ProseMirror document, the shape the API stores in `content_json`. */
function doc(...nodes: Record<string, unknown>[]) {
  return { type: 'doc', content: nodes }
}

function paragraph(text: string) {
  return { type: 'paragraph', content: [{ type: 'text', text }] }
}

function heading(level: number, text: string) {
  return { type: 'heading', attrs: { level }, content: [{ type: 'text', text }] }
}

/** The contenteditable ProseMirror manages. */
async function editorSurface(container: HTMLElement): Promise<HTMLElement> {
  await waitFor(() => expect(container.querySelector('.ProseMirror')).toBeTruthy())
  return container.querySelector('.ProseMirror') as HTMLElement
}

const EMPTY_RECT = {
  x: 0, y: 0, top: 0, left: 0, right: 0, bottom: 0, width: 0, height: 0,
  toJSON: () => ({}),
} as DOMRect

beforeEach(() => {
  if (typeof globalThis.CSS?.escape !== 'function') {
    globalThis.CSS = { ...(globalThis.CSS ?? {}), escape: (value: string) => value } as never
  }
  Element.prototype.scrollIntoView = vi.fn()
  Element.prototype.getClientRects = (() => Object.assign([], { item: () => null })) as never
  Element.prototype.getBoundingClientRect = () => EMPTY_RECT
  Range.prototype.getClientRects = (() => Object.assign([], { item: () => null })) as never
  Range.prototype.getBoundingClientRect = () => EMPTY_RECT
  window.matchMedia = ((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addEventListener: () => {},
    removeEventListener: () => {},
    addListener: () => {},
    removeListener: () => {},
    dispatchEvent: () => false,
  })) as unknown as typeof window.matchMedia
})

afterEach(cleanup)

describe('showing a document', () => {
  it('renders the content it was given', async () => {
    const { container } = render(<DocEditor content={doc(paragraph('The system shall boot'))} />)
    const surface = await editorSurface(container)
    expect(surface.textContent).toContain('The system shall boot')
  })

  it('shows the placeholder for an empty document', async () => {
    const { container } = render(<DocEditor content={null} placeholder="Start writing here" />)
    await editorSurface(container)
    expect(container.innerHTML).toContain('Start writing here')
  })

  it('renders headings at the level the document declares', async () => {
    const { container } = render(
      <DocEditor content={doc(heading(1, 'Scope'), heading(2, 'Boot timing'))} />,
    )
    const surface = await editorSurface(container)
    expect(surface.querySelector('h1')?.textContent).toContain('Scope')
    expect(surface.querySelector('h2')?.textContent).toContain('Boot timing')
  })

  it('takes no input when it is not editable', async () => {
    const { container } = render(<DocEditor content={doc(paragraph('Frozen'))} editable={false} />)
    const surface = await editorSurface(container)
    expect(surface.getAttribute('contenteditable')).toBe('false')
    expect(screen.queryByTitle('Bold (Ctrl+B)')).toBeNull()
  })
})

describe('editing', () => {
  it('cancels pending outline work when the editor unmounts', async () => {
    const frame = vi.spyOn(window, 'requestAnimationFrame').mockImplementation(() => 271)
    const cancel = vi.spyOn(window, 'cancelAnimationFrame')
    try {
      const { container, unmount } = render(
        <DocEditor content={doc(heading(1, 'Scope'))} showOutline />,
      )
      await editorSurface(container)
      expect(frame).toHaveBeenCalled()
      unmount()
      expect(cancel).toHaveBeenCalledWith(271)
    } finally {
      frame.mockRestore()
      cancel.mockRestore()
    }
  })

  it('does not read document focus after an editor with pending menu work is destroyed', async () => {
    const { container, unmount } = render(<DocEditor content={doc(paragraph('Before'))} />)
    const surface = await editorSurface(container)
    const menuVisibility = vi.spyOn(BubbleMenuView.prototype, 'getShouldShow')
    vi.useFakeTimers()
    let documentFocus: ReturnType<typeof vi.spyOn> | undefined
    try {
      fireEvent.keyDown(surface, { key: 'a', ctrlKey: true })
      fireEvent.click(screen.getByTitle('Bold (Ctrl+B)'))
      unmount()
      await act(async () => { await vi.advanceTimersByTimeAsync(5) })
      const before = menuVisibility.mock.calls.length
      documentFocus = vi.spyOn(document, 'activeElement', 'get').mockImplementation(() => {
        throw new Error('Document focus was read after editor teardown')
      })
      await act(async () => { await vi.advanceTimersByTimeAsync(500) })
      expect(menuVisibility.mock.calls.length).toBeGreaterThan(before)
      expect(documentFocus).not.toHaveBeenCalled()
    } finally {
      documentFocus?.mockRestore()
      menuVisibility.mockRestore()
      vi.useRealTimers()
    }
  })

  it('reports every change as both JSON and HTML', async () => {
    const onChange = vi.fn()
    const { container } = render(
      <DocEditor content={doc(paragraph('Before'))} onChange={onChange} />,
    )
    const surface = await editorSurface(container)

    fireEvent.input(surface, { target: { textContent: 'After' } })
    fireEvent.keyDown(surface, { key: 'a' })

    await waitFor(() => expect(onChange).toHaveBeenCalled())
    const [json, html] = onChange.mock.calls[onChange.mock.calls.length - 1]
    expect(json).toHaveProperty('type', 'doc')
    expect(typeof html).toBe('string')
  })
})

describe('the toolbar', () => {
  it('offers the formatting a document needs', async () => {
    const { container } = render(<DocEditor content={doc(paragraph('Text'))} />)
    await editorSurface(container)

    for (const control of [
      'Bold (Ctrl+B)',
      'Italic (Ctrl+I)',
      'Underline (Ctrl+U)',
      'Bullet list',
      'Numbered list',
      'Task list',
      'Blockquote',
      'Insert table',
      'Code block',
      'Insert link',
      'Clear formatting',
      'Undo',
      'Redo',
    ]) {
      expect(screen.getByTitle(control)).toBeTruthy()
    }
  })

  it('marks the whole document bold', async () => {
    const { container } = render(<DocEditor content={doc(paragraph('Make me bold'))} />)
    const surface = await editorSurface(container)

    fireEvent.keyDown(surface, { key: 'a', ctrlKey: true })
    fireEvent.click(screen.getByTitle('Bold (Ctrl+B)'))

    await waitFor(() => expect(surface.querySelector('strong')).toBeTruthy())
    expect(surface.querySelector('strong')?.textContent).toBe('Make me bold')
  })

  it('turns the paragraph into a bulleted list', async () => {
    const { container } = render(<DocEditor content={doc(paragraph('An item'))} />)
    const surface = await editorSurface(container)

    fireEvent.click(screen.getByTitle('Bullet list'))

    await waitFor(() => expect(surface.querySelector('ul li')).toBeTruthy())
  })

  it('inserts a table', async () => {
    const { container } = render(<DocEditor content={doc(paragraph(''))} />)
    const surface = await editorSurface(container)

    fireEvent.click(screen.getByTitle('Insert table'))

    await waitFor(() => expect(surface.querySelector('table')).toBeTruthy())
  })

  it('undoes what it just did', async () => {
    const { container } = render(<DocEditor content={doc(paragraph('An item'))} />)
    const surface = await editorSurface(container)

    fireEvent.click(screen.getByTitle('Bullet list'))
    await waitFor(() => expect(surface.querySelector('ul li')).toBeTruthy())

    fireEvent.click(screen.getByTitle('Undo'))

    await waitFor(() => expect(surface.querySelector('ul li')).toBeNull())
    expect(surface.textContent).toContain('An item')
  })

  it('keeps the toolbar in step with the document', async () => {
    const { container } = render(<DocEditor content={doc(paragraph('An item'))} />)
    const surface = await editorSurface(container)
    const bulletList = screen.getByTitle('Bullet list')
    const before = bulletList.className

    fireEvent.click(bulletList)
    await waitFor(() => expect(surface.querySelector('ul li')).toBeTruthy())

    await waitFor(() => expect(screen.getByTitle('Bullet list').className).not.toBe(before))
  })

  it('hands the heading-numbering choice back to its owner', async () => {
    const onHeadingNumberedChange = vi.fn()
    const { container } = render(
      <DocEditor
        content={doc(heading(1, 'Scope'))}
        headingNumbered
        onHeadingNumberedChange={onHeadingNumberedChange}
      />,
    )
    await editorSurface(container)

    fireEvent.click(screen.getByTitle('Disable heading numbering'))

    expect(onHeadingNumberedChange).toHaveBeenCalledWith(false)
  })
})

describe('the toolbar menus', () => {
  it('turns the paragraph into a heading, and back again', async () => {
    const { container } = render(<DocEditor content={doc(paragraph('A title'))} />)
    const surface = await editorSurface(container)

    fireEvent.click(screen.getByText('Paragraph'))
    fireEvent.click(await screen.findByText('Heading 2'))

    await waitFor(() => expect(surface.querySelector('h2')?.textContent).toBe('A title'))
    await waitFor(() => expect(screen.getByText('H2')).toBeTruthy())

    fireEvent.click(screen.getByText('H2'))
    fireEvent.click(await screen.findByText('Paragraph'))
    await waitFor(() => expect(surface.querySelector('h2')).toBeNull())
  })

  it('offers every heading level the document model allows', async () => {
    const { container } = render(<DocEditor content={doc(paragraph('A title'))} />)
    await editorSurface(container)

    fireEvent.click(screen.getByText('Paragraph'))

    for (const level of [1, 2, 3, 4, 5, 6]) {
      expect(await screen.findByText(`Heading ${level}`)).toBeTruthy()
    }
  })

  it('colours the text, and takes the colour off again', async () => {
    const { container } = render(<DocEditor content={doc(paragraph('Coloured'))} />)
    const surface = await editorSurface(container)

    fireEvent.keyDown(surface, { key: 'a', ctrlKey: true })
    fireEvent.click(screen.getByTitle('Text color'))
    const swatch = (await screen.findAllByTitle(/^#/))[0]
    fireEvent.click(swatch)

    await waitFor(() => expect(surface.querySelector('[style*="color"]')).toBeTruthy())

    fireEvent.keyDown(surface, { key: 'a', ctrlKey: true })
    fireEvent.click(screen.getByTitle('Text color'))
    fireEvent.click(await screen.findByText('Reset color'))

    await waitFor(() => expect(surface.querySelector('[style*="color"]')).toBeNull())
  })

  it('stores the line spacing on the paragraph at the cursor and leaves the others', async () => {
    const onChange = vi.fn()
    const { container } = render(
      <DocEditor content={doc(paragraph('Plain'), paragraph('Spaced'))} onChange={onChange} />,
    )
    const surface = await editorSurface(container)

    fireEvent.click(screen.getByTitle('Line spacing'))
    fireEvent.click(await screen.findByText('1.5'))

    await waitFor(() => expect(surface.querySelector('p[data-line-spacing="1.5"]')?.textContent).toBe('Spaced'))
    expect(surface.querySelectorAll('[data-line-spacing]')).toHaveLength(1)
    const [json, html] = onChange.mock.calls[onChange.mock.calls.length - 1]
    expect(json.content[0].attrs.lineSpacing).toBeNull()
    expect(json.content[1].attrs.lineSpacing).toBe('1.5')
    expect(html).toContain('data-line-spacing="1.5"')
  })

  it('switches to Double and back to Single, which removes the stored spacing', async () => {
    const onChange = vi.fn()
    const { container } = render(<DocEditor content={doc(paragraph('Spaced'))} onChange={onChange} />)
    const surface = await editorSurface(container)

    fireEvent.click(screen.getByTitle('Line spacing'))
    fireEvent.click(await screen.findByText('Double'))
    await waitFor(() => expect(surface.querySelector('p[data-line-spacing="2"]')).toBeTruthy())

    fireEvent.click(screen.getByTitle('Line spacing'))
    fireEvent.click(await screen.findByText('Single'))
    await waitFor(() => expect(surface.querySelector('[data-line-spacing]')).toBeNull())
    const [json] = onChange.mock.calls[onChange.mock.calls.length - 1]
    expect(json.content[0].attrs.lineSpacing).toBeNull()
  })

  it('shows stored spacing when the document is opened again and marks it in the menu', async () => {
    const stored = { ...paragraph('Saved'), attrs: { lineSpacing: '2' } }
    const { container } = render(<DocEditor content={doc(stored)} />)
    const surface = await editorSurface(container)

    expect(surface.querySelector('p[data-line-spacing="2"]')?.textContent).toBe('Saved')
    fireEvent.click(screen.getByTitle('Line spacing'))
    expect((await screen.findByText('Double')).className).toContain('bg-primary/10')
    expect(screen.getByText('Single').className).not.toContain('bg-primary/10')
  })

  it('marks Single for a paragraph without spacing', async () => {
    render(<DocEditor content={doc(paragraph('Plain'))} />)

    fireEvent.click(await screen.findByTitle('Line spacing'))
    expect((await screen.findByText('Single')).className).toContain('bg-primary/10')
  })

  it('shows stored spacing in a read-only editor', async () => {
    const stored = { ...paragraph('Read'), attrs: { lineSpacing: '1.5' } }
    const { container } = render(<DocEditor content={doc(stored)} editable={false} />)
    const surface = await editorSurface(container)

    expect(surface.querySelector('p[data-line-spacing="1.5"]')?.textContent).toBe('Read')
  })

  it('sets the spacing of a list item through its paragraph', async () => {
    const list = { type: 'bulletList', content: [{ type: 'listItem', content: [paragraph('Item')] }] }
    const { container } = render(<DocEditor content={doc(list)} />)
    const surface = await editorSurface(container)

    fireEvent.click(screen.getByTitle('Line spacing'))
    fireEvent.click(await screen.findByText('1.5'))

    await waitFor(() => expect(surface.querySelector('li p[data-line-spacing="1.5"]')?.textContent).toBe('Item'))
  })

  it('sets the spacing of a heading', async () => {
    const { container } = render(<DocEditor content={doc(heading(2, 'Title'))} />)
    const surface = await editorSurface(container)

    fireEvent.click(screen.getByTitle('Line spacing'))
    fireEvent.click(await screen.findByText('Double'))

    await waitFor(() => expect(surface.querySelector('h2[data-line-spacing="2"]')?.textContent).toContain('Title'))
  })

  it('marks Single for a stored spacing the editor does not offer', async () => {
    const stored = { ...paragraph('Odd'), attrs: { lineSpacing: '7' } }
    render(<DocEditor content={doc(stored)} />)

    fireEvent.click(await screen.findByTitle('Line spacing'))
    expect((await screen.findByText('Single')).className).toContain('bg-primary/10')
  })

  it('aligns the paragraph', async () => {
    const { container } = render(<DocEditor content={doc(paragraph('Centred'))} />)
    const surface = await editorSurface(container)

    fireEvent.click(screen.getByTitle('Align center'))

    await waitFor(() => expect(surface.innerHTML).toContain('center'))
  })

  it('links the selection to the URL that was typed', async () => {
    const prompt = vi.fn(() => 'https://example.com/spec')
    vi.stubGlobal('prompt', prompt)
    const { container } = render(<DocEditor content={doc(paragraph('See the spec'))} />)
    const surface = await editorSurface(container)

    fireEvent.keyDown(surface, { key: 'a', ctrlKey: true })
    fireEvent.click(screen.getByTitle('Insert link'))

    await waitFor(() =>
      expect(surface.querySelector('a')?.getAttribute('href')).toBe('https://example.com/spec'),
    )
    vi.unstubAllGlobals()
  })

  it('leaves the document alone when the link prompt is dismissed', async () => {
    vi.stubGlobal('prompt', vi.fn(() => null))
    const { container } = render(<DocEditor content={doc(paragraph('See the spec'))} />)
    const surface = await editorSurface(container)

    fireEvent.keyDown(surface, { key: 'a', ctrlKey: true })
    fireEvent.click(screen.getByTitle('Insert link'))

    expect(surface.querySelector('a')).toBeNull()
    vi.unstubAllGlobals()
  })

  it('inserts an image at the URL that was typed', async () => {
    vi.stubGlobal('prompt', vi.fn(() => 'https://example.com/diagram.png'))
    const { container } = render(<DocEditor content={doc(paragraph(''))} />)
    const surface = await editorSurface(container)

    fireEvent.click(screen.getByTitle('Insert image'))

    await waitFor(() =>
      expect(surface.querySelector('img')?.getAttribute('src')).toBe(
        'https://example.com/diagram.png',
      ),
    )
    vi.unstubAllGlobals()
  })

  it('strips every mark with clear formatting', async () => {
    const { container } = render(<DocEditor content={doc(paragraph('Overdressed'))} />)
    const surface = await editorSurface(container)

    fireEvent.keyDown(surface, { key: 'a', ctrlKey: true })
    fireEvent.click(screen.getByTitle('Bold (Ctrl+B)'))
    fireEvent.click(screen.getByTitle('Italic (Ctrl+I)'))
    await waitFor(() => expect(surface.querySelector('strong em, em strong')).toBeTruthy())

    fireEvent.keyDown(surface, { key: 'a', ctrlKey: true })
    fireEvent.click(screen.getByTitle('Clear formatting'))

    await waitFor(() => expect(surface.querySelector('strong')).toBeNull())
    expect(surface.querySelector('em')).toBeNull()
    expect(surface.textContent).toContain('Overdressed')
  })

  it('turns the block into a quote and a code block', async () => {
    const { container } = render(<DocEditor content={doc(paragraph('Quoted'))} />)
    const surface = await editorSurface(container)

    fireEvent.click(screen.getByTitle('Blockquote'))
    await waitFor(() => expect(surface.querySelector('blockquote')).toBeTruthy())

    fireEvent.click(screen.getByTitle('Code block'))
    await waitFor(() => expect(surface.querySelector('pre')).toBeTruthy())
  })

  it('builds a task list with a checkbox per item', async () => {
    const { container } = render(<DocEditor content={doc(paragraph('To do'))} />)
    const surface = await editorSurface(container)

    fireEvent.click(screen.getByTitle('Task list'))

    await waitFor(() => expect(surface.querySelector('input[type="checkbox"]')).toBeTruthy())
  })
})

describe('the outline', () => {
  const document_ = doc(
    heading(1, 'Scope'),
    paragraph('What this covers.'),
    heading(2, 'Boot timing'),
    paragraph('Cold start to ready.'),
    heading(2, 'Shutdown'),
  )

  it('lists every heading in the document', async () => {
    const { container } = render(<DocEditor content={document_} showOutline />)
    await editorSurface(container)

    await waitFor(() => expect(screen.getAllByText('Scope').length).toBeGreaterThan(1))
    expect(screen.getAllByText('Boot timing').length).toBeGreaterThan(1)
    expect(screen.getAllByText('Shutdown').length).toBeGreaterThan(1)
  })

  it('scrolls to the heading that was clicked, not the top of the document', async () => {
    const scrollIntoView = vi.fn()
    Element.prototype.scrollIntoView = scrollIntoView
    const { container } = render(<DocEditor content={document_} showOutline />)
    const surface = await editorSurface(container)

    const entry = container.querySelector(
      'nav button[data-outline-slug="shutdown"]',
    ) as HTMLElement | null
    expect(entry).toBeTruthy()
    scrollIntoView.mockClear()

    fireEvent.click(entry as HTMLElement)

    await waitFor(() => expect(scrollIntoView).toHaveBeenCalled())
    const target = scrollIntoView.mock.instances[scrollIntoView.mock.instances.length - 1] as
      | HTMLElement
      | undefined
    expect(target).toBeTruthy()
    expect(target).not.toBe(surface)
  })

  it('can be hidden and shown again', async () => {
    const onOutlineToggle = vi.fn()
    const { container } = render(
      <DocEditor content={document_} showOutline onOutlineToggle={onOutlineToggle} />,
    )
    await editorSurface(container)

    fireEvent.click(screen.getByTitle('Hide outline'))
    expect(onOutlineToggle).toHaveBeenCalledWith(false)
  })

  it('is offered even when it starts closed', async () => {
    const onOutlineToggle = vi.fn()
    const { container } = render(
      <DocEditor content={document_} onOutlineToggle={onOutlineToggle} />,
    )
    await editorSurface(container)

    fireEvent.click(screen.getByTitle('Toggle outline'))
    expect(onOutlineToggle).toHaveBeenCalledWith(true)
  })
})
