import { NextRequest } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(request: NextRequest) {
  const apiUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:7000";
  let controller: AbortController | null = new AbortController();

  try {
    // Parse request body
    const body = await request.json();
    const thread_id = body.thread_id;

    console.log("[API Route] SSE 连接请求，thread_id:", thread_id);

    // Connect to backend SSE
    const response = await fetch(`${apiUrl}/events/web-ui`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
      },
      body: JSON.stringify({ thread_id }),
      signal: controller.signal,
    });

    if (!response.ok) {
      return new Response(`SSE connection failed: ${response.status}`, {
        status: response.status,
      });
    }

    // Create a readable stream from the response body
    const reader = response.body?.getReader();
    if (!reader) {
      return new Response("Response body is null", { status: 500 });
    }

    console.log("[API Route] 开始转发 SSE 流");

    // Create a TransformStream (if needed) or just pipe
    const stream = new ReadableStream({
      async start(controller) {
        const decoder = new TextDecoder();

        try {
          while (true) {
            const { done, value } = await reader.read();

            if (done) {
              console.log("[API Route] 后端流结束");
              controller.close();
              break;
            }

            // Forward chunks directly to the client
            controller.enqueue(value);
          }
        } catch (error) {
          const errorName = error instanceof Error ? error.name : "Unknown";
          console.log(`[API Route] 流被中断: ${errorName}`);

          // Don't call controller.error() if already closed
          try {
            controller.close();
          } catch (e) {
            // Ignore already closed errors
          }
        } finally {
          reader.releaseLock();
          console.log("[API Route] Reader released");
        }
      },

      cancel() {
        console.log("[API Route] 客户端断开连接，取消后端请求");
        if (controller) {
          controller.abort();
          controller = null;
        }
      },
    });

    // Setup request abortion when client disconnects
    request.signal.addEventListener("abort", () => {
      console.log("[API Route] 检测到客户端断开");
      if (controller) {
        controller.abort();
        controller = null;
      }
    });

    return new Response(stream, {
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
      },
    });
  } catch (error) {
    console.error("[API Route] Error:", error);
    return new Response(`Error: ${error}`, { status: 500 });
  }
}
