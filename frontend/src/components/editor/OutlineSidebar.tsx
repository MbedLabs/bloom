import type { Editor } from '@tiptap/react'
import { List, ListTree } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'

interface HeadingItem {
  id: string
  level: number
  text: string
  pos: number
}

interface OutlineSidebarProps {
  editor: Editor | null
  open: boolean
  onToggle: () => void
}

function extractHeadings(editor: Editor | null): HeadingItem[] {
  if (!editor) return []
  const headings: HeadingItem[] = []
  editor.state.doc.descendants((node, pos) => {
    if (node.type.name.startsWith('heading')) {
      const text = node.textContent || 'Untitled'
      headings.push({
        id: `heading-${pos}`,
        level: parseInt(node.attrs.level, 10),
        text,
        pos,
      })
    }
  })
  return headings
}

function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^\w\s-]/g, '')
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-')
    .trim()
}

export default function OutlineSidebar({ editor, open, onToggle }: OutlineSidebarProps) {
  const [headings, setHeadings] = useState<HeadingItem[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)

  const updateHeadings = useCallback(() => {
    setHeadings(extractHeadings(editor))
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

  const scrollToHeading = useCallback(
    (heading: HeadingItem) => {
      if (!editor) return
      const dom = editor.view.domAtPos(heading.pos)
      const el = dom.node instanceof HTMLElement ? dom.node : dom.node.parentElement
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'start' })
        editor.commands.setTextSelection(heading.pos)
      }
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
    <div className="w-56 border-r border-border bg-card/30 overflow-y-auto shrink-0 animate-slide-in-left">
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
      <nav className="py-2">
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
