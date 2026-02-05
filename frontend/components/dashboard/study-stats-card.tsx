"use client";

import { AppCard } from "@/components/ui/app-card";
import { Play, Calendar, Zap } from "lucide-react";
import { useRouter } from "next/navigation";
import { cn } from "@/lib/utils";

interface StudyStatsCardProps {
    todaySec: number;
    weekSec: number;
}

export function StudyStatsCard({ todaySec, weekSec }: StudyStatsCardProps) {
    const router = useRouter();

    const formatTime = (sec: number) => {
        const h = Math.floor(sec / 3600);
        const m = Math.floor((sec % 3600) / 60);
        if (h > 0) return `${h}h ${m}m`;
        return `${m}m`;
    };

    return (
        <AppCard className="relative overflow-hidden group">
            <div className="p-6 flex flex-col md:flex-row items-center justify-between gap-6 h-full">

                {/* Left: Stats */}
                <div className="flex items-center gap-8 w-full md:w-auto">
                    <div className="space-y-1">
                        <div className="flex items-center text-xs text-muted-foreground gap-1">
                            <Zap className="w-3 h-3 text-primary" />
                            <span>今日专注</span>
                        </div>
                        <div className="text-2xl font-bold font-mono tracking-tight">
                            {formatTime(todaySec)}
                        </div>
                    </div>

                    <div className="w-px h-10 bg-border hidden md:block" />

                    <div className="space-y-1">
                        <div className="flex items-center text-xs text-muted-foreground gap-1">
                            <Calendar className="w-3 h-3 text-muted-foreground" />
                            <span>本周累计</span>
                        </div>
                        <div className="text-2xl font-bold font-mono tracking-tight text-muted-foreground">
                            {formatTime(weekSec)}
                        </div>
                    </div>
                </div>

                {/* Right: Action */}
                <button
                    onClick={() => router.push("/focus")}
                    className="w-full md:w-auto flex items-center justify-center gap-2 bg-primary text-primary-foreground px-6 py-3 rounded-full font-medium shadow-lg shadow-primary/20 hover:scale-105 transition-all active:scale-95 whitespace-nowrap"
                >
                    <Play className="w-4 h-4 fill-current" />
                    开始专注 (Start Focus)
                </button>
            </div>

            {/* Background Decoration */}
            <div className="absolute top-0 right-0 p-6 opacity-5 pointer-events-none">
                <Zap className="w-32 h-32" />
            </div>
        </AppCard>
    );
}
