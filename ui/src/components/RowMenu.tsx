import type { ReactNode } from 'react'

/** Where an open row menu is drawn, in viewport pixels. */
export type MenuPosition = { top: number; left: number }

const MENU_WIDTH = 176

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
        <div className="fixed z-100 w-44 border border-border bg-card shadow-elegant" style={{ top: position.top, left: position.left }}>
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
  onClick,
}: Readonly<{
  icon: ReactNode
  label: string
  destructive?: boolean
  onClick: () => void
}>) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-accent ${destructive ? 'text-destructive' : 'text-foreground'}`}
    >
      {icon}
      {label}
    </button>
  )
}
