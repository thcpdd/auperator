import { NextRequest } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(request: NextRequest) {
  const apiUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:7000";
  let controller: AbortController | null = new AbortController();

  try {
    // Parse request body
    const body = await request.json();
    const { since, tail } = body;

    // Connect to backend SSE
    const response = await fetch(`${apiUrl}/events/docker-logs`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
      },
      body: JSON.stringify({
        since: since || "1h",
        tail: tail || null,
      }),
      signal: controller.signal,
    });

    if (!response.ok) {
      console.error("[API Route] Backend SSE connection failed:", response.status);
      return new Response(`SSE connection failed: ${response.status}`, {
        status: response.status,
      });
    }

    // Create a readable stream from the response body
    const reader = response.body?.getReader();
    if (!reader) {
      return new Response("Response body is null", { status: 500 });
    }

    // Create a TransformStream to forward the backend stream
    const stream = new ReadableStream({
      async start(controller) {
        try {
          while (true) {
            const { done, value } = await reader.read();

            if (done) {
              controller.close();
              break;
            }

            // Forward chunks directly to the client
            controller.enqueue(value);
          }
        } catch (error) {
          try {
            controller.close();
          } catch (e) {
            // Ignore already closed errors
          }
        } finally {
          reader.releaseLock();
        }
      },

      cancel() {
        if (controller) {
          controller.abort();
          controller = null;
        }
      },
    });

    // Setup request abortion when client disconnects
    request.signal.addEventListener("abort", () => {
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
    console.error("[API Route] Docker Logs Error:", error);
    return new Response(`Error: ${error}`, { status: 500 });
  }
}
