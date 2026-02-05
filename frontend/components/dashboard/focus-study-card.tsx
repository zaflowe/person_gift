"use client";

import { AppCard } from "@/components/ui/app-card";
import { Clock, Play } from "lucide-react";
import Link from "next/link";
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from "recharts";
import { getProjectColorHex } from "@/lib/project-colors";
import useSWR from "swr";
import { fetcher } from "@/lib/utils";
import { Project } from "@/types";

interface FocusStudyCardProps {
    todaySec: number;
    weekSec: number;
    distribution: Array<{ name: string; value: number; color?: string; project_id?: string }>;
}

export function FocusStudyCard({ todaySec, weekSec, distribution }: FocusStudyCardProps) {
    const todayMin = Math.floor(todaySec / 60);
    const weekMin = Math.floor(weekSec / 60);

    const { data: projects } = useSWR<Project[]>("/api/projects", fetcher);

    // 1. Unified Data Source: Calculate total from distribution
    // Ensure we handle potential empty or malformed data gracefully
    const validDistribution = distribution || [];

    // Use raw seconds for precision
    const calculatedTotalSeconds = validDistribution.reduce((acc, curr) => acc + (curr.value || 0), 0);

    // Use calculated total for display to ensure consistency
    const displayTotalSeconds = calculatedTotalSeconds;
    const hasData = displayTotalSeconds > 0;

    // Calculate percentages and prepare chart data with colors
    const chartData = validDistribution.map(entry => {
        let isStrategic = false;
        let strategicIndex = -1;
        let customColor = undefined;

        if (entry.project_id && projects) {
            const project = projects.find(p => p.id === entry.project_id);
            if (project) {
                // Check strategic status from project list, or use logic if needed
                // The project object from API has is_strategic
                const activeProjects = projects.filter(p => p.status !== 'SUCCESS' && p.status !== 'FAILURE');
                const strategicList = activeProjects.slice(0, 3);

                isStrategic = strategicList.some(sp => sp.id === entry.project_id);
                strategicIndex = strategicList.findIndex(sp => sp.id === entry.project_id);
                customColor = project.color;
            }
        }

        const colorKey = entry.project_id || entry.name;
        // Use updated color logic with custom color support
        const fill = getProjectColorHex(colorKey, isStrategic, strategicIndex, customColor);

        return {
            ...entry,
            fill,
            // 2. Correct Percentage: (value / total) * 100
            percentage: displayTotalSeconds > 0 ? Math.round((entry.value / displayTotalSeconds) * 100) : 0
        };
    }).sort((a, b) => b.value - a.value); // Sort for Top 1

    const topProject = chartData[0];

    // Empty State
    if (!hasData) {
        return (
            <AppCard className="flex flex-col gap-4 h-full" noPadding>
                <div className="p-5 flex items-center justify-between border-b border-sidebar-border/40">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-indigo-50 rounded-full text-indigo-600">
                            <Clock className="w-5 h-5" />
                        </div>
                        <div>
                            <p className="text-xs text-muted-foreground">专注学习</p>
                            <p className="text-xl font-bold font-mono">0s</p>
                        </div>
                    </div>
                </div>

                <div className="flex-1 flex flex-col items-center justify-center p-6 text-center space-y-4">
                    <div className="w-16 h-16 bg-slate-50 rounded-full flex items-center justify-center">
                        <Play className="w-6 h-6 text-slate-300 ml-1" />
                    </div>
                    <div className="space-y-1">
                        <p className="text-sm font-medium text-slate-700">本周还没开始专注</p>
                        <p className="text-xs text-slate-400">积跬步以至千里</p>
                    </div>
                    <Link href="/focus">
                        <button className="px-5 py-2 bg-primary text-primary-foreground rounded-full hover:bg-primary/90 transition text-sm font-medium shadow-sm shadow-primary/20">
                            开始专注
                        </button>
                    </Link>
                </div>
            </AppCard>
        );
    }

    return (
        <AppCard className="flex flex-col h-full" noPadding>
            {/* Header */}
            <div className="px-5 pt-5 pb-2 flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-indigo-50 rounded-full text-indigo-600">
                        <Clock className="w-5 h-5" />
                    </div>
                    <div>
                        <p className="text-xs text-muted-foreground">本周专注</p>
                        <div className="flex items-baseline gap-1">
                            <span className="text-2xl font-bold font-mono">{Math.floor(displayTotalSeconds / 3600)}</span>
                            <span className="text-xs text-muted-foreground">h</span>
                            <span className="text-2xl font-bold font-mono ml-1">{Math.floor((displayTotalSeconds % 3600) / 60)}</span>
                            <span className="text-xs text-muted-foreground">m</span>
                            <span className="text-2xl font-bold font-mono ml-1">{displayTotalSeconds % 60}</span>
                            <span className="text-xs text-muted-foreground">s</span>
                        </div>
                    </div>
                </div>

                <Link href="/focus">
                    <button className="w-8 h-8 flex items-center justify-center bg-slate-100 text-slate-600 rounded-full hover:bg-primary hover:text-white transition">
                        <Play className="w-3.5 h-3.5 ml-0.5" />
                    </button>
                </Link>
            </div>

            {/* Chart Area */}
            <div className="flex-1 min-h-[160px] relative mt-2 mb-4">
                {/* Center Text */}
                <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none z-10">
                    <div className="text-[10px] text-muted-foreground">Top 1</div>
                    <div className="text-xs font-bold text-slate-800 max-w-[80px] truncate text-center px-1">
                        {topProject ? topProject.name : '--'}
                    </div>
                    <div className="text-[10px] font-mono text-slate-500">
                        {topProject ? `${topProject.percentage}%` : '0%'}
                    </div>
                </div>

                <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                        <Pie
                            data={chartData}
                            cx="50%"
                            cy="50%"
                            innerRadius={60} // Adjusted sizing as requested
                            outerRadius={85}
                            paddingAngle={2} // Better breathing room
                            cornerRadius={4}
                            dataKey="value"
                            stroke="none"
                        >
                            {chartData.map((entry, index) => (
                                <Cell key={`cell-${index}`} fill={entry.fill} />
                            ))}
                        </Pie>
                        <Tooltip
                            wrapperStyle={{ outline: 'none', zIndex: 50 }} // FIX: Ensure tooltip is above interactions
                            contentStyle={{ backgroundColor: 'white', borderColor: '#e2e8f0', borderRadius: '8px', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                            itemStyle={{ color: '#1e293b', fontSize: '12px' }}
                            formatter={(value: any, name: any, props: any) => {
                                // Value is in seconds now. Format to m:s or just m
                                const m = Math.floor(value / 60);
                                const s = value % 60;
                                return [`${m}m ${s}s (${props.payload.percentage}%)`, props.payload.name];
                            }}
                        />
                    </PieChart>
                </ResponsiveContainer>
            </div>

            {/* Custom Legend */}
            <div className="px-4 pb-4 grid grid-cols-2 gap-x-2 gap-y-1 relative z-20">
                {chartData.slice(0, 4).map((item, i) => ( // Limit to top 4 for cleanliness
                    <div key={i} className="flex items-center gap-1.5 text-xs text-slate-600 mb-1" title={item.name}>
                        <div className="w-2 h-2 rounded-full flex-none" style={{ backgroundColor: item.fill }} />
                        <div className="flex-1 truncate max-w-[6rem]">
                            {item.name.length > 8 ? item.name.substring(0, 8) + '...' : item.name}
                        </div>
                        <div className="font-mono text-[10px] text-slate-400">{item.percentage}%</div>
                    </div>
                ))}
                {chartData.length > 4 && (
                    <div className="text-[10px] text-slate-400 pl-3.5 self-center">
                        +{chartData.length - 4}
                    </div>
                )}
            </div>
        </AppCard>
    );
}
