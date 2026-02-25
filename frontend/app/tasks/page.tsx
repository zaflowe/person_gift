"use client";

import { useMemo, useState } from "react";
import useSWR, { mutate } from "swr";
import { Calendar, Clock, Folder, Lock, Plus } from "lucide-react";
import { useRouter } from "next/navigation";

import { RequireAuth } from "@/lib/auth-context";
import { AppLayout } from "@/components/layout/app-layout";
import { TasksSkeleton } from "@/components/ui/empty-state";
import { StatusBadge } from "@/components/ui/status-badge";
import { CreateTaskModal } from "@/components/modals/create-task-modal";
import { ScheduleDrawer } from "@/components/drawers/schedule-drawer";
import { apiPatch, fetcher, formatDate } from "@/lib/utils";
import { Project, Task } from "@/types";
import { getProjectColor } from "@/lib/project-colors";

const IN_PROGRESS_LIMIT = 5;
const FROZEN_AFTER_DAYS = 14;

const BAR_COLORS = {
    OPEN: "bg-amber-400",
    DONE: "bg-green-500",
    OVERDUE: "bg-red-500",
    EVIDENCE_SUBMITTED: "bg-blue-500",
    EXCUSED: "bg-gray-400",
    LOCKED: "bg-slate-300",
} as const;

type TabKey = "in_progress" | "todo" | "completed" | "frozen";

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

    const [tab, setTab] = useState<TabKey>("in_progress");
    const [isCreateOpen, setIsCreateOpen] = useState(false);
    const [scheduleTask, setScheduleTask] = useState<Task | null>(null);
    const [laneUpdatingTaskId, setLaneUpdatingTaskId] = useState<string | null>(null);

    const loading = !tasks && !error;
    const allTasks = tasks || [];
    const projectMap = useMemo(
        () => projects?.reduce((acc, p) => ({ ...acc, [p.id]: p }), {} as Record<string, Project>) || {},
        [projects]
    );

    const now = new Date();
    const frozenThreshold = new Date(now.getTime() - FROZEN_AFTER_DAYS * 24 * 60 * 60 * 1000);

    const isFrozenTask = (task: Task) =>
        !!task.deadline &&
        task.status !== "DONE" &&
        task.status !== "EXCUSED" &&
        new Date(task.deadline) < frozenThreshold;

    const plannedOrder = (a: Task, b: Task) => {
        const aStart = a.scheduled_time ? new Date(a.scheduled_time).getTime() : Number.MAX_SAFE_INTEGER;
        const bStart = b.scheduled_time ? new Date(b.scheduled_time).getTime() : Number.MAX_SAFE_INTEGER;
        if (aStart !== bStart) return aStart - bStart;
        const aDeadline = a.deadline ? new Date(a.deadline).getTime() : Number.MAX_SAFE_INTEGER;
        const bDeadline = b.deadline ? new Date(b.deadline).getTime() : Number.MAX_SAFE_INTEGER;
        if (aDeadline !== bDeadline) return aDeadline - bDeadline;
        return new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
    };

    const pinnedOrder = (a: Task, b: Task) => {
        const aTs = a.board_lane_updated_at ? new Date(a.board_lane_updated_at).getTime() : 0;
        const bTs = b.board_lane_updated_at ? new Date(b.board_lane_updated_at).getTime() : 0;
        if (aTs !== bTs) return bTs - aTs;
        return plannedOrder(a, b);
    };

    const completedTasks = useMemo(
        () =>
            allTasks
                .filter(t => t.status === "DONE" || t.status === "EXCUSED")
                .sort(
                    (a, b) =>
                        new Date(b.completed_at || b.updated_at || b.created_at).getTime() -
                        new Date(a.completed_at || a.updated_at || a.created_at).getTime()
                ),
        [allTasks]
    );

    const frozenTasks = useMemo(
        () => allTasks.filter(isFrozenTask).sort(plannedOrder),
        [allTasks, tasks]
    );

    const activeNonFrozen = useMemo(
        () =>
            allTasks.filter(
                t => t.status !== "DONE" && t.status !== "EXCUSED" && !isFrozenTask(t)
            ),
        [allTasks, tasks]
    );

    const { inProgressTasks, todoTasks } = useMemo(() => {
        const pinnedInProgress = activeNonFrozen
            .filter(t => t.board_lane === "IN_PROGRESS")
            .sort(pinnedOrder);
        const manualTodo = activeNonFrozen
            .filter(t => t.board_lane === "TODO")
            .sort(plannedOrder);
        const autoPool = activeNonFrozen
            .filter(t => t.board_lane !== "IN_PROGRESS" && t.board_lane !== "TODO")
            .sort(plannedOrder);

        const keepPinned = pinnedInProgress.slice(0, IN_PROGRESS_LIMIT);
        const overflowPinned = pinnedInProgress.slice(IN_PROGRESS_LIMIT);
        const autoFill = autoPool.slice(0, Math.max(0, IN_PROGRESS_LIMIT - keepPinned.length));
        const inProgress = [...keepPinned, ...autoFill];
        const inProgressIds = new Set(inProgress.map(t => t.id));
        const todo = [
            ...manualTodo,
            ...overflowPinned,
            ...autoPool.filter(t => !inProgressIds.has(t.id)),
        ].sort(plannedOrder);

        return { inProgressTasks: inProgress, todoTasks: todo };
    }, [activeNonFrozen, tasks]);

    const setTaskLane = async (taskId: string, lane: "IN_PROGRESS" | "TODO" | null) => {
        await apiPatch(`/api/tasks/${taskId}`, { board_lane: lane });
    };

    const handlePromote = async (task: Task) => {
        setLaneUpdatingTaskId(task.id);
        try {
            const demoteCandidate =
                inProgressTasks.length >= IN_PROGRESS_LIMIT
                    ? [...inProgressTasks].sort(plannedOrder)[inProgressTasks.length - 1]
                    : null;
            const ops: Promise<any>[] = [setTaskLane(task.id, "IN_PROGRESS")];
            if (demoteCandidate && demoteCandidate.id !== task.id) {
                ops.push(setTaskLane(demoteCandidate.id, "TODO"));
            }
            await Promise.all(ops);
            mutate("/api/tasks");
        } catch (e) {
            console.error(e);
            alert("拉入进行中失败");
        } finally {
            setLaneUpdatingTaskId(null);
        }
    };

    const handleDemote = async (task: Task) => {
        setLaneUpdatingTaskId(task.id);
        try {
            await setTaskLane(task.id, "TODO");
            mutate("/api/tasks");
        } catch (e) {
            console.error(e);
            alert("移到待办失败");
        } finally {
            setLaneUpdatingTaskId(null);
        }
    };

    const handleClearLane = async (task: Task) => {
        setLaneUpdatingTaskId(task.id);
        try {
            await setTaskLane(task.id, null);
            mutate("/api/tasks");
        } catch (e) {
            console.error(e);
            alert("恢复自动失败");
        } finally {
            setLaneUpdatingTaskId(null);
        }
    };

    const tabs: { key: TabKey; label: string; count: number }[] = [
        { key: "in_progress", label: "进行中", count: inProgressTasks.length },
        { key: "todo", label: "待办", count: todoTasks.length },
        { key: "completed", label: "已完成", count: completedTasks.length },
        { key: "frozen", label: "冻结", count: frozenTasks.length },
    ];

    const currentView = (() => {
        if (tab === "in_progress") {
            return {
                title: "进行中",
                subtitle: `固定显示 ${IN_PROGRESS_LIMIT} 个以内`,
                tasks: inProgressTasks,
                emptyTitle: "当前进行中为空",
                emptyDesc: "系统会按计划时间自动补位，你也可以从待办手动换位",
                actions: "in_progress" as const,
            };
        }
        if (tab === "todo") {
            return {
                title: "待办",
                subtitle: "不占用进行中名额",
                tasks: todoTasks,
                emptyTitle: "待办为空",
                emptyDesc: "当前非冻结任务都在进行中或已完成",
                actions: "todo" as const,
            };
        }
        if (tab === "completed") {
            return {
                title: "已完成",
                subtitle: "已完成 / 已豁免",
                tasks: completedTasks,
                emptyTitle: "暂无已完成任务",
                emptyDesc: "完成后的任务会出现在这里",
                actions: "completed" as const,
            };
        }
        return {
            title: "冻结",
            subtitle: `逾期超过 ${FROZEN_AFTER_DAYS} 天；仅冻结任务可调整时间`,
            tasks: frozenTasks,
            emptyTitle: "暂无冻结任务",
            emptyDesc: "冻结任务重新安排时间后会回到待办",
            actions: "frozen" as const,
        };
    })();

    return (
        <div className="max-w-6xl mx-auto">
            <div className="p-6 pb-2">
                <div className="flex items-center justify-between mb-4">
                    <div>
                        <h1 className="text-2xl font-bold tracking-tight text-slate-900">任务中心</h1>
                        <p className="text-sm text-slate-500 mt-1">
                            保留原交互：顶部切换页签。进行中最多 {IN_PROGRESS_LIMIT} 个；换位不改计划时间。
                        </p>
                    </div>
                    <button
                        onClick={() => setIsCreateOpen(true)}
                        className="flex items-center gap-2 px-5 py-2.5 bg-slate-900 text-white rounded-xl hover:bg-slate-800 transition-all shadow-lg shadow-slate-900/10 text-sm font-medium"
                    >
                        <Plus className="w-4 h-4" />
                        新建任务
                    </button>
                </div>

                <div className="flex items-center gap-6 border-b border-slate-100 overflow-x-auto no-scrollbar">
                    {tabs.map(t => {
                        const active = tab === t.key;
                        return (
                            <button
                                key={t.key}
                                onClick={() => setTab(t.key)}
                                className={`pb-3 text-sm font-medium relative whitespace-nowrap ${active ? "text-slate-900" : "text-slate-500 hover:text-slate-700"}`}
                            >
                                {t.label}
                                <span className={`ml-2 text-xs px-1.5 py-0.5 rounded-full ${active ? "bg-slate-100 text-slate-900" : "bg-slate-50 text-slate-400"}`}>
                                    {t.count}
                                </span>
                                {active && <span className="absolute bottom-0 left-0 right-0 h-[2px] bg-slate-900 rounded-t-full" />}
                            </button>
                        );
                    })}
                </div>
            </div>

            <div className="min-h-[420px] p-6 pt-4">
                {loading ? (
                    <TasksSkeleton />
                ) : (
                    <TaskSection
                        title={currentView.title}
                        subtitle={currentView.subtitle}
                        tasks={currentView.tasks}
                        emptyTitle={currentView.emptyTitle}
                        emptyDesc={currentView.emptyDesc}
                        projectMap={projectMap}
                        projects={projects || []}
                        laneUpdatingTaskId={laneUpdatingTaskId}
                        onOpenTask={(id) => router.push(`/tasks/${id}`)}
                        onPromote={currentView.actions === "todo" ? handlePromote : undefined}
                        onDemote={currentView.actions === "in_progress" ? handleDemote : undefined}
                        onClearLane={
                            currentView.actions === "in_progress" || currentView.actions === "todo" || currentView.actions === "frozen"
                                ? handleClearLane
                                : undefined
                        }
                        onScheduleTask={currentView.actions === "frozen" ? setScheduleTask : undefined}
                    />
                )}
            </div>

            <CreateTaskModal isOpen={isCreateOpen} onClose={() => setIsCreateOpen(false)} />
            <ScheduleDrawer
                isOpen={!!scheduleTask}
                onClose={() => setScheduleTask(null)}
                task={scheduleTask}
                extraPatch={{ board_lane: "TODO" }}
            />
        </div>
    );
}

type TaskSectionProps = {
    title: string;
    subtitle: string;
    tasks: Task[];
    emptyTitle: string;
    emptyDesc: string;
    projectMap: Record<string, Project>;
    projects: Project[];
    laneUpdatingTaskId: string | null;
    onOpenTask: (id: string) => void;
    onPromote?: (task: Task) => void;
    onDemote?: (task: Task) => void;
    onClearLane?: (task: Task) => void;
    onScheduleTask?: (task: Task) => void;
};

function TaskSection(props: TaskSectionProps) {
    const { title, subtitle, tasks, emptyTitle, emptyDesc } = props;
    return (
        <section className="bg-white border border-slate-200 rounded-2xl p-4">
            <div className="flex items-center justify-between mb-3">
                <h2 className="text-base font-semibold text-slate-900">{title}</h2>
                <span className="text-xs text-slate-500">{subtitle}</span>
            </div>

            {tasks.length === 0 ? (
                <div className="py-14 text-center">
                    <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-slate-50 mb-3">
                        <Lock className="w-6 h-6 text-slate-300" />
                    </div>
                    <div className="text-sm font-medium text-slate-900">{emptyTitle}</div>
                    <div className="text-xs text-slate-500 mt-1">{emptyDesc}</div>
                </div>
            ) : (
                <div className="flex flex-col gap-3">
                    {tasks.map(task => (
                        <TaskCard key={task.id} task={task} {...props} />
                    ))}
                </div>
            )}
        </section>
    );
}

function TaskCard({
    task,
    projectMap,
    projects,
    laneUpdatingTaskId,
    onOpenTask,
    onPromote,
    onDemote,
    onClearLane,
    onScheduleTask,
}: TaskSectionProps & { task: Task }) {
    const laneUpdating = laneUpdatingTaskId === task.id;
    const project = task.project_id ? projectMap[task.project_id] : undefined;
    const strategicCandidates = projects.filter(p => p.status !== "SUCCESS" && p.status !== "FAILURE").slice(0, 3);
    const strategicIndex = project ? strategicCandidates.findIndex(p => p.id === project.id) : -1;
    const color = project ? getProjectColor(project.id, strategicIndex >= 0, strategicIndex) : null;

    const startText = task.scheduled_time
        ? `${formatDate(task.scheduled_time)} ${new Date(task.scheduled_time).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" })}`
        : "未设置";
    const endText = task.deadline
        ? new Date(task.deadline).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" })
        : "--:--";

    return (
        <div
            onClick={() => onOpenTask(task.id)}
            className="group relative bg-white border border-slate-200 rounded-xl p-4 pl-5 shadow-sm hover:shadow-md transition-all duration-200 overflow-hidden cursor-pointer"
        >
            <div className={`absolute left-0 top-1 bottom-1 w-1 rounded-r-md mx-1 ${BAR_COLORS[task.status as keyof typeof BAR_COLORS] || "bg-slate-200"}`} />

            <div className="flex items-center justify-between mb-3 gap-3">
                <h3 className="text-base font-semibold text-slate-900 truncate">{task.title}</h3>
                <div className="flex items-center gap-2 shrink-0">
                    {onPromote && (
                        <button
                            onClick={(e) => {
                                e.stopPropagation();
                                onPromote(task);
                            }}
                            disabled={laneUpdating}
                            className="hidden group-hover:flex items-center gap-1.5 px-3 py-1.5 bg-indigo-600 text-white text-xs font-medium rounded-lg hover:bg-indigo-700 transition-all disabled:opacity-50"
                        >
                            {laneUpdating ? "处理中..." : "拉入进行中"}
                        </button>
                    )}
                    {onDemote && (
                        <button
                            onClick={(e) => {
                                e.stopPropagation();
                                onDemote(task);
                            }}
                            disabled={laneUpdating}
                            className="hidden group-hover:flex items-center gap-1.5 px-3 py-1.5 bg-white border border-slate-200 text-slate-700 text-xs font-medium rounded-lg hover:border-slate-400 transition-all shadow-sm disabled:opacity-50"
                        >
                            {laneUpdating ? "处理中..." : "移到待办"}
                        </button>
                    )}
                    {onScheduleTask && (
                        <button
                            onClick={(e) => {
                                e.stopPropagation();
                                onScheduleTask(task);
                            }}
                            className="hidden group-hover:flex items-center gap-1.5 px-3 py-1.5 bg-white border border-indigo-200 text-indigo-600 text-xs font-medium rounded-lg hover:border-indigo-500 transition-all shadow-sm"
                        >
                            <Calendar className="w-3.5 h-3.5" />
                            调整时间
                        </button>
                    )}
                    {onClearLane && task.board_lane && (
                        <button
                            onClick={(e) => {
                                e.stopPropagation();
                                onClearLane(task);
                            }}
                            disabled={laneUpdating}
                            className="hidden group-hover:flex items-center gap-1.5 px-3 py-1.5 bg-white border border-slate-200 text-slate-700 text-xs font-medium rounded-lg hover:border-slate-400 transition-all shadow-sm disabled:opacity-50"
                        >
                            恢复自动
                        </button>
                    )}
                    <StatusBadge status={task.status} type="task" className="px-2.5 py-1 text-xs font-semibold shadow-none border-0 bg-slate-100/80" />
                </div>
            </div>

            <div className="flex items-center flex-wrap gap-x-4 gap-y-2 text-sm">
                <div className="flex items-center gap-1.5 text-slate-500">
                    <Clock className="w-3.5 h-3.5" />
                    <span>{startText} - {endText}</span>
                </div>

                {project ? (
                    <div className={`flex items-center gap-1.5 px-2 py-0.5 rounded-md text-xs font-medium border ${color?.bgLight} ${color?.text} ${color?.border}`}>
                        <Folder className="w-3 h-3" />
                        <span className="max-w-[160px] truncate">{project.title}</span>
                    </div>
                ) : (
                    <div className="flex items-center gap-1.5 bg-slate-50 text-slate-400 border border-slate-100 px-2 py-0.5 rounded-md text-xs font-medium">
                        <Folder className="w-3 h-3" />
                        <span>无项目</span>
                    </div>
                )}

                {task.board_lane && (
                    <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">
                        手动标记: {task.board_lane === "IN_PROGRESS" ? "进行中" : "待办"}
                    </span>
                )}

                {task.tags && task.tags.length > 0 && (
                    <div className="flex items-center gap-2">
                        {task.tags.slice(0, 3).map((tag, i) => (
                            <span key={i} className="text-xs text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded-full font-medium">
                                #{tag}
                            </span>
                        ))}
                        {task.tags.length > 3 && <span className="text-xs text-slate-400">+{task.tags.length - 3}</span>}
                    </div>
                )}
            </div>
        </div>
    );
}
