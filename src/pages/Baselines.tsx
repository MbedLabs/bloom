import { Layers } from 'lucide-react'

export default function Baselines() {
  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h2 className="text-2xl font-bold text-foreground">Baselines</h2>
        <p className="text-muted-foreground">Snapshot and compare project artefacts at specific points in time</p>
      </div>

      <div className="bg-card rounded-lg shadow-elegant p-12 text-center">
        <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary/10 to-cyan-500/10 flex items-center justify-center mx-auto mb-4">
          <Layers className="h-8 w-8 text-primary/40" />
        </div>
        <h3 className="text-lg font-medium text-foreground mb-2">Baselines Coming Soon</h3>
        <p className="text-muted-foreground max-w-md mx-auto">
          Baselines will allow you to create snapshots of requirements, test cases, and documents for comparison and audit trails.
        </p>
      </div>
    </div>
  )
}
