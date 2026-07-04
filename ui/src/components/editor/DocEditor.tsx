import './editor-styles.css'
import { useRef, useCallback, useEffect } from 'react'
import { useEditor, EditorContent } from '@tiptap/react'
import { BubbleMenu } from '@tiptap/react/menus'
import { ReactRenderer } from '@tiptap/react'
import Mention from '@tiptap/extension-mention'
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
import { LineHeight } from './LineHeight'
import DocEditorToolbar from './DocEditorToolbar'
import OutlineSidebar from './OutlineSidebar'
import MentionList, { type MentionListRef, type MentionSuggestion } from './MentionList'

const lowlight = createLowlight(common)
const PARAMETER_MENTION_TRIGGER = '{{'
const PARAMETER_MENTION_SUFFIX = '}}'

interface DocEditorProps {
  content?: Record<string, unknown> | null
  onChange?: (json: Record<string, unknown>, html: string) => void
  placeholder?: string
  editable?: boolean
  className?: string
  minHeight?: string
  headingNumbered?: boolean
  onHeadingNumberedChange?: (numbered: boolean) => void
  showOutline?: boolean
  onOutlineToggle?: (open: boolean) => void
  mentionItems?: MentionSuggestion[]
  userMentionItems?: MentionSuggestion[]
}

export default function DocEditor({
  content,
  onChange,
  placeholder = 'Start writing... Use / for commands',
  editable = true,
  className = '',
  minHeight = 'min-h-[500px]',
  headingNumbered = true,
  onHeadingNumberedChange,
  showOutline = false,
  onOutlineToggle,
  mentionItems = [],
  userMentionItems = [],
}: DocEditorProps) {
  const mentionItemsRef = useRef(mentionItems)
  const userMentionItemsRef = useRef(userMentionItems)

  useEffect(() => {
    mentionItemsRef.current = mentionItems
  }, [mentionItems])

  useEffect(() => {
    userMentionItemsRef.current = userMentionItems
  }, [userMentionItems])

  const renderParameterMentionList = useCallback(() => {
    let component: ReactRenderer<MentionListRef> | null = null
    let popup: HTMLDivElement | null = null

    const destroy = () => {
      component?.destroy()
      component = null
      popup?.remove()
      popup = null
    }

    const position = (clientRect: (() => DOMRect | null) | null | undefined) => {
      if (!popup || !clientRect) return
      const rect = clientRect()
      if (!rect) return
      popup.style.left = `${rect.left}px`
      popup.style.top = `${rect.bottom + 8}px`
    }

    return {
      onStart: (props: { editor: typeof editor; items: MentionSuggestion[]; command: (item: MentionSuggestion) => void; clientRect?: (() => DOMRect | null) | null }) => {
        component = new ReactRenderer(MentionList, {
          editor: props.editor,
          props: {
            items: props.items,
            command: props.command,
            triggerPrefix: PARAMETER_MENTION_TRIGGER,
            triggerSuffix: PARAMETER_MENTION_SUFFIX,
          },
          as: 'div',
          className: 'mention-suggestion-popover',
        })

        popup = document.createElement('div')
        popup.style.position = 'fixed'
        popup.style.zIndex = '50'
        popup.appendChild(component.element)
        document.body.appendChild(popup)
        position(props.clientRect)
      },
      onUpdate: (props: { items: MentionSuggestion[]; command: (item: MentionSuggestion) => void; clientRect?: (() => DOMRect | null) | null }) => {
        component?.updateProps({
          items: props.items,
          command: props.command,
          triggerPrefix: PARAMETER_MENTION_TRIGGER,
          triggerSuffix: PARAMETER_MENTION_SUFFIX,
        })
        position(props.clientRect)
      },
      onKeyDown: (props: { event: KeyboardEvent }) => component?.ref?.onKeyDown(props) ?? false,
      onExit: destroy,
    }
  }, [])

  const renderUserMentionList = useCallback(() => {
    let component: ReactRenderer<MentionListRef> | null = null
    let popup: HTMLDivElement | null = null

    const destroy = () => {
      component?.destroy()
      component = null
      popup?.remove()
      popup = null
    }

    const position = (clientRect: (() => DOMRect | null) | null | undefined) => {
      if (!popup || !clientRect) return
      const rect = clientRect()
      if (!rect) return
      popup.style.left = `${rect.left}px`
      popup.style.top = `${rect.bottom + 8}px`
    }

    return {
      onStart: (props: { editor: typeof editor; items: MentionSuggestion[]; command: (item: MentionSuggestion) => void; clientRect?: (() => DOMRect | null) | null }) => {
        component = new ReactRenderer(MentionList, {
          editor: props.editor,
          props: {
            items: props.items,
            command: props.command,
            triggerPrefix: '@',
            triggerSuffix: '',
          },
          as: 'div',
          className: 'mention-suggestion-popover',
        })

        popup = document.createElement('div')
        popup.style.position = 'fixed'
        popup.style.zIndex = '50'
        popup.appendChild(component.element)
        document.body.appendChild(popup)
        position(props.clientRect)
      },
      onUpdate: (props: { items: MentionSuggestion[]; command: (item: MentionSuggestion) => void; clientRect?: (() => DOMRect | null) | null }) => {
        component?.updateProps({
          items: props.items,
          command: props.command,
          triggerPrefix: '@',
          triggerSuffix: '',
        })
        position(props.clientRect)
      },
      onKeyDown: (props: { event: KeyboardEvent }) => component?.ref?.onKeyDown(props) ?? false,
      onExit: destroy,
    }
  }, [])

  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        codeBlock: false,
        heading: { levels: [1, 2, 3, 4, 5, 6] },
      }),
      Mention.configure({
        HTMLAttributes: { class: 'mention' },
        renderText: ({ node }) => node.attrs.mentionSuggestionChar === '@'
          ? `@${String(node.attrs.label ?? node.attrs.id)}`
          : `{{${String(node.attrs.label ?? node.attrs.id)}}}`,
        renderHTML: ({ node }) => [
          'span',
          { 'data-type': 'mention', class: node.attrs.mentionSuggestionChar === '@' ? 'mention-user text-blue-500 font-medium' : 'mention' },
          node.attrs.mentionSuggestionChar === '@' ? `@${String(node.attrs.label ?? node.attrs.id)}` : `{{${String(node.attrs.label ?? node.attrs.id)}}}`
        ],
        suggestions: [
          {
            char: PARAMETER_MENTION_TRIGGER,
            allowedPrefixes: null,
            items: ({ query }) => {
              console.log('{{ trigger called! mentionItemsRef.current:', mentionItemsRef.current);
              return mentionItemsRef.current.filter((item) => {
                const normalizedQuery = query.trim().toLowerCase()
                if (!normalizedQuery) return true
                return item.label.toLowerCase().includes(normalizedQuery)
              })
            },
            command: ({ editor: mentionEditor, range, props }) => {
              mentionEditor.chain().focus().insertContentAt(range, {
                type: 'mention',
                attrs: {
                  id: String(props.id),
                  label: props.label,
                  mentionSuggestionChar: PARAMETER_MENTION_TRIGGER,
                },
              }).run()
            },
            render: renderParameterMentionList,
          },
          {
            char: '@',
            allowedPrefixes: null,
            items: ({ query }) => userMentionItemsRef.current.filter((item) => {
              const normalizedQuery = query.trim().toLowerCase()
              if (!normalizedQuery) return true
              return item.label.toLowerCase().includes(normalizedQuery)
            }),
            command: ({ editor: mentionEditor, range, props }) => {
              mentionEditor.chain().focus().insertContentAt(range, {
                type: 'mention',
                attrs: {
                  id: String(props.id),
                  label: props.label,
                  mentionSuggestionChar: '@',
                },
              }).run()
            },
            render: renderUserMentionList,
          },
        ],
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
      LineHeight,
    ],
    content: content as Record<string, unknown> | undefined,
    editable,
    onUpdate: ({ editor: e }) => {
      onChange?.(e.getJSON() as Record<string, unknown>, e.getHTML())
    },
    editorProps: {
      attributes: {
        class: `prose prose-sm dark:prose-invert max-w-none focus:outline-none ${minHeight} px-6 pt-4 ${headingNumbered ? 'heading-numbered' : ''}`,
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
    <div className="flex flex-1">
      <OutlineSidebar
        editor={editor}
        open={showOutline}
        onToggle={() => onOutlineToggle?.(!showOutline)}
      />
      <div className={`flex-1 flex flex-col border border-border rounded-lg bg-background min-h-0 ${className}`}>
        {editable && (
          <DocEditorToolbar
            editor={editor}
            onAddLink={addLink}
            onAddImage={addImage}
            onAddTable={addTable}
            headingNumbered={headingNumbered}
            onHeadingNumberedChange={onHeadingNumberedChange}
            onOutlineToggle={() => onOutlineToggle?.(!showOutline)}
            outlineOpen={showOutline}
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
              label="\u{1F517}"
            />
          </BubbleMenu>
        )}

        <div className="flex-1 flex flex-col">
          <EditorContent editor={editor} />
        </div>
      </div>
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
