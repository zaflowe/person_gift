"use client";

import { RequireAuth } from "@/lib/auth-context";
import { AppLayout } from "@/components/layout/app-layout";
import { StatusBadge } from "@/components/ui/status-badge";
import { TasksSkeleton } from "@/components/ui/empty-state";
import { NextActions } from "@/components/ui/next-actions";
import useSWR from "swr";
import { fetcher, formatDate } from "@/lib/utils";
import { Task, NextAction, Project } from "@/types";
import { Plus, Calendar, Clock, Lock, Tag, CalendarClock, Folder } from "lucide-react";
import { useState } from "react";
import { getProjectColor } from "@/lib/project-colors";
import { CreateTaskModal } from "@/components/modals/create-task-modal";
import { ScheduleDrawer } from "@/components/drawers/schedule-drawer";
import { useRouter } from "next/navigation";

// A2. Fixed Color Mapping (Tailwind classes) - for the 4px bar
const BAR_COLORS = {
    OPEN: "bg-amber-400",
    DONE: "bg-green-500",
    OVERDUE: "bg-red-500",
    EVIDENCE_SUBMITTED: "bg-blue-500",
    EXCUSED: "bg-gray-400",
    LOCKED: "bg-slate-300"
};

export default function TasksPage() {
    return (
        <RequireAuth>
            <AppLayout>
                <div className="bg-white min-h-screen pb-20">
                    <TasksContent />
                </div>
            </AppLayout>
        </RequireAuth>
    );
}

function TasksContent() {
    const router = useRouter();
    const { data: tasks, error } = useSWR<Task[]>("/api/tasks", fetcher);
    const { data: projects } = useSWR<Project[]>("/api/projects", fetcher);
    // Create a map for project lookup
    const projectMap = projects?.reduce((acc, p) => ({ ...acc, [p.id]: p }), {} as Record<string, Project>) || {};

    const [filter, setFilter] = useState<string>("open");
    const [isCreateOpen, setIsCreateOpen] = useState(false);

    // Drawer State
    const [scheduleTask, setScheduleTask] = useState<Task | null>(null);

    const loading = !tasks && !error;

    // Filter Logic
    const filteredTasks = tasks?.filter(t => {
        if (filter === "all") return t.status !== "DONE" && t.status !== "EXCUSED";
        if (filter === "completed") return t.status === "DONE" || t.status === "EXCUSED";
        if (filter === "overdue") return t.status === "OVERDUE";
        if (filter === "open") return t.status === "OPEN";
        if (filter === "evidence") return t.status === "EVIDENCE_SUBMITTED";
        if (filter === "scheduled") return !!t.scheduled_time;
        if (filter === "unscheduled") return !t.scheduled_time && t.status !== "DONE" && t.status !== "EXCUSED";
        return true;
    }).sort((a, b) => {
        // D. Sorting: Overdue > Today > Scheduled > Unscheduled > Others
        const score = (t: Task) => {
            if (t.status === 'OVERDUE') return 5;
            if (t.deadline && new Date(t.deadline).toDateString() === new Date().toDateString()) return 4;
            if (t.scheduled_time) return 3;
            if (!t.scheduled_time && t.status === 'OPEN') return 2;
            return 1;
        };
        return score(b) - score(a);
    }) || [];

    // Counts for Tabs
    const getCount = (key: string) => {
        if (!tasks) return 0;
        if (key === 'all') return tasks.filter(t => t.status !== 'DONE' && t.status !== 'EXCUSED').length;
        if (key === 'completed') return tasks.filter(t => t.status === 'DONE' || t.status === 'EXCUSED').length;
        if (key === 'open') return tasks.filter(t => t.status === 'OPEN').length;
        if (key === 'overdue') return tasks.filter(t => t.status === 'OVERDUE').length;
        if (key === 'evidence') return tasks.filter(t => t.status === 'EVIDENCE_SUBMITTED').length;
        if (key === 'unscheduled') return tasks.filter(t => !t.scheduled_time && t.status !== 'DONE' && t.status !== 'EXCUSED').length;
        if (key === 'scheduled') return tasks.filter(t => !!t.scheduled_time).length;
        return 0;
    };

    // Next Actions Logic
    const overdueCount = getCount('overdue');
    const unscheduledCount = getCount('unscheduled');
    const nextActions: NextAction[] = [];

    if (unscheduledCount > 0) {
        nextActions.push({
            id: "schedule",
            priority: "medium",
            title: `${unscheduledCount} 个任务未安排`,
            action: "批量安排", // TODO: Implement batch later, for now just links to filter
            onClick: () => setFilter("unscheduled")
        });
    }

    return (
        <div className="max-w-5xl mx-auto">
            {/* Header Area */}
            <div className="p-6 pb-2">
                <div className="flex items-center justify-between mb-6">
                    <div>
                        <h1 className="text-2xl font-bold tracking-tight text-slate-900">任务中心</h1>
                    </div>
                    <button
                        onClick={() => setIsCreateOpen(true)}
                        className="flex items-center gap-2 px-5 py-2.5 bg-slate-900 text-white rounded-xl hover:bg-slate-800 transition-all shadow-lg shadow-slate-900/10 text-sm font-medium"
                    >
                        <Plus className="w-4 h-4" />
                        新建任务
                    </button>
                </div>

                <NextActions actions={nextActions} />

                {/* Tabs with Counts */}
                <div className="flex items-center gap-8 border-b border-slate-100 overflow-x-auto no-scrollbar mt-6">
                    {[
                        { key: "open", label: "进行中" },
                        { key: "all", label: "待办" }, // Renamed from "全部" to "待办" (Active) for clarity, or keep "全部" but meaning active
                        { key: "unscheduled", label: "未安排" },
                        { key: "scheduled", label: "已安排" },
                        { key: "overdue", label: "已逾期", alert: true },
                        { key: "evidence", label: "待验收" },
                        { key: "completed", label: "已完成" }
                    ].map(f => {
                        const count = getCount(f.key);
                        const isActive = filter === f.key;
                        return (
                            <button
                                key={f.key}
                                onClick={() => setFilter(f.key)}
                                className={`pb-3 text-sm font-medium transition-all relative whitespace-nowrap flex items-center gap-2 ${isActive ? "text-slate-900" : "text-slate-500 hover:text-slate-700"
                                    }`}
                            >
                                {f.label}
                                <span className={`text-xs px-1.5 py-0.5 rounded-full ${isActive ? "bg-slate-100 text-slate-900" : "bg-slate-50 text-slate-400"
                                    }`}>
                                    {count}
                                </span>
                                {isActive && (
                                    <span className="absolute bottom-0 left-0 right-0 h-[2px] bg-slate-900 rounded-t-full" />
                                )}
                            </button>
                        );
                    })}
                </div>
            </div>

            {/* Task List (Refined Card Style) */}
            <div className="min-h-[400px]">
                {loading ? (
                    <div className="p-6"><TasksSkeleton /></div>
                ) : filteredTasks.length === 0 ? (
                    <div className="py-20 text-center">
                        <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-slate-50 mb-4">
                            <Lock className="w-8 h-8 text-slate-300" />
                        </div>
                        <h3 className="text-lg font-medium text-slate-900">暂无任务</h3>
                        <p className="text-slate-500 text-sm mt-1">当前列表为空</p>
                    </div>
                ) : (
                    <div className="flex flex-col gap-3 p-6 pt-0">
                        {filteredTasks.map(task => (
                            <div
                                key={task.id}
                                onClick={() => router.push(`/tasks/${task.id}`)}
                                className="group relative bg-white border border-slate-200 rounded-xl p-4 pl-5 shadow-sm hover:shadow-md transition-all duration-200 overflow-hidden cursor-pointer"
                            >
                                {/* Left Color Bar (Inside the card) */}
                                <div className={`absolute left-0 top-1 bottom-1 w-1 rounded-r-md mx-1 ${BAR_COLORS[task.status as keyof typeof BAR_COLORS] || 'bg-slate-200'}`} />

                                {/* Row 1: Title & Right Actions */}
                                <div className="flex items-center justify-between mb-3">
                                    <h3 className="text-base font-semibold text-slate-900 truncate pr-4">
                                        {task.title}
                                    </h3>

                                    <div className="flex items-center gap-3">
                                        {/* A4. Schedule Button for Unscheduled Tasks */}
                                        {!task.scheduled_time && task.status === 'OPEN' && (
                                            <button
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    setScheduleTask(task);
                                                }}
                                                className="hidden group-hover:flex items-center gap-1.5 px-3 py-1.5 bg-white border border-slate-200 text-slate-700 text-xs font-medium rounded-lg hover:border-indigo-500 hover:text-indigo-600 transition-all shadow-sm"
                                            >
                                                <Calendar className="w-3.5 h-3.5" />
                                                安排时间
                                            </button>
                                        )}
                                        <StatusBadge
                                            status={task.status}
                                            type="task"
                                            className="px-2.5 py-1 text-xs font-semibold shadow-none border-0 bg-slate-100/80"
                                        />
                                    </div>
                                </div>

                                {/* Row 2: Info (Time / Project / Tags) */}
                                <div className="flex items-center flex-wrap gap-x-4 gap-y-2 text-sm">
                                    {/* 1. Time */}
                                    {task.scheduled_time ? (
                                        <div className="flex items-center gap-1.5 text-slate-500">
                                            <Clock className="w-3.5 h-3.5" />
                                            <span>
                                                {formatDate(task.scheduled_time)} {" "}
                                                {new Date(task.scheduled_time).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}
                                                {task.deadline && ` – ${new Date(task.deadline).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}`}
                                            </span>
                                        </div>
                                    ) : (
                                        <div className="flex items-center gap-1.5 text-slate-400">
                                            <Clock className="w-3.5 h-3.5" />
                                            <span>未安排</span>
                                        </div>
                                    )}

                                    {/* 2. Project Chip */}
                                    {task.project_id && projectMap[task.project_id] ? (
                                        (() => {
                                            const p = projectMap[task.project_id!];
                                            const isStrategic = projects?.filter(p => p.status !== 'SUCCESS' && p.status !== 'FAILURE').slice(0, 3).some(sp => sp.id === p.id) || false;
                                            const strategicIndex = projects?.filter(p => p.status !== 'SUCCESS' && p.status !== 'FAILURE').slice(0, 3).findIndex(sp => sp.id === p.id) ?? -1;
                                            const color = getProjectColor(p.id, isStrategic, strategicIndex);

                                            return (
                                                <div className={`flex items-center gap-1.5 px-2 py-0.5 rounded-md text-xs font-medium border ${color.bgLight} ${color.text} ${color.border}`}>
                                                    <Folder className="w-3 h-3" />
                                                    <span className="max-w-[120px] truncate">{p.title}</span>
                                                </div>
                                            );
                                        })()
                                    ) : (
                                        <div className="flex items-center gap-1.5 bg-slate-50 text-slate-400 border border-slate-100 px-2 py-0.5 rounded-md text-xs font-medium">
                                            <Folder className="w-3 h-3" />
                                            <span>无项目</span>
                                        </div>
                                    )}

                                    {/* 3. Tags */}
                                    {task.tags && task.tags.length > 0 && (
                                        <div className="flex items-center gap-2">
                                            {task.tags.slice(0, 3).map((tag, i) => (
                                                <span key={i} className="text-xs text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded-full font-medium">
                                                    #{tag}
                                                </span>
                                            ))}
                                            {task.tags.length > 3 && (
                                                <span className="text-xs text-slate-400">+{task.tags.length - 3}</span>
                                            )}
                                        </div>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            <CreateTaskModal
                isOpen={isCreateOpen}
                onClose={() => setIsCreateOpen(false)}
            />

            <ScheduleDrawer
                isOpen={!!scheduleTask}
                onClose={() => setScheduleTask(null)}
                task={scheduleTask}
            />
        </div>
    );
}

