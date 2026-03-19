import { useEffect, useState, type Dispatch, type SetStateAction } from "react";
import { StatusPill, type Step } from "@/components/statuspill";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
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
  conversationId: string | null;
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
  conversationId,
}: ResultsAreaProps) => {
  const selectedSource = adkSource[selectedSourceIndex];
  const [answerFeedback, setAnswerFeedback] = useState<"like" | "dislike" | null>(null);
  const [selectedSourceSupabase, setSelectedSourceSupabase] = useState<string | null>(null);

<<<<<<< 160-adding-dislikelike-button
  useEffect(() => {
    const loadFeedback = async () => {
      setAnswerFeedback(null);

      if (!conversationId) return;

      const { data, error } = await supabase
        .from("answer_feedback")
        .select("feedback")
        .eq("conversation_id", conversationId)
        .maybeSingle();

      if (error) {
        console.error("Error loading feedback:", error);
        return;
      }

      if (data?.feedback === "like" || data?.feedback === "dislike") {
        setAnswerFeedback(data.feedback);
      }
    };

    loadFeedback();
  }, [conversationId]);

  const saveFeedback = async (value: "like" | "dislike") => {
    if (!conversationId) return;

    setAnswerFeedback(value);

    const { data: existing, error: existingError } = await supabase
      .from("answer_feedback")
      .select("id")
      .eq("conversation_id", conversationId)
      .maybeSingle();

    if (existingError) {
      console.error("Error checking existing feedback:", existingError);
      return;
    }

    if (existing?.id) {
      const { error } = await supabase
        .from("answer_feedback")
        .update({ feedback: value })
        .eq("id", existing.id);

      if (error) {
        console.error("Error updating feedback:", error);
      }

      return;
    }

    const { error } = await supabase.from("answer_feedback").insert([
      {
        conversation_id: conversationId,
        feedback: value,
      },
    ]);

    if (error) {
      console.error("Error saving feedback:", error);
=======
  const getArgumentEntries = (argumentDetail?: string): Array<{ key: string; value: string }> | null => {
    if (!argumentDetail) return null;

    try {
      const parsed = JSON.parse(argumentDetail);

      if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
        return null;
      }

      return Object.entries(parsed).map(([key, value]) => ({
        key,
        value: typeof value === "string" ? value : JSON.stringify(value),
      }));
    } catch {
      return null;
>>>>>>> main
    }
  };

  const getSupabaseSource = async (source: string) => {
    const { data, error } = await supabase.storage
      .from("documents")
      .createSignedUrl(source, 60);

    if (error) {
      console.error("Error fetching signed URL from Supabase:", error);
      return;
    }

    setSelectedSourceSupabase(data.signedUrl);
  };
<<<<<<< 160-adding-dislikelike-button
=======

  const renderArguments = (argumentDetail: string) => {
    const entries = getArgumentEntries(argumentDetail);

    if (!entries || entries.length === 0) {
      return (
        <div className="mt-1 whitespace-pre-line text-sm text-muted-foreground">
          <span className="font-medium">Arguments:</span>
          <div className="mt-1 rounded-md p-2 text-xs text-muted-foreground whitespace-pre-wrap break-words">
            {argumentDetail}
          </div>
        </div>
      );
    }

    return (
      <div className="mt-1 whitespace-pre-line text-sm text-muted-foreground">
        <span className="font-medium">Arguments:</span>
        <div className="mt-1 space-y-1 rounded-md p-2 text-xs text-muted-foreground">
          {entries.map((entry) => (
            <div key={entry.key} className="whitespace-pre-wrap break-words">
              <span className="font-medium text-foreground">{entry.key}:</span>{" "}
              <span>{entry.value}</span>
            </div>
          ))}
        </div>
      </div>
    );
  };

  const renderResponse = (responseDetail: string) => (
    <details className="mt-2 text-sm text-muted-foreground">
      <summary className="cursor-pointer select-none font-medium">
        Response
      </summary>
      <pre className="mt-2 whitespace-pre-wrap break-words rounded-md bg-muted p-2 text-xs text-muted-foreground">
        {responseDetail}
      </pre>
    </details>
  );
>>>>>>> main

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

          {hasResults && conversationId && (
            <div className="ml-auto">
              <ToggleGroup
                type="single"
                value={answerFeedback ?? ""}
                onValueChange={(value) => {
                  if (value === "like" || value === "dislike") {
                    saveFeedback(value);
                  }
                }}
              >
                <ToggleGroupItem value="like" aria-label="Like">
                  <IconThumbUp className="h-4 w-4" />
                </ToggleGroupItem>
                <ToggleGroupItem value="dislike" aria-label="Dislike">
                  <IconThumbDown className="h-4 w-4" />
                </ToggleGroupItem>
              </ToggleGroup>
            </div>
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

                    <div className="mt-4 flex justify-end gap-4">
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
                    {s.argumentDetail && renderArguments(s.argumentDetail)}
                    {s.responseDetail && renderResponse(s.responseDetail)}
                    {!s.argumentDetail && !s.responseDetail && s.detail && (
                      <div className="mt-1 whitespace-pre-line text-sm text-muted-foreground">
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