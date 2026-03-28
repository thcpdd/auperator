"use client";

import {
  MessageSquare,
  Settings,
  Activity,
  ScrollText,
  Wrench,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";

export type ViewType = "chat" | "config" | "status" | "logs";

interface SidebarProps {
  currentView: ViewType;
  onViewChange: (view: ViewType) => void;
  className?: string;
}

const navItems = [
  { id: "chat" as ViewType, label: "对话", icon: MessageSquare },
  { id: "config" as ViewType, label: "配置", icon: Settings },
  { id: "status" as ViewType, label: "状态", icon: Activity },
  { id: "logs" as ViewType, label: "日志", icon: ScrollText },
];

export function Sidebar({
  currentView,
  onViewChange,
  className,
}: SidebarProps) {
  return (
    <div
      className={cn(
        "flex flex-col border-r bg-background",
        className
      )}
    >
      {/* Navigation */}
      <ScrollArea className="flex-1 px-3 py-2">
        <nav className="space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentView === item.id;

            return (
              <button
                key={item.id}
                onClick={() => onViewChange(item.id)}
                className={cn(
                  "flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                )}
              >
                <Icon className="h-4 w-4" />
                {item.label}
              </button>
            );
          })}
        </nav>
      </ScrollArea>

      {/* Footer - Tools */}
      <div className="p-4 border-t">
        <Button variant="outline" className="w-full justify-start" size="sm">
          <Wrench className="mr-2 h-4 w-4" />
          工具管理
        </Button>
      </div>
    </div>
  );
}
