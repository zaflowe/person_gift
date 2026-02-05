"use client";

import { RequireAuth } from "@/lib/auth-context";
import { AppLayout } from "@/components/layout/app-layout";
import { LoadingSkeleton, ScheduleSkeleton } from "@/components/ui/empty-state";
import useSWR from "swr";
import { fetcher, formatDate } from "@/lib/utils";
import { Task, Project } from "@/types";
import { useState, useRef, useEffect } from "react";
import { HabitSidebar } from "@/components/habits/habit-list";
import { FixedBlockSidebar } from "@/components/habits/fixed-block-list";
import { checkDailyHabits } from "@/lib/api/habits";
import { getToken } from "@/lib/utils";
import { getProjectColor } from "@/lib/project-colors";

// 1. Fixed Time Blocks (06:00 - 24:00, 2h intervals)
const TIME_BLOCKS = [
    { start: 6, end: 8, label: "06:00" },
    { start: 8, end: 10, label: "08:00" },
    { start: 10, end: 12, label: "10:00" },
    { start: 12, end: 14, label: "12:00" },
    { start: 14, end: 16, label: "14:00" },
    { start: 16, end: 18, label: "16:00" },
    { start: 18, end: 20, label: "18:00" },
    { start: 20, end: 22, label: "20:00" },
    { start: 22, end: 24, label: "22:00" },
];

// Helper: Get Urgency Color
const getStatusColor = (deadline: string | null, status: string) => {
    if (status === 'OVERDUE') return "bg-red-500";
    if (status === 'DONE') return "bg-green-500";
    if (status === 'EVIDENCE_SUBMITTED') return "bg-blue-500";

    if (!deadline) return "bg-slate-300";
    const now = new Date();
    const d = new Date(deadline);
    const diffHours = (d.getTime() - now.getTime()) / (1000 * 60 * 60);

    if (diffHours < 0) return "bg-red-500";
    if (diffHours <= 2) return "bg-orange-500";
    if (diffHours <= 6) return "bg-yellow-400";
    return "bg-slate-300";
};

// Infinite Range
const PAST_DAYS = 14;
const FUTURE_DAYS = 30;

// Column Widths (px)
const WIDTH_NARROW = 240; // w-60
const WIDTH_WIDE = 320;   // w-80

export default function SchedulePage() {
    return (
        <RequireAuth>
            <AppLayout>
                <div className="bg-white min-h-screen flex flex-col h-screen overflow-hidden">
                    <ScheduleContent />
                </div>
            </AppLayout>
        </RequireAuth>
    );
}

function ScheduleContent() {
    const { data: tasks } = useSWR<Task[]>("/api/tasks", fetcher);
    const { data: projects } = useSWR<Project[]>("/api/projects", fetcher);
    // Trigger Daily Habit Check
    useEffect(() => {
        // Non-blocking trigger. API client handles token.
        checkDailyHabits().catch(console.error);
    }, []);

    // Project Map for sidebar or tooltips
    const projectMap = projects?.reduce((acc, p) => ({ ...acc, [p.id]: p.title }), {} as Record<string, string>) || {};

    const [days, setDays] = useState<Date[]>([]);
    const scrollContainerRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const today = new Date();
        const arr = [];
        for (let i = -PAST_DAYS; i <= FUTURE_DAYS; i++) {
            const d = new Date(today);
            d.setDate(today.getDate() + i);
            arr.push(d);
        }
        setDays(arr);
    }, []);

    // Initial Scroll (Auto to Today at Left)
    useEffect(() => {
        if (days.length > 0 && scrollContainerRef.current) {
            // Logic: All past days are NARROW.
            // Today is at index PAST_DAYS.
            // Target Left = PAST_DAYS * WIDTH_NARROW
            // Use requestAnimationFrame to ensure layout is ready
            requestAnimationFrame(() => {
                if (scrollContainerRef.current) {
                    const targetLeft = (PAST_DAYS * WIDTH_NARROW);
                    scrollContainerRef.current.scrollTo({ left: targetLeft, behavior: 'auto' });
                }
            });
        }
    }, [days]);

    if (!tasks) return (
        <div className="flex flex-col h-full bg-slate-50">
            {/* Match Header Height roughly */}
            <div className="h-[60px] bg-white border-b border-slate-200 shrink-0"></div>
            <div className="flex-1 overflow-hidden">
                <ScheduleSkeleton />
            </div>
        </div>
    );

    // Grouping & Sort (Same as before)
    const scheduleMap: Record<string, Record<number, Task[]>> = {};
    tasks.forEach(task => {
        if (!task.deadline) return;
        const d = new Date(task.deadline);
        const dayKey = d.toDateString();
        const hour = d.getHours();

        let blockStart = -1;
        for (const block of TIME_BLOCKS) {
            if (hour >= block.start && hour < block.end) {
                blockStart = block.start;
                break;
            }
        }
        if (blockStart !== -1) {
            if (!scheduleMap[dayKey]) scheduleMap[dayKey] = {};
            if (!scheduleMap[dayKey][blockStart]) scheduleMap[dayKey][blockStart] = [];
            scheduleMap[dayKey][blockStart].push(task);
        }
    });
    Object.keys(scheduleMap).forEach(day => {
        Object.keys(scheduleMap[day]).forEach(block => {
            scheduleMap[day][Number(block)].sort((a, b) => new Date(a.deadline!).getTime() - new Date(b.deadline!).getTime());
        });
    });

    const isToday = (d: Date) => d.toDateString() === new Date().toDateString();
    const isPastDate = (d: Date) => {
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        return d < today;
    };

    const now = new Date();
    const currentHour = now.getHours();
    const currentMinutes = now.getMinutes();

    return (
        <div className="flex flex-col h-full bg-slate-50">
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-4 bg-white border-b border-slate-200 shrink-0 z-30 shadow-sm">
                <div className="flex items-center gap-4">
                    <h1 className="text-xl font-bold text-slate-900">🗓️ 日程</h1>
                    <div className="text-xs text-slate-500 bg-slate-100 px-2 py-1 rounded">
                        {formatDate(days[0]?.toISOString())} - {formatDate(days[days.length - 1]?.toISOString())}
                    </div>
                </div>
                <button
                    onClick={() => {
                        if (scrollContainerRef.current && days.length > 0) {
                            scrollContainerRef.current.scrollTo({ left: (PAST_DAYS * WIDTH_NARROW), behavior: 'smooth' });
                        }
                    }}
                    className="text-xs font-medium px-3 py-1.5 bg-indigo-50 text-indigo-600 rounded-lg hover:bg-indigo-100 transition-colors"
                >
                    回到今天
                </button>
            </div>

            {/* Main Layout: Row */}
            <div className="flex-1 flex overflow-hidden">
                {/* Scrollable Schedule Grid */}
                <div
                    ref={scrollContainerRef}
                    className="flex-1 flex overflow-x-auto bg-white custom-scrollbar"
                    onWheel={(e) => {
                        // Smart Wheel Logic:
                        // 1. Check if we are scrolling inside a task list that strictly has overflow
                        const target = e.target as HTMLElement;
                        const scrollableList = target.closest('.custom-scrollbar');

                        if (scrollableList) {
                            const { scrollHeight, clientHeight } = scrollableList;
                            // Margin of error 1px
                            if (scrollHeight > clientHeight + 1) {
                                // List needs to scroll vertically. Let native behavior happen.
                                return;
                            }
                        }

                        // 2. Otherwise, map vertical wheel to horizontal scroll
                        if (scrollContainerRef.current) {
                            scrollContainerRef.current.scrollLeft += e.deltaY;
                        }
                    }}
                >
                    {/* Sticky Sidebar (Left Time Labels) */}
                    <div className="w-16 shrink-0 flex flex-col pt-12 border-r border-slate-100 bg-white sticky left-0 z-20 shadow-[4px_0_12px_-4px_rgba(0,0,0,0.05)]">
                        {TIME_BLOCKS.map(block => (
                            <div key={block.start} className="flex-1 relative border-b border-transparent min-h-[80px]">
                                <span className="absolute -top-3 right-2 text-xs font-medium text-slate-400 font-mono">
                                    {block.start.toString().padStart(2, '0')}:00
                                </span>
                            </div>
                        ))}
                    </div>

                    {/* Infinite Columns */}
                    {days.map((day, i) => {
                        const dayStr = day.toDateString();
                        const isCurrent = isToday(day);
                        const isPast = isPastDate(day);

                        let colBg = "bg-white";
                        if (isPast) colBg = "bg-slate-50";
                        if (isCurrent) colBg = "bg-indigo-50/20";

                        // Variable Width logic: Today is Wide, others Narrow
                        const widthClass = isCurrent ? "w-80" : "w-60"; // w-80=320px, w-60=240px

                        return (
                            <div key={i} className={`flex-none ${widthClass} flex flex-col border-r border-slate-100/50 shrink-0 ${colBg} transition-all`}>
                                {/* Date Header */}
                                <div className={`
                                    h-12 flex items-center justify-center border-b border-slate-200/50 sticky top-0 z-10
                                    ${isCurrent ? "bg-indigo-50/80 backdrop-blur-sm border-indigo-100" : isPast ? "bg-slate-50" : "bg-white"}
                                `}>
                                    <div className="flex flex-col items-center leading-none">
                                        <span className={`text-[10px] uppercase font-bold mb-0.5 ${isCurrent ? "text-indigo-600" : "text-slate-400"}`}>
                                            {day.toLocaleDateString('en-US', { weekday: 'short' })}
                                        </span>
                                        <span className={`text-sm font-bold ${isCurrent ? "text-indigo-600" : "text-slate-700"}`}>
                                            {day.getDate()}
                                        </span>
                                    </div>
                                </div>

                                {/* Time Blocks Container */}
                                <div className="flex-1 flex flex-col">
                                    {TIME_BLOCKS.map(block => {
                                        const tasksInBlock = scheduleMap[dayStr]?.[block.start] || [];
                                        const isBlockEndPast = isCurrent && block.end <= currentHour;
                                        const isCurrentBlock = isCurrent && block.start <= currentHour && block.end > currentHour;

                                        // Styling
                                        let blockStyleClass = "border-b border-slate-100/50 relative p-1.5 flex-1 min-h-[80px] flex flex-col group/block transition-colors ";
                                        if (isBlockEndPast) {
                                            blockStyleClass += "bg-slate-200/20";
                                        } else if (!isPast && !isCurrentBlock) {
                                            blockStyleClass += "hover:bg-slate-50";
                                        }

                                        // Red Line
                                        let redLineTop = -1;
                                        if (isCurrentBlock) {
                                            const totalMinutes = (block.end - block.start) * 60;
                                            const passedMinutes = (currentHour - block.start) * 60 + currentMinutes;
                                            redLineTop = (passedMinutes / totalMinutes) * 100;
                                        }

                                        return (
                                            <div
                                                key={block.start}
                                                className={blockStyleClass}
                                            // Removed e.stopPropagation() to allow logic to bubble to container
                                            >
                                                {redLineTop !== -1 && (
                                                    <div
                                                        className="absolute left-0 right-0 border-t-2 border-red-500 z-0 pointer-events-none shadow-[0_0_4px_rgba(239,68,68,0.4)]"
                                                        style={{ top: `${redLineTop}%` }}
                                                    >
                                                        <div className="absolute -left-1 -top-1 w-2 h-2 bg-red-500 rounded-full" />
                                                    </div>
                                                )}

                                                <div className="flex-1 overflow-y-hidden group-hover/block:overflow-y-auto custom-scrollbar relative z-10 space-y-1">
                                                    {tasksInBlock.map(task => {
                                                        const date = new Date(task.deadline!);
                                                        const timeStr = date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
                                                        const statusColor = getStatusColor(task.deadline!, task.status);

                                                        // Project Color Logic
                                                        let projectColorBg = "bg-slate-300";
                                                        if (task.project_id && projectMap[task.project_id]) {
                                                            const pId = task.project_id;
                                                            // Logic to determine strategic index matching global Project list is tricky without full project list here (we only have map).
                                                            // For now, let's just use hash. To be perfect, we need `projects` array to find index.
                                                            // Let's grab `projects` from closure.
                                                            const isStrategic = projects?.filter(p => p.status !== 'SUCCESS' && p.status !== 'FAILURE').slice(0, 3).some(sp => sp.id === pId) || false;
                                                            const strategicIndex = projects?.filter(p => p.status !== 'SUCCESS' && p.status !== 'FAILURE').slice(0, 3).findIndex(sp => sp.id === pId) ?? -1;
                                                            projectColorBg = getProjectColor(pId, isStrategic, strategicIndex).bg;
                                                        }

                                                        return (
                                                            <a
                                                                key={task.id}
                                                                href={`/tasks/${task.id}`}
                                                                title={`${task.title} (${timeStr})`}
                                                                className="flex items-center gap-2 bg-white border border-slate-100/80 shadow-sm rounded px-2 py-1 hover:shadow-md hover:border-indigo-200 transition-all cursor-pointer group/card h-[32px]"
                                                            >
                                                                <div className={`w-1.5 h-1.5 rounded-full shrink-0 ${projectColorBg}`} />
                                                                <div className="flex-1 flex items-center justify-between min-w-0 overflow-hidden">
                                                                    <span className="text-xs font-medium text-slate-700 truncate line-clamp-1 mr-2 group-hover/card:text-indigo-700">
                                                                        {task.title}
                                                                    </span>
                                                                    <span className="text-[10px] text-slate-400 font-mono shrink-0">
                                                                        {timeStr}
                                                                    </span>
                                                                </div>
                                                            </a>
                                                        );
                                                    })}
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>
                            </div>
                        );
                    })}
                </div>

                {/* Right Sidebar (Fixed 380px) */}
                <div className="w-[380px] shrink-0 border-l border-slate-200 bg-white flex flex-col z-20 shadow-[-4px_0_12px_-4px_rgba(0,0,0,0.05)]">
                    {/* Upper Half: Habits */}
                    <div className="h-1/2 overflow-hidden flex flex-col">
                        <HabitSidebar className="flex-1" />
                    </div>

                    {/* Lower Half: Fixed Blocks */}
                    <div className="h-1/2 overflow-hidden flex flex-col border-t border-slate-200">
                        <FixedBlockSidebar className="flex-1" />
                    </div>
                </div>
            </div>
        </div>
    );
}
