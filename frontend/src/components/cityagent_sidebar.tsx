import { useState } from "react";
import { Sidebar, SidebarBody, SidebarLink } from "@/components/ui/aceternity/sidebar";
import type { Links } from "@/components/ui/aceternity/sidebar";
import {
  IconArrowLeft,
  IconPlus,
  IconSunMoon,
  IconHistory,
  IconLayoutDashboard,
} from "@tabler/icons-react";
import CityAgentWordmark from "@/assets/cityagent_wordmark.svg";
import CityAgentLogoIcon from "@/assets/cityagent_logo.svg";
import { useAuth } from "@/context/AuthContext";
import { Link } from "react-router-dom";

export function CityAgentSidebar() {
  const [open, setOpen] = useState(false);
  const { signOut } = useAuth();

  const links_top: Links[] = [
    {
      kind: "link",
      label: "New Search",
      href: "/search",
      icon: <IconPlus className="h-5 w-5 shrink-0" />,
    },
    {
      kind: "link",
      disabled: true,
      label: "History",
      href: "/history", // TODO: implement the history view
      icon: <IconHistory className="h-5 w-5 shrink-0" />,
    },
  ];

  const links_bottom: Links[] = [
    {
      kind: "action",
      disabled: true,
      label: "Dark/Light Mode",
      onClick: () => {
        // TODO: hook into theme toggle
      },
      icon: <IconSunMoon className="h-5 w-5 shrink-0" />,
    },
    {
      kind: "link",
      label: "Dashboard",
      href: "/dashboard",
      icon: <IconLayoutDashboard className="h-5 w-5 shrink-0" />,
    },
    {
      kind: "action",
      label: "Sign Out",
      onClick: signOut,
      icon: <IconArrowLeft className="h-5 w-5 shrink-0" />,
    },
  ];

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
