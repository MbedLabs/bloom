import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { documentsApi, Document } from '../api/client'
import { Plus, FileText, Search, BookOpen } from 'lucide-react'

function DocTypeBadge({ docType }: { docType: string }) {
  const config: Record<string, string> = {
    Specification: 'bg-primary/10 text-primary',
    'Test Concept': 'bg-cyan-500/10 text-cyan-700 dark:text-cyan-400',
    Report: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400',
    Other: 'bg-muted text-muted-foreground',
  }

  return (
    <span className={`px-2 py-0.5 rounded-md text-[11px] font-semibold ${config[docType] || config.Other}`}>
      {docType}
    </span>
  )
}

function DocStatusBadge({ status }: { status: string }) {
  const config: Record<string, string> = {
    Draft: 'bg-amber-500/10 text-amber-700 dark:text-amber-400',
    Review: 'bg-blue-500/10 text-blue-700 dark:text-blue-400',
    Approved: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400',
  }

  return (
    <span className={`px-2 py-0.5 rounded-md text-[11px] font-semibold ${config[status] || config.Draft}`}>
      {status}
    </span>
  )
}

function DocumentCard({ document, projectId }: { document: Document; projectId: number }) {
  return (
    <Link to={`/projects/${projectId}/documents/${document.id}`} className="block group">
      <div className="bg-card rounded-lg border border-border shadow-elegant hover:shadow-glow hover:border-primary/20 transition-all duration-300 overflow-hidden">
        <div className={`h-1 ${
          document.status === 'Approved'
            ? 'bg-gradient-to-r from-emerald-500 to-teal-400'
            : document.status === 'Review'
              ? 'bg-gradient-to-r from-blue-500 to-blue-400'
              : 'bg-gradient-to-r from-amber-500 to-amber-400'
        }`} />

        <div className="p-5">
          <div className="flex items-start justify-between mb-3">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-primary/10 flex items-center justify-center group-hover:bg-primary/20 transition-colors">
                <FileText className="h-4 w-4 text-primary" />
              </div>
              <div>
                <h3 className="font-semibold text-foreground text-sm group-hover:text-primary transition-colors">
                  {document.title}
                </h3>
                <span className="text-xs text-muted-foreground">v{document.version}</span>
              </div>
            </div>
            <DocStatusBadge status={document.status} />
          </div>

          {document.description && (
            <p className="text-xs text-muted-foreground mb-4 line-clamp-2">{document.description}</p>
          )}

          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <DocTypeBadge docType={document.doc_type} />
              <span className="text-xs text-muted-foreground">
                {document.section_count} section{document.section_count !== 1 ? 's' : ''}
              </span>
            </div>
            <span className="text-[11px] text-muted-foreground">
              {new Date(document.updated_at).toLocaleDateString()}
            </span>
          </div>
        </div>
      </div>
    </Link>
  )
}

export default function Documents() {
  const { id } = useParams<{ id: string }>()
  const projectId = Number(id)
  const navigate = useNavigate()
  const [search, setSearch] = useState('')

  const { data: documents, isLoading } = useQuery({
    queryKey: ['documents', projectId],
    queryFn: () => documentsApi.list(projectId),
    enabled: !!projectId,
  })

  const filteredDocuments = search
    ? documents?.filter(d =>
        d.title.toLowerCase().includes(search.toLowerCase()) ||
        d.doc_type.toLowerCase().includes(search.toLowerCase()) ||
        d.status.toLowerCase().includes(search.toLowerCase())
      )
    : documents

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex justify-between items-center">
        <div>
          <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
            <Link to={`/projects/${projectId}`} className="hover:text-primary transition-colors">
              Project
            </Link>
            <span>/</span>
            <span className="text-foreground">Documents</span>
          </div>
          <h2 className="text-xl font-bold text-foreground">Documents</h2>
          <p className="text-sm text-muted-foreground mt-0.5">
            {documents?.length || 0} document{documents?.length !== 1 ? 's' : ''}
          </p>
        </div>
        <button
          onClick={() => navigate(`/projects/${projectId}/docs/new?type=DOC`)}
          className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 hover:shadow-glow transition-all duration-200"
        >
          <Plus className="h-4 w-4" />
          New Document
        </button>
      </div>

      <div className="relative">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <input
          type="text"
          placeholder="Search documents..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full pl-9 pr-4 py-2.5 bg-card border border-border rounded-lg text-sm text-foreground placeholder:text-muted-foreground focus:ring-2 focus:ring-ring focus:border-ring transition-colors shadow-elegant"
        />
      </div>

      {isLoading ? (
        <div className="bg-card rounded-lg border border-border shadow-elegant p-8 text-center text-muted-foreground">
          Loading...
        </div>
      ) : !filteredDocuments || filteredDocuments.length === 0 ? (
        <div className="bg-card rounded-lg border border-border shadow-elegant p-16 text-center">
          <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-primary/10 to-cyan-500/10 flex items-center justify-center mx-auto mb-5">
            <BookOpen className="h-10 w-10 text-primary/40" />
          </div>
          <h3 className="text-lg font-semibold text-foreground mb-2">
            {search ? 'No documents found' : 'No Documents Yet'}
          </h3>
          <p className="text-sm text-muted-foreground mb-5 max-w-md mx-auto">
            {search
              ? 'Try a different search term.'
              : 'Create your first document to start building structured specifications and reports.'}
          </p>
          {!search && (
            <button
              onClick={() => navigate(`/projects/${projectId}/docs/new?type=DOC`)}
              className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 transition-colors"
            >
              <Plus className="h-4 w-4" />
              New Document
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredDocuments.map((doc) => (
            <DocumentCard key={doc.id} document={doc} projectId={projectId} />
          ))}
        </div>
      )}
    </div>
  )
}
