import { forwardRef, useEffect, useImperativeHandle, useState } from 'react'

export interface MentionSuggestion {
  id: number
  label: string
}

export interface MentionListRef {
  onKeyDown: (props: { event: KeyboardEvent }) => boolean
}

interface MentionListProps {
  items: MentionSuggestion[]
  command: (item: MentionSuggestion) => void
}

const MentionList = forwardRef<MentionListRef, MentionListProps>(({ items, command }, ref) => {
  const [selectedIndex, setSelectedIndex] = useState(0)

  useEffect(() => setSelectedIndex(0), [items])

  useImperativeHandle(ref, () => ({
    onKeyDown: ({ event }: { event: KeyboardEvent }) => {
      if (event.key === 'ArrowUp') {
        setSelectedIndex((i) => (i + items.length - 1) % items.length)
        return true
      }
      if (event.key === 'ArrowDown') {
        setSelectedIndex((i) => (i + 1) % items.length)
        return true
      }
      if (event.key === 'Enter') {
        if (items[selectedIndex]) command(items[selectedIndex])
        return true
      }
      return false
    },
  }))

  if (!items.length) {
    return (
      <div className="bg-card border border-border rounded-lg shadow-elegant p-3 text-xs text-muted-foreground">
        No results
      </div>
    )
  }

  return (
    <div className="bg-card border border-border rounded-lg shadow-elegant overflow-hidden min-w-[180px]">
      {items.map((item, index) => (
        <button
          key={item.id}
          onClick={() => command(item)}
          className={`w-full text-left px-3 py-2 text-sm transition-colors ${
            index === selectedIndex
              ? 'bg-primary/10 text-primary'
              : 'text-foreground hover:bg-accent'
          }`}
        >
          <span className="font-medium">@{item.label}</span>
        </button>
      ))}
    </div>
  )
})

MentionList.displayName = 'MentionList'

export default MentionList
