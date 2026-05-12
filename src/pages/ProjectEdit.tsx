import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { extractApiErrorMessage, projectsApi } from '../api/client'
import { useAuth } from '../contexts/AuthContext'
import { useProjectByPrefix } from '../hooks/useProjectByPrefix'
import {
  projectDeleteConfirmationMatches,
  projectDeleteConfirmationPhrase,
} from '../lib/projectDelete'
import IntegrationSettingsPanel from '../components/IntegrationSettingsPanel'

const PROJECT_PREFIX_PATTERN = /^[A-Z]{3}$/
const PROJECT_PREFIX_ERROR = 'Use exactly three uppercase letters, e.g. PRJ.'

const STATUS_OPTIONS = ['Active', 'Archived', 'Draft'] as const

export default function ProjectEdit() {
  const { prefix } = useParams<{ prefix: string }>()
  const navigate = useNavigate()
  const { user } = useAuth()
  const { data: project, isLoading } = useProjectByPrefix(prefix)
  const queryClient = useQueryClient()

  const [name, setName] = useState('')
  const [projectPrefix, setProjectPrefix] = useState('')
  const [description, setDescription] = useState('')
  const [status, setStatus] = useState('Active')
  const [formError, setFormError] = useState('')
  const [confirmDeleteOpen, setConfirmDeleteOpen] = useState(false)
  const [deleteConfirmationText, setDeleteConfirmationText] = useState('')
  const [deleteExpectedPhrase, setDeleteExpectedPhrase] = useState('')
  const [deleteError, setDeleteError] = useState('')

  useEffect(() => {
    if (!project) return
    setName(project.name)
    setProjectPrefix(project.prefix)
    setDescription(project.description || '')
    setStatus(project.status || 'Active')
  }, [project])

  const normalizedPrefix = projectPrefix.trim().toUpperCase()
  const prefixIsValid = PROJECT_PREFIX_PATTERN.test(normalizedPrefix)
  const showPrefixError = projectPrefix.length > 0 && !prefixIsValid

  const updateMutation = useMutation({
    mutationFn: () =>
      projectsApi.update(project!.id, {
        name,
        prefix: normalizedPrefix,
        description: description || undefined,
        status,
      }),
    onSuccess: (updated) => {
      setFormError('')
      queryClient.invalidateQueries({ queryKey: ['projects'] })
      queryClient.invalidateQueries({ queryKey: ['project-by-prefix', prefix] })
      queryClient.invalidateQueries({ queryKey: ['project-by-prefix', updated.prefix] })
      if (updated.prefix !== prefix) {
        navigate(`/projects/${updated.prefix}/edit`, { replace: true })
      }
    },
    onError: (error) => {
      setFormError(extractApiErrorMessage(error, 'Could not update project'))
    },
  })

  const deleteMutation = useMutation({
    mutationFn: () => projectsApi.delete(project!.id),
    onSuccess: () => {
      setDeleteError('')
      queryClient.invalidateQueries({ queryKey: ['projects'] })
      navigate('/projects', { replace: true })
    },
    onError: (error) => {
      setDeleteError(extractApiErrorMessage(error, 'Could not delete project'))
    },
  })

  const isAdmin = user?.role === 'admin'

  const { data: projectList } = useQuery({
    queryKey: ['projects'],
    queryFn: projectsApi.list,
    enabled: isAdmin,
  })

  if (isLoading) {
    return <div className="flex items-center justify-center h-64 text-muted-foreground">Loading...</div>
  }

  if (!project) {
    return (
      <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-6 text-center">
        <h3 className="text-lg font-medium text-destructive">Project Not Found</h3>
        <Link to="/projects" className="mt-4 inline-block text-primary hover:text-primary/80">
          &larr; Back to Projects
        </Link>
      </div>
    )
  }

  if (!isAdmin) {
    return (
      <div className="space-y-4 animate-fade-in">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Link to={`/projects/${prefix}`} className="hover:text-primary transition-colors">
            {project.name}
          </Link>
          <span>/</span>
          <span className="text-foreground">Edit project</span>
        </div>
        <div className="rounded-lg border border-border bg-card p-6 text-sm text-muted-foreground">
          Only administrators can edit project details. You can still view integration status below if applicable.
        </div>
        <IntegrationSettingsPanel projectId={project.id} />
      </div>
    )
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setFormError('')
    if (!prefixIsValid) {
      setFormError(PROJECT_PREFIX_ERROR)
      return
    }
    updateMutation.mutate()
  }

  const prefixTaken =
    normalizedPrefix !== project.prefix &&
    projectList?.some((p) => p.prefix === normalizedPrefix && p.id !== project.id)

  const deleteConfirmationMatches = projectDeleteConfirmationMatches(
    deleteConfirmationText,
    deleteExpectedPhrase,
  )

  const openDeleteModal = () => {
    setDeleteError('')
    setDeleteConfirmationText('')
    setDeleteExpectedPhrase(projectDeleteConfirmationPhrase(project.prefix))
    setConfirmDeleteOpen(true)
  }

  const closeDeleteModal = () => {
    setDeleteError('')
    setDeleteConfirmationText('')
    setDeleteExpectedPhrase('')
    setConfirmDeleteOpen(false)
  }

  return (
    <div className="space-y-8 animate-fade-in max-w-3xl">
      <div>
        <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
          <Link to={`/projects/${prefix}`} className="hover:text-primary transition-colors">
            {project.name}
          </Link>
          <span>/</span>
          <span className="text-foreground">Edit project</span>
        </div>
        <h2 className="text-xl font-bold text-foreground">Edit project</h2>
        <p className="text-sm text-muted-foreground mt-0.5">Update project metadata and external issue tracker.</p>
      </div>

      <form onSubmit={handleSubmit} className="bg-card rounded-lg border border-border shadow-elegant p-6 space-y-4">
        <h3 className="text-sm font-semibold text-foreground uppercase tracking-wide">Project details</h3>
        {formError && (
          <div className="rounded-md border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-600">{formError}</div>
        )}
        {prefixTaken && (
          <div className="rounded-md border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-sm text-amber-800 dark:text-amber-200">
            Another project already uses prefix {normalizedPrefix}.
          </div>
        )}
        <div>
          <label className="block text-xs font-medium text-muted-foreground uppercase tracking-wider mb-1.5">Name</label>
          <input
            type="text"
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            title="Project name"
            placeholder="My Project"
            className="w-full px-3 py-2 bg-background border border-input rounded-md text-sm text-foreground focus:ring-2 focus:ring-ring"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-muted-foreground uppercase tracking-wider mb-1.5">Prefix</label>
          <input
            type="text"
            required
            value={projectPrefix}
            onChange={(e) => setProjectPrefix(e.target.value.toUpperCase())}
            maxLength={3}
            title="Project prefix"
            placeholder="PRJ"
            className={`w-full px-3 py-2 bg-background border rounded-md text-sm font-mono focus:ring-2 focus:ring-ring ${
              showPrefixError ? 'border-red-500/70' : 'border-input'
            }`}
          />
          <p className={`mt-1 text-xs ${showPrefixError ? 'text-red-600' : 'text-muted-foreground'}`}>
            {showPrefixError ? PROJECT_PREFIX_ERROR : 'Item IDs use PRJ-TYP-001.'}
          </p>
        </div>
        <div>
          <label className="block text-xs font-medium text-muted-foreground uppercase tracking-wider mb-1.5">Status</label>
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            title="Project status"
            className="w-full px-3 py-2 bg-background border border-input rounded-md text-sm"
          >
            {STATUS_OPTIONS.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-muted-foreground uppercase tracking-wider mb-1.5">Description</label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
            title="Project description"
            placeholder="Project description..."
            className="w-full px-3 py-2 bg-background border border-input rounded-md text-sm"
          />
        </div>
        <div className="flex justify-end gap-3 pt-2">
          <Link
            to={`/projects/${prefix}`}
            className="px-4 py-2 border border-border rounded-md text-sm text-muted-foreground hover:bg-accent transition-colors"
          >
            Cancel
          </Link>
          <button
            type="submit"
            disabled={updateMutation.isPending || !prefixIsValid || !!prefixTaken}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 disabled:opacity-50"
          >
            {updateMutation.isPending ? 'Saving...' : 'Save project'}
          </button>
        </div>
      </form>

      <section className="rounded-lg border border-destructive/30 bg-card p-6 shadow-elegant">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-destructive">Danger zone</h3>
        <p className="mt-2 text-sm text-muted-foreground">
          Permanently delete this project and its project-scoped data. This action cannot be undone.
        </p>
        <div className="mt-4 flex justify-end">
          <button
            type="button"
            onClick={openDeleteModal}
            className="rounded-md border border-destructive/30 px-4 py-2 text-sm text-destructive transition-colors hover:bg-destructive/10"
          >
            Delete project
          </button>
        </div>
      </section>

      {confirmDeleteOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="mx-4 w-full max-w-md rounded-lg bg-card p-6 shadow-elegant">
            <h3 className="text-lg font-semibold text-foreground">Delete project?</h3>
            <p className="mt-2 text-sm text-muted-foreground">
              This permanently removes <span className="font-medium text-foreground">{project.name}</span> ({project.prefix}).
              Type <span className="font-mono text-foreground">{deleteExpectedPhrase}</span> to confirm.
            </p>
            <label className="mt-4 block text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Confirmation
              <input
                type="text"
                value={deleteConfirmationText}
                onChange={(e) => setDeleteConfirmationText(e.target.value)}
                autoComplete="off"
                spellCheck={false}
                placeholder={deleteExpectedPhrase}
                className="mt-1.5 w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground focus:ring-2 focus:ring-ring"
              />
            </label>
            {deleteError && (
              <div className="mt-3 rounded-md border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-600">
                {deleteError}
              </div>
            )}
            <div className="mt-6 flex justify-end gap-2">
              <button
                type="button"
                onClick={closeDeleteModal}
                className="rounded-md border border-input px-4 py-2 text-sm text-foreground transition-colors hover:bg-accent/50"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => deleteMutation.mutate()}
                disabled={!deleteConfirmationMatches || deleteMutation.isPending}
                className="rounded-md bg-destructive px-4 py-2 text-sm text-white transition-colors hover:bg-destructive/90 disabled:opacity-50"
              >
                {deleteMutation.isPending ? 'Deleting...' : 'Delete project'}
              </button>
            </div>
          </div>
        </div>
      )}

      <IntegrationSettingsPanel projectId={project.id} />
    </div>
  )
}
