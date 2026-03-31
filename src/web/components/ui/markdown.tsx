"use client";

import ReactMarkdown from "react-markdown";
import rehypeHighlight from "rehype-highlight";
import remarkGfm from "remark-gfm";
import { cn } from "@/lib/utils";
import "highlight.js/styles/github.css";

interface MarkdownProps {
  content: string;
  className?: string;
}

export function Markdown({ content, className }: MarkdownProps) {
  return (
    <div className={cn("prose prose-sm max-w-none dark:prose-invert leading-loose", className)}>
      <style jsx global>{`
        .prose pre {
          overflow-x: auto;
          white-space: pre;
        }
        .prose code {
          word-break: break-word;
        }
        .prose pre code {
          word-break: normal;
        }
        /* Ensure lists are properly displayed */
        .prose ul {
          list-style-type: disc;
          padding-left: 1.5em;
          margin-top: 0.5em;
          margin-bottom: 0.5em;
        }
        .prose ol {
          list-style-type: decimal;
          padding-left: 1.5em;
          margin-top: 0.5em;
          margin-bottom: 0.5em;
        }
        .prose li {
          margin-top: 0.25em;
          margin-bottom: 0.25em;
        }
        /* Link styles */
        .prose a {
          color: oklch(0.65 0.18 255) !important;
          text-decoration-color: oklch(0.65 0.18 255 / 0.3) !important;
          transition: all 0.2s ease !important;
        }
        .prose a:hover {
          color: oklch(0.6 0.18 255) !important;
          text-decoration-color: oklch(0.65 0.18 255) !important;
        }
        /* Table styles with borders - using !important to override prose defaults */
        .prose table {
          border-collapse: collapse !important;
          width: 100% !important;
          margin-top: 1em !important;
          margin-bottom: 1em !important;
          border: 1px solid #e5e7eb !important;
        }
        .prose thead {
          border-bottom: 1px solid #d1d5db !important;
        }
        .prose tbody tr {
          border-bottom: 1px solid #e5e7eb !important;
        }
        .prose tbody tr:last-child {
          border-bottom: none !important;
        }
        .prose th,
        .prose td {
          border: 1px solid #e5e7eb !important;
          padding: 0.5em !important;
        }
        .prose th {
          background-color: #f9fafb !important;
          font-weight: 600 !important;
        }
        .prose td {
          background-color: transparent !important;
        }
        /* Dark mode support */
        .dark .prose table {
          border-color: #374151 !important;
        }
        .dark .prose thead {
          border-bottom-color: #4b5563 !important;
        }
        .dark .prose tbody tr {
          border-bottom-color: #374151 !important;
        }
        .dark .prose th,
        .dark .prose td {
          border-color: #374151 !important;
        }
        .dark .prose th {
          background-color: #1f2937 !important;
        }
      `}</style>
      <ReactMarkdown rehypePlugins={[rehypeHighlight]} remarkPlugins={[remarkGfm]}>
        {content}
      </ReactMarkdown>
    </div>
  );
}
