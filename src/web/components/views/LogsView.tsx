"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollText } from "lucide-react";

export function LogsView() {
  return (
    <div className="flex h-full items-center justify-center p-8">
      <Card className="max-w-md w-full">
        <CardHeader>
          <div className="flex items-center gap-2">
            <ScrollText className="h-5 w-5 text-muted-foreground" />
            <CardTitle>系统日志</CardTitle>
          </div>
          <CardDescription>
            实时日志查看 - 开发中
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            这里将显示实时系统日志：
          </p>
          <ul className="mt-4 space-y-2 text-sm text-muted-foreground">
            <li>• 实时日志流</li>
            <li>• 日志级别过滤</li>
            <li>• 搜索功能</li>
            <li>• 自动滚动控制</li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
