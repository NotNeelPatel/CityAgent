import { cn } from "@/lib/utils";
import { CityAgentSidebar } from "./cityagent_sidebar";

export function Layout({ children, hasAIdisclaimer }: { children: React.ReactNode; hasAIdisclaimer?: boolean }) {
  return (
    <div
      className={cn(
        "mx-auto flex w-full flex-1 flex-col overflow-hidden rounded-md border border-neutral-200 bg-gray-100 md:flex-row dark:border-neutral-700 dark:bg-neutral-800",
        "h-dvh",
      )}
    >
      <CityAgentSidebar />

      <div className="flex min-h-0 flex-1">
        {/* ⬇️ This is the positioning context */}
        <div className="relative flex min-h-0 w-full flex-1 flex-col gap-2 rounded-tl-2xl rounded-tr-2xl border border-neutral-200 bg-white p-2 dark:border-neutral-700 dark:bg-neutral-900 md:rounded-bl-2xl md:rounded-tr-none md:p-10">

          {/* Scrollable content */}
          <div className="flex min-h-0 w-full flex-1 flex-col overflow-y-auto">
            {children}
          </div>

          {/* Fixed-to-bottom disclaimer */}
          {hasAIdisclaimer && (
            <div className="absolute bottom-2 inset-x-0 text-center text-xs text-muted-foreground">
              Responses may contain inaccuracies.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}