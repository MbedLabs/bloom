import type { Editor } from '@tiptap/react'
import { List, ListTree } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'

import {
  activeHeadingAt,
  extractHeadings,
  headingElement,
  sameHeadings,
  scrollParentOf,
  slugify,
  type HeadingItem,
} from './outlineNavigation'

interface OutlineSidebarProps {
  editor: Editor | null
  open: boolean
  onToggle: () => void
}

export default function OutlineSidebar({ editor, open, onToggle }: OutlineSidebarProps) {
  const [headings, setHeadings] = useState<HeadingItem[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)

  const navRef = useRef<HTMLElement | null>(null)

  const updateHeadings = useCallback(() => {
    const next = extractHeadings(editor)
    // Every transaction fires this, including plain cursor moves. Replacing the
    // array each time re-rendered the outline - and re-subscribed the listeners
    // below - on every keystroke, which is what made it stutter.
    setHeadings((current) => (sameHeadings(current, next) ? current : next))
  }, [editor])

  useEffect(() => {
    updateHeadings()
    editor?.on('update', updateHeadings)
    editor?.on('transaction', updateHeadings)
    return () => {
      editor?.off('update', updateHeadings)
      editor?.off('transaction', updateHeadings)
    }
  }, [editor, updateHeadings])

  useEffect(() => {
    if (!editor) return
    const handleSelectionUpdate = () => {
      const { from } = editor.state.selection
      let closest: HeadingItem | null = null
      for (const h of headings) {
        if (h.pos <= from) {
          closest = h
        } else {
          break
        }
      }
      setActiveId(closest?.id ?? null)
    }
    editor.on('selectionUpdate', handleSelectionUpdate)
    return () => {
      editor.off('selectionUpdate', handleSelectionUpdate)
    }
  }, [editor, headings])

  // Reading is scrolling, not typing. Without this the highlight only moved
  // when the cursor did, so scrolling through a document left the outline
  // pointing at wherever the caret happened to be.
  useEffect(() => {
    if (!editor || !open || headings.length === 0) return
    const container = scrollParentOf(editor.view.dom)
    const target: HTMLElement | Window = container ?? window

    let queued = false
    const onScroll = () => {
      if (queued) return
      queued = true
      requestAnimationFrame(() => {
        queued = false
        const viewportTop = container ? container.getBoundingClientRect().top : 0
        setActiveId(activeHeadingAt(editor, headings, viewportTop))
      })
    }

    onScroll()
    target.addEventListener('scroll', onScroll, { passive: true })
    return () => target.removeEventListener('scroll', onScroll)
  }, [editor, headings, open])

  // Keep the highlighted entry visible in a long outline.
  useEffect(() => {
    if (!activeId) return
    navRef.current
      ?.querySelector(`[data-outline-id="${CSS.escape(activeId)}"]`)
      ?.scrollIntoView({ block: 'nearest' })
  }, [activeId])

  const scrollToHeading = useCallback(
    (heading: HeadingItem) => {
      const el = headingElement(editor, heading.pos)
      if (!el) return
      el.scrollIntoView({ behavior: 'smooth', block: 'start' })
      // +1 puts the cursor inside the heading; `heading.pos` is the position
      // before it, which belongs to the node above.
      editor?.commands.setTextSelection(heading.pos + 1)
    },
    [editor],
  )

  if (!open) {
    return (
      <button
        onClick={onToggle}
        className="p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
        title="Show outline"
      >
        <ListTree className="h-4 w-4" />
      </button>
    )
  }

  return (
    <div className="w-56 border-r border-border bg-card/30 overflow-y-auto themed-scrollbar shrink-0 animate-slide-in-left">
      <div className="flex items-center justify-between px-3 py-2 border-b border-border">
        <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-1.5">
          <List className="h-3 w-3" />
          Outline
        </span>
        <button
          onClick={onToggle}
          className="p-1 rounded text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
          title="Hide outline"
        >
          <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M18 6L6 18" /><path d="M6 6l12 12" />
          </svg>
        </button>
      </div>
      <nav ref={navRef} className="py-2">
        {headings.length === 0 ? (
          <p className="px-3 py-4 text-xs text-muted-foreground/60 italic">
            Add headings to see the outline
          </p>
        ) : (
          headings.map((h) => {
            const indent = (h.level - 1) * 12
            const isActive = h.id === activeId
            return (
              <button
                key={h.id}
                onClick={() => scrollToHeading(h)}
                data-outline-id={h.id}
                data-outline-slug={slugify(h.text)}
                className={`w-full text-left px-3 py-1.5 text-xs transition-colors truncate block ${
                  isActive
                    ? 'bg-primary/10 text-primary font-medium'
                    : 'text-muted-foreground hover:text-foreground hover:bg-accent/50'
                }`}
                style={{ paddingLeft: `${12 + indent}px` }}
                title={h.text}
              >
                <span className="truncate">{h.text}</span>
              </button>
            )
          })
        )}
      </nav>
    </div>
  )
}
