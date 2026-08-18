import { useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Download, Paperclip, Trash2, Upload } from 'lucide-react'
import { attachmentsApi, extractApiErrorMessage, type DocumentAttachment } from '../api/client'
import { useAuth } from '../contexts/AuthContext'
import { SectionCard } from './DocDetailShell'
import { useToast } from './useToast'

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export default function DocumentAttachmentsPanel({ documentId }: { documentId: number }) {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const toast = useToast()
  const fileInput = useRef<HTMLInputElement>(null)
  const [busyId, setBusyId] = useState<number | null>(null)
  const canEdit = user?.role === 'admin' || user?.role === 'maintainer'

  const { data: attachments, isLoading } = useQuery({
    queryKey: ['attachments', documentId],
    queryFn: () => attachmentsApi.list(documentId),
    enabled: !!documentId,
  })

  const uploadMutation = useMutation({
    mutationFn: (file: File) => attachmentsApi.upload(documentId, file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['attachments', documentId] })
      toast.notify('File attached', 'success')
    },
    onError: (error) => toast.failed('Attaching the file', error),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => attachmentsApi.remove(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['attachments', documentId] })
      toast.notify('Attachment removed', 'success')
    },
    onError: (error) => toast.failed('Removing the attachment', error),
  })

  const download = async (attachment: DocumentAttachment) => {
    setBusyId(attachment.id)
    try {
      const { blob, filename } = await attachmentsApi.download(
        attachment.id,
        attachment.original_filename,
      )
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = filename
      link.click()
      URL.revokeObjectURL(url)
    } catch (failure) {
      toast.failed('Downloading the attachment', extractApiErrorMessage(failure))
    } finally {
      setBusyId(null)
    }
  }

  return (
    <SectionCard
      title="Attachments"
      actions={
        canEdit ? (
          <>
            <input
              ref={fileInput}
              type="file"
              className="hidden"
              aria-label="Attach a file"
              onChange={(event) => {
                const file = event.target.files?.[0]
                if (file) uploadMutation.mutate(file)
                event.target.value = ''
              }}
            />
            <button
              onClick={() => fileInput.current?.click()}
              disabled={uploadMutation.isPending}
              className="inline-flex items-center px-3 py-2 border border-input rounded-md text-sm font-medium hover:bg-accent/50 disabled:opacity-50"
            >
              <Upload className="h-4 w-4 mr-2" />
              {uploadMutation.isPending ? 'Attaching...' : 'Attach file'}
            </button>
          </>
        ) : undefined
      }
    >
      {isLoading ? (
        <p className="text-muted-foreground">Loading attachments...</p>
      ) : !attachments || attachments.length === 0 ? (
        <p className="text-muted-foreground">Nothing attached yet.</p>
      ) : (
        <ul className="divide-y divide-border -mx-6 -mb-6">
          {attachments.map((attachment) => (
            <li key={attachment.id} className="flex items-center gap-3 px-6 py-3">
              <Paperclip className="h-4 w-4 shrink-0 text-muted-foreground" />
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-foreground">
                  {attachment.original_filename}
                </p>
                <p className="text-xs text-muted-foreground">
                  {formatBytes(attachment.size_bytes)}
                  {attachment.source_ref ? ` · from ${attachment.source_ref}` : ''}
                </p>
              </div>
              <button
                onClick={() => download(attachment)}
                disabled={busyId === attachment.id}
                title="Download"
                className="p-2 rounded-md text-muted-foreground hover:text-foreground hover:bg-accent/50 disabled:opacity-50"
              >
                <Download className="h-4 w-4" />
              </button>
              {canEdit && (
                <button
                  onClick={() => deleteMutation.mutate(attachment.id)}
                  title="Remove attachment"
                  className="p-2 rounded-md text-muted-foreground hover:text-red-500 hover:bg-red-500/10"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </SectionCard>
  )
}
