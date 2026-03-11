import { useState } from "react";
import { Layout } from "@/components/layout";
import { SearchBar } from "@/components/searchbar";
import { ResultsArea, type Source } from "@/components/results_area";
import { QuickSearchItem } from "@/components/quick_search";
import { type Step } from "@/components/statuspill";
import { cn } from "@/lib/utils";
import { fetchData } from "@/lib/client";
import { useAuth } from "@/context/AuthContext";

export function Search() {
  const { user } = useAuth();
  const [query, setQuery] = useState("");
  const [submittedQuery, setSubmittedQuery] = useState<string | null>(null);

  const [activeTab, setActiveTab] = useState<"steps" | "overview" | "sources">("steps");
  const [steps, setSteps] = useState<Step[]>([]);
  const [hasResults, setHasResults] = useState(false);

  const [sessionId, setSessionId] = useState<string | null>(null);
  const [userId, setUserId] = useState<string | null>(null);

  const [adkResponse, setAdkResponse] = useState<string>("");
  const [adkSource, setAdkSource] = useState<Source[]>([]);
  const [selectedSourceIndex, setSelectedSourceIndex] = useState<number>(0);

  const processADKEvent = (rawData: any) => {
    const author = rawData.author;
    const parts = rawData.content?.parts || [];

    parts.forEach((part: any) => {
      // Check for agent handoffs or tool calls
      if (part.functionCall) {
        const taskName = part.functionCall.name === "transfer_to_agent"
          ? `Transferring to ${part.functionCall.args.agent_name}`
          : `${author} Agent is running tool: ${part.functionCall.name}`;
        setSteps((prev) => [
          ...prev.map(s => ({ ...s, status: "done" as const })),
          { id: rawData.id, title: taskName, status: "running" as const }
        ]);
      }

      // Check for final text response
      if (part.text && author === "Reasoner") {
        try {
          const parsed = JSON.parse(part.text);
          if (parsed.response) {
            setAdkResponse((parsed.response));
            setAdkSource((parsed.sources || []));
            setHasResults(true);
            setActiveTab("overview");
            return;
          }
        } catch (error) {
          console.error("Error parsing ADK response part text:", error);
        }
      } else if (part.text) {
        const taskName = `${author} Agent completed a step`;
        setSteps((prev) => [
          ...prev.map(s => ({ ...s, status: "done" as const })),
          { id: rawData.id, title: taskName, status: "done" as const, detail: part.text }
        ]);
      }

    });
  };

  const initializeSession = async (): Promise<{ session_id: string; user_id: string } | null> => {
    try {
      let random_session_id = crypto.randomUUID();

      const currentUserId = user?.id || "dev";

      const response = await fetchData(`/adk/apps/city_agent/users/${currentUserId}/sessions/${random_session_id}`, {
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
          setUserId(currentUserId);
          return { session_id: random_session_id, user_id: currentUserId };
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

      const response = await fetchData(`/adk/run_sse`, {
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

          <SearchBar query={query} setQuery={setQuery} onSubmit={onSubmit} />
          {hasSearch && <QuickSearchItem onSubmit={onSubmit} setQuery={setQuery} />}

        </div>

        {!hasSearch && (
          <ResultsArea
            steps={steps}
            activeTab={activeTab}
            setActiveTab={setActiveTab}
            hasResults={hasResults}
            selectedSourceIndex={selectedSourceIndex}
            setSelectedSourceIndex={setSelectedSourceIndex}
            adkResponse={adkResponse}
            adkSource={adkSource}
          />
        )}
      </div>
    </Layout >
  );
};
