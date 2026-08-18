// @vitest-environment jsdom
/**
 * Editing a test case's steps.
 *
 * The step table *is* the test case - there is no rich-text body behind it - so
 * everything a user needs to do to a procedure has to work here: add a row,
 * insert one in the middle, rewrite it, duplicate it, indent it under a loop,
 * and delete it. The existing tests only checked the pure row helpers; these
 * drive the editor itself.
 */
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { useState } from 'react'
import { afterEach, describe, expect, it } from 'vitest'

import { TcsArteTable } from '../components/TcsArteTable'
import { createDefaultTcsRow, type TcsRow } from '../utils/tcs'

afterEach(cleanup)

function step(description: string, expected: string, indent = 0): TcsRow {
  return { ...createDefaultTcsRow('step'), description, expected_result: expected, indent_level: indent }
}

/** Holds the rows in state the way the detail page does, so edits stick. */
function Harness({ initial }: { initial: TcsRow[] }) {
  const [rows, setRows] = useState(initial)
  return (
    <>
      <TcsArteTable rows={rows} onChange={setRows} editable />
      <output data-testid="row-count">{rows.length}</output>
      <output data-testid="indents">{rows.map((row) => row.indent_level).join(',')}</output>
    </>
  )
}

function rowCount(): number {
  return Number(screen.getByTestId('row-count').textContent)
}

function openRowMenu(index: number) {
  fireEvent.click(screen.getAllByTitle('Row actions')[index])
}

describe('the step table', () => {
  it('adds a step', () => {
    render(<Harness initial={[step('Power on', 'It boots')]} />)
    expect(rowCount()).toBe(1)

    fireEvent.click(screen.getByTitle('Add row'))
    fireEvent.click(screen.getByRole('button', { name: /^step$/i }))

    expect(rowCount()).toBe(2)
  })

  it('inserts a step below an existing one', () => {
    render(<Harness initial={[step('First', 'ok'), step('Third', 'ok')]} />)

    openRowMenu(0)
    fireEvent.click(screen.getByRole('button', { name: 'Insert below' }))

    expect(rowCount()).toBe(3)
    const actions = screen.getAllByPlaceholderText('Action / description') as HTMLTextAreaElement[]
    expect(actions.map((field) => field.value)).toEqual(['First', '', 'Third'])
  })

  it('rewrites a step and its expected result', () => {
    render(<Harness initial={[step('Power on', 'It boots')]} />)

    const action = screen.getByPlaceholderText('Action / description')
    fireEvent.change(action, { target: { value: 'Power on with a flat battery' } })
    fireEvent.change(screen.getByPlaceholderText('Expected result'), {
      target: { value: 'It refuses to boot' },
    })

    expect((action as HTMLTextAreaElement).value).toBe('Power on with a flat battery')
    expect((screen.getByPlaceholderText('Expected result') as HTMLTextAreaElement).value).toBe(
      'It refuses to boot',
    )
  })

  it('duplicates a step, giving the copy its own identity', () => {
    render(<Harness initial={[step('Power on', 'It boots')]} />)

    openRowMenu(0)
    fireEvent.click(screen.getByRole('button', { name: 'Duplicate' }))

    expect(rowCount()).toBe(2)
    const actions = screen.getAllByPlaceholderText('Action / description') as HTMLTextAreaElement[]
    expect(actions.map((field) => field.value)).toEqual(['Power on', 'Power on'])
    // Editing the copy must not edit the original.
    fireEvent.change(actions[1], { target: { value: 'Power on again' } })
    const after = screen.getAllByPlaceholderText('Action / description') as HTMLTextAreaElement[]
    expect(after.map((field) => field.value)).toEqual(['Power on', 'Power on again'])
  })

  it('indents and outdents a step', () => {
    render(<Harness initial={[step('Outer', 'ok'), step('Inner', 'ok')]} />)

    openRowMenu(1)
    fireEvent.click(screen.getByRole('button', { name: 'Indent' }))
    expect(screen.getByTestId('indents').textContent).toBe('0,1')

    openRowMenu(1)
    fireEvent.click(screen.getByRole('button', { name: 'Outdent' }))
    expect(screen.getByTestId('indents').textContent).toBe('0,0')
  })

  it('never outdents past the left margin', () => {
    render(<Harness initial={[step('Only', 'ok')]} />)

    openRowMenu(0)
    fireEvent.click(screen.getByRole('button', { name: 'Outdent' }))

    expect(screen.getByTestId('indents').textContent).toBe('0')
  })

  it('deletes a step', () => {
    render(<Harness initial={[step('Keep', 'ok'), step('Remove', 'ok')]} />)

    openRowMenu(1)
    fireEvent.click(screen.getByRole('button', { name: 'Delete' }))

    expect(rowCount()).toBe(1)
    expect(
      (screen.getByPlaceholderText('Action / description') as HTMLTextAreaElement).value,
    ).toBe('Keep')
  })

  it('collapses a loop and hides the steps nested under it', () => {
    const loop = { ...createDefaultTcsRow('loop'), description: 'For each channel' }
    render(<Harness initial={[loop, step('Read voltage', 'In range', 1)]} />)
    expect(screen.getAllByPlaceholderText('Action / description')).toHaveLength(1)

    fireEvent.click(screen.getByTitle('Collapse loop'))

    expect(screen.queryByPlaceholderText('Action / description')).toBeNull()
    fireEvent.click(screen.getByTitle('Expand loop'))
    expect(screen.getAllByPlaceholderText('Action / description')).toHaveLength(1)
  })

  it('reorders a step by dragging it', () => {
    render(<Harness initial={[step('First', 'ok'), step('Second', 'ok')]} />)
    const rows = screen.getAllByPlaceholderText('Action / description') as HTMLTextAreaElement[]
    const draggables = rows.map((field) => field.closest('[draggable]')!)

    fireEvent.dragStart(draggables[1])
    fireEvent.dragOver(draggables[0])
    fireEvent.drop(draggables[0])

    const after = screen.getAllByPlaceholderText('Action / description') as HTMLTextAreaElement[]
    expect(after.map((field) => field.value)).toEqual(['Second', 'First'])
  })
})

describe('the read-only table', () => {
  it('shows the procedure without any editing controls', () => {
    render(<TcsArteTable rows={[step('Power on', 'It boots')]} onChange={() => {}} />)

    expect(screen.getByText('Power on')).toBeTruthy()
    expect(screen.getByText('It boots')).toBeTruthy()
    expect(screen.queryByTitle('Add row')).toBeNull()
    expect(screen.queryByTitle('Row actions')).toBeNull()
  })

  it('keeps a collapsed loop collapsed for the reader', () => {
    const loop = { ...createDefaultTcsRow('loop'), description: 'For each channel', collapsed: true }
    render(
      <TcsArteTable rows={[loop, step('Read voltage', 'In range', 1)]} onChange={() => {}} />,
    )

    expect(screen.getByText('For each channel')).toBeTruthy()
    expect(screen.queryByText('Read voltage')).toBeNull()
  })

  it('renders nothing at all for a test case with no steps', () => {
    const { container } = render(<TcsArteTable rows={[]} onChange={() => {}} />)
    expect(container.firstChild).toBeNull()
  })
})
