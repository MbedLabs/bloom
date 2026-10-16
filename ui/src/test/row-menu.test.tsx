// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { RowActionsMenu } from '../components/RowMenu'

afterEach(cleanup)

describe('row action menus', () => {
  it('navigates enabled actions by keyboard and returns focus on Escape', () => {
    const download = vi.fn()
    render(<RowActionsMenu label="Attachment actions for report.pdf" actions={[
      { label: 'Download', icon: null, onClick: download },
      { label: 'Unavailable', icon: null, disabled: true, onClick: vi.fn() },
      { label: 'Remove', icon: null, destructive: true, onClick: vi.fn() },
    ]} />)
    const trigger = screen.getByRole('button', { name: 'Attachment actions for report.pdf' })
    trigger.focus()
    fireEvent.keyDown(trigger, { key: 'ArrowDown' })
    expect(trigger.getAttribute('aria-expanded')).toBe('true')
    expect(document.activeElement).toBe(screen.getByRole('menuitem', { name: 'Download' }))
    fireEvent.keyDown(document.activeElement!, { key: 'ArrowDown' })
    expect(document.activeElement).toBe(screen.getByRole('menuitem', { name: 'Remove' }))
    fireEvent.keyDown(document.activeElement!, { key: 'Home' })
    expect(document.activeElement).toBe(screen.getByRole('menuitem', { name: 'Download' }))
    fireEvent.keyDown(document.activeElement!, { key: 'End' })
    expect(document.activeElement).toBe(screen.getByRole('menuitem', { name: 'Remove' }))
    fireEvent.keyDown(document.activeElement!, { key: 'Escape' })
    expect(screen.queryByRole('menu')).toBeNull()
    expect(document.activeElement).toBe(trigger)
    expect(download).not.toHaveBeenCalled()
  })

  it('dismisses outside interaction and closes after one action', () => {
    const remove = vi.fn()
    render(<><button>Outside</button><RowActionsMenu label="Member actions" actions={[{ label: 'Remove', icon: null, onClick: remove }]} /></>)
    const trigger = screen.getByRole('button', { name: 'Member actions' })
    fireEvent.click(trigger)
    fireEvent.pointerDown(screen.getByRole('button', { name: 'Outside' }))
    expect(screen.queryByRole('menu')).toBeNull()
    expect(remove).not.toHaveBeenCalled()
    fireEvent.keyDown(trigger, { key: 'ArrowUp' })
    fireEvent.click(screen.getByRole('menuitem', { name: 'Remove' }))
    expect(remove).toHaveBeenCalledTimes(1)
    expect(screen.queryByRole('menu')).toBeNull()
    expect(document.activeElement).toBe(trigger)
  })

  it('keeps a disabled trigger closed and a busy action inactive', () => {
    const action = vi.fn()
    const { rerender } = render(<RowActionsMenu label="Member actions" disabled actions={[{ label: 'Remove', icon: null, onClick: action }]} />)
    fireEvent.click(screen.getByRole('button', { name: 'Member actions' }))
    expect(screen.queryByRole('menu')).toBeNull()
    rerender(<RowActionsMenu label="Member actions" actions={[{ label: 'Remove', icon: null, disabled: true, onClick: action }]} />)
    fireEvent.click(screen.getByRole('button', { name: 'Member actions' }))
    fireEvent.click(screen.getByRole('menuitem', { name: 'Remove' }))
    expect(action).not.toHaveBeenCalled()
    fireEvent.keyDown(screen.getByRole('menu'), { key: 'Escape' })
    expect(screen.queryByRole('menu')).toBeNull()
  })

  it('restores focus when scrolling or resizing closes a focused menu', () => {
    render(<RowActionsMenu label="Member actions" actions={[{ label: 'Remove', icon: null, onClick: vi.fn() }]} />)
    const trigger = screen.getByRole('button', { name: 'Member actions' })
    fireEvent.click(trigger)
    fireEvent.scroll(document)
    expect(screen.queryByRole('menu')).toBeNull()
    expect(document.activeElement).toBe(trigger)
    fireEvent.click(trigger)
    fireEvent.resize(window)
    expect(screen.queryByRole('menu')).toBeNull()
    expect(document.activeElement).toBe(trigger)
  })

  it('retains measured placement above a row when its parent refreshes', () => {
    const bounds = vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockImplementation(function (this: HTMLElement) {
      if (this.getAttribute('role') === 'menu') return { top: 0, bottom: 38, left: 0, right: 176, width: 176, height: 38, x: 0, y: 0, toJSON: () => ({}) }
      return { top: window.innerHeight - 42, bottom: window.innerHeight - 10, left: 200, right: 232, width: 32, height: 32, x: 200, y: window.innerHeight - 42, toJSON: () => ({}) }
    })
    try {
      const actions = [{ label: 'Remove', icon: null, onClick: vi.fn() }]
      const { rerender } = render(<RowActionsMenu label="Member actions" actions={actions} />)
      fireEvent.click(screen.getByRole('button', { name: 'Member actions' }))
      const menu = screen.getByRole('menu')
      expect(menu.style.top).toBe(`${window.innerHeight - 84}px`)
      rerender(<RowActionsMenu label="Updated member actions" actions={[...actions]} />)
      expect(screen.getByRole('menu').style.top).toBe(`${window.innerHeight - 84}px`)
    } finally {
      bounds.mockRestore()
    }
  })
})
