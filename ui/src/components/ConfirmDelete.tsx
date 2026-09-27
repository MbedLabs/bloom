interface ConfirmDeleteProps {
  pending: boolean
  onConfirm: () => void
  onCancel: () => void
}

/** Render deletion confirmation and cancellation controls. */
export default function ConfirmDelete({ pending, onConfirm, onCancel }: ConfirmDeleteProps) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-muted-foreground">Are you sure?</span>
      <button
        onClick={onConfirm}
        disabled={pending}
        className="inline-flex items-center px-3 py-1.5 bg-red-600 text-white rounded-md hover:bg-red-700 text-sm disabled:opacity-50"
      >
        {pending ? 'Deleting...' : 'Delete'}
      </button>
      <button onClick={onCancel} className="px-3 py-1.5 border border-input rounded-md text-sm hover:bg-accent/40">
        Cancel
      </button>
    </div>
  )
}
