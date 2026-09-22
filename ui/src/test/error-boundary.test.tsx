// @vitest-environment jsdom

import { type ReactNode } from 'react'
import '@testing-library/jest-dom/vitest'
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import ErrorBoundary from '../components/ErrorBoundary'

function Boom(): ReactNode {
  throw new Error('kaboom')
}

beforeEach(() => {
  vi.spyOn(console, 'error').mockImplementation(() => undefined)
})

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

describe('ErrorBoundary', () => {
  it('renders its children when nothing throws', () => {
    render(
      <MemoryRouter>
        <ErrorBoundary>
          <div>all good</div>
        </ErrorBoundary>
      </MemoryRouter>,
    )
    expect(screen.getByText('all good')).toBeInTheDocument()
  })

  it('shows a fallback and the error message when a child throws', () => {
    render(
      <MemoryRouter>
        <ErrorBoundary>
          <Boom />
        </ErrorBoundary>
      </MemoryRouter>,
    )
    expect(screen.getByText('Something went wrong')).toBeInTheDocument()
    expect(screen.getByText('kaboom')).toBeInTheDocument()
  })
})
