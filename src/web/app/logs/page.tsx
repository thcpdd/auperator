"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { apiClient } from "@/lib/api";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  ScrollText,
  Trash2,
  Play,
  Search,
  Filter,
  AlertCircle,
  AlertTriangle,
  Info,
  Bug,
  Zap,
  Plug,
  Power,
} from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuCheckboxItem,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

// 日志级别类型
type LogLevel = "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL";

// 日志条目接口
interface LogEntry {
  id: string;
  timestamp: string;
  level: LogLevel;
  message: string;
  source?: string;
  containerId?: string;
  containerName?: string;
  stream?: "stdout" | "stderr";
}

// 从日志内容中提取日志级别
function extractLogLevel(logLine: string): LogLevel {
  const upperLine = logLine.toUpperCase();

  // 按优先级从高到低检查
  if (upperLine.includes("CRITICAL") || upperLine.includes("FATAL")) {
    return "CRITICAL";
  }
  if (upperLine.includes("ERROR")) {
    return "ERROR";
  }
  if (upperLine.includes("WARNING") || upperLine.includes("WARN")) {
    return "WARNING";
  }
  if (upperLine.includes("DEBUG")) {
    return "DEBUG";
  }

  // 默认为 INFO
  return "INFO";
}

// 将后端的 DockerLogEntry 转换为前端的 LogEntry
function convertDockerLogEntry(entry: {
  container_name: string;
  container_id: string;
  timestamp: string;
  log_line: string;
  stream: "stdout" | "stderr";
}, index: number): LogEntry {
  const level = extractLogLevel(entry.log_line);

  return {
    id: `log-${index}-${Date.now()}-${Math.random()}`,
    timestamp: entry.timestamp,
    level,
    message: entry.log_line,
    source: entry.container_name,
    containerId: entry.container_id,
    containerName: entry.container_name,
    stream: entry.stream,
  };
}

// 获取日志级别对应的图标
function getLogLevelIcon(level: LogLevel) {
  switch (level) {
    case "DEBUG":
      return <Bug className="h-3.5 w-3.5" />;
    case "INFO":
      return <Info className="h-3.5 w-3.5" />;
    case "WARNING":
      return <AlertTriangle className="h-3.5 w-3.5" />;
    case "ERROR":
      return <AlertCircle className="h-3.5 w-3.5" />;
    case "CRITICAL":
      return <Zap className="h-3.5 w-3.5" />;
  }
}

// 获取日志级别对应的颜色
function getLogLevelColor(level: LogLevel) {
  switch (level) {
    case "DEBUG":
      return "text-muted-foreground";
    case "INFO":
      return "text-blue-500";
    case "WARNING":
      return "text-yellow-500";
    case "ERROR":
      return "text-orange-500";
    case "CRITICAL":
      return "text-red-500";
  }
}


export default function LogsPage() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [filteredLogs, setFilteredLogs] = useState<LogEntry[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [since, setSince] = useState("1h");
  const [tail, setTail] = useState<string>("");
  const [selectedLevels, setSelectedLevels] = useState<Set<LogLevel>>(
    new Set(["ERROR", "CRITICAL"])
  );

  const scrollRef = useRef<HTMLDivElement>(null);
  const logCountRef = useRef(0);
  const cleanupConnectionRef = useRef<(() => void) | null>(null);

  // 过滤日志
  useEffect(() => {
    let filtered = logs;

    // 按级别过滤
    if (selectedLevels.size > 0) {
      filtered = filtered.filter((log) => selectedLevels.has(log.level));
    }

    // 按搜索关键词过滤
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (log) =>
          log.message.toLowerCase().includes(query) ||
          log.source?.toLowerCase().includes(query) ||
          log.containerName?.toLowerCase().includes(query)
      );
    }

    setFilteredLogs(filtered);
  }, [logs, selectedLevels, searchQuery]);

  // 连接日志流
  const connectLogs = useCallback(() => {
    if (cleanupConnectionRef.current) return;

    setIsConnected(true);
    setLogs([]); // 清空旧日志
    logCountRef.current = 0;

    const tailValue = tail ? parseInt(tail, 10) : null;

    cleanupConnectionRef.current = apiClient.connectDockerLogs(
      {
        since: since === "all" ? "" : since,
        tail: tailValue,
      },
      // onLog
      (logEntry) => {
        logCountRef.current += 1;
        const log = convertDockerLogEntry(logEntry, logCountRef.current);
        setLogs((prev) => [...prev.slice(-500), log]); // 保留最近500条
      },
      // onError
      (error) => {
        console.error("Docker logs connection error:", error);
        setIsConnected(false);
        cleanupConnectionRef.current = null;
      },
      // onComplete
      () => {
        setIsConnected(false);
        cleanupConnectionRef.current = null;
      }
    );
  }, [since, tail]);

  const disconnectLogs = useCallback(() => {
    if (cleanupConnectionRef.current) {
      cleanupConnectionRef.current();
      cleanupConnectionRef.current = null;
    }
    setIsConnected(false);
  }, []);

  // 切换日志级别过滤
  const toggleLevel = (level: LogLevel) => {
    setSelectedLevels((prev) => {
      const next = new Set(prev);
      if (next.has(level)) {
        next.delete(level);
      } else {
        next.add(level);
      }
      return next;
    });
  };

  // 清空日志
  const clearLogs = () => {
    setLogs([]);
    setFilteredLogs([]);
    logCountRef.current = 0;
  };

  // 切换连接状态
  const toggleConnection = () => {
    if (isConnected) {
      disconnectLogs();
    } else {
      connectLogs();
    }
  };

  // 组件卸载时清理
  useEffect(() => {
    return () => {
      if (cleanupConnectionRef.current) {
        cleanupConnectionRef.current();
      }
    };
  }, []);

  // 格式化时间戳
  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString("zh-CN", {
      hour12: false,
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      fractionalSecondDigits: 3,
    });
  };

  return (
    <div className="flex flex-col h-full bg-background">
      {/* 顶部工具栏 */}
      <div className="border-b bg-card px-6 py-4">
        <div className="flex items-center justify-between gap-4">
          {/* 左侧标题和状态 */}
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <ScrollText className="h-5 w-5 text-primary" />
              <h1 className="text-lg font-semibold">目标项目日志</h1>
            </div>

            {/* 连接状态指示器 */}
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-muted/50 text-xs">
              <div
                className={`h-2 w-2 rounded-full ${
                  isConnected ? "bg-primary animate-pulse" : "bg-muted-foreground"
                }`}
              />
              <span className="text-muted-foreground">
                {isConnected ? "已连接" : "未连接"}
              </span>
            </div>

            {/* 日志计数 */}
            <div className="text-xs text-muted-foreground">
              显示 {filteredLogs.length} / 接收 {logs.length} 条
            </div>
          </div>

          {/* 右侧控制按钮 */}
          <div className="flex items-center gap-2">
            {/* 连接/断开按钮 */}
            <Button
              variant={isConnected ? "destructive" : "default"}
              size="sm"
              onClick={toggleConnection}
              className="gap-1.5"
            >
              {isConnected ? (
                <>
                  <Power className="h-3.5 w-3.5 text-primary-foreground" />
                  <span className="text-primary-foreground">断开</span>
                </>
              ) : (
                <>
                  <Play className="h-3.5 w-3.5" />
                  连接
                </>
              )}
            </Button>

            {/* 清空按钮 */}
            <Button variant="outline" size="sm" onClick={clearLogs} className="gap-1.5">
              <Trash2 className="h-3.5 w-3.5" />
              清空
            </Button>

            {/* 级别过滤 */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="sm" className="gap-1.5">
                  <Filter className="h-3.5 w-3.5" />
                  级别
                  <span className="ml-0.5 px-1.5 py-0.5 rounded bg-primary/10 text-primary text-[10px]">
                    {selectedLevels.size}
                  </span>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-40">
                <DropdownMenuCheckboxItem
                  checked={selectedLevels.has("DEBUG")}
                  onCheckedChange={() => toggleLevel("DEBUG")}
                >
                  <div className="flex items-center gap-2">
                    <Bug className="h-3.5 w-3.5 text-muted-foreground" />
                    <span>DEBUG</span>
                  </div>
                </DropdownMenuCheckboxItem>
                <DropdownMenuCheckboxItem
                  checked={selectedLevels.has("INFO")}
                  onCheckedChange={() => toggleLevel("INFO")}
                >
                  <div className="flex items-center gap-2">
                    <Info className="h-3.5 w-3.5 text-blue-500" />
                    <span>INFO</span>
                  </div>
                </DropdownMenuCheckboxItem>
                <DropdownMenuCheckboxItem
                  checked={selectedLevels.has("WARNING")}
                  onCheckedChange={() => toggleLevel("WARNING")}
                >
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="h-3.5 w-3.5 text-yellow-500" />
                    <span>WARNING</span>
                  </div>
                </DropdownMenuCheckboxItem>
                <DropdownMenuCheckboxItem
                  checked={selectedLevels.has("ERROR")}
                  onCheckedChange={() => toggleLevel("ERROR")}
                >
                  <div className="flex items-center gap-2">
                    <AlertCircle className="h-3.5 w-3.5 text-orange-500" />
                    <span>ERROR</span>
                  </div>
                </DropdownMenuCheckboxItem>
                <DropdownMenuCheckboxItem
                  checked={selectedLevels.has("CRITICAL")}
                  onCheckedChange={() => toggleLevel("CRITICAL")}
                >
                  <div className="flex items-center gap-2">
                    <Zap className="h-3.5 w-3.5 text-red-500" />
                    <span>CRITICAL</span>
                  </div>
                </DropdownMenuCheckboxItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => setSelectedLevels(new Set(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]))}>
                  全选
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => setSelectedLevels(new Set())}>
                  清空选择
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>

        {/* 搜索栏和参数设置 */}
        <div className="mt-4 flex items-center gap-3">
          {/* 搜索框 */}
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="搜索日志内容、来源或容器名称..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10 h-9"
            />
          </div>

          {/* Since 参数 */}
          <div className="flex items-center gap-2">
            <label className="text-xs text-muted-foreground whitespace-nowrap">时间范围:</label>
            <Select value={since || "all"} onValueChange={(value) => setSince(value === "all" ? "" : value)}>
              <SelectTrigger className="h-9 w-[140px]">
                <SelectValue placeholder="选择时间范围" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部时间</SelectItem>
                <SelectItem value="5m">最近 5 分钟</SelectItem>
                <SelectItem value="15m">最近 15 分钟</SelectItem>
                <SelectItem value="30m">最近 30 分钟</SelectItem>
                <SelectItem value="1h">最近 1 小时</SelectItem>
                <SelectItem value="3h">最近 3 小时</SelectItem>
                <SelectItem value="6h">最近 6 小时</SelectItem>
                <SelectItem value="12h">最近 12 小时</SelectItem>
                <SelectItem value="24h">最近 24 小时</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Tail 参数 */}
          <div className="flex items-center gap-2">
            <label className="text-xs text-muted-foreground whitespace-nowrap">行数:</label>
            <Input
              type="number"
              placeholder="全部"
              value={tail}
              onChange={(e) => setTail(e.target.value)}
              className="h-9 w-24"
              min="1"
            />
          </div>
        </div>
      </div>

      {/* 日志内容区域 */}
      <div className="flex-1 relative overflow-hidden">
        {filteredLogs.length === 0 ? (
          // 空状态
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center space-y-4">
              {!isConnected ? (
                <>
                  <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-muted">
                    <Plug className="h-8 w-8 text-muted-foreground" />
                  </div>
                  <div className="space-y-2">
                    <p className="text-lg font-medium">未连接到日志流</p>
                    <p className="text-sm text-muted-foreground">
                      点击上方“连接”按钮开始接收实时日志
                    </p>
                  </div>
                </>
              ) : logs.length === 0 ? (
                <>
                  <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-muted">
                    <ScrollText className="h-8 w-8 text-muted-foreground" />
                  </div>
                  <div className="space-y-2">
                    <p className="text-lg font-medium">等待日志...</p>
                    <p className="text-sm text-muted-foreground">
                      已连接，正在等待日志数据
                    </p>
                  </div>
                </>
              ) : (
                <>
                  <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-muted">
                    <Search className="h-8 w-8 text-muted-foreground" />
                  </div>
                  <div className="space-y-2">
                    <p className="text-lg font-medium">没有匹配的日志</p>
                    <p className="text-sm text-muted-foreground">
                      尝试调整搜索条件或过滤器
                    </p>
                  </div>
                </>
              )}
            </div>
          </div>
        ) : (
          // 日志列表
          <div
            ref={scrollRef}
            className="h-full overflow-y-auto overflow-x-hidden"
          >
            <div className="p-4 space-y-0.5">
              {filteredLogs.map((log) => (
                <div
                  key={log.id}
                  className="px-4 py-2 hover:bg-muted/30 transition-colors rounded"
                >
                  <div className="flex items-center gap-3 text-sm">
                    {/* 时间戳 */}
                    <span className="text-xs text-muted-foreground font-mono shrink-0">
                      {formatTimestamp(log.timestamp)}
                    </span>

                    {/* 级别标识 */}
                    <span className={`shrink-0 ${getLogLevelColor(log.level)}`}>
                      {getLogLevelIcon(log.level)}
                    </span>

                    {/* 来源信息 */}
                    {log.source && (
                      <span className="text-xs text-muted-foreground shrink-0">
                        [{log.source}]
                      </span>
                    )}

                    {/* 日志内容 */}
                    <span className="font-mono flex-1 break-all">
                      {log.message}
                    </span>

                    {/* 容器信息 */}
                    {log.containerName && (
                      <span className="text-xs text-muted-foreground/60 shrink-0">
                        {log.containerName}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
