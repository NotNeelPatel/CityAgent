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
import { supabase } from "@/lib/client";

type StoredConversation = {
  id: string;
  query: string;
  date: string;
};

export function CityAgentSidebar() {
  const [open, setOpen] = useState(false);
  const { signOut, role, user } = useAuth();
  const { theme, setTheme } = useTheme();
  const [history, setHistory] = useState<StoredConversation[]>([]);

  const isDark =
    theme === "dark" ||
    (theme === "system" &&
      window.matchMedia?.("(prefers-color-scheme: dark)").matches);

  const toggleTheme = () => {
    setTheme(isDark ? "light" : "dark");
  };

  const linksTop: Links[] = [
    {
      kind: "link",
      label: "New Search",
      href: "/search",
      icon: <IconPlus className="h-5 w-5 shrink-0" />,
    },
  ];

  const linksBottom: Links[] = [
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
    const loadHistory = async () => {
      if (!user?.id) {
        setHistory([]);
        return;
      }

      const { data, error } = await supabase
        .from("conversations")
        .select("id, query, created_at")
        .eq("user_id", user.id)
        .order("created_at", { ascending: false })
        .limit(20);

      if (error) {
        console.error("Error loading conversation history:", error);
        setHistory([]);
        return;
      }

      const mapped: StoredConversation[] = (data ?? []).map((item) => ({
        id: item.id,
        query: item.query,
        date: item.created_at,
      }));

      setHistory(mapped);
    };

    loadHistory();
  }, [user]);

  return (
    <Sidebar open={open} setOpen={setOpen}>
      <SidebarBody className="justify-between gap-10">
        <div className="flex flex-1 flex-col overflow-x-hidden overflow-y-auto">
          {open ? <Wordmark /> : <LogoIcon />}

          <div className="flex flex-1 flex-col justify-between">
            <div className="mt-8 flex flex-col gap-2">
              {linksTop.map((link) => (
                <SidebarLink key={link.label} link={link} />
              ))}

              {history.length > 0 && (
                <div className="mt-6 flex flex-col gap-1">
                  <SidebarLink
                    link={{
                      kind: "action",
                      label: "History",
                      onClick: () => {},
                      icon: <IconHistory className="h-5 w-5 shrink-0" />,
                    }}
                  />

                  {open &&
                    history.map((item) => {
                      const shortQuery =
                        item.query.length > 40
                          ? `${item.query.slice(0, 40)}...`
                          : item.query;

                      return (
                        <Link
                          key={item.id}
                          to={`/search?conversation=${encodeURIComponent(item.id)}`}
                          className="block truncate rounded px-2 py-1 text-sm hover:bg-muted"
                          title={item.query}
                        >
                          {shortQuery}
                        </Link>
                      );
                    })}
                </div>
              )}
            </div>

            <div className="mt-8 flex flex-col gap-2">
              {linksBottom.map((link) => (
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