import { createQueryClient } from '../lib/queryClient'
// @vitest-environment jsdom
import { QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router'

const projects = [
  { id: 1, name: 'Zulu', prefix: 'ZUL', status: 'Active', requirement_count: 10, test_case_count: 2, uncovered_requirement_count: 2 },
  { id: 2, name: 'Alpha', prefix: 'ALP', status: 'Draft', requirement_count: 2, test_case_count: 100, uncovered_requirement_count: 1 },
  { id: 3, name: 'Bravo', prefix: 'BRA', status: 'Archived', requirement_count: 100, test_case_count: 10, uncovered_requirement_count: 90 },
]
vi.mock('../api/client', () => ({ dashboardApi: { getStats: vi.fn().mockResolvedValue({ projects }) } }))
const Reports = (await import('../pages/Reports')).default
afterEach(cleanup)

describe('Reports project summary sorting', () => {
  it.each([
    ['Project', ['Alpha', 'Bravo', 'Zulu']],
    ['Status', ['Zulu', 'Bravo', 'Alpha']],
    ['Requirements', ['Alpha', 'Zulu', 'Bravo']],
    ['Test Cases', ['Zulu', 'Bravo', 'Alpha']],
    ['Coverage', ['Bravo', 'Alpha', 'Zulu']],
    ['Health', ['Bravo', 'Zulu', 'Alpha']],
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
    const zulu = screen.getByRole('link', { name: 'Zulu' }).closest('tr')!
    expect(within(zulu).getByText('80%')).toBeTruthy()
    expect(within(zulu).getByText('Good')).toBeTruthy()
    expect(projects.map((project) => project.name)).toEqual(['Zulu', 'Alpha', 'Bravo'])
  })
})
