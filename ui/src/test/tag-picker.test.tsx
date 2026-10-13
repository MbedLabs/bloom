import { createQueryClient } from '../lib/queryClient'
// @vitest-environment jsdom
import { QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { useState } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'

const scope = vi.hoisted(() => ({ value: { limited: false, tags: [] as { id: number; name: string; created_at: string }[] } }))
const seen = vi.hoisted(() => ({ last: [] as number[] }))

vi.mock('../api/client', () => ({
  tagsApi: { scope: vi.fn(async () => scope.value) },
}))

const TagPicker = (await import('../components/TagPicker')).default

function Host() {
  const [value, setValue] = useState<number[]>([])
  seen.last = value
  return <TagPicker projectId={7} value={value} onChange={setValue} />
}

function renderPicker() {
  const client = createQueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <Host />
    </QueryClientProvider>,
  )
}

afterEach(cleanup)

describe('the tag picker on a create form', () => {
  it('preselects the only tag of a limited scope', async () => {
    scope.value = { limited: true, tags: [{ id: 4, name: 'Field', created_at: '' }] }
    renderPicker()
    expect(await screen.findByText('Origin (choose at least one)')).toBeTruthy()
    await waitFor(() => expect(seen.last).toEqual([4]))
  })

  it('lets an unscoped user pick any tag or none', async () => {
    scope.value = {
      limited: false,
      tags: [
        { id: 4, name: 'Field', created_at: '' },
        { id: 5, name: 'Lab', created_at: '' },
      ],
    }
    renderPicker()
    fireEvent.click(await screen.findByRole('button', { name: 'Lab' }))
    expect(seen.last).toEqual([5])
    fireEvent.click(screen.getByRole('button', { name: 'Lab' }))
    expect(seen.last).toEqual([])
    expect(screen.getByText('Origin')).toBeTruthy()
  })

  it('shows nothing when there are no tags', async () => {
    scope.value = { limited: false, tags: [] }
    const { container } = renderPicker()
    await waitFor(() => expect(container.textContent).toBe(''))
  })
})
