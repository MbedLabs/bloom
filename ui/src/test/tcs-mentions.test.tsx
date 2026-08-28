// @vitest-environment jsdom
/**
 * Mentions inside a test case.
 *
 * A test case has no rich-text body - the step table *is* the document - so the
 * two triggers a requirement gets have to work in the table's own cells. They
 * are not decorative here: a step that pins a value ("ramp to {{BOOT_BUDGET_MS}}")
 * is the surface where a project parameter is most often used, and before this
 * the table was a plain textarea where `{{` and `@` did nothing at all.
 *
 * The cells store plain strings, so a mention has to serialize to the same text
 * DocEditor writes - `{{KEY}}` and `@Name` - or the same parameter would be
 * addressed two different ways depending on which screen wrote it.
 */
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { useState } from 'react'
import { afterEach, describe, expect, it } from 'vitest'

import { TcsArteTable } from '../components/TcsArteTable'
import { createDefaultTcsRow, type TcsRow } from '../utils/tcs'

afterEach(cleanup)

const PARAMETERS = [
  { id: 301, label: 'BOOT_BUDGET_MS' },
  { id: 302, label: 'BOARD_REV' },
]
const PEOPLE = [
  { id: 7, label: 'Grace Hopper' },
  { id: 8, label: 'Ada Lovelace' },
]

function Harness() {
  const [rows, setRows] = useState<TcsRow[]>([createDefaultTcsRow('step')])
  return (
    <>
      <TcsArteTable
        rows={rows}
        onChange={setRows}
        editable
        mentionItems={PARAMETERS}
        userMentionItems={PEOPLE}
      />
      <output data-testid="description">{rows[0].description}</output>
      <output data-testid="expected">{rows[0].expected_result}</output>
    </>
  )
}

function actionCell(): HTMLTextAreaElement {
  return screen.getByPlaceholderText('Action / description') as HTMLTextAreaElement
}

function expectedCell(): HTMLTextAreaElement {
  return screen.getByPlaceholderText('Expected result') as HTMLTextAreaElement
}

/** Type into a cell and put the caret at the end, the way a person would. */
function type(cell: HTMLTextAreaElement, text: string) {
  fireEvent.change(cell, { target: { value: text, selectionStart: text.length, selectionEnd: text.length } })
}

function offered(): string[] {
  return Array.from(document.querySelectorAll('.mention-suggestion-popover button')).map(
    (node) => node.textContent ?? '',
  )
}

describe('mentions in the step table', () => {
  it('offers project parameters under {{', () => {
    render(<Harness />)
    type(actionCell(), 'ramp to {{')
    expect(offered()).toEqual(['{{BOOT_BUDGET_MS}}', '{{BOARD_REV}}'])
  })

  it('offers people, and only people, under @', () => {
    render(<Harness />)
    type(actionCell(), 'ask @')
    expect(offered()).toEqual(['@Grace Hopper', '@Ada Lovelace'])
  })

  it('narrows the list as the query is typed', () => {
    render(<Harness />)
    type(actionCell(), '{{BOARD')
    expect(offered()).toEqual(['{{BOARD_REV}}'])
  })

  it('writes a parameter as {{KEY}}, the same text DocEditor writes', () => {
    render(<Harness />)
    type(actionCell(), 'ramp to {{BOOT')
    fireEvent.click(screen.getByText('{{BOOT_BUDGET_MS}}'))
    expect(screen.getByTestId('description').textContent).toBe('ramp to {{BOOT_BUDGET_MS}}')
  })

  it('writes a person as @Name', () => {
    render(<Harness />)
    type(actionCell(), 'ask @Grace')
    fireEvent.click(screen.getByText('@Grace Hopper'))
    expect(screen.getByTestId('description').textContent).toBe('ask @Grace Hopper')
  })

  it('works in the expected-result cell too', () => {
    render(<Harness />)
    type(expectedCell(), 'within {{BOOT')
    fireEvent.click(screen.getByText('{{BOOT_BUDGET_MS}}'))
    expect(screen.getByTestId('expected').textContent).toBe('within {{BOOT_BUDGET_MS}}')
  })

  it('keeps the two lists apart', () => {
    render(<Harness />)
    type(actionCell(), '{{')
    expect(offered().join(' ')).not.toContain('Grace Hopper')
    cleanup()

    render(<Harness />)
    type(actionCell(), '@')
    expect(offered().join(' ')).not.toContain('BOOT_BUDGET_MS')
  })

  it('leaves ordinary text alone', () => {
    render(<Harness />)
    type(actionCell(), 'power on the board')
    expect(document.querySelector('.mention-suggestion-popover')).toBeNull()
  })

  // A `{` that never becomes `{{`, or an `@` with no match, must not leave a
  // popover sitting over the table.
  it('closes once the trigger no longer matches anything', () => {
    render(<Harness />)
    type(actionCell(), '{{ZZZ')
    expect(offered()).toEqual([])
    type(actionCell(), 'plain text')
    expect(document.querySelector('.mention-suggestion-popover')).toBeNull()
  })
})

describe('keyboard handling in the step table', () => {
  it('moves through the list with the arrow keys and takes the selection on Enter', () => {
    render(<Harness />)
    const cell = actionCell()
    type(cell, '{{')

    fireEvent.keyDown(cell, { key: 'ArrowDown' })
    fireEvent.keyDown(cell, { key: 'Enter' })

    expect(screen.getByTestId('description').textContent).toBe('{{BOARD_REV}}')
  })

  it('wraps from the first entry to the last', () => {
    render(<Harness />)
    const cell = actionCell()
    type(cell, '@')

    fireEvent.keyDown(cell, { key: 'ArrowUp' })
    fireEvent.keyDown(cell, { key: 'Enter' })

    expect(screen.getByTestId('description').textContent).toBe('@Ada Lovelace')
  })

  it('closes on Escape without writing anything', () => {
    render(<Harness />)
    const cell = actionCell()
    type(cell, 'ramp to {{')

    fireEvent.keyDown(cell, { key: 'Escape' })

    expect(document.querySelector('.mention-suggestion-popover')).toBeNull()
    expect(screen.getByTestId('description').textContent).toBe('ramp to {{')
  })

  // The cell has to stay a textarea. Swallowing Enter whenever a trigger was
  // open would mean a stray `@` behind the caret silently costs the user their
  // newline, which is worse than offering no completion at all.
  it('leaves Enter to the textarea when the list has nothing to offer', () => {
    render(<Harness />)
    const cell = actionCell()
    type(cell, 'ask @ZZZ')

    expect(fireEvent.keyDown(cell, { key: 'Enter' })).toBe(true)
  })

  it('takes Enter only while a selectable entry is showing', () => {
    render(<Harness />)
    const cell = actionCell()
    type(cell, 'ask @Grace')

    expect(fireEvent.keyDown(cell, { key: 'Enter' })).toBe(false)
  })

  it('ignores the triggers when text is selected rather than a caret sitting in it', () => {
    render(<Harness />)
    const cell = actionCell()
    fireEvent.change(cell, { target: { value: 'ramp to {{', selectionStart: 0, selectionEnd: 10 } })

    expect(document.querySelector('.mention-suggestion-popover')).toBeNull()
  })
})

describe('reading a parameter back out of a step', () => {
  const STEP = {
    ...createDefaultTcsRow('step'),
    description: 'ramp to {{BOOT_BUDGET_MS}} then hold',
    expected_result: 'within {{BOOT_BUDGET_MS}}',
  }

  it('links each reference to the screen that owns the value', () => {
    render(<TcsArteTable rows={[STEP]} onChange={() => {}} parameterHref="/projects/FLT/parameters" />)

    // A step is plain text, so a reference is only characters - "{{BOOT_BUDGET_MS}}"
    // says nothing about what the budget is unless you can go and look.
    const links = Array.from(document.querySelectorAll('a')) as HTMLAnchorElement[]
    expect(links.map((a) => a.textContent)).toEqual(['{{BOOT_BUDGET_MS}}', '{{BOOT_BUDGET_MS}}'])
    expect(links[0].getAttribute('href')).toBe('/projects/FLT/parameters')
  })

  it('keeps the surrounding words intact', () => {
    const { container } = render(
      <TcsArteTable rows={[STEP]} onChange={() => {}} parameterHref="/projects/FLT/parameters" />,
    )

    expect(container.textContent).toContain('ramp to {{BOOT_BUDGET_MS}} then hold')
  })

  it('leaves the text alone when there is nowhere to send the reader', () => {
    render(<TcsArteTable rows={[STEP]} onChange={() => {}} />)

    expect(document.querySelector('a')).toBeNull()
  })

  it('does not invent links for ordinary braces', () => {
    const plain = { ...createDefaultTcsRow('step'), description: 'set {x} to 3', expected_result: 'ok' }
    render(<TcsArteTable rows={[plain]} onChange={() => {}} parameterHref="/projects/FLT/parameters" />)

    expect(document.querySelector('a')).toBeNull()
  })
})
