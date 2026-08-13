import { useState, useMemo } from 'react'
import { useParams, Link, useNavigate } from 'react-router'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  type TcsRow,
  projectsApi,
  testCasesApi,
  usersApi,
} from '../api/client'
import { TcsArteTable } from '../components/TcsArteTable'
import { DocumentLinksPanel } from '../components/DocumentLinksPanel'
import DocumentActivityPanel from '../components/DocumentActivityPanel'
import { normalizeTcsRows } from '../utils/tcs'
import { Pencil, UserCheck, UserCog, Trash2 } from 'lucide-react'
import { formatDateTime } from '../test/date-utils'
import { docEditUrl } from '../types/doc'
import { DocEditor } from '../components/editor'
import { docRegistryListUrl } from '../lib/docRegistryParams'
import DocDetailShell, { MetaItem, SectionCard } from '../components/DocDetailShell'
import { useAuth } from '../contexts/AuthContext'
import { useToast } from '../components/useToast'
import BudRunLink from '../components/BudRunLink'
import {
  membershipLinksForCampaigns,
  membershipLinksForSuites,
} from '../lib/membershipLinks'

function normalizeSteps(steps: unknown): TcsRow[] {
  return normalizeTcsRows(steps) as TcsRow[]
}

function resolveUserName(users: Array<{ id: number; full_name: string }> | undefined, userId: number | null) {
  if (!userId) return 'Unassigned'
  return users?.find((u) => u.id === userId)?.full_name || `User #${userId}`
}

function ExecutionBadge({ status }: { status: string }) {
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

export default function TestCaseDetail({ resolvedId }: { resolvedId?: number } = {}) {
  const { user } = useAuth()
  const { prefix, itemId } = useParams<{ prefix: string; itemId: string }>()
  const tcId = resolvedId || parseInt(itemId || '0')
  const queryClient = useQueryClient()
  const toast = useToast()
  const navigate = useNavigate()



  const { data: testCase, isLoading, error } = useQuery({
    queryKey: ['testCase', tcId],
    queryFn: () => testCasesApi.get(tcId),
    enabled: !!tcId,
  })

  const { data: project } = useQuery({
    queryKey: ['project', testCase?.project_id],
    queryFn: () => projectsApi.get(testCase!.project_id),
    enabled: !!testCase?.project_id,
  })

  const { data: users } = useQuery({
    queryKey: ['users'],
    queryFn: usersApi.list,
    enabled: user?.role === 'admin' || user?.role === 'maintainer',
  })

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

  const markReviewedMutation = useMutation({
    mutationFn: (reviewedById: number) => testCasesApi.setReviewed(tcId, reviewedById),
    onSuccess: (updated) => {
      queryClient.setQueryData(['testCase', tcId], (old: unknown) => {
        if (old && typeof old === 'object') {
          return { ...(old as object), ...(updated as object) }
        }
        return updated
      })
      queryClient.invalidateQueries({ queryKey: ['testCase', tcId] })
      queryClient.invalidateQueries({ queryKey: ['artefactActivity', 'test-case', tcId] })
      toast.notify('Test case marked as reviewed', 'success')
    },
    onError: (err: unknown) => {
      toast.failed('Marking the test case reviewed', err)
    },
  })

  const markApprovedMutation = useMutation({
    mutationFn: (approvedById: number) => testCasesApi.setApproved(tcId, approvedById),
    onSuccess: (updated) => {
      queryClient.setQueryData(['testCase', tcId], (old: unknown) => {
        if (old && typeof old === 'object') {
          return { ...(old as object), ...(updated as object) }
        }
        return updated
      })
      queryClient.invalidateQueries({ queryKey: ['testCase', tcId] })
      queryClient.invalidateQueries({ queryKey: ['artefactActivity', 'test-case', tcId] })
      toast.notify('Test case approved', 'success')
    },
    onError: (err: unknown) => {
      toast.failed('Approving the test case', err)
    },
  })

  const [deleteConfirm, setDeleteConfirm] = useState(false)
  const deleteMutation = useMutation({
    mutationFn: () => testCasesApi.delete(tcId),
    onSuccess: () => {
      if (!testCase) return
      queryClient.invalidateQueries({ queryKey: ['testCases', testCase.project_id] })
      queryClient.invalidateQueries({ queryKey: ['all-docs', prefix] })
      queryClient.invalidateQueries({ queryKey: ['project', testCase.project_id] })
      queryClient.invalidateQueries({ queryKey: ['artefactActivity', 'test-case', tcId] })
      toast.notify('Test case deleted', 'success')
      setTimeout(() => {
        navigate(docRegistryListUrl(prefix!, 'TC'))
      }, 800)
    },
    onError: (err: unknown) => {
      toast.failed('Deleting the test case', err)
      setDeleteConfirm(false)
    },
  })

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
  const canEditDocs = user?.role === 'admin' || user?.role === 'maintainer'

  return (
    <>
    <DocDetailShell
      projectPrefix={projectPrefix}
      docType="TC"
      docCode={testCase.tc_id}
      title={testCase.title}
      status={testCase.status}
      actions={canEditDocs ? (
        <div className="flex items-center gap-2">
          <button
            onClick={() => navigate(`${editUrl}?type=TC`)}
            className="inline-flex items-center px-4 py-2 bg-primary text-white rounded-md hover:bg-primary/90 transition-colors text-sm"
          >
            <Pencil className="h-4 w-4 mr-2" />
            Edit
          </button>
          {!deleteConfirm ? (
            <button
              type="button"
              onClick={() => setDeleteConfirm(true)}
              className="inline-flex items-center gap-1.5 px-4 py-2 border border-red-300 text-red-600 rounded-md hover:bg-red-50 text-sm"
            >
              <Trash2 className="h-4 w-4" />
              Delete
            </button>
          ) : (
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground">Are you sure?</span>
              <button
                onClick={() => { setDeleteConfirm(false); deleteMutation.mutate(); }}
                disabled={deleteMutation.isPending}
                className="inline-flex items-center px-3 py-1.5 bg-red-600 text-white rounded-md hover:bg-red-700 text-sm disabled:opacity-50"
              >
                {deleteMutation.isPending ? 'Deleting...' : 'Delete'}
              </button>
              <button onClick={() => setDeleteConfirm(false)} className="px-3 py-1.5 border border-input rounded-md text-sm hover:bg-accent/40">
                Cancel
              </button>
            </div>
          )}
        </div>
      ) : undefined}
      rightRail={
        <>
          <SectionCard title="Last Execution">
            {testCase.last_execution_status ? (
              <div className="space-y-4">
                <div>
                  <div className="text-xs uppercase tracking-wide text-muted-foreground mb-1">Result</div>
                  <ExecutionBadge status={testCase.last_execution_status} />
                </div>
                <MetaItem
                  label="Executed"
                  value={testCase.last_executed_at ? formatDateTime(testCase.last_executed_at) : 'Unknown'}
                />
                <MetaItem
                  label="Bud Run"
                  value={<BudRunLink runId={testCase.last_bud_run_id} />}
                />
                {testCase.last_execution_comment && (
                  <div>
                    <div className="text-xs uppercase tracking-wide text-muted-foreground mb-1">Comment</div>
                    <div className="text-sm text-foreground whitespace-pre-wrap">{testCase.last_execution_comment}</div>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No synced execution has been recorded for this test case yet.</p>
            )}
          </SectionCard>

          <SectionCard title="Review">
            <div className="space-y-3">
              <div>
                <div className="text-xs uppercase tracking-wide text-muted-foreground mb-1">Reviewer</div>
                <div className="text-sm text-foreground">{resolveUserName(users, testCase.reviewer_id)}</div>
              </div>
              <div>
                <div className="text-xs uppercase tracking-wide text-muted-foreground mb-1">Reviewed by</div>
                <div className="text-sm text-foreground">{resolveUserName(users, testCase.reviewed_by_id)}</div>
                {testCase.reviewed_at && <div className="text-xs text-muted-foreground mt-0.5">{formatDateTime(testCase.reviewed_at)}</div>}
              </div>
              <button
                disabled={!canEditDocs || !testCase.reviewer_id || markReviewedMutation.isPending}
                onClick={() => testCase.reviewer_id && markReviewedMutation.mutate(testCase.reviewer_id)}
                className="w-full inline-flex items-center justify-center px-3 py-1.5 rounded-md bg-amber-500/90 text-white text-xs font-medium hover:bg-amber-500 disabled:opacity-50"
              >
                <UserCheck className="h-3.5 w-3.5 mr-1" />
                Mark Reviewed
              </button>
            </div>
          </SectionCard>

          <SectionCard title="Approval">
            <div className="space-y-3">
              <div>
                <div className="text-xs uppercase tracking-wide text-muted-foreground mb-1">Approver</div>
                <div className="text-sm text-foreground">{resolveUserName(users, testCase.approver_id)}</div>
              </div>
              <div>
                <div className="text-xs uppercase tracking-wide text-muted-foreground mb-1">Approved by</div>
                <div className="text-sm text-foreground">{resolveUserName(users, testCase.approved_by_id)}</div>
                {testCase.approved_at && <div className="text-xs text-muted-foreground mt-0.5">{formatDateTime(testCase.approved_at)}</div>}
              </div>
              <button
                disabled={!canEditDocs || !testCase.approver_id || markApprovedMutation.isPending}
                onClick={() => testCase.approver_id && markApprovedMutation.mutate(testCase.approver_id)}
                className="w-full inline-flex items-center justify-center px-3 py-1.5 rounded-md bg-emerald-600 text-white text-xs font-medium hover:bg-emerald-500 disabled:opacity-50"
              >
                <UserCog className="h-3.5 w-3.5 mr-1" />
                Mark Approved
              </button>
            </div>
          </SectionCard>

          <SectionCard title="Metadata">
            <div className="space-y-4">
              <MetaItem label="Created" value={formatDateTime(testCase.created_at) + ' ago'} />
              <MetaItem label="Updated" value={formatDateTime(testCase.updated_at) + ' ago'} />
            </div>
          </SectionCard>
        </>
      }
    >
      {(testCase.content_json as Record<string, unknown> | null) ? (
        <SectionCard title="Content">
          <DocEditor
            content={testCase.content_json as Record<string, unknown>}
            editable={false}
            minHeight="min-h-[120px]"
            className="border-0"
          />
        </SectionCard>
      ) : testCase.description ? (
        <SectionCard title="Description">
          <p className="text-foreground whitespace-pre-wrap">{testCase.description}</p>
        </SectionCard>
      ) : null}

      {tcsRows.length > 0 && (
        <TcsArteTable rows={tcsRows} onChange={() => {}} editable={false} />
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
    </>
  )
}
