// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { useState } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import MentionTextarea from '../components/editor/MentionTextarea'

afterEach(cleanup)

const FOUND = [
  { id: 7, label: 'PRJ-DES-007', hint: 'Hydraulic loop' },
  { id: 9, label: 'PRJ-SPEC-009', hint: 'Braking specification' },
]

function Harness({ search }: Readonly<{ search?: (query: string) => Promise<typeof FOUND> }>) {
  const [value, setValue] = useState('')
  return (
    <>
      <MentionTextarea aria-label="Description" value={value} onChange={setValue} artefactSearch={search} />
      <output data-testid="value">{value}</output>
    </>
  )
}

function type(text: string) {
  const box = screen.getByRole('textbox', { name: 'Description' })
  fireEvent.change(box, { target: { value: text, selectionStart: text.length, selectionEnd: text.length } })
}

function offered(): string[] {
  return Array.from(document.querySelectorAll('.mention-suggestion-popover button')).map((node) => node.textContent ?? '')
}

describe('document tags in a plain description', () => {
  it('searches the project under # and offers what it finds', async () => {
    const search = vi.fn().mockResolvedValue(FOUND)
    render(<Harness search={search} />)
    type('follows #hyd')
    await waitFor(() => expect(search).toHaveBeenLastCalledWith('hyd'))
    await waitFor(() => expect(offered().join(' ')).toContain('PRJ-DES-007'))
    expect(offered().join(' ')).toContain('PRJ-SPEC-009')
  })

  it('writes the chosen document as #ID', async () => {
    render(<Harness search={vi.fn().mockResolvedValue(FOUND)} />)
    type('follows #hyd')
    fireEvent.click(await screen.findByText(/PRJ-DES-007/))
    expect(screen.getByTestId('value').textContent).toBe('follows #PRJ-DES-007')
  })

  it('offers nothing under # without a search', () => {
    render(<Harness />)
    type('issue #12')
    expect(offered()).toEqual([])
  })
})
