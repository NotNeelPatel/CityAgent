import { Layout } from "@/components/layout"
import { useMemo, useState, useEffect } from "react"
import { FileUpload } from "@/components/ui/aceternity/file-upload"
import { SearchBar } from "@/components/searchbar"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { IconTrash } from "@tabler/icons-react"
import { Button } from "@/components/ui/button"
import { supabase } from "@/lib/client"
import { useAuth } from "@/context/AuthContext"
import type { User } from "@supabase/supabase-js"

export function Dashboard() {
  const [files, setFiles] = useState<FileRow[]>([])
  const [loading, setLoading] = useState(true)
  const [query, setQuery] = useState("")
  const { user } = useAuth()

  const loadFiles = async () => {
    setLoading(true)

    const { data, error } = await supabase
      .from("documents")
      .select("id, owner_id, title, storage_bucket, storage_path, mime_type, size_bytes, created_at, last_updated")
      .eq("storage_bucket", "documents")
      .order("created_at", { ascending: false })

    if (error) {
      console.error(error)
      alert(`Failed to load files: ${error.message}`)
      setFiles([])
      setLoading(false)
      return
    }

    const rows: FileRow[] = (data ?? []).map((d) => ({
      id: d.id,
      ownerId: d.owner_id,
      name: d.title,
      storagePath: d.storage_path,
      mimeType: d.mime_type ?? "",
      sizeBytes: d.size_bytes ?? 0,
      createdAt: d.created_at,
      lastUpdated: d.last_updated ?? null,
    }))

    setFiles(rows)
    setLoading(false)
  }

  useEffect(() => {
    if (!user) return
    loadFiles()
  }, [user])

  const uploadToSupabase = async (user: User, f: File) => {
    const safeName = f.name.replace(/\s+/g, "_")
    const storagePath = `${crypto.randomUUID()}-${safeName}`

    // upload file to storage
    const { error: uploadError } = await supabase.storage
      .from("documents")
      .upload(storagePath, f, {
        contentType: f.type,
        upsert: false,
      })

    if (uploadError) {
      console.error(uploadError)
      alert(`Upload failed for ${f.name}: ${uploadError.message}`)
      return
    }

    // insert metadata to DB
    const { error: dbError } = await supabase.from("documents").insert({
      owner_id: user.id,
      title: f.name,
      storage_bucket: "documents",
      storage_path: storagePath,
      mime_type: f.type,
      size_bytes: f.size,
      last_updated: new Date(f.lastModified), // safest
    })

    if (dbError) {
      console.error(dbError)
      alert(`Uploaded ${f.name} but DB insert failed: ${dbError.message}`)
      await supabase.storage.from("documents").remove([storagePath])
      return
    }
  }

  const handleFileUpload = async (incoming: File[]) => {
    if (!user) {
      alert("Session expired. Please sign in again.")
      return
    }

    for (const f of incoming) {
      await uploadToSupabase(user, f)
    }

    // refresh table from DB so it shows all files
    await loadFiles()
  }

  const handleFileDelete = async (row: FileRow) => {
    // delete storage object
    const { error: storageError } = await supabase.storage
      .from("documents")
      .remove([row.storagePath])

    if (storageError) {
      console.error(storageError)
      alert(`Failed to delete file from storage: ${storageError.message}`)
      return
    }

    // delete DB row
    const { error: dbError } = await supabase.from("documents").delete().eq("id", row.id)

    if (dbError) {
      console.error(dbError)
      alert(`Deleted from storage but DB delete failed: ${dbError.message}`)
      return
    }

    // update UI
    setFiles((prev) => prev.filter((f) => f.id !== row.id))
  }

  const filteredFiles = useMemo(() => {
    const q = normalize(query)
    if (!q) return files
    const tokens = q.split(/\s+/).filter(Boolean)

    return files.filter((f) => {
      const haystack = normalize(
        `${f.name} ${f.mimeType} ${formatBytes(f.sizeBytes)} ${f.createdAt} ${f.lastUpdated ?? ""}`
      )
      return tokens.every((t) => haystack.includes(t))
    })
  }, [files, query])

  return (
    <Layout>
      <div className="p-1">
        <SearchBar placeholder="Search files" query={query} setQuery={setQuery} onSubmit={() => { }} />
      </div>

      <div className="my-6 flex justify-end">
        <FileUploadDialog onUpload={handleFileUpload} />
      </div>

      {loading ? (
        <div className="text-sm text-muted-foreground">Loading files...</div>
      ) : (
        <FilesTable
          files={filteredFiles}
          onDelete={handleFileDelete}
        />
      )}
    </Layout>
  )
}

type FileRow = {
  id: string
  ownerId: string
  name: string
  storagePath: string
  mimeType: string
  sizeBytes: number
  createdAt: string
  lastUpdated: string | null
}


function formatBytes(bytes: number) {
  if (bytes === 0) return "0 B"
  const k = 1024
  const sizes = ["B", "KB", "MB", "GB", "TB"]
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  const value = bytes / Math.pow(k, i)
  return `${value.toFixed(i === 0 ? 0 : 1)} ${sizes[i]}`
}

function normalize(s: string) {
  return s.trim().toLowerCase()
}

function FilesTable({
  files,
  onDelete,
}: {
  files: FileRow[]
  onDelete: (row: FileRow) => void
}) {
  return (
    <Table>

      <TableHeader>
        <TableRow>
          <TableHead>Filename</TableHead>
          <TableHead>Last updated</TableHead>
          <TableHead>Size</TableHead>
          <TableHead className="text-right">Actions</TableHead>
        </TableRow>
      </TableHeader>

      <TableBody>
        {files.length === 0 ? (
          <TableRow>
            <TableCell colSpan={4} className="text-muted-foreground">
              No matching files.
            </TableCell>
          </TableRow>
        ) : (
          files.map((file) => (
            <TableRow key={file.id}>
              <TableCell className="font-medium">{file.name}</TableCell>
              <TableCell className="text-muted-foreground">
                {file.lastUpdated}
              </TableCell>
              <TableCell>{formatBytes(file.sizeBytes)}</TableCell>
              <TableCell className="text-right">
                <Button
                  variant="secondary"
                  size="icon"
                  aria-label={`Delete ${file.name}`}
                  onClick={() => onDelete(file)}
                >
                  <IconTrash className="h-4 w-4 hover:text-destructive" />
                </Button>
              </TableCell>
            </TableRow>
          ))
        )}
      </TableBody>
    </Table>
  )
}

function FileUploadDialog({ onUpload }: { onUpload: (files: File[]) => void }) {
  const [open, setOpen] = useState(false)
  const [pendingFiles, setPendingFiles] = useState<File[]>([])

  const hasPending = pendingFiles.length > 0

  const closeDialog = () => setOpen(false)
  const clearPending = () => setPendingFiles([])

  const handleOpenChange = (nextOpen: boolean) => {
    if (!nextOpen) clearPending()
    setOpen(nextOpen)
  }

  const handleUploadClick = () => {
    if (!hasPending) return
    onUpload(pendingFiles)
    clearPending()
    closeDialog()
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button>Upload files</Button>
      </DialogTrigger>

      <DialogContent className="flex max-h-[80vh] w-[calc(100%-1rem)] max-w-lg flex-col">
        <DialogHeader>
          <DialogTitle>Upload new files</DialogTitle>
          <DialogDescription>
            Drag and drop files here or click to browse (csv, pdf, xls, xlsx)
          </DialogDescription>
        </DialogHeader>

        <div className="overflow-auto">
          <div className="py-2">
            <FileUpload
              onChange={setPendingFiles}
              allowedFileTypes={["csv", "pdf", "xls", "xlsx"]}
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={closeDialog}>
            Cancel
          </Button>

          <Button onClick={handleUploadClick} disabled={!hasPending}>
            Upload{hasPending ? ` (${pendingFiles.length})` : ""}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}