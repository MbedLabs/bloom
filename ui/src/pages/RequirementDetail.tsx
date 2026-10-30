import { finishArtefactDeletion } from '../lib/refreshProjectViews'
import { useState, useMemo } from 'react'
import ArtefactTags from '../components/ArtefactTags'
import { useParams, Link, useNavigate } from 'react-router'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { requirementsApi, projectsApi } from '../api/client'
import { ExternalLink, ChevronRight, Trash2 } from 'lucide-react'
import { formatDateTime } from '../lib/dateTime'
import { docEditUrl, docUrl, type DocType } from '../types/doc'
import { docRegistryListUrl } from '../lib/docRegistryParams'
import DocumentActivityPanel from '../components/DocumentActivityPanel'
import DocDetailShell, { StatusBadge, MetaItem, SectionCard } from '../components/DocDetailShell'
import { DocumentLinksPanel } from '../components/DocumentLinksPanel'
import { useAuth } from '../contexts/AuthContext'
import { useToast } from '../components/useToast'
import {
  membershipLinksForCampaigns,
  membershipLinksForSuites,
} from '../lib/membershipLinks'
import { useProjectPermissions, useRowActions } from '../hooks/useProjectPermissions'
import { useParameterValues } from '../hooks/useParameterValues'
import { useArtefactLabels } from '../hooks/useArtefactLabels'
import BudRunLink from '../components/BudRunLink'
import ConfirmDelete from '../components/ConfirmDelete'
import WorkflowPanel from '../components/WorkflowPanel'
import { CommentableDocEditor, CommentsColumn, ReviewCommentsProvider } from '../components/comments/ReviewComments'
import { useDocumentWorkflow } from '../hooks/useDocumentWorkflow'
import { useSignOffPeople } from '../hooks/useSignOff'

function TypeBadge({ reqType }: Readonly<{ reqType: string }>) {
  return (
    <span className="px-2 py-1 rounded-full text-xs font-medium bg-purple-500/10 text-purple-700 dark:text-purple-400">
      {reqType}
    </span>
  )
}

function OriginBadge({ origin }: Readonly<{ origin: string }>) {
  const colors: Record<string, string> = {
    Internal: 'bg-slate-500/10 text-slate-700 dark:text-slate-400',
    Customer: 'bg-sky-500/10 text-sky-700 dark:text-sky-400',
    Compliance: 'bg-violet-500/10 text-violet-700 dark:text-violet-400',
    Regulatory: 'bg-rose-500/10 text-rose-700 dark:text-rose-400',
    Legal: 'bg-indigo-500/10 text-indigo-700 dark:text-indigo-400',
    Business: 'bg-amber-500/10 text-amber-700 dark:text-amber-400',
    Technical: 'bg-violet-500/10 text-violet-700 dark:text-violet-400',
  }
  return (
    <span className={`px-2 py-1 rounded-full text-xs font-medium ${colors[origin] || 'bg-gray-500/10 text-gray-700 dark:text-gray-400'}`}>
      {origin}
    </span>
  )
}

function RunStatusBadge({ status }: Readonly<{ status: string }>) {
  const colors: Record<string, string> = {
    Passed: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400',
    Failed: 'bg-red-500/10 text-red-700 dark:text-red-400',
    Running: 'bg-blue-500/10 text-blue-700 dark:text-blue-400',
    Pending: 'bg-gray-500/10 text-gray-700 dark:text-gray-400',
  }
  return (
    <span className={`px-2 py-1 rounded-full text-xs font-medium ${colors[status] || 'bg-gray-500/10 text-gray-700 dark:text-gray-400'}`}>
      {status}
    </span>
  )
}

export default function RequirementDetail({
  resolvedId,
  allowedActions,
}: { resolvedId?: number; allowedActions?: string[] } = {}) {
  const { user } = useAuth()
  const { prefix, itemId } = useParams<{ prefix: string; itemId: string }>()
  const { can } = useProjectPermissions(prefix)
  const parameterValues = useParameterValues(prefix)
  const reqId = resolvedId || Number.parseInt(itemId || '0')
  const workflow = useDocumentWorkflow('requirement', reqId)
  const queryClient = useQueryClient()
  const toast = useToast()
  const navigate = useNavigate()

  const { data: requirement, isLoading, error } = useQuery({
    queryKey: ['requirement', reqId],
    queryFn: () => requirementsApi.get(reqId),
    enabled: !!reqId,
  })

  const artefactLabels = useArtefactLabels(prefix, requirement?.content_json)
  const { data: project } = useQuery({
    queryKey: ['project', requirement?.project_id],
    queryFn: () => projectsApi.get(requirement!.project_id),
    enabled: !!requirement?.project_id,
  })

  const projectPrefix = project?.prefix || ''

  const derivedMembershipLinks = useMemo(() => {
    if (!requirement) return []
    return [
      ...membershipLinksForSuites(
        requirement.suite_backlinks,
        'REQ',
        requirement.id,
        requirement.project_id,
      ),
      ...membershipLinksForCampaigns(
        requirement.campaign_backlinks,
        'REQ',
        requirement.id,
        requirement.project_id,
      ),
    ]
  }, [requirement])

  const { data: parentReq } = useQuery({
    queryKey: ['requirement', requirement?.parent_id],
    queryFn: () => requirementsApi.get(requirement!.parent_id!),
    enabled: !!requirement?.parent_id,
  })



  const users = useSignOffPeople(requirement?.project_id, user?.role === 'admin')

  const [deleteConfirm, setDeleteConfirm] = useState(false)
  const deleteMutation = useMutation({
    mutationFn: () => requirementsApi.delete(reqId),
    onSuccess: () => {
      if (!requirement) return
      toast.notify('Requirement deleted', 'success')
      setTimeout(() => {
        finishArtefactDeletion(queryClient, { prefix, projectId: requirement.project_id, detailKey: 'requirement', artefactType: 'requirement', recordId: reqId, kind: 'requirements', docId: requirement.req_id }, () => navigate(docRegistryListUrl(prefix!, 'REQ')))
      }, 800)
    },
    onError: (err: unknown) => {
      toast.failed('Deleting the requirement', err)
      setDeleteConfirm(false)
    },
  })


  const rowAllows = useRowActions(prefix, 'REQ', requirement?.req_id, allowedActions)

  if (isLoading) {
    return <div className="flex items-center justify-center h-64 text-muted-foreground">Loading...</div>
  }

  if (error || !requirement) {
    return (
      <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-6 text-center">
        <h3 className="text-lg font-medium text-destructive">Requirement Not Found</h3>
        <Link to={docRegistryListUrl(prefix!, 'REQ')} className="mt-4 inline-block text-primary hover:text-primary/80">
          &larr; Back to Requirements
        </Link>
      </div>
    )
  }

  const canEditDocs = can('edit', 'REQ')
  const showEdit = canEditDocs && rowAllows('edit') && workflow.data?.actions?.edit_current === true
  const showDelete = canEditDocs && can('delete', 'REQ') && rowAllows('delete')

  return (
    <ReviewCommentsProvider artefactType="requirement" artefactId={reqId} projectPrefix={projectPrefix} projectId={requirement.project_id}>
    <DocDetailShell
      projectPrefix={projectPrefix}
      docType="REQ"
      docCode={requirement.req_id}
      title={requirement.title}
      status={requirement.status}
      priority={requirement.priority}
      actions={showEdit || showDelete ? (
        <div className="flex items-center gap-2">
          {showEdit && (
          <button
            onClick={() => navigate(docEditUrl(projectPrefix, 'REQ', requirement.req_id))}
            className="inline-flex items-center px-4 py-2 bg-primary text-white rounded-md hover:bg-primary/90 transition-colors text-sm"
          >
            Edit
          </button>
          )}
          {showDelete && (!deleteConfirm ? (
            <button
              type="button"
              onClick={() => setDeleteConfirm(true)}
              className="inline-flex items-center gap-1.5 px-4 py-2 border border-red-300 text-red-600 rounded-md hover:bg-red-50 text-sm"
            >
              <Trash2 className="h-4 w-4" />
              Delete
            </button>
          ) : (
            <ConfirmDelete
              pending={deleteMutation.isPending}
              onConfirm={() => { setDeleteConfirm(false); deleteMutation.mutate(); }}
              onCancel={() => setDeleteConfirm(false)}
            />
          ))}
        </div>
      ) : undefined}
      review={<WorkflowPanel artefactType="requirement" artefactId={reqId} projectPrefix={projectPrefix} projectId={requirement.project_id} layout="bar" />}
      comments={<CommentsColumn />}
    >
      {requirement.parent_id && parentReq && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <span className="text-sm text-blue-600 font-medium">Parent Requirement: </span>
          <Link to={docUrl(projectPrefix, 'REQ', parentReq.req_id)} className="text-sm text-primary hover:text-primary/80 font-medium">
            {parentReq.req_id} ({parentReq.title}) →
          </Link>
        </div>
      )}

      {(requirement.content_json as Record<string, unknown> | null) ? (
        <SectionCard title="Content">
          <CommentableDocEditor
            content={requirement.content_json as Record<string, unknown>}
            editable={false}
            userMentionItems={users.map(person => ({ id: person.id, label: person.full_name, user: person }))}
            parameterHref={prefix ? `/projects/${prefix}/parameters` : undefined} parameterValues={parameterValues} artefactLabels={artefactLabels}
            artefactHref={(type, _id, label) => docUrl(prefix, type as DocType, label)}
            minHeight="min-h-[120px]"
            className="border-0"
          />
        </SectionCard>
      ) : (
        <SectionCard title="Description">
          <p className="text-foreground whitespace-pre-wrap">
            {requirement.description || 'No description provided.'}
          </p>
        </SectionCard>
      )}

      {requirement.children && requirement.children.length > 0 && (
        <SectionCard title="Child Requirements" actions={<span className="text-sm text-muted-foreground">{requirement.children.length}</span>}>
          <div className="divide-y divide-border -m-6">
            {requirement.children.map((child) => (
              <Link
                key={child.id}
                to={docUrl(projectPrefix, 'REQ', child.req_id)}
                className="flex items-center justify-between px-6 py-4 hover:bg-accent/50 transition-colors"
              >
                <div className="flex items-center">
                  <ChevronRight className="h-4 w-4 text-muted-foreground mr-3" />
                  <div>
                    <span className="font-mono text-sm text-primary mr-2">{child.req_id}</span>
                    <span className="text-foreground">{child.title}</span>
                  </div>
                </div>
                <StatusBadge status={child.status} />
              </Link>
            ))}
          </div>
        </SectionCard>
      )}

      {requirement.linked_test_runs && requirement.linked_test_runs.length > 0 && (
        <SectionCard title="Linked Test Runs">
          <div className="overflow-x-auto -mx-6">
            <table className="min-w-full divide-y divide-border">
              <thead className="bg-muted/50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Test Run</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Status</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Created</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Link</th>
                </tr>
              </thead>
              <tbody className="bg-card divide-y divide-border">
                {requirement.linked_test_runs.map((tr) => (
                  <tr key={tr.id} className="hover:bg-accent/50">
                    <td className="px-6 py-4 text-sm font-medium text-foreground">
                      {tr.test_run_name || `Test Run #${tr.test_run_id}`}
                    </td>
                    <td className="px-6 py-4 text-sm">
                      {tr.status ? <RunStatusBadge status={tr.status} /> : '-'}
                    </td>
                    <td className="px-6 py-4 text-sm text-muted-foreground">
                      {formatDateTime(tr.created_at)} ago
                    </td>
                    <td className="px-6 py-4 text-sm">
                      {tr.teststation_url ? (
                        <a
                          href={tr.teststation_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center text-primary hover:text-primary/80"
                        >
                          <ExternalLink className="h-4 w-4 mr-1" />
                          Open
                        </a>
                      ) : (
                        <span className="text-muted-foreground">-</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </SectionCard>
      )}


      <DocumentActivityPanel artefactType="requirement" artefactId={reqId} />

      <DocumentLinksPanel
        projectId={requirement.project_id}
        projectPrefix={projectPrefix}
        sourceType="REQ"
        sourceId={reqId}
        sourceDocId={requirement.req_id}
        derivedLinks={derivedMembershipLinks}
      />
      <>
          <SectionCard title="Metadata">
            <div className="space-y-4">
              <div>
                <div className="text-xs uppercase tracking-wide text-muted-foreground mb-1">Type</div>
                <TypeBadge reqType={requirement.req_type} />
              </div>
              <div>
                <div className="text-xs uppercase tracking-wide text-muted-foreground mb-1">Origin</div>
                <div className="flex flex-wrap items-center gap-1.5">
                  <OriginBadge origin={requirement.req_origin} />
                  <ArtefactTags type="requirement" id={reqId} projectId={requirement.project_id} canEdit={showEdit} />
                </div>
              </div>
              <MetaItem label="Created" value={formatDateTime(requirement.created_at) + ' ago'} />
              <MetaItem label="Updated" value={formatDateTime(requirement.updated_at) + ' ago'} />
            </div>
          </SectionCard>

          {requirement.linked_test_runs?.length > 0 && (
            <SectionCard title="Test runs">
              <ul className="space-y-2">
                {requirement.linked_test_runs.map((run) => (
                  <li key={run.id} className="text-sm">
                    <BudRunLink runId={run.test_run_id} source={{ source_kind: 'requirement', source_id: requirement.id }} label={run.test_run_name || undefined} />
                    <div className="text-xs text-muted-foreground">{run.status || 'Status not recorded'}</div>
                  </li>
                ))}
              </ul>
              <p className="text-xs text-muted-foreground mt-3">
                A run opens in Bud, where its report can be downloaded.
              </p>
            </SectionCard>
          )}
      </>
    </DocDetailShell>
    </ReviewCommentsProvider>
  )
}
