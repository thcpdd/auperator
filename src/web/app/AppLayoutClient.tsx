"use client";

import { useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { Header } from "@/components/layout/Header";
import { Sidebar, ViewType } from "@/components/layout/Sidebar";
import { cn } from "@/lib/utils";
import { ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { ChevronLeft, ChevronRight } from "lucide-react";

interface AppLayoutClientProps {
  children: ReactNode;
}

// Map paths to ViewType
function pathToView(pathname: string): ViewType {
  if (pathname === "/chat") return "chat";
  if (pathname === "/config") return "config";
  if (pathname === "/status") return "status";
  if (pathname === "/logs") return "logs";
  return "chat"; // default
}

export default function AppLayoutClient({ children }: AppLayoutClientProps) {
  const pathname = usePathname();
  const router = useRouter();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

  const currentView = pathToView(pathname);

  const handleViewChange = (view: ViewType) => {
    // Navigate to the corresponding route
    router.push(`/${view}`);
    setMobileMenuOpen(false);
  };

  return (
    <div className="flex h-screen flex-col overflow-hidden">
      <Header
        onMenuClick={() => setMobileMenuOpen(!mobileMenuOpen)}
      />

      <div className="flex flex-1 overflow-hidden relative">
        {/* Mobile Overlay */}
        {mobileMenuOpen && (
          <div
            className="fixed inset-0 z-40 bg-background/80 backdrop-blur-sm lg:hidden"
            onClick={() => setMobileMenuOpen(false)}
          />
        )}

        {/* Sidebar */}
        <aside
          className={cn(
            "absolute z-50 h-full transition-all duration-300 lg:relative lg:z-auto border-r bg-background",
            mobileMenuOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0",
            isSidebarCollapsed ? "lg:w-0 lg:overflow-hidden lg:border-none" : "lg:w-64",
            "w-64"
          )}
        >
          <Sidebar
            currentView={currentView}
            onViewChange={handleViewChange}
            className="h-full"
          />
        </aside>

        {/* Floating Toggle Button */}
        <Button
          variant="default"
          size="icon"
          onClick={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
          className={cn(
            "absolute bottom-4 left-4 z-[60] h-8 w-8 transition-all duration-300 shadow-md",
            isSidebarCollapsed ? "opacity-100" : "opacity-50 hover:opacity-100"
          )}
        >
          {isSidebarCollapsed ? (
            <ChevronRight className="h-4 w-4" />
          ) : (
            <ChevronLeft className="h-4 w-4" />
          )}
        </Button>

        {/* Main Content Area */}
        <main className="flex flex-1 overflow-hidden">
          <div className="flex h-full w-full flex-col">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
