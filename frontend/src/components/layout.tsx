import { cn } from "@/lib/utils";
import { CityAgentSidebar } from "./cityagent_sidebar";

export function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div
      className={cn(
        "mx-auto flex w-full flex-1 flex-col overflow-hidden rounded-md border border-neutral-200 bg-gray-100 md:flex-row dark:border-neutral-700 dark:bg-neutral-800",
        "h-dvh",
      )}
    >
      <CityAgentSidebar />

      <div className="flex min-h-0 flex-1">
        <div className="flex min-h-0 w-full flex-1 flex-col gap-2 rounded-tl-2xl rounded-tr-2xl border border-neutral-200 bg-white p-2 dark:border-neutral-700 dark:bg-neutral-900 md:rounded-bl-2xl md:rounded-tr-none md:p-10">
          <div className="flex min-h-0 w-full flex-1 flex-col overflow-y-auto">
            {children}
          </div>
        </div>
      </div>
    </div>
  );
}