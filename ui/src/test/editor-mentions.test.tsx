// @vitest-environment jsdom
/**
 * The two mention triggers, driven through the real editor.
 *
 * `{{` addresses a project parameter or variable, `@` addresses a person. Each
 * has its own popover, mounted outside the editor into document.body and
 * positioned against the caret, and each has to be torn down again when the
 * trigger goes away. That plumbing - open, re-filter, insert, close - was the
 * single largest uncovered piece of the editor, because the other tests either
 * stub the editor out or never type a trigger.
 *
 * ProseMirror reads typing off DOM mutations, so these type the way a
 * keystroke lands: set the text and let the observer pick it up.
 */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const DocEditor = (await import('../components/editor/DocEditor')).default

/** Parameters and variables, which is what `{{` offers. */
const parameters = [
  { id: 1, label: 'BOOT_BUDGET_MS' },
  { id: 2, label: 'MAX_TEMP_C' },
  { id: 3, label: 'BOARD_REV' },
]
/** People, which is what `@` offers. */
const people = [
  { id: 11, label: 'Ada Lovelace' },
  { id: 12, label: 'Grace Hopper' },
]

const EMPTY_RECT = {
  x: 0, y: 0, top: 0, left: 0, right: 0, bottom: 0, width: 0, height: 0,
  toJSON: () => ({}),
} as DOMRect

function renderEditor(props: Record<string, unknown> = {}) {
  return render(
    <DocEditor
      content={{ type: 'doc', content: [{ type: 'paragraph' }] }}
      mentionItems={parameters}
      userMentionItems={people}
      {...props}
    />,
  )
}

/** The contenteditable ProseMirror manages. */
async function editorSurface(container: HTMLElement): Promise<HTMLElement> {
  await waitFor(() => expect(container.querySelector('.ProseMirror')).toBeTruthy())
  return container.querySelector('.ProseMirror') as HTMLElement
}

/**
 * Type into the document the way a keystroke does: ProseMirror observes the
 * DOM rather than listening for synthetic React events.
 */
async function type(surface: HTMLElement, text: string) {
  const paragraph = surface.querySelector('p') as HTMLElement
  paragraph.textContent = text
  fireEvent.input(surface)
  await new Promise((resolve) => setTimeout(resolve, 20))
}

/** The popover the suggestion plugin mounts outside the editor. */
function popover(): HTMLElement | null {
  return document.querySelector('.mention-suggestion-popover')
}

beforeEach(() => {
  // The outline builds a selector with CSS.escape, which jsdom does not
  // provide. Every browser does, so this is a gap in the test environment
  // rather than in the app.
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

afterEach(() => {
  cleanup()
  // The popover lives outside the React tree, so cleanup does not remove it.
  document.querySelectorAll('.mention-suggestion-popover').forEach((node) => {
    node.parentElement?.remove()
  })
})

describe('the {{ trigger', () => {
  it('opens on {{ and offers the project’s parameters', async () => {
    const { container } = renderEditor()
    const surface = await editorSurface(container)

    await type(surface, '{{')

    await waitFor(() => expect(popover()).toBeTruthy())
    expect(screen.getByText('{{BOOT_BUDGET_MS}}')).toBeTruthy()
    expect(screen.getByText('{{MAX_TEMP_C}}')).toBeTruthy()
  })

  it('offers no people under {{', async () => {
    const { container } = renderEditor()
    const surface = await editorSurface(container)

    await type(surface, '{{')
    await waitFor(() => expect(popover()).toBeTruthy())

    expect(screen.queryByText(/Ada Lovelace/)).toBeNull()
  })

  it('narrows the list as the query is typed', async () => {
    const { container } = renderEditor()
    const surface = await editorSurface(container)

    await type(surface, '{{')
    await waitFor(() => expect(popover()).toBeTruthy())

    await type(surface, '{{TEMP')
    await waitFor(() => expect(screen.queryByText('{{BOOT_BUDGET_MS}}')).toBeNull())
    expect(screen.getByText('{{MAX_TEMP_C}}')).toBeTruthy()
  })

  it('matches without regard to case', async () => {
    const { container } = renderEditor()
    const surface = await editorSurface(container)

    await type(surface, '{{board')

    await waitFor(() => expect(screen.getByText('{{BOARD_REV}}')).toBeTruthy())
    expect(screen.queryByText('{{MAX_TEMP_C}}')).toBeNull()
  })

  it('says so when the query matches nothing', async () => {
    const { container } = renderEditor()
    const surface = await editorSurface(container)

    await type(surface, '{{nothing_like_this')

    await waitFor(() => expect(screen.getByText('No results')).toBeTruthy())
  })

  it('offers nothing at all when the project has no parameters', async () => {
    const { container } = renderEditor({ mentionItems: [] })
    const surface = await editorSurface(container)

    await type(surface, '{{')

    await waitFor(() => expect(popover()).toBeTruthy())
    expect(screen.getByText('No results')).toBeTruthy()
  })

  it('inserts the parameter that was picked, wrapped in braces', async () => {
    const { container } = renderEditor()
    const surface = await editorSurface(container)

    await type(surface, '{{')
    await waitFor(() => expect(popover()).toBeTruthy())
    fireEvent.click(screen.getByText('{{BOOT_BUDGET_MS}}'))

    await waitFor(() => {
      const mention = surface.querySelector('span[data-type="mention"]')
      expect(mention?.textContent).toBe('{{BOOT_BUDGET_MS}}')
    })
    // A parameter is not a person, and must not be styled as one.
    expect(surface.querySelector('.mention-user')).toBeNull()
  })

  it('closes the popover once something is inserted', async () => {
    const { container } = renderEditor()
    const surface = await editorSurface(container)

    await type(surface, '{{')
    await waitFor(() => expect(popover()).toBeTruthy())
    fireEvent.click(screen.getByText('{{BOARD_REV}}'))

    // The popover is mounted outside the editor, so it has to be taken down
    // explicitly or it is left hanging over the page.
    await waitFor(() => expect(popover()).toBeNull())
  })

  it('closes the popover when the trigger is deleted', async () => {
    const { container } = renderEditor()
    const surface = await editorSurface(container)

    await type(surface, '{{')
    await waitFor(() => expect(popover()).toBeTruthy())

    await type(surface, '')
    await waitFor(() => expect(popover()).toBeNull())
  })

  it('positions the popover over the page rather than in the document flow', async () => {
    const { container } = renderEditor()
    const surface = await editorSurface(container)

    await type(surface, '{{')
    await waitFor(() => expect(popover()).toBeTruthy())

    const host = popover()?.parentElement as HTMLElement
    expect(host.style.position).toBe('fixed')
    expect(host.style.zIndex).toBe('50')
    // Placed against the caret, not left at the origin by default.
    expect(host.style.top).not.toBe('')
  })
})

describe('the @ trigger', () => {
  it('opens on @ and offers people', async () => {
    const { container } = renderEditor()
    const surface = await editorSurface(container)

    await type(surface, '@')

    await waitFor(() => expect(popover()).toBeTruthy())
    expect(screen.getByText('@Ada Lovelace')).toBeTruthy()
    expect(screen.getByText('@Grace Hopper')).toBeTruthy()
  })

  it('offers no parameters under @', async () => {
    const { container } = renderEditor()
    const surface = await editorSurface(container)

    await type(surface, '@')
    await waitFor(() => expect(popover()).toBeTruthy())

    expect(screen.queryByText(/BOOT_BUDGET_MS/)).toBeNull()
  })

  it('narrows to a name', async () => {
    const { container } = renderEditor()
    const surface = await editorSurface(container)

    await type(surface, '@grace')

    await waitFor(() => expect(screen.getByText('@Grace Hopper')).toBeTruthy())
    expect(screen.queryByText('@Ada Lovelace')).toBeNull()
  })

  it('inserts the person that was picked, with no closing braces', async () => {
    const { container } = renderEditor()
    const surface = await editorSurface(container)

    await type(surface, '@')
    await waitFor(() => expect(popover()).toBeTruthy())
    fireEvent.click(screen.getByText('@Ada Lovelace'))

    await waitFor(() => {
      const mention = surface.querySelector('span[data-type="mention"]')
      expect(mention?.textContent).toBe('@Ada Lovelace')
    })
    // A person is styled as a person, which is how the two are told apart on
    // the page.
    expect(surface.querySelector('.mention-user')).toBeTruthy()
  })

  it('offers nothing when the project has no members to mention', async () => {
    const { container } = renderEditor({ userMentionItems: [] })
    const surface = await editorSurface(container)

    await type(surface, '@')

    await waitFor(() => expect(screen.getByText('No results')).toBeTruthy())
  })
})

describe('mentions already in a document', () => {
  const withBoth = {
    type: 'doc',
    content: [
      {
        type: 'paragraph',
        content: [
          {
            type: 'mention',
            attrs: { id: '1', label: 'BOOT_BUDGET_MS', mentionSuggestionChar: '{{' },
          },
          { type: 'text', text: ' owned by ' },
          {
            type: 'mention',
            attrs: { id: '11', label: 'Ada Lovelace', mentionSuggestionChar: '@' },
          },
        ],
      },
    ],
  }

  it('spells a parameter with braces and a person with an @', async () => {
    const { container } = renderEditor({ content: withBoth })
    const surface = await editorSurface(container)

    expect(surface.textContent).toContain('{{BOOT_BUDGET_MS}}')
    expect(surface.textContent).toContain('@Ada Lovelace')
    // Never the other way round.
    expect(surface.textContent).not.toContain('@BOOT_BUDGET_MS')
    expect(surface.textContent).not.toContain('{{Ada Lovelace}}')
  })

  it('styles the two kinds differently', async () => {
    const { container } = renderEditor({ content: withBoth })
    const surface = await editorSurface(container)

    const mentions = Array.from(surface.querySelectorAll('span[data-type="mention"]'))
    expect(mentions).toHaveLength(2)
    expect(mentions[0].className).toContain('mention')
    expect(mentions[0].className).not.toContain('mention-user')
    expect(mentions[1].className).toContain('mention-user')
  })

  it('survives a mention that has only an id', async () => {
    const { container } = renderEditor({
      content: {
        type: 'doc',
        content: [
          {
            type: 'paragraph',
            content: [
              { type: 'mention', attrs: { id: '42', mentionSuggestionChar: '{{' } },
            ],
          },
        ],
      },
    })
    const surface = await editorSurface(container)

    // A parameter that has since been deleted still has to render as something.
    expect(surface.textContent).toContain('{{42}}')
  })
})
