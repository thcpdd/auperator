"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Activity } from "lucide-react";

export function StatusView() {
  return (
    <div className="flex h-full items-center justify-center p-8">
      <Card className="max-w-md w-full">
        <CardHeader>
          <div className="flex items-center gap-2">
            <Activity className="h-5 w-5 text-muted-foreground" />
            <CardTitle>系统状态</CardTitle>
          </div>
          <CardDescription>
            系统状态监控 - 开发中
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            这里将显示系统运行状态：
          </p>
          <ul className="mt-4 space-y-2 text-sm text-muted-foreground">
            <li>• Agent Worker 状态</li>
            <li>• Event Center 状态</li>
            <li>• Redis 连接状态</li>
            <li>• 数据库连接状态</li>
            <li>• 资源使用情况</li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
