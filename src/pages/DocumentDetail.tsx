import { useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { documentsApi, projectsApi, DocumentSection } from '../api/client'
import { Trash2, ChevronRight, FileText, ArrowLeft, FileEdit } from 'lucide-react'
import { DocEditor } from '../components/editor'

function DocTypeBadge({ docType }: { docType: string }) {
  const config: Record<string, string> = {
    Specification: 'bg-primary/10 text-primary',
    'Test Concept': 'bg-cyan-500/10 text-cyan-700 dark:text-cyan-400',
    Report: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400',
    Other: 'bg-muted text-muted-foreground',
  }
  return <span className={`px-2 py-0.5 rounded-md text-[11px] font-semibold ${config[docType] || config.Other}`}>{docType}</span>
}

function DocStatusBadge({ status }: { status: string }) {
  const config: Record<string, string> = {
    Draft: 'bg-amber-500/10 text-amber-700 dark:text-amber-400',
    Review: 'bg-blue-500/10 text-blue-700 dark:text-blue-400',
    Approved: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400',
  }
  return <span className={`px-2.5 py-1 rounded-md text-xs font-semibold ${config[status] || config.Draft}`}>{status}</span>
}

function flattenSections(sections: DocumentSection[]): DocumentSection[] {
  const result: DocumentSection[] = []
  const walk = (items: DocumentSection[]) => {
    for (const s of items.sort((a, b) => a.order - b.order)) {
      result.push(s)
      if (s.child_sections?.length) walk(s.child_sections)
    }
  }
  walk(sections)
  return result
}

function TocItem({ section, depth }: { section: DocumentSection; depth: number }) {
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

export default function DocumentDetail({ resolvedId }: { resolvedId?: number } = {}) {
  const { prefix, docId: docIdParam } = useParams<{ prefix: string; docId: string }>()
  const docId = resolvedId || Number(docIdParam)
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const { data: doc, isLoading } = useQuery({
    queryKey: ['document', docId],
    queryFn: () => documentsApi.get(docId),
    enabled: !!docId,
  })

  const { data: project } = useQuery({
    queryKey: ['project', doc?.project_id],
    queryFn: () => projectsApi.get(doc!.project_id),
    enabled: !!doc?.project_id,
  })

  const projectPrefix = prefix || project?.prefix || ''

  const deleteDocumentMutation = useMutation({
    mutationFn: () => documentsApi.delete(docId),
    onSuccess: () => {
      if (projectPrefix) {
        queryClient.invalidateQueries({ queryKey: ['documents', doc?.project_id] })
        navigate(`/projects/${projectPrefix}/docs`)
      } else {
        navigate('/projects')
      }
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
          <Link to="/" className="text-sm text-primary hover:text-primary/80 transition-colors">&larr; Back to Dashboard</Link>
        </div>
      </div>
    )
  }

  return (
    <div className="animate-fade-in space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-4">
          <Link to={`/projects/${projectPrefix}/docs`} className="p-2 hover:bg-accent/50 rounded-md">
            <ArrowLeft className="h-5 w-5 text-muted-foreground" />
          </Link>
          <div>
            <div className="flex items-center gap-3 flex-wrap mb-1">
              {doc.doc_id && <span className="font-mono text-sm text-primary font-semibold">{doc.doc_id}</span>}
              <DocTypeBadge docType={doc.doc_type} />
              <DocStatusBadge status={doc.status} />
              <span className="text-xs text-muted-foreground">v{doc.version}</span>
            </div>
            <h2 className="text-2xl font-bold text-foreground">{doc.title}</h2>
            {doc.description && <p className="text-muted-foreground mt-2">{doc.description}</p>}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => navigate(`/projects/${projectPrefix}/docs/${doc.doc_id || docId}/edit?type=DOC`)}
            className="inline-flex items-center px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 text-sm font-medium"
          >
            <FileEdit className="h-4 w-4 mr-2" />
            Edit
          </button>
          <button
            onClick={() => { if (window.confirm(`Delete document "${doc.title}"?`)) deleteDocumentMutation.mutate() }}
            disabled={deleteDocumentMutation.isPending}
            className="inline-flex items-center gap-2 px-3 py-2 border border-red-500/50 text-red-600 rounded-md text-sm hover:bg-red-500/10 disabled:opacity-50"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      </div>

      {hasRichContent && (
        <div className="bg-card rounded-lg border border-border shadow-elegant p-8">
          <div className="max-w-4xl mx-auto">
            <DocEditor
              content={doc.content_json as Record<string, unknown>}
              editable={false}
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
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary/10 to-cyan-500/10 flex items-center justify-center mx-auto mb-4">
            <FileText className="h-8 w-8 text-primary/40" />
          </div>
          <h3 className="text-lg font-semibold text-foreground mb-2">Empty Document</h3>
          <p className="text-sm text-muted-foreground max-w-md mx-auto mb-4">This document has no content yet. Open the editor to start writing.</p>
          <button
            onClick={() => navigate(`/projects/${projectPrefix}/docs/${doc.doc_id || docId}/edit?type=DOC`)}
            className="inline-flex items-center px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 text-sm font-medium"
          >
            <FileEdit className="h-4 w-4 mr-2" />
            Open Editor
          </button>
        </div>
      )}
    </div>
  )
}
