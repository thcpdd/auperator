import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import AppLayoutClient from "./AppLayoutClient";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Auperator - AI 超级运维智能体",
  description: "基于 AI 的运维智能体，自动监控和修复系统问题",
  icons: {
    icon: "/favicon-r.png",
    apple: "/favicon-r.png",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <AppLayoutClient>{children}</AppLayoutClient>
      </body>
    </html>
  );
}