import { Settings, Menu } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useState, useEffect } from "react";
import { apiClient } from "@/lib/api";

interface HeaderProps {
  onMenuClick?: () => void;
}

type HealthStatus = "healthy" | "error" | "loading";

export function Header({ onMenuClick }: HeaderProps) {
  const [healthStatus, setHealthStatus] = useState<HealthStatus>("loading");

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const data = await apiClient.checkHealth();
        if (data.status === "healthy") {
          setHealthStatus("healthy");
        } else {
          setHealthStatus("error");
        }
      } catch {
        setHealthStatus("error");
      }
    };

    // 立即检查一次
    checkHealth();

    // 每5秒检查一次
    const interval = setInterval(checkHealth, 5000);

    return () => clearInterval(interval);
  }, []);

  const getStatusConfig = () => {
    switch (healthStatus) {
      case "healthy":
        return {
          text: "运行中",
          bgColor: "bg-primary/10",
          textColor: "text-primary",
          dotColor: "bg-primary",
          pingColor: "bg-primary/50",
        };
      case "error":
        return {
          text: "连接断开",
          bgColor: "bg-destructive/10",
          textColor: "text-destructive",
          dotColor: "bg-destructive",
          pingColor: "",
        };
      case "loading":
        return {
          text: "连接中...",
          bgColor: "bg-muted",
          textColor: "text-muted-foreground",
          dotColor: "bg-muted-foreground",
          pingColor: "",
        };
    }
  };

  const statusConfig = getStatusConfig();
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
          <img src="/favicon.png" alt="Auperator" className="h-8 w-8 rounded-lg" />
          <span className="text-lg hidden sm:inline">Auperator</span>
        </div>

        {/* Spacer */}
        <div className="flex flex-1" />

        {/* Status Indicator */}
        <div className="flex items-center gap-2">
          <div className={`hidden sm:flex items-center gap-1.5 rounded-full ${statusConfig.bgColor} px-3 py-1 text-sm ${statusConfig.textColor}`}>
            <span className="relative flex h-2 w-2">
              {healthStatus === "healthy" && (
                <span className={`animate-ping absolute inline-flex h-full w-full rounded-full ${statusConfig.pingColor} opacity-75`} />
              )}
              <span className={`relative inline-flex rounded-full h-2 w-2 ${statusConfig.dotColor}`} />
            </span>
            <span>{statusConfig.text}</span>
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
