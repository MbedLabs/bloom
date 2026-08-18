// @vitest-environment jsdom
/**
 * The popover that appears when a `{{` or an `@` is typed in the editor.
 *
 * It is driven almost entirely from the keyboard - the suggestion plugin
 * forwards every keystroke to it and acts on what it returns - so the
 * interesting behaviour is which keys it claims, how the highlight wraps at
 * either end of the list, and what it does with a key it does not handle. None
 * of that was covered.
 */
import { act, cleanup, fireEvent, render, screen } from '@testing-library/react'
import { createRef } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import MentionList, { type MentionListRef } from '../components/editor/MentionList'

/** Project parameters and variables: what `{{` addresses. */
const items = [
  { id: 1, label: 'BOOT_BUDGET_MS' },
  { id: 2, label: 'MAX_TEMP_C' },
  { id: 3, label: 'BOARD_REV' },
]

/** People: what `@` addresses. The two triggers never share a list. */
const people = [
  { id: 11, label: 'Ada Lovelace' },
  { id: 12, label: 'Grace Hopper' },
]

/**
 * Mount the list as the `{{` trigger opens it. Every case that is not about
 * people uses this, so a parameter is never shown behind an `@`.
 */
function mountList(props: Partial<React.ComponentProps<typeof MentionList>> = {}) {
  const command = vi.fn()
  const ref = createRef<MentionListRef>()
  const view = render(
    <MentionList
      ref={ref}
      items={items}
      command={command}
      triggerPrefix="{{"
      triggerSuffix="}}"
      {...props}
    />,
  )
  return { command, ref, ...view }
}

/**
 * What the suggestion plugin does with a keystroke. The plugin calls this from
 * outside React, so the state change it causes has to be flushed by hand.
 */
function press(ref: React.RefObject<MentionListRef | null>, key: string): boolean {
  let handled = false
  act(() => {
    handled = ref.current!.onKeyDown({ event: new KeyboardEvent('keydown', { key }) })
  })
  return handled
}

/** The label of the entry currently highlighted. */
function highlighted(): string {
  const active = screen
    .getAllByRole('button')
    .find((button) => button.className.includes('text-primary'))
  if (!active) throw new Error('nothing is highlighted')
  return active.textContent ?? ''
}

afterEach(cleanup)

describe('the mention popover', () => {
  it('wraps each suggestion in the trigger it was opened with', () => {
    mountList()

    expect(screen.getByText('{{BOOT_BUDGET_MS}}')).toBeTruthy()
    expect(screen.getByText('{{MAX_TEMP_C}}')).toBeTruthy()
  })

  it('uses a bare @ for people, who take no closing braces', () => {
    mountList({ triggerPrefix: '@', triggerSuffix: '', items: people })

    expect(screen.getByText('@Ada Lovelace')).toBeTruthy()
    expect(screen.getByText('@Grace Hopper')).toBeTruthy()
    // A person is never wrapped in braces; that spelling belongs to a
    // parameter, and the two are looked up in different places.
    expect(screen.queryByText('{{Ada Lovelace}}')).toBeNull()
  })

  it('highlights the first entry to begin with', () => {
    mountList()

    expect(highlighted()).toBe('{{BOOT_BUDGET_MS}}')
  })

  it('moves the highlight down the list', () => {
    const { ref } = mountList()

    expect(press(ref, 'ArrowDown')).toBe(true)
    expect(highlighted()).toBe('{{MAX_TEMP_C}}')
  })

  it('wraps round the bottom of the list', () => {
    const { ref } = mountList()

    press(ref, 'ArrowDown')
    press(ref, 'ArrowDown')
    press(ref, 'ArrowDown')

    expect(highlighted()).toBe('{{BOOT_BUDGET_MS}}')
  })

  it('wraps round the top of the list', () => {
    const { ref } = mountList()

    expect(press(ref, 'ArrowUp')).toBe(true)
    expect(highlighted()).toBe('{{BOARD_REV}}')
  })

  it('inserts the highlighted entry on Enter', () => {
    const { ref, command } = mountList()

    press(ref, 'ArrowDown')
    expect(press(ref, 'Enter')).toBe(true)

    expect(command).toHaveBeenCalledWith(items[1])
  })

  it('inserts the entry that was clicked', () => {
    const { command } = mountList()

    fireEvent.click(screen.getByText('{{BOARD_REV}}'))

    expect(command).toHaveBeenCalledWith(items[2])
  })

  it('leaves any other key to the editor', () => {
    const { ref, command } = mountList()

    // Returning false is what lets the keystroke reach the document; claiming
    // it would swallow ordinary typing while the popover is open.
    expect(press(ref, 'a')).toBe(false)
    expect(press(ref, 'Escape')).toBe(false)
    expect(command).not.toHaveBeenCalled()
  })

  it('says so when nothing matches, and inserts nothing on Enter', () => {
    const { ref, command } = mountList({ items: [] })

    expect(screen.getByText('No results')).toBeTruthy()
    expect(press(ref, 'Enter')).toBe(true)
    expect(command).not.toHaveBeenCalled()
  })

  it('starts again from the top when the query narrows the list', () => {
    const { ref, rerender, command } = mountList()

    press(ref, 'ArrowDown')
    press(ref, 'ArrowDown')
    expect(highlighted()).toBe('{{BOARD_REV}}')

    // Typing another character re-filters; a highlight left at index 2 would
    // point past the end of the shorter list.
    rerender(
      <MentionList
        ref={ref}
        items={items.slice(0, 2)}
        command={command}
        triggerPrefix="{{"
        triggerSuffix="}}"
      />,
    )

    expect(highlighted()).toBe('{{BOOT_BUDGET_MS}}')
  })
})
