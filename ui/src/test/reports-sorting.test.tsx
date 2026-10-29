import { createQueryClient } from '../lib/queryClient'
// @vitest-environment jsdom
import { QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router'

const projects = [
  { id: 1, name: 'XYZ', prefix: 'XYZ', status: 'Active', requirement_count: 10, test_case_count: 2, uncovered_requirement_count: 2 },
  { id: 2, name: 'ABC', prefix: 'ABC', status: 'Draft', requirement_count: 2, test_case_count: 100, uncovered_requirement_count: 1 },
  { id: 3, name: 'Demo', prefix: 'PRJ', status: 'Archived', requirement_count: 100, test_case_count: 10, uncovered_requirement_count: 90 },
]
vi.mock('../api/client', () => ({ dashboardApi: { getStats: vi.fn().mockResolvedValue({ projects }) } }))
const Reports = (await import('../pages/Reports')).default
afterEach(cleanup)

describe('Reports project summary sorting', () => {
  it.each([
    ['Project', ['ABC', 'Demo', 'XYZ']],
    ['Status', ['XYZ', 'Demo', 'ABC']],
    ['Requirements', ['ABC', 'XYZ', 'Demo']],
    ['Test Cases', ['XYZ', 'Demo', 'ABC']],
    ['Coverage', ['Demo', 'ABC', 'XYZ']],
    ['Health', ['Demo', 'XYZ', 'ABC']],
  ])('sorts %s in both directions while preserving metrics and source data', async (column, ascending) => {
    const client = createQueryClient({ defaultOptions: { queries: { retry: false } } })
    render(<QueryClientProvider client={client}><MemoryRouter><Reports /></MemoryRouter></QueryClientProvider>)
    await screen.findByRole('table')
    const names = () => within(screen.getByRole('table')).getAllByRole('row').slice(1).map((row) => within(row).getAllByRole('link')[0].textContent)
    const header = screen.getByRole('columnheader', { name: column })
    if (column !== 'Project') fireEvent.click(header)
    expect(names()).toEqual(ascending)
    fireEvent.click(header)
    expect(names()).toEqual([...ascending].reverse())
    const xyz = screen.getByRole('link', { name: 'XYZ' }).closest('tr')!
    expect(within(xyz).getByText('80%')).toBeTruthy()
    expect(within(xyz).getByText('Good')).toBeTruthy()
    expect(projects.map((project) => project.name)).toEqual(['XYZ', 'ABC', 'Demo'])
  })
})
