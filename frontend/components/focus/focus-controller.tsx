"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { apiPost, fetcher } from "@/lib/utils";
import { Project, Task } from "@/types";
import { FocusTimer } from "./focus-timer";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { AlertCircle, ArrowLeft } from "lucide-react";

type SessionStatus = "entry" | "running" | "paused" | "completed";

interface FocusState {
    status: SessionStatus;
    startTime: number; // timestamp
    pausedTotalSec: number;
    lastPauseTime?: number; // timestamp
    projectId: string | null;
    taskId: string | null;
    customLabel: string;
    projectNameSnapshot?: string;
    taskTitleSnapshot?: string;
}

export function FocusController() {
    const { user } = useAuth();
    const router = useRouter();

    // Data
    const [projects, setProjects] = useState<Project[]>([]);
    const [tasks, setTasks] = useState<Task[]>([]);
    const [loading, setLoading] = useState(true);

    // Entry Form State
    const [selectedTaskId, setSelectedTaskId] = useState<string>("");
    const [selectedProjectId, setSelectedProjectId] = useState<string>("");
    const [customLabel, setCustomLabel] = useState<string>("");

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

    // Timer Logic
    const [elapsedSec, setElapsedSec] = useState(0);
    const timerRef = useRef<NodeJS.Timeout | null>(null);

    // Initial Load
    useEffect(() => {
        const loadData = async () => {
            try {
                const [pData, tData] = await Promise.all([
                    fetcher<Project[]>("/api/projects"),
                    fetcher<Task[]>("/api/tasks")
                ]);
                setProjects(pData.filter(p => p.status !== "SUCCESS" && p.status !== "FAILURE"));
                setTasks(tData.filter(t => t.status !== "DONE"));
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
            projectNameSnapshot: activeProjectName,
            taskTitleSnapshot: activeTaskTitle
        };
        localStorage.setItem("focus_state", JSON.stringify(state));
    }, [sessionStatus, startTime, pausedTotalSec, lastPauseTime, activeProjectId, activeTaskId, activeLabel]);


    // Handlers
    const handleStart = () => {
        const now = Date.now();
        setStartTime(now);
        setSessionStatus("running");

        // Snapshot names
        const task = tasks.find(t => t.id === selectedTaskId);
        const project = projects.find(p => p.id === selectedProjectId);

        setActiveTaskId(selectedTaskId || null);
        setActiveProjectId(selectedProjectId || null);
        setActiveLabel(customLabel);
        setActiveTaskTitle(task?.title || "");
        setActiveProjectName(project?.title || "");

        // Determine if logic path is valid
        if (!selectedTaskId && !selectedProjectId && !customLabel) {
            alert("请至少选择一个任务、项目或输入标签");
            setSessionStatus("entry");
            return;
        }
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
            await apiPost("/api/study/sessions", {
                project_id: activeProjectId,
                task_id: activeTaskId,
                custom_label: activeLabel,
                created_at: new Date(startTime).toISOString(),
                duration_sec: elapsedSec,
                status: "completed"
            });

            // Clear local storage logic handled by effect when status changes to completed/entry
            setSessionStatus("entry");
            localStorage.removeItem("focus_state");
            router.push("/dashboard");
        } catch (e) {
            alert("提交失败，请重试");
        }
    };

    const handleAbandon = () => {
        setSessionStatus("entry");
        localStorage.removeItem("focus_state");
        // Reset local state fields
        setElapsedSec(0);
        setStartTime(0);
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
        if (projectId && selectedTaskId) {
            const task = tasks.find(t => t.id === selectedTaskId);
            if (task && task.project_id !== projectId) {
                setSelectedTaskId("");
            }
        }
    };


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
                contextLabel={activeProjectName || activeLabel || "Free Focus"}
                subContextLabel={activeTaskTitle}
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
                            className="w-full h-10 px-3 rounded-md border border-input bg-background"
                            value={selectedTaskId}
                            onChange={(e) => onTaskSelect(e.target.value)}
                        >
                            <option value="">-- 不绑定任务 --</option>
                            {filteredTasks.map(t => (
                                <option key={t.id} value={t.id}>{t.title}</option>
                            ))}
                        </select>
                    </div>

                    {/* Path A: Project Select */}
                    <div className="space-y-2">
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
                    </div>

                    {/* Path C: Custom Label (Only if no task/project usually, but can be additive) */}
                    {!selectedTaskId && !selectedProjectId && (
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

                    <button
                        onClick={handleStart}
                        disabled={!selectedTaskId && !selectedProjectId && !customLabel}
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
        </div>
    );
}
