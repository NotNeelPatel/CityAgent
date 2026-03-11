import { useEffect, useState } from "react";
import { Sidebar, SidebarBody, SidebarLink } from "@/components/ui/aceternity/sidebar";
import type { Links } from "@/components/ui/aceternity/sidebar";
import {
  IconArrowLeft,
  IconPlus,
  IconSun,
  IconMoon,
  IconHistory,
  IconLayoutDashboard,
} from "@tabler/icons-react";
import CityAgentWordmark from "@/assets/cityagent_wordmark.svg";
import CityAgentLogoIcon from "@/assets/cityagent_logo.svg";
import { useAuth } from "@/context/AuthContext";
import { Link, useNavigate } from "react-router-dom";
import { useTheme } from "@/context/ThemeContext";

type StoredConversation = {
  id: string;
  query: string;
  date: string;
  sessionId: string;
};

export function CityAgentSidebar() {
  const [open, setOpen] = useState(false);
  const { signOut, role, user } = useAuth();
  const { theme, setTheme } = useTheme();
  const navigate = useNavigate();

  const [history, setHistory] = useState<StoredConversation[]>([]);

  const isDark =
    theme === "dark" ||
    (theme === "system" &&
      window.matchMedia?.("(prefers-color-scheme: dark)").matches);

  const toggleTheme = () => {
    setTheme(isDark ? "light" : "dark");
  };

  const links_top: Links[] = [
    {
      kind: "link",
      label: "New Search",
      href: "/search",
      icon: <IconPlus className="h-5 w-5 shrink-0" />,
    },
  ];

  const links_bottom: Links[] = [
    {
      kind: "action",
      label: isDark ? "Light Mode" : "Dark Mode",
      onClick: toggleTheme,
      icon: isDark ? (
        <IconSun className="h-5 w-5 shrink-0" />
      ) : (
        <IconMoon className="h-5 w-5 shrink-0" />
      ),
    },
    ...(role === "admin"
      ? [
          {
            kind: "link",
            label: "Dashboard",
            href: "/dashboard",
            icon: <IconLayoutDashboard className="h-5 w-5 shrink-0" />,
          } satisfies Links,
        ]
      : []),
    {
      kind: "action",
      label: "Sign Out",
      onClick: signOut,
      icon: <IconArrowLeft className="h-5 w-5 shrink-0" />,
    },
  ];

  useEffect(() => {
    const historyKey = `search_history_${user?.id || "dev"}`;

    const loadHistory = () => {
      const raw = JSON.parse(localStorage.getItem(historyKey) || "[]");

      const safeHistory: StoredConversation[] = Array.isArray(raw)
        ? raw.filter(
            (item): item is StoredConversation =>
              item &&
              typeof item === "object" &&
              typeof item.id === "string" &&
              typeof item.query === "string" &&
              typeof item.date === "string" &&
              typeof item.sessionId === "string"
          )
        : [];

      setHistory(safeHistory);
    };

    loadHistory();
    window.addEventListener("historyUpdated", loadHistory);

    return () => {
      window.removeEventListener("historyUpdated", loadHistory);
    };
  }, [user]);

  return (
    <Sidebar open={open} setOpen={setOpen}>
      <SidebarBody className="justify-between gap-10">
        <div className="flex flex-1 flex-col overflow-x-hidden overflow-y-auto">
          {open ? <Wordmark /> : <LogoIcon />}

          <div className="flex flex-1 flex-col justify-between">
            <div className="mt-8 flex flex-col gap-2">
              {links_top.map((link) => (
                <SidebarLink key={link.label} link={link} />
              ))}

              {history.length > 0 && (
                <div className="mt-6 flex flex-col gap-1">
                  <div className="flex items-center gap-2 px-2 text-sm text-muted-foreground">
                    <IconHistory className="h-4 w-4" />
                    History
                  </div>

                  {history.map((item, i) => {
                    const query = typeof item?.query === "string" ? item.query : "";
                    const id = typeof item?.id === "string" ? item.id : `${i}`;

                    if (!query) return null;

                    return (
                      <button
                        key={id}
                        onClick={() =>
                          navigate(
                            `/search?conversation=${encodeURIComponent(
                              id
                            )}&q=${encodeURIComponent(query)}`
                          )
                        }
                        className="truncate rounded px-2 py-1 text-left text-sm hover:bg-muted"
                        title={query}
                      >
                        {query.length > 40 ? `${query.slice(0, 40)}...` : query}
                      </button>
                    );
                  })}
                </div>
              )}
            </div>

            <div className="mt-8 flex flex-col gap-2">
              {links_bottom.map((link) => (
                <SidebarLink key={link.label} link={link} />
              ))}
            </div>
          </div>
        </div>
      </SidebarBody>
    </Sidebar>
  );
}

export const Wordmark = () => {
  return (
    <Link
      to="/search"
      className="relative z-20 flex py-1 text-sm font-normal text-black dark:text-white"
    >
      <img src={CityAgentWordmark} alt="CityAgent Wordmark" className="h-8 w-auto" />
    </Link>
  );
};

export const LogoIcon = () => {
  return (
    <Link
      to="/search"
      className="relative z-20 flex py-1 text-sm font-normal text-black dark:text-white"
    >
      <img src={CityAgentLogoIcon} alt="CityAgent Logo" className="h-8 w-auto" />
    </Link>
  );
};