import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { FileText, Link2, Search, X } from 'lucide-react'
import {
  type ArtefactLink,
  type DocShell,
  docsApi,
  linksApi,
} from '../api/client'
import { formatDateTime } from '../test/date-utils'
import { docUrl, DOC_TYPE_LABELS, type DocType } from '../types/doc'
import { SectionCard } from './DocDetailShell'
import { useAuth } from '../contexts/AuthContext'

const LINK_ROLES = ['verifies', 'implements', 'references', 'depends_on', 'impacts', 'blocks'] as const

function docKey(type: string, id: number) {
  return `${type}:${id}`
}

function roleLabel(role: string, direction: 'incoming' | 'outgoing') {
  const labels: Record<string, [string, string]> = {
    verifies: ['verifies', 'verified by'],
    implements: ['implements', 'implemented by'],
    references: ['references', 'referenced by'],
    depends_on: ['depends on', 'dependency of'],
    impacts: ['impacts', 'impacted by'],
    blocks: ['blocks', 'blocked by'],
  }
  const pair = labels[role]
  if (!pair) return role.split('_').join(' ')
  return direction === 'outgoing' ? pair[0] : pair[1]
}

function DocumentLinkRow({
  link,
  doc,
  projectPrefix,
  direction,
  onDelete,
}: {
  link: ArtefactLink
  doc: DocShell | undefined
  projectPrefix: string
  direction: 'incoming' | 'outgoing'
  onDelete?: () => void
}) {
  return (
    <div className="flex items-center justify-between px-6 py-4 hover:bg-accent/50 transition-colors">
      <Link to={doc ? docUrl(projectPrefix, (doc.doc_type || 'SPEC') as DocType, doc.doc_id) : '#'} className="min-w-0 flex items-center">
        <FileText className="h-5 w-5 text-primary mr-3 shrink-0" />
        <div className="min-w-0">
          <div>
            <span className="font-mono text-sm text-primary mr-2">{doc?.doc_id || `${direction === 'outgoing' ? link.target_type : link.source_type} #${direction === 'outgoing' ? link.target_id : link.source_id}`}</span>
            <span className="text-foreground">{doc?.title || 'Linked document'}</span>
          </div>
          <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
            <span>{direction === 'incoming' ? 'Incoming' : 'Outgoing'}</span>
            <span className="rounded-full bg-primary/10 px-2 py-0.5 text-primary">{roleLabel(link.role, direction)}</span>
            {link.suspect && <span className="rounded-full bg-amber-500/10 px-2 py-0.5 text-amber-700 dark:text-amber-400">suspect</span>}
            <span>{formatDateTime(link.created_at)} ago</span>
          </div>
        </div>
      </Link>
      {onDelete && (
        <button
          onClick={onDelete}
          className="ml-3 p-1.5 rounded text-muted-foreground hover:text-red-500 hover:bg-red-500/10"
          title="Remove link"
        >
          <X className="h-4 w-4" />
        </button>
      )}
    </div>
  )
}

function LinkDocumentModal({
  projectId,
  sourceType,
  sourceId,
  docs,
  onClose,
}: {
  projectId: number
  sourceType: string
  sourceId: number
  docs: DocShell[]
  onClose: () => void
}) {
  const queryClient = useQueryClient()
  const [role, setRole] = useState<(typeof LINK_ROLES)[number]>('verifies')
  const [search, setSearch] = useState('')

  const createMutation = useMutation({
    mutationFn: (target: DocShell) => linksApi.create({
      project_id: projectId,
      source_type: sourceType,
      source_id: sourceId,
      target_type: target.doc_type,
      target_id: target.id,
      role,
      suspect: false,
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['docLinks', projectId] })
      onClose()
    },
  })

  const filteredDocs = docs.filter((doc) => {
    const q = search.trim().toLowerCase()
    if (!q) return true
    return doc.doc_id.toLowerCase().includes(q) || doc.title.toLowerCase().includes(q) || doc.doc_type.toLowerCase().includes(q)
  })

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="bg-card rounded-lg shadow-elegant max-w-2xl w-full mx-4 max-h-[80vh] flex flex-col">
        <div className="px-6 py-4 border-b border-border flex justify-between items-center">
          <h3 className="text-lg font-semibold">Link Document</h3>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground">✕</button>
        </div>
        <div className="p-6 border-b border-border grid grid-cols-1 md:grid-cols-[1fr_12rem] gap-3">
          <div className="relative">
            <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search controlled documents"
              className="w-full pl-9 pr-3 py-2 bg-background border border-input rounded-md text-sm"
            />
          </div>
          <select
            value={role}
            onChange={(event) => setRole(event.target.value as (typeof LINK_ROLES)[number])}
            className="px-3 py-2 bg-background border border-input rounded-md text-sm"
          >
            {LINK_ROLES.map((item) => (
              <option key={item} value={item}>{roleLabel(item, 'outgoing')}</option>
            ))}
          </select>
        </div>
        <div className="overflow-y-auto p-3">
          {filteredDocs.length === 0 ? (
            <div className="p-8 text-center text-muted-foreground">No matching documents.</div>
          ) : (
            <div className="divide-y divide-border">
              {filteredDocs.map((doc) => (
                <button
                  key={`${doc.doc_type}-${doc.id}`}
                  onClick={() => createMutation.mutate(doc)}
                  disabled={createMutation.isPending}
                  className="w-full px-3 py-3 text-left hover:bg-accent/50 disabled:opacity-50"
                >
                  <div className="flex items-center justify-between gap-3">
                    <div className="min-w-0">
                      <span className="font-mono text-sm text-primary mr-2">{doc.doc_id}</span>
                      <span className="text-sm font-medium text-foreground">{doc.title}</span>
                    </div>
                    <span className="shrink-0 rounded border border-border px-2 py-0.5 text-[11px] font-semibold text-muted-foreground">
                      {DOC_TYPE_LABELS[doc.doc_type as DocType] || doc.doc_type}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export function DocumentLinksPanel({
  projectId,
  projectPrefix,
  sourceType,
  sourceId,
}: {
  projectId: number
  projectPrefix: string
  sourceType: string
  sourceId: number
}) {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const [showModal, setShowModal] = useState(false)
  const canEditDocs = user?.role === 'admin' || user?.role === 'maintainer'

  const { data: docs } = useQuery({
    queryKey: ['all-docs', projectPrefix, `${sourceType.toLowerCase()}-links`],
    queryFn: () => docsApi.list(projectPrefix),
    enabled: !!projectPrefix,
  })

  const { data: outgoingLinks } = useQuery({
    queryKey: ['docLinks', projectId, sourceType, sourceId, 'outgoing'],
    queryFn: () => linksApi.list({ project_id: projectId, source_type: sourceType, source_id: sourceId }),
  })

  const { data: incomingLinks } = useQuery({
    queryKey: ['docLinks', projectId, sourceType, sourceId, 'incoming'],
    queryFn: () => linksApi.list({ project_id: projectId, target_type: sourceType, target_id: sourceId }),
  })

  const deleteMutation = useMutation({
    mutationFn: linksApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['docLinks', projectId] })
    },
  })

  const docLookup = useMemo(() => {
    const map = new Map<string, DocShell>()
    ;(docs || []).forEach((doc) => map.set(docKey(doc.doc_type, doc.id), doc))
    return map
  }, [docs])

  const linkCount = (outgoingLinks?.length || 0) + (incomingLinks?.length || 0)

  return (
    <SectionCard
      title="Document Links"
      actions={canEditDocs ? (
        <button
          onClick={() => setShowModal(true)}
          className="inline-flex items-center px-3 py-2 border border-input rounded-md text-sm font-medium hover:bg-accent/50"
        >
          <Link2 className="h-4 w-4 mr-2" />
          Link Document
        </button>
      ) : undefined}
    >
      <p className="text-xs text-muted-foreground mb-3">Typed links to requirements, specifications, designs, risks, and other controlled documents.</p>
      {linkCount === 0 ? (
        <p className="text-muted-foreground">No document links yet.</p>
      ) : (
        <div className="divide-y divide-border -mx-6 -mb-6">
          {(outgoingLinks || []).map((link) => (
            <DocumentLinkRow
              key={`out-${link.id}`}
              link={link}
              doc={docLookup.get(docKey(link.target_type, link.target_id))}
              projectPrefix={projectPrefix}
              direction="outgoing"
              onDelete={canEditDocs ? () => deleteMutation.mutate(link.id) : undefined}
            />
          ))}
          {(incomingLinks || []).map((link) => (
            <DocumentLinkRow
              key={`in-${link.id}`}
              link={link}
              doc={docLookup.get(docKey(link.source_type, link.source_id))}
              projectPrefix={projectPrefix}
              direction="incoming"
              onDelete={canEditDocs ? () => deleteMutation.mutate(link.id) : undefined}
            />
          ))}
        </div>
      )}

      {canEditDocs && showModal && (
        <LinkDocumentModal
          projectId={projectId}
          sourceType={sourceType}
          sourceId={sourceId}
          docs={(docs || []).filter((doc) => !(doc.doc_type === sourceType && doc.id === sourceId))}
          onClose={() => setShowModal(false)}
        />
      )}
    </SectionCard>
  )
}
