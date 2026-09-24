// @vitest-environment jsdom
/**
 * A `#` tag shows the current public id of the artefact it points at, looked up once
 * per document. The stored label is the fallback until the lookup answers, and a tag
 * whose target is gone reads as plain text.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('../api/client', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>()
  return { ...actual, docsApi: { list: vi.fn() } }
})

const client = await import('../api/client')
const DocEditor = (await import('../components/editor/DocEditor')).default
const { tagKeys, useArtefactLabels } = await import('../hooks/useArtefactLabels')

const EMPTY_RECT = { x: 0, y: 0, top: 0, left: 0, right: 0, bottom: 0, width: 0, height: 0, toJSON: () => ({}) } as DOMRect

const body = {
  type: 'doc',
  content: [
    {
      type: 'paragraph',
      content: [
        { type: 'text', text: 'See ' },
        { type: 'mention', attrs: { id: 'REQ:12', label: 'FLT-REQ-001', mentionSuggestionChar: '#' } },
        { type: 'text', text: ' and ' },
        { type: 'mention', attrs: { id: 'TC:4', label: 'FLT-TC-004', mentionSuggestionChar: '#' } },
        { type: 'mention', attrs: { id: 'BOOT', label: 'BOOT', mentionSuggestionChar: '{{' } },
      ],
    },
    { type: 'bulletList', content: [{ type: 'listItem', content: [{ type: 'paragraph', content: [
      { type: 'mention', attrs: { id: 'REQ:12', label: 'FLT-REQ-001', mentionSuggestionChar: '#' } },
    ] }] }] },
  ],
}

function tags(container: HTMLElement) {
  return Array.from(container.querySelectorAll('.ProseMirror .mention-artefact, .ProseMirror .mention-artefact-gone')) as HTMLElement[]
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
  cleanup()
  vi.clearAllMocks()
})

describe('a tag in a body', () => {
  const href = (type: string, _id: number, label: string) => `/projects/FLT/docs/${type}/${label}`

  it('shows and links the current id, and reads as plain text once the target is gone', async () => {
    const { container, rerender } = render(<DocEditor content={body} editable={false} artefactHref={href} />)
    await waitFor(() => expect(tags(container)).toHaveLength(3))
    expect(tags(container).map((t) => t.textContent)).toEqual(['FLT-REQ-001', 'FLT-TC-004', 'FLT-REQ-001'])

    rerender(
      <DocEditor
        content={body}
        editable={false}
        artefactHref={href}
        artefactLabels={{ 'REQ:12': 'FLT-REQ-0001', 'TC:4': null }}
      />,
    )
    await waitFor(() => expect(tags(container)[0].textContent).toBe('FLT-REQ-0001'))
    expect(tags(container)[0].getAttribute('href')).toBe('/projects/FLT/docs/REQ/FLT-REQ-0001')
    expect(tags(container)[1].tagName).toBe('SPAN')
    expect(tags(container)[1].className).toBe('mention-artefact-gone')
    expect(tags(container)[1].textContent).toBe('FLT-TC-004')
    expect(tags(container)[2].textContent).toBe('FLT-REQ-0001')
  })
})

describe('tagKeys', () => {
  it('collects every tag once, ignoring parameters and malformed ids', () => {
    expect(tagKeys(body)).toEqual(['REQ:12', 'TC:4'])
    expect(tagKeys(null)).toEqual([])
    expect(tagKeys({ type: 'mention', attrs: { id: 'nocolon', mentionSuggestionChar: '#' } })).toEqual([])
  })
})

describe('useArtefactLabels', () => {
  function wrapper({ children }: { children: ReactNode }) {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  }

  it('resolves every tag in one request and marks what did not come back', async () => {
    vi.mocked(client.docsApi.list).mockResolvedValue({
      items: [{ id: 12, doc_id: 'FLT-REQ-0001', doc_type: 'REQ' }],
      total: 1,
      skip: 0,
      limit: 2,
    } as never)
    const { result } = renderHook(() => useArtefactLabels('FLT', body), { wrapper })
    await waitFor(() => expect(result.current).toEqual({ 'REQ:12': 'FLT-REQ-0001', 'TC:4': null }))
    expect(client.docsApi.list).toHaveBeenCalledTimes(1)
    expect(client.docsApi.list).toHaveBeenCalledWith('FLT', { keys: ['REQ:12', 'TC:4'], includeLinkCounts: false, limit: 2 })
  })

  it('asks nothing for a body without tags and stays undefined on a failure', async () => {
    const empty = renderHook(() => useArtefactLabels('FLT', { type: 'doc', content: [] }), { wrapper })
    expect(empty.result.current).toBeUndefined()
    expect(client.docsApi.list).not.toHaveBeenCalled()

    vi.mocked(client.docsApi.list).mockRejectedValue(new Error('403'))
    const failed = renderHook(() => useArtefactLabels('FLT', body), { wrapper })
    await waitFor(() => expect(client.docsApi.list).toHaveBeenCalled())
    expect(failed.result.current).toBeUndefined()
  })
})
