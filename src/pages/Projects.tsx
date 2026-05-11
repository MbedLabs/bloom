import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { extractApiErrorMessage, projectsApi, type Project } from '../api/client'
import { Plus, FolderKanban, Search, FileText, CheckCircle, ArrowRight, Pencil } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'

const PROJECT_PREFIX_PATTERN = /^[A-Z]{3}$/
const PROJECT_PREFIX_ERROR = 'Use exactly three uppercase letters, e.g. PRJ.'

export default function Projects() {
  const { user } = useAuth()
  const canManageProjects = user?.role === 'admin'
  const canCreateProjects = user?.role === 'admin' || user?.role === 'maintainer'
  const navigate = useNavigate()
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [name, setName] = useState('')
  const [prefix, setPrefix] = useState('')
  const [description, setDescription] = useState('')
  const [search, setSearch] = useState('')
  const [formError, setFormError] = useState('')
  const queryClient = useQueryClient()

  const { data: projects, isLoading } = useQuery({
    queryKey: ['projects'],
    queryFn: projectsApi.list,
  })

  const createMutation = useMutation({
    mutationFn: projectsApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] })
      setFormError('')
      setShowCreateModal(false)
      setName('')
      setPrefix('')
      setDescription('')
    },
    onError: (error) => {
      setFormError(extractApiErrorMessage(error, 'Could not create project'))
    },
  })

  const filteredProjects = search
    ? projects?.filter(p =>
        p.name.toLowerCase().includes(search.toLowerCase()) ||
        p.prefix.toLowerCase().includes(search.toLowerCase())
      )
    : projects

  const normalizedPrefix = prefix.trim().toUpperCase()
  const prefixIsValid = PROJECT_PREFIX_PATTERN.test(normalizedPrefix)
  const showPrefixError = prefix.length > 0 && !prefixIsValid

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setFormError('')
    if (!prefixIsValid) {
      setFormError(PROJECT_PREFIX_ERROR)
      return
    }

    createMutation.mutate({ name, prefix: normalizedPrefix, description: description || undefined })
  }

  const openCreateModal = () => {
    setFormError('')
    setName('')
    setPrefix('')
    setDescription('')
    setShowCreateModal(true)
  }

  const closeModal = () => {
    setFormError('')
    setShowCreateModal(false)
    setName('')
    setPrefix('')
    setDescription('')
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-xl font-bold text-foreground">Projects</h2>
          <p className="text-sm text-muted-foreground mt-0.5">{projects?.length || 0} projects total</p>
        </div>
        {canCreateProjects && (
          <button
            onClick={openCreateModal}
            className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 hover:shadow-glow transition-all duration-200"
          >
            <Plus className="h-4 w-4" />
            New Project
          </button>
        )}
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <input
          type="text"
          placeholder="Search projects..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full pl-9 pr-4 py-2.5 bg-card border border-border rounded-lg text-sm text-foreground placeholder:text-muted-foreground focus:ring-2 focus:ring-ring focus:border-ring transition-colors shadow-elegant"
        />
      </div>

      {/* Project Grid */}
      {isLoading ? (
        <div className="bg-card rounded-lg border border-border shadow-elegant p-8 text-center text-muted-foreground">
          Loading...
        </div>
      ) : !filteredProjects || filteredProjects.length === 0 ? (
        <div className="bg-card rounded-lg border border-border shadow-elegant p-16 text-center">
          <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-primary/10 to-cyan-500/10 flex items-center justify-center mx-auto mb-5">
            <FolderKanban className="h-10 w-10 text-primary/40" />
          </div>
          <h3 className="text-lg font-semibold text-foreground mb-2">
            {search ? 'No projects found' : 'No Projects Yet'}
          </h3>
          <p className="text-sm text-muted-foreground mb-5 max-w-md mx-auto">
            {search ? 'Try a different search term.' : 'Create your first project to start managing requirements and test cases.'}
          </p>
          {!search && canCreateProjects && (
            <button
              onClick={openCreateModal}
              className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 transition-colors"
            >
              <Plus className="h-4 w-4" />
              New Project
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredProjects.map((project) => (
            <ProjectCard
              key={project.id}
              project={project}
              canEdit={canManageProjects}
              onEdit={() => navigate(`/projects/${project.prefix}/edit`)}
            />
          ))}
        </div>
      )}

      {/* Create Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-card border border-border rounded-xl shadow-glow max-w-md w-full mx-4 animate-fade-in">
            <div className="px-6 py-4 border-b border-border">
              <h3 className="text-lg font-semibold text-foreground">New Project</h3>
              <p className="text-xs text-muted-foreground mt-0.5">Create a new project</p>
            </div>
            <form onSubmit={handleSubmit}>
              <div className="p-6 space-y-4">
                {formError && (
                  <div className="rounded-md border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-600">
                    {formError}
                  </div>
                )}
                <div>
                  <label className="block text-xs font-medium text-muted-foreground uppercase tracking-wider mb-1.5">Name</label>
                  <input
                    type="text"
                    required
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="w-full px-3 py-2 bg-background border border-input rounded-md text-sm text-foreground placeholder:text-muted-foreground focus:ring-2 focus:ring-ring focus:border-ring transition-colors"
                    placeholder="My Project"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-muted-foreground uppercase tracking-wider mb-1.5">Prefix</label>
                  <input
                    type="text"
                    required
                    value={prefix}
                    onChange={(e) => setPrefix(e.target.value.toUpperCase())}
                    className={`w-full px-3 py-2 bg-background border rounded-md text-sm text-foreground placeholder:text-muted-foreground focus:ring-2 focus:ring-ring focus:border-ring transition-colors font-mono ${
                      showPrefixError ? 'border-red-500/70' : 'border-input'
                    }`}
                    placeholder="PRJ"
                    maxLength={3}
                    aria-invalid={showPrefixError}
                  />
                  <p className={`mt-1 text-xs ${showPrefixError ? 'text-red-600' : 'text-muted-foreground'}`}>
                    {showPrefixError ? PROJECT_PREFIX_ERROR : 'Item IDs use PRJ-TYP-001.'}
                  </p>
                </div>
                <div>
                  <label className="block text-xs font-medium text-muted-foreground uppercase tracking-wider mb-1.5">Description</label>
                  <textarea
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    className="w-full px-3 py-2 bg-background border border-input rounded-md text-sm text-foreground placeholder:text-muted-foreground focus:ring-2 focus:ring-ring focus:border-ring transition-colors"
                    rows={3}
                    placeholder="Project description..."
                  />
                </div>
              </div>
              <div className="px-6 py-4 border-t border-border flex justify-end gap-3">
                <button
                  type="button"
                  onClick={closeModal}
                  className="px-4 py-2 border border-border rounded-md text-sm text-muted-foreground hover:bg-accent transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createMutation.isPending || !prefixIsValid}
                  className="px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 disabled:opacity-50 transition-colors"
                >
                  {createMutation.isPending ? 'Creating...' : 'Create Project'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

function ProjectCard({
  project,
  canEdit,
  onEdit,
}: {
  project: Project
  canEdit: boolean
  onEdit: () => void
}) {
  const navigate = useNavigate()
  const coverage = project.requirement_count > 0
    ? Math.min(100, Math.round((project.test_case_count / project.requirement_count) * 100))
    : 0

  return (
    <div
      className="group bg-card rounded-lg border border-border shadow-elegant hover:shadow-glow hover:border-primary/20 transition-all duration-300 overflow-hidden cursor-pointer"
      onClick={() => navigate(`/projects/${project.prefix}`)}
    >
      <div className={`h-1 ${
        project.status === 'Active' ? 'bg-gradient-to-r from-primary via-teal-500 to-cyan-500' : 'bg-muted'
      }`} />

      <div className="p-5">
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-primary/10 flex items-center justify-center group-hover:bg-primary/20 transition-colors">
              <FolderKanban className="h-4 w-4 text-primary" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-semibold text-foreground text-sm group-hover:text-primary transition-colors">{project.name}</h3>
                {canEdit && (
                  <button
                    type="button"
                    onClick={(e) => { e.stopPropagation(); onEdit() }}
                    className="inline-flex h-7 w-7 items-center justify-center rounded-md border border-border text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
                    title="Edit project"
                  >
                    <Pencil className="h-3.5 w-3.5" />
                  </button>
                )}
              </div>
              <span className="text-xs text-muted-foreground font-mono">{project.prefix}</span>
            </div>
          </div>
          <ProjectStatusBadge status={project.status} />
        </div>

        {project.description && (
          <p className="text-xs text-muted-foreground mb-4 line-clamp-2">{project.description}</p>
        )}

        {/* Stats */}
        <div className="flex items-center gap-4 text-xs text-muted-foreground mb-3">
          <div className="flex items-center gap-1">
            <FileText className="h-3.5 w-3.5" />
            {project.requirement_count} reqs
          </div>
          <div className="flex items-center gap-1">
            <CheckCircle className="h-3.5 w-3.5" />
            {project.test_case_count} TCs
          </div>
        </div>

        {/* Coverage bar */}
        <div className="flex items-center gap-2">
          <div className="flex-1 h-1.5 bg-muted rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${
                coverage >= 80 ? 'bg-gradient-to-r from-emerald-500 to-teal-400' : coverage >= 50 ? 'bg-gradient-to-r from-amber-500 to-amber-400' : 'bg-gradient-to-r from-red-400 to-red-300'
              }`}
              style={{ width: `${Math.max(coverage, 3)}%` }}
            />
          </div>
          <span className="text-[11px] text-muted-foreground font-medium">{coverage}%</span>
        </div>

        {/* Arrow */}
        <div className="flex justify-end mt-3">
          <button
            type="button"
            onClick={() => navigate(`/projects/${project.prefix}`)}
            className="inline-flex items-center gap-1 text-sm text-primary hover:text-primary/80 transition-colors"
          >
            Open
            <ArrowRight className="h-4 w-4 transition-all duration-200 -translate-x-1 group-hover:translate-x-0" />
          </button>
        </div>
      </div>
    </div>
  )
}

function ProjectStatusBadge({ status }: { status: string }) {
  const config: Record<string, string> = {
    Active: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400',
    Archived: 'bg-muted text-muted-foreground',
    Draft: 'bg-amber-500/10 text-amber-700 dark:text-amber-400',
  }

  return (
    <span className={`px-2 py-0.5 rounded-md text-[11px] font-semibold ${config[status] || config.Draft}`}>
      {status}
    </span>
  )
}
