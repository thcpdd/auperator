"use client";

import { useState, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { MainLayout } from "@/components/layout/MainLayout";
import { ChatView } from "@/components/views/ChatView";
import { ConfigView } from "@/components/views/ConfigView";
import { StatusView } from "@/components/views/StatusView";
import { LogsView } from "@/components/views/LogsView";
import { ViewType } from "@/components/layout/Sidebar";

export default function Home() {
  const searchParams = useSearchParams();
  const [currentView, setCurrentView] = useState<ViewType>("chat");
  const [activeThreadId, setActiveThreadId] = useState<string | undefined>(
    () => searchParams.get("threadId") || undefined
  );
  const [chatKey, setChatKey] = useState(0);

  // Update URL when activeThreadId or currentView changes
  useEffect(() => {
    const url = new URL(window.location.href);

    // Only show threadId in URL when on chat view
    if (currentView === "chat" && activeThreadId) {
      url.searchParams.set("threadId", activeThreadId);
    } else {
      url.searchParams.delete("threadId");
    }

    window.history.replaceState({}, "", url.toString());
  }, [activeThreadId, currentView]);

  // Handle view changes
  const handleViewChange = (view: ViewType) => {
    if (view !== currentView) {
      if (view === "chat") {
        // Switching back to chat - increment key to remount ChatView
        setChatKey(prev => prev + 1);
      }
      setCurrentView(view);
    }
  };

  return (
    <MainLayout onViewChange={handleViewChange}>
      {(view: ViewType) => {
        switch (view) {
          case "chat":
            return <ChatView
              key={chatKey}
              initialThreadId={activeThreadId}
              onThreadIdChange={setActiveThreadId}
            />;
          case "config":
            return <ConfigView />;
          case "status":
            return <StatusView />;
          case "logs":
            return <LogsView />;
          default:
            return <ChatView
              key={chatKey}
              initialThreadId={activeThreadId}
              onThreadIdChange={setActiveThreadId}
            />;
        }
      }}
    </MainLayout>
  );
}
