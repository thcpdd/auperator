import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // 启用 standalone 输出模式（Docker 部署必需）
  output: 'standalone',

  async rewrites() {
    const apiUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:7000";

    return [
      {
        source: "/api/:path*",
        destination: `${apiUrl}/:path*`,
      },
    ];
  },
};

export default nextConfig;
