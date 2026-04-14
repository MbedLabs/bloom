import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { projectsApi } from '../api/client'
import { FolderKanban, FileText, CheckCircle, TrendingUp } from 'lucide-react'

export default function Dashboard() {
  const { data: projects, isLoading } = useQuery({
    queryKey: ['projects'],
    queryFn: projectsApi.list,
  })

  const totalProjects = projects?.length || 0
  const totalRequirements = projects?.reduce((sum, p) => sum + p.requirement_count, 0) || 0
  const totalTestCases = projects?.reduce((sum, p) => sum + p.test_case_count, 0) || 0
  const coverage = totalRequirements > 0
    ? Math.min(100, Math.round((totalTestCases / totalRequirements) * 100))
    : 0

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <StatCard
          title="Total Projects"
          value={totalProjects}
          icon={FolderKanban}
          color="bg-teal-600"
        />
        <StatCard
          title="Total Requirements"
          value={totalRequirements}
          icon={FileText}
          color="bg-teal-500"
        />
        <StatCard
          title="Total Test Cases"
          value={totalTestCases}
          icon={CheckCircle}
          color="bg-emerald-500"
        />
        <StatCard
          title="Coverage"
          value={`${coverage}%`}
          icon={TrendingUp}
          color={coverage >= 80 ? 'bg-emerald-500' : coverage >= 50 ? 'bg-amber-500' : 'bg-red-500'}
        />
      </div>

      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
          <h3 className="text-lg font-semibold">Projects</h3>
          <Link to="/projects" className="text-sm text-teal-600 hover:text-teal-700">
            View all →
          </Link>
        </div>

        {isLoading ? (
          <div className="p-6 text-center text-gray-500">Loading...</div>
        ) : !projects || projects.length === 0 ? (
          <div className="p-12 text-center">
            <FolderKanban className="h-16 w-16 text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No Projects Yet</h3>
            <p className="text-gray-500 mb-4">Create your first project to start managing requirements.</p>
            <Link
              to="/projects"
              className="inline-flex items-center px-4 py-2 bg-teal-600 text-white rounded-lg hover:bg-teal-700 transition-colors"
            >
              Create Project
            </Link>
          </div>
        ) : (
          <div className="divide-y divide-gray-200">
            {projects.slice(0, 10).map((project) => (
              <Link
                key={project.id}
                to={`/projects/${project.id}`}
                className="block px-6 py-4 hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-gray-900">{project.name}</p>
                    <p className="text-sm text-gray-500">
                      {project.prefix}{project.description ? ` — ${project.description}` : ''}
                    </p>
                  </div>
                  <div className="flex items-center space-x-4">
                    <ProjectStatusBadge status={project.status} />
                    <span className="text-sm text-gray-500">
                      {project.requirement_count} reqs · {project.test_case_count} TCs
                    </span>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>

      {projects && projects.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4">Requirements by Status</h3>
          <div className="space-y-3">
            {['Draft', 'Review', 'Approved', 'Implemented', 'Verified', 'Rejected'].map((status) => {
              const count = projects.filter(p => p.status === status).length
              if (count === 0 && status !== 'Draft') return null
              const maxCount = Math.max(projects.length, 1)
              const width = (count / maxCount) * 100
              return (
                <div key={status} className="flex items-center">
                  <span className="w-28 text-sm text-gray-600">{status}</span>
                  <div className="flex-1 bg-gray-100 rounded-full h-6 ml-3">
                    <div
                      className={`h-6 rounded-full ${getStatusColor(status)}`}
                      style={{ width: `${Math.max(width, 2)}%` }}
                    />
                  </div>
                  <span className="w-12 text-sm text-gray-500 text-right ml-3">{count}</span>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}

function StatCard({ title, value, icon: Icon, color }: {
  title: string
  value: number | string
  icon: React.ComponentType<{ className?: string }>
  color: string
}) {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center">
        <div className={`p-3 rounded-lg ${color}`}>
          <Icon className="h-6 w-6 text-white" />
        </div>
        <div className="ml-4">
          <p className="text-sm text-gray-500">{title}</p>
          <p className="text-2xl font-semibold text-gray-900">{value}</p>
        </div>
      </div>
    </div>
  )
}

function ProjectStatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    Active: 'bg-emerald-100 text-emerald-800',
    Archived: 'bg-gray-100 text-gray-800',
    Draft: 'bg-amber-100 text-amber-800',
  }

  return (
    <span className={`px-2 py-1 rounded-full text-xs font-medium ${colors[status] || 'bg-gray-100 text-gray-800'}`}>
      {status}
    </span>
  )
}

function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    Draft: 'bg-gray-400',
    Review: 'bg-amber-400',
    Approved: 'bg-blue-400',
    Implemented: 'bg-teal-400',
    Verified: 'bg-emerald-400',
    Rejected: 'bg-red-400',
  }
  return colors[status] || 'bg-gray-400'
}
