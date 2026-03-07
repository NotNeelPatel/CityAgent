import DocViewer, { DocViewerRenderers } from "@cyntler/react-doc-viewer";

type FileViewerProps = {
  src: string | null;
  filename: string | null;
  className?: string;
};

const getFileType = (filename: string | null) => {
  if (!filename) return "";

  const ext = filename.split(".").pop()?.toLowerCase() ?? "";

  switch (ext) {
    case "pdf":
      return "pdf";
    case "csv":
      return "csv";
    case "xls":
      return "xls";
    case "xlsx":
      return "xlsx";
    default:
      return "";
  }
};

const FileViewer = ({ src, filename, className }: FileViewerProps) => {
  if (!src || !filename) {
    return (
      <div className={className}>
        <div className="text-sm text-muted-foreground">No file selected.</div>
      </div>
    );
  }

  const fileType = getFileType(filename);

  if (!fileType) {
    return (
      <div className={className}>
        <div className="text-sm text-muted-foreground">
          Preview not available for this file type.
        </div>
      </div>
    );
  }

  return (
    <div className={className}>
      <DocViewer
        documents={[
          {
            uri: src,
            fileType,
            fileName: filename,
          },
        ]}
        pluginRenderers={DocViewerRenderers}
        style={{ width: "100%", height: "auto" }}

      />
    </div>
  );
};

export { FileViewer };