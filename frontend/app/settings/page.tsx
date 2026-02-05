"use client";

import { RequireAuth } from "@/lib/auth-context";
import { AppLayout } from "@/components/layout/app-layout";
import { useAuth } from "@/lib/auth-context";
import { API_BASE_URL } from "@/lib/utils";
import { Shield, Server, User as UserIcon } from "lucide-react";

export default function SettingsPage() {
    return (
        <RequireAuth>
            <AppLayout>
                <SettingsContent />
            </AppLayout>
        </RequireAuth>
    );
}

function SettingsContent() {
    const { user } = useAuth();

    return (
        <div className="p-6 max-w-4xl mx-auto space-y-8">
            <div>
                <h1 className="text-2xl font-bold">系统设置</h1>
                <p className="text-muted-foreground">管理您的个人主权系统配置</p>
            </div>

            {/* User Profile */}
            <div className="bg-card border border-border rounded-lg p-6">
                <div className="flex items-center gap-4 mb-6">
                    <div className="p-3 bg-primary/10 rounded-full">
                        <UserIcon className="w-6 h-6 text-primary" />
                    </div>
                    <div>
                        <h2 className="text-lg font-semibold">当前身份</h2>
                        <p className="text-sm text-muted-foreground">正在使用的数字身份</p>
                    </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="space-y-1">
                        <label className="text-xs font-medium text-muted-foreground uppercase">用户名</label>
                        <p className="font-mono text-sm">{user?.username || "Unknown"}</p>
                    </div>
                    <div className="space-y-1">
                        <label className="text-xs font-medium text-muted-foreground uppercase">ID</label>
                        <p className="font-mono text-sm">{user?.id || "-"}</p>
                    </div>
                    <div className="space-y-1">
                        <label className="text-xs font-medium text-muted-foreground uppercase">角色</label>
                        <div className="inline-flex items-center px-2 py-1 rounded-full bg-success/10 text-success text-xs font-medium">
                            <Shield className="w-3 h-3 mr-1" />
                            Super Admin
                        </div>
                    </div>
                </div>
            </div>

            {/* System Status */}
            <div className="bg-card border border-border rounded-lg p-6">
                <div className="flex items-center gap-4 mb-6">
                    <div className="p-3 bg-info/10 rounded-full">
                        <Server className="w-6 h-6 text-info" />
                    </div>
                    <div>
                        <h2 className="text-lg font-semibold">系统状态</h2>
                        <p className="text-sm text-muted-foreground">连接与环境诊断</p>
                    </div>
                </div>

                <div className="space-y-4">
                    <div className="flex items-center justify-between p-3 bg-muted/50 rounded-md border border-border">
                        <div className="flex items-center gap-3">
                            <div className="w-2 h-2 rounded-full bg-success animate-pulse" />
                            <span className="text-sm font-medium">后端连接 (Proxy Mode)</span>
                        </div>
                        <span className="text-xs font-mono text-muted-foreground">Active</span>
                    </div>

                    <div className="flex items-center justify-between p-3 bg-muted/50 rounded-md border border-border">
                        <div className="flex items-center gap-3">
                            <div className="w-2 h-2 rounded-full bg-success" />
                            <span className="text-sm font-medium">API Base URL</span>
                        </div>
                        <span className="text-xs font-mono text-muted-foreground">Relative (Next.js Rewrites)</span>
                    </div>
                </div>
            </div>
        </div>
    );
}
