import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link2, Search, X } from 'lucide-react'
import {
  type ArtefactLink,
  type DocShell,
  docsApi,
  linksApi,
} from '../api/client'
import {
  docUrl,
  DOC_TYPE_LABELS,
  DOC_TYPE_COLORS,
  getDocLinkOptions,
  getDocLinkRoleLabel,
  normalizeDocTypeParam,
  type DocType,
} from '../types/doc'
import { SectionCard } from './DocDetailShell'
import { useAuth } from '../contexts/AuthContext'

export interface LinkTarget {
  id: number
  doc_id: string
  doc_type: DocType
  title: string
  status: string
}

function docKey(type: string, id: number) {
  return `${type}:${id}`
}

function targetUrl(prefix: string, type: DocType, target: LinkTarget | undefined): string {
  if (!target) return '#'
  return docUrl(prefix, type, target.doc_id)
}

function docShellToTarget(doc: DocShell): LinkTarget | null {
  const normalized = normalizeDocTypeParam(doc.doc_type)
  if (!normalized) return null
  return {
    id: doc.id,
    doc_id: doc.doc_id,
    doc_type: normalized,
    title: doc.title,
    status: doc.status,
  }
}

function DocumentLinkRow({
  link,
  target,
  projectPrefix,
  direction,
  onDelete,
}: {
  link: ArtefactLink
  target: LinkTarget | undefined
  projectPrefix: string
  direction: 'incoming' | 'outgoing'
  onDelete?: () => void
}) {
  const otherType = (direction === 'outgoing' ? link.target_type : link.source_type) as DocType
  const otherId = direction === 'outgoing' ? link.target_id : link.source_id
  const fallbackLabel = `${otherType} #${otherId}`
  const roleLabel = getDocLinkRoleLabel(link.role, direction)
  const typeColor = DOC_TYPE_COLORS[otherType] || 'bg-muted text-muted-foreground'

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-md text-xs border border-border/60 hover:border-border ${typeColor}`}>
      <Link
        to={targetUrl(projectPrefix, otherType, target)}
        className="font-mono text-[11px] hover:underline"
        title={roleLabel + ': ' + (target?.title || fallbackLabel)}
      >
        {target?.doc_id || fallbackLabel}
      </Link>
      {link.suspect && (
        <span className="shrink-0 rounded-full bg-amber-500/10 px-1 py-0.5 text-[10px] font-medium text-amber-700 dark:text-amber-400">
          !
        </span>
      )}
      {onDelete && (
        <button
          onClick={onDelete}
          className="ml-0.5 p-0.5 rounded text-muted-foreground hover:text-red-500 hover:bg-red-500/10 shrink-0"
          title="Remove link"
        >
          <X className="h-3 w-3" />
        </button>
      )}
    </span>
  )
}

function LinkDocumentModal({
  projectId,
  sourceType,
  sourceId,
  targets,
  onClose,
}: {
  projectId: number
  sourceType: string
  sourceId: number
  targets: LinkTarget[]
  onClose: () => void
}) {
  const queryClient = useQueryClient()
  const normalizedSourceType = normalizeDocTypeParam(sourceType)
  const [search, setSearch] = useState('')
  const eligibleTargets = useMemo(
    () => targets.filter((target) => {
      if (!normalizedSourceType) return false
      if (target.doc_type === normalizedSourceType && target.id === sourceId) return false
      return getDocLinkOptions(normalizedSourceType, target.doc_type).length > 0
    }),
    [targets, normalizedSourceType, sourceId]
  )
  const availableTargetTypes = useMemo(
    () => Array.from(new Set(eligibleTargets.map((target) => target.doc_type))),
    [eligibleTargets]
  )
  const [targetType, setTargetType] = useState<DocType | ''>('')
  const availableOptions = useMemo(
    () => (normalizedSourceType && targetType ? getDocLinkOptions(normalizedSourceType, targetType) : []),
    [normalizedSourceType, targetType]
  )
  const [selectedOptionKey, setSelectedOptionKey] = useState('')
  const selectedOption = useMemo(
    () => availableOptions.find((option) => option.key === selectedOptionKey) || null,
    [availableOptions, selectedOptionKey]
  )

  useEffect(() => {
    if (availableTargetTypes.length === 0) {
      setTargetType('')
      return
    }
    setTargetType((current) => (current && availableTargetTypes.includes(current) ? current : availableTargetTypes[0]))
  }, [availableTargetTypes])

  useEffect(() => {
    if (availableOptions.length === 0) {
      setSelectedOptionKey('')
      return
    }
    setSelectedOptionKey((current) => (
      current && availableOptions.some((option) => option.key === current)
        ? current
        : availableOptions[0].key
    ))
  }, [availableOptions])

  const createMutation = useMutation({
    mutationFn: (target: LinkTarget) => {
      if (!normalizedSourceType || !selectedOption) {
        throw new Error('Link type configuration is incomplete')
      }
      return linksApi.create({
        project_id: projectId,
        source_type: selectedOption.sourceType,
        source_id: selectedOption.displayDirection === 'outgoing' ? sourceId : target.id,
        target_type: selectedOption.targetType,
        target_id: selectedOption.displayDirection === 'outgoing' ? target.id : sourceId,
        role: selectedOption.role,
        suspect: false,
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['docLinks', projectId] })
      onClose()
    },
  })

  const filteredTargets = eligibleTargets.filter((target) => {
    if (!targetType || target.doc_type !== targetType) return false
    const q = search.trim().toLowerCase()
    if (!q) return true
    return (
      target.doc_id.toLowerCase().includes(q) ||
      target.title.toLowerCase().includes(q) ||
      target.doc_type.toLowerCase().includes(q)
    )
  })

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="bg-card rounded-lg shadow-elegant max-w-2xl w-full mx-4 max-h-[80vh] flex flex-col">
        <div className="px-6 py-4 border-b border-border flex justify-between items-center">
          <h3 className="text-lg font-semibold">Link Document</h3>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground">✕</button>
        </div>
        <div className="p-6 border-b border-border grid grid-cols-1 md:grid-cols-[1fr_12rem_12rem] gap-3">
          <div className="relative">
            <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder={targetType ? `Search ${DOC_TYPE_LABELS[targetType].toLowerCase()}s` : 'Search linkable artefacts'}
              title="Filter targets by ID, title, or type"
              className="w-full pl-9 pr-3 py-2 bg-background border border-input rounded-md text-sm"
            />
          </div>
          <select
            value={targetType}
            onChange={(event) => setTargetType(event.target.value as DocType)}
            title="Target artefact kind"
            className="px-3 py-2 bg-background border border-input rounded-md text-sm"
            disabled={availableTargetTypes.length === 0}
          >
            {availableTargetTypes.length === 0 ? (
              <option value="">No target kinds</option>
            ) : (
              availableTargetTypes.map((item) => (
                <option key={item} value={item}>{DOC_TYPE_LABELS[item]}</option>
              ))
            )}
          </select>
          <select
            value={selectedOptionKey}
            onChange={(event) => setSelectedOptionKey(event.target.value)}
            title="Link relationship"
            className="px-3 py-2 bg-background border border-input rounded-md text-sm"
            disabled={availableOptions.length === 0}
          >
            {availableOptions.length === 0 ? (
              <option value="">No valid roles</option>
            ) : (
              availableOptions.map((option) => (
                <option key={option.key} value={option.key}>{option.label}</option>
              ))
            )}
          </select>
        </div>
        <div className="overflow-y-auto p-3">
          {availableTargetTypes.length === 0 ? (
            <div className="p-8 text-center text-muted-foreground">No valid link targets for this artefact type yet.</div>
          ) : filteredTargets.length === 0 ? (
            <div className="p-8 text-center text-muted-foreground">No matching items for the selected kind.</div>
          ) : (
            <div className="divide-y divide-border">
              {filteredTargets.map((target) => (
                <button
                  key={`${target.doc_type}-${target.id}`}
                  onClick={() => createMutation.mutate(target)}
                  disabled={createMutation.isPending || !selectedOption}
                  className="w-full px-3 py-3 text-left hover:bg-accent/50 disabled:opacity-50"
                >
                  <div className="flex items-center justify-between gap-3">
                    <div className="min-w-0">
                      <span className="font-mono text-sm text-primary mr-2">{target.doc_id}</span>
                      <span className="text-sm font-medium text-foreground">{target.title}</span>
                    </div>
                    <span className="shrink-0 rounded border border-border px-2 py-0.5 text-[11px] font-semibold text-muted-foreground">
                      {DOC_TYPE_LABELS[target.doc_type] || target.doc_type}
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
  derivedLinks,
}: {
  projectId: number
  projectPrefix: string
  sourceType: string
  sourceId: number
  derivedLinks?: ArtefactLink[]
}) {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const [showModal, setShowModal] = useState(false)
  const canEditDocs = user?.role === 'admin' || user?.role === 'maintainer'

  const { data: outgoingLinks } = useQuery({
    queryKey: ['docLinks', projectId, sourceType, sourceId, 'outgoing'],
    queryFn: () => linksApi.list({ project_id: projectId, source_type: sourceType, source_id: sourceId }),
  })

  const { data: incomingLinks } = useQuery({
    queryKey: ['docLinks', projectId, sourceType, sourceId, 'incoming'],
    queryFn: () => linksApi.list({ project_id: projectId, target_type: sourceType, target_id: sourceId }),
  })

  const directLinkCount = (outgoingLinks?.length || 0) + (incomingLinks?.length || 0)
  const hasDerived = (derivedLinks?.length || 0) > 0
  const enabled = !!projectId && (showModal || directLinkCount > 0 || hasDerived)

  const { data: docsData } = useQuery({
    queryKey: ['all-docs', projectPrefix, 'link-targets'],
    queryFn: () => docsApi.list(projectPrefix, { includeLinkCounts: false }),
    enabled: !!projectPrefix && enabled,
  })
  const docs = useMemo(() => docsData?.items ?? [], [docsData])

  const targets = useMemo<LinkTarget[]>(() => {
    const seen = new Set<string>()
    const items: LinkTarget[] = []
    ;(docs || []).forEach((doc) => {
      const target = docShellToTarget(doc)
      if (target) {
        const key = docKey(target.doc_type, target.id)
        if (!seen.has(key)) {
          seen.add(key)
          items.push(target)
        }
      }
    })
    return items
  }, [docs])

  const deleteMutation = useMutation({
    mutationFn: linksApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['docLinks', projectId] })
    },
  })

  const targetLookup = useMemo(() => {
    const map = new Map<string, LinkTarget>()
    targets.forEach((target) => map.set(docKey(target.doc_type, target.id), target))
    return map
  }, [targets])

  const filteredDerivedLinks = useMemo(() => {
    if (!derivedLinks?.length) return []
    const directIds = new Set<number>()
    ;(outgoingLinks || []).forEach((l) => directIds.add(l.id))
    ;(incomingLinks || []).forEach((l) => directIds.add(l.id))
    return derivedLinks.filter((l) => !directIds.has(l.id))
  }, [derivedLinks, outgoingLinks, incomingLinks])

  const allLinks = useMemo(() => {
    const items: { link: ArtefactLink; direction: 'outgoing' | 'incoming'; isDerived: boolean }[] = []
    ;(outgoingLinks || []).forEach((link) => items.push({ link, direction: 'outgoing', isDerived: false }))
    ;(incomingLinks || []).forEach((link) => items.push({ link, direction: 'incoming', isDerived: false }))
    ;filteredDerivedLinks.forEach((link) => items.push({ link, direction: 'incoming', isDerived: true }))
    return items
  }, [outgoingLinks, incomingLinks, filteredDerivedLinks])

  return (
    <SectionCard
      title="Linked Documents"
      actions={canEditDocs ? (
        <button
          onClick={() => setShowModal(true)}
          className="inline-flex items-center px-3 py-2 border border-input rounded-md text-sm font-medium hover:bg-accent/50"
        >
          <Link2 className="h-4 w-4 mr-2" />
          Link Artefact
        </button>
      ) : undefined}
    >
      <p className="text-xs text-muted-foreground mb-3">Typed links to requirements, specifications, designs, risks, defects, campaigns, test suites, and other controlled documents.</p>
      {allLinks.length === 0 ? (
        <p className="text-muted-foreground">No links yet.</p>
      ) : (
        <div className="flex flex-wrap gap-1.5 -mx-6 -mb-6 px-6 pb-6">
          {allLinks.map(({ link, direction, isDerived }) => {
            const targetType = (direction === 'outgoing' ? link.target_type : link.source_type) as DocType
            const targetId = direction === 'outgoing' ? link.target_id : link.source_id
            return (
              <DocumentLinkRow
                key={`${isDerived ? 'derived' : 'direct'}-${link.id}`}
                link={link}
                target={targetLookup.get(docKey(targetType, targetId))}
                projectPrefix={projectPrefix}
                direction={direction}
                onDelete={canEditDocs && !isDerived ? () => deleteMutation.mutate(link.id) : undefined}
              />
            )
          })}
        </div>
      )}

      {canEditDocs && showModal && (
        <LinkDocumentModal
          projectId={projectId}
          sourceType={sourceType}
          sourceId={sourceId}
          targets={targets.filter((target) => !(target.doc_type === sourceType && target.id === sourceId))}
          onClose={() => setShowModal(false)}
        />
      )}
    </SectionCard>
  )
}
