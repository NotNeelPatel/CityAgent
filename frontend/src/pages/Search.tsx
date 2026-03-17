import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Layout } from "@/components/layout";
import { SearchBar } from "@/components/searchbar";
import { ResultsArea, type Source } from "@/components/results_area";
import { QuickSearchItem } from "@/components/quick_search";
import { type Step } from "@/components/statuspill";
import { cn } from "@/lib/utils";
import { fetchData } from "@/lib/client";
import { useAuth } from "@/context/AuthContext";

type ConversationHistoryItem = {
  id: string;
  query: string;
  date: string;
  sessionId: string;
};

type SavedConversationState = {
  submittedQuery: string | null;
  adkResponse: string;
  adkSource: Source[];
  steps: Step[];
  hasResults: boolean;
  activeTab: "steps" | "overview" | "sources";
  selectedSourceIndex: number;
};

export function Search() {
  const { user } = useAuth();
  const [searchParams] = useSearchParams();

  const [query, setQuery] = useState("");
  const [submittedQuery, setSubmittedQuery] = useState<string | null>(null);

  const [activeTab, setActiveTab] = useState<"steps" | "overview" | "sources">("steps");
  const [steps, setSteps] = useState<Step[]>([]);
  const [hasResults, setHasResults] = useState(false);

  const [sessionId, setSessionId] = useState<string | null>(null);
  const [userId, setUserId] = useState<string | null>(null);
  const [conversationId, setConversationId] = useState<string | null>(null);

  const [adkResponse, setAdkResponse] = useState("");
  const [adkSource, setAdkSource] = useState<Source[]>([]);
  const [selectedSourceIndex, setSelectedSourceIndex] = useState(0);

  const currentUserId = user?.id || "dev";
  const historyKey = `search_history_${currentUserId}`;

  const getConversationStateKey = (id: string) => {
    return `conversation_state_${currentUserId}_${id}`;
  };

  const resetSearchState = () => {
    setSteps([]);
    setHasResults(false);
    setAdkResponse("");
    setAdkSource([]);
    setSelectedSourceIndex(0);
    setActiveTab("steps");
  };

  const getHistoryFromStorage = (): ConversationHistoryItem[] => {
    try {
      const raw = localStorage.getItem(historyKey);
      if (!raw) return [];

      const parsed = JSON.parse(raw);
      if (!Array.isArray(parsed)) return [];

      return parsed;
    } catch (error) {
      console.error("Error reading history from localStorage:", error);
      return [];
    }
  };

  const saveHistoryToStorage = (history: ConversationHistoryItem[]) => {
    localStorage.setItem(historyKey, JSON.stringify(history));
    window.dispatchEvent(new Event("historyUpdated"));
  };

  const saveConversationState = (id: string) => {
    const state: SavedConversationState = {
      submittedQuery,
      adkResponse,
      adkSource,
      steps,
      hasResults,
      activeTab,
      selectedSourceIndex,
    };

    localStorage.setItem(getConversationStateKey(id), JSON.stringify(state));
  };

  const loadConversationState = (id: string): SavedConversationState | null => {
    try {
      const raw = localStorage.getItem(getConversationStateKey(id));
      if (!raw) return null;
      return JSON.parse(raw);
    } catch (error) {
      console.error("Error loading saved conversation state:", error);
      return null;
    }
  };

  const processADKEvent = (rawData: any) => {
    const author = rawData.author;
    const parts = rawData.content?.parts || [];

    const parseJSON = (value: unknown): unknown => {
      if (typeof value !== "string") return value;

      const trimmed = value.trim();
      if (!trimmed) return value;

      if (
        (trimmed.startsWith("{") && trimmed.endsWith("}")) ||
        (trimmed.startsWith("[") && trimmed.endsWith("]"))
      ) {
        try {
          return JSON.parse(trimmed);
        } catch {
          return value;
        }
      }

      return value;
    };

    const formatDetailValue = (value: unknown): string => {
      const parsedValue = parseJSON(value);

      if (typeof parsedValue === "string") {
        return parsedValue;
      }

      try {
        return JSON.stringify(parsedValue, null, 2).trim();
      } catch {
        return String(parsedValue ?? "").trim();
      }
    };

    parts.forEach((part: any) => {
      // Function call
      if (part.functionCall) {
        const isTransfer = part.functionCall.name === "transfer_to_agent";

        const stepTitle = isTransfer
          ? `Transferring to ${part.functionCall.args.agent_name}`
          : `${author} Agent is running tool: ${part.functionCall.name}`;

        const argumentDetail = isTransfer
          ? ""
          : formatDetailValue(part.functionCall.args);

        setSteps((prev) => [
          ...prev.map((step) => ({ ...step, status: "done" as const })),
          {
            id: rawData.id,
            title: stepTitle,
            status: "running" as const,
            argumentDetail,
          },
        ]);
        return;
      }

      // Function Response
      if (part.functionResponse) {
        const responseValue =
          part.functionResponse.response.result ?? part.functionResponse;
        const responseDetail = formatDetailValue(responseValue).includes("transfer_to_agent")
          ? "" // Remove transfer details
          : `${formatDetailValue(responseValue)}`;

        setSteps((prev) => {
          // Get the most recent running step index to update with the response
          let runningIndex = -1;
          for (let i = prev.length - 1; i >= 0; i--) {
            if (prev[i].status === "running") {
              runningIndex = i;
              break;
            }
          }

          // Fallback if no step found
          if (runningIndex === -1) {
            return [
              ...prev,
              {
                id: rawData.id,
                title: `Tool response received`,
                status: "done" as const,
                responseDetail,
              },
            ];
          }

          // Update found running step
          const updated = [...prev];
          updated[runningIndex] = {
            ...updated[runningIndex],
            status: "done" as const,
            responseDetail, 
          };

          return updated;
        });

        return;
      }

      if (part.text && author === "Reasoner") {
        try {
          const parsedText = JSON.parse(part.text);

          if (parsedText.response) {
            setAdkResponse(parsedText.response);
            setAdkSource(parsedText.sources || []);
            setHasResults(true);
            setActiveTab("overview");
          }
        } catch (error) {
          console.error("Error parsing ADK response:", error);
        }
      } else if (part.text) {
        const stepTitle = `${author} Agent completed a step`;

        setSteps((prev) => [
          ...prev.map((step) => ({ ...step, status: "done" as const })),
          {
            id: rawData.id,
            title: stepTitle,
            status: "done" as const,
            detail: part.text,
          },
        ]);
      }
    });
  };

  const initializeSession = async (existingSessionId?: string) => {
    try {
      const sessionToUse = existingSessionId || crypto.randomUUID();

      const response = await fetchData(
        `/adk/apps/city_agent/users/${currentUserId}/sessions/${sessionToUse}`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
        }
      );

      if (!response.ok) {
        const errBody = await response.json().catch(() => ({}));

        if (
          errBody &&
          typeof errBody.detail === "string" &&
          errBody.detail.startsWith("Session already exists")
        ) {
          setSessionId(sessionToUse);
          setUserId(currentUserId);

          return {
            session_id: sessionToUse,
            user_id: currentUserId,
          };
        }

        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();

      setSessionId(data.id);
      setUserId(data.userId);

      return {
        session_id: data.id,
        user_id: data.userId,
      };
    } catch (error) {
      console.error("Error initializing session:", error);
      return null;
    }
  };

  const updateConversationHistory = (conversationIdToUse: string, searchText: string, sid: string) => {
    const oldHistory = getHistoryFromStorage();

    const newHistory: ConversationHistoryItem[] = [
      {
        id: conversationIdToUse,
        query: searchText,
        date: new Date().toISOString(),
        sessionId: sid,
      },
      ...oldHistory.filter((item) => item.id !== conversationIdToUse),
    ].slice(0, 20);

    saveHistoryToStorage(newHistory);
  };

  const readSSEStream = async (response: Response) => {
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
      buffer = lines.pop() || "";

      for (const line of lines) {
        const trimmedLine = line.trim();
        if (!trimmedLine.startsWith("data: ")) continue;

        try {
          const jsonData = JSON.parse(trimmedLine.replace("data: ", ""));
          processADKEvent(jsonData);
        } catch (error) {
          console.error("Error parsing SSE JSON line:", error);
        }
      }
    }
  };

  const handleSearch = async (searchText: string, existingConversationId?: string) => {
    if (!searchText.trim()) return;

    const currentConversationId =
      existingConversationId || conversationId || crypto.randomUUID();

    setConversationId(currentConversationId);

    let sid = sessionId;
    let uid = userId;

    try {
      if (!sid || !uid) {
        const history = getHistoryFromStorage();
        const oldConversation = history.find(
          (item) => item.id === currentConversationId
        );

        const sessionData = await initializeSession(oldConversation?.sessionId);

        sid = sessionData?.session_id ?? null;
        uid = sessionData?.user_id ?? null;
      }

      if (!sid || !uid) {
        throw new Error("Session initialization failed.");
      }

      updateConversationHistory(currentConversationId, searchText, sid);

      const response = await fetchData("/adk/run_sse", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          appName: "city_agent",
          user_id: uid,
          session_id: sid,
          new_message: {
            parts: [{ text: searchText }],
            role: "user",
          },
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      await readSSEStream(response);
    } catch (error) {
      console.error("Error during search:", error);
    } finally {
      setSteps((prev) =>
        prev.map((step) => ({
          ...step,
          status: "done",
        }))
      );
    }
  };

  const onSubmit = (searchText: string) => {
    const trimmed = searchText.trim();
    if (!trimmed) return;

    setSubmittedQuery(trimmed);
    setQuery(trimmed);

    resetSearchState();
    handleSearch(trimmed, conversationId || undefined);
  };

  useEffect(() => {
    const conversationFromUrl = searchParams.get("conversation");
    const queryFromUrl = searchParams.get("q");

    if (!conversationFromUrl) return;

    setConversationId(conversationFromUrl);

    const history = getHistoryFromStorage();
    const selectedConversation = history.find(
      (item) => item.id === conversationFromUrl
    );

    if (selectedConversation) {
      setSessionId(selectedConversation.sessionId);
      setUserId(currentUserId);
    }

    const savedState = loadConversationState(conversationFromUrl);

    if (savedState) {
      setSubmittedQuery(savedState.submittedQuery);
      setQuery(savedState.submittedQuery || queryFromUrl || "");
      setAdkResponse(savedState.adkResponse || "");
      setAdkSource(savedState.adkSource || []);
      setSteps(savedState.steps || []);
      setHasResults(savedState.hasResults || false);
      setActiveTab(savedState.activeTab || "overview");
      setSelectedSourceIndex(savedState.selectedSourceIndex || 0);
    } else if (selectedConversation) {
      setSubmittedQuery(selectedConversation.query);
      setQuery(selectedConversation.query);
    } else if (queryFromUrl) {
      setSubmittedQuery(queryFromUrl);
      setQuery(queryFromUrl);
    }
  }, [searchParams, currentUserId]);

  useEffect(() => {
    if (!conversationId) return;
    saveConversationState(conversationId);
  }, [
    conversationId,
    submittedQuery,
    adkResponse,
    adkSource,
    steps,
    hasResults,
    activeTab,
    selectedSourceIndex,
  ]);

  const hasSearch = submittedQuery === null;

  return (
    <Layout hasAIdisclaimer={true}>
      <div className="relative mx-auto w-full max-w-5xl md:px-10">
        <div
          className={cn(
            "flex flex-col items-center gap-10",
            hasSearch ? "h-[80vh] justify-center" : "md:pt-6"
          )}
        >
          {hasSearch && <h1 className="text-7xl font-bold">CityAgent</h1>}

          <SearchBar query={query} setQuery={setQuery} onSubmit={onSubmit} />
          {hasSearch && (
            <QuickSearchItem onSubmit={onSubmit} setQuery={setQuery} />
          )}
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
    </Layout>
  );
}