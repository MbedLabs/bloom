import SelectField from '../components/SelectField'
import { OpenThreads } from '../components/comments/ReviewComments'
import { refreshProjectViews, finishArtefactDeletion } from '../lib/refreshProjectViews'
import { useState, useCallback, useEffect, useMemo } from 'react'
import TagPicker from '../components/TagPicker'
import { useParams, useSearchParams, useNavigate, useLocation, Link } from 'react-router'
import { useMutation, useQuery, useQueryClient, type QueryClient } from '@tanstack/react-query'
import { ArrowLeft, PanelRightOpen, PanelRightClose, Trash2 } from 'lucide-react'
import { DocEditor } from '../components/editor'
import { TcsArteTable } from '../components/TcsArteTable'
import { createDefaultTcRows, normalizeTcsRows, type TcsRow } from '../utils/tcs'
import {
  docsApi, projectsApi, requirementsApi, testCasesApi, designsApi,
  risksApi, changesApi, testConceptsApi, documentsApi, usersApi, projectVariablesApi,
  extractApiErrorMessage,
  type ArtefactVisibility,
  searchApi,
} from '../api/client'
import type { DocType } from '../types/doc'
import {
  DOC_CONFIGS,
  DOC_TYPE_LABELS,
  DOC_TYPE_COLORS,
  DOC_TYPE_SLUGS,
  docUrl,
  isDocTagHostType,
  isDocTagTargetAllowed,
  normalizeDocTypeParam,
  isWorkflowControlledDocType,
} from '../types/doc'
import { useToast } from '../components/useToast'
import { docRegistryBackUrl, docRegistryListLabel } from '../lib/docRegistryParams'
import {
  dedicatedListUrl,
  isServerAssignedDocIdOnCreate,
  usesDocumentEditor,
} from './docCreateIdPolicy'
import { useProjectPermissions } from '../hooks/useProjectPermissions'
import { useAuth } from '../contexts/AuthContext'
import { useParameterValues } from '../hooks/useParameterValues'
import { useArtefactLabels } from '../hooks/useArtefactLabels'
import { useDocumentWorkflow } from '../hooks/useDocumentWorkflow'

/** The statuses offered by the status picker of the document form. */
function statusChoicesFor(draftOnly: boolean, external: boolean, editMode: boolean, statusOptions: readonly string[], editStatus: string, firstStatus: string): readonly string[] {
  if (draftOnly) return ['Draft']
  if (!external) return statusOptions
  if (!editMode) return [firstStatus]
  return [...new Set([editStatus, ...(statusOptions.includes('Draft') ? ['Draft'] : [])])]
}

/** Label of the save button. */
function saveLabel(saved: boolean, pending: boolean): string {
  if (saved) return 'Saved'
  return pending ? 'Saving...' : 'Save'
}

function artefactActivityTypeForDocType(docType: DocType): string | null {
  if (docType === 'REQ') return 'requirement'
  if (docType === 'TC') return 'test-case'
  if (docType === 'SPEC' || docType === 'PRT' || docType === 'RPT' || docType === 'STD' || docType === 'VIS') return 'document'
  if (docType === 'DES') return 'design'
  if (docType === 'CPT') return 'test-concept'
  if (docType === 'CHG') return 'change'
  if (docType === 'RSK') return 'risk'
  return null
}

function isControlledSharedDocument(docType: DocType): boolean {
  return docType === 'SPEC' || docType === 'PRT' || docType === 'RPT' || docType === 'STD' || docType === 'VIS'
}

function requirementVisibilityFromOrigin(origin: string | undefined): ArtefactVisibility {
  return origin === 'Customer' ? 'customer' : 'internal'
}

function sharedDocumentCreatePayload(
  docType: DocType,
  title: string,
  contentJson: Record<string, unknown> | null,
  contentHtml: string,
  metadata: Record<string, string>,
) {
  const visibility: ArtefactVisibility =
    metadata.visibility === 'customer' ? 'customer' : 'internal'
  return {
    title,
    doc_type: docType,
    description: metadata.description || undefined,
    content_json: contentJson,
    content_html: contentHtml || undefined,
    status: 'Draft',
    visibility,
  }
}

function sharedDocumentUpdatePayload(
  docType: DocType,
  title: string,
  contentJson: Record<string, unknown> | null,
  contentHtml: string,
  metadata: Record<string, string>,
  statusOptions: string[],
) {
  const visibility: ArtefactVisibility =
    metadata.visibility === 'customer' ? 'customer' : 'internal'
  return {
    title,
    doc_type: docType,
    description: metadata.description || null,
    content_json: contentJson,
    content_html: contentHtml || null,
    ...(!isWorkflowControlledDocType(docType) ? { status: metadata.status || statusOptions[0] } : {}),
    visibility,
  }
}

/**
 * The singular query keys the detail pages read one record under.
 *
 * TestCaseDetail uses 'testCase', RequirementDetail 'requirement', and
 * ArtefactDetail one of the artefact kinds; DocumentDetail uses 'document'.
 * A save has to clear whichever of these holds the record just edited, and the
 * id is the same numeric one for all of them, so clearing all of them is both
 * correct and cheap - a key nothing is subscribed to is a no-op.
 */
const DETAIL_QUERY_KEYS = [
  'document',
  'testCase',
  'requirement',
  'design',
  'risk',
  'change',
  'testConcept',
  'defect',
] as const

function invalidateDocumentQueries(
  queryClient: QueryClient,
  projectId: number,
  prefix: string | undefined,
  resolvedDocId?: number,
  kind?: string,
  docIdStr?: string,
) {
  refreshProjectViews(queryClient, { projectId, prefix })
  if (resolvedDocId) {
    for (const key of DETAIL_QUERY_KEYS) {
      void queryClient.invalidateQueries({ queryKey: [key, resolvedDocId] })
    }
  }
  if (prefix && kind && docIdStr) {
    void queryClient.invalidateQueries({ queryKey: ['doc-facade', prefix, kind, docIdStr] })
  }
}

interface DocCreateProps {
  editMode?: boolean
}

export default function DocCreate({ editMode = false }: Readonly<DocCreateProps>) {
  const { prefix, kind, docId: docIdStr } = useParams<{ prefix: string; kind?: string; docId: string }>()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const location = useLocation()
  const queryClient = useQueryClient()
  const toast = useToast()
  const returnTo = (location.state as { returnTo?: string } | null)?.returnTo

  const rawRequestedDocType = normalizeDocTypeParam(searchParams.get('type')) || 'REQ'
  const requestedDocType = rawRequestedDocType in DOC_CONFIGS ? rawRequestedDocType : 'REQ'

  const [title, setTitle] = useState('')
  const [contentJson, setContentJson] = useState<Record<string, unknown> | null>(null)
  const [contentHtml, setContentHtml] = useState('')
  const [tcRows, setTcRows] = useState<TcsRow[]>(() => requestedDocType === 'TC' && !editMode ? createDefaultTcRows() : [])
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [metadata, setMetadata] = useState<Record<string, string>>({})
  const [tagIds, setTagIds] = useState<number[]>([])
  const [outlineOpen, setOutlineOpen] = useState(() => editMode)
  const [headingNumbered, setHeadingNumbered] = useState(true)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [saveSuccess, setSaveSuccess] = useState(false)

  const { data: project, isLoading: isProjectLoading, isError: isProjectError } = useQuery({
    queryKey: ['project-by-prefix', prefix],
    queryFn: () => projectsApi.getByPrefix(prefix!),
    enabled: !!prefix,
  })

  const projectId = project?.id ?? 0
  const projectReady = projectId > 0

  const { data: editDocFacade } = useQuery({
    queryKey: ['doc-facade', prefix, kind, docIdStr],
    queryFn: () => docsApi.get(prefix!, kind!, docIdStr!),
    enabled: editMode && !!prefix && !!kind && !!docIdStr,
  })

  const docType = ((editMode && editDocFacade?.doc_type) || requestedDocType) as DocType
  const config = DOC_CONFIGS[docType]
  const resolvedDocId = editMode ? editDocFacade?.id : undefined
  const workflowType = artefactActivityTypeForDocType(docType)
  const workflow = useDocumentWorkflow(workflowType ?? 'document', editMode ? resolvedDocId : undefined)
  const listBackUrl = prefix ? docRegistryBackUrl(prefix, docType, returnTo ?? null) : '/projects'
  const backNavLabel =
    typeof returnTo === 'string' && returnTo.trim() !== ''
      ? 'Back'
      : `Back to ${docRegistryListLabel(docType)}`
  const { can } = useProjectPermissions(prefix, projectId)
  const parameterValues = useParameterValues(prefix, projectId)
  const artefactLabels = useArtefactLabels(prefix, contentJson)
  const { user } = useAuth()
  const external = user?.role === 'external'
  const rowActions = editMode ? editDocFacade?.allowed_actions : undefined
  const rowAllows = (action: string) => rowActions === undefined || rowActions.includes(action)
  const canEditDocs = can(editMode ? 'edit' : 'create', docType) && (!editMode || rowAllows('edit'))
  const sent: Record<string, string> = external
    ? { ...metadata, visibility: 'customer', ...(docType === 'REQ' ? { req_origin: 'Customer' } : {}) }
    : metadata
  const controlled = isWorkflowControlledDocType(docType)
  const firstStatus = controlled ? 'Draft' : config.statusOptions[0]
  const displayedStatus = editMode && controlled ? workflow.data?.phase ?? editDocFacade?.status ?? '' : metadata.status || firstStatus
  const statusChoices = statusChoicesFor(
    !editMode && (controlled || isControlledSharedDocument(docType)),
    external,
    editMode,
    config.statusOptions,
    editDocFacade?.status ?? firstStatus,
    firstStatus,
  )
  const { data: nextDocId } = useQuery({
    queryKey: ['next-doc-id', prefix, config.typeCode],
    queryFn: () => docsApi.nextDocId(prefix!, config.typeCode),
    enabled: !editMode && !!prefix,
    staleTime: 0,
  })
  const expectedDocIdExample = nextDocId ?? (project ? `${project.prefix}-${config.typeCode}-…` : '')
  const serverAssignedId = !editMode && isServerAssignedDocIdOnCreate(docType)
  const docIdIsValid = editMode || serverAssignedId

  const handleBack = useCallback(() => {
    if (window.history.length > 1) {
      void navigate(-1)
    } else {
      void navigate(listBackUrl)
    }
  }, [navigate, listBackUrl])

  const { data: users } = useQuery({
    queryKey: ['mentionableUsers', projectId],
    queryFn: () => usersApi.listMentionable(projectId),
    enabled: canEditDocs && !!projectId,
  })

  const { data: projectVariables } = useQuery({
    queryKey: ['projectVariables', projectId],
    queryFn: () => projectVariablesApi.list(projectId),
    enabled: can('view', 'parameter') && !!projectId,
  })

  const parameterMentionItems = useMemo(
    () => (projectVariables ?? []).map((variable) => ({
      id: variable.id,
      label: variable.key,
      hint: variable.value,
    })),
    [projectVariables],
  )
  const userMentionItems = useMemo(
    () => (users ?? []).map((u) => ({ id: u.id, label: u.full_name, user: u })),
    [users],
  )

  const artefactSearch = useMemo(() => {
    if (!projectId || !isDocTagHostType(docType)) return undefined
    return async (query: string) => {
      const response = await searchApi.global(query, { projectId, limit: 20 })
      return response.items
        .filter((item) => isDocTagTargetAllowed(docType, item.type))
        .map((item) => ({
          id: item.id,
          label: item.doc_id ?? `${item.type} ${item.id}`,
          hint: item.title,
          docType: item.type,
        }))
    }
  }, [projectId, docType])

  const artefactHref = useCallback(
    (type: string, id: number) => docUrl(prefix, type as DocType, id),
    [prefix],
  )

  const apiForType = useCallback((type: DocType) => {
    const map: Record<string, unknown> = {
      REQ: requirementsApi, TC: testCasesApi, DES: designsApi,
      RSK: risksApi, CHG: changesApi, CPT: testConceptsApi,
      SPEC: documentsApi, PRT: documentsApi, RPT: documentsApi, STD: documentsApi, VIS: documentsApi,
    }
    return map[type]
  }, [])

  useEffect(() => {
    if (!prefix || usesDocumentEditor(docType)) return
    if (editMode) {
      void navigate(
        docIdStr
          ? docUrl(prefix, docType, docIdStr)
          : docRegistryBackUrl(prefix, docType, null),
        { replace: true },
      )
      return
    }
    void navigate(dedicatedListUrl(prefix, docType) ?? docRegistryBackUrl(prefix, docType, null), {
      replace: true,
    })
  }, [docIdStr, docType, editMode, navigate, prefix])

  useEffect(() => {
    if (editMode || !prefix || !usesDocumentEditor(docType)) return
    if (!isServerAssignedDocIdOnCreate(docType)) {
      void navigate(docRegistryBackUrl(prefix, docType, returnTo ?? null), { replace: true })
    }
  }, [docType, editMode, navigate, prefix, returnTo])

  useEffect(() => {
    if (!editMode || !resolvedDocId) return
    if (isControlledSharedDocument(docType) && editDocFacade) {
      setTitle(editDocFacade.title || '')
      setContentJson(editDocFacade.content_json)
      setContentHtml(editDocFacade.content_html || '')
      const meta: Record<string, string> = {}
      if (editDocFacade.description) meta.description = editDocFacade.description
      if (editDocFacade.status) meta.status = editDocFacade.status
      if (editDocFacade.visibility) meta.visibility = editDocFacade.visibility
      setMetadata(meta)
      return
    }
    const api = apiForType(docType) as unknown as { get: (id: number) => Promise<Record<string, unknown>> }
    api.get(resolvedDocId).then((data) => {
      setTitle((data[config.titleField] as string) || '')
      if (data.content_json) setContentJson(data.content_json as Record<string, unknown>)
      if (data.content_html) setContentHtml(data.content_html as string)
      if (docType === 'TC') setTcRows(normalizeTcsRows(data.steps))
      const meta: Record<string, string> = {}
      for (const field of config.fields) {
        if (field.key !== config.titleField && data[field.key] != null) {
          meta[field.key] = String(data[field.key])
        }
      }
      if (typeof data.visibility === 'string') meta.visibility = data.visibility
      if (data.status) meta.status = data.status as string
      setMetadata(meta)
    }).catch(() => {
      setSaveError('Could not load document for editing.')
    })
  }, [editMode, resolvedDocId, docType, config, apiForType, editDocFacade])

  useEffect(() => {
    if (!editMode && docType === 'TC' && tcRows.length === 0) {
      setTcRows(createDefaultTcRows())
    }
  }, [docType, editMode, tcRows.length])

  const createMutation = useMutation({
    mutationFn: async () => {
      const api = apiForType(docType)
      const tag_ids = tagIds
      if (docType === 'TC') {
        return testCasesApi.create({
          project_id: projectId,
          title,
          description: sent.description || undefined,
          preconditions: sent.preconditions || undefined,
          steps: tcRows.length > 0 ? tcRows : undefined,
          status: 'Draft',
          visibility: sent.visibility === 'customer' ? 'customer' : 'internal',
          reviewer_id: sent.reviewer_id ? Number(sent.reviewer_id) : undefined,
          tag_ids,
        })
      }
      if (isControlledSharedDocument(docType)) {
        return documentsApi.create({
          project_id: projectId,
          ...sharedDocumentCreatePayload(docType, title, contentJson, contentHtml, sent),
          tag_ids,
        })
      }
      const payload: Record<string, unknown> = {
        project_id: projectId,
        [config.titleField]: title,
        content_json: contentJson,
        content_html: contentHtml,
        ...sent,
        tag_ids,
      }
      if (docType === 'REQ') {
        payload.visibility = requirementVisibilityFromOrigin(sent.req_origin)
      }
      if (controlled) payload.status = 'Draft'
      if (docType !== 'REQ') delete payload.reviewer_id
      return (api as unknown as { create: (data: Record<string, unknown>) => Promise<Record<string, unknown>> }).create(payload)
    },
    onSuccess: (data) => {
      invalidateDocumentQueries(queryClient, projectId, prefix)
      const record = data as Record<string, unknown>
      const docIdFieldMap: Record<string, string> = {
        REQ: 'req_id', TC: 'tc_id', DES: 'design_id',
        RSK: 'risk_id', CHG: 'change_id', CPT: 'concept_id',
        SPEC: 'doc_id', PRT: 'doc_id', RPT: 'doc_id', STD: 'doc_id', VIS: 'doc_id',
      }
      const newDocId = record[docIdFieldMap[docType]] || record.id
      const kindSlug = DOC_TYPE_SLUGS[docType]
      void navigate(`/projects/${prefix}/docs/${kindSlug}/${newDocId}/edit`, { replace: true })
    },
    onError: (error) => {
      setSaveError(extractApiErrorMessage(error, 'Could not save document'))
    },
  })

  const updateMutation = useMutation({
    mutationFn: async () => {
      if (!resolvedDocId) return
      if (docType === 'TC') {
        return testCasesApi.update(resolvedDocId, {
          title,
          description: sent.description || null,
          preconditions: sent.preconditions || null,
          steps: tcRows.length > 0 ? tcRows : null,
          visibility: sent.visibility === 'customer' ? 'customer' : 'internal',
        })
      }
      if (isControlledSharedDocument(docType)) {
        return documentsApi.update(
          resolvedDocId,
          sharedDocumentUpdatePayload(docType, title, contentJson, contentHtml, sent, config.statusOptions),
        )
      }
      const api = apiForType(docType) as unknown as { update: (id: number, data: Record<string, unknown>) => Promise<Record<string, unknown>> }
      const payload: Record<string, unknown> = {
        [config.titleField]: title,
        content_json: contentJson,
        content_html: contentHtml,
        ...sent,
      }
      if (docType === 'REQ') {
        payload.visibility = requirementVisibilityFromOrigin(sent.req_origin)
      }
      if (controlled) delete payload.status
      delete payload.reviewer_id
      delete payload.approver_id
      return api.update(resolvedDocId, payload)
    },
    onSuccess: (updated) => {
      if (resolvedDocId) {
        const record = updated as Record<string, unknown>
        queryClient.setQueryData(['document', resolvedDocId], (old: unknown) => {
          if (old && typeof old === 'object') {
            return { ...(old as object), ...record }
          }
          return record
        })
        if (prefix && kind && docIdStr) {
          queryClient.setQueryData(['doc-facade', prefix, kind, docIdStr], (old: unknown) => {
            if (old && typeof old === 'object') {
              return { ...(old as object), ...record }
            }
            return record
          })
        }
      }
      const activityType = artefactActivityTypeForDocType(docType)
      if (activityType && resolvedDocId) {
        void queryClient.invalidateQueries({ queryKey: ['artefactActivity', activityType, resolvedDocId] })
        void queryClient.invalidateQueries({ queryKey: ['document-workflow', activityType, resolvedDocId] })
      }
      invalidateDocumentQueries(queryClient, projectId, prefix, resolvedDocId, kind, docIdStr)
      setSaveError(null)
      setSaveSuccess(true)
      toast.saved(DOC_TYPE_LABELS[docType])
      const timer = setTimeout(() => setSaveSuccess(false), 2000)
      return () => clearTimeout(timer)
    },
    onError: (error) => {
      setSaveError(extractApiErrorMessage(error, 'Could not save document'))
      toast.failed(`Saving the ${DOC_TYPE_LABELS[docType].toLowerCase()}`, error)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: async () => {
      if (!resolvedDocId) {
        throw new Error('Document is not ready to delete.')
      }
      const api = apiForType(docType) as { delete: (id: number) => Promise<void> }
      await api.delete(resolvedDocId)
    },
    onSuccess: () => {
      const artefactType = artefactActivityTypeForDocType(docType) || 'defect'
      const detailKey = ({ 'test-case': 'testCase', 'test-concept': 'testConcept' } as Record<string, string>)[artefactType] || artefactType
      finishArtefactDeletion(queryClient, { projectId, prefix, detailKey, artefactType, recordId: resolvedDocId!, kind, docId: docIdStr }, () => navigate(listBackUrl))
      toast.deleted(docIdStr ? `${DOC_TYPE_LABELS[docType]} ${docIdStr}` : DOC_TYPE_LABELS[docType])
    },
    onError: (error) => {
      setSaveError(extractApiErrorMessage(error, 'Could not delete document'))
      toast.failed(`Deleting the ${DOC_TYPE_LABELS[docType].toLowerCase()}`, error)
    },
  })

  const handleEditorChange = useCallback((json: Record<string, unknown>, html: string) => {
    setContentJson(json)
    setContentHtml(html)
  }, [])

  const handleSave = () => {
    if (!editMode && !docIdIsValid) return
    if (!projectReady) return
    if (editMode && !resolvedDocId) return
    if (editMode && !workflow.data?.actions?.edit_current) return

    setSaveError(null)
    setSaveSuccess(false)
    if (editMode) {
      updateMutation.mutate()
    } else {
      createMutation.mutate()
    }
  }

  const isPending = createMutation.isPending || updateMutation.isPending || deleteMutation.isPending
  const canSave = title.trim().length > 0
    && docIdIsValid
    && projectReady
    && (!editMode || !!resolvedDocId)
    && (!editMode || !!workflow.data?.actions?.edit_current)
  const visibleConfigFields = config.fields.filter((field) =>
    field.key !== 'req_origin' &&
    field.key !== config.titleField &&
    field.key !== 'description' &&
    !(field.key === 'priority' && config.priorityOptions) &&
    !(docType === 'TC' && field.key === 'preconditions')
  )
  const showDescriptionMetadata = config.fields.some((field) => field.key === 'description')

  if (editMode && docIdStr && !resolvedDocId) {
    return <div className="flex items-center justify-center h-64 text-muted-foreground">Loading...</div>
  }

  if (!editMode && prefix && isProjectLoading) {
    return <div className="flex items-center justify-center h-64 text-muted-foreground">Loading project...</div>
  }

  if (!editMode && prefix && isProjectError) {
    return (
      <div className="flex items-center justify-center h-64 text-destructive">
        Could not load project. Return to the project list and try again.
      </div>
    )
  }

  if (!canEditDocs) {
    return (
      <div className="flex items-center justify-center h-64 animate-fade-in">
        <div className="text-center">
          <h3 className="text-lg font-semibold text-foreground mb-2">You do not have edit access</h3>
          <p className="text-sm text-muted-foreground mb-4">Only admins and maintainers can create or edit documents.</p>
          <Link
            to={listBackUrl}
            className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 transition-colors"
            onClick={(e) => { e.preventDefault(); handleBack() }}
          >
            <ArrowLeft className="h-4 w-4" />
            {backNavLabel}
          </Link>
        </div>
      </div>
    )
  }

  if (editMode && workflow.isPending) return <div className="p-8 text-muted-foreground">Loading document...</div>
  if (editMode && (workflow.isError || !workflow.data?.actions?.edit_current)) {
    return <div className="p-8 space-y-4"><p>{workflow.isError ? 'Could not load document.' : 'This document is read-only.'}</p><Link to={prefix && docIdStr ? docUrl(prefix, docType, docIdStr) : listBackUrl}>View document</Link></div>
  }

  return (
    <div className="animate-fade-in -m-6 flex flex-col flex-1 min-h-0">
      <div className="flex items-center justify-between px-6 py-3 border-b border-border bg-card shrink-0">
        <div className="flex items-center gap-3">
          <button
            onClick={handleBack}
            className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
            aria-label="Go back"
          >
            <ArrowLeft className="h-4 w-4" />
            {backNavLabel}
          </button>
          <span className={`px-2 py-0.5 rounded-md text-[11px] font-semibold ${DOC_TYPE_COLORS[docType]}`}>
            {DOC_TYPE_LABELS[docType]}
          </span>
          <span className="text-xs font-mono text-muted-foreground">
            {editMode ? editDocFacade?.doc_id || docIdStr : expectedDocIdExample}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-2 rounded-md text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
            title={sidebarOpen ? 'Hide metadata' : 'Show metadata'}
          >
            {sidebarOpen ? <PanelRightClose className="h-4 w-4" /> : <PanelRightOpen className="h-4 w-4" />}
          </button>
          <button
            onClick={handleBack}
            className="px-3 py-1.5 text-sm text-muted-foreground border border-border rounded-md hover:bg-accent transition-colors"
          >
            Discard
          </button>
          {editMode && resolvedDocId && can('delete', docType) && rowAllows('delete') ? (
            <button
              type="button"
              onClick={() => {
                if (!window.confirm(`Delete this ${DOC_TYPE_LABELS[docType].toLowerCase()}?`)) return
                setSaveError(null)
                deleteMutation.mutate()
              }}
              disabled={isPending}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm text-destructive border border-destructive/30 rounded-md hover:bg-destructive/10 disabled:opacity-50 transition-colors"
            >
              <Trash2 className="h-4 w-4" />
              Delete
            </button>
          ) : null}
          <button
            onClick={handleSave}
            disabled={(!canSave || isPending) && !saveSuccess}
            className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
              saveSuccess
                ? 'bg-emerald-500 text-white'
                : 'bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50'
            }`}
          >
            {saveLabel(saveSuccess, isPending)}
          </button>
        </div>
      </div>

      {saveError ? (
        <div className="px-6 py-2 text-sm text-destructive bg-destructive/10 border-b border-destructive/20">
          {saveError}
        </div>
      ) : null}

      <div className="flex">
        <div className="flex-1 flex flex-col min-w-0">
          <div className={`${docType === 'TC' ? 'max-w-none' : 'max-w-4xl mx-auto'} w-full px-8 pt-8 pb-0`}>
            <div className="flex items-center gap-2 mb-4 flex-wrap">
              <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-muted text-muted-foreground">
                {displayedStatus}
              </span>
            </div>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Untitled"
              autoFocus
              className="w-full text-3xl font-bold text-foreground placeholder:text-muted-foreground/40 bg-transparent border-none outline-hidden mb-2"
            />

            {showDescriptionMetadata && (
              <input
                type="text"
                value={metadata.description || ''}
                onChange={(e) => setMetadata({ ...metadata, description: e.target.value })}
                placeholder="Brief description..."
                className="w-full text-sm text-muted-foreground placeholder:text-muted-foreground/40 bg-transparent border-none outline-hidden mb-4 pb-4 border-b border-border"
              />
            )}
          </div>

          <div className="flex-1">
            {!sidebarOpen && editMode && resolvedDocId && artefactActivityTypeForDocType(docType) && (
              <div className="max-w-4xl mx-auto w-full px-4 pt-4">
                <OpenThreads artefactType={artefactActivityTypeForDocType(docType)!} artefactId={resolvedDocId} />
              </div>
            )}
            <div className={`${docType === 'TC' ? 'max-w-none' : 'max-w-4xl mx-auto'} w-full px-4 py-4`}>
              {docType === 'TC' ? (
                <TcsArteTable
                  rows={tcRows}
                  onChange={setTcRows}
                  editable
                  mentionItems={parameterMentionItems}
                  userMentionItems={userMentionItems}
                  parameterHref={prefix ? `/projects/${prefix}/parameters` : undefined} parameterValues={parameterValues}
                />
              ) : (
                <DocEditor
                  content={contentJson}
                  onChange={handleEditorChange}
                  placeholder={`Start writing your ${config.label.toLowerCase()}... Use the toolbar above for formatting.`}
                  editable={true}
                  minHeight="min-h-[60vh]"
                  headingNumbered={headingNumbered}
                  onHeadingNumberedChange={setHeadingNumbered}
                  showOutline={outlineOpen}
                  onOutlineToggle={setOutlineOpen}
                  mentionItems={parameterMentionItems}
                  userMentionItems={userMentionItems}
                  artefactSearch={artefactSearch}
                  artefactHref={artefactHref}
                  parameterValues={parameterValues}
                  artefactLabels={artefactLabels}
                />
              )}
            </div>
          </div>
        </div>

        {sidebarOpen && (
          <div className="w-72 border-l border-border bg-card/50 overflow-y-auto themed-scrollbar shrink-0">
            <div className="p-4 space-y-4">
              {editMode && resolvedDocId && artefactActivityTypeForDocType(docType) && (
                <OpenThreads artefactType={artefactActivityTypeForDocType(docType)!} artefactId={resolvedDocId} />
              )}
              <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Properties</h3>

              <MetaField label="Status">
                {editMode && controlled ? <span>{displayedStatus}</span> :
                <SelectField
                  value={metadata.status || firstStatus}
                  onChange={(e) => setMetadata({ ...metadata, status: e.target.value })}
                  title="Select status"
                  className="w-full px-2 py-1.5 bg-background border border-input rounded-md text-sm"
                >
                  {statusChoices.map((opt) => (
                    <option key={opt} value={opt}>{opt}</option>
                  ))}
                </SelectField>}
              </MetaField>

              {!external && (
                <MetaField label="Origin">
                  <SelectField
                    value={docType === 'REQ' ? metadata.req_origin || 'Internal' : metadata.visibility || 'internal'}
                    onChange={(event) => setMetadata(docType === 'REQ'
                      ? { ...metadata, req_origin: event.target.value, visibility: requirementVisibilityFromOrigin(event.target.value) }
                      : { ...metadata, visibility: event.target.value })}
                    title="Select origin"
                    className="w-full px-2 py-1.5 bg-background border border-input rounded-md text-sm"
                  >
                    {docType === 'REQ'
                      ? config.fields.find(field => field.key === 'req_origin')?.options?.map(origin => <option key={origin} value={origin}>{origin}</option>)
                      : <><option value="internal">Internal</option><option value="customer">Customer</option></>}
                  </SelectField>
                  {!editMode && projectId > 0 && <TagPicker projectId={projectId} value={tagIds} onChange={setTagIds} showLabel={false} />}
                </MetaField>
              )}
              {external && !editMode && projectId > 0 && <TagPicker projectId={projectId} value={tagIds} onChange={setTagIds} />}

              {!editMode && (docType === 'REQ' || docType === 'TC') && <MetaField label="Assigned to">
                <UserSelect value={metadata.reviewer_id || ''} onChange={value => setMetadata({ ...metadata, reviewer_id: value })} users={users ?? []} label="Select reviewer" />
              </MetaField>}

              {config.priorityOptions && (
                <MetaField label="Priority">
                  <SelectField
                    value={metadata.priority || config.priorityOptions[0]}
                    onChange={(e) => setMetadata({ ...metadata, priority: e.target.value })}
                    title="Select priority"
                    className="w-full px-2 py-1.5 bg-background border border-input rounded-md text-sm"
                  >
                    {config.priorityOptions.map((opt) => (
                      <option key={opt} value={opt}>{opt}</option>
                    ))}
                  </SelectField>
                </MetaField>
              )}

              {visibleConfigFields.length > 0 && (
                <>
                  {visibleConfigFields.filter((field) => field.type !== 'textarea').map((field) => (
                    <MetaField key={field.key} label={field.label}>
                      {field.type === 'select' && field.options && (
                        <SelectField
                          value={metadata[field.key] || field.options[0]}
                          onChange={(e) => setMetadata({ ...metadata, [field.key]: e.target.value })}
                          title={field.label}
                          className="w-full px-2 py-1.5 bg-background border border-input rounded-md text-sm"
                        >
                          {field.options.map((opt) => (
                            <option key={opt} value={opt}>{opt}</option>
                          ))}
                        </SelectField>
                      )}
                      {field.type === 'number' && (
                        <input
                          type="number"
                          value={metadata[field.key] || ''}
                          onChange={(e) => setMetadata({ ...metadata, [field.key]: e.target.value })}
                          title={field.label}
                          placeholder={field.label}
                          className="w-full px-2 py-1.5 bg-background border border-input rounded-md text-sm"
                        />
                      )}
                      {field.type !== 'number' && (field.type !== 'select' || !field.options) && (
                        <input
                          type="text"
                          value={metadata[field.key] || ''}
                          onChange={(e) => setMetadata({ ...metadata, [field.key]: e.target.value })}
                          title={field.label}
                          placeholder={field.label}
                          className="w-full px-2 py-1.5 bg-background border border-input rounded-md text-sm"
                        />
                      )}
                    </MetaField>
                  ))}

                  {visibleConfigFields.filter((field) => field.type === 'textarea').map((field) => (
                    <MetaField key={field.key} label={field.label}>
                      <textarea
                        value={metadata[field.key] || ''}
                        onChange={(e) => setMetadata({ ...metadata, [field.key]: e.target.value })}
                        title={field.label}
                        placeholder={field.label}
                        rows={3}
                        className="w-full px-2 py-1.5 bg-background border border-input rounded-md text-sm resize-none"
                      />
                    </MetaField>
                  ))}
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function MetaField({ label, children }: Readonly<{ label: string; children: React.ReactNode }>) {
  return (
    <div>
      <label className="block text-[11px] font-medium text-muted-foreground uppercase tracking-wider mb-1">
        {label}
      </label>
      {children}
    </div>
  )
}
import UserSelect from '../components/UserSelect'
