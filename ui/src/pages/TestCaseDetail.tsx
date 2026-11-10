import { finishArtefactDeletion } from '../lib/refreshProjectViews'
import { useState, useMemo } from 'react'
import ArtefactTags from '../components/ArtefactTags'
import { useParams, Link, useNavigate } from 'react-router'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  type TcsRow,
  projectsApi,
  testCasesApi,
  } from '../api/client'
import { TcsArteTable } from '../components/TcsArteTable'
import { DocumentLinksPanel } from '../components/DocumentLinksPanel'
import DocumentActivityPanel from '../components/DocumentActivityPanel'
import { normalizeTcsRows } from '../utils/tcs'
import { Pencil, Trash2 } from 'lucide-react'
import { formatDateTime } from '../lib/dateTime'
import { docEditUrl, docUrl, type DocType } from '../types/doc'
import { docRegistryListUrl } from '../lib/docRegistryParams'
import DocDetailShell, { MetaItem, SectionCard } from '../components/DocDetailShell'
import { useAuth } from '../contexts/AuthContext'
import { useToast } from '../components/useToast'
import BudRunLink from '../components/BudRunLink'
import {
  membershipLinksForCampaigns,
  membershipLinksForSuites,
} from '../lib/membershipLinks'
import { useProjectPermissions, useRowActions } from '../hooks/useProjectPermissions'
import { useParameterValues } from '../hooks/useParameterValues'
import { useArtefactLabels } from '../hooks/useArtefactLabels'
import ConfirmDelete from '../components/ConfirmDelete'
import WorkflowPanel from '../components/WorkflowPanel'
import { InfoSection } from '../components/DocumentInfoPanel'
import { CommentableDocEditor, CommentsColumn, ReviewCommentsProvider } from '../components/comments/ReviewComments'
import { useDocumentWorkflow } from '../hooks/useDocumentWorkflow'
import { useSignOffPeople } from '../hooks/useSignOff'

function normalizeSteps(steps: unknown): TcsRow[] {
  return normalizeTcsRows(steps) as TcsRow[]
}

function ExecutionBadge({ status }: Readonly<{ status: string }>) {
  const colors: Record<string, string> = {
    Passed: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400',
    Failed: 'bg-red-500/10 text-red-700 dark:text-red-400',
    Skipped: 'bg-slate-500/10 text-slate-700 dark:text-slate-400',
  }
  return (
    <span className={`px-2 py-1 rounded-full text-xs font-medium ${colors[status] || 'bg-muted text-muted-foreground'}`}>
      {status}
    </span>
  )
}

export default function TestCaseDetail({
  resolvedId,
  allowedActions,
}: { resolvedId?: number; allowedActions?: string[] } = {}) {
  const { user } = useAuth()
  const { prefix, itemId } = useParams<{ prefix: string; itemId: string }>()
  const { can } = useProjectPermissions(prefix)
  const parameterValues = useParameterValues(prefix)
  const tcId = resolvedId || Number.parseInt(itemId || '0')
  const workflow = useDocumentWorkflow('test-case', tcId)
  const queryClient = useQueryClient()
  const toast = useToast()
  const navigate = useNavigate()



  const { data: testCase, isLoading, error } = useQuery({
    queryKey: ['testCase', tcId],
    queryFn: () => testCasesApi.get(tcId),
    enabled: !!tcId,
  })

  const artefactLabels = useArtefactLabels(prefix, testCase?.content_json)
  const { data: project } = useQuery({
    queryKey: ['project', testCase?.project_id],
    queryFn: () => projectsApi.get(testCase!.project_id),
    enabled: !!testCase?.project_id,
  })

  const users = useSignOffPeople(testCase?.project_id, user?.role === 'admin')

  const derivedMembershipLinks = useMemo(() => {
    if (!testCase) return []
    return [
      ...membershipLinksForSuites(
        testCase.suite_memberships,
        'TC',
        testCase.id,
        testCase.project_id,
      ),
      ...membershipLinksForCampaigns(
        testCase.campaign_memberships,
        'TC',
        testCase.id,
        testCase.project_id,
      ),
    ]
  }, [testCase])


  const [deleteConfirm, setDeleteConfirm] = useState(false)
  const deleteMutation = useMutation({
    mutationFn: () => testCasesApi.delete(tcId),
    onSuccess: () => {
      if (!testCase) return
      toast.notify('Test case deleted', 'success')
      setTimeout(() => {
        finishArtefactDeletion(queryClient, { prefix, projectId: testCase.project_id, detailKey: 'testCase', artefactType: 'test-case', recordId: tcId, kind: 'test-cases', docId: testCase.tc_id }, () => navigate(docRegistryListUrl(prefix!, 'TC')))
      }, 800)
    },
    onError: (err: unknown) => {
      toast.failed('Deleting the test case', err)
      setDeleteConfirm(false)
    },
  })

  const rowAllows = useRowActions(prefix, 'TC', testCase?.tc_id, allowedActions)

  if (isLoading) {
    return <div className="flex items-center justify-center h-64 text-muted-foreground">Loading...</div>
  }

  if (error || !testCase) {
    return (
      <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-6 text-center">
        <h3 className="text-lg font-medium text-destructive">Test Case Not Found</h3>
        <Link to={docRegistryListUrl(prefix!, 'TC')} className="mt-4 inline-block text-primary hover:text-primary/80">
          &larr; Back to Test Cases
        </Link>
      </div>
    )
  }

  const projectPrefix = project?.prefix || ''
  const tcsRows = normalizeSteps(testCase.steps)
  const editUrl = docEditUrl(projectPrefix, 'TC', testCase.tc_id)
  const canEditDocs = can('edit', 'TC')
  const showEdit = canEditDocs && rowAllows('edit') && workflow.data?.actions?.edit_current === true
  const showDelete = canEditDocs && can('delete', 'TC') && rowAllows('delete')

  return (
    <ReviewCommentsProvider artefactType="test-case" artefactId={tcId} projectPrefix={projectPrefix} projectId={testCase.project_id}>
    <DocDetailShell
      projectPrefix={projectPrefix}
      docType="TC"
      docCode={testCase.tc_id}
      title={testCase.title}
      status={testCase.status}
      actions={showEdit || showDelete ? (
        <div className="flex items-center gap-2">
          {showEdit && (
          <button
            onClick={() => navigate(`${editUrl}?type=TC`)}
            className="inline-flex items-center px-4 py-2 bg-primary text-white rounded-md hover:bg-primary/90 transition-colors text-sm"
          >
            <Pencil className="h-4 w-4 mr-2" />
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
      info={<>
        <InfoSection title="Workflow state">
          <WorkflowPanel artefactType="test-case" artefactId={tcId} projectPrefix={projectPrefix} projectId={testCase.project_id} layout="panel" />
        </InfoSection>
        <InfoSection title="Last Execution">
          {testCase.last_execution_status ? (
            <div className="grid grid-cols-2 gap-x-4 gap-y-3">
              <MetaItem label="Result" value={<ExecutionBadge status={testCase.last_execution_status} />} />
              <MetaItem
                label="Executed"
                value={testCase.last_executed_at ? formatDateTime(testCase.last_executed_at) : 'Unknown'}
              />
              <div className="col-span-2">
                <MetaItem
                  label="Bud Run"
                  value={<BudRunLink runId={testCase.last_bud_run_id} source={{ source_kind: 'test-case', source_id: testCase.id }} />}
                />
              </div>
              {testCase.last_execution_comment && (
                <div className="col-span-2">
                  <div className="text-xs uppercase tracking-wide text-muted-foreground mb-1">Comment</div>
                  <div className="text-sm text-foreground whitespace-pre-wrap">{testCase.last_execution_comment}</div>
                </div>
              )}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">No synced execution has been recorded for this test case yet.</p>
          )}
        </InfoSection>
        <InfoSection title="Metadata">
          <div className="grid grid-cols-2 gap-x-4 gap-y-3">
            <div className="col-span-2">
              <MetaItem label="Origin" value={<ArtefactTags type="test-case" id={tcId} projectId={testCase.project_id} canEdit={showEdit} origin={testCase.visibility === 'customer' ? 'Customer' : 'Internal'} />} />
            </div>
            <MetaItem label="ID" value={testCase.tc_id} mono />
            <MetaItem label="Project" value={project ? `${project.prefix} · ${project.name}` : `#${testCase.project_id}`} />
            <MetaItem label="Created" value={formatDateTime(testCase.created_at) + ' ago'} />
            <MetaItem label="Updated" value={formatDateTime(testCase.updated_at) + ' ago'} />
          </div>
        </InfoSection>
      </>}
      comments={<CommentsColumn />}
    >
      {!!testCase.content_json && (
        <SectionCard title="Content">
          <CommentableDocEditor
            content={testCase.content_json as Record<string, unknown>}
            editable={false}
            userMentionItems={users.map(person => ({ id: person.id, label: person.full_name, user: person }))}
            parameterHref={prefix ? `/projects/${prefix}/parameters` : undefined} parameterValues={parameterValues} artefactLabels={artefactLabels}
            artefactHref={(type, _id, label) => docUrl(prefix, type as DocType, label)}
            minHeight="min-h-[120px]"
            className="border-0"
          />
        </SectionCard>
      )}
      {!testCase.content_json && !!testCase.description && (
        <SectionCard title="Description">
          <p className="text-foreground whitespace-pre-wrap">{testCase.description}</p>
        </SectionCard>
      )}

      {tcsRows.length > 0 && (
        <TcsArteTable userMentionItems={users.map(person => ({ id: person.id, label: person.full_name, user: person }))} rows={tcsRows} onChange={() => {}} editable={false} parameterHref={prefix ? `/projects/${prefix}/parameters` : undefined} parameterValues={parameterValues} />
      )}

      <DocumentActivityPanel artefactType="test-case" artefactId={tcId} />

      {project && (
        <DocumentLinksPanel
          projectId={testCase.project_id}
          projectPrefix={project.prefix}
          sourceType="TC"
          sourceId={testCase.id}
          sourceDocId={testCase.tc_id}
          derivedLinks={derivedMembershipLinks}
        />
      )}

    </DocDetailShell>
    </ReviewCommentsProvider>
  )
}
