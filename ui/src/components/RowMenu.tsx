import { useEffect, useId, useLayoutEffect, useRef, useState, type ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { MoreVertical } from 'lucide-react'

/** Where an open row menu is drawn, in viewport pixels. */
export type MenuPosition = { top: number; left: number }

const MENU_WIDTH = 176
const MENU_CLASS_NAME = 'fixed z-100 w-44 border border-border bg-card shadow-elegant'

/** The position of a menu of the given height for its button: below it, or above it when the viewport has no room below. */
function menuPositionFor(button: HTMLButtonElement, menuHeight: number): MenuPosition {
  const rect = button.getBoundingClientRect()
  const spaceBelow = window.innerHeight - rect.bottom
  const top = spaceBelow < menuHeight + 12
    ? Math.max(8, rect.top - menuHeight - 4)
    : rect.bottom + 4
  const left = Math.min(window.innerWidth - MENU_WIDTH - 8, Math.max(8, rect.right - MENU_WIDTH))
  return { top, left }
}

/**
 * A row's action button and, while open, its menu at a fixed position. A click on the button
 * passes the position for a menu of `menuHeight` pixels to `onToggle`; the caller keeps which
 * menu is open and where.
 */
export function RowMenu({
  icon,
  title,
  buttonClassName,
  menuHeight,
  open,
  position,
  onToggle,
  children,
}: Readonly<{
  icon: ReactNode
  title: string
  buttonClassName: string
  menuHeight: number
  open: boolean
  position: MenuPosition | null
  onToggle: (position: MenuPosition) => void
  children: ReactNode
}>) {
  return (
    <>
      <button
        type="button"
        onClick={(event) => onToggle(menuPositionFor(event.currentTarget, menuHeight))}
        className={buttonClassName}
        title={title}
      >
        {icon}
      </button>
      {open && position && (
        <div className={MENU_CLASS_NAME} style={{ top: position.top, left: position.left }}>
          {children}
        </div>
      )}
    </>
  )
}

/** One entry of a row menu. */
export function MenuAction({
  icon,
  label,
  destructive = false,
  disabled = false,
  role,
  onClick,
}: Readonly<{
  icon: ReactNode
  label: string
  destructive?: boolean
  disabled?: boolean
  role?: 'menuitem'
  onClick: () => void
}>) {
  const colorClassName = destructive ? 'text-destructive' : 'text-foreground'
  return (
    <button
      type="button"
      role={role}
      tabIndex={role ? -1 : undefined}
      disabled={disabled}
      onClick={onClick}
      className={`flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-accent disabled:opacity-50 ${role ? '[@media(pointer:coarse)]:min-h-11' : ''} ${role && destructive ? 'text-[#c52632] dark:text-red-500' : colorClassName}`}
    >
      {icon}
      {label}
    </button>
  )
}

type RowAction = {
  icon: ReactNode
  label: string
  destructive?: boolean
  disabled?: boolean
  onClick: () => void
}

/** A vertical row action menu with keyboard navigation and viewport placement. */
export function RowActionsMenu({ label, actions, disabled = false }: Readonly<{
  label: string
  actions: readonly RowAction[]
  disabled?: boolean
}>) {
  const id = useId()
  const button = useRef<HTMLButtonElement>(null)
  const menu = useRef<HTMLDivElement>(null)
  const [position, setPosition] = useState<MenuPosition | null>(null)
  const [lastFirst, setLastFirst] = useState(false)
  const open = position !== null

  const close = () => {
    setPosition(null)
    button.current?.focus()
  }
  const show = (last = false) => {
    if (disabled || !button.current) return
    setLastFirst(last)
    setPosition(menuPositionFor(button.current, actions.length * 44 + 2))
  }

  useLayoutEffect(() => {
    if (!open || !menu.current || !button.current) return
    const items = menu.current.querySelectorAll<HTMLButtonElement>('[role="menuitem"]:not(:disabled)')
    ;(items[lastFirst ? items.length - 1 : 0] ?? menu.current).focus()
    const next = menuPositionFor(button.current, menu.current.getBoundingClientRect().height)
    setPosition({ ...next, left: Math.max(8, next.left) })
  }, [open, lastFirst])

  useEffect(() => {
    if (!open) return
    const outside = (event: Event) => {
      if (!button.current?.contains(event.target as Node) && !menu.current?.contains(event.target as Node)) setPosition(null)
    }
    const dismiss = () => {
      const hadFocus = menu.current?.contains(document.activeElement)
      setPosition(null)
      if (hadFocus) button.current?.focus()
    }
    const scroll = (event: Event) => {
      if (!menu.current?.contains(event.target as Node)) dismiss()
    }
    document.addEventListener('pointerdown', outside)
    document.addEventListener('scroll', scroll, true)
    window.addEventListener('resize', dismiss)
    return () => {
      document.removeEventListener('pointerdown', outside)
      document.removeEventListener('scroll', scroll, true)
      window.removeEventListener('resize', dismiss)
    }
  }, [open])

  return <>
    <button ref={button} type="button" title={label} aria-label={label} aria-haspopup="menu"
      aria-expanded={open} aria-controls={open ? id : undefined} disabled={disabled}
      className="flex h-8 w-8 shrink-0 items-center justify-center rounded border border-transparent text-muted-foreground hover:bg-accent hover:text-foreground aria-expanded:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-wait disabled:opacity-50 [@media(pointer:coarse)]:h-11 [@media(pointer:coarse)]:w-11"
      onClick={() => { if (open) close(); else show() }}
      onKeyDown={(event) => {
        if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
          event.preventDefault()
          show(event.key === 'ArrowUp')
        }
      }}>
      <MoreVertical className="h-4 w-4" aria-hidden="true" />
    </button>
    {position && createPortal(<div ref={menu} id={id} role="menu" aria-label={label} tabIndex={-1}
      className={`${MENU_CLASS_NAME} themed-scrollbar max-w-[calc(100vw-16px)] overflow-y-auto`}
      style={{ ...position, maxHeight: 'calc(100dvh - 16px)' }}
      onBlur={(event) => { if (!event.currentTarget.contains(event.relatedTarget as Node | null) && event.relatedTarget !== button.current) setPosition(null) }}
      onKeyDown={(event) => {
        if (event.key === 'Escape' || event.key === 'Tab') {
          if (event.key === 'Escape') event.preventDefault()
          close()
          return
        }
        if (!['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) return
        event.preventDefault()
        const items = [...event.currentTarget.querySelectorAll<HTMLButtonElement>('[role="menuitem"]:not(:disabled)')]
        const current = items.indexOf(document.activeElement as HTMLButtonElement)
        let next = (current + (event.key === 'ArrowUp' ? -1 : 1) + items.length) % items.length
        if (event.key === 'Home') next = 0
        else if (event.key === 'End') next = items.length - 1
        items[next]?.focus()
      }}>
      {actions.map((action) => <MenuAction key={action.label} {...action} disabled={disabled || action.disabled} role="menuitem" onClick={() => { close(); action.onClick() }} />)}
    </div>, document.body)}
  </>
}
