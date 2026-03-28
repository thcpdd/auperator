"use client";

import { MainLayout } from "@/components/layout/MainLayout";
import { ChatView } from "@/components/views/ChatView";
import { ConfigView } from "@/components/views/ConfigView";
import { StatusView } from "@/components/views/StatusView";
import { LogsView } from "@/components/views/LogsView";
import { ViewType } from "@/components/layout/Sidebar";

export default function Home() {
  return (
    <MainLayout>
      {(currentView: ViewType) => {
        switch (currentView) {
          case "chat":
            return <ChatView />;
          case "config":
            return <ConfigView />;
          case "status":
            return <StatusView />;
          case "logs":
            return <LogsView />;
          default:
            return <ChatView />;
        }
      }}
    </MainLayout>
  );
}
