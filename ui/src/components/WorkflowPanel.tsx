import { refreshProjectViews } from '../lib/refreshProjectViews'
import { useState } from 'react'
import { UserCheck, UserCog } from 'lucide-react'
import { formatDateTime } from '../test/date-utils'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { artefactsApi, extractApiErrorMessage, workflowApi, type ApprovedDocumentRevision, type DocumentSection } from '../api/client'
import { useDocumentWorkflow } from '../hooks/useDocumentWorkflow'
import UserIdentity from './UserIdentity'
import UserSelect from './UserSelect'
import { SectionCard } from './DocDetailShell'
import { DocEditor } from './editor'
import { useToast } from './useToast'
import { docUrl, type DocType } from '../types/doc'
import { normalizeTcsRows } from '../utils/tcs'
import { TcsArteTable } from './TcsArteTable'

type Operation = { kind: 'review' | 'approval' | 'approve' | 'decline' | 'draft' | 'comment' | 'assign'; data?: { reviewer_id?: number | null; approver_id?: number | null } }
const actionButtonClass = 'px-3 py-2 rounded-md border border-input text-sm hover:bg-accent/40 disabled:opacity-50'
const reviewButtonClass = 'w-full inline-flex items-center justify-center px-3 py-1.5 rounded-md bg-amber-500/90 text-white text-xs font-medium hover:bg-amber-500 disabled:opacity-50'
const approvalButtonClass = 'w-full inline-flex items-center justify-center px-3 py-1.5 rounded-md bg-emerald-600 text-white text-xs font-medium hover:bg-emerald-500 disabled:opacity-50'
const ENTITY_KEYS: Record<string, string> = { requirement: 'requirement', 'test-case': 'testCase', document: 'document', design: 'design', risk: 'risk', change: 'change', 'test-concept': 'testConcept', defect: 'defect', 'test-suite': 'testSuite', campaign: 'campaign' }

export default function WorkflowPanel({ artefactType, artefactId, projectPrefix, projectId }: { artefactType: string; artefactId: number; projectPrefix?: string; projectId?: number }) {
  const workflow = useDocumentWorkflow(artefactType, artefactId)
  const queryClient = useQueryClient()
  const toast = useToast()
  const [tab, setTab] = useState<'workflow' | 'comments' | 'history'>('workflow')
  const [comment, setComment] = useState('')
  const [revision, setRevision] = useState<number | null>(null)
  const [downloadId, setDownloadId] = useState<number | null>(null)
  const comments = useQuery({ queryKey: ['artefactComments', artefactType, artefactId], queryFn: () => artefactsApi.listComments(artefactType, artefactId), enabled: !!workflow.data && tab === 'comments', retry: false })
  const archive = useQuery({ queryKey: ['document-revision', artefactType, artefactId, revision], queryFn: () => workflowApi.getRevision(artefactType, artefactId, revision!), enabled: !!workflow.data && revision !== null, retry: false })
  const mutation = useMutation({
    mutationFn: (operation: Operation) => {
      if (operation.kind === 'assign') return workflowApi.assign(artefactType, artefactId, operation.data ?? {})
      if (operation.kind === 'review' || operation.kind === 'approval') return workflowApi.request(artefactType, artefactId, operation.kind)
      if (operation.kind === 'approve') return workflowApi.approve(artefactType, artefactId)
      if (operation.kind === 'decline') return workflowApi.decline(workflow.data!.pending_request!.id)
      if (operation.kind === 'draft') return workflowApi.startDraft(artefactType, artefactId)
      return artefactsApi.createComment(artefactType, artefactId, comment.trim())
    },
    onSuccess: (result, operation) => {
      if (operation.kind === 'comment') setComment('')
      refreshProjectViews(queryClient, { prefix: projectPrefix, projectId })
      void Promise.all([
        ['document-workflow', artefactType, artefactId], [ENTITY_KEYS[artefactType], artefactId],
        ['artefactComments', artefactType, artefactId], ['artefactActivity', artefactType, artefactId],
        ['document-revision', artefactType, artefactId], ['doc-facade', projectPrefix],
      ].map(queryKey => queryClient.invalidateQueries({ queryKey })))
      toast.notify(result?.already_requested ? 'Already requested' : 'Document updated', 'success')
    },
    onError: failure => toast.failed('Updating the document', failure),
  })
  const download = async (file: ApprovedDocumentRevision['snapshot']['attachments'][number]) => {
    if (revision === null) return
    setDownloadId(file.id)
    try {
      const blob = await workflowApi.downloadRevisionAttachment(artefactType, artefactId, revision, file.id)
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = file.original_filename
      link.click()
      URL.revokeObjectURL(url)
    } catch (error) { toast.failed('Downloading the approved file', error) }
    finally { setDownloadId(null) }
  }
  if (workflow.isPending) return <section aria-label="Document review" className="rounded-lg border border-border p-4">Loading review details...</section>
  if (workflow.isError || !workflow.data?.actions) return <section aria-label="Document review" className="rounded-lg border border-border p-4"><p role="alert">Could not load review details.</p><button className={actionButtonClass} type="button" onClick={() => workflow.refetch()}>Retry</button></section>
  const state = workflow.data
  const busy = mutation.isPending
  return <section aria-label="Document review" className="space-y-4">
    <SectionCard title="Review">
      <div className="space-y-3">
        {state.controlled && state.phase && state.revision_number !== null && <div className="text-sm text-muted-foreground">{state.phase} · Revision {state.revision_number}</div>}
        <div>
          <div className="text-xs uppercase tracking-wide text-muted-foreground mb-1">Reviewer</div>
          <div className="text-sm text-foreground">{state.reviewer ? <UserIdentity user={state.reviewer} /> : 'Unassigned'}</div>
        </div>
        <div>
          <div className="text-xs uppercase tracking-wide text-muted-foreground mb-1">Reviewed by</div>
          <div className="text-sm text-foreground">{state.reviewed_by ? <UserIdentity user={state.reviewed_by} /> : 'Unassigned'}</div>
          {state.reviewed_at && <div className="text-xs text-muted-foreground mt-0.5">{formatDateTime(state.reviewed_at)}</div>}
        </div>
        <fieldset disabled={busy} className="space-y-3">
          {state.actions.assign_reviewer && <UserSelect value={String(state.reviewer?.id ?? '')} onChange={value => mutation.mutate({ kind: 'assign', data: { reviewer_id: value ? Number(value) : null } })} users={state.options.reviewers} label="Select reviewer" />}
          {state.controlled && state.actions.request_review && <button className={reviewButtonClass} type="button" onClick={() => mutation.mutate({ kind: 'review' })}><UserCheck className="h-3.5 w-3.5 mr-1" />Request review</button>}
          {state.controlled && <button className={reviewButtonClass} type="button" disabled={!state.actions.request_approval} onClick={() => mutation.mutate({ kind: 'approval' })}><UserCheck className="h-3.5 w-3.5 mr-1" />Mark Reviewed</button>}
          {state.controlled && state.actions.decline && state.pending_request?.kind === 'review' && <button className={actionButtonClass} type="button" onClick={() => mutation.mutate({ kind: 'decline' })}>Decline</button>}
        </fieldset>
        <button className={actionButtonClass} type="button" aria-pressed={tab === 'comments'} onClick={() => setTab(tab === 'comments' ? 'workflow' : 'comments')}>Comments</button>
      </div>
    </SectionCard>
    {state.controlled && <SectionCard title="Approval">
      <div className="space-y-3">
        <div>
          <div className="text-xs uppercase tracking-wide text-muted-foreground mb-1">Approver</div>
          <div className="text-sm text-foreground">{state.approver ? <UserIdentity user={state.approver} /> : 'Unassigned'}</div>
        </div>
        <div>
          <div className="text-xs uppercase tracking-wide text-muted-foreground mb-1">Approved by</div>
          <div className="text-sm text-foreground">{state.approved_by ? <UserIdentity user={state.approved_by} /> : 'Unassigned'}</div>
          {state.approved_at && <div className="text-xs text-muted-foreground mt-0.5">{formatDateTime(state.approved_at)}</div>}
        </div>
        <fieldset disabled={busy} className="space-y-3">
          {state.actions.assign_approver && <UserSelect value={String(state.approver?.id ?? '')} onChange={value => mutation.mutate({ kind: 'assign', data: { approver_id: value ? Number(value) : null } })} users={state.options.approvers} label="Select approver" />}
          <button className={approvalButtonClass} type="button" disabled={!state.actions.approve} onClick={() => mutation.mutate({ kind: 'approve' })}><UserCog className="h-3.5 w-3.5 mr-1" />Mark Approved</button>
          {state.actions.decline && state.pending_request?.kind === 'approval' && <button className={actionButtonClass} type="button" onClick={() => mutation.mutate({ kind: 'decline' })}>Decline</button>}
          {state.actions.start_draft && <button className={actionButtonClass} type="button" onClick={() => mutation.mutate({ kind: 'draft' })}>Start working Draft</button>}
        </fieldset>
        {state.pending_request && <p className="text-sm text-muted-foreground">Pending {state.pending_request.kind} request · {formatDateTime(state.pending_request.created_at)}</p>}
        {!state.pending_request && state.last_request && <p className="text-sm text-muted-foreground">Last {state.last_request.kind} request: {state.last_request.status}{state.last_request.retry_at && ` · Request again after ${formatDateTime(state.last_request.retry_at)}`}</p>}
        <button className={actionButtonClass} type="button" aria-pressed={tab === 'history'} onClick={() => setTab(tab === 'history' ? 'workflow' : 'history')}>Revision history</button>
      </div>
    </SectionCard>}
    {mutation.isError && <p role="alert" className="text-destructive">{extractApiErrorMessage(mutation.error)}</p>}
    {tab === 'comments' && <SectionCard title="Discussion">
      {comments.isPending ? <p>Loading comments...</p> : comments.isError ? <p role="alert">Could not load comments.</p> : (comments.data ?? []).map(item => <article key={item.id} className="mb-4"><UserIdentity user={{ id: item.author_user_id ?? undefined, full_name: item.author_name, profile_picture_url: item.author_profile_picture_url }} /><p className="whitespace-pre-wrap">{item.body}</p><time>{formatDateTime(item.created_at)}</time></article>)}
      {state.actions.comment && <fieldset disabled={busy} className="mt-4 space-y-3"><label className="block">Comment<textarea aria-label="Comment" value={comment} onChange={event => setComment(event.target.value)} className="block w-full rounded-md border border-input bg-background p-3" /></label><button className={actionButtonClass} type="button" disabled={!comment.trim()} onClick={() => mutation.mutate({ kind: 'comment' })}>Post Comment</button></fieldset>}
    </SectionCard>}
    {tab === 'history' && state.controlled && <SectionCard title="Approved revisions">
      {state.revisions.length === 0 ? <p>No approved revisions recorded.</p> : state.revisions.map(item => <div key={item.revision_number} className="mb-3"><button className={actionButtonClass} type="button" onClick={() => setRevision(item.revision_number)}>Open revision {item.revision_number}</button><span> · {item.approved_by ? <UserIdentity user={item.approved_by} /> : 'Approval actor not recorded'} · {formatDateTime(item.approved_at ?? item.captured_at)}</span></div>)}
    </SectionCard>}
    {revision !== null && <section role="dialog" aria-label={`Approved revision ${revision}`} className="rounded-lg border border-border bg-card p-6 space-y-4"><div className="flex justify-between"><h3>Approved revision {revision}</h3><button className={actionButtonClass} type="button" onClick={() => setRevision(null)}>Close revision</button></div>{archive.isPending ? <p>Loading approved content...</p> : archive.isError || !archive.data ? <p role="alert">Could not load this approved revision.</p> : <ArchivedBody archive={archive.data} projectPrefix={projectPrefix} download={download} downloadId={downloadId} />}</section>}
  </section>
}

function ArchivedBody({ archive, projectPrefix, download, downloadId }: { archive: ApprovedDocumentRevision; projectPrefix?: string; download: (file: ApprovedDocumentRevision['snapshot']['attachments'][number]) => Promise<void>; downloadId: number | null }) {
  const { fields, sections, attachments, suite_items: items } = archive.snapshot
  const html = typeof fields.content_html === 'string' ? new DOMParser().parseFromString(fields.content_html, 'text/html').body.textContent : null
  const steps = normalizeTcsRows(fields.steps)
  const properties = Object.entries(fields).filter(([key, value]) => value !== null && value !== undefined && !['title', 'name', 'description', 'content_json', 'content_html', 'steps'].includes(key))
  return <div className="space-y-4">
    <h4>{String(fields.title ?? fields.name ?? 'Approved document')}</h4>
    <p>Approved by {archive.approved_by ? <UserIdentity user={archive.approved_by} /> : 'Not recorded'}{archive.approved_at && ` · ${formatDateTime(archive.approved_at)}`}</p>
    {archive.authorizing_change && <p>Authorizing change: {archive.authorizing_change.change_id} · {archive.authorizing_change.title}</p>}
    {fields.description ? <p className="whitespace-pre-wrap">{String(fields.description)}</p> : null}
    {properties.length > 0 && <dl className="grid gap-3 sm:grid-cols-2">{properties.map(([key, value]) => <div key={key}><dt className="text-xs uppercase tracking-wide text-muted-foreground">{key.replace(/_/g, ' ')}</dt><dd className="whitespace-pre-wrap">{typeof value === 'object' ? JSON.stringify(value) : String(value)}</dd></div>)}</dl>}
    {fields.content_json && typeof fields.content_json === 'object' ? <DocEditor content={fields.content_json as Record<string, unknown>} editable={false} artefactHref={(type, _id, label) => docUrl(projectPrefix, type as DocType, label)} /> : html ? <p className="whitespace-pre-wrap">{html}</p> : null}
    {steps.length > 0 && <TcsArteTable rows={steps} editable={false} onChange={() => {}} />}
    {sections.map(section => <ArchivedSection key={section.id} section={section} />)}
    {items.length > 0 && <SectionCard title="Suite membership">{items.map(item => <p key={item.id}>{item.test_case ? `${item.test_case.tc_id} · ${item.test_case.title}` : 'Test case unavailable'}</p>)}</SectionCard>}
    {attachments.length > 0 && <SectionCard title="Approved files">{attachments.map(file => <button key={file.id} type="button" disabled={downloadId === file.id} onClick={() => download(file)} className={`${actionButtonClass} block`}>Download {file.original_filename}</button>)}</SectionCard>}
  </div>
}

function ArchivedSection({ section }: { section: DocumentSection }) {
  return <section><h4>{section.title}</h4><p className="whitespace-pre-wrap">{section.content}</p>{section.child_sections?.map(child => <ArchivedSection key={child.id} section={child} />)}</section>
}
