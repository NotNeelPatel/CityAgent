import { Layout } from "@/components/layout";
import { useState } from "react";
import { FileUpload } from "@/components/ui/aceternity/file-upload";

export function Upload() {
  const [files, setFiles] = useState<File[]>([]);

  const handleFileUpload = (files: File[]) => {
    setFiles(files);
  };

  return (
    <Layout>
      <div className="flex justify-center items-center h-full p-10">
        <div className="flex justify-center items-center h-full w-full max-w-4xl border border-dashed rounded-lg">
          <FileUpload onChange={handleFileUpload} allowedFileTypes={["csv", "pdf", "xls", "xlsx"]} />
        </div>
      </div>
    </Layout>
  );
}