import type { Editor } from '@tiptap/react'
import {
  Bold, Italic, Underline as UnderlineIcon, Strikethrough,
  List, ListOrdered, ListChecks, Quote,
  Code, Minus, Image as ImageIcon, Link2, Table as TableIcon,
  Undo2, Redo2, RemoveFormatting, AlignLeft, AlignCenter,
  AlignRight, Superscript, Subscript, ChevronDown, Palette
} from 'lucide-react'
import { useState, useRef, useEffect } from 'react'

interface DocEditorToolbarProps {
  editor: Editor
  onAddLink: () => void
  onAddImage: () => void
  onAddTable: () => void
}

export default function DocEditorToolbar({ editor, onAddLink, onAddImage, onAddTable }: DocEditorToolbarProps) {
  const [headingOpen, setHeadingOpen] = useState(false)
  const [colorOpen, setColorOpen] = useState(false)
  const headingRef = useRef<HTMLDivElement>(null)
  const colorRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (headingRef.current && !headingRef.current.contains(e.target as Node)) setHeadingOpen(false)
      if (colorRef.current && !colorRef.current.contains(e.target as Node)) setColorOpen(false)
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const currentHeading = (() => {
    for (let i = 1; i <= 6; i++) {
      if (editor.isActive('heading', { level: i })) return `H${i}`
    }
    return 'Paragraph'
  })()

  const colors = [
    '#000000', '#434343', '#666666', '#999999',
    '#E03131', '#E8590C', '#F08C00', '#2F9E44',
    '#1971C2', '#6741D9', '#C2255C', '#0C8599',
  ]

  const highlightColors = [
    { label: 'Yellow', color: '#FFF3BF' },
    { label: 'Green', color: '#D3F9D8' },
    { label: 'Blue', color: '#D0EBFF' },
    { label: 'Pink', color: '#FFE3E3' },
    { label: 'Purple', color: '#E5DBFF' },
    { label: 'Orange', color: '#FFE8CC' },
  ]

  return (
    <div className="sticky top-0 z-10 flex items-center gap-0.5 p-2 border-b border-border bg-card flex-wrap">
      {/* Undo / Redo */}
      <ToolbarButton
        onClick={() => editor.chain().focus().undo().run()}
        disabled={!editor.can().undo()}
        icon={<Undo2 className="h-4 w-4" />}
        title="Undo"
      />
      <ToolbarButton
        onClick={() => editor.chain().focus().redo().run()}
        disabled={!editor.can().redo()}
        icon={<Redo2 className="h-4 w-4" />}
        title="Redo"
      />

      <Separator />

      {/* Text formatting */}
      <ToolbarButton
        onClick={() => editor.chain().focus().toggleBold().run()}
        active={editor.isActive('bold')}
        icon={<Bold className="h-4 w-4" />}
        title="Bold (Ctrl+B)"
      />
      <ToolbarButton
        onClick={() => editor.chain().focus().toggleItalic().run()}
        active={editor.isActive('italic')}
        icon={<Italic className="h-4 w-4" />}
        title="Italic (Ctrl+I)"
      />
      <ToolbarButton
        onClick={() => editor.chain().focus().toggleUnderline().run()}
        active={editor.isActive('underline')}
        icon={<UnderlineIcon className="h-4 w-4" />}
        title="Underline (Ctrl+U)"
      />
      <ToolbarButton
        onClick={() => editor.chain().focus().toggleStrike().run()}
        active={editor.isActive('strike')}
        icon={<Strikethrough className="h-4 w-4" />}
        title="Strikethrough"
      />
      <ToolbarButton
        onClick={() => editor.chain().focus().toggleSuperscript().run()}
        active={editor.isActive('superscript')}
        icon={<Superscript className="h-4 w-4" />}
        title="Superscript"
      />
      <ToolbarButton
        onClick={() => editor.chain().focus().toggleSubscript().run()}
        active={editor.isActive('subscript')}
        icon={<Subscript className="h-4 w-4" />}
        title="Subscript"
      />

      {/* Color picker */}
      <div className="relative" ref={colorRef}>
        <ToolbarButton
          onClick={() => setColorOpen(!colorOpen)}
          icon={<Palette className="h-4 w-4" />}
          title="Text color"
        />
        {colorOpen && (
          <div className="absolute top-full left-0 mt-1 bg-card border border-border rounded-lg shadow-elegant p-3 z-50 w-48">
            <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider mb-2">Text Color</p>
            <div className="grid grid-cols-6 gap-1 mb-3">
              {colors.map((c) => (
                <button
                  key={c}
                  onClick={() => { editor.chain().focus().setColor(c).run(); setColorOpen(false) }}
                  className="w-6 h-6 rounded border border-border hover:scale-110 transition-transform"
                  style={{ backgroundColor: c }}
                  title={c}
                />
              ))}
            </div>
            <button
              onClick={() => { editor.chain().focus().unsetColor().run(); setColorOpen(false) }}
              className="text-xs text-muted-foreground hover:text-foreground"
            >
              Reset color
            </button>
            <div className="h-px bg-border my-2" />
            <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider mb-2">Highlight</p>
            <div className="flex flex-wrap gap-1">
              {highlightColors.map((h) => (
                <button
                  key={h.color}
                  onClick={() => { editor.chain().focus().toggleHighlight({ color: h.color }).run(); setColorOpen(false) }}
                  className="px-2 py-1 rounded text-[10px] font-medium border border-border hover:scale-105 transition-transform"
                  style={{ backgroundColor: h.color }}
                >
                  {h.label}
                </button>
              ))}
            </div>
            <button
              onClick={() => { editor.chain().focus().unsetHighlight().run(); setColorOpen(false) }}
              className="text-xs text-muted-foreground hover:text-foreground mt-2"
            >
              Remove highlight
            </button>
          </div>
        )}
      </div>

      <Separator />

      {/* Heading dropdown */}
      <div className="relative" ref={headingRef}>
        <button
          onClick={() => setHeadingOpen(!headingOpen)}
          className="flex items-center gap-1 px-2 py-1.5 rounded-md text-xs font-medium text-foreground hover:bg-accent transition-colors min-w-[90px]"
        >
          {currentHeading}
          <ChevronDown className="h-3 w-3 text-muted-foreground" />
        </button>
        {headingOpen && (
          <div className="absolute top-full left-0 mt-1 bg-card border border-border rounded-lg shadow-elegant overflow-hidden z-50 min-w-[140px]">
            <HeadingOption
              label="Paragraph"
              active={!editor.isActive('heading')}
              onClick={() => { editor.chain().focus().setParagraph().run(); setHeadingOpen(false) }}
              className="text-sm"
            />
            {([1, 2, 3, 4, 5, 6] as const).map((level) => (
              <HeadingOption
                key={level}
                label={`Heading ${level}`}
                active={editor.isActive('heading', { level })}
                onClick={() => { editor.chain().focus().toggleHeading({ level }).run(); setHeadingOpen(false) }}
                className={level <= 2 ? 'text-lg font-bold' : level <= 4 ? 'text-base font-semibold' : 'text-sm font-medium'}
              />
            ))}
          </div>
        )}
      </div>

      <Separator />

      {/* Lists */}
      <ToolbarButton
        onClick={() => editor.chain().focus().toggleBulletList().run()}
        active={editor.isActive('bulletList')}
        icon={<List className="h-4 w-4" />}
        title="Bullet list"
      />
      <ToolbarButton
        onClick={() => editor.chain().focus().toggleOrderedList().run()}
        active={editor.isActive('orderedList')}
        icon={<ListOrdered className="h-4 w-4" />}
        title="Numbered list"
      />
      <ToolbarButton
        onClick={() => editor.chain().focus().toggleTaskList().run()}
        active={editor.isActive('taskList')}
        icon={<ListChecks className="h-4 w-4" />}
        title="Task list"
      />
      <ToolbarButton
        onClick={() => editor.chain().focus().toggleBlockquote().run()}
        active={editor.isActive('blockquote')}
        icon={<Quote className="h-4 w-4" />}
        title="Blockquote"
      />

      <Separator />

      {/* Alignment */}
      <ToolbarButton
        onClick={() => editor.chain().focus().setTextAlign('left').run()}
        active={editor.isActive({ textAlign: 'left' })}
        icon={<AlignLeft className="h-4 w-4" />}
        title="Align left"
      />
      <ToolbarButton
        onClick={() => editor.chain().focus().setTextAlign('center').run()}
        active={editor.isActive({ textAlign: 'center' })}
        icon={<AlignCenter className="h-4 w-4" />}
        title="Align center"
      />
      <ToolbarButton
        onClick={() => editor.chain().focus().setTextAlign('right').run()}
        active={editor.isActive({ textAlign: 'right' })}
        icon={<AlignRight className="h-4 w-4" />}
        title="Align right"
      />

      <Separator />

      {/* Inserts */}
      <ToolbarButton onClick={onAddTable} icon={<TableIcon className="h-4 w-4" />} title="Insert table" />
      <ToolbarButton
        onClick={() => editor.chain().focus().toggleCodeBlock().run()}
        active={editor.isActive('codeBlock')}
        icon={<Code className="h-4 w-4" />}
        title="Code block"
      />
      <ToolbarButton
        onClick={() => editor.chain().focus().setHorizontalRule().run()}
        icon={<Minus className="h-4 w-4" />}
        title="Horizontal rule"
      />
      <ToolbarButton onClick={onAddImage} icon={<ImageIcon className="h-4 w-4" />} title="Insert image" />
      <ToolbarButton
        onClick={onAddLink}
        active={editor.isActive('link')}
        icon={<Link2 className="h-4 w-4" />}
        title="Insert link"
      />

      <Separator />

      <ToolbarButton
        onClick={() => editor.chain().focus().clearNodes().unsetAllMarks().run()}
        icon={<RemoveFormatting className="h-4 w-4" />}
        title="Clear formatting"
      />

      {/* Table controls (show only when inside a table) */}
      {editor.isActive('table') && (
        <>
          <Separator />
          <div className="flex items-center gap-0.5">
            <SmallButton onClick={() => editor.chain().focus().addColumnBefore().run()} label="+Col←" />
            <SmallButton onClick={() => editor.chain().focus().addColumnAfter().run()} label="+Col→" />
            <SmallButton onClick={() => editor.chain().focus().addRowBefore().run()} label="+Row↑" />
            <SmallButton onClick={() => editor.chain().focus().addRowAfter().run()} label="+Row↓" />
            <SmallButton onClick={() => editor.chain().focus().deleteColumn().run()} label="−Col" className="text-red-500" />
            <SmallButton onClick={() => editor.chain().focus().deleteRow().run()} label="−Row" className="text-red-500" />
            <SmallButton onClick={() => editor.chain().focus().mergeCells().run()} label="Merge" />
            <SmallButton onClick={() => editor.chain().focus().splitCell().run()} label="Split" />
            <SmallButton onClick={() => editor.chain().focus().toggleHeaderRow().run()} label="Header" />
            <SmallButton onClick={() => editor.chain().focus().deleteTable().run()} label="Del Table" className="text-red-500" />
          </div>
        </>
      )}
    </div>
  )
}

function ToolbarButton({
  onClick,
  active = false,
  disabled = false,
  icon,
  title,
}: {
  onClick: () => void
  active?: boolean
  disabled?: boolean
  icon: React.ReactNode
  title: string
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={`p-1.5 rounded-md transition-colors ${
        active
          ? 'bg-primary/15 text-primary'
          : disabled
            ? 'text-muted-foreground/30 cursor-not-allowed'
            : 'text-muted-foreground hover:text-foreground hover:bg-accent'
      }`}
      title={title}
    >
      {icon}
    </button>
  )
}

function SmallButton({ onClick, label, className = '' }: { onClick: () => void; label: string; className?: string }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`px-1.5 py-0.5 rounded text-[10px] font-medium hover:bg-accent transition-colors ${className || 'text-muted-foreground hover:text-foreground'}`}
    >
      {label}
    </button>
  )
}

function Separator() {
  return <div className="w-px h-5 bg-border mx-1" />
}

function HeadingOption({
  label,
  active,
  onClick,
  className = '',
}: {
  label: string
  active: boolean
  onClick: () => void
  className?: string
}) {
  return (
    <button
      onClick={onClick}
      className={`w-full text-left px-3 py-2 transition-colors ${
        active ? 'bg-primary/10 text-primary' : 'text-foreground hover:bg-accent'
      } ${className}`}
    >
      {label}
    </button>
  )
}
