import { DOC_TYPE_SLUGS } from '../types/doc'
import { finishArtefactDeletion } from '../lib/refreshProjectViews'
import WorkflowPanel from '../components/WorkflowPanel'
import { useDocumentWorkflow } from '../hooks/useDocumentWorkflow'
import { useAuth } from '../contexts/AuthContext'
import { useSignOffPeople } from '../hooks/useSignOff'
import { useMemo, useState } from 'react'
import ArtefactTags from '../components/ArtefactTags'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useParams, Link, useNavigate } from 'react-router'
import { documentsApi, projectsApi, DocumentSection } from '../api/client'
import { Trash2, ChevronRight, FileText, FileEdit } from 'lucide-react'
import { DocEditor } from '../components/editor'
import DocDetailShell, { MetaItem, SectionCard } from '../components/DocDetailShell'
import { DocumentLinksPanel } from '../components/DocumentLinksPanel'
import DocumentActivityPanel from '../components/DocumentActivityPanel'
import DocumentAttachmentsPanel from '../components/DocumentAttachmentsPanel'
import { docEditUrl, docUrl, kindSlugToType, type DocType } from '../types/doc'
import { formatDateTime } from '../test/date-utils'
import { useToast } from '../components/useToast'
import { useProjectPermissions, useRowActions } from '../hooks/useProjectPermissions'
import { useParameterValues } from '../hooks/useParameterValues'
import { useArtefactLabels } from '../hooks/useArtefactLabels'
import ConfirmDelete from '../components/ConfirmDelete'

function flattenSections(sections: DocumentSection[]): DocumentSection[] {
  const result: DocumentSection[] = []
  const walk = (items: DocumentSection[]) => {
    for (const s of [...items].sort((a, b) => a.order - b.order)) {
      result.push(s)
      if (s.child_sections?.length) walk(s.child_sections)
    }
  }
  walk(sections)
  return result
}

function TocItem({ section, depth }: Readonly<{ section: DocumentSection; depth: number }>) {
  return (
    <>
      <div
        className="px-3 py-1.5 text-xs text-muted-foreground"
        style={{ paddingLeft: `${depth * 12 + 12}px` }}
      >
        {section.child_sections?.length > 0 && <ChevronRight className="h-3 w-3 shrink-0 inline mr-1" />}
        <span className="truncate">{section.title || 'Untitled Section'}</span>
      </div>
      {section.child_sections?.map((child) => (
        <TocItem key={child.id} section={child} depth={depth + 1} />
      ))}
    </>
  )
}

export default function DocumentDetail({
  resolvedId,
  allowedActions,
}: { resolvedId?: number; allowedActions?: string[] } = {}) {
  const { prefix, docId: docIdParam, kind } = useParams<{ prefix: string; docId: string; kind: string }>()
  const docId = resolvedId || Number(docIdParam)
  const workflow = useDocumentWorkflow('document', docId)
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const toast = useToast()



  const resolvedDocType = kindSlugToType(kind || '')
  const { can } = useProjectPermissions(prefix)
  const parameterValues = useParameterValues(prefix)
  const { data: doc, isLoading } = useQuery({
    queryKey: ['document', docId],
    queryFn: () => documentsApi.get(docId),
    enabled: !!docId,
  })
  const { user } = useAuth()
  const people = useSignOffPeople(doc?.project_id, user?.role === 'admin')
  const docType = (doc?.doc_type as DocType | undefined) ?? resolvedDocType
  const rowAllows = useRowActions(prefix, docType ?? 'SPEC', doc?.doc_id, allowedActions)
  const canEditDocs = docType ? can('edit', docType) : false
  const showEdit = canEditDocs && rowAllows('edit') && workflow.data?.actions?.edit_current === true
  const showDelete = canEditDocs && !!docType && can('delete', docType) && rowAllows('delete')

  const artefactLabels = useArtefactLabels(prefix, doc?.content_json)
  const { data: project } = useQuery({
    queryKey: ['project', doc?.project_id],
    queryFn: () => projectsApi.get(doc!.project_id),
    enabled: !!doc?.project_id,
  })

  const projectPrefix = prefix || project?.prefix || ''

  const [deleteConfirm, setDeleteConfirm] = useState(false)
  const deleteDocumentMutation = useMutation({
    mutationFn: () => documentsApi.delete(docId),
    onSuccess: () => {
      toast.notify('Document deleted', 'success')
      setTimeout(() => {
        finishArtefactDeletion(queryClient, { prefix: projectPrefix, projectId: doc?.project_id, detailKey: 'document', artefactType: 'document', recordId: docId, kind: docType ? DOC_TYPE_SLUGS[docType] : undefined, docId: doc?.doc_id ?? undefined }, () => navigate(projectPrefix ? `/projects/${projectPrefix}/docs` : '/projects'))
      }, 800)
    },
    onError: (err: unknown) => {
      toast.failed('Deleting the document', err)
      setDeleteConfirm(false)
    },
  })

  const topSections = useMemo(() => [...(doc?.sections || [])].sort((a, b) => a.order - b.order), [doc?.sections])
  const hasRichContent = !!doc?.content_json
  const hasLegacySections = !!doc?.sections?.length && !hasRichContent

  if (isLoading) {
    return <div className="flex items-center justify-center h-64 animate-fade-in"><div className="text-muted-foreground">Loading document...</div></div>
  }

  if (!doc) {
    return (
      <div className="flex items-center justify-center h-64 animate-fade-in">
        <div className="text-center">
          <h3 className="text-lg font-semibold text-foreground mb-2">Document not found</h3>
          <Link to={kind ? `/projects/${projectPrefix}/docs?type=${kind}` : `/projects/${projectPrefix}/docs`} className="text-sm text-primary hover:text-primary/80 transition-colors">&larr; Back to Documents</Link>
        </div>
      </div>
    )
  }

  if (!resolvedDocType) {
    return (
      <div className="flex items-center justify-center h-64 animate-fade-in">
        <div className="text-center">
          <h3 className="text-lg font-semibold text-foreground mb-2">Invalid document route</h3>
          <p className="text-sm text-muted-foreground">Unknown document kind &quot;{kind}&quot;.</p>
        </div>
      </div>
    )
  }

  const editUrl = docEditUrl(projectPrefix, resolvedDocType, doc.doc_id || String(docId))

  return (
    <>
    <DocDetailShell
      projectPrefix={projectPrefix}
      docType={resolvedDocType}
      docCode={doc.doc_id || String(docId)}
      title={doc.title}
      status={doc.status}
      actions={showEdit || showDelete ? (
        <>
          {showEdit && (
          <button
            onClick={() => navigate(`${editUrl}?type=${resolvedDocType}`)}
            className="inline-flex items-center px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 text-sm font-medium"
          >
            <FileEdit className="h-4 w-4 mr-2" />
            Edit
          </button>
          )}
          {showDelete && (!deleteConfirm ? (
            <button
              onClick={() => setDeleteConfirm(true)}
              disabled={deleteDocumentMutation.isPending}
              className="inline-flex items-center gap-2 px-3 py-2 border border-red-300 text-red-600 rounded-md text-sm hover:bg-red-50 disabled:opacity-50"
            >
              <Trash2 className="h-4 w-4" />
              Delete
            </button>
          ) : (
            <ConfirmDelete
              pending={deleteDocumentMutation.isPending}
              onConfirm={() => { setDeleteConfirm(false); deleteDocumentMutation.mutate(); }}
              onCancel={() => setDeleteConfirm(false)}
            />
          ))}
        </>
      ) : undefined}
      rightRail={
        <>
        <WorkflowPanel artefactType="document" artefactId={docId} projectPrefix={projectPrefix} projectId={doc.project_id} />
        <SectionCard title="Metadata">
          <div className="space-y-4">
            <MetaItem label="Origin" value={<ArtefactTags type="document" id={docId} projectId={doc.project_id} canEdit={showEdit} origin={doc.visibility === 'customer' ? 'Customer' : 'Internal'} />} />
            <MetaItem label="ID" value={doc.doc_id || String(docId)} mono />
            <MetaItem label="Version" value={`v${doc.version}`} />
            <MetaItem label="Created" value={formatDateTime(doc.created_at) + ' ago'} />
            <MetaItem label="Updated" value={formatDateTime(doc.updated_at) + ' ago'} />
          </div>
        </SectionCard>
        </>
      }
    >
      {hasRichContent && (
        <div className="bg-card rounded-lg border border-border shadow-elegant p-8">
          <div className="max-w-4xl mx-auto">
            <DocEditor
              content={doc.content_json as Record<string, unknown>}
              editable={false}
              userMentionItems={people.map(person => ({ id: person.id, label: person.full_name, user: person }))}
              parameterHref={prefix ? `/projects/${prefix}/parameters` : undefined} parameterValues={parameterValues} artefactLabels={artefactLabels}
            artefactHref={(type, _id, label) => docUrl(prefix, type as DocType, label)}
              minHeight="min-h-[40vh]"
            />
          </div>
        </div>
      )}

      {hasLegacySections && (
        <div className="flex gap-6">
          <div className="w-56 shrink-0">
            <div className="bg-card rounded-lg border border-border shadow-elegant p-3 sticky top-20">
              <p className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider mb-2">Outline</p>
              {topSections.map((section) => (
                <TocItem key={section.id} section={section} depth={0} />
              ))}
            </div>
          </div>
          <div className="flex-1 space-y-4">
            {flattenSections(doc.sections).map((section) => (
              <div key={section.id} className="bg-card border border-border rounded-lg p-5">
                <h3 className="font-semibold text-foreground text-sm mb-2">{section.title}</h3>
                {section.content && <pre className="text-sm text-muted-foreground whitespace-pre-wrap">{section.content}</pre>}
              </div>
            ))}
          </div>
        </div>
      )}

      {!hasRichContent && !hasLegacySections && (
        <div className="bg-card rounded-lg border border-border shadow-elegant p-16 text-center">
          <div className="w-16 h-16 rounded-2xl bg-linear-to-br/srgb from-primary/10 to-violet-500/10 flex items-center justify-center mx-auto mb-4">
            <FileText className="h-8 w-8 text-primary/40" />
          </div>
          <h3 className="text-lg font-semibold text-foreground mb-2">Empty Document</h3>
          <p className="text-sm text-muted-foreground max-w-md mx-auto mb-4">This document has no content yet. Open the editor to start writing.</p>
          {showEdit && (
            <button
              onClick={() => navigate(`${editUrl}?type=${resolvedDocType}`)}
              className="inline-flex items-center px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 text-sm font-medium"
            >
              <FileEdit className="h-4 w-4 mr-2" />
              Open Editor
            </button>
          )}
        </div>
      )}

      <DocumentAttachmentsPanel documentId={docId} docType={docType} rowAllowsEdit={showEdit} projectId={doc.project_id} />

      <DocumentActivityPanel artefactType="document" artefactId={docId} />

      <DocumentLinksPanel
        projectId={doc.project_id}
        projectPrefix={projectPrefix}
        sourceType={resolvedDocType}
        sourceId={docId}
        sourceDocId={doc.doc_id ?? undefined}
      />
    </DocDetailShell>
    </>
  )
}
