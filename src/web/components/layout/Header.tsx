import { MessageSquare, Settings, Menu } from "lucide-react";
import { Button } from "@/components/ui/button";

interface HeaderProps {
  currentView?: string;
  onMenuClick?: () => void;
}

export function Header({ currentView = "chat", onMenuClick }: HeaderProps) {
  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="flex h-14 items-center px-4">
        {/* Mobile Menu Button */}
        <Button
          variant="ghost"
          size="icon"
          className="mr-2 lg:hidden"
          onClick={onMenuClick}
        >
          <Menu className="h-5 w-5" />
        </Button>

        {/* Logo and Title */}
        <div className="flex items-center gap-2 font-semibold">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <MessageSquare className="h-5 w-5" />
          </div>
          <span className="text-lg hidden sm:inline">Auperator</span>
        </div>

        {/* Spacer */}
        <div className="flex flex-1" />

        {/* Status Indicator */}
        <div className="flex items-center gap-2">
          <div className="hidden sm:flex items-center gap-1.5 rounded-full bg-green-50 px-3 py-1 text-sm text-green-700">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500" />
            </span>
            <span>运行中</span>
          </div>

          {/* Settings Button */}
          <Button variant="ghost" size="icon" className="ml-2">
            <Settings className="h-5 w-5" />
          </Button>
        </div>
      </div>
    </header>
  );
}
