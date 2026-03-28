"use client";

import { useState } from "react";
import { Header } from "./Header";
import { Sidebar, ViewType } from "./Sidebar";
import { cn } from "@/lib/utils";
import { ReactNode } from "react";

interface MainLayoutProps {
  children: ReactNode | ((view: ViewType) => ReactNode);
  defaultView?: ViewType;
}

export function MainLayout({ children, defaultView = "chat" }: MainLayoutProps) {
  const [currentView, setCurrentView] = useState<ViewType>(defaultView);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

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
            "absolute z-50 h-full transition-transform duration-300 lg:relative lg:z-auto",
            mobileMenuOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0",
            "w-64"
          )}
        >
          <Sidebar
            currentView={currentView}
            onViewChange={(view) => {
              setCurrentView(view);
              setMobileMenuOpen(false);
            }}
            className="h-full"
          />
        </aside>

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
