import './editor-styles.css'
import { useEditor, EditorContent } from '@tiptap/react'
import { BubbleMenu } from '@tiptap/react/menus'
import StarterKit from '@tiptap/starter-kit'
import Placeholder from '@tiptap/extension-placeholder'
import LinkExtension from '@tiptap/extension-link'
import Image from '@tiptap/extension-image'
import { Table, TableRow, TableHeader, TableCell } from '@tiptap/extension-table'
import TextAlign from '@tiptap/extension-text-align'
import Underline from '@tiptap/extension-underline'
import Highlight from '@tiptap/extension-highlight'
import { Color, TextStyle } from '@tiptap/extension-text-style'
import CodeBlockLowlight from '@tiptap/extension-code-block-lowlight'
import TaskList from '@tiptap/extension-task-list'
import TaskItem from '@tiptap/extension-task-item'
import Typography from '@tiptap/extension-typography'
import Superscript from '@tiptap/extension-superscript'
import Subscript from '@tiptap/extension-subscript'
import { common, createLowlight } from 'lowlight'
import { useCallback, useEffect } from 'react'
import DocEditorToolbar from './DocEditorToolbar'

const lowlight = createLowlight(common)

interface DocEditorProps {
  content?: Record<string, unknown> | null
  onChange?: (json: Record<string, unknown>, html: string) => void
  placeholder?: string
  editable?: boolean
  className?: string
  minHeight?: string
}

export default function DocEditor({
  content,
  onChange,
  placeholder = 'Start writing... Use / for commands',
  editable = true,
  className = '',
  minHeight = 'min-h-[500px]',
}: DocEditorProps) {
  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        codeBlock: false,
        heading: { levels: [1, 2, 3, 4, 5, 6] },
      }),
      Placeholder.configure({ placeholder }),
      LinkExtension.configure({
        openOnClick: false,
        HTMLAttributes: { class: 'text-primary underline cursor-pointer' },
      }),
      Image.configure({ inline: false, allowBase64: true }),
      Table.configure({ resizable: true }),
      TableRow,
      TableHeader,
      TableCell,
      TextAlign.configure({ types: ['heading', 'paragraph'] }),
      Underline,
      Highlight.configure({ multicolor: true }),
      Color,
      TextStyle,
      CodeBlockLowlight.configure({ lowlight }),
      TaskList,
      TaskItem.configure({ nested: true }),
      Typography,
      Superscript,
      Subscript,
    ],
    content: content as Record<string, unknown> | undefined,
    editable,
    onUpdate: ({ editor: e }) => {
      onChange?.(e.getJSON() as Record<string, unknown>, e.getHTML())
    },
    editorProps: {
      attributes: {
        class: `prose prose-sm dark:prose-invert max-w-none focus:outline-none ${minHeight} px-6 py-4`,
      },
    },
  })

  useEffect(() => {
    if (editor && content && !editor.isFocused) {
      const currentJson = JSON.stringify(editor.getJSON())
      const newJson = JSON.stringify(content)
      if (currentJson !== newJson) {
        editor.commands.setContent(content as Record<string, unknown>)
      }
    }
  }, [content, editor])

  useEffect(() => {
    editor?.setEditable(editable)
  }, [editable, editor])

  const addLink = useCallback(() => {
    if (!editor) return
    const previousUrl = editor.getAttributes('link').href
    const url = window.prompt('URL', previousUrl)
    if (url === null) return
    if (url === '') {
      editor.chain().focus().extendMarkRange('link').unsetLink().run()
      return
    }
    editor.chain().focus().extendMarkRange('link').setLink({ href: url }).run()
  }, [editor])

  const addImage = useCallback(() => {
    if (!editor) return
    const url = window.prompt('Image URL')
    if (url) {
      editor.chain().focus().setImage({ src: url }).run()
    }
  }, [editor])

  const addTable = useCallback(() => {
    editor?.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run()
  }, [editor])

  if (!editor) return null

  return (
    <div className={`border border-border rounded-lg overflow-hidden bg-background ${className}`}>
      {editable && (
        <DocEditorToolbar
          editor={editor}
          onAddLink={addLink}
          onAddImage={addImage}
          onAddTable={addTable}
        />
      )}

      {editable && editor && (
        <BubbleMenu editor={editor} className="bg-card border border-border rounded-lg shadow-elegant flex items-center gap-0.5 p-1">
          <BubbleButton
            active={editor.isActive('bold')}
            onClick={() => editor.chain().focus().toggleBold().run()}
            label="B"
            className="font-bold"
          />
          <BubbleButton
            active={editor.isActive('italic')}
            onClick={() => editor.chain().focus().toggleItalic().run()}
            label="I"
            className="italic"
          />
          <BubbleButton
            active={editor.isActive('underline')}
            onClick={() => editor.chain().focus().toggleUnderline().run()}
            label="U"
            className="underline"
          />
          <BubbleButton
            active={editor.isActive('highlight')}
            onClick={() => editor.chain().focus().toggleHighlight().run()}
            label="H"
            className="bg-yellow-200/50 dark:bg-yellow-500/20 px-1 rounded"
          />
          <BubbleButton
            active={editor.isActive('link')}
            onClick={addLink}
            label="🔗"
          />
        </BubbleMenu>
      )}

      <EditorContent editor={editor} />
    </div>
  )
}

function BubbleButton({
  active,
  onClick,
  label,
  className = '',
}: {
  active: boolean
  onClick: () => void
  label: string
  className?: string
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`px-2 py-1 rounded text-xs transition-colors ${
        active
          ? 'bg-primary/20 text-primary'
          : 'text-foreground hover:bg-accent'
      } ${className}`}
    >
      {label}
    </button>
  )
}
