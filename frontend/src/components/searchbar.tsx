import { IconSearch } from "@tabler/icons-react";
import { Input } from "@/components/ui/input";

type SearchBarProps = {
  placeholder?: string;
  query: string;
  setQuery: (q: string) => void;
  onSubmit: (q: string) => void;
};

export function SearchBar({ placeholder, query, setQuery, onSubmit }: SearchBarProps) {
  return (
    <div className="relative w-full">
      <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center justify-center pl-3 text-muted-foreground">
        <IconSearch className="size-4" />
        <span className="sr-only">Search</span>
      </div>

      <Input
        id="search-input"
        type="search"
        placeholder={placeholder || "Ask us anything..."}
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") onSubmit(query);
        }}
        className="peer px-9 [&::-webkit-search-cancel-button]:appearance-none [&::-webkit-search-decoration]:appearance-none [&::-webkit-search-results-button]:appearance-none [&::-webkit-search-results-decoration]:appearance-none"
      />
    </div>
  );
};