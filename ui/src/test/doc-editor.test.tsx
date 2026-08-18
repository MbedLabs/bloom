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
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
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
  // The outline builds a selector with CSS.escape, which jsdom does not
  // provide. Every browser does, so this is a gap in the test environment
  // rather than in the app.
  if (typeof globalThis.CSS?.escape !== 'function') {
    globalThis.CSS = { ...(globalThis.CSS ?? {}), escape: (value: string) => value } as never
  }
  // ProseMirror measures and scrolls; jsdom implements neither, and the
  // outline's scroll tracking calls getClientRects on every transaction.
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
    // A read-only editor offers no formatting controls either.
    expect(screen.queryByTitle('Bold (Ctrl+B)')).toBeNull()
  })
})

describe('editing', () => {
  it('reports every change as both JSON and HTML', async () => {
    const onChange = vi.fn()
    const { container } = render(
      <DocEditor content={doc(paragraph('Before'))} onChange={onChange} />,
    )
    const surface = await editorSurface(container)

    // Typing through ProseMirror's own transaction, the way a keystroke lands.
    fireEvent.input(surface, { target: { textContent: 'After' } })
    fireEvent.keyDown(surface, { key: 'a' })

    // The editor may batch, so assert on what it eventually reported.
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

    // Select everything the way Ctrl+A does, then apply the mark.
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
    // TipTap 3 stopped re-rendering on transactions by default, which froze
    // every toolbar state at whatever it showed when the editor mounted.
    const { container } = render(<DocEditor content={doc(paragraph('An item'))} />)
    const surface = await editorSurface(container)
    const bulletList = screen.getByTitle('Bullet list')
    const before = bulletList.className

    fireEvent.click(bulletList)
    await waitFor(() => expect(surface.querySelector('ul li')).toBeTruthy())

    // The button now shows the list as the active block.
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
    // The menu button now names the level the caret sits in.
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

  it('sets the line spacing on the whole document', async () => {
    const { container } = render(<DocEditor content={doc(paragraph('Spaced'))} />)
    const surface = await editorSurface(container)

    fireEvent.click(screen.getByTitle('Line spacing'))
    fireEvent.click(await screen.findByText('1.5'))

    // Spacing is a property of the document, so the class lands on the editor
    // surface rather than on the block the caret happens to be in.
    await waitFor(() => expect(surface.classList.contains('line-height-1_5')).toBe(true))

    fireEvent.click(screen.getByTitle('Line spacing'))
    fireEvent.click(await screen.findByText('2.0'))

    // Only one spacing applies at a time.
    await waitFor(() => expect(surface.classList.contains('line-height-2')).toBe(true))
    expect(surface.classList.contains('line-height-1_5')).toBe(false)
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

    // Once in the document itself and once in the outline.
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
    // The element scrolled to is the heading itself - resolving the position
    // *before* it would hand back the editor's own content element, which is
    // what used to send every entry to the top.
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
