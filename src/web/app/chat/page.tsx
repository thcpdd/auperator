"use client";

import { useSearchParams, useRouter } from "next/navigation";
import { ChatView } from "@/components/views/ChatView";
import { useMemo, Suspense } from "react";

function ChatPageContent() {
  const searchParams = useSearchParams();
  const router = useRouter();

  // URL 是唯一的源，直接从 URL 读取
  const threadId = useMemo(() => searchParams.get("threadId") || undefined, [searchParams]);

  const handleThreadIdChange = (newThreadId: string | undefined) => {
    // 只更新 URL，不需要 state
    const params = new URLSearchParams();
    if (newThreadId) {
      params.set("threadId", newThreadId);
    }
    router.push(`/chat?${params.toString()}`, { scroll: false });
  };

  return <ChatView initialThreadId={threadId} onThreadIdChange={handleThreadIdChange} />;
}

export default function ChatPage() {
  return (
    <Suspense fallback={<div className="flex items-center justify-center h-screen">Loading...</div>}>
      <ChatPageContent />
    </Suspense>
  );
}

