import { useState, type Dispatch, type SetStateAction } from "react";
import ReactMarkdown from "react-markdown";
import { Layout } from "@/components/layout";
import { Button } from "@/components/ui/button";
import { SearchBar } from "@/components/searchbar";
import { IconCircleCheck, IconCircleX, IconCircle, IconCircleDashed } from "@tabler/icons-react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";
import { BACKEND_URL } from "@/lib/client";

export function Search() {
  const [query, setQuery] = useState("");
  const [submittedQuery, setSubmittedQuery] = useState<string | null>(null);

  const [activeTab, setActiveTab] = useState<"steps" | "overview" | "sources">("steps");
  const [steps, setSteps] = useState<Step[]>([]);
  const [hasResults, setHasResults] = useState(false);

  const [sessionId, setSessionId] = useState<string | null>(null);
  const [userId, setUserId] = useState<string | null>(null);

  const [adkResponse, setAdkResponse] = useState<string>("");
  const [selectedSourceIndex, setSelectedSourceIndex] = useState<number>(0);

  const processADKEvent = (rawData: any) => {
    const author = rawData.author;
    const parts = rawData.content?.parts || [];

    parts.forEach((part: any) => {
      // Check for agent handoffs or tool calls
      if (part.functionCall) {
        const taskName = part.functionCall.name === "transfer_to_agent"
          ? `Transferring to ${part.functionCall.args.agent_name}`
          : `Agent ${author} is running tool ${part.functionCall.name}`;
        setSteps((prev) => [
          ...prev.map(s => ({ ...s, status: "done" as const })),
          { id: rawData.id, title: taskName, status: "running" as const }
        ]);
      }

      // Check for final text response
      if (part.text) {
        setAdkResponse((part.text));
        setHasResults(true);
        setActiveTab("overview");
      }

    });
  };

  const initializeSession = async (): Promise<{ session_id: string; user_id: string } | null> => {
    try {
      // TODO: replace with actual user/session management
      // This can be done by using a randomized userID or one associated with the auth of the user
      // and then for sessionID either we fetch from history or we create a new one. 
      // This is NOT something that will be done with this current PR though (issue #107)
      // At the moment this just creates a new session for a hardcoded "dev" user every time
      // and you can refresh to reset history.

      // For now generate a random UUID for session ID
      let random_session_id = crypto.randomUUID();

      // We should eventually make a system where we have a dedicated user and not just use dev
      // And also something that is not handled client side only

      const response = await fetch(`${BACKEND_URL}/adk/apps/city_agent/users/dev/sessions/${random_session_id}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
      });
      if (!response.ok) {
        const errBody = await response.json().catch(() => ({}));
        // Check if session already exists and reuse
        if (errBody && typeof errBody.detail === "string" && errBody.detail.startsWith("Session already exists")) {
          setSessionId(random_session_id);
          setUserId("dev");
          return { session_id: random_session_id, user_id: "dev" };
        }
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();

      setSessionId(data.id);
      setUserId(data.userId);

      return { session_id: data.id, user_id: data.userId };

    } catch (error) {
      console.error("Error initializing session:", error)
      return null;
    }
  };

  const handleSearch = async (q: string) => {
    setSubmittedQuery(q);
    setHasResults(false);
    setActiveTab("steps");
    setSteps([]);
    setAdkResponse("");

    try {
      let sid = sessionId;
      let uid = userId;
      if (!sid || !uid) {
        const res = await initializeSession();
        sid = res?.session_id ?? sid;
        uid = res?.user_id ?? uid;
      }

      const response = await fetch(`${BACKEND_URL}/adk/run_sse`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          appName: "city_agent",
          user_id: uid,
          session_id: sid,
          new_message: {
            parts: [{ text: q }],
            role: "user",
          },
        }),
      });
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      if (!response.body) {
        throw new Error("ReadableStream not supported in this browser.");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";  // Keep incomplete line in buffer

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed.startsWith("data: ")) continue;

          try {
            const data = JSON.parse(trimmed.replace("data: ", ""));
            processADKEvent(data);
          } catch (error) {
            console.error("Error parsing SSE JSON line:", error);
          }
        }
      }
    } catch (error) {
      console.error("Error during search:", error);
    } finally {
      setSteps((prev) => prev.map(s => ({ ...s, status: "done" })));
    }
  };

  const onSubmit = (q: string) => {
    const trimmed = q.trim();
    if (!trimmed) return;
    handleSearch(trimmed);
  };

  const hasSearch = submittedQuery === null;

  return (
    <Layout hasAIdisclaimer={true}>
      <div className="mx-auto w-full max-w-5xl md:px-10 relative">
        <div className={cn("flex flex-col items-center gap-10", hasSearch ? "h-[80vh] justify-center" : "md:pt-6")} >
          {hasSearch && <h1 className="text-7xl font-bold">CityAgent</h1>}

          {SearchBar({ query, setQuery, onSubmit })}
          {hasSearch && QuickSearchItem({ onSubmit, setQuery })}

        </div>

        {!hasSearch && ResultsArea({ steps, activeTab, setActiveTab, hasResults, selectedSourceIndex, setSelectedSourceIndex, adkResponse })}
      </div>
    </Layout >
  );
};

/******************** Mock quick search items ********************/
const QuickSearchs = [
  { questions: "What is the road condition of Longfields Rd?", href: "#" },
  { questions: "Are there any parks near Baseline?", href: "#" },
  { questions: "What public transport is available near Carleton University?", href: "#" },
  { questions: "What are the nearby schools in Nepean?", href: "#" },
  { questions: "What are the crime rates in Ottawa?", href: "#" },
  { questions: "What are the popular restaurants in downtown Ottawa?", href: "#" },
];

type QuickSearchItemProps = {
  onSubmit: (q: string) => void;
  setQuery: (q: string) => void;
};

const QuickSearchItem = ({ onSubmit, setQuery }: QuickSearchItemProps) => {
  return (
    <div className="grid w-full grid-cols-3 gap-4">
      {QuickSearchs.map((item, idx) => (
        <Button
          key={idx}
          variant="secondary"
          className="h-auto items-start justify-start whitespace-normal break-words text-left"
          asChild
        >
          <a
            href={item.href}
            onClick={(e) => {
              e.preventDefault();
              setQuery(item.questions);
              onSubmit(item.questions);
            }}
          >
            {item.questions}
          </a>
        </Button>
      ))}
    </div>

  );
};

/******************** Mock Step Plan and Status Pill ********************/
type StepStatus = "queued" | "running" | "done" | "error";

type Step = {
  id: string;
  title: string;
  status: StepStatus;
  detail?: string;
};

const statusLabel: Record<StepStatus, string> = {
  queued: "Queued",
  running: "Running",
  done: "Done",
  error: "Error",
};

function StatusPill({ status }: { status: StepStatus }) {
  const getStatusClass = (status: StepStatus) => {
    switch (status) {
      case "done":
        return "text-emerald-600";
      case "error":
        return "text-destructive";
      default:
        return "text-muted-foreground";
    }
  };

  const style = "size-6 " + getStatusClass(status);

  return (
    <span className={style}>
      {status === "queued" && <IconCircle className={style} />}
      {status === "running" && <IconCircleDashed className={style} />}
      {status === "done" && <IconCircleCheck className={style} />}
      {status === "error" && <IconCircleX className={style} />}
    </span>
  );
}


/******************** Results Area with Tabs ********************/
type ResultsAreaProps = {
  steps: Step[];
  activeTab: "steps" | "overview" | "sources";
  setActiveTab: Dispatch<SetStateAction<"steps" | "overview" | "sources">>;
  hasResults: boolean;
  selectedSourceIndex: number;
  setSelectedSourceIndex: Dispatch<SetStateAction<number>>;
  adkResponse: string;
};

type Source = {
  filename: string;
  lastUpdated: string;
  href: string;
};

// TODO: Replace with sources. ADK needs to respond with a list of sources that can be parsed easier.
const sources: Source[] = [
  {
    filename: "roads_data.xlsx (Longfields Rd segment)",
    lastUpdated: "2023-10-01",
    href: '#',
  },
  {
    filename: "transit_routes.csv (Carleton vicinity)",
    lastUpdated: "2023-09-28",
    href: '#',
  },
  {
    filename: "parks.geojson (Baseline area)",
    lastUpdated: "2023-09-15",
    href: '#',
  },
];
const ResultsArea = ({ steps, activeTab, setActiveTab, hasResults, selectedSourceIndex, setSelectedSourceIndex, adkResponse }: ResultsAreaProps) => {
  const selectedSource = sources[selectedSourceIndex];

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
                <ReactMarkdown>{adkResponse}</ReactMarkdown>
              </div>

              <div className="flex-1 w-full md:max-w-96 flex flex-col gap-4">
                {sources.map((src, idx) => (
                  <div key={idx} className="rounded-md bg-muted p-4">
                    <div className="text-muted-foreground text-xs">Last updated: {src.lastUpdated}</div>
                    <h2 className="font-medium">{src.filename}</h2>
                    <div className="flex float-right gap-4 mt-4">
                      <Button className="text-blue-800 p-0 h-auto" variant="link" asChild>
                        <a href={src.href}
                          onClick={(e) => {
                            e.preventDefault();
                            setSelectedSourceIndex(idx);
                            setActiveTab("sources");
                          }}>View here</a>
                      </Button>
                      <Button className="text-blue-800 p-0 h-auto" variant="link" asChild>
                        <a href={src.href} target="_blank">Original PDF →</a>
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
                {sources.map((src, idx) => {
                  const isSelected = idx === selectedSourceIndex;

                  return (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => setSelectedSourceIndex(idx)}
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
                          Original PDF →
                        </a>
                      </Button>
                    </button>
                  );
                })}
              </div>

              <div className="flex-1 h-160 rounded-md border p-4">
                <div className="text-muted-foreground text-xs mb-2">Selected file</div>
                <div className="font-medium">
                  {selectedSource ? selectedSource.filename : "No file selected"}
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