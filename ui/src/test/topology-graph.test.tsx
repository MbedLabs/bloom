import { createQueryClient } from '../lib/queryClient'
// @vitest-environment jsdom
/**
 * The project topology graph.
 *
 * It answers one question at a glance - which kinds of document a project has,
 * and how they are linked - by aggregating every artefact and every link into
 * one node per type and one edge per type pair. Nothing covered it, so the
 * counting, the aggregation and the suspect-link tally were all unchecked, and
 * a wrong roll-up here misreports the shape of the whole project.
 */
import { QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { docShell, link, testCaseDocShell } from './apiFixtures'

const docsApi = { list: vi.fn(), get: vi.fn(), nextDocId: vi.fn(), typeSummary: vi.fn() }
const linksApi = { list: vi.fn(), create: vi.fn(), delete: vi.fn() }

vi.mock('../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/client')>()
  return { ...actual, docsApi, linksApi }
})

const ProjectDocTopology = (await import('../components/ProjectDocTopology')).default

/** The per-type tally the graph is drawn from. */
function summary(
  types: { doc_type: string; count: number; suspect_links: number }[],
  membershipEdges: { source_type: string; target_type: string; role: string; count: number }[] = [],
) {
  return {
    types,
    total: types.reduce((sum, entry) => sum + entry.count, 0),
    membership_edges: membershipEdges,
  }
}

function renderTopology() {
  const queryClient = createQueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <ProjectDocTopology projectId={1} prefix="PRJ" />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

async function settled() {
  await waitFor(() => expect(screen.queryByText(/loading topology/i)).toBeNull())
}

beforeEach(() => {
  vi.clearAllMocks()
  docsApi.typeSummary.mockResolvedValue(
    summary([
      { doc_type: docShell.doc_type, count: 1, suspect_links: docShell.suspect_links },
      {
        doc_type: testCaseDocShell.doc_type,
        count: 1,
        suspect_links: testCaseDocShell.suspect_links,
      },
    ]),
  )
  linksApi.list.mockResolvedValue([link])

  globalThis.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  } as never
  globalThis.DOMMatrixReadOnly = class {
    m22 = 1
  } as never
  Element.prototype.getBoundingClientRect = () =>
    ({
      x: 0, y: 0, top: 0, left: 0, right: 800, bottom: 600, width: 800, height: 600,
      toJSON: () => ({}),
    }) as DOMRect
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

describe('loading', () => {
  it('says it is loading until both documents and links have arrived', async () => {
    let releaseLinks: (value: unknown) => void = () => {}
    linksApi.list.mockReturnValue(new Promise((resolve) => (releaseLinks = resolve)))
    renderTopology()

    expect(screen.getByText(/loading topology/i)).toBeTruthy()
    releaseLinks([link])
    await settled()
  })

  it('asks for the tally rather than for the documents', async () => {
    renderTopology()
    await settled()

    expect(docsApi.typeSummary).toHaveBeenCalledWith('PRJ')
    expect(docsApi.list).not.toHaveBeenCalled()
    expect(await screen.findByText('2')).toBeTruthy()
  })
})

describe('the roll-up', () => {
  it('counts the documents and the links', async () => {
    renderTopology()
    await settled()

    const header = screen.getByText('Topology').closest('div')?.parentElement as HTMLElement
    expect(header.textContent).toContain('2')
    expect(header.textContent).toContain('docs')
    expect(header.textContent).toContain('links')
  })

  it('calls out suspect links, and stays quiet when there are none', async () => {
    renderTopology()
    await settled()
    expect(screen.queryByText(/suspect/i)).toBeNull()
    cleanup()

    linksApi.list.mockResolvedValue([
      { ...link, suspect: true },
      { ...link, id: 132, suspect: true },
      { ...link, id: 133, suspect: true },
    ])
    renderTopology()
    await settled()

    await waitFor(() =>
      expect(
        screen.getByText('Topology').closest('div')?.parentElement?.textContent,
      ).toContain('3 suspect'),
    )
  })

  it('shows one node per document type present, and none for absent types', async () => {
    renderTopology()
    await settled()

    expect(screen.getAllByText('Requirements').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Test Cases').length).toBeGreaterThan(0)
    expect(screen.queryByText('Requirement')).toBeNull()
    expect(screen.queryByText('Risks')).toBeNull()
    expect(screen.queryByText('Changes')).toBeNull()
  })

  it('says so when nothing is linked yet', async () => {
    linksApi.list.mockResolvedValue([])
    renderTopology()
    await settled()

    expect(
      await screen.findByText(/link documents to see them here/i),
    ).toBeTruthy()
  })

  it('draws the campaign, suite and test case chain that links never carry', async () => {
    docsApi.typeSummary.mockResolvedValue(
      summary(
        [
          { doc_type: 'CMP', count: 1, suspect_links: 0 },
          { doc_type: 'TS', count: 12, suspect_links: 0 },
          { doc_type: 'TC', count: 285, suspect_links: 0 },
        ],
        [
          { source_type: 'CMP', target_type: 'TS', role: 'relates_to', count: 12 },
          { source_type: 'TS', target_type: 'TC', role: 'contains', count: 285 },
        ],
      ),
    )
    linksApi.list.mockResolvedValue([])
    renderTopology()
    await settled()

    expect(screen.queryByText(/link documents to see them here/i)).toBeNull()
  })

  it('leaves out a membership edge whose type has no documents', async () => {
    docsApi.typeSummary.mockResolvedValue(
      summary(
        [{ doc_type: 'TC', count: 3, suspect_links: 0 }],
        [{ source_type: 'CMP', target_type: 'TS', role: 'relates_to', count: 4 }],
      ),
    )
    linksApi.list.mockResolvedValue([])
    renderTopology()
    await settled()

    expect(await screen.findByText(/link documents to see them here/i)).toBeTruthy()
  })

  it('ignores links whose endpoints are not on the graph', async () => {
    linksApi.list.mockResolvedValue([
      link,
      { ...link, id: 999, source_type: 'RSK', target_type: 'CHG' },
    ])
    renderTopology()
    await settled()

    expect(screen.queryByText(/link documents to see them here/i)).toBeNull()
    expect(screen.queryByText('Risks')).toBeNull()
  })
})

describe('the controls', () => {
  it('rebuilds the layout on request', async () => {
    const { container } = renderTopology()
    await settled()

    const reset = screen.getByTitle('Reset layout')
    fireEvent.click(reset)

    await waitFor(() => expect(container.querySelector('.react-flow')).toBeTruthy())
    expect(screen.getByText('Topology')).toBeTruthy()
  })
})
