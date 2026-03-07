import { useState, type Dispatch, type SetStateAction } from "react";
import { StatusPill, type Step } from "@/components/statuspill";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { FileViewer } from "@/components/file_viewer";
import { Button } from "@/components/ui/button";
import { supabase } from "@/lib/client";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { cn } from "@/lib/utils";

type ResultsAreaProps = {
  steps: Step[];
  activeTab: "steps" | "overview" | "sources";
  setActiveTab: Dispatch<SetStateAction<"steps" | "overview" | "sources">>;
  hasResults: boolean;
  selectedSourceIndex: number;
  setSelectedSourceIndex: Dispatch<SetStateAction<number>>;
  adkResponse: string;
  adkSource: Source[];
};

type Source = {
  filename: string;
  lastUpdated: string;
  href: string;
};

const ResultsArea = ({ steps, activeTab, setActiveTab, hasResults, selectedSourceIndex, setSelectedSourceIndex, adkResponse, adkSource }: ResultsAreaProps) => {
  const selectedSource = adkSource[selectedSourceIndex];

  const [selectedSourceSupabase, setSelectedSourceSupabase] = useState<string | null>(null);

  const getSupabaseSource = async (source: string) => {
    console.log("Fetching source from Supabase with path:", source);
    const { data, error } = await supabase.storage
      .from('documents')
      .createSignedUrl(source, 60); // URL valid for 60 seconds
    if (error) {
      console.error("Error fetching signed URL from Supabase:", error);
      return;
    }

    console.log("Supabase public URL for source:", data.signedUrl);
    setSelectedSourceSupabase(data.signedUrl);
  }

  return (
    <div className="mt-8">
      <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as any)}>
        <TabsList>
          {hasResults && <TabsTrigger value="overview">Overview</TabsTrigger>}
          {hasResults && <TabsTrigger value="sources">Source Viewer</TabsTrigger>}
          <TabsTrigger value="steps">Steps</TabsTrigger>
        </TabsList>

        {hasResults && (
          <TabsContent value="overview" className="mt-6">
            <div className="flex flex-col md:flex-row gap-4 justify-between">

              <div className="prose flex-1">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{adkResponse}</ReactMarkdown>
              </div>

              <div className="flex-1 w-full md:max-w-96 flex flex-col gap-4">
                {adkSource.map((src, idx) => (
                  <div key={idx} className="rounded-md bg-muted p-4">
                    <div className="text-muted-foreground text-xs">Last updated: {src.lastUpdated}</div>
                    <h2 className="font-medium">{src.filename}</h2>
                    <div className="flex float-right gap-4 mt-4">
                      <Button className="text-blue-800 p-0 h-auto" variant="link" asChild>
                        <a href={src.href}
                          onClick={(e) => {
                            e.preventDefault();
                            setSelectedSourceIndex(idx);
                            getSupabaseSource(src.filename);
                            setActiveTab("sources");
                          }}>View here</a>
                      </Button>
                      <Button className="text-blue-800 p-0 h-auto" variant="link" asChild>
                        <a href={src.href} target="_blank">Original Source →</a>
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </TabsContent>
        )}

        {hasResults && (
          <TabsContent value="sources" className="mt-6">
            <div className="flex flex-col md:flex-row gap-4 justify-between">

              <div className="flex-1 w-full md:max-w-96 flex flex-col gap-4">
                {adkSource.map((src, idx) => {
                  const isSelected = idx === selectedSourceIndex;

                  return (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => {
                        setSelectedSourceIndex(idx)
                        getSupabaseSource(src.filename);
                      }}
                      className={cn(
                        "text-left rounded-md bg-muted p-4 border transition",
                        "hover:bg-muted/80 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
                        isSelected ? "border-ring" : "border-transparent"
                      )}
                      aria-pressed={isSelected}
                    >
                      <div className="text-muted-foreground text-xs">
                        Last updated: {src.lastUpdated}
                      </div>

                      <div className="mt-1 flex items-start justify-between gap-3">
                        <h2 className="font-medium">{src.filename}</h2>
                      </div>

                      <Button
                        className="text-blue-800 mt-4 p-0 h-auto"
                        variant="link"
                        asChild
                      >
                        <a href={src.href} target="_blank" rel="noreferrer">
                          Original Source →
                        </a>
                      </Button>
                    </button>
                  );
                })}
              </div>

              <div className="flex-1 h-160 rounded-md border p-4">
                <div className="font-medium h-full">
                  {selectedSource ? (
                    <FileViewer
                      src={selectedSourceSupabase}
                      filename={selectedSource.filename}
                      className="doc-viewer-wrapper h-full"
                    />
                  ) : (
                    "No file selected"
                  )}
                </div>
              </div>

            </div>
          </TabsContent>
        )}


        <TabsContent value="steps" className="mt-6">
          <div className="mt-6 space-y-8">
            {steps.length === 0 ? (
              <div className="text-sm text-muted-foreground">Processing query...</div>
            ) : (
              steps.map((s) => (
                <div key={s.id} className="flex items-start gap-4">
                  <StatusPill status={s.status} />
                  <div className="min-w-0">
                    <div className="font-medium">{s.title}</div>
                    {s.detail && (
                      <div className="mt-1 text-sm text-muted-foreground">
                        {s.detail}
                      </div>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </TabsContent>

      </Tabs>
    </div>
  );
};

export { ResultsArea };
export type { ResultsAreaProps, Source };