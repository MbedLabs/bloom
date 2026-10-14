import { fireEvent, screen } from '@testing-library/react'

/** Change a field through its visible themed options or its native input event. */
export function changeControl(element: HTMLElement, event: { target: { value?: string | number; [key: string]: unknown } }) {
  if (element.tagName === 'SELECT' && element.hasAttribute('hidden')) element = element.parentElement!.querySelector('button')!
  if (element.getAttribute('role') !== 'combobox' || element.tagName !== 'BUTTON') throw new Error('Expected a themed selector')
  fireEvent.click(element)
  const value = String(event.target.value)
  const option = screen.getAllByRole('option').find((item) => item.getAttribute('data-value') === value)
  if (!option) throw new Error(`No selectable option for ${value}`)
  fireEvent.click(option)
}

/** Stored values of the choices in a visible themed menu. */
export function optionValues(element: HTMLElement) {
  fireEvent.click(element)
  const values = screen.getAllByRole('option').map((item) => item.getAttribute('data-value'))
  fireEvent.keyDown(element, { key: 'Escape' })
  return values
}
