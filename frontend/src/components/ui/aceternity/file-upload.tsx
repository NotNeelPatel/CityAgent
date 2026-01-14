import { cn } from "@/lib/utils";
import React, { useRef, useState } from "react";
import { motion } from "motion/react";
import { IconUpload, IconX } from "@tabler/icons-react";
import { useDropzone } from "react-dropzone";
import { Button } from "@/components/ui/button";

const mainVariant = {
  initial: {
    x: 0,
    y: 0,
  },
  animate: {
    x: 20,
    y: -20,
    opacity: 0.9,
  },
};

const secondaryVariant = {
  initial: {
    opacity: 0,
  },
  animate: {
    opacity: 1,
  },
};


type AllowedExt = "csv" | "pdf" | "xls" | "xlsx";

const EXT_TO_MIME: Record<AllowedExt, string> = {
  csv: "text/csv",
  pdf: "application/pdf",
  xls: "application/vnd.ms-excel",
  xlsx: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
};

function buildDropzoneAccept(exts?: AllowedExt[]) {
  if (!exts || exts.length === 0) return undefined;

  return exts.reduce<Record<string, string[]>>((acc, ext) => {
    acc[EXT_TO_MIME[ext]] = [`.${ext}`];
    return acc;
  }, {});
}

function buildInputAccept(exts?: AllowedExt[]) {
  if (!exts || exts.length === 0) return undefined;
  return exts.map((e) => `.${e}`).join(",");
}


export const FileUpload = ({
  onChange,
  allowedFileTypes,
}: {
  onChange?: (files: File[]) => void;
  allowedFileTypes?: AllowedExt[];
}) => {
  const [files, setFiles] = useState<File[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const dropzoneAccept = buildDropzoneAccept(allowedFileTypes);
  const inputAccept = buildInputAccept(allowedFileTypes);

  const handleFileChange = (newFiles: File[]) => {
    setFiles((prevFiles) => [...prevFiles, ...newFiles]);
    onChange && onChange(newFiles);
  };

  const removeFileAtIndex = (idxToRemove: number) => {
    setFiles((prev) => prev.filter((_, idx) => idx !== idxToRemove));
  };

  const handleClick = () => {
    fileInputRef.current?.click();
  };

  const { getRootProps, isDragActive, isDragReject, isDragAccept } = useDropzone({
    multiple: true,
    noClick: true,
    accept: dropzoneAccept,
    onDrop: handleFileChange,
    onDropRejected: (error) => {
      console.log(error);
    },
  });

  return (
    <div className=" w-full h-full" {...getRootProps()}>
      <motion.div
        onClick={handleClick}
        whileHover="animate"
        className={cn(
          "flex justify-center items-center group/file rounded-lg cursor-pointer w-full h-full relative overflow-hidden",
          files.length > 0 ? "p-4" : "p-10"
        )}
      >
        <input
          ref={fileInputRef}
          id="file-upload-handle"
          type="file"
          multiple
          accept={inputAccept}
          onChange={(e) => handleFileChange(Array.from(e.target.files || []))}
          className="hidden"
        />
        {/* <div className="flex flex-col items-center justify-center"> */}
        {/* <h1 className="relative z-20 text-2xl font-sans font-bold">
            Upload files
          </h1>
          <p className="relative z-20 font-sans font-normal text-neutral-400 dark:text-neutral-400 text-base mt-2">
            Drag & drop your files here or click to upload {allowedFileTypes ? `(.${allowedFileTypes.join(", .")})` : ""}
          </p> */}
        <div className="relative w-full max-w-xl mx-auto">
          {files.length > 0 &&
            files.map((file, idx) => (
              <motion.div
                key={"file" + idx}
                layoutId={idx === 0 ? "file-upload" : "file-upload-" + idx}
                className={cn(
                  "relative overflow-hidden z-40 bg-white dark:bg-neutral-900 flex flex-col items-start justify-start md:h-24 p-4 mb-4 w-full mx-auto rounded-md",
                  "shadow-sm"
                )}
              >
                <div className="flex justify-between w-full items-center gap-4">
                  <motion.p
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    layout
                    className="text-base truncate max-w-xs"
                  >
                    {file.name}
                  </motion.p>
                  <div className="flex items-center gap-2">
                    <Button
                      variant={"secondary"}
                      onClick={(e) => {
                        e.stopPropagation(); // prevents triggering the upload click
                        removeFileAtIndex(idx);
                      }}
                      aria-label={`Remove ${file.name}`}
                    >
                      <IconX className="h-4 w-4" />
                    </Button>
                  </div>
                </div>

                <div className="flex gap-1 text-sm md:flex-row flex-col items-start md:items-center w-full mt-2 text-muted-foreground">
                  <motion.p
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    layout
                    className=""
                  >
                    {(file.size / (1024 * 1024)).toFixed(2)} MB
                  </motion.p>
                  <p className="hidden md:inline">|</p>
                  <motion.p
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    layout
                  >
                    modified{" "}
                    {new Date(file.lastModified).toLocaleDateString()}
                  </motion.p>


                </div>
              </motion.div>
            ))}
          {!files.length && (
            <motion.div
              layoutId="file-upload"
              variants={mainVariant}
              transition={{
                type: "spring",
                stiffness: 300,
                damping: 20,
              }}
              className={cn(
                "relative group-hover/file:shadow-2xl z-40 bg-white dark:bg-neutral-900 flex items-center justify-center h-32 mt-4 w-full max-w-[8rem] mx-auto rounded-md",
                "shadow-[0px_10px_50px_rgba(0,0,0,0.1)]"
              )}
            >
              {isDragActive ? (
                <motion.p
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="text-neutral-600 flex flex-col items-center"
                >
                  Drop it
                  <IconUpload className="h-4 w-4 text-neutral-600 dark:text-neutral-400" />
                </motion.p>
              ) : (
                <IconUpload className="h-4 w-4 text-neutral-600 dark:text-neutral-300" />
              )}
            </motion.div>
          )}

          {!files.length && (
            <motion.div
              variants={secondaryVariant}
              className="absolute opacity-0 border border-dashed border-sky-400 inset-0 z-30 bg-transparent flex items-center justify-center h-32 mt-4 w-full max-w-[8rem] mx-auto rounded-md"
            ></motion.div>
          )}
        </div>
        {/* </div> */}
      </motion.div>
    </div>
  );
};

export function GridPattern() {
  const columns = 41;
  const rows = 11;
  return (
    <div className="flex bg-gray-100 dark:bg-neutral-900 shrink-0 flex-wrap justify-center items-center gap-x-px gap-y-px  scale-105">
      {Array.from({ length: rows }).map((_, row) =>
        Array.from({ length: columns }).map((_, col) => {
          const index = row * columns + col;
          return (
            <div
              key={`${col}-${row}`}
              className={`w-10 h-10 flex shrink-0 rounded-[2px] ${index % 2 === 0
                ? "bg-gray-50 dark:bg-neutral-950"
                : "bg-gray-50 dark:bg-neutral-950 shadow-[0px_0px_1px_3px_rgba(255,255,255,1)_inset] dark:shadow-[0px_0px_1px_3px_rgba(0,0,0,1)_inset]"
                }`}
            />
          );
        })
      )}
    </div>
  );
}
