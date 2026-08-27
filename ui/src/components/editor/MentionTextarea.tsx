import { useCallback, useLayoutEffect, useRef, useState } from 'react'
import type { TextareaHTMLAttributes } from 'react'

import MentionList, { type MentionListRef, type MentionSuggestion } from './MentionList'

const PARAMETER_TRIGGER = '{{'
const PARAMETER_SUFFIX = '}}'

/**
 * A plain <textarea> that offers the same two mention triggers as DocEditor.
 *
 * The TCS table stores `description` and `expected_result` as plain strings -
 * the Bud runner and the exporters read them as text - so a mention here has to
 * serialize to text, not to a ProseMirror node. It writes exactly what
 * DocEditor's `renderText` produces (`{{KEY}}` and `@Name`) so a parameter
 * written in a test case is addressed the same way as one written in a
 * requirement.
 */

type TriggerKind = 'parameter' | 'user'

interface ActiveTrigger {
  kind: TriggerKind
  /** Index in the value where the trigger token starts (at `{` or `@`). */
  start: number
  query: string
}

export interface MentionTextareaProps
  extends Omit<TextareaHTMLAttributes<HTMLTextAreaElement>, 'value' | 'onChange'> {
  value: string
  onChange: (value: string) => void
  mentionItems?: MentionSuggestion[]
  userMentionItems?: MentionSuggestion[]
}

/**
 * Which trigger, if any, the caret is currently sitting inside.
 *
 * `{{` is tested first: `{` is excluded from the `@` token charset, so the two
 * patterns cannot both match, but ordering keeps that independent of the
 * charsets drifting later.
 */
function detectTrigger(textBeforeCaret: string): ActiveTrigger | null {
  const parameter = /\{\{([^{}\n]*)$/.exec(textBeforeCaret)
  if (parameter) {
    return { kind: 'parameter', start: parameter.index, query: parameter[1] }
  }
  const user = /@([^\s@{}]*)$/.exec(textBeforeCaret)
  if (user) {
    return { kind: 'user', start: user.index, query: user[1] }
  }
  return null
}

/** The same filter DocEditor applies, so both surfaces offer the same list. */
function filterSuggestions(items: MentionSuggestion[], query: string): MentionSuggestion[] {
  const normalizedQuery = query.trim().toLowerCase()
  if (!normalizedQuery) return items
  return items.filter((item) => item.label.toLowerCase().includes(normalizedQuery))
}

export default function MentionTextarea({
  value,
  onChange,
  mentionItems = [],
  userMentionItems = [],
  onKeyDown,
  onBlur,
  ...textareaProps
}: MentionTextareaProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const listRef = useRef<MentionListRef>(null)
  const [trigger, setTrigger] = useState<ActiveTrigger | null>(null)
  const [anchor, setAnchor] = useState<{ left: number; top: number } | null>(null)

  const items = trigger
    ? filterSuggestions(trigger.kind === 'parameter' ? mentionItems : userMentionItems, trigger.query)
    : []

  const close = useCallback(() => {
    setTrigger(null)
    setAnchor(null)
  }, [])

  const syncTrigger = useCallback((element: HTMLTextAreaElement) => {
    // A selection is not a caret; offering a mention there would replace text
    // the user deliberately highlighted.
    if (element.selectionStart !== element.selectionEnd) {
      close()
      return
    }
    const next = detectTrigger(element.value.slice(0, element.selectionStart))
    setTrigger(next)
    if (!next) setAnchor(null)
  }, [close])

  useLayoutEffect(() => {
    if (!trigger) return
    const element = textareaRef.current
    if (!element) return
    // Anchored to the field rather than the caret: a caret-accurate position in
    // a textarea needs a mirrored div, which is not worth it for a table cell.
    const rect = element.getBoundingClientRect()
    setAnchor({ left: rect.left, top: rect.bottom + 4 })
  }, [trigger])

  const insert = useCallback((item: MentionSuggestion) => {
    const element = textareaRef.current
    if (!element || !trigger) return
    const caret = element.selectionStart
    const replacement = trigger.kind === 'parameter'
      ? `${PARAMETER_TRIGGER}${item.label}${PARAMETER_SUFFIX}`
      : `@${item.label}`
    const next = `${value.slice(0, trigger.start)}${replacement}${value.slice(caret)}`
    onChange(next)
    close()
    const caretAfter = trigger.start + replacement.length
    // The value lands on the next render, so move the caret after it.
    requestAnimationFrame(() => {
      const target = textareaRef.current
      if (!target) return
      target.focus()
      target.setSelectionRange(caretAfter, caretAfter)
    })
  }, [close, onChange, trigger, value])

  const handleKeyDown = useCallback((event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (trigger) {
      if (event.key === 'Escape') {
        event.preventDefault()
        close()
        return
      }
      // Only hand navigation keys to the list when it has something to select.
      // Swallowing Enter on an empty list would stop the textarea from ever
      // taking a newline while a stray `@` sits behind the caret.
      if (items.length > 0 && ['ArrowUp', 'ArrowDown', 'Enter'].includes(event.key)) {
        if (listRef.current?.onKeyDown({ event: event.nativeEvent })) {
          event.preventDefault()
          return
        }
      }
    }
    onKeyDown?.(event)
  }, [close, items.length, onKeyDown, trigger])

  return (
    <>
      <textarea
        {...textareaProps}
        ref={textareaRef}
        value={value}
        onChange={(event) => {
          onChange(event.target.value)
          syncTrigger(event.target)
        }}
        onSelect={(event) => syncTrigger(event.currentTarget)}
        onKeyDown={handleKeyDown}
        onBlur={(event) => {
          // Let a click on the popover land before it is torn down.
          window.setTimeout(close, 150)
          onBlur?.(event)
        }}
      />
      {trigger && anchor && (
        <div
          className="mention-suggestion-popover fixed z-[120]"
          style={{ left: anchor.left, top: anchor.top }}
        >
          <MentionList
            ref={listRef}
            items={items}
            command={insert}
            triggerPrefix={trigger.kind === 'parameter' ? PARAMETER_TRIGGER : '@'}
            triggerSuffix={trigger.kind === 'parameter' ? PARAMETER_SUFFIX : ''}
          />
        </div>
      )}
    </>
  )
}
