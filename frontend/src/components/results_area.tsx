import { useState, type Dispatch, type SetStateAction } from "react";
import { StatusPill, type Step } from "@/components/statuspill";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { FileViewer } from "@/components/file_viewer";
import { Button } from "@/components/ui/button";
import { supabase } from "@/lib/client";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { cn } from "@/lib/utils";
import { IconThumbUp, IconThumbDown } from "@tabler/icons-react";

type ResultsAreaProps = {
  steps: Step[];
  activeTab: "steps" | "overview" | "sources";
  setActiveTab: Dispatch<SetStateAction<"steps" | "overview" | "sources">>;
  hasResults: boolean;
  selectedSourceIndex: number;
  setSelectedSourceIndex: Dispatch<SetStateAction<number>>;
  adkResponse: string;
  adkSource: Source[];
  query: string;
};

type Source = {
  filename: string;
  lastUpdated: string;
  href: string;
};

const ResultsArea = ({
  steps,
  activeTab,
  setActiveTab,
  hasResults,
  selectedSourceIndex,
  setSelectedSourceIndex,
  adkResponse,
  adkSource,
  query,
}: ResultsAreaProps) => {
  const selectedSource = adkSource[selectedSourceIndex];

  const [answerFeedback, setAnswerFeedback] = useState<"like" | "dislike" | null>(null);
  const [selectedSourceSupabase, setSelectedSourceSupabase] = useState<string | null>(null);

  const allStepsComplete =
    steps.length > 0 && steps.every((step) => step.status === "done");

  const saveFeedback = async (value: "like" | "dislike") => {
    const nextValue = answerFeedback === value ? null : value;
    setAnswerFeedback(nextValue);

    if (!nextValue) return;

    const { error } = await supabase.from("answer_feedback").insert([
      {
        query,
        response: adkResponse,
        feedback: nextValue,
      },
    ]);

    if (error) {
      console.error("Error saving feedback:", error);
    }
  };

  const getSupabaseSource = async (source: string) => {
    console.log("Fetching source from Supabase with path:", source);

    const { data, error } = await supabase.storage
      .from("documents")
      .createSignedUrl(source, 60);

    if (error) {
      console.error("Error fetching signed URL from Supabase:", error);
      return;
    }

    console.log("Supabase public URL for source:", data.signedUrl);
    setSelectedSourceSupabase(data.signedUrl);
  };

  return (
    <div className="mt-8">
      <Tabs
        value={activeTab}
        onValueChange={(v) => setActiveTab(v as "steps" | "overview" | "sources")}
      >
        <div className="flex w-full items-center gap-4">
          <TabsList className="flex items-center gap-2">
            {hasResults && <TabsTrigger value="overview">Overview</TabsTrigger>}
            {hasResults && <TabsTrigger value="sources">Source Viewer</TabsTrigger>}
            <TabsTrigger value="steps">Steps</TabsTrigger>
          </TabsList>

          {allStepsComplete && (
            <TabsList className="ml-auto flex items-center gap-1">
              <button
                type="button"
                onClick={() => saveFeedback("like")}
                className={cn(
                  "inline-flex h-[calc(100%-1px)] items-center justify-center rounded-md border border-transparent px-2 py-1 transition-[color,box-shadow] hover:bg-background",
                  answerFeedback === "like" && "bg-background shadow-sm"
                )}
                aria-label="Like answer"
              >
                <IconThumbUp
                  className={cn(
                    "h-4 w-4",
                    answerFeedback === "like"
                      ? "text-blue-500"
                      : "text-muted-foreground"
                  )}
                />
              </button>

              <button
                type="button"
                onClick={() => saveFeedback("dislike")}
                className={cn(
                  "inline-flex h-[calc(100%-1px)] items-center justify-center rounded-md border border-transparent px-2 py-1 transition-[color,box-shadow] hover:bg-background",
                  answerFeedback === "dislike" && "bg-background shadow-sm"
                )}
                aria-label="Dislike answer"
              >
                <IconThumbDown
                  className={cn(
                    "h-4 w-4",
                    answerFeedback === "dislike"
                      ? "text-blue-500"
                      : "text-muted-foreground"
                  )}
                />
              </button>
            </TabsList>
          )}
        </div>

        {hasResults && (
          <TabsContent value="overview" className="mt-6">
            <div className="flex flex-col justify-between gap-4 md:flex-row">
              <div className="prose flex-1 dark:prose-invert">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {adkResponse}
                </ReactMarkdown>
              </div>

              <div className="flex w-full flex-1 flex-col gap-4 md:max-w-96">
                {adkSource.map((src, idx) => (
                  <div key={idx} className="rounded-md bg-muted p-4">
                    <div className="text-xs text-muted-foreground">
                      Last updated: {src.lastUpdated}
                    </div>
                    <h2 className="font-medium">{src.filename}</h2>

                    <div className="mt-4 flex float-right gap-4">
                      <Button className="h-auto p-0 text-blue-800" variant="link" asChild>
                        <a
                          href={src.href}
                          onClick={(e) => {
                            e.preventDefault();
                            setSelectedSourceIndex(idx);
                            getSupabaseSource(src.filename);
                            setActiveTab("sources");
                          }}
                        >
                          View here
                        </a>
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
            <div className="flex flex-col justify-between gap-4 md:flex-row">
              <div className="flex w-full flex-1 flex-col gap-4 md:max-w-96">
                {adkSource.map((src, idx) => {
                  const isSelected = idx === selectedSourceIndex;

                  return (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => {
                        setSelectedSourceIndex(idx);
                        getSupabaseSource(src.filename);
                      }}
                      className={cn(
                        "rounded-md border bg-muted p-4 text-left transition",
                        "hover:bg-muted/80 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
                        isSelected ? "border-ring" : "border-transparent"
                      )}
                      aria-pressed={isSelected}
                    >
                      <div className="text-xs text-muted-foreground">
                        Last updated: {src.lastUpdated}
                      </div>

                      <div className="mt-1 flex items-start justify-between gap-3">
                        <h2 className="font-medium">{src.filename}</h2>
                      </div>
                    </button>
                  );
                })}
              </div>

              <div className="h-160 flex-1 rounded-md border p-4">
                <div className="h-full font-medium">
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