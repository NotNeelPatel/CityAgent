import { Layout } from "@/components/layout"
import { useMemo, useState } from "react"
import { FileUpload } from "@/components/ui/aceternity/file-upload"
import { SearchBar } from "@/components/searchbar"
import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { IconTrash } from "@tabler/icons-react"
import { Button } from "@/components/ui/button"

export function Dashboard() {
  const [files, setFiles] = useState<FileRow[]>([])
  const [query, setQuery] = useState("")

  const handleFilesCommitted = (incoming: File[]) => {
    const rows: FileRow[] = incoming.map((f) => ({
      id: `${f.name}-${f.size}-${f.lastModified}`,
      name: f.name,
      lastUpdated: formatDate(new Date(f.lastModified)),
      size: formatBytes(f.size),
      file: f,
    }))

    setFiles((prev) => {
      const seen = new Set(prev.map((p) => p.id))
      const next = [...prev]
      for (const r of rows) {
        if (!seen.has(r.id)) next.push(r)
      }
      return next
    })
  }

  const handleDelete = (id: string) => {
    setFiles((prev) => prev.filter((f) => f.id !== id))
  }

  const filteredFiles = useMemo(() => {
    const q = normalize(query)
    if (!q) return files
    const tokens = q.split(/\s+/).filter(Boolean)

    return files.filter((f) => {
      const haystack = normalize(`${f.name} ${f.lastUpdated} ${f.size}`)
      return tokens.every((t) => haystack.includes(t))
    })
  }, [files, query])

  return (
    <Layout>
      <SearchBar placeholder="Search files" query={query} setQuery={setQuery} onSubmit={() => { }} />

      <div className="my-6 flex justify-end">
        <FileUploadDialog onUpload={handleFilesCommitted} />
      </div>

      <FilesTable files={filteredFiles} onDelete={handleDelete} />
    </Layout>
  )
}

type FileRow = {
  id: string
  name: string
  lastUpdated: string
  size: string
  file: File
}

function formatBytes(bytes: number) {
  if (bytes === 0) return "0 B"
  const k = 1024
  const sizes = ["B", "KB", "MB", "GB", "TB"]
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  const value = bytes / Math.pow(k, i)
  return `${value.toFixed(i === 0 ? 0 : 1)} ${sizes[i]}`
}

function formatDate(d: Date) {
  return d.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  })
}

function normalize(s: string) {
  return s.trim().toLowerCase()
}

function FilesTable({
  files,
  onDelete,
}: {
  files: FileRow[]
  onDelete: (id: string) => void
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
              <TableCell>{file.size}</TableCell>
              <TableCell className="text-right">
                <Button
                  variant="secondary"
                  size="icon"
                  aria-label={`Delete ${file.name}`}
                  onClick={() => onDelete(file.id)}
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

function FileUploadDialog({
  onUpload,
}: {
  onUpload: (files: File[]) => void
}) {
  const [pendingFiles, setPendingFiles] = useState<File[]>([])

  const hasPending = pendingFiles.length > 0

  const handleSelect = (incoming: File[]) => {
    // If your FileUpload returns the full list each time, this is fine.
    // If it returns deltas, switch to setPendingFiles(prev => [...prev, ...incoming])
    setPendingFiles(incoming)
  }

  const clearPending = () => setPendingFiles([])

  const handleUploadClick = () => {
    if (!hasPending) return
    onUpload(pendingFiles)
    clearPending()
  }

  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button>Upload files</Button>
      </DialogTrigger>

      <DialogContent className="flex max-h-[80vh] w-full max-w-lg flex-col">
        <DialogHeader>
          <DialogTitle>Upload new files</DialogTitle>
          <DialogDescription>
            Drag and drop files here or click to browse (csv, pdf, xls, xlsx)
          </DialogDescription>
        </DialogHeader>

        {/* Scrollable middle section */}
        <div className="overflow-auto">
          <div className="py-2">
            <FileUpload
              onChange={handleSelect}
              allowedFileTypes={["csv", "pdf", "xls", "xlsx"]}
            />
          </div>
        </div>

        <DialogFooter>
          <DialogClose asChild>
            <Button variant="outline" onClick={clearPending}>
              Cancel
            </Button>
          </DialogClose>

          <DialogClose asChild>
            <Button onClick={handleUploadClick} disabled={!hasPending}>
              Upload{hasPending ? ` (${pendingFiles.length})` : ""}
            </Button>
          </DialogClose>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
