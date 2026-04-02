"use client";

import { useState } from "react";
import { Header } from "./Header";
import { Sidebar, ViewType } from "./Sidebar";
import { cn } from "@/lib/utils";
import { ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { ChevronLeft, ChevronRight } from "lucide-react";

interface MainLayoutProps {
  children: ReactNode | ((view: ViewType) => ReactNode);
  defaultView?: ViewType;
  onViewChange?: (view: ViewType) => void;
}

export function MainLayout({ children, defaultView = "chat", onViewChange }: MainLayoutProps) {
  const [currentView, setCurrentView] = useState<ViewType>(defaultView);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

  const handleViewChange = (view: ViewType) => {
    setCurrentView(view);
    setMobileMenuOpen(false);
    onViewChange?.(view);
  };

  return (
    <div className="flex h-screen flex-col overflow-hidden">
      <Header
        currentView={currentView}
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
            {typeof children === "function"
              ? (children as (view: ViewType) => ReactNode)(currentView)
              : children}
          </div>
        </main>
      </div>
    </div>
  );
}
