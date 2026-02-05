"use client";

import { useState, useMemo } from "react";
import { AppCard } from "@/components/ui/app-card";
import { Plus, Check, TrendingDown, TrendingUp, Minus } from "lucide-react";
import useSWR, { useSWRConfig } from "swr";
import { fetcher, apiPost } from "@/lib/utils";
import { ResponsiveContainer, LineChart, Line, YAxis, ReferenceLine, XAxis, Tooltip } from "recharts";
import {
    Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter
} from "@/components/ui/dialog";

const TARGET_WEIGHT = 85.0;
const TARGET_FAT = 18.0;

export function BodyMetricsCard() {
    const { mutate } = useSWRConfig();
    // Fetch ample history to calculate start/cumulative
    const { data: weightHistory } = useSWR<any[]>("/api/metrics/history?metric_type=weight&days=90", fetcher);
    const { data: fatHistory } = useSWR<any[]>("/api/metrics/history?metric_type=bodyfat&days=90", fetcher);

    const [isAdding, setIsAdding] = useState(false);

    // --- Data Processing ---
    const processMetric = (history: any[] | undefined, target: number) => {
        if (!history || history.length === 0) return {
            current: 0,
            start: 0,
            cumulative: 0,
            gap: 0,
            trendData: [],
            chart6Weeks: []
        };

        // Sort by date ascending (oldest -> newest) for processing
        const sorted = [...history].sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime());

        const current = sorted[sorted.length - 1].value;
        const start = sorted[0].value;
        const cumulative = current - start; // Negative means loss (good)
        const gap = current - target;

        // 4-Week Trend (Sparkline) - Last 4 points
        // If we have sparse data, we just take the last 4 available records
        const trendData = sorted.slice(-4).map(d => ({ value: d.value }));

        // 6-Week Chart (Small Multiples) - Last 6 weeks (by calendar week)
        // We need to bucket by week to check for "Missed" tasks
        // For simplicity: Create 6 slots for "Last 6 Weeks". 
        // Iterate backwards from Today.
        const chart6Weeks = [];
        const now = new Date();
        // Align to start of current week (Monday)
        const currentWeekStart = new Date(now);
        currentWeekStart.setDate(now.getDate() - now.getDay() + 1); // Monday
        currentWeekStart.setHours(0, 0, 0, 0);

        for (let i = 5; i >= 0; i--) {
            const weekStart = new Date(currentWeekStart);
            weekStart.setDate(weekStart.getDate() - (i * 7));
            const weekEnd = new Date(weekStart);
            weekEnd.setDate(weekEnd.getDate() + 7);

            // Find record in this week
            const record = sorted.find(d => {
                const date = new Date(d.created_at);
                return date >= weekStart && date < weekEnd;
            });

            chart6Weeks.push({
                weekIndex: i, // 0 is oldest (5 weeks ago), 5 is current
                weekLabel: `W${i}`,
                value: record ? record.value : null,
                hasData: !!record,
                isCurrentWeek: i === 0 // Actually query loop is reversed (5->0), so 0 is current... wait
            });
        }
        // Fix order: 5 weeks ago -> Today. 
        // Loop above i=5 is "5 weeks ago", i=0 is "Current". List is [5WeeksAgo, ..., Current]
        // But chart wants Left->Right time. so i=5 (oldest) -> i=0 (newest).
        // Let's re-do clearly.

        const weeksData = [];
        for (let i = 5; i >= 0; i--) { // 5 weeks ago to 0 (current)
            const specificDate = new Date();
            specificDate.setDate(now.getDate() - i * 7);
            // Find any record in close proximity (simple approximation for now)
            // Better: Match strict ISO week, but for UI smooth feel:
            // Find last record within [Date-3days, Date+4days]
            const targetTime = specificDate.getTime();
            const closest = sorted.find(d => Math.abs(new Date(d.created_at).getTime() - targetTime) < 3.5 * 24 * 3600 * 1000);

            weeksData.push({
                index: 5 - i,
                value: closest ? closest.value : null,
                hasData: !!closest
            });
        }

        return { current, start, cumulative, gap, trendData, chart6Weeks: weeksData };
    };

    const w = useMemo(() => processMetric(weightHistory, TARGET_WEIGHT), [weightHistory]);
    const f = useMemo(() => processMetric(fatHistory, TARGET_FAT), [fatHistory]);

    // Handle Task Creation
    const handleCreateTask = async (type: 'weight' | 'fat') => {
        try {
            const payload = type === 'weight'
                ? {
                    title: "【补充】体重记录",
                    description: "手动补充一次体重记录",
                    evidence_type: "text",
                    evidence_criteria: "请输入当前的体重数值(kg)",
                    tags: ["健康", "体重"]
                }
                : {
                    title: "【补充】身材记录",
                    description: "手动补充一次身材照片",
                    evidence_type: "image",
                    evidence_criteria: "请上传一张半身正面照",
                    tags: ["健康", "体脂"]
                };

            // Create task scheduled for NOW so it appears in Today's list
            await apiPost("/api/tasks", {
                ...payload,
                scheduled_time: new Date().toISOString(),
                duration: 15
            });

            setIsAdding(false);
            // Optionally trigger a global task refresh if possible, but user will see it in the list.
            // We can mutate the system notification or just let the user go to the task list.
        } catch (e) { console.error(e); }
    };

    // Component: Left Side Metric Block (Compact)
    const MetricBlock = ({ label, target, data, unit, colorClass }: any) => (
        <div className="flex flex-col gap-0.5 min-w-[100px] flex-1">
            {/* Label Row */}
            <div className="flex items-center gap-1.5 text-[10px] text-[var(--muted)] mb-0.5">
                <span className="font-bold text-[var(--text)] opacity-80">{label}</span>
                <span className="opacity-50">|</span>
                <span>目标 {target}{unit}</span>
            </div>

            {/* Value Row */}
            <div className="flex items-baseline gap-1.5">
                <span className="text-2xl font-bold font-mono tracking-tight text-[var(--foreground)] leading-none">
                    {data.current > 0 ? data.current : "--"}
                </span>
                <span className="text-xs text-[var(--muted)] font-medium">{unit}</span>
            </div>

            {/* Cumulative & Gap (Horizontal single line for compactness) */}
            <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5 text-[10px] leading-tight mt-1">
                <div className={`font-semibold ${data.cumulative <= 0 ? 'text-[var(--success)]' : 'text-[var(--warning)]'}`}>
                    累计 {data.cumulative > 0 ? '+' : ''}{data.cumulative.toFixed(1)}
                </div>
                <div className="text-[var(--muted)]/60 scale-90 origin-left">
                    (差 {Math.abs(data.gap).toFixed(1)})
                </div>
            </div>

            {/* Sparkline (Bottom) */}
            <div className="h-8 w-full mt-2 opacity-80 relative">
                <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={data.trendData}>
                        <Line type="monotone" dataKey="value" stroke={colorClass} strokeWidth={2} dot={{ r: 2 }} isAnimationActive={false} />
                        <ReferenceLine y={target} stroke="var(--success)" strokeDasharray="2 2" />
                    </LineChart>
                </ResponsiveContainer>
                {/* Trend Arrow */}
                {data.trendData.length >= 2 && data.trendData[data.trendData.length - 1].value < data.trendData[data.trendData.length - 2].value && (
                    <div className="absolute right-0 top-0 text-[10px] text-[var(--success)]">
                        ↘ {(data.trendData[data.trendData.length - 2].value - data.trendData[data.trendData.length - 1].value).toFixed(1)}
                    </div>
                )}
            </div>
        </div>
    );

    // Component: Right Side Small Multiple Chart
    const SmallChart = ({ data, target, color, unit }: any) => (
        <div className="h-14 w-full relative group">
            <ResponsiveContainer width="100%" height="100%">
                <LineChart data={data}>
                    {/* Faint Target Line */}
                    <ReferenceLine y={target} stroke="var(--success)" strokeOpacity={0.3} strokeDasharray="3 3" />
                    <Line
                        type="monotone"
                        dataKey="value"
                        stroke={color}
                        strokeWidth={2}
                        dot={false}
                        connectNulls={true}
                        isAnimationActive={true}
                    />
                </LineChart>
            </ResponsiveContainer>

            {/* Task Markers Axis - Explicitly rendered outside chart logic for precision control */}
            <div className="absolute bottom-0 inset-x-0 flex justify-between px-2">
                {data.map((d: any, i: number) => (
                    <div key={i} className="flex flex-col items-center">
                        <div className={`mb-1 transition-all duration-300 ${d.hasData ? "scale-100" : "scale-75 opacity-20 grayscale"}`}>
                            {d.hasData ? (
                                <div className={`w-1.5 h-1.5 rounded-full ${color.replace('var(--', 'bg-').replace(')', '-500')}`} style={{ backgroundColor: color }} />
                            ) : (
                                <div className="w-1.5 h-1.5 rounded-full border border-[var(--muted)]" />
                            )}
                        </div>
                        {/* Tiny verification icon for completed tasks */}
                        {d.hasData ? (
                            <Check className="w-2.5 h-2.5 text-[var(--success)] opacity-50" />
                        ) : (
                            <div className="w-2.5 h-2.5" /> // Spacer
                        )}
                    </div>
                ))}
            </div>
        </div>
    );

    return (
        <AppCard className="flex flex-row items-stretch h-full p-0 overflow-hidden box-border">
            {/* LEFT: Quick Read Area (Allocated ~35%) */}
            <div className="w-[38%] flex flex-col p-3 pr-4 border-r border-[var(--border)] bg-[var(--surface)] relative shrink-0">
                <div className="text-[10px] font-bold text-[var(--muted)] uppercase tracking-wider mb-2">当前状态</div>
                <div className="flex flex-row gap-4 h-full">
                    <MetricBlock label="体重" target={TARGET_WEIGHT} data={w} unit="kg" colorClass="var(--primary)" />
                    <div className="w-px bg-[var(--border)]/50 h-full mx-1 self-center" />
                    <MetricBlock label="体脂" target={TARGET_FAT} data={f} unit="%" colorClass="var(--accent)" />
                </div>
            </div>

            {/* RIGHT: System Task Charts (Small Multiples) */}
            <div className="flex-1 flex flex-col p-3 bg-slate-50/50 min-w-0">
                <div className="flex items-center justify-between mb-2 shrink-0">
                    <div className="text-[10px] font-bold text-[var(--muted)] uppercase tracking-wider flex items-center gap-2">
                        <span>核心任务进度</span>
                        <span className="text-[9px] bg-slate-200 px-1.5 py-0.5 rounded text-slate-500 font-medium">近6周</span>
                    </div>
                    {/* Add Button Trigger */}
                    <Dialog open={isAdding} onOpenChange={setIsAdding}>
                        <DialogTrigger asChild>
                            <button className="w-6 h-6 flex items-center justify-center rounded-full bg-[var(--surface)] border border-[var(--border)] hover:border-[var(--primary)] text-[var(--muted)] hover:text-[var(--primary)] transition shadow-sm">
                                <Plus className="w-3.5 h-3.5" />
                            </button>
                        </DialogTrigger>
                        <DialogContent className="sm:max-w-[400px]">
                            <DialogHeader>
                                <DialogTitle>发布今日任务</DialogTitle>
                            </DialogHeader>
                            <div className="grid grid-cols-2 gap-4 py-4">
                                <button
                                    onClick={() => handleCreateTask('weight')}
                                    className="flex flex-col items-center justify-center gap-2 p-4 h-32 rounded-lg border-2 border-dashed border-slate-200 hover:border-[var(--primary)] hover:bg-[var(--primary)]/5 transition-all group"
                                >
                                    <div className="w-10 h-10 rounded-full bg-[var(--primary)]/10 text-[var(--primary)] flex items-center justify-center group-hover:scale-110 transition-transform">
                                        <span className="text-lg font-bold">Kg</span>
                                    </div>
                                    <span className="text-sm font-medium text-slate-600 group-hover:text-[var(--primary)]">记录体重</span>
                                </button>

                                <button
                                    onClick={() => handleCreateTask('fat')}
                                    className="flex flex-col items-center justify-center gap-2 p-4 h-32 rounded-lg border-2 border-dashed border-slate-200 hover:border-[var(--accent)] hover:bg-[var(--accent)]/5 transition-all group"
                                >
                                    <div className="w-10 h-10 rounded-full bg-[var(--accent)]/10 text-[var(--accent)] flex items-center justify-center group-hover:scale-110 transition-transform">
                                        <TrendingDown className="w-5 h-5" />
                                    </div>
                                    <span className="text-sm font-medium text-slate-600 group-hover:text-[var(--accent)]">记录身材</span>
                                </button>
                            </div>
                        </DialogContent>
                    </Dialog>
                </div>

                <div className="flex-1 flex flex-col justify-between gap-2 min-h-0">
                    {/* Weight Chart Row */}
                    <div className="flex-1 flex flex-col justify-center min-h-0">
                        <div className="flex items-center justify-between text-[10px] mb-1 px-1 opacity-90">
                            <span className="font-bold text-slate-700">体重 (Weight)</span>
                            <span className="text-[9px] text-slate-400">目标: {TARGET_WEIGHT}kg</span>
                        </div>
                        <SmallChart data={w.chart6Weeks} target={TARGET_WEIGHT} color="var(--primary)" unit="kg" />
                    </div>

                    {/* Fat Chart Row */}
                    <div className="flex-1 flex flex-col justify-center border-t border-slate-200/50 pt-2 min-h-0">
                        <div className="flex items-center justify-between text-[10px] mb-1 px-1 opacity-90">
                            <span className="font-bold text-slate-700">体脂 (Body Fat)</span>
                            <span className="text-[9px] text-slate-400">目标: {TARGET_FAT}%</span>
                        </div>
                        <SmallChart data={f.chart6Weeks} target={TARGET_FAT} color="var(--accent)" unit="%" />
                    </div>
                </div>
            </div>
        </AppCard>
    );
}
