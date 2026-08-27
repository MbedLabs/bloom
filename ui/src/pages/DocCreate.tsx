import { useState, useCallback, useEffect, useMemo } from 'react'
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
} from '../api/client'
import type { DocType } from '../types/doc'
import {
  DOC_CONFIGS,
  DOC_TYPE_LABELS,
  DOC_TYPE_COLORS,
  DOC_TYPE_SLUGS,
  docUrl,
  normalizeDocTypeParam,
} from '../types/doc'
import { useAuth } from '../contexts/AuthContext'
import { useToast } from '../components/useToast'
import { docRegistryBackUrl, docRegistryListLabel } from '../lib/docRegistryParams'
import {
  dedicatedListUrl,
  isServerAssignedDocIdOnCreate,
  usesDocumentEditor,
} from './docCreateIdPolicy'

function artefactActivityTypeForDocType(docType: DocType): string | null {
  if (docType === 'REQ') return 'requirement'
  if (docType === 'TC') return 'test-case'
  if (docType === 'SPEC' || docType === 'PRT' || docType === 'RPT' || docType === 'STD') return 'document'
  return null
}

function isControlledSharedDocument(docType: DocType): boolean {
  return docType === 'SPEC' || docType === 'PRT' || docType === 'RPT' || docType === 'STD'
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
  statusOptions: string[],
) {
  const visibility: ArtefactVisibility =
    metadata.visibility === 'customer' ? 'customer' : 'internal'
  return {
    title,
    doc_type: docType,
    description: metadata.description || undefined,
    content_json: contentJson,
    content_html: contentHtml || undefined,
    status: metadata.status || statusOptions[0],
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
    status: metadata.status || statusOptions[0],
    visibility,
  }
}

function invalidateDocumentQueries(
  queryClient: QueryClient,
  projectId: number,
  prefix: string | undefined,
  resolvedDocId?: number,
  kind?: string,
  docIdStr?: string,
) {
  queryClient.invalidateQueries({ queryKey: ['requirements', projectId] })
  queryClient.invalidateQueries({ queryKey: ['test-cases', projectId] })
  queryClient.invalidateQueries({ queryKey: ['testCases', projectId] })
  queryClient.invalidateQueries({ queryKey: ['designs', projectId] })
  queryClient.invalidateQueries({ queryKey: ['risks', projectId] })
  queryClient.invalidateQueries({ queryKey: ['changes', projectId] })
  queryClient.invalidateQueries({ queryKey: ['test-concepts', projectId] })
  queryClient.invalidateQueries({ queryKey: ['defects', projectId] })
  queryClient.invalidateQueries({ queryKey: ['documents', projectId] })
  queryClient.invalidateQueries({ queryKey: ['project-by-prefix', prefix] })
  queryClient.invalidateQueries({ queryKey: ['project-docs-shell', prefix] })
  if (resolvedDocId) {
    queryClient.invalidateQueries({ queryKey: ['document', resolvedDocId] })
  }
  if (prefix && kind && docIdStr) {
    queryClient.invalidateQueries({ queryKey: ['doc-facade', prefix, kind, docIdStr] })
  }
}

interface DocCreateProps {
  editMode?: boolean
}

export default function DocCreate({ editMode = false }: DocCreateProps) {
  const { user } = useAuth()
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
  const listBackUrl = prefix ? docRegistryBackUrl(prefix, docType, returnTo ?? null) : '/projects'
  const backNavLabel =
    typeof returnTo === 'string' && returnTo.trim() !== ''
      ? 'Back'
      : `Back to ${docRegistryListLabel(docType)}`
  const canEditDocs = user?.role === 'admin' || user?.role === 'maintainer'
  // The server allocates ids with MAX(suffix)+1, so ask it rather than assuming
  // -001, which was almost always already taken.
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
      navigate(-1)
    } else {
      navigate(listBackUrl)
    }
  }, [navigate, listBackUrl])

  const { data: users } = useQuery({
    queryKey: ['users'],
    queryFn: usersApi.list,
    enabled: canEditDocs,
  })

  const { data: projectVariables } = useQuery({
    queryKey: ['projectVariables', projectId],
    queryFn: () => projectVariablesApi.list(projectId),
    enabled: canEditDocs && !!projectId,
  })

  // `{{` inserts a project parameter *or* a project variable - both kinds live
  // on the Parameters & Variables screen and both are addressed the same way in
  // a document. `@` is for people, and only people.
  //
  // Both lists go to the TCS table as well as to the editor: a test step that
  // references a parameter has to name it the same way a requirement does, and
  // a test case is the surface where a parameter is most often pinned down.
  const parameterMentionItems = useMemo(
    () => (projectVariables ?? []).map((variable) => ({ id: variable.id, label: variable.key })),
    [projectVariables],
  )
  const userMentionItems = useMemo(
    () => (users ?? []).map((u) => ({ id: u.id, label: u.full_name })),
    [users],
  )

  const apiForType = useCallback((type: DocType) => {
    const map: Record<string, unknown> = {
      REQ: requirementsApi, TC: testCasesApi, DES: designsApi,
      RSK: risksApi, CHG: changesApi, CPT: testConceptsApi,
      SPEC: documentsApi, PRT: documentsApi, RPT: documentsApi, STD: documentsApi,
    }
    return map[type]
  }, [])

  // Types with a dedicated page never open the generic document editor - not on
  // create and not on edit either. `docs/defects/PRJ-DEF-001/edit` used to render
  // the rich-text editor, which has no severity, resolution summary or tracker
  // link, so a defect could not be edited there without losing them.
  useEffect(() => {
    if (!prefix || usesDocumentEditor(docType)) return
    if (editMode) {
      navigate(
        docIdStr
          ? docUrl(prefix, docType, docIdStr)
          : docRegistryBackUrl(prefix, docType, null),
        { replace: true },
      )
      return
    }
    navigate(dedicatedListUrl(prefix, docType) ?? docRegistryBackUrl(prefix, docType, null), {
      replace: true,
    })
  }, [docIdStr, docType, editMode, navigate, prefix])

  useEffect(() => {
    if (editMode || !prefix || !usesDocumentEditor(docType)) return
    if (!isServerAssignedDocIdOnCreate(docType)) {
      navigate(docRegistryBackUrl(prefix, docType, returnTo ?? null), { replace: true })
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
      if (docType === 'TC') {
        return testCasesApi.create({
          project_id: projectId,
          title,
          description: metadata.description || undefined,
          preconditions: metadata.preconditions || undefined,
          steps: tcRows.length > 0 ? tcRows : undefined,
          status: metadata.status || config.statusOptions[0],
          visibility: metadata.visibility === 'customer' ? 'customer' : 'internal',
          reviewer_id: metadata.reviewer_id ? Number(metadata.reviewer_id) : undefined,
        })
      }
      if (isControlledSharedDocument(docType)) {
        return documentsApi.create({
          project_id: projectId,
          ...sharedDocumentCreatePayload(docType, title, contentJson, contentHtml, metadata, config.statusOptions),
        })
      }
      const payload: Record<string, unknown> = {
        project_id: projectId,
        [config.titleField]: title,
        content_json: contentJson,
        content_html: contentHtml,
        ...metadata,
      }
      if (docType === 'REQ') {
        payload.visibility = requirementVisibilityFromOrigin(metadata.req_origin)
      }
      return (api as unknown as { create: (data: Record<string, unknown>) => Promise<Record<string, unknown>> }).create(payload)
    },
    onSuccess: (data) => {
      invalidateDocumentQueries(queryClient, projectId, prefix)
      const record = data as Record<string, unknown>
      const docIdFieldMap: Record<string, string> = {
        REQ: 'req_id', TC: 'tc_id', DES: 'design_id',
        RSK: 'risk_id', CHG: 'change_id', CPT: 'concept_id',
        SPEC: 'doc_id', PRT: 'doc_id', RPT: 'doc_id', STD: 'doc_id',
      }
      const newDocId = record[docIdFieldMap[docType]] || record.id
      const kindSlug = DOC_TYPE_SLUGS[docType]
      navigate(`/projects/${prefix}/docs/${kindSlug}/${newDocId}/edit`, { replace: true })
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
          description: metadata.description || null,
          preconditions: metadata.preconditions || null,
          steps: tcRows.length > 0 ? tcRows : null,
          status: metadata.status || config.statusOptions[0],
          visibility: metadata.visibility === 'customer' ? 'customer' : 'internal',
          reviewer_id: metadata.reviewer_id ? Number(metadata.reviewer_id) : null,
        })
      }
      if (isControlledSharedDocument(docType)) {
        return documentsApi.update(
          resolvedDocId,
          sharedDocumentUpdatePayload(docType, title, contentJson, contentHtml, metadata, config.statusOptions),
        )
      }
      const api = apiForType(docType) as unknown as { update: (id: number, data: Record<string, unknown>) => Promise<Record<string, unknown>> }
      const payload: Record<string, unknown> = {
        [config.titleField]: title,
        content_json: contentJson,
        content_html: contentHtml,
        ...metadata,
      }
      if (docType === 'REQ') {
        payload.visibility = requirementVisibilityFromOrigin(metadata.req_origin)
      }
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
        queryClient.invalidateQueries({ queryKey: ['artefactActivity', activityType, resolvedDocId] })
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
      invalidateDocumentQueries(queryClient, projectId, prefix, resolvedDocId, kind, docIdStr)
      toast.deleted(docIdStr ? `${DOC_TYPE_LABELS[docType]} ${docIdStr}` : DOC_TYPE_LABELS[docType])
      navigate(listBackUrl)
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
  const visibleConfigFields = config.fields.filter((field) =>
    field.key !== config.titleField &&
    field.key !== 'description' &&
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

  return (
    <div className="animate-fade-in -m-6 flex flex-col flex-1 min-h-0">
      {/* Top bar */}
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
          {/* The only place the document id is rendered. */}
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
          {editMode && resolvedDocId ? (
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
            {saveSuccess ? 'Saved' : isPending ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>

      {saveError ? (
        <div className="px-6 py-2 text-sm text-destructive bg-destructive/10 border-b border-destructive/20">
          {saveError}
        </div>
      ) : null}

      {/* Document frame */}
      <div className="flex">
        {/* Editor area with outline */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Document header inside frame */}
          <div className={`${docType === 'TC' ? 'max-w-none' : 'max-w-4xl mx-auto'} w-full px-8 pt-8 pb-0`}>
            {/* Status only: the type and document id are already shown in the top bar. */}
            <div className="flex items-center gap-2 mb-4 flex-wrap">
              <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-muted text-muted-foreground">
                {metadata.status || config.statusOptions[0]}
              </span>
            </div>
            {/* Title inside the document frame */}
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Untitled"
              autoFocus
              className="w-full text-3xl font-bold text-foreground placeholder:text-muted-foreground/40 bg-transparent border-none outline-none mb-2"
            />

            {/* Description field inside frame for applicable types */}
            {showDescriptionMetadata && (
              <input
                type="text"
                value={metadata.description || ''}
                onChange={(e) => setMetadata({ ...metadata, description: e.target.value })}
                placeholder="Brief description..."
                className="w-full text-sm text-muted-foreground placeholder:text-muted-foreground/40 bg-transparent border-none outline-none mb-4 pb-4 border-b border-border"
              />
            )}
          </div>

          {/* Editor body */}
          <div className="flex-1">
            <div className={`${docType === 'TC' ? 'max-w-none' : 'max-w-4xl mx-auto'} w-full px-4 py-4`}>
              {docType === 'TC' ? (
                <TcsArteTable
                  rows={tcRows}
                  onChange={setTcRows}
                  editable
                  mentionItems={parameterMentionItems}
                  userMentionItems={userMentionItems}
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
                />
              )}
            </div>
          </div>
        </div>

        {/* Metadata sidebar */}
        {sidebarOpen && (
          <div className="w-72 border-l border-border bg-card/50 overflow-y-auto themed-scrollbar shrink-0">
            <div className="p-4 space-y-4">
              <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Properties</h3>

              {/* Status */}
              <MetaField label="Status">
                <select
                  value={metadata.status || config.statusOptions[0]}
                  onChange={(e) => setMetadata({ ...metadata, status: e.target.value })}
                  title="Select status"
                  className="w-full px-2 py-1.5 bg-background border border-input rounded-md text-sm"
                >
                  {config.statusOptions.map((opt) => (
                    <option key={opt} value={opt}>{opt}</option>
                  ))}
                </select>
              </MetaField>

              {docType !== 'REQ' && (
              <MetaField label="Visibility">
                <select
                  value={metadata.visibility || 'internal'}
                  onChange={(e) => setMetadata({ ...metadata, visibility: e.target.value })}
                  title="Select visibility"
                  className="w-full px-2 py-1.5 bg-background border border-input rounded-md text-sm"
                >
                  <option value="internal">Internal</option>
                  <option value="customer">Customer</option>
                </select>
              </MetaField>
              )}

              {/* Assigned to */}
              <MetaField label="Assigned to">
                <select
                  value={metadata.reviewer_id || ''}
                  onChange={(e) => setMetadata({ ...metadata, reviewer_id: e.target.value })}
                  title="Select reviewer"
                  className="w-full px-2 py-1.5 bg-background border border-input rounded-md text-sm"
                >
                  <option value="">Unassigned</option>
                  {users?.map((u) => (
                    <option key={u.id} value={u.id}>{u.full_name}</option>
                  ))}
                </select>
              </MetaField>

              {/* Priority (if applicable) */}
              {config.priorityOptions && (
                <MetaField label="Priority">
                  <select
                    value={metadata.priority || config.priorityOptions[0]}
                    onChange={(e) => setMetadata({ ...metadata, priority: e.target.value })}
                    title="Select priority"
                    className="w-full px-2 py-1.5 bg-background border border-input rounded-md text-sm"
                  >
                    {config.priorityOptions.map((opt) => (
                      <option key={opt} value={opt}>{opt}</option>
                    ))}
                  </select>
                </MetaField>
              )}

              {/* Type-specific fields */}
              {visibleConfigFields.length > 0 && (
                <>
                  {visibleConfigFields.filter((field) => field.type !== 'textarea').map((field) => (
                    <MetaField key={field.key} label={field.label}>
                      {field.type === 'select' && field.options ? (
                        <select
                          value={metadata[field.key] || field.options[0]}
                          onChange={(e) => setMetadata({ ...metadata, [field.key]: e.target.value })}
                          title={field.label}
                          className="w-full px-2 py-1.5 bg-background border border-input rounded-md text-sm"
                        >
                          {field.options.map((opt) => (
                            <option key={opt} value={opt}>{opt}</option>
                          ))}
                        </select>
                      ) : field.type === 'number' ? (
                        <input
                          type="number"
                          value={metadata[field.key] || ''}
                          onChange={(e) => setMetadata({ ...metadata, [field.key]: e.target.value })}
                          title={field.label}
                          placeholder={field.label}
                          className="w-full px-2 py-1.5 bg-background border border-input rounded-md text-sm"
                        />
                      ) : (
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

function MetaField({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-[11px] font-medium text-muted-foreground uppercase tracking-wider mb-1">
        {label}
      </label>
      {children}
    </div>
  )
}
