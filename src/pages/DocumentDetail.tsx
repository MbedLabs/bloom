import { useState, useRef, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useParams, Link } from 'react-router-dom'
import { documentsApi, DocumentSection } from '../api/client'
import {
  Plus,
  Pencil,
  Trash2,
  ChevronRight,
  FileText,
  BookOpen,
  Link as LinkIcon,
  ArrowLeft,
} from 'lucide-react'

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
    <span className={`px-2.5 py-1 rounded-md text-xs font-semibold ${config[status] || config.Draft}`}>
      {status}
    </span>
  )
}

function SectionTypeBadge({ sectionType }: { sectionType: string }) {
  const config: Record<string, string> = {
    heading: 'bg-violet-500/10 text-violet-700 dark:text-violet-400',
    text: 'bg-muted text-muted-foreground',
    table: 'bg-blue-500/10 text-blue-700 dark:text-blue-400',
    requirement: 'bg-amber-500/10 text-amber-700 dark:text-amber-400',
  }

  return (
    <span className={`px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider ${config[sectionType] || config.text}`}>
      {sectionType}
    </span>
  )
}

function flattenSections(sections: DocumentSection[]): DocumentSection[] {
  const result: DocumentSection[] = []
  const walk = (items: DocumentSection[]) => {
    for (const s of items) {
      result.push(s)
      if (s.child_sections?.length) walk(s.child_sections)
    }
  }
  walk(sections)
  return result
}

interface SectionFormData {
  title: string
  content: string
  section_type: string
  linked_requirement_id: string
}

const emptySectionForm: SectionFormData = {
  title: '',
  content: '',
  section_type: 'text',
  linked_requirement_id: '',
}

function TocItem({
  section,
  depth,
  activeId,
  onClick,
}: {
  section: DocumentSection
  depth: number
  activeId: number | null
  onClick: (id: number) => void
}) {
  const isActive = section.id === activeId
  return (
    <>
      <button
        onClick={() => onClick(section.id)}
        className={`w-full text-left px-3 py-1.5 rounded-md text-xs transition-colors flex items-center gap-1.5 ${
          isActive
            ? 'bg-primary/10 text-primary font-semibold'
            : 'text-muted-foreground hover:bg-accent hover:text-foreground'
        }`}
        style={{ paddingLeft: `${depth * 12 + 12}px` }}
      >
        {section.child_sections?.length > 0 && (
          <ChevronRight className="h-3 w-3 shrink-0" />
        )}
        <span className="truncate">{section.title || 'Untitled Section'}</span>
      </button>
      {section.child_sections?.map((child) => (
        <TocItem
          key={child.id}
          section={child}
          depth={depth + 1}
          activeId={activeId}
          onClick={onClick}
        />
      ))}
    </>
  )
}

function SectionCard({
  section,
  onEdit,
  onDelete,
}: {
  section: DocumentSection
  onEdit: (section: DocumentSection) => void
  onDelete: (section: DocumentSection) => void
}) {
  return (
    <div
      id={`section-${section.id}`}
      className="bg-card border border-border rounded-lg shadow-elegant p-5 scroll-mt-4"
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2 flex-wrap">
          <h3 className="font-semibold text-foreground text-sm">{section.title}</h3>
          <SectionTypeBadge sectionType={section.section_type} />
          {section.linked_requirement_id && (
            <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-semibold bg-primary/10 text-primary">
              <LinkIcon className="h-2.5 w-2.5" />
              REQ-{section.linked_requirement_id}
            </span>
          )}
        </div>
        <div className="flex items-center gap-1 shrink-0">
          <button
            onClick={() => onEdit(section)}
            className="p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
          >
            <Pencil className="h-3.5 w-3.5" />
          </button>
          <button
            onClick={() => onDelete(section)}
            className="p-1.5 rounded-md text-muted-foreground hover:text-red-500 hover:bg-red-500/10 transition-colors"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      {section.content && (
        <div className="text-sm text-muted-foreground whitespace-pre-wrap leading-relaxed pl-0.5">
          {section.content}
        </div>
      )}

      {section.child_sections?.length > 0 && (
        <div className="mt-4 ml-4 space-y-3 border-l-2 border-border pl-4">
          {section.child_sections.map((child) => (
            <SectionCard
              key={child.id}
              section={child}
              onEdit={onEdit}
              onDelete={onDelete}
            />
          ))}
        </div>
      )}
    </div>
  )
}

export default function DocumentDetail() {
  const { id } = useParams<{ id: string }>()
  const docId = Number(id)
  const queryClient = useQueryClient()
  const [activeSectionId, setActiveSectionId] = useState<number | null>(null)
  const [showSectionModal, setShowSectionModal] = useState(false)
  const [editingSection, setEditingSection] = useState<DocumentSection | null>(null)
  const [deletingSection, setDeletingSection] = useState<DocumentSection | null>(null)
  const [sectionForm, setSectionForm] = useState<SectionFormData>(emptySectionForm)
  const contentRef = useRef<HTMLDivElement>(null)

  const { data: doc, isLoading } = useQuery({
    queryKey: ['document', docId],
    queryFn: () => documentsApi.get(docId),
    enabled: !!docId,
  })

  const addSectionMutation = useMutation({
    mutationFn: (data: { title: string; content?: string; section_type?: string; linked_requirement_id?: number }) =>
      documentsApi.addSection(docId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['document', docId] })
      closeSectionModal()
    },
  })

  const updateSectionMutation = useMutation({
    mutationFn: ({ sectionId, data }: { sectionId: number; data: Partial<DocumentSection> }) =>
      documentsApi.updateSection(sectionId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['document', docId] })
      closeSectionModal()
    },
  })

  const deleteSectionMutation = useMutation({
    mutationFn: (sectionId: number) => documentsApi.deleteSection(sectionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['document', docId] })
      setDeletingSection(null)
    },
  })

  useEffect(() => {
    if (!contentRef.current || !doc?.sections?.length) return
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            const sectionId = Number(entry.target.id.replace('section-', ''))
            setActiveSectionId(sectionId)
          }
        }
      },
      { root: contentRef.current, threshold: 0.3 }
    )
    const flat = flattenSections(doc.sections)
    for (const s of flat) {
      const el = globalThis.document.getElementById(`section-${s.id}`)
      if (el) observer.observe(el)
    }
    return () => observer.disconnect()
  }, [doc])

  const scrollToSection = (sectionId: number) => {
    setActiveSectionId(sectionId)
    const el = globalThis.document.getElementById(`section-${sectionId}`)
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  const openAddSectionModal = () => {
    setEditingSection(null)
    setSectionForm(emptySectionForm)
    setShowSectionModal(true)
  }

  const openEditSectionModal = (section: DocumentSection) => {
    setEditingSection(section)
    setSectionForm({
      title: section.title,
      content: section.content || '',
      section_type: section.section_type,
      linked_requirement_id: section.linked_requirement_id?.toString() || '',
    })
    setShowSectionModal(true)
  }

  const closeSectionModal = () => {
    setShowSectionModal(false)
    setEditingSection(null)
    setSectionForm(emptySectionForm)
  }

  const handleSectionSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const linkedReqId = sectionForm.linked_requirement_id
      ? Number(sectionForm.linked_requirement_id)
      : undefined

    if (editingSection) {
      updateSectionMutation.mutate({
        sectionId: editingSection.id,
        data: {
          title: sectionForm.title,
          content: sectionForm.content || null,
          section_type: sectionForm.section_type,
          linked_requirement_id: linkedReqId ?? null,
        },
      })
    } else {
      addSectionMutation.mutate({
        title: sectionForm.title,
        content: sectionForm.content || undefined,
        section_type: sectionForm.section_type,
        linked_requirement_id: linkedReqId,
      })
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64 animate-fade-in">
        <div className="text-muted-foreground">Loading document...</div>
      </div>
    )
  }

  if (!doc) {
    return (
      <div className="flex items-center justify-center h-64 animate-fade-in">
        <div className="text-center">
          <h3 className="text-lg font-semibold text-foreground mb-2">Document not found</h3>
          <Link to="/" className="text-sm text-primary hover:text-primary/80 transition-colors">
            &larr; Back to Dashboard
          </Link>
        </div>
      </div>
    )
  }

  const flatSections = flattenSections(doc.sections)

  return (
    <div className="animate-fade-in -m-6">
      <div className="flex h-[calc(100vh-8rem)]">
        {/* Sidebar */}
        <div className="w-64 border-r border-border bg-card/50 flex flex-col shrink-0">
          <div className="p-4 border-b border-border">
            <Link
              to={`/projects/${doc.project_id}/documents`}
              className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-primary transition-colors mb-3"
            >
              <ArrowLeft className="h-3 w-3" />
              Back to documents
            </Link>
            <h2 className="font-semibold text-foreground text-sm truncate">{doc.title}</h2>
            <div className="flex items-center gap-2 mt-2">
              <DocTypeBadge docType={doc.doc_type} />
              <DocStatusBadge status={doc.status} />
            </div>
            <div className="mt-2 text-[11px] text-muted-foreground">
              Version {doc.version}
            </div>
          </div>

          <div className="p-3 border-b border-border">
            <div className="flex items-center justify-between mb-2">
              <span className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider">
                Outline
              </span>
              <button
                onClick={openAddSectionModal}
                className="p-1 rounded text-muted-foreground hover:text-primary hover:bg-primary/10 transition-colors"
              >
                <Plus className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-2 space-y-0.5">
            {doc.sections.length === 0 ? (
              <p className="text-xs text-muted-foreground p-3">No sections yet</p>
            ) : (
              doc.sections.map((section) => (
                <TocItem
                  key={section.id}
                  section={section}
                  depth={0}
                  activeId={activeSectionId}
                  onClick={scrollToSection}
                />
              ))
            )}
          </div>
        </div>

        {/* Main Content */}
        <div className="flex-1 flex flex-col min-w-0">
          <div className="border-b border-border bg-card px-8 py-5">
            <div className="flex items-center justify-between">
              <div>
                <div className="flex items-center gap-3 mb-1">
                  <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
                    <BookOpen className="h-4 w-4 text-primary" />
                  </div>
                  <h1 className="text-lg font-bold text-foreground">{doc.title}</h1>
                </div>
                {doc.description && (
                  <p className="text-sm text-muted-foreground mt-1 ml-11">{doc.description}</p>
                )}
              </div>
              <button
                onClick={openAddSectionModal}
                className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 hover:shadow-glow transition-all duration-200"
              >
                <Plus className="h-4 w-4" />
                Add Section
              </button>
            </div>
          </div>

          <div ref={contentRef} className="flex-1 overflow-y-auto p-8">
            {flatSections.length === 0 ? (
              <div className="bg-card rounded-lg border border-border shadow-elegant p-16 text-center">
                <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary/10 to-cyan-500/10 flex items-center justify-center mx-auto mb-4">
                  <FileText className="h-8 w-8 text-primary/40" />
                </div>
                <h3 className="text-lg font-semibold text-foreground mb-2">No Sections Yet</h3>
                <p className="text-sm text-muted-foreground mb-5 max-w-md mx-auto">
                  Start building your document by adding sections.
                </p>
                <button
                  onClick={openAddSectionModal}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 transition-colors"
                >
                  <Plus className="h-4 w-4" />
                  Add Section
                </button>
              </div>
            ) : (
              <div className="space-y-4 max-w-4xl">
                {doc.sections
                  .sort((a, b) => a.order - b.order)
                  .map((section) => (
                    <SectionCard
                      key={section.id}
                      section={section}
                      onEdit={openEditSectionModal}
                      onDelete={setDeletingSection}
                    />
                  ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Section Modal */}
      {showSectionModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-card border border-border rounded-xl shadow-glow max-w-lg w-full mx-4 animate-fade-in">
            <div className="px-6 py-4 border-b border-border">
              <h3 className="text-lg font-semibold text-foreground">
                {editingSection ? 'Edit Section' : 'New Section'}
              </h3>
              <p className="text-xs text-muted-foreground mt-0.5">
                {editingSection ? 'Update section details' : 'Add a new section to this document'}
              </p>
            </div>
            <form onSubmit={handleSectionSubmit}>
              <div className="p-6 space-y-4">
                <div>
                  <label className="block text-xs font-medium text-muted-foreground uppercase tracking-wider mb-1.5">
                    Title
                  </label>
                  <input
                    type="text"
                    required
                    value={sectionForm.title}
                    onChange={(e) => setSectionForm({ ...sectionForm, title: e.target.value })}
                    className="w-full px-3 py-2 bg-background border border-input rounded-md text-sm text-foreground placeholder:text-muted-foreground focus:ring-2 focus:ring-ring focus:border-ring transition-colors"
                    placeholder="Section title"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-muted-foreground uppercase tracking-wider mb-1.5">
                    Type
                  </label>
                  <select
                    value={sectionForm.section_type}
                    onChange={(e) => setSectionForm({ ...sectionForm, section_type: e.target.value })}
                    className="w-full px-3 py-2 bg-background border border-input rounded-md text-sm text-foreground focus:ring-2 focus:ring-ring focus:border-ring transition-colors"
                  >
                    <option value="text">Text</option>
                    <option value="heading">Heading</option>
                    <option value="table">Table</option>
                    <option value="requirement">Requirement</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-muted-foreground uppercase tracking-wider mb-1.5">
                    Content
                  </label>
                  <textarea
                    value={sectionForm.content}
                    onChange={(e) => setSectionForm({ ...sectionForm, content: e.target.value })}
                    className="w-full px-3 py-2 bg-background border border-input rounded-md text-sm text-foreground placeholder:text-muted-foreground focus:ring-2 focus:ring-ring focus:border-ring transition-colors"
                    rows={6}
                    placeholder="Section content..."
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-muted-foreground uppercase tracking-wider mb-1.5">
                    Linked Requirement ID
                  </label>
                  <input
                    type="number"
                    value={sectionForm.linked_requirement_id}
                    onChange={(e) => setSectionForm({ ...sectionForm, linked_requirement_id: e.target.value })}
                    className="w-full px-3 py-2 bg-background border border-input rounded-md text-sm text-foreground placeholder:text-muted-foreground focus:ring-2 focus:ring-ring focus:border-ring transition-colors"
                    placeholder="Optional requirement ID"
                  />
                </div>
              </div>
              <div className="px-6 py-4 border-t border-border flex justify-end gap-3">
                <button
                  type="button"
                  onClick={closeSectionModal}
                  className="px-4 py-2 border border-border rounded-md text-sm text-muted-foreground hover:bg-accent transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={addSectionMutation.isPending || updateSectionMutation.isPending}
                  className="px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 disabled:opacity-50 transition-colors"
                >
                  {addSectionMutation.isPending || updateSectionMutation.isPending
                    ? 'Saving...'
                    : editingSection
                      ? 'Update Section'
                      : 'Add Section'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Confirmation */}
      {deletingSection && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-card border border-border rounded-xl shadow-glow max-w-sm w-full mx-4 animate-fade-in">
            <div className="p-6">
              <h3 className="text-lg font-semibold text-foreground mb-2">Delete Section</h3>
              <p className="text-sm text-muted-foreground">
                Are you sure you want to delete &ldquo;{deletingSection.title}&rdquo;? This action cannot be undone.
              </p>
            </div>
            <div className="px-6 py-4 border-t border-border flex justify-end gap-3">
              <button
                onClick={() => setDeletingSection(null)}
                className="px-4 py-2 border border-border rounded-md text-sm text-muted-foreground hover:bg-accent transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => deleteSectionMutation.mutate(deletingSection.id)}
                disabled={deleteSectionMutation.isPending}
                className="px-4 py-2 bg-red-500 text-white rounded-md text-sm font-medium hover:bg-red-600 disabled:opacity-50 transition-colors"
              >
                {deleteSectionMutation.isPending ? 'Deleting...' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
