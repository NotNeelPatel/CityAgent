"use client";
import React, { useState } from "react";
import { Sidebar, SidebarBody, SidebarLink } from "@/components/ui/sidebar";
import { Button } from "@/components/ui/button";
import {
  IconArrowLeft,
  IconPlus,
  IconSunMoon,
  IconHistory,
  IconFileUpload,
} from "@tabler/icons-react";
import CityAgentWordmark from "@/assets/cityagent_wordmark.svg";
import CityAgentLogoIcon from "@/assets/cityagent_logo.svg";
import { useAuth } from "@/context/AuthContext";


export function CityAgentSidebar() {
  const [open, setOpen] = useState(false);
  const { signOut } = useAuth();

  const links_top = [
    {
      label: "New Search",
      href: "/search",
      icon: (
        <IconPlus className="h-5 w-5 shrink-0 " />
      ),
    },
    {
      label: "History",
      href: "#",
      icon: (
        <IconHistory className="h-5 w-5 shrink-0 " />
      ),
    },
  ];

  const links_bottom = [
    {
      label: "Dark/Light Mode",
      href: "#",
      icon: (
        <IconSunMoon className="h-5 w-5 shrink-0 " />
      ),
    },
    {
      label: "Upload",
      href: "#",
      icon: (
        <IconFileUpload className="h-5 w-5 shrink-0 " />
      ),
    },
    {
      label: "Sign Out",
      onClick: () => signOut(),
      icon: (
        <IconArrowLeft className="h-5 w-5 shrink-0 " />
      ),
    },
  ];



  return (
    <Sidebar open={open} setOpen={setOpen}>
      <SidebarBody className="justify-between gap-10">
        <div className="flex flex-1 flex-col overflow-x-hidden overflow-y-auto">
          {open ? <Wordmark /> : <LogoIcon />}
          <div className="flex flex-col flex-1 justify-between">
            <div className="mt-8 flex flex-col gap-2">
              {links_top.map((link, idx) => (
                <SidebarLink key={idx} link={link} />
              ))}
            </div>

            <div className="mt-8 flex flex-col gap-2">
              {links_bottom.map((link, idx) => (
                <SidebarLink key={idx} link={link} />
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
    <a
      href="#"
      className=" h-8! relative z-20 flex space-x-2 py-1 text-sm font-normal text-black"
    >
      <img src={CityAgentWordmark} alt="CityAgent Wordmark" className="h-8! w-auto" />
    </a>
  );
};
export const LogoIcon = () => {
  return (
    <a
      href="#"
      className=" h-8 relative z-20 flex space-x-2 py-1 text-sm font-normal text-black"
    >
      <img src={CityAgentLogoIcon} alt="CityAgent Logo" className="h-8!" />
    </a>
  );
};