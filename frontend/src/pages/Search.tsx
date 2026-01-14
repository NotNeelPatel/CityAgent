import * as React from "react";
import ReactMarkdown from "react-markdown";
import { Layout } from "@/components/layout";
import { Button } from "@/components/ui/button";
import { SearchBar } from "@/components/searchbar";
import { IconCircleCheck, IconCircleX, IconCircle, IconCircleDashed } from "@tabler/icons-react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";

export function Search() {
  const [query, setQuery] = React.useState("");
  const [submittedQuery, setSubmittedQuery] = React.useState<string | null>(null);

  const [activeTab, setActiveTab] = React.useState<"steps" | "overview" | "sources">("steps");
  const [steps, setSteps] = React.useState<Step[]>([]);
  const [hasResults, setHasResults] = React.useState(false);

  const [selectedSourceIndex, setSelectedSourceIndex] = React.useState<number>(0);

  const runIdRef = React.useRef(0);

  const startMockRun = React.useCallback((q: string) => {
    runIdRef.current += 1;
    const runId = runIdRef.current;

    setSubmittedQuery(q);
    setHasResults(false);
    setActiveTab("steps");

    setSteps([]);

    const plan = makeStepPlan(q);

    const emitNext = (index: number) => {
      if (runIdRef.current !== runId) return;

      // done, reveal other tabs and jump to overview
      if (index >= plan.length) {
        setHasResults(true);
        setActiveTab("overview");
        return;
      }

      const incoming = plan[index];

      // Step arrives as running
      setSteps((prev) => [
        ...prev,
        { ...incoming, status: "running" as const },
      ]);

      // After a moment, mark it done, then emit the next
      const runTime = 900 + Math.random() * 700;

      setTimeout(() => {
        if (runIdRef.current !== runId) return;

        setSteps((prev) =>
          prev.map((s) =>
            s.id === incoming.id ? { ...s, status: "done" } : s
          )
        );

        setTimeout(() => emitNext(index + 1), 250);
      }, runTime);
    };

    emitNext(0);
  }, []);

  // live ref of steps to avoid stale closure in timeouts
  const stepsRef = React.useRef<Step[]>([]);
  React.useEffect(() => {
    stepsRef.current = steps;
  }, [steps]);

  const onSubmit = (q: string) => {
    const trimmed = q.trim();
    if (!trimmed) return;
    startMockRun(trimmed);
  };

  const hasSearch = submittedQuery === null;

  return (
    <Layout>
      <div className="mx-auto w-full max-w-5xl px-10">
        <div className={cn("flex flex-col items-center gap-10", hasSearch ? "h-[80vh] justify-center" : "pt-6")} >
          {hasSearch && <h1 className="text-7xl font-bold">CityAgent</h1>}

          {SearchBar({ query, setQuery, onSubmit })}

          {hasSearch && QuickSearchItem({ onSubmit, setQuery })}

        </div>

        {!hasSearch && ResultsArea({ steps, activeTab, setActiveTab, hasResults, selectedSourceIndex, setSelectedSourceIndex })}
      </div>
    </Layout>
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

function makeStepPlan(query: string): Array<Omit<Step, "status">> {
  const plans = [
    [
      { id: "s1", title: "Orchestrator: selecting agents", detail: `Query: "${query}"` },
      { id: "s2", title: "RAG agent: retrieving sources" },
      { id: "s3", title: "Math agent: computing metrics" },
      { id: "s4", title: "Answer agent: compiling response" },
    ],
    [
      { id: "s1", title: "Orchestrator: asking agents", detail: `Query: "${query}"` },
      { id: "s2", title: "Geo agent: resolving locations" },
      { id: "s3", title: "Validator: checking consistency" },
      { id: "s4", title: "Answer agent: formatting output" },
    ],
  ];

  return plans[Math.floor(Math.random() * plans.length)];
}

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
  setActiveTab: React.Dispatch<React.SetStateAction<"steps" | "overview" | "sources">>;
  hasResults: boolean;
  selectedSourceIndex: number;
  setSelectedSourceIndex: React.Dispatch<React.SetStateAction<number>>;
};

type Source = {
  filename: string;
  lastUpdated: string;
  href: string;
};

const overviewAnswer = `
## Overview

This is a **placeholder response** for now.

- Once wired up  
- This will show agent outputs  
- Including citations, lists, and formatting
`.trim();

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
const ResultsArea = ({ steps, activeTab, setActiveTab, hasResults, selectedSourceIndex, setSelectedSourceIndex }: ResultsAreaProps) => {
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
                <ReactMarkdown>{overviewAnswer}</ReactMarkdown>
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
            {steps.map((s) => (
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
            ))}
          </div>
        </TabsContent>

      </Tabs>
    </div>
  );
};