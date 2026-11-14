// @vitest-environment jsdom
import { QueryClientProvider } from '@tanstack/react-query'
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import type { ComponentProps } from 'react'
import { MemoryRouter } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { ArtefactComment, CommentAnchor } from '../api/client'
import { ToastProvider } from '../components/Toast'
import type DocEditorComponent from '../components/editor/DocEditor'
import { createQueryClient } from '../lib/queryClient'
import { resetApiMocks, user, workflowFixture } from './apiFixtures'
import { settle } from './settle'

type EditorProps = ComponentProps<typeof DocEditorComponent>

const PASSAGE_TEXT = 'The brake shall engage when the pedal is pressed.'
const NOW = '2026-10-26T10:00:00Z'

let currentUser: Record<string, unknown> = user
let editorProps: EditorProps | null = null

vi.mock('../api/client', async importOriginal => {
  const { mockApiModule } = await import('./apiFixtures')
  return mockApiModule(await importOriginal<Record<string, unknown>>(), vi)
})

vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({ user: currentUser, isLoading: false, isAuthenticated: true }),
}))

vi.mock('../components/editor/DocEditor', () => ({
  default: (props: EditorProps) => {
    editorProps = props
    return <p data-testid="doc-text">
      {(props.commentThreads ?? []).filter(thread => PASSAGE_TEXT.includes(thread.anchor.exact)).map(thread => <span
        key={thread.id}
        data-comment-id={thread.id}
        className={thread.selected ? 'comment-highlight comment-highlight-selected' : 'comment-highlight'}
        onClick={() => props.onThreadClick?.(thread.id)}
      >{thread.anchor.exact}</span>)}
    </p>
  },
}))

const client = await import('../api/client')
const { CommentableDocEditor, CommentsColumn, OpenThreads, ReviewCommentsProvider, ThreadList } = await import('../components/comments/ReviewComments')
const { default: DocDetailShell } = await import('../components/DocDetailShell')

const brake: CommentAnchor = { exact: 'brake', prefix: 'The ', suffix: ' shall engage' }

/** A comment on the requirement under review. */
function comment(fields: Partial<ArtefactComment> & { id: number; body: string }): ArtefactComment {
  return { artefact_type: 'requirement', artefact_id: 11, author_user_id: 2, author_name: 'Grace Hopper', created_at: NOW, parent_id: null, anchor: null, resolved_at: null, resolved_by: null, replies: [], ...fields }
}

const passageThread = comment({
  id: 1,
  body: 'Which brake?',
  anchor: brake,
  replies: [comment({ id: 3, parent_id: 1, author_user_id: 1, author_name: 'Ada Lovelace', body: 'The front one.' })],
})
const generalThread = comment({ id: 2, body: 'General remark' })
const resolvedThread = comment({ id: 4, body: 'Fixed the typo', anchor: { exact: 'pedal', prefix: 'the ', suffix: ' is' }, resolved_at: NOW, resolved_by: { id: 1, full_name: 'Ada Lovelace' } })
const detachedThread = comment({ id: 5, body: 'Gone passage', anchor: { exact: 'accelerator', prefix: 'the ', suffix: '.' } })
const threads = [passageThread, generalThread, resolvedThread, detachedThread]

/** Allow or deny commenting on a controlled document whose people are the signed-in user. */
function allowComment(comment: boolean) {
  vi.mocked(client.workflowApi.get).mockResolvedValue({ ...workflowFixture, actions: { ...workflowFixture.actions, comment } })
}

/** Render a document text and its comments column, as a detail page does. */
function renderReview({ column = true, content = { type: 'doc' } }: { column?: boolean; content?: Record<string, unknown> } = {}) {
  const queryClient = createQueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 }, mutations: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <MemoryRouter>
          <ReviewCommentsProvider artefactType="requirement" artefactId={11}>
            <div data-testid="text"><CommentableDocEditor content={content} editable={false} /></div>
            {column && <CommentsColumn />}
          </ReviewCommentsProvider>
        </MemoryRouter>
      </ToastProvider>
    </QueryClientProvider>,
  )
}

/** Render the discussion list of a side panel. */
function renderThreadList() {
  const queryClient = createQueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 }, mutations: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <MemoryRouter>
          <ThreadList artefactType="test-suite" artefactId={41} />
        </MemoryRouter>
      </ToastProvider>
    </QueryClientProvider>,
  )
}

/** Wait until the threads and the workflow have loaded. */
async function loaded() {
  await waitFor(() => expect(client.workflowApi.get).toHaveBeenCalled())
  await waitFor(() => expect(editorProps?.commentThreads?.length).toBeGreaterThan(0))
  await settle()
}

/** Report a text selection of the passage "brake" from the text. */
function selectBrake() {
  act(() => editorProps!.onCommentSelection!({ anchor: brake, rect: new DOMRect(40, 100, 50, 18) }))
}

/** The thread card that holds a comment body. */
function threadCard(body: string) {
  return screen.getByText(body).closest('section')!
}

/** Make the window report whether it is at least 1024 pixels wide. */
function setWide(wide: boolean) {
  window.matchMedia = ((query: string) => ({
    matches: wide,
    media: query,
    addEventListener: () => undefined,
    removeEventListener: () => undefined,
  })) as unknown as typeof window.matchMedia
}

/** Make the window the given number of pixels wide for every min-width query. */
function setWindowWidth(width: number) {
  window.matchMedia = ((query: string) => ({
    matches: width >= Number(/min-width:\s*(\d+)px/.exec(query)?.[1] ?? 0),
    media: query,
    addEventListener: () => undefined,
    removeEventListener: () => undefined,
  })) as unknown as typeof window.matchMedia
}

/** The general comment box of the comments column, opened. */
function generalBox() {
  const column = screen.getByRole('region', { name: 'Document comments' })
  fireEvent.click(within(column).getByRole('button', { name: 'Add a general comment' }))
  return within(column).getByRole('textbox', { name: 'Comment' }) as HTMLTextAreaElement
}

beforeEach(() => {
  setWide(true)
  vi.clearAllMocks()
  resetApiMocks(client as unknown as Record<string, unknown>, vi)
  currentUser = user
  editorProps = null
  allowComment(true)
  vi.mocked(client.artefactsApi.listComments).mockResolvedValue(threads)
  Element.prototype.scrollIntoView = vi.fn()
})

afterEach(() => {
  cleanup()
})

describe('commenting on a selected passage', () => {
  it('shows the Comment button on a selection when the viewer may comment', async () => {
    renderReview({ column: false })
    await loaded()
    const text = screen.getByTestId('text')
    expect(within(text).queryByRole('button', { name: 'Comment' })).toBeNull()
    selectBrake()
    expect(within(text).getByRole('button', { name: 'Comment' })).toBeTruthy()
    act(() => editorProps!.onCommentSelection!(null))
    expect(within(text).queryByRole('button', { name: 'Comment' })).toBeNull()
  })

  it('shows no Comment button on a selection without actions.comment', async () => {
    allowComment(false)
    renderReview({ column: false })
    await loaded()
    selectBrake()
    expect(within(screen.getByTestId('text')).queryByRole('button', { name: 'Comment' })).toBeNull()
  })

  it('posts a passage comment with its anchor and closes the composer', async () => {
    renderReview()
    await loaded()
    selectBrake()
    fireEvent.click(within(screen.getByTestId('text')).getByRole('button', { name: 'Comment' }))
    const box = await screen.findByRole('textbox', { name: 'Comment on the selected passage' })
    const composer = box.closest('div.absolute') as HTMLElement
    expect(within(composer).getByText('brake').tagName).toBe('BLOCKQUOTE')
    expect(within(screen.getByTestId('text')).queryByRole('button', { name: 'Comment' })).toBeNull()
    fireEvent.change(box, { target: { value: 'Name the brake.' } })
    fireEvent.click(within(composer).getByRole('button', { name: 'Comment' }))
    await waitFor(() => expect(client.artefactsApi.createComment).toHaveBeenCalledWith('requirement', 11, 'Name the brake.', { parentId: undefined, anchor: brake }))
    await waitFor(() => expect(screen.queryByRole('textbox', { name: 'Comment on the selected passage' })).toBeNull())
    expect(within(screen.getByTestId('text')).queryByRole('button', { name: 'Comment' })).toBeNull()
  })

  it('closes the composer on Cancel without posting', async () => {
    renderReview()
    await loaded()
    selectBrake()
    fireEvent.click(within(screen.getByTestId('text')).getByRole('button', { name: 'Comment' }))
    const box = await screen.findByRole('textbox', { name: 'Comment on the selected passage' })
    fireEvent.click(within(box.closest('div.absolute') as HTMLElement).getByRole('button', { name: 'Cancel' }))
    expect(screen.queryByRole('textbox', { name: 'Comment on the selected passage' })).toBeNull()
    await settle()
    expect(client.artefactsApi.createComment).not.toHaveBeenCalled()
  })
})

describe('the comments column', () => {
  it('lists general and detached threads apart and passage threads with their replies', async () => {
    renderReview()
    await loaded()
    const column = screen.getByRole('region', { name: 'Document comments' })
    expect(within(column).getByRole('heading', { name: 'Comments' })).toBeTruthy()
    expect(within(column).queryByRole('heading', { name: 'General' })).toBeNull()
    fireEvent.click(within(column).getByRole('button', { name: 'General (1)' }))
    const general = within(column).getByRole('heading', { name: 'General' }).parentElement!
    expect(within(general).getByText('General remark')).toBeTruthy()
    fireEvent.click(within(column).getByRole('button', { name: 'Detached (1)' }))
    const detached = within(column).getByRole('heading', { name: 'Detached' }).parentElement!
    expect(within(detached).getByText('Gone passage')).toBeTruthy()
    expect(within(detached).queryByText('Which brake?')).toBeNull()
    const card = threadCard('Which brake?')
    expect(card.getAttribute('aria-label')).toBe('Comment thread by Grace Hopper')
    expect(within(card).getByText('brake').tagName).toBe('BLOCKQUOTE')
    expect(within(card).getByText('The front one.')).toBeTruthy()
    expect(within(card).getAllByText('Ada Lovelace').length).toBeGreaterThan(0)
    expect(card.parentElement!.classList.contains('absolute')).toBe(true)
    expect(screen.queryByText('Fixed the typo')).toBeNull()
  })

  it('highlights only open threads whose passage is in the text', async () => {
    renderReview()
    await loaded()
    expect(editorProps!.commentThreads!.map(thread => thread.id).sort()).toEqual([1, 5])
    expect(document.querySelector('[data-comment-id="1"]')?.textContent).toBe('brake')
    expect(document.querySelector('[data-comment-id="5"]')).toBeNull()
  })

  it('shows resolved threads and their highlights only with Show resolved', async () => {
    renderReview()
    await loaded()
    const toggle = screen.getByRole('checkbox', { name: 'Show resolved (1)' })
    fireEvent.click(toggle)
    const card = threadCard('Fixed the typo')
    expect(within(card).getByText(/Resolved by Ada Lovelace/)).toBeTruthy()
    expect(within(card).getByRole('button', { name: 'Reopen' })).toBeTruthy()
    expect(editorProps!.commentThreads!.map(thread => thread.id)).toContain(4)
    fireEvent.click(toggle)
    expect(screen.queryByText('Fixed the typo')).toBeNull()
    expect(editorProps!.commentThreads!.map(thread => thread.id)).not.toContain(4)
  })

  it('selects a thread when its highlight is clicked and offers a reply box', async () => {
    renderReview()
    await loaded()
    expect(within(threadCard('Which brake?')).queryByRole('textbox', { name: 'Reply' })).toBeNull()
    fireEvent.click(document.querySelector('[data-comment-id="1"]')!)
    const card = threadCard('Which brake?')
    expect(card.classList.contains('border-primary')).toBe(true)
    expect(within(card).getByRole('textbox', { name: 'Reply' })).toBeTruthy()
    expect(document.querySelector('[data-comment-id="1"]')!.classList.contains('comment-highlight-selected')).toBe(true)
  })

  it('selects a thread when it is clicked, highlights its passage and scrolls to it', async () => {
    renderReview()
    await loaded()
    fireEvent.click(within(threadCard('Which brake?')).getByRole('button', { name: 'Open the thread by Grace Hopper' }))
    expect(threadCard('Which brake?').classList.contains('border-primary')).toBe(true)
    expect(editorProps!.commentThreads!.find(thread => thread.id === 1)?.selected).toBe(true)
    expect(editorProps!.commentThreads!.find(thread => thread.id === 5)?.selected).toBe(false)
    expect(Element.prototype.scrollIntoView).toHaveBeenCalled()
  })

  it('posts a reply to the selected thread', async () => {
    renderReview()
    await loaded()
    act(() => editorProps!.onThreadClick!(1))
    const card = threadCard('Which brake?')
    fireEvent.change(within(card).getByRole('textbox', { name: 'Reply' }), { target: { value: 'Agreed.' } })
    fireEvent.click(within(card).getByRole('button', { name: 'Comment' }))
    await waitFor(() => expect(client.artefactsApi.createComment).toHaveBeenCalledWith('requirement', 11, 'Agreed.', { parentId: 1, anchor: undefined }))
  })

  it('resolves an open thread and reopens a resolved one', async () => {
    renderReview()
    await loaded()
    fireEvent.click(within(threadCard('Which brake?')).getByRole('button', { name: 'Resolve' }))
    await waitFor(() => expect(client.artefactsApi.resolveComment).toHaveBeenCalledWith('requirement', 11, 1))
    fireEvent.click(screen.getByRole('checkbox', { name: 'Show resolved (1)' }))
    fireEvent.click(within(threadCard('Fixed the typo')).getByRole('button', { name: 'Reopen' }))
    await waitFor(() => expect(client.artefactsApi.reopenComment).toHaveBeenCalledWith('requirement', 11, 4))
    await waitFor(() => expect(vi.mocked(client.artefactsApi.listComments).mock.calls.length).toBeGreaterThan(1))
  })

  it('offers Resolve only to the people of a controlled document', async () => {
    currentUser = { ...user, id: 99, full_name: 'Someone Else' }
    renderReview()
    await loaded()
    expect(within(threadCard('Which brake?')).queryByRole('button', { name: 'Resolve' })).toBeNull()
  })

  it('shows no comment box without actions.comment', async () => {
    allowComment(false)
    renderReview()
    await loaded()
    expect(screen.getByText('Which brake?')).toBeTruthy()
    expect(screen.queryByRole('textbox', { name: 'Comment' })).toBeNull()
  })
})

describe('the comments column on a narrow screen', () => {
  it('lists passage threads in text order without placing them and keeps the composer in the list', async () => {
    setWide(false)
    renderReview()
    await loaded()
    fireEvent.click(screen.getByRole('button', { name: 'Show comments (3)' }))
    const card = threadCard('Which brake?')
    expect(card.parentElement!.classList.contains('absolute')).toBe(false)
    selectBrake()
    fireEvent.click(within(screen.getByTestId('text')).getByRole('button', { name: 'Comment' }))
    const box = await screen.findByRole('textbox', { name: 'Comment on the selected passage' })
    expect(box.closest('div.absolute')).toBeNull()
  })
})

describe('the comment box', () => {
  it('has 5 rows, grows with its text up to 15 and posts a general comment', async () => {
    renderReview()
    await loaded()
    const box = generalBox()
    expect(box.rows).toBe(5)
    fireEvent.change(box, { target: { value: Array.from({ length: 8 }, (_, index) => `line ${index}`).join('\n') } })
    expect(box.rows).toBe(9)
    fireEvent.change(box, { target: { value: Array.from({ length: 30 }, (_, index) => `line ${index}`).join('\n') } })
    expect(box.rows).toBe(15)
    fireEvent.change(box, { target: { value: 'Whole document remark' } })
    fireEvent.click(within(box.parentElement!).getByRole('button', { name: 'Comment' }))
    await waitFor(() => expect(client.artefactsApi.createComment).toHaveBeenCalledWith('requirement', 11, 'Whole document remark', { parentId: undefined, anchor: undefined }))
    await waitFor(() => expect(screen.queryByRole('textbox', { name: 'Comment' })).toBeNull())
  })

  it.each([['Ctrl+Enter', { ctrlKey: true }], ['Cmd+Enter', { metaKey: true }]] as const)('posts on %s and not on Enter alone', async (_name, modifier) => {
    renderReview()
    await loaded()
    const box = generalBox()
    fireEvent.change(box, { target: { value: 'Quick remark' } })
    fireEvent.keyDown(box, { key: 'Enter' })
    await settle()
    expect(client.artefactsApi.createComment).not.toHaveBeenCalled()
    fireEvent.keyDown(box, { key: 'Enter', ...modifier })
    await waitFor(() => expect(client.artefactsApi.createComment).toHaveBeenCalledWith('requirement', 11, 'Quick remark', { parentId: undefined, anchor: undefined }))
  })

  it('does not post an empty comment', async () => {
    renderReview()
    await loaded()
    const box = generalBox()
    fireEvent.change(box, { target: { value: '   ' } })
    expect((within(box.parentElement!).getByRole('button', { name: 'Comment' }) as HTMLButtonElement).disabled).toBe(true)
    fireEvent.keyDown(box, { key: 'Enter', ctrlKey: true })
    await settle()
    expect(client.artefactsApi.createComment).not.toHaveBeenCalled()
  })
})

describe('the discussion list of a side panel', () => {
  it('lists threads with replies and posts a comment, a reply, a resolve and a reopen', async () => {
    renderThreadList()
    const card = (await screen.findByText('Which brake?')).closest('section')!
    expect(within(card).getByText('The front one.')).toBeTruthy()
    expect(screen.getByText('General remark')).toBeTruthy()
    expect(screen.queryByText('Fixed the typo')).toBeNull()

    const box = await screen.findByRole('textbox', { name: 'Comment' })
    fireEvent.change(box, { target: { value: 'Suite remark' } })
    fireEvent.click(within(box.parentElement!).getByRole('button', { name: 'Comment' }))
    await waitFor(() => expect(client.artefactsApi.createComment).toHaveBeenCalledWith('test-suite', 41, 'Suite remark', { parentId: undefined, anchor: undefined }))

    expect(within(card).queryByRole('textbox', { name: 'Reply' })).toBeNull()
    fireEvent.click(within(card).getByRole('button', { name: 'Open the thread by Grace Hopper' }))
    fireEvent.change(within(card).getByRole('textbox', { name: 'Reply' }), { target: { value: 'Front brake.' } })
    fireEvent.keyDown(within(card).getByRole('textbox', { name: 'Reply' }), { key: 'Enter', ctrlKey: true })
    await waitFor(() => expect(client.artefactsApi.createComment).toHaveBeenCalledWith('test-suite', 41, 'Front brake.', { parentId: 1, anchor: undefined }))

    fireEvent.click(within(card).getByRole('button', { name: 'Resolve' }))
    await waitFor(() => expect(client.artefactsApi.resolveComment).toHaveBeenCalledWith('test-suite', 41, 1))

    fireEvent.click(screen.getByRole('checkbox', { name: 'Show resolved (1)' }))
    const resolved = screen.getByText('Fixed the typo').closest('section')!
    fireEvent.click(within(resolved).getByRole('button', { name: 'Reopen' }))
    await waitFor(() => expect(client.artefactsApi.reopenComment).toHaveBeenCalledWith('test-suite', 41, 4))
    fireEvent.click(screen.getByRole('checkbox', { name: 'Show resolved (1)' }))
    expect(screen.queryByText('Fixed the typo')).toBeNull()
  })

  it('shows no comment box or resolve without the actions', async () => {
    allowComment(false)
    vi.mocked(client.workflowApi.get).mockResolvedValue({ ...workflowFixture, controlled: false, actions: { ...workflowFixture.actions, comment: false } })
    renderThreadList()
    const card = (await screen.findByText('Which brake?')).closest('section')!
    await settle()
    expect(screen.queryByRole('textbox')).toBeNull()
    expect(within(card).queryByRole('button', { name: 'Resolve' })).toBeNull()
  })
})

describe('the open comments of the editing page', () => {
  it('lists the open threads with their passages and replies, read-only', async () => {
    const queryClient = createQueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })
    render(<QueryClientProvider client={queryClient}><ToastProvider><MemoryRouter><OpenThreads artefactType="requirement" artefactId={11} /></MemoryRouter></ToastProvider></QueryClientProvider>)
    const region = await screen.findByRole('region', { name: 'Open comments' })
    expect(within(region).getByRole('heading', { name: 'Open comments (3)' })).toBeTruthy()
    expect(within(region).getByText('Which brake?')).toBeTruthy()
    expect(within(region).getByText('The front one.')).toBeTruthy()
    expect(within(region).queryByText('Fixed the typo')).toBeNull()
    expect(within(region).queryByRole('textbox')).toBeNull()
    expect(within(region).queryByRole('button')).toBeNull()
  })
})

/** A document text with one heading. */
const withHeading = { type: 'doc', content: [{ type: 'heading', attrs: { level: 1 }, content: [{ type: 'text', text: 'Scope' }] }] }

/** Render a detail page shell with its document information panel, text and comments column. */
function renderShell() {
  const queryClient = createQueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 }, mutations: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <MemoryRouter>
          <ReviewCommentsProvider artefactType="requirement" artefactId={11}>
            <DocDetailShell projectPrefix="PRJ" docType="REQ" docCode="PRJ-REQ-001" title="Brake requirement" status="Draft" info={<p>Panel contents</p>} comments={<CommentsColumn />}>
              <CommentableDocEditor content={withHeading} editable={false} />
            </DocDetailShell>
          </ReviewCommentsProvider>
        </MemoryRouter>
      </ToastProvider>
    </QueryClientProvider>,
  )
}

/** The grid that holds the text and the right column of the shell. */
function shellGrid() {
  return screen.getByRole('complementary', { name: 'Document comments column' }).parentElement!.parentElement!
}

describe('showing and hiding the comments', () => {
  it('opens the comments shown on a window 1280 pixels wide and hides and shows them with one control', async () => {
    setWindowWidth(1280)
    renderReview()
    await loaded()
    expect(screen.getByRole('region', { name: 'Document comments' })).toBeTruthy()
    const hide = screen.getByRole('button', { name: 'Hide comments' })
    expect(hide.getAttribute('aria-expanded')).toBe('true')
    fireEvent.click(hide)
    expect(screen.queryByRole('region', { name: 'Document comments' })).toBeNull()
    const show = screen.getByRole('button', { name: 'Show comments (3)' })
    expect(show.getAttribute('aria-expanded')).toBe('false')
    fireEvent.click(show)
    expect(screen.getByRole('region', { name: 'Document comments' })).toBeTruthy()
    expect(threadCard('Which brake?')).toBeTruthy()
  })

  it('opens the comments collapsed on a window narrower than 1280 pixels', async () => {
    setWindowWidth(1279)
    renderReview()
    await loaded()
    expect(screen.queryByRole('region', { name: 'Document comments' })).toBeNull()
    expect(screen.getByRole('button', { name: 'Show comments (3)' }).getAttribute('aria-expanded')).toBe('false')
  })

  it('shows the collapsed comments with the composer when a passage is commented on', async () => {
    setWindowWidth(1000)
    renderReview()
    await loaded()
    selectBrake()
    fireEvent.click(within(screen.getByTestId('text')).getByRole('button', { name: 'Comment' }))
    expect(screen.getByRole('region', { name: 'Document comments' })).toBeTruthy()
    expect(await screen.findByRole('textbox', { name: 'Comment on the selected passage' })).toBeTruthy()
  })

  it('shows the collapsed comments with the thread selected when its highlight is clicked', async () => {
    setWindowWidth(1000)
    const { container } = renderReview()
    await loaded()
    fireEvent.click(container.querySelector('[data-comment-id="1"]')!)
    expect(screen.getByRole('region', { name: 'Document comments' })).toBeTruthy()
    expect(within(threadCard('Which brake?')).getByRole('textbox', { name: 'Reply' })).toBeTruthy()
  })
})

describe('showing and hiding the outline', () => {
  it('opens the outline shown for a text with headings on a window 1536 pixels wide and hides and shows it', async () => {
    setWindowWidth(1536)
    renderReview({ content: withHeading })
    await loaded()
    expect(editorProps!.showOutline).toBe(true)
    act(() => editorProps!.onOutlineToggle!(false))
    expect(editorProps!.showOutline).toBe(false)
    act(() => editorProps!.onOutlineToggle!(true))
    expect(editorProps!.showOutline).toBe(true)
  })

  it('opens the outline collapsed on a window narrower than 1536 pixels and shows it on request', async () => {
    setWindowWidth(1535)
    renderReview({ content: withHeading })
    await loaded()
    expect(editorProps!.showOutline).toBe(false)
    act(() => editorProps!.onOutlineToggle!(true))
    expect(editorProps!.showOutline).toBe(true)
  })

  it('opens the outline collapsed for a text without headings', async () => {
    setWindowWidth(1536)
    renderReview()
    await loaded()
    expect(editorProps!.showOutline).toBe(false)
  })
})

describe('the right column of a detail page', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('keeps its 380 pixels while the comments or the document information are shown and gives the text the width when both are hidden', async () => {
    setWindowWidth(1280)
    renderShell()
    await loaded()
    const wideTrack = 'lg:grid-cols-[minmax(0,1fr)_380px]'
    const autoTrack = 'lg:grid-cols-[minmax(0,1fr)_auto]'
    expect(shellGrid().classList.contains(wideTrack)).toBe(true)
    fireEvent.click(screen.getByRole('button', { name: 'Hide comments' }))
    expect(shellGrid().classList.contains(wideTrack)).toBe(true)
    fireEvent.click(screen.getByRole('button', { name: 'Hide document information' }))
    expect(shellGrid().classList.contains(autoTrack)).toBe(true)
    expect(shellGrid().classList.contains(wideTrack)).toBe(false)
    fireEvent.click(screen.getByRole('button', { name: 'Show comments (3)' }))
    expect(shellGrid().classList.contains(wideTrack)).toBe(true)
  })

  it('opens the comments collapsed beside the document information on a narrow window', async () => {
    setWindowWidth(1000)
    renderShell()
    await loaded()
    expect(screen.getByRole('complementary', { name: 'Document information' })).toBeTruthy()
    expect(screen.queryByRole('region', { name: 'Document comments' })).toBeNull()
    expect(screen.getByRole('button', { name: 'Show comments (3)' })).toBeTruthy()
  })
})
