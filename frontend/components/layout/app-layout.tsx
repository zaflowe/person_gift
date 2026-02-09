"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect } from "react";
import { cn, API_BASE_URL } from "@/lib/utils";
import { LayoutDashboard, CheckSquare, Folder, Shield, Settings, LogOut, Calendar } from "lucide-react";
import { useAuth } from "@/lib/auth-context";

const navigation = [
    { name: "仪表盘", href: "/dashboard", icon: LayoutDashboard },
    { name: "日程", href: "/schedule", icon: Calendar },
    { name: "任务", href: "/tasks", icon: CheckSquare },
    { name: "项目", href: "/projects", icon: Folder },
    { name: "设置", href: "/settings", icon: Settings },
];

export function AppLayout({ children }: { children: React.ReactNode }) {
    const pathname = usePathname();
    const { user, logout } = useAuth();

    // Check for daily reminder on mount/login
    useEffect(() => {
        if (user) {
            const checkReminderAndSystemTasks = async () => {
                const token = localStorage.getItem("token") || localStorage.getItem("auth_token");
                if (!token) return;
                try {
                    // 1. Check Daily Reminder
                    await fetch(`${API_BASE_URL}/conversation/check-reminder`, {
                        method: "POST",
                        headers: { Authorization: `Bearer ${token}` }
                    });

                    // 2. Check Weekly System Tasks (Global Trigger)
                    await fetch(`${API_BASE_URL}/system-tasks/weekly-check`, {
                        method: "POST",
                        headers: { Authorization: `Bearer ${token}` }
                    });
                } catch (e) {
                    console.error("Global checks failed", e);
                }
            };
            checkReminderAndSystemTasks();
        }
    }, [user]);

    return (
        <div className="min-h-screen bg-background">
            {/* Desktop Sidebar */}
            <aside className="hidden md:fixed md:inset-y-0 md:flex md:w-64 md:flex-col border-r border-[var(--border)] bg-[var(--surface)]">
                <div className="flex flex-col flex-1">
                    {/* Logo */}
                    <div className="flex items-center h-16 px-6 border-b border-[var(--border)]">
                        <div className="w-8 h-8 rounded-lg bg-[var(--primary)] flex items-center justify-center mr-3 shadow-lg shadow-[var(--primary)]/20">
                            <span className="text-white font-bold text-lg">P</span>
                        </div>
                        <h1 className="text-[16px] font-bold tracking-tight text-[var(--text)]">个人主权系统</h1>
                    </div>

                    {/* Navigation */}
                    <nav className="flex-1 px-4 py-6 space-y-1.5">
                        {navigation.map((item) => {
                            const Icon = item.icon;
                            const isActive = pathname.startsWith(item.href);
                            return (
                                <Link
                                    key={item.href}
                                    href={item.href}
                                    className={cn(
                                        "group flex items-center gap-3 px-3 py-2.5 text-[14px] font-medium rounded-[var(--radius-md)] transition-all duration-200 relative overflow-hidden",
                                        isActive
                                            ? "text-[var(--primary)] bg-[var(--primary-bg)]"
                                            : "text-[var(--muted)] hover:text-[var(--text)] hover:bg-[var(--surface-hover)]"
                                    )}
                                >
                                    {isActive && (
                                        <div className="absolute left-0 top-1.5 bottom-1.5 w-[3px] rounded-r-full bg-[var(--primary)]" />
                                    )}
                                    <Icon className={cn("w-[18px] h-[18px] transition-colors", isActive ? "text-[var(--primary)]" : "text-[var(--muted)] group-hover:text-[var(--text)]")} />
                                    {item.name}
                                </Link>
                            );
                        })}
                    </nav>

                    {/* User Info */}
                    <div className="border-t border-[var(--border)] p-4 m-4 mt-auto rounded-[var(--radius)] bg-[var(--surface-hover)]">
                        <div className="flex items-center justify-between">
                            <div className="min-w-0 flex-1">
                                <p className="text-[14px] font-medium truncate text-[var(--text)]">{user?.username}</p>
                                <div className="flex items-center mt-1">
                                    <div className="w-2 h-2 rounded-full bg-[var(--success)] mr-2 animate-pulse"></div>
                                    <p className="text-[11px] text-[var(--muted)] font-mono">ONLINE</p>
                                </div>
                            </div>
                            <button
                                onClick={logout}
                                className="ml-2 p-2 rounded-full text-[var(--muted)] hover:text-[var(--danger)] hover:bg-[var(--danger-bg)] transition-colors"
                                title="退出登录"
                            >
                                <LogOut className="w-4 h-4" />
                            </button>
                        </div>
                    </div>
                </div>
            </aside>

            {/* Mobile Bottom Nav */}
            <nav className="md:hidden fixed bottom-0 inset-x-0 bg-card border-t border-border z-40">
                <div className="flex items-center justify-around h-16 px-2">
                    {navigation.slice(0, 4).map((item) => {
                        const Icon = item.icon;
                        const isActive = pathname.startsWith(item.href);
                        return (
                            <Link
                                key={item.href}
                                href={item.href}
                                className={cn(
                                    "flex flex-col items-center justify-center min-w-0 flex-1 gap-1 py-2 rounded-sm transition-colors",
                                    isActive
                                        ? "text-foreground"
                                        : "text-muted-foreground"
                                )}
                            >
                                <Icon className="w-5 h-5" />
                                <span className="text-xs font-medium">{item.name}</span>
                            </Link>
                        );
                    })}
                </div>
            </nav>

            {/* Main Content */}
            <main className="md:pl-64 pb-20 md:pb-0">
                {children}
            </main>
        </div>
    );
}
