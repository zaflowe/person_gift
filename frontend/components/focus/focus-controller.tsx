"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { apiPost, fetcher } from "@/lib/utils";
import { Project, Task } from "@/types";
import { FocusTimer } from "./focus-timer";

type SessionStatus = "entry" | "running" | "paused" | "completed";
const QUICK_START_TASK_VALUE = "__quick_start__";

interface FocusState {
    status: SessionStatus;
    startTime: number; // timestamp
    pausedTotalSec: number;
    lastPauseTime?: number; // timestamp
    projectId: string | null;
    taskId: string | null;
    customLabel: string;
    isQuickStart?: boolean;
    quickStartAction?: string;
    projectNameSnapshot?: string;
    taskTitleSnapshot?: string;
}

export function FocusController() {
    const router = useRouter();

    // Data
    const [projects, setProjects] = useState<Project[]>([]);
    const [tasks, setTasks] = useState<Task[]>([]);
    const [loading, setLoading] = useState(true);

    // Entry Form State
    const [selectedTaskId, setSelectedTaskId] = useState<string>("");
    const [selectedProjectId, setSelectedProjectId] = useState<string>("");
    const [customLabel, setCustomLabel] = useState<string>("");
    const [quickStartAction, setQuickStartAction] = useState<string>("");
    const [quickStartTodayCount, setQuickStartTodayCount] = useState<number>(0);

    // Session State
    const [sessionStatus, setSessionStatus] = useState<SessionStatus>("entry");
    const [startTime, setStartTime] = useState<number>(0);
    const [pausedTotalSec, setPausedTotalSec] = useState<number>(0);
    const [lastPauseTime, setLastPauseTime] = useState<number | undefined>(undefined);

    // Snapshots
    const [activeProjectId, setActiveProjectId] = useState<string | null>(null);
    const [activeTaskId, setActiveTaskId] = useState<string | null>(null);
    const [activeLabel, setActiveLabel] = useState<string>("");
    const [activeProjectName, setActiveProjectName] = useState<string>("");
    const [activeTaskTitle, setActiveTaskTitle] = useState<string>("");
    const [activeIsQuickStart, setActiveIsQuickStart] = useState<boolean>(false);
    const [activeQuickStartAction, setActiveQuickStartAction] = useState<string>("");
    const [showQuickStartPrompt, setShowQuickStartPrompt] = useState(false);
    const [quickStartPromptTaskId, setQuickStartPromptTaskId] = useState<string | null>(null);

    // Timer Logic
    const [elapsedSec, setElapsedSec] = useState(0);
    const timerRef = useRef<NodeJS.Timeout | null>(null);

    // Initial Load
    useEffect(() => {
        const loadData = async () => {
            try {
                const [pData, tData, studyStats] = await Promise.all([
                    fetcher<Project[]>("/api/projects"),
                    fetcher<Task[]>("/api/tasks"),
                    fetcher<any>("/api/study/stats")
                ]);
                setProjects(pData.filter(p => p.status !== "SUCCESS" && p.status !== "FAILURE"));
                setTasks(tData.filter(t => t.status !== "DONE"));
                setQuickStartTodayCount(studyStats?.quick_start_today_count || 0);
            } catch (e) {
                console.error("Failed to load setup data", e);
            } finally {
                setLoading(false);
            }
        };

        loadData();

        // Restore state
        const savedState = localStorage.getItem("focus_state");
        if (savedState) {
            try {
                const state: FocusState = JSON.parse(savedState);
                // Validate expiry (e.g. paused for too long)
                // For MVP, just restore
                setSessionStatus(state.status);
                setStartTime(state.startTime);
                setPausedTotalSec(state.pausedTotalSec);
                setLastPauseTime(state.lastPauseTime);
                setActiveProjectId(state.projectId);
                setActiveTaskId(state.taskId);
                setActiveLabel(state.customLabel);
                setActiveIsQuickStart(!!state.isQuickStart);
                setActiveQuickStartAction(state.quickStartAction || "");
                setActiveProjectName(state.projectNameSnapshot || "");
                setActiveTaskTitle(state.taskTitleSnapshot || "");
            } catch (e) {
                localStorage.removeItem("focus_state");
            }
        }
    }, []);

    // Timer Tick
    useEffect(() => {
        if (sessionStatus === "running") {
            timerRef.current = setInterval(() => {
                const now = Date.now();
                const totalElapsed = Math.floor((now - startTime) / 1000);
                setElapsedSec(totalElapsed - pausedTotalSec);
            }, 1000);
        } else if (sessionStatus === "paused") {
            // Check pause limit (5 mins)
            if (lastPauseTime) {
                const pauseDuration = (Date.now() - lastPauseTime) / 1000;
                if (pauseDuration > 5 * 60) {
                    // Pause limit exceeded logic (For now just warn or visual indicator, strictly invalidating might be harsh for MVP)
                }
            }
            if (timerRef.current) clearInterval(timerRef.current);
        } else {
            if (timerRef.current) clearInterval(timerRef.current);
        }

        return () => {
            if (timerRef.current) clearInterval(timerRef.current);
        };
    }, [sessionStatus, startTime, pausedTotalSec, lastPauseTime]);

    // Recalculate elapsed on restore
    useEffect(() => {
        if (startTime > 0) {
            const now = Date.now();
            let currentPause = 0;
            if (sessionStatus === "paused" && lastPauseTime) {
                currentPause = Math.floor((now - lastPauseTime) / 1000);
            }
            const totalElapsed = Math.floor((now - startTime) / 1000);
            setElapsedSec(totalElapsed - pausedTotalSec - currentPause);
        }
    }, [startTime, pausedTotalSec, lastPauseTime, sessionStatus]);

    // Persist State
    useEffect(() => {
        if (sessionStatus === "entry") {
            localStorage.removeItem("focus_state");
            return;
        }

        const state: FocusState = {
            status: sessionStatus,
            startTime,
            pausedTotalSec,
            lastPauseTime,
            projectId: activeProjectId,
            taskId: activeTaskId,
            customLabel: activeLabel,
            isQuickStart: activeIsQuickStart,
            quickStartAction: activeQuickStartAction,
            projectNameSnapshot: activeProjectName,
            taskTitleSnapshot: activeTaskTitle
        };
        localStorage.setItem("focus_state", JSON.stringify(state));
    }, [sessionStatus, startTime, pausedTotalSec, lastPauseTime, activeProjectId, activeTaskId, activeLabel, activeIsQuickStart, activeQuickStartAction, activeProjectName, activeTaskTitle]);


    // Handlers
    const resetSessionToEntry = () => {
        setSessionStatus("entry");
        localStorage.removeItem("focus_state");
        setElapsedSec(0);
        setStartTime(0);
        setPausedTotalSec(0);
        setLastPauseTime(undefined);
        setActiveProjectId(null);
        setActiveTaskId(null);
        setActiveLabel("");
        setActiveProjectName("");
        setActiveTaskTitle("");
        setActiveIsQuickStart(false);
        setActiveQuickStartAction("");
    };

    const handleStart = () => {
        const isQuickStartMode = selectedTaskId === QUICK_START_TASK_VALUE;
        if (!isQuickStartMode && !selectedTaskId && !selectedProjectId && !customLabel) {
            alert("请至少选择一个任务、项目或输入标签");
            return;
        }

        const now = Date.now();
        setStartTime(now);
        setSessionStatus("running");

        // Snapshot names
        const task = isQuickStartMode ? undefined : tasks.find(t => t.id === selectedTaskId);
        const project = isQuickStartMode ? undefined : projects.find(p => p.id === selectedProjectId);

        setActiveTaskId(isQuickStartMode ? null : (selectedTaskId || null));
        setActiveProjectId(isQuickStartMode ? null : (selectedProjectId || null));
        setActiveLabel(isQuickStartMode ? "Quick Start" : customLabel);
        setActiveTaskTitle(task?.title || "");
        setActiveProjectName(project?.title || "");
        setActiveIsQuickStart(isQuickStartMode);
        setActiveQuickStartAction(isQuickStartMode ? quickStartAction.trim() : "");
    };

    const handlePause = () => {
        setSessionStatus("paused");
        setLastPauseTime(Date.now());
    };

    const handleResume = () => {
        if (lastPauseTime) {
            const pauseDuration = Math.floor((Date.now() - lastPauseTime) / 1000);
            setPausedTotalSec(prev => prev + pauseDuration);
        }
        setLastPauseTime(undefined);
        setSessionStatus("running");
    };

    const handleComplete = async () => {
        if (elapsedSec < 60) {
            if (!confirm("专注时间少于1分钟，确定要结束吗？(不会记录)")) return;
        }

        try {
            const result = await apiPost<any>("/api/study/sessions", {
                project_id: activeIsQuickStart ? null : activeProjectId,
                task_id: activeIsQuickStart ? null : activeTaskId,
                custom_label: activeLabel,
                created_at: new Date(startTime).toISOString(),
                duration_sec: elapsedSec,
                status: "completed",
                is_quick_start: activeIsQuickStart,
                quick_start_action: activeIsQuickStart ? activeQuickStartAction : null,
            });
            const shouldPromptQuickStart = Boolean(
                activeIsQuickStart &&
                elapsedSec >= 5 * 60 &&
                result?.quick_start_valid &&
                result?.quick_start_task_id
            );

            if (shouldPromptQuickStart) {
                setQuickStartTodayCount(prev => prev + 1);
                setQuickStartPromptTaskId(result.quick_start_task_id);
                setShowQuickStartPrompt(true);
                resetSessionToEntry();
                return;
            }

            resetSessionToEntry();
            router.push("/dashboard");
        } catch (e) {
            alert("提交失败，请重试");
        }
    };

    const handleAbandon = () => {
        resetSessionToEntry();
    };

    // Filter Logic
    const filteredTasks = tasks.filter(t => {
        if (!selectedProjectId) return true;
        // If project selected, only show tasks of that project
        return t.project_id === selectedProjectId;
    });

    // Auto-fill Project on Task Select
    const onTaskSelect = (taskId: string) => {
        setSelectedTaskId(taskId);
        if (taskId === QUICK_START_TASK_VALUE) {
            setSelectedProjectId("");
            setCustomLabel("");
            return;
        }
        if (taskId) {
            const task = tasks.find(t => t.id === taskId);
            // If task belongs to a project, auto-select that project
            if (task && task.project_id) {
                setSelectedProjectId(task.project_id);
            }
        }
    };

    // Handle Project Change - Clear task if not in new project
    const onProjectSelect = (projectId: string) => {
        setSelectedProjectId(projectId);
        // If we selected a specific project (not "All/None"), check if current task is valid
        if (projectId && selectedTaskId && selectedTaskId !== QUICK_START_TASK_VALUE) {
            const task = tasks.find(t => t.id === selectedTaskId);
            if (task && task.project_id !== projectId) {
                setSelectedTaskId("");
            }
        }
    };


    const isQuickStartMode = selectedTaskId === QUICK_START_TASK_VALUE;
    const startDisabled = !isQuickStartMode && !selectedTaskId && !selectedProjectId && !customLabel;

    if (loading) return <div className="flex h-screen items-center justify-center">Loading...</div>;

    // View: Running / Paused
    if (sessionStatus === "running" || sessionStatus === "paused") {
        return (
            <FocusTimer
                durationSec={elapsedSec}
                isPaused={sessionStatus === "paused"}
                onPause={handlePause}
                onResume={handleResume}
                onComplete={handleComplete}
                onAbandon={() => {
                    if (confirm("确定要放弃本次专注吗？记录将不会保存。")) handleAbandon();
                }}
                contextLabel={activeIsQuickStart ? "Quick Start" : (activeProjectName || activeLabel || "Free Focus")}
                subContextLabel={activeIsQuickStart ? (activeQuickStartAction || undefined) : activeTaskTitle}
                quickStartHint={activeIsQuickStart ? `Quick Start · 今日第 ${quickStartTodayCount + 1} 次` : null}
            />
        );
    }

    // View: Entry
    return (
        <div className="flex flex-col items-center justify-center min-h-screen p-6 max-w-md mx-auto w-full animate-fade-in">
            <div className="w-full space-y-8">
                <div className="text-center space-y-2">
                    <h1 className="text-2xl font-bold tracking-tight">开始专注</h1>
                    <p className="text-muted-foreground text-sm">选择任务或设定目标，进入心流状态</p>
                </div>

                <div className="space-y-6 bg-surface p-6 rounded-xl border border-border shadow-sm">

                    {/* Path A/B: Task Select */}
                    <div className="space-y-2">
                        <label className="text-sm font-medium">选择任务 (Optional)</label>
                        <select
                            className={`w-full h-10 px-3 rounded-md border border-input bg-background ${isQuickStartMode ? "font-semibold text-amber-700 border-amber-300 bg-amber-50/50" : ""}`}
                            value={selectedTaskId}
                            onChange={(e) => onTaskSelect(e.target.value)}
                        >
                            <option value="">-- 不绑定任务 --</option>
                            <option value={QUICK_START_TASK_VALUE} style={{ fontWeight: "700", color: "#b45309" }}>⚡ 快速启动</option>
                            {filteredTasks.map(t => (
                                <option key={t.id} value={t.id}>{t.title}</option>
                            ))}
                        </select>
                        {isQuickStartMode && (
                            <p className="text-xs text-amber-700 font-medium">Quick Start 模式：不绑定项目，不填写专注目标</p>
                        )}
                    </div>

                    {/* Path A: Project Select */}
                    {!isQuickStartMode && <div className="space-y-2">
                        <label className="text-sm font-medium">所属项目 (Optional)</label>
                        <select
                            className="w-full h-10 px-3 rounded-md border border-input bg-background"
                            value={selectedProjectId}
                            onChange={(e) => onProjectSelect(e.target.value)}
                        >
                            <option value="">-- 无项目 (显示全部任务) --</option>
                            {projects.map(p => (
                                <option key={p.id} value={p.id}>{p.title}</option>
                            ))}
                        </select>
                        <p className="text-xs text-muted-foreground">
                            * 绑定项目可计入项目投入分布
                        </p>
                    </div>}

                    {/* Path C: Custom Label (Only if no task/project usually, but can be additive) */}
                    {!isQuickStartMode && !selectedTaskId && !selectedProjectId && (
                        <div className="space-y-2 animate-slide-in-right">
                            <label className="text-sm font-medium">或 输入专注目标</label>
                            <input
                                type="text"
                                className="w-full h-10 px-3 rounded-md border border-input bg-background"
                                placeholder="例如：阅读、思考..."
                                value={customLabel}
                                onChange={(e) => setCustomLabel(e.target.value)}
                            />
                        </div>
                    )}

                    {isQuickStartMode && (
                        <div className="space-y-2 animate-slide-in-right">
                            <label className="text-sm font-medium text-amber-700">最小启动动作（可选）</label>
                            <input
                                type="text"
                                className="w-full h-10 px-3 rounded-md border border-amber-200 bg-amber-50/40"
                                placeholder="例如：打开题册、写5分钟代码、整理桌面..."
                                value={quickStartAction}
                                onChange={(e) => setQuickStartAction(e.target.value)}
                            />
                        </div>
                    )}

                    <button
                        onClick={handleStart}
                        disabled={startDisabled}
                        className="w-full h-12 bg-primary text-primary-foreground font-medium rounded-md hover:bg-primary/90 disabled:opacity-50 transition-colors"
                    >
                        进入专注模式
                    </button>

                    <button
                        onClick={() => router.push("/dashboard")}
                        className="w-full h-10 text-muted-foreground text-sm hover:text-foreground transition-colors"
                    >
                        返回仪表盘
                    </button>
                </div>
            </div>

            {showQuickStartPrompt && (
                <div className="fixed inset-0 z-50 flex items-center justify-center">
                    <div
                        className="absolute inset-0 bg-black/40"
                        onClick={() => {
                            setShowQuickStartPrompt(false);
                            router.push("/dashboard");
                        }}
                    />
                    <div className="relative w-full max-w-sm mx-4 rounded-xl bg-white border border-slate-200 shadow-xl p-5">
                        <h3 className="text-base font-semibold text-slate-900">本次专注已结束</h3>
                        <p className="text-sm text-slate-600 mt-2">要现在补录任务吗？</p>
                        <div className="mt-4 flex gap-3">
                            <button
                                className="flex-1 h-10 rounded-md border border-slate-200 hover:bg-slate-50 text-sm"
                                onClick={() => {
                                    setShowQuickStartPrompt(false);
                                    router.push("/dashboard");
                                }}
                            >
                                稍后
                            </button>
                            <button
                                className="flex-1 h-10 rounded-md bg-foreground text-white hover:bg-slate-700 text-sm font-medium"
                                onClick={() => {
                                    const taskId = quickStartPromptTaskId;
                                    setShowQuickStartPrompt(false);
                                    if (taskId) router.push(`/tasks/${taskId}`);
                                    else router.push("/tasks");
                                }}
                            >
                                去填写
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
