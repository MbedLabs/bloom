import { useMemo, useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { documentsApi, DocumentSection, projectVariablesApi } from '../api/client'
import { Trash2, ChevronRight, FileText, BookOpen, ArrowLeft, Save, PenLine } from 'lucide-react'

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

function SectionTypeBadge({ sectionType }: { sectionType: string }) {
  const config: Record<string, string> = {
    heading: 'bg-violet-500/10 text-violet-700 dark:text-violet-400',
    text: 'bg-muted text-muted-foreground',
    table: 'bg-blue-500/10 text-blue-700 dark:text-blue-400',
    requirement: 'bg-amber-500/10 text-amber-700 dark:text-amber-400',
  }
  return <span className={`px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider ${config[sectionType] || config.text}`}>{sectionType}</span>
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

function TocItem({ section, depth, activeId, onClick }: { section: DocumentSection; depth: number; activeId: number | null; onClick: (id: number) => void }) {
  const isActive = section.id === activeId
  return (
    <>
      <button
        onClick={() => onClick(section.id)}
        className={`w-full text-left px-3 py-1.5 rounded-md text-xs transition-colors flex items-center gap-1.5 ${isActive ? 'bg-primary/10 text-primary font-semibold' : 'text-muted-foreground hover:bg-accent hover:text-foreground'}`}
        style={{ paddingLeft: `${depth * 12 + 12}px` }}
      >
        {section.child_sections?.length > 0 && <ChevronRight className="h-3 w-3 shrink-0" />}
        <span className="truncate">{section.title || 'Untitled Section'}</span>
      </button>
      {section.child_sections?.map((child) => (
        <TocItem key={child.id} section={child} depth={depth + 1} activeId={activeId} onClick={onClick} />
      ))}
    </>
  )
}

function SectionCard({ section, selectedSectionId, onSelect }: { section: DocumentSection; selectedSectionId: number | null; onSelect: (section: DocumentSection) => void }) {
  const isSelected = section.id === selectedSectionId
  return (
    <div
      id={`section-${section.id}`}
      className={`bg-card border rounded-lg shadow-elegant p-5 scroll-mt-4 cursor-pointer transition-colors ${isSelected ? 'border-primary/60 bg-primary/5' : 'border-border hover:border-primary/30'}`}
      onClick={() => onSelect(section)}
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2 flex-wrap">
          <h3 className="font-semibold text-foreground text-sm">{section.title}</h3>
          <SectionTypeBadge sectionType={section.section_type} />
        </div>
      </div>
      {section.content && <pre className="text-sm text-muted-foreground leading-relaxed whitespace-pre-wrap pl-0.5">{section.content}</pre>}
      {section.child_sections?.length > 0 && (
        <div className="mt-4 ml-4 space-y-3 border-l-2 border-border pl-4">
          {section.child_sections.map((child) => (
            <SectionCard key={child.id} section={child} selectedSectionId={selectedSectionId} onSelect={onSelect} />
          ))}
        </div>
      )}
    </div>
  )
}

export default function DocumentDetail() {
  const { docId: docIdParam } = useParams<{ id: string; docId: string }>()
  const docId = Number(docIdParam)
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [activeSectionId, setActiveSectionId] = useState<number | null>(null)
  const [draft, setDraft] = useState({ title: '', content: '', section_type: 'text' })

  const { data: doc, isLoading } = useQuery({ queryKey: ['document', docId], queryFn: () => documentsApi.get(docId), enabled: !!docId })

  const { data: projectVariables } = useQuery({
    queryKey: ['projectVariables', doc?.project_id],
    queryFn: () => projectVariablesApi.list(doc!.project_id),
    enabled: !!doc?.project_id,
  })

  const updateSectionMutation = useMutation({
    mutationFn: ({ sectionId, data }: { sectionId: number; data: Partial<DocumentSection> }) => documentsApi.updateSection(sectionId, data),
    onSuccess: (_result, variables) => {
      queryClient.invalidateQueries({ queryKey: ['document', docId] })
      setActiveSectionId(variables.sectionId)
    },
  })

  const deleteSectionMutation = useMutation({
    mutationFn: (sectionId: number) => documentsApi.deleteSection(sectionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['document', docId] })
      setActiveSectionId(null)
    },
  })

  const deleteDocumentMutation = useMutation({
    mutationFn: () => documentsApi.delete(docId),
    onSuccess: () => {
      if (doc?.project_id) {
        queryClient.invalidateQueries({ queryKey: ['documents', doc.project_id] })
        navigate(`/projects/${doc.project_id}/documents`)
      } else {
        navigate('/projects')
      }
    },
  })

  const flatSections = useMemo(() => flattenSections(doc?.sections || []), [doc?.sections])
  const selectedSection = flatSections.find((s) => s.id === activeSectionId) || null

  useEffect(() => {
    if (!doc?.sections?.length) return
    const selected = activeSectionId ? flatSections.find((s) => s.id === activeSectionId) : flatSections[0]
    if (selected) {
      setActiveSectionId(selected.id)
      setDraft({ title: selected.title, content: selected.content || '', section_type: selected.section_type })
    }
  }, [doc?.sections, activeSectionId, flatSections])

  const topSections = useMemo(() => [...(doc?.sections || [])].sort((a, b) => a.order - b.order), [doc?.sections])

  const scrollToSection = (sectionId: number) => {
    setActiveSectionId(sectionId)
    const s = flatSections.find((item) => item.id === sectionId)
    if (s) {
      setDraft({ title: s.title, content: s.content || '', section_type: s.section_type })
    }
    const el = globalThis.document.getElementById(`section-${sectionId}`)
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  const saveSelectedSection = () => {
    if (!selectedSection) return
    updateSectionMutation.mutate({
      sectionId: selectedSection.id,
      data: {
        title: draft.title,
        content: draft.content || null,
        section_type: draft.section_type,
      },
    })
  }

  const insertVariableToken = (key: string) => {
    const token = `{{${key}}}`
    setDraft((prev) => ({ ...prev, content: `${prev.content}${prev.content ? '\n' : ''}${token}` }))
  }

  const deleteSelectedSection = () => {
    if (!selectedSection) return
    if (!window.confirm(`Delete section \"${selectedSection.title}\"?`)) return
    deleteSectionMutation.mutate(selectedSection.id)
  }

  const deleteDocument = () => {
    if (!window.confirm(`Delete document \"${doc?.title || 'Untitled'}\"?`)) return
    deleteDocumentMutation.mutate()
  }

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
    <div className="animate-fade-in -m-6">
      <div className="flex min-h-[calc(100vh-8rem)]">
        <div className="w-64 border-r border-border bg-card/70 flex flex-col shrink-0">
          <div className="p-4 border-b border-border">
            <Link to={`/projects/${doc.project_id}/documents`} className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-primary transition-colors mb-3">
              <ArrowLeft className="h-3 w-3" />
              Back to documents
            </Link>
            <h2 className="font-semibold text-foreground text-sm truncate">{doc.title}</h2>
            <div className="flex items-center gap-2 mt-2">
              <DocTypeBadge docType={doc.doc_type} />
              <DocStatusBadge status={doc.status} />
            </div>
            <div className="mt-2 text-[11px] text-muted-foreground">Version {doc.version}</div>
          </div>

          <div className="p-3 border-b border-border">
            <div className="flex items-center justify-between mb-2">
              <span className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider">Outline</span>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-2 space-y-0.5">
            {doc.sections.length === 0 ? <p className="text-xs text-muted-foreground p-3">No sections yet</p> : topSections.map((section) => (
              <TocItem key={section.id} section={section} depth={0} activeId={activeSectionId} onClick={scrollToSection} />
            ))}
          </div>
        </div>

        <div className="flex-1 flex flex-col min-w-0">
          <div className="border-b border-border bg-card px-8 py-5">
            <div className="flex items-center justify-between gap-4">
              <div>
                <div className="flex items-center gap-3 mb-1">
                  <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center"><BookOpen className="h-4 w-4 text-primary" /></div>
                  <h1 className="text-lg font-bold text-foreground">{doc.title}</h1>
                </div>
                {doc.description && <p className="text-sm text-muted-foreground mt-1 ml-11">{doc.description}</p>}
              </div>
            </div>
            <div className="mt-3 flex justify-end">
              <button
                onClick={deleteDocument}
                disabled={deleteDocumentMutation.isPending}
                className="inline-flex items-center gap-2 px-3 py-2 border border-red-500/50 text-red-600 rounded-md text-sm hover:bg-red-500/10 disabled:opacity-50"
              >
                <Trash2 className="h-4 w-4" />
                {deleteDocumentMutation.isPending ? 'Deleting...' : 'Delete Document'}
              </button>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-8 pb-16">
            {flatSections.length === 0 ? (
              <div className="bg-card rounded-lg border border-border shadow-elegant p-16 text-center">
                <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary/10 to-cyan-500/10 flex items-center justify-center mx-auto mb-4"><FileText className="h-8 w-8 text-primary/40" /></div>
                <h3 className="text-lg font-semibold text-foreground mb-2">No Sections Yet</h3>
                <p className="text-sm text-muted-foreground max-w-md mx-auto">This document currently has no sections.</p>
              </div>
            ) : (
              <div className="space-y-5 max-w-6xl">
                <div className="bg-card border border-border rounded-lg p-5 shadow-elegant">
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="text-sm font-semibold text-foreground flex items-center gap-2"><PenLine className="h-4 w-4 text-primary" />Full-Page Editor</h3>
                    {selectedSection && <SectionTypeBadge sectionType={draft.section_type} />}
                  </div>

                  {selectedSection ? (
                    <div className="space-y-4">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                          <label className="block text-xs font-medium text-muted-foreground uppercase tracking-wider mb-1.5">Section Title</label>
                          <input value={draft.title} onChange={(e) => setDraft({ ...draft, title: e.target.value })} className="w-full px-3 py-2 bg-background border border-input rounded-md text-sm" />
                        </div>
                        <div>
                          <label className="block text-xs font-medium text-muted-foreground uppercase tracking-wider mb-1.5">Section Type</label>
                          <select value={draft.section_type} onChange={(e) => setDraft({ ...draft, section_type: e.target.value })} className="w-full px-3 py-2 bg-background border border-input rounded-md text-sm">
                            <option value="text">Text</option>
                            <option value="heading">Heading</option>
                            <option value="table">Table</option>
                            <option value="requirement">Requirement</option>
                          </select>
                        </div>
                      </div>

                      <div>
                        <label className="block text-xs font-medium text-muted-foreground uppercase tracking-wider mb-1.5">Content</label>
                        <textarea value={draft.content} onChange={(e) => setDraft({ ...draft, content: e.target.value })} rows={18} className="w-full px-3 py-2 bg-background border border-input rounded-md text-sm leading-6" placeholder="Write section content..." />
                      </div>

                      <div className="bg-background border border-border rounded-md p-3">
                        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Project Parameters</p>
                        {!projectVariables || projectVariables.length === 0 ? (
                          <p className="text-xs text-muted-foreground">No project parameters configured yet. Add them in Parameters page.</p>
                        ) : (
                          <div className="flex flex-wrap gap-2">
                            {projectVariables.map((item) => (
                              <button
                                key={item.id}
                                onClick={() => insertVariableToken(item.key)}
                                className="px-2 py-1 rounded border border-input bg-card text-xs text-foreground hover:border-primary/40 hover:bg-primary/5"
                                title={item.description || ''}
                              >
                                {item.key}
                              </button>
                            ))}
                          </div>
                        )}
                      </div>

                      <div className="flex items-center gap-3">
                        <button onClick={saveSelectedSection} disabled={updateSectionMutation.isPending} className="inline-flex items-center px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 disabled:opacity-50">
                          <Save className="h-4 w-4 mr-2" />
                          {updateSectionMutation.isPending ? 'Saving...' : 'Save Section'}
                        </button>
                        <button onClick={deleteSelectedSection} disabled={deleteSectionMutation.isPending} className="inline-flex items-center px-3 py-2 border border-red-500/50 text-red-600 rounded-md text-sm hover:bg-red-500/10 disabled:opacity-50">
                          <Trash2 className="h-4 w-4 mr-1" />
                          Delete
                        </button>
                      </div>
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground">Select a section from outline or cards to edit.</p>
                  )}
                </div>

                <div className="space-y-4">
                  {topSections.map((section) => (
                    <SectionCard
                      key={section.id}
                      section={section}
                      selectedSectionId={activeSectionId}
                      onSelect={(s) => {
                        setActiveSectionId(s.id)
                        setDraft({ title: s.title, content: s.content || '', section_type: s.section_type })
                      }}
                    />
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
