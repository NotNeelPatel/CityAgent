import { Progress } from "@/components/ui/progress"
import { fetchData } from "@/lib/client"
import { toast } from "sonner"

type VectorizeEvent = {
  type: "loading" | "success" | "error"
  message?: string
  file_path?: string
  chunks_embedded?: number
  total_chunks?: number
}

export const vectorizeToast = (
  id: string,
  state: "loading" | "success" | "error",
  fileName: string,
  message: string,
  percentage: number
) => {
  const content = (
    <div className="flex w-full min-w-0 flex-col gap-3">
      <h2 className="truncate text-sm font-semibold">{fileName}</h2>

      <div className="flex items-center justify-between gap-3 text-xs text-muted-foreground">
        <p className="truncate">{message}</p>
        <span className="shrink-0">{percentage}%</span>
      </div>

      <Progress value={percentage} className="w-full" />
    </div>
  )

  switch (state) {
    case "error":
      return toast.error(`Vectorization failed for ${fileName}: ${message}`, { id })
    case "success":
      return toast(content, { id, duration: 10000 })
    case "loading":
    default:
      return toast(content, { id, duration: 10000 })
  }
}

const getPercentage = (completed?: number, total?: number) => {
  if (!total || total <= 0) return 0
  return Math.round((completed ?? 0) / total * 100)
}

const parseSseChunk = (
  chunk: string,
  previousBuffer = ""
): { events: VectorizeEvent[]; buffer: string } => {
  const combined = previousBuffer + chunk
  const blocks = combined.split("\n\n")
  const buffer = blocks.pop() || ""
  const events: VectorizeEvent[] = []

  for (const block of blocks) {
    const line = block
      .split("\n")
      .find((entry) => entry.trim().startsWith("data:"))

    if (!line) continue

    const raw = line.replace(/^data:\s*/, "")

    try {
      events.push(JSON.parse(raw) as VectorizeEvent)
    } catch {
      console.error("Failed to parse SSE event:", raw)
    }
  }

  return { events, buffer }
}

const streamVectorizeFile = async (
  bucket: string,
  storagePath: string,
  fileName: string
) => {
  const toastId = `vectorize-${fileName}-${Date.now()}`
  vectorizeToast(toastId, "loading", fileName, "Starting vectorization...", 0)

  const response = await fetchData("/api/vectorize-file", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      bucket,
      storage_path: storagePath,
    }),
  })

  if (!response.ok) {
    let errorDetail = `status ${response.status}`
    try {
      const payload = await response.json()
      errorDetail = payload?.detail ?? errorDetail
    } catch {
      // ignore
    }

    vectorizeToast(toastId, "error", fileName, errorDetail, 0)
    throw new Error(errorDetail)
  }

  if (!response.body) {
    vectorizeToast(toastId, "error", fileName, "Streaming not supported", 0)
    throw new Error("ReadableStream not supported in this browser.")
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder("utf-8")
  let buffer = ""
  let finished = false

  const handleEvents = (events: VectorizeEvent[]) => {
    for (const event of events) {
      vectorizeToast(
        toastId,
        event.type,
        fileName,
        event.message ?? "",
        getPercentage(event.chunks_embedded, event.total_chunks)
      )

      if (event.type === "success") {
        finished = true
      }

      if (event.type === "error") {
        throw new Error(event.message ?? "Vectorization failed")
      }
    }
  }

  while (true) {
    const { value, done } = await reader.read()
    if (done) break

    const chunk = decoder.decode(value, { stream: true })
    const result = parseSseChunk(chunk, buffer)
    buffer = result.buffer
    handleEvents(result.events)
  }

  const finalChunk = decoder.decode()
  if (finalChunk || buffer) {
    const result = parseSseChunk(finalChunk, buffer)
    handleEvents(result.events)
  }

  if (!finished) {
    vectorizeToast(
      toastId,
      "error",
      fileName,
      "Vectorization stream ended unexpectedly",
      0
    )
    throw new Error("Vectorization stream ended unexpectedly")
  }
}

export default streamVectorizeFile