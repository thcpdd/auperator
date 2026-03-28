"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Settings } from "lucide-react";

export function ConfigView() {
  return (
    <div className="flex h-full items-center justify-center p-8">
      <Card className="max-w-md w-full">
        <CardHeader>
          <div className="flex items-center gap-2">
            <Settings className="h-5 w-5 text-muted-foreground" />
            <CardTitle>配置管理</CardTitle>
          </div>
          <CardDescription>
            配置管理界面 - 开发中
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            这里将显示系统配置选项，包括：
          </p>
          <ul className="mt-4 space-y-2 text-sm text-muted-foreground">
            <li>• Redis 连接配置</li>
            <li>• OpenAI API 设置</li>
            <li>• Daytona Sandbox 配置</li>
            <li>• Langfuse 追踪设置</li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
