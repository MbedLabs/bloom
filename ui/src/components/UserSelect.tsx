import { useEffect, useId, useRef, useState } from 'react'
import { ChevronDown } from 'lucide-react'
import type { ProfilePerson } from '../api/client'
import UserIdentity from './UserIdentity'

export default function UserSelect({ value, onChange, users, label, emptyLabel = 'Unassigned', options = [], className = '' }: {
  value: string
  onChange: (value: string) => void
  users: Array<ProfilePerson & { id: number }>
  label: string
  emptyLabel?: string
  options?: Array<{ value: string; label: string }>
  className?: string
}) {
  const id = useId()
  const button = useRef<HTMLButtonElement>(null)
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(0)
  const choices = [{ value: '', label: emptyLabel, user: undefined as ProfilePerson | undefined },
    ...options.map(option => ({ ...option, user: undefined as ProfilePerson | undefined })),
    ...users.map(user => ({ value: String(user.id), label: user.full_name, user }))]
  const selected = choices.find(choice => choice.value === value) ?? choices[0]
  const list = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (open) list.current?.children[active]?.scrollIntoView?.({ block: 'nearest' })
  }, [open, active])
  const choose = (index: number) => {
    if (!choices[index]) return
    onChange(choices[index].value)
    setOpen(false)
    button.current?.focus()
  }
  return <div className="relative" onBlur={event => {
    if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setOpen(false)
  }}>
    <button ref={button} type="button" role="combobox" aria-label={label} title={label}
      aria-expanded={open} aria-haspopup="listbox" aria-controls={`${id}-list`}
      aria-activedescendant={open ? `${id}-${active}` : undefined}
      className={`flex w-full items-center justify-between gap-2 rounded-md border border-input bg-background px-2.5 py-1.5 text-left text-sm ${className}`}
      onClick={() => { setActive(Math.max(0, choices.findIndex(choice => choice.value === value))); setOpen(!open) }}
      onKeyDown={event => {
        if (event.key === 'Escape') { event.preventDefault(); setOpen(false) }
        else if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
          event.preventDefault()
          const index = open ? active : Math.max(0, choices.findIndex(choice => choice.value === value))
          setActive((index + (event.key === 'ArrowDown' ? 1 : choices.length - 1)) % choices.length)
          setOpen(true)
        } else if (event.key === 'Home' || event.key === 'End') {
          event.preventDefault(); setActive(event.key === 'Home' ? 0 : choices.length - 1); setOpen(true)
        } else if ((event.key === 'Enter' || event.key === ' ') && open) {
          event.preventDefault(); choose(active)
        } else if (event.key.length === 1 && event.key !== ' ') {
          const index = choices.findIndex(choice => choice.label.toLowerCase().startsWith(event.key.toLowerCase()))
          if (index >= 0) { event.preventDefault(); setActive(index); setOpen(true) }
        }
      }}>
      {selected.user ? <UserIdentity user={selected.user} /> : selected.label}
      <ChevronDown className="h-4 w-4 shrink-0" />
    </button>
    {open && <div ref={list} id={`${id}-list`} role="listbox" aria-label={label} className="absolute z-50 mt-1 max-h-64 w-full min-w-48 overflow-auto rounded-md border border-border bg-card p-1 shadow-elegant">
      {choices.map((choice, index) => <button type="button" role="option" id={`${id}-${index}`} key={choice.value}
        aria-selected={choice.value === value} tabIndex={-1}
        className={`block w-full rounded px-2 py-1.5 text-left text-sm ${index === active ? 'bg-primary/10 text-primary' : 'hover:bg-accent'}`}
        onMouseEnter={() => setActive(index)} onClick={() => choose(index)}>
        {choice.user ? <UserIdentity user={choice.user} /> : choice.label}
      </button>)}
    </div>}
  </div>
}
