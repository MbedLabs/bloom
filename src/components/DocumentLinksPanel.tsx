import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link2, Search, X } from 'lucide-react'
import {
  type ArtefactLink,
  type DocShell,
  campaignsApi,
  defectsApi,
  docsApi,
  linksApi,
  testSuitesApi,
} from '../api/client'
import {
  docUrl,
  DOC_TYPE_LABELS,
  DOC_LINK_ROLE_COLORS,
  getDocLinkOptions,
  getDocLinkRoleLabel,
  normalizeDocTypeParam,
  type DocLinkRole,
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
  const role = link.role as DocLinkRole
  const roleLabel = getDocLinkRoleLabel(link.role, direction)
  const roleColor = DOC_LINK_ROLE_COLORS[role] || 'bg-muted text-muted-foreground'

  return (
    <div className="flex items-center justify-between px-4 py-2.5 hover:bg-accent/50 transition-colors">
      <Link
        to={targetUrl(projectPrefix, otherType, target)}
        className="min-w-0 flex items-center gap-3 flex-1"
      >
        <span
          className={`shrink-0 px-1.5 py-0.5 rounded text-[10px] font-medium ${roleColor}`}
          title={roleLabel}
        >
          {roleLabel}
        </span>
        <span className="font-mono text-sm text-primary shrink-0">
          {target?.doc_id || fallbackLabel}
        </span>
        {link.suspect && (
          <span className="shrink-0 rounded-full bg-amber-500/10 px-1.5 py-0.5 text-[10px] font-medium text-amber-700 dark:text-amber-400">
            suspect
          </span>
        )}
      </Link>
      {onDelete && (
        <button
          onClick={onDelete}
          className="ml-2 p-1 rounded text-muted-foreground hover:text-red-500 hover:bg-red-500/10 shrink-0"
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

  const { data: defectsData } = useQuery({
    queryKey: ['defects', projectId, 'link-targets'],
    queryFn: () => defectsApi.list(projectId),
    enabled,
  })
  const defects = useMemo(() => defectsData?.items ?? [], [defectsData])

  const { data: campaignsData } = useQuery({
    queryKey: ['campaigns', projectId, 'link-targets'],
    queryFn: () => campaignsApi.list(projectId),
    enabled,
  })
  const campaigns = useMemo(() => campaignsData?.items ?? [], [campaignsData])

  const { data: suitesData } = useQuery({
    queryKey: ['test-suites', projectId, 'link-targets'],
    queryFn: () => testSuitesApi.list(projectId),
    enabled,
  })
  const suites = useMemo(() => suitesData?.items ?? [], [suitesData])

  const targets = useMemo<LinkTarget[]>(() => {
    const items: LinkTarget[] = []
    ;(docs || []).forEach((doc) => {
      const target = docShellToTarget(doc)
      if (target) items.push(target)
    })
    ;(defects || []).forEach((defect) =>
      items.push({
        id: defect.id,
        doc_id: defect.defect_id,
        doc_type: 'DEF',
        title: defect.title,
        status: defect.status,
      })
    )
    ;(campaigns || []).forEach((campaign) =>
      items.push({
        id: campaign.id,
        doc_id: campaign.campaign_id || `CMP-${campaign.id}`,
        doc_type: 'CMP',
        title: campaign.name,
        status: campaign.status,
      })
    )
    ;(suites || []).forEach((suite) =>
      items.push({
        id: suite.id,
        doc_id: suite.suite_id,
        doc_type: 'TS',
        title: suite.name,
        status: suite.status,
      })
    )
    return items
  }, [docs, defects, campaigns, suites])

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

  const totalCount = directLinkCount + filteredDerivedLinks.length

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
      {totalCount === 0 ? (
        <p className="text-muted-foreground">No links yet.</p>
      ) : (
        <div className="divide-y divide-border -mx-6 -mb-6">
          {(outgoingLinks || []).map((link) => (
            <DocumentLinkRow
              key={`out-${link.id}`}
              link={link}
              target={targetLookup.get(docKey(link.target_type, link.target_id))}
              projectPrefix={projectPrefix}
              direction="outgoing"
              onDelete={canEditDocs ? () => deleteMutation.mutate(link.id) : undefined}
            />
          ))}
          {(incomingLinks || []).map((link) => (
            <DocumentLinkRow
              key={`in-${link.id}`}
              link={link}
              target={targetLookup.get(docKey(link.source_type, link.source_id))}
              projectPrefix={projectPrefix}
              direction="incoming"
              onDelete={canEditDocs ? () => deleteMutation.mutate(link.id) : undefined}
            />
          ))}
          {filteredDerivedLinks.map((link) => (
            <DocumentLinkRow
              key={`derived-${link.id}`}
              link={link}
              target={targetLookup.get(docKey(link.source_type, link.source_id))}
              projectPrefix={projectPrefix}
              direction="incoming"
            />
          ))}
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
