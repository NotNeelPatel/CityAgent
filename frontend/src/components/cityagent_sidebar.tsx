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
import { Link } from "react-router-dom";
import { useTheme } from "@/context/ThemeContext";

export function CityAgentSidebar() {
  const [open, setOpen] = useState(false);
  const { signOut, role } = useAuth();
  const { theme, setTheme } = useTheme(); 

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
      icon: isDark ? <IconSun className="h-5 w-5 shrink-0" /> : <IconMoon className="h-5 w-5 shrink-0" />,
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

  const [history, setHistory] = useState<{ query: string; date: string }[]>([]);

useEffect(() => {
  const loadHistory = () => {
    const stored = JSON.parse(localStorage.getItem("search_history") || "[]");
    setHistory(stored);
  };

  loadHistory(); 

  window.addEventListener("historyUpdated", loadHistory);

  return () => {
    window.removeEventListener("historyUpdated", loadHistory);
  };
}, []);

  return (
    <Sidebar open={open} setOpen={setOpen}>
      <SidebarBody className="justify-between gap-10">
        <div className="flex flex-1 flex-col overflow-x-hidden overflow-y-auto">
          {open ? <Wordmark /> : <LogoIcon />}

          <div className="flex flex-col flex-1 justify-between">
            <div className="mt-8 flex flex-col gap-2">

  {links_top.map((link) => (
    <SidebarLink key={link.label} link={link} />
  ))}

  {/* History Section */}
  {history.length > 0 && (
    <div className="mt-6 flex flex-col gap-1">
      <div className="flex items-center gap-2 text-sm text-muted-foreground px-2">
        <IconHistory className="h-4 w-4" />
        History
      </div>

      {history.map((item, i) => (
        <button
          key={i}
          onClick={() => window.location.href = `/search?q=${encodeURIComponent(item.query)}`}
          className="text-left text-sm truncate px-2 py-1 rounded hover:bg-muted"
        >
          {item.query.length > 40
            ? item.query.slice(0, 40) + "..."
            : item.query}
        </button>
      ))}
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
