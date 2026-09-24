// @vitest-environment jsdom
/**
 * A `{{parameter}}` chip shows the name while editing, with the value on hover, and
 * the value while reading. A parameter without a value keeps showing its name. The
 * steps table of a test case follows the same rule when read.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('../api/client', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>()
  return {
    ...actual,
    projectVariablesApi: { list: vi.fn() },
    projectsApi: { getByPrefix: vi.fn(async () => ({ id: 5, prefix: 'VCU' })) },
  }
})

const client = await import('../api/client')
const DocEditor = (await import('../components/editor/DocEditor')).default
const { TcsArteTable } = await import('../components/TcsArteTable')
const { useParameterValues } = await import('../hooks/useParameterValues')

const EMPTY_RECT = { x: 0, y: 0, top: 0, left: 0, right: 0, bottom: 0, width: 0, height: 0, toJSON: () => ({}) } as DOMRect

function doc(...keys: string[]) {
  return {
    type: 'doc',
    content: [
      {
        type: 'paragraph',
        content: keys.flatMap((key) => [
          { type: 'text', text: 'Boot within ' },
          { type: 'mention', attrs: { id: key, label: key, mentionSuggestionChar: '{{' } },
        ]),
      },
    ],
  }
}

function chips(container: HTMLElement) {
  return Array.from(container.querySelectorAll('.ProseMirror .mention')) as HTMLElement[]
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

describe('the parameter chip', () => {
  it('shows the name while editing, the value on hover, and the value while reading', async () => {
    const values = { BOOT_BUDGET_MS: '500' }
    const { container, rerender } = render(
      <DocEditor content={doc('BOOT_BUDGET_MS')} parameterValues={values} parameterHref="/projects/VCU/parameters" />,
    )
    await waitFor(() => expect(chips(container)).toHaveLength(1))
    expect(chips(container)[0].textContent).toBe('{{BOOT_BUDGET_MS}}')
    expect(chips(container)[0].getAttribute('title')).toBe('500')
    expect(chips(container)[0].getAttribute('href')).toBe('/projects/VCU/parameters?key=BOOT_BUDGET_MS')

    rerender(
      <DocEditor content={doc('BOOT_BUDGET_MS')} parameterValues={values} parameterHref="/projects/VCU/parameters" editable={false} />,
    )
    await waitFor(() => expect(chips(container)[0].textContent).toBe('500'))
    expect(chips(container)[0].getAttribute('title')).toBe('{{BOOT_BUDGET_MS}}')
  })

  it('keeps the name when there is no value, and updates when the values arrive', async () => {
    const { container, rerender } = render(<DocEditor content={doc('MAX_TEMP_C')} editable={false} />)
    await waitFor(() => expect(chips(container)).toHaveLength(1))
    expect(chips(container)[0].textContent).toBe('{{MAX_TEMP_C}}')
    expect(chips(container)[0].tagName).toBe('SPAN')

    rerender(<DocEditor content={doc('MAX_TEMP_C')} editable={false} parameterValues={{ OTHER: '1' }} />)
    await new Promise((resolve) => setTimeout(resolve, 10))
    expect(chips(container)[0].textContent).toBe('{{MAX_TEMP_C}}')

    rerender(<DocEditor content={doc('MAX_TEMP_C')} editable={false} parameterValues={{ MAX_TEMP_C: '85' }} />)
    await waitFor(() => expect(chips(container)[0].textContent).toBe('85'))
  })
})

describe('the steps table when read', () => {
  const rows = [
    {
      id: 'row-1',
      row_type: 'step' as const,
      label: '',
      description: 'Wait {{BOOT_BUDGET_MS}} ms',
      expected_result: 'Below {{MAX_TEMP_C}}',
      indent_level: 0,
      collapsed: false,
    },
  ]

  it('shows values, keeping the name on hover', () => {
    const { container } = render(
      <TcsArteTable
        rows={rows}
        onChange={() => {}}
        editable={false}
        parameterHref="/p"
        parameterValues={{ BOOT_BUDGET_MS: '500' }}
      />,
    )
    const links = Array.from(container.querySelectorAll('a.mention'))
    expect(links.map((a) => a.textContent)).toEqual(['500', '{{MAX_TEMP_C}}'])
    expect(links[0].getAttribute('title')).toBe('{{BOOT_BUDGET_MS}}')
    expect(links[1].getAttribute('title')).toBe('Open parameter MAX_TEMP_C')
  })

  it('shows values without a link target, and plain text without values', () => {
    const { container, rerender } = render(
      <TcsArteTable rows={rows} onChange={() => {}} editable={false} parameterValues={{ MAX_TEMP_C: '85' }} />,
    )
    expect(Array.from(container.querySelectorAll('span.mention')).map((s) => s.textContent)).toEqual([
      '{{BOOT_BUDGET_MS}}',
      '85',
    ])
    rerender(<TcsArteTable rows={rows} onChange={() => {}} editable={false} />)
    expect(container.querySelector('.mention')).toBeNull()
    expect(container.textContent).toContain('Wait {{BOOT_BUDGET_MS}} ms')
  })
})

describe('useParameterValues', () => {
  function wrapper({ children }: { children: ReactNode }) {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  }

  it('maps the project parameters and variables by key', async () => {
    vi.mocked(client.projectVariablesApi.list).mockResolvedValue([
      { id: 1, project_id: 5, kind: 'parameter', key: 'BOOT_BUDGET_MS', value: '500', description: null, created_at: '', updated_at: '' },
      { id: 2, project_id: 5, kind: 'variable', key: 'BOARD_REV', value: 'C', description: null, created_at: '', updated_at: '' },
    ] as never)
    const { result } = renderHook(() => useParameterValues('VCU'), { wrapper })
    await waitFor(() => expect(result.current).toEqual({ BOOT_BUDGET_MS: '500', BOARD_REV: 'C' }))
    expect(client.projectVariablesApi.list).toHaveBeenCalledWith(5)
  })

  it('stays undefined when the reader may not list them', async () => {
    vi.mocked(client.projectVariablesApi.list).mockRejectedValue(new Error('403'))
    const { result } = renderHook(() => useParameterValues(undefined, 5), { wrapper })
    await waitFor(() => expect(client.projectVariablesApi.list).toHaveBeenCalledWith(5))
    expect(result.current).toBeUndefined()
    expect(client.projectsApi.getByPrefix).not.toHaveBeenCalled()
  })
})
