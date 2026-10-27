import { createContext, useCallback, useContext, useLayoutEffect, useMemo, useRef, useState, type ComponentProps, type ReactNode } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { MessageSquarePlus } from 'lucide-react'

import { artefactsApi, type ArtefactComment, type CommentAnchor } from '../../api/client'
import { useAuth } from '../../contexts/AuthContext'
import { useDocumentWorkflow } from '../../hooks/useDocumentWorkflow'
import { refreshArtefactViews } from '../../lib/refreshArtefactViews'
import { stackThreads } from '../../lib/threadLayout'
import { formatDateTime } from '../../test/date-utils'
import { DocEditor } from '../editor'
import type { HighlightedThread } from '../editor/CommentHighlights'
import UserIdentity from '../UserIdentity'
import { useToast } from '../useToast'

const buttonClass = 'px-2.5 py-1 rounded-md border border-input text-xs hover:bg-accent/40 disabled:opacity-50'
const boxClass = 'block w-full rounded-md border border-input bg-background p-2 text-sm resize-y'

type Pending = { anchor: CommentAnchor; rect: DOMRect; pageTop: number }

interface ReviewCommentsState {
  artefactType: string
  artefactId: number
  projectPrefix?: string
  projectId?: number
  selectedId: number | null
  select: (id: number | null) => void
  pending: Pending | null
  setPending: (pending: Pending | null) => void
  composing: Pending | null
  setComposing: (pending: Pending | null) => void
  showResolved: boolean
  setShowResolved: (show: boolean) => void
}

const ReviewCommentsContext = createContext<ReviewCommentsState | null>(null)

/** Shares a document's selected thread, its text selection and the resolved-thread toggle between its text and its comments column. */
export function ReviewCommentsProvider({ artefactType, artefactId, projectPrefix, projectId, children }: Readonly<{ artefactType: string; artefactId: number; projectPrefix?: string; projectId?: number; children: ReactNode }>) {
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [pending, setPending] = useState<Pending | null>(null)
  const [composing, setComposing] = useState<Pending | null>(null)
  const [showResolved, setShowResolved] = useState(false)
  const value = useMemo(() => ({
    artefactType, artefactId, projectPrefix, projectId, selectedId, select: setSelectedId, pending, setPending, composing, setComposing, showResolved, setShowResolved,
  }), [artefactType, artefactId, projectPrefix, projectId, selectedId, pending, composing, showResolved])
  return <ReviewCommentsContext.Provider value={value}>{children}</ReviewCommentsContext.Provider>
}

/** The threads of a document and whether the viewer may comment and resolve. */
function useThreads(artefactType: string, artefactId: number) {
  const { user } = useAuth()
  const workflow = useDocumentWorkflow(artefactType, artefactId || undefined)
  const comments = useQuery({
    queryKey: ['artefactComments', artefactType, artefactId],
    queryFn: () => artefactsApi.listComments(artefactType, artefactId),
    enabled: !!artefactId,
    retry: false,
  })
  const state = workflow.data
  const canComment = !!state?.actions?.comment
  const people = [state?.created_by, state?.assignee, state?.reviewer, state?.approver].map(person => person?.id)
  const canResolve = state?.controlled ? !!user && people.includes(user.id) : canComment
  return { comments, canComment, canResolve }
}

/** A read-only document text whose commented passages are highlighted and whose selections can be commented. */
export function CommentableDocEditor(props: Readonly<ComponentProps<typeof DocEditor>>) {
  const context = useContext(ReviewCommentsContext)
  const { comments, canComment } = useThreads(context?.artefactType ?? '', context?.artefactId ?? 0)
  const threads = useMemo<HighlightedThread[]>(() => (comments.data ?? [])
    .filter(thread => thread.anchor && (context?.showResolved || !thread.resolved_at))
    .map(thread => ({ id: thread.id, anchor: thread.anchor!, selected: thread.id === context?.selectedId })),
  [comments.data, context?.showResolved, context?.selectedId])
  const setPending = context?.setPending
  const onSelection = useCallback((selection: { anchor: CommentAnchor; rect: DOMRect } | null) => setPending?.(canComment && selection ? { ...selection, pageTop: selection.rect.top + window.scrollY } : null), [setPending, canComment])
  const composing = context?.composing
  useLayoutEffect(() => {
    if (!setPending || composing) return
    const clear = () => setPending(null)
    window.addEventListener('scroll', clear, { passive: true })
    return () => window.removeEventListener('scroll', clear)
  }, [setPending, composing])
  if (!context) return <DocEditor {...props} />
  return <>
    <DocEditor {...props} commentThreads={threads} onThreadClick={context.select} onCommentSelection={onSelection} />
    {context.pending && !context.composing && <button
      type="button"
      className="fixed z-40 inline-flex items-center gap-1 rounded-md bg-primary px-2.5 py-1 text-xs text-primary-foreground shadow-elegant"
      style={{ top: context.pending.rect.bottom + 6, left: context.pending.rect.left }}
      onMouseDown={event => event.preventDefault()}
      onClick={() => context.setComposing(context.pending)}
    ><MessageSquarePlus className="h-3.5 w-3.5" />Comment</button>}
  </>
}

/** A comment box that grows with its text and posts on Ctrl+Enter or Cmd+Enter. */
function CommentBox({ label, placeholder, busy, onPost, onCancel, autoFocus }: Readonly<{
  label: string
  placeholder: string
  busy: boolean
  onPost: (body: string) => Promise<unknown>
  onCancel?: () => void
  autoFocus?: boolean
}>) {
  const [body, setBody] = useState('')
  const rows = Math.min(15, Math.max(5, body.split('\n').length + 1))
  const post = () => {
    if (!body.trim() || busy) return
    void onPost(body.trim()).then(() => setBody(''), () => undefined)
  }
  return <div className="space-y-2" onClick={event => event.stopPropagation()}>
    <textarea
      aria-label={label}
      placeholder={placeholder}
      rows={rows}
      value={body}
      autoFocus={autoFocus}
      onChange={event => setBody(event.target.value)}
      onKeyDown={event => { if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) { event.preventDefault(); post() } }}
      className={boxClass}
    />
    <div className="flex gap-2">
      <button type="button" className={buttonClass} disabled={!body.trim() || busy} onClick={post}>Comment</button>
      {onCancel && <button type="button" className={buttonClass} onClick={onCancel}>Cancel</button>}
    </div>
  </div>
}

/** One comment with its author, picture and time. */
function CommentLine({ comment }: Readonly<{ comment: ArtefactComment }>) {
  return <article className="break-words space-y-1">
    <div className="flex items-center justify-between gap-2 text-xs">
      <UserIdentity user={{ id: comment.author_user_id ?? undefined, full_name: comment.author_name, profile_picture_url: comment.author_profile_picture_url }} />
      <time className="text-muted-foreground shrink-0">{formatDateTime(comment.created_at)}</time>
    </div>
    <p className="whitespace-pre-wrap text-sm">{comment.body}</p>
  </article>
}

/** A thread: its quoted passage, first comment, replies, reply box and resolve control. */
function ThreadCard({ thread, selected, onSelect, canComment, canResolve, busy, onReply, onResolve }: Readonly<{
  thread: ArtefactComment
  selected: boolean
  onSelect: () => void
  canComment: boolean
  canResolve: boolean
  busy: boolean
  onReply: (body: string) => Promise<unknown>
  onResolve: (resolved: boolean) => void
}>) {
  return <section
    aria-label={`Comment thread by ${thread.author_name}`}
    data-thread-id={thread.id}
    className={`rounded-lg border bg-card p-3 space-y-3 ${selected ? 'border-primary ring-1 ring-primary' : 'border-border'} ${thread.resolved_at ? 'opacity-70' : ''}`}
  >
    <button type="button" className="block w-full text-left space-y-2" aria-label={`Open the thread by ${thread.author_name}`} onClick={onSelect}>
      {thread.anchor && <blockquote className="border-l-2 border-primary pl-2 text-xs text-muted-foreground line-clamp-3">{thread.anchor.exact}</blockquote>}
      <CommentLine comment={thread} />
    </button>
    {(thread.replies ?? []).map(reply => <div key={reply.id} className="pl-3 border-l border-border"><CommentLine comment={reply} /></div>)}
    {thread.resolved_at && <p className="text-xs text-muted-foreground">Resolved{thread.resolved_by ? ` by ${thread.resolved_by.full_name}` : ''} · {formatDateTime(thread.resolved_at)}</p>}
    {selected && canComment && !thread.resolved_at && <CommentBox label="Reply" placeholder="Reply" busy={busy} onPost={onReply} />}
    {canResolve && <button type="button" className={buttonClass} disabled={busy} onClick={() => onResolve(!thread.resolved_at)}>
      {thread.resolved_at ? 'Reopen' : 'Resolve'}
    </button>}
  </section>
}

/** The mutations of a document's discussion. */
function useDiscussion(artefactType: string, artefactId: number, projectPrefix?: string, projectId?: number) {
  const queryClient = useQueryClient()
  const toast = useToast()
  const refresh = () => refreshArtefactViews(queryClient, artefactType, artefactId, projectPrefix, projectId)
  const post = useMutation({
    mutationFn: ({ body, parentId, anchor }: { body: string; parentId?: number; anchor?: CommentAnchor }) => artefactsApi.createComment(artefactType, artefactId, body, { parentId, anchor }),
    onSuccess: refresh,
    onError: failure => toast.failed('Posting the comment', failure),
  })
  const resolve = useMutation({
    mutationFn: ({ id, resolved }: { id: number; resolved: boolean }) => resolved ? artefactsApi.resolveComment(artefactType, artefactId, id) : artefactsApi.reopenComment(artefactType, artefactId, id),
    onSuccess: refresh,
    onError: failure => toast.failed('Updating the thread', failure),
  })
  return { post, resolve, busy: post.isPending || resolve.isPending }
}

/** The checkbox that shows resolved threads, with their number. */
function ResolvedToggle({ show, onChange, count }: Readonly<{ show: boolean; onChange: (show: boolean) => void; count: number }>) {
  if (count === 0) return null
  return <label className="flex items-center gap-2 whitespace-nowrap text-xs text-muted-foreground">
    <input type="checkbox" checked={show} onChange={event => onChange(event.target.checked)} />Show resolved ({count})
  </label>
}

/** The discussion of a document as a list: threads with replies, a box for a new comment and the resolved toggle. */
export function ThreadList({ artefactType, artefactId, projectPrefix, projectId }: Readonly<{ artefactType: string; artefactId: number; projectPrefix?: string; projectId?: number }>) {
  const { comments, canComment, canResolve } = useThreads(artefactType, artefactId)
  const { post, resolve, busy } = useDiscussion(artefactType, artefactId, projectPrefix, projectId)
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [showResolved, setShowResolved] = useState(false)
  const threads = (comments.data ?? []).filter(thread => showResolved || !thread.resolved_at)
  return <div className="space-y-3">
    <ResolvedToggle show={showResolved} onChange={setShowResolved} count={(comments.data ?? []).filter(thread => thread.resolved_at).length} />
    {comments.isPending && <p className="text-sm">Loading comments...</p>}
    {!comments.isPending && comments.isError && <p role="alert">Could not load comments.</p>}
    {!comments.isPending && !comments.isError && threads.length === 0 && <p className="text-sm text-muted-foreground">No comments yet.</p>}
    {threads.map(thread => <ThreadCard key={thread.id} thread={thread} selected={selectedId === thread.id} onSelect={() => setSelectedId(thread.id)}
      canComment={canComment} canResolve={canResolve} busy={busy}
      onReply={body => post.mutateAsync({ body, parentId: thread.id })} onResolve={resolved => resolve.mutate({ id: thread.id, resolved })} />)}
    {canComment && <CommentBox label="Comment" placeholder="Write a comment" busy={busy} onPost={body => post.mutateAsync({ body })} />}
  </div>
}

const COMPOSER_ID = -1

/** True while the window is at least as wide as the given number of pixels. */
function useWideScreen(width: number): boolean {
  const query = `(min-width: ${width}px)`
  const [wide, setWide] = useState(() => typeof window !== 'undefined' && typeof window.matchMedia === 'function' && window.matchMedia(query).matches)
  useLayoutEffect(() => {
    if (typeof window.matchMedia !== 'function') return
    const media = window.matchMedia(query)
    const update = () => setWide(media.matches)
    update()
    media.addEventListener('change', update)
    return () => media.removeEventListener('change', update)
  }, [query])
  return wide
}

/** The comments column beside a document's text: general and detached threads behind two buttons at its top, and from 1024 pixels wide the passage threads level with their passages; narrower, the passage threads as a list in text order. */
export function CommentsColumn() {
  const context = useContext(ReviewCommentsContext)
  if (!context) throw new Error('CommentsColumn needs a ReviewCommentsProvider')
  const { artefactType, artefactId, projectPrefix, projectId, selectedId, select, composing, setComposing, setPending, showResolved, setShowResolved } = context
  const { comments, canComment, canResolve } = useThreads(artefactType, artefactId)
  const { post, resolve, busy } = useDiscussion(artefactType, artefactId, projectPrefix, projectId)
  const wide = useWideScreen(1024)
  const zone = useRef<HTMLDivElement>(null)
  const composerBox = useRef<HTMLDivElement>(null)
  const cards = useRef(new Map<number, HTMLElement>())
  const [writingGeneral, setWritingGeneral] = useState(false)
  const [openList, setOpenList] = useState<'general' | 'detached' | null>(null)
  const [layout, setLayout] = useState<{ tops: Record<number, number>; order: number[]; detached: number[]; composerTop: number | null; height: number }>({ tops: {}, order: [], detached: [], composerTop: null, height: 0 })
  const all = comments.data ?? []
  const visible = all.filter(thread => showResolved || !thread.resolved_at)
  const anchored = visible.filter(thread => thread.anchor)
  const general = visible.filter(thread => !thread.anchor)

  useLayoutEffect(() => {
    const measure = () => {
      if (!zone.current) return
      const origin = zone.current.getBoundingClientRect().top
      const items: { id: number; desired: number; height: number }[] = []
      const detached: number[] = []
      for (const thread of anchored) {
        const passage = document.querySelector(`[data-comment-id="${thread.id}"]`)
        if (!passage) { detached.push(thread.id); continue }
        items.push({ id: thread.id, desired: passage.getBoundingClientRect().top - origin, height: cards.current.get(thread.id)?.offsetHeight ?? 120 })
      }
      const order = [...items].sort((left, right) => left.desired - right.desired).map(item => item.id)
      const placedItems = wide && composing
        ? [...items, { id: COMPOSER_ID, desired: composing.pageTop - (origin + window.scrollY), height: composerBox.current?.offsetHeight ?? 220 }]
        : items
      const tops = wide ? stackThreads(placedItems, composing ? COMPOSER_ID : selectedId, 0) : {}
      const composerTop = wide && composing ? tops[COMPOSER_ID] ?? 0 : null
      const height = wide ? Math.max(0, ...placedItems.map(item => (tops[item.id] ?? 0) + item.height)) : 0
      const next = { tops, order, detached, composerTop, height }
      setLayout(current => JSON.stringify(current) === JSON.stringify(next) ? current : next)
    }
    measure()
    window.addEventListener('resize', measure)
    const observer = typeof ResizeObserver === 'undefined' ? null : new ResizeObserver(measure)
    observer?.observe(document.body)
    return () => { window.removeEventListener('resize', measure); observer?.disconnect() }
  })

  const card = (thread: ArtefactComment) => <ThreadCard thread={thread} selected={selectedId === thread.id} canComment={canComment} canResolve={canResolve} busy={busy}
    onSelect={() => { select(thread.id); document.querySelector(`[data-comment-id="${thread.id}"]`)?.scrollIntoView?.({ block: 'center', behavior: 'smooth' }) }}
    onReply={body => post.mutateAsync({ body, parentId: thread.id })} onResolve={resolved => resolve.mutate({ id: thread.id, resolved })} />
  const detached = anchored.filter(thread => layout.detached.includes(thread.id))
  const placed = layout.order.map(id => anchored.find(thread => thread.id === id)).filter((thread): thread is ArtefactComment => !!thread)
  const composer = composing && <div ref={composerBox} className={`${wide ? 'absolute inset-x-0 z-10' : ''} rounded-lg border border-primary bg-card p-3 space-y-2`} style={wide && layout.composerTop !== null ? { top: layout.composerTop } : undefined}>
    <blockquote className="border-l-2 border-primary pl-2 text-xs text-muted-foreground line-clamp-3">{composing.anchor.exact}</blockquote>
    <CommentBox label="Comment on the selected passage" placeholder="Comment on this passage" busy={busy} autoFocus
      onPost={body => post.mutateAsync({ body, anchor: composing.anchor }).then(() => { setComposing(null); setPending(null) })}
      onCancel={() => { setComposing(null); setPending(null) }} />
  </div>

  return <section aria-label="Document comments" className="min-w-0 space-y-3">
    <div className="flex flex-wrap items-center justify-between gap-2">
      <h3 className="text-lg font-semibold text-foreground">Comments</h3>
      <div className="flex flex-wrap items-center gap-3">
        <ResolvedToggle show={showResolved} onChange={setShowResolved} count={all.filter(thread => thread.resolved_at).length} />
        {canComment && !writingGeneral && <button type="button" className={`${buttonClass} whitespace-nowrap`} onClick={() => setWritingGeneral(true)}>Add a general comment</button>}
      </div>
    </div>
    {(general.length > 0 || detached.length > 0) && <div className="flex flex-wrap gap-2">
      {general.length > 0 && <button type="button" className={buttonClass} aria-expanded={openList === 'general'} onClick={() => setOpenList(openList === 'general' ? null : 'general')}>General ({general.length})</button>}
      {detached.length > 0 && <button type="button" className={buttonClass} aria-expanded={openList === 'detached'} onClick={() => setOpenList(openList === 'detached' ? null : 'detached')}>Detached ({detached.length})</button>}
    </div>}
    {openList === 'general' && general.length > 0 && <div className="space-y-2"><h4 className="text-xs uppercase tracking-wide text-muted-foreground">General</h4>{general.map(thread => <div key={thread.id}>{card(thread)}</div>)}</div>}
    {openList === 'detached' && detached.length > 0 && <div className="space-y-2"><h4 className="text-xs uppercase tracking-wide text-muted-foreground">Detached</h4><p className="text-xs text-muted-foreground">The commented passage changed.</p>{detached.map(thread => <div key={thread.id}>{card(thread)}</div>)}</div>}
    {comments.isPending && <p className="text-sm">Loading comments...</p>}
    {!comments.isPending && comments.isError && <p role="alert">Could not load comments.</p>}
    {!comments.isPending && !comments.isError && all.length === 0 && <p className="text-sm text-muted-foreground">No comments yet.{canComment ? ' Select text to comment on a passage.' : ''}</p>}
    {canComment && writingGeneral && <CommentBox label="Comment" placeholder="Comment on the whole document" busy={busy} autoFocus
      onPost={body => post.mutateAsync({ body }).then(() => setWritingGeneral(false))} onCancel={() => setWritingGeneral(false)} />}
    {!wide && composer}
    <div ref={zone} className="relative" style={wide ? { height: layout.height } : undefined}>
      {wide && composer}
      {anchored.filter(thread => !layout.detached.includes(thread.id)).map(thread => wide
        ? <div key={thread.id} ref={element => { if (element) cards.current.set(thread.id, element); else cards.current.delete(thread.id) }} className="absolute inset-x-0" style={{ top: layout.tops[thread.id] ?? 0 }}>{card(thread)}</div>
        : null)}
      {!wide && <div className="space-y-2">{placed.map(thread => <div key={thread.id}>{card(thread)}</div>)}</div>}
    </div>
  </section>
}

/** The open threads of a document, read-only, for the person editing it. */
export function OpenThreads({ artefactType, artefactId }: Readonly<{ artefactType: string; artefactId: number }>) {
  const { comments } = useThreads(artefactType, artefactId)
  const open = (comments.data ?? []).filter(thread => !thread.resolved_at)
  if (open.length === 0) return null
  return <section aria-label="Open comments" className="space-y-2">
    <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Open comments ({open.length})</h3>
    {open.map(thread => <div key={thread.id} className="rounded-lg border border-border bg-card p-3 space-y-2">
      {thread.anchor && <blockquote className="border-l-2 border-primary pl-2 text-xs text-muted-foreground line-clamp-3">{thread.anchor.exact}</blockquote>}
      <CommentLine comment={thread} />
      {(thread.replies ?? []).map(reply => <div key={reply.id} className="pl-3 border-l border-border"><CommentLine comment={reply} /></div>)}
    </div>)}
  </section>
}
