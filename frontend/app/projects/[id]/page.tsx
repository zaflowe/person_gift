"use client";

import { RequireAuth } from "@/lib/auth-context";
import { AppLayout } from "@/components/layout/app-layout";
import { StatusBadge } from "@/components/ui/status-badge";
import { apiPost, fetcher, apiPatch, apiDelete } from "@/lib/utils";
import { Project, Milestone, Task } from "@/types";
import { ArrowLeft, CheckCircle, Flag, Lock, Play, Target, ListTodo, Edit2, Trash2, Plus, Calendar } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import useSWR, { mutate } from "swr";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { useToast } from "@/components/ui/toast";
import { CreateTaskModal } from "@/components/modals/create-task-modal";
import { CreateLongTaskModal } from "@/components/modals/create-long-task-modal";
import { EditTaskModal } from "@/components/modals/edit-task-modal";
import { EditLongTaskModal } from "@/components/modals/edit-long-task-modal";
import { ProjectLongTaskTemplate, hideProjectLongTaskTemplate } from "@/lib/api/project-long-tasks";

import { EditProjectModal } from "@/components/modals/edit-project-modal";

interface MilestoneInput {
    title: string;
    description?: string;
    is_critical: boolean;
    target_date?: string;
}

interface MilestoneFormProps {
    initialData: Partial<MilestoneInput>;
    onSave: (data: MilestoneInput) => Promise<void>;
    onCancel: () => void;
    isProcessing: boolean;
}

type Rgb = { r: number; g: number; b: number };

function hexToRgb(hex?: string | null): Rgb {
    const normalized = (hex || "#3b82f6").replace("#", "").trim();
    const full = normalized.length === 3
        ? normalized.split("").map((c) => c + c).join("")
        : normalized.padEnd(6, "0").slice(0, 6);
    const num = Number.parseInt(full, 16);
    if (Number.isNaN(num)) return { r: 59, g: 130, b: 246 };
    return { r: (num >> 16) & 255, g: (num >> 8) & 255, b: num & 255 };
}

function rgbToHex({ r, g, b }: Rgb): string {
    return `#${[r, g, b].map((v) => Math.max(0, Math.min(255, Math.round(v))).toString(16).padStart(2, "0")).join("")}`;
}

function mix(colorA: string, colorB: string, ratio: number): string {
    const a = hexToRgb(colorA);
    const b = hexToRgb(colorB);
    const t = Math.max(0, Math.min(1, ratio));
    return rgbToHex({
        r: a.r + (b.r - a.r) * t,
        g: a.g + (b.g - a.g) * t,
        b: a.b + (b.b - a.b) * t,
    });
}

function alpha(hex: string, opacity: number): string {
    const { r, g, b } = hexToRgb(hex);
    const a = Math.max(0, Math.min(1, opacity));
    return `rgba(${r}, ${g}, ${b}, ${a})`;
}

function milestoneThemeColor(baseColor: string, index: number): string {
    const paletteTargets = ["#3b82f6", "#6366f1", "#8b5cf6", "#0ea5e9", "#14b8a6", "#f59e0b"];
    return mix(baseColor, paletteTargets[index % paletteTargets.length], 0.45);
}

export default function ProjectDetailPage() {
    return (
        <RequireAuth>
            <AppLayout>
                <ProjectDetailContent />
            </AppLayout>
        </RequireAuth>
    );
}

function ProjectDetailContent() {
    const params = useParams();
    const router = useRouter();
    const { showToast } = useToast();
    const id = params.id as string;

    // Fetch project, milestones, and tasks
    const { data: project, error, mutate: reloadProject } = useSWR<Project>(id ? `/api/projects/${id}` : null, fetcher);
    const { data: milestones, mutate: reloadMilestones } = useSWR<Milestone[]>(id ? `/api/projects/${id}/milestones` : null, fetcher);
    // FIX: Filter tasks by project_id
    const { data: tasks, mutate: reloadTasks } = useSWR<Task[]>(id ? `/api/tasks?project_id=${id}` : null, fetcher);
    const { data: longTaskTemplates, mutate: reloadLongTaskTemplates } = useSWR<ProjectLongTaskTemplate[]>(
        id ? `/api/projects/${id}/long-task-templates` : null,
        fetcher
    );

    const [processing, setProcessing] = useState(false);
    const [isEditing, setIsEditing] = useState(false);
    const [isAddingMilestone, setIsAddingMilestone] = useState(false);
    const [isAddingTask, setIsAddingTask] = useState(false);
    const [isAddingLongTask, setIsAddingLongTask] = useState(false);
    const [editingMilestoneId, setEditingMilestoneId] = useState<string | null>(null);
    const [editingTask, setEditingTask] = useState<Task | null>(null);
    const [editingLongTask, setEditingLongTask] = useState<ProjectLongTaskTemplate | null>(null);
    const [createTaskMilestoneId, setCreateTaskMilestoneId] = useState<string | null>(null);
    const [milestoneSort, setMilestoneSort] = useState<'asc' | 'desc'>('asc'); // Not used yet but requested
    const [showColorPicker, setShowColorPicker] = useState(false);
    const [editForm, setEditForm] = useState({
        description: "",
        success_criteria: "",
        failure_criteria: ""
    });
    const terminalTaskStatuses = new Set(["DONE", "EXCUSED"]);
    const allMilestonesAchieved = milestones && milestones.length > 0 && milestones.every(m => m.status === "ACHIEVED");
    const milestoneTasksById = (tasks || []).reduce<Record<string, Task[]>>((acc, task) => {
        if (!task.milestone_id) return acc;
        (acc[task.milestone_id] ||= []).push(task);
        return acc;
    }, {});

    const orderedMilestones = useMemo(
        () => (milestones || []).slice().sort((a, b) => (a.order_index ?? 0) - (b.order_index ?? 0)),
        [milestones]
    );
    const milestoneLookup = useMemo(
        () => Object.fromEntries((orderedMilestones || []).map(m => [m.id, m])),
        [orderedMilestones]
    );
    const allProjectTasks = useMemo(
        () => (tasks || []).slice().sort((a, b) => {
            const aDeadline = a.deadline ? new Date(a.deadline).getTime() : Number.MAX_SAFE_INTEGER;
            const bDeadline = b.deadline ? new Date(b.deadline).getTime() : Number.MAX_SAFE_INTEGER;
            return aDeadline - bDeadline;
        }),
        [tasks]
    );

    const currentUnlockedMilestone = orderedMilestones.find(m => m.is_unlocked && m.status !== "ACHIEVED") || null;
    const projectTaskTotal = allProjectTasks.length;
    const projectTaskDone = allProjectTasks.filter(t => terminalTaskStatuses.has(t.status)).length;
    const projectTaskUnlocked = allProjectTasks.filter(t => t.status !== "LOCKED").length;
    const projectMilestoneTotal = orderedMilestones.length;
    const projectMilestoneDone = orderedMilestones.filter(m => m.status === "ACHIEVED").length;
    const projectProgressPercent = projectTaskTotal > 0 ? Math.round((projectTaskDone / projectTaskTotal) * 100) : 0;
    const baseProjectColor = (project?.color && /^#?[0-9a-fA-F]{3,8}$/.test(project.color))
        ? (project.color.startsWith("#") ? project.color : `#${project.color}`)
        : "#3b82f6";
    const themeVars = {
        ["--project-primary" as any]: baseProjectColor,
        ["--project-primary-12" as any]: alpha(baseProjectColor, 0.12),
        ["--project-primary-20" as any]: alpha(baseProjectColor, 0.2),
        ["--project-primary-30" as any]: alpha(baseProjectColor, 0.3),
        ["--project-primary-40" as any]: alpha(baseProjectColor, 0.4),
        ["--project-primary-60" as any]: alpha(baseProjectColor, 0.6),
        ["--project-primary-gradient-start" as any]: mix(baseProjectColor, "#ffffff", 0.08),
        ["--project-primary-gradient-end" as any]: mix(baseProjectColor, "#111827", 0.06),
    } as React.CSSProperties;

    const getMilestoneTasks = (milestoneId: string) =>
        (milestoneTasksById[milestoneId] || []).slice().sort((a, b) => {
            const aDeadline = a.deadline ? new Date(a.deadline).getTime() : Number.MAX_SAFE_INTEGER;
            const bDeadline = b.deadline ? new Date(b.deadline).getTime() : Number.MAX_SAFE_INTEGER;
            return aDeadline - bDeadline;
        });

    const getMilestoneMetrics = (milestoneId: string) => {
        const list = getMilestoneTasks(milestoneId);
        const total = list.length;
        const done = list.filter(t => terminalTaskStatuses.has(t.status)).length;
        const percent = total > 0 ? Math.round((done / total) * 100) : 0;
        return { list, total, done, percent };
    };
    const isTaskEffectivelyLocked = (task: Task) => {
        if (terminalTaskStatuses.has(task.status)) return false;
        if (task.status === "LOCKED") return true;
        if (!task.milestone_id) return false;
        return milestoneLookup[task.milestone_id]?.is_unlocked === false;
    };
    const shouldHideTaskSchedule = (task: Task) => isTaskEffectivelyLocked(task);
    const getTaskVisualStatus = (task: Task) => (isTaskEffectivelyLocked(task) ? "LOCKED" : task.status);
    const getMilestoneVisual = (milestone: Milestone, index: number) => {
        const isLocked = milestone.is_unlocked === false;
        const isDone = milestone.status === "ACHIEVED";
        const isCurrent = currentUnlockedMilestone?.id === milestone.id && !isDone;
        const accent = isLocked ? "#9CA3AF" : milestoneThemeColor(baseProjectColor, index);
        return {
            isLocked,
            isDone,
            isCurrent,
            accent,
            cardStyle: isLocked
                ? {
                    backgroundColor: "#F8FAFC",
                    borderColor: "#E5E7EB",
                    borderStyle: "dashed" as const,
                }
                : isDone
                    ? {
                        backgroundColor: alpha(accent, 0.07),
                        borderColor: alpha(accent, 0.26),
                        boxShadow: `0 10px 28px ${alpha(accent, 0.10)}`,
                    }
                    : {
                        backgroundColor: "#FFFFFF",
                        borderColor: milestone.is_unlocked ? alpha(accent, 0.35) : "#E5E7EB",
                        boxShadow: milestone.is_unlocked
                            ? `${isCurrent ? `0 0 0 1px ${alpha(accent, 0.35)}, ` : ""}0 12px 34px ${alpha(accent, isCurrent ? 0.16 : 0.10)}`
                            : "0 2px 10px rgba(15,23,42,0.04)",
                    },
        };
    };

    if (error) return <div className="p-6 text-red-500">Loading failed</div>;
    if (!project) return <div className="p-6">Loading...</div>;

    // ... (Milestone handlers omitted for brevity, logic unchanged)

    // ... (Milestone handlers continued...)
    const handleAddMilestone = async (data: MilestoneInput) => {
        setProcessing(true);
        try {
            await apiPost(`/api/projects/${id}/milestones`, data);
            reloadMilestones();
        } catch (e: any) {
            alert(e.message);
        } finally {
            setProcessing(false);
        }
    };
    const handleUpdateMilestone = async (mid: string, data: Partial<MilestoneInput>) => {
        setProcessing(true);
        try {
            await apiPatch(`/api/projects/${id}/milestones/${mid}`, data);
            reloadMilestones();
        } catch (e: any) {
            alert(e.message);
        } finally {
            setProcessing(false);
        }
    };
    const handleDeleteMilestone = async (mid: string) => {
        if (!confirm("确定删除此里程碑吗？")) return;
        setProcessing(true);
        try {
            await apiDelete(`/api/projects/${id}/milestones/${mid}`);
            reloadMilestones();
        } catch (e: any) {
            alert(e.message);
        } finally {
            setProcessing(false);
        }
    };
    const markAchieved = async (mid: string) => {
        if (!confirm("确认标记此里程碑已完成？这可能会更新项目状态。")) return;
        setProcessing(true);
        try {
            await apiPost(`/api/projects/${id}/milestones/${mid}/mark-achieved`);
            reloadMilestones();
            reloadProject();
        } catch (e: any) {
            alert(e.message);
        } finally {
            setProcessing(false);
        }
    };
    // Removed inline edit handlers in favor of keys
    // Keeping toggleStrategic and handleConfirm
    const toggleStrategic = async () => {
        try {
            // Optimistic update
            reloadProject({ ...project, is_strategic: !project.is_strategic }, false);
            await apiPatch(`/api/projects/${id}`, { is_strategic: !project.is_strategic });
            reloadProject();
        } catch (err: unknown) {
            alert("切换战略状态失败: " + (err instanceof Error ? err.message : ""));
            reloadProject();
        }
    };

    // Handle Confirm Project (PROPOSED -> ACTIVE)
    const handleConfirm = async () => {
        const userConfirmed = confirm("确认启动此项目？一旦启动，您必须严格遵守里程碑。");
        if (!userConfirmed) return;

        const agreement = prompt("请输入 'I AGREE' 确认：");
        if (agreement !== "I AGREE") return;

        setProcessing(true);
        try {
            // Generate hash locally for simplicity
            const hash = btoa(new Date().toISOString() + project.id);
            await apiPost(`/api/projects/${id}/confirm`, { agreement_hash: hash });
            reloadProject();
            showToast("success", "项目已启动! Good luck. 契约已锁定。");
            // Optional: window.location.reload(); 
        } catch (err: unknown) {
            showToast("error", "启动失败: " + (err instanceof Error ? err.message : ""));
        } finally {
            setProcessing(false);
        }
    };

    const WEEKDAYS = ["一", "二", "三", "四", "五", "六", "日"];
    const formatLongTaskFrequency = (t: ProjectLongTaskTemplate) => {
        if (t.frequency_mode === "specific_days") {
            return `每周 ${t.days_of_week?.map(d => WEEKDAYS[d]).join(" ")}`;
        }
        return t.interval_days === 1 ? "每天" : `每 ${t.interval_days} 天`;
    };

    const handleHideLongTask = async (templateId: string) => {
        if (!confirm("确认隐藏该长期任务模板？隐藏后仍会继续生成任务。")) return;
        try {
            await hideProjectLongTaskTemplate(id, templateId);
            reloadLongTaskTemplates();
        } catch (e: any) {
            alert(e.message || "隐藏失败");
        }
    };

    const handleUpdateTask = async (taskId: string, payload: any) => {
        setProcessing(true);
        try {
            await apiPatch(`/api/tasks/${taskId}`, payload);
            reloadTasks();
            setEditingTask(null);
        } catch (e: any) {
            alert(e.message || "更新任务失败");
        } finally {
            setProcessing(false);
        }
    };

    const handleUpdateLongTaskTemplate = async (templateId: string, payload: any) => {
        setProcessing(true);
        try {
            await apiPatch(`/api/projects/${id}/long-task-templates/${templateId}`, payload);
            reloadLongTaskTemplates();
            setEditingLongTask(null);
        } catch (e: any) {
            alert(e.message || "更新长期任务失败");
        } finally {
            setProcessing(false);
        }
    };

    const handleCompleteProject = async () => {
        if (!confirm("确认完成项目？此操作会将项目标记为已完成。")) return;
        setProcessing(true);
        try {
            await apiPost(`/api/projects/${id}/complete`, {});
            reloadProject();
        } catch (e: any) {
            alert(e.message || "完成项目失败");
        } finally {
            setProcessing(false);
        }
    };

    return (
        <div
            className="max-w-4xl mx-auto p-6 space-y-6 bg-[var(--project-page-bg,#F8FAFC)]"
            style={{ ...themeVars, ["--project-page-bg" as any]: "#F8FAFC" }}
        >
            <style jsx>{`
                .project-progress-fill,
                .milestone-progress-fill {
                    transition: width 0.4s ease;
                }
                .milestone-card-hover {
                    transition: transform 0.2s ease, box-shadow 0.25s ease, border-color 0.25s ease;
                }
                .milestone-card-hover:hover {
                    transform: translateY(-2px);
                }
                .milestone-current-glow {
                    animation: projectCardPulse 2.4s ease-in-out infinite;
                }
                @keyframes projectCardPulse {
                    0%, 100% { box-shadow: inherit; }
                    50% { box-shadow: 0 0 0 1px rgba(255,255,255,0.35), 0 14px 32px rgba(15,23,42,0.1); }
                }
            `}</style>
            {/* Header */}
            <div className="flex items-center gap-4">
                <Link href="/projects" className="p-2 hover:bg-muted rounded-full">
                    <ArrowLeft className="w-5 h-5" />
                </Link>
                <div className="flex-1 min-w-0">
                    <h1 className="text-2xl font-bold break-all flex items-center gap-2">
                        {project.title}
                        <button
                            onClick={toggleStrategic}
                            className={`px-2 py-0.5 text-xs rounded-full border transition-colors ${project.is_strategic
                                ? "bg-indigo-100 text-indigo-700 border-indigo-200 hover:bg-indigo-200"
                                : "bg-gray-100 text-gray-500 border-gray-200 hover:bg-gray-200"
                                }`}
                            title="点击切换战略状态"
                        >
                            {project.is_strategic ? "⭐ 战略项目" : "☆ 普通项目"}
                        </button>
                    </h1>
                    <div className="flex items-center gap-2 text-muted-foreground mt-1">
                        <Target className="w-4 h-4" />
                        <span className="text-sm truncate">{project.success_criteria || "No specific criteria"}</span>
                    </div>
                </div>
                <div className="ml-auto flex items-center gap-3 relative">
                    {/* Color Picker Trigger */}
                    <div className="relative group">
                        <button
                            className="w-6 h-6 rounded-full border border-border hover:scale-110 transition-transform shadow-sm"
                            style={{ backgroundColor: project.color || "#cbd5e1" }}
                            title="更改项目颜色"
                            onClick={() => setShowColorPicker(!showColorPicker)}
                        />
                        {/* Dropdown - Click to toggle */}
                        {showColorPicker && (
                            <div className="absolute right-0 top-8 bg-white dark:bg-zinc-900 border-2 border-border shadow-xl rounded-lg p-2 w-[140px] z-50">
                                <div className="grid grid-cols-4 gap-2">
                                    {[
                                        "#ef4444", "#f97316", "#f59e0b", "#22c55e", "#14b8a6",
                                        "#3b82f6", "#6366f1", "#8b5cf6", "#d946ef", "#f43f5e",
                                        "#cbd5e1", "" // Slate & Auto
                                    ].map((c, i) => (
                                        <button
                                            key={i}
                                            className="w-5 h-5 rounded-full border hover:scale-125 transition-transform"
                                            style={{ backgroundColor: c || "#ffffff", borderColor: c ? "transparent" : "#e2e8f0" }}
                                            title={c || "默认"}
                                            onClick={async () => {
                                                // Optimistic update
                                                reloadProject({ ...project, color: c }, false);
                                                setShowColorPicker(false); // Close dropdown
                                                try {
                                                    await apiPatch(`/api/projects/${id}`, { color: c });
                                                    reloadProject();
                                                    // Invalidate global caches so Dashboard updates immediately
                                                    mutate("/api/projects");
                                                    mutate("/api/dashboard/projects/strategic");
                                                } catch (e: unknown) {
                                                    alert("Update failed");
                                                }
                                            }}
                                        >
                                            {!c && <div className="text-[8px] text-center text-slate-400">A</div>}
                                        </button>
                                    ))}
                                </div>
                                {/* Backdrop to close on click outside - simple version */}
                                <div
                                    className="fixed inset-0 z-[-1]"
                                    onClick={() => setShowColorPicker(false)}
                                ></div>
                            </div>
                        )}
                    </div>

                    <StatusBadge status={project.status} type="project" className="text-lg px-3 py-1" />
                </div>
            </div>

            {/* Project Progress (Lightweight) */}
            <div
                className="rounded-2xl border p-4 md:p-5"
                style={{
                    background: `linear-gradient(180deg, ${alpha(baseProjectColor, 0.10)} 0%, rgba(255,255,255,0.96) 100%)`,
                    borderColor: alpha(baseProjectColor, 0.20),
                    boxShadow: `0 8px 24px ${alpha(baseProjectColor, 0.08)}`,
                }}
            >
                <div className="flex flex-wrap items-center justify-between gap-3 mb-2">
                    <div className="text-sm font-medium text-slate-800">
                        项目进度 <span className="font-bold">{projectProgressPercent}%</span>
                    </div>
                    <div className="flex flex-wrap gap-2 text-xs">
                        <span
                            className="px-2.5 py-1 rounded-full border text-slate-700"
                            style={{ backgroundColor: alpha(baseProjectColor, 0.10), borderColor: alpha(baseProjectColor, 0.20) }}
                        >
                            里程碑 {projectMilestoneDone}/{projectMilestoneTotal || 0}
                        </span>
                        <span
                            className="px-2.5 py-1 rounded-full border text-slate-700"
                            style={{ backgroundColor: alpha(baseProjectColor, 0.08), borderColor: alpha(baseProjectColor, 0.18) }}
                        >
                            任务 {projectTaskDone}/{projectTaskTotal || 0}
                        </span>
                        <span className="px-2.5 py-1 rounded-full border bg-white/80 text-slate-600 border-slate-200">
                            已解锁 {projectTaskUnlocked}/{projectTaskTotal || 0}
                        </span>
                    </div>
                </div>
                <div className="relative h-3 rounded-full overflow-hidden bg-slate-200/80">
                    <div
                        className="project-progress-fill h-full rounded-full"
                        style={{
                            width: `${Math.max(0, Math.min(projectProgressPercent, 100))}%`,
                            background: project.status === "SUCCESS"
                                ? "linear-gradient(90deg, #22c55e 0%, #16a34a 100%)"
                                : `linear-gradient(90deg, ${mix(baseProjectColor, "#ffffff", 0.05)} 0%, ${mix(baseProjectColor, "#111827", 0.08)} 100%)`,
                            boxShadow: projectProgressPercent > 0 ? `0 0 0 1px ${alpha(baseProjectColor, 0.18)} inset` : undefined,
                        }}
                    />
                    {projectProgressPercent > 0 && (
                        <div
                            className="absolute top-1/2 -translate-y-1/2 w-3 h-3 rounded-full border border-white"
                            style={{
                                left: `calc(${Math.max(0, Math.min(projectProgressPercent, 100))}% - 6px)`,
                                backgroundColor: project.status === "SUCCESS" ? "#16a34a" : baseProjectColor,
                                boxShadow: `0 2px 8px ${alpha(project.status === "SUCCESS" ? "#16a34a" : baseProjectColor, 0.35)}`,
                            }}
                        />
                    )}
                </div>
                <div className="mt-3 text-xs text-slate-600 flex flex-wrap items-center justify-between gap-2">
                    <div>
                        {project.status === "SUCCESS"
                            ? "✅ 已完成"
                            : currentUnlockedMilestone
                                ? `进行中：当前里程碑「${currentUnlockedMilestone.title}」`
                                : "进行中：等待里程碑解锁"}
                    </div>
                    {currentUnlockedMilestone?.target_date && project.status !== "SUCCESS" && (
                        <div>预计完成：{new Date(currentUnlockedMilestone.target_date).toLocaleDateString()}</div>
                    )}
                </div>
            </div>

            {/* Actions for PROPOSED */}
            {
                project.status === "PROPOSED" && (
                    <Alert className="bg-primary/5 border-primary/20">
                        <Play className="h-4 w-4 text-primary" />
                        <AlertTitle>项目待启动</AlertTitle>
                        <AlertDescription className="mt-2">
                            <p className="mb-4">此项目仍处于提案阶段。请确认里程碑是否合理，一旦启动，不可更改目标。</p>
                            <div className="flex gap-3">
                                <button
                                    onClick={handleConfirm}
                                    disabled={processing || isEditing}
                                    className="px-4 py-2 bg-primary text-primary-foreground rounded-md font-medium hover:bg-primary/90 disabled:opacity-50"
                                >
                                    {processing ? "处理中..." : "确认签署协议并启动"}
                                </button>
                                {!isEditing && (
                                    <button
                                        onClick={() => setIsEditing(true)}
                                        className="px-4 py-2 bg-card border border-input rounded-md font-medium hover:bg-accent hover:text-accent-foreground"
                                    >
                                        编辑内容
                                    </button>
                                )}
                            </div>
                        </AlertDescription>
                    </Alert>
                )
            }

            {project.status === "ACTIVE" && (
                <Alert className="bg-success/5 border-success/20">
                    <CheckCircle className="h-4 w-4 text-success" />
                    <AlertTitle>项目进行中</AlertTitle>
                    <AlertDescription className="mt-2">
                        <p className="mb-4">当全部里程碑完成后，可手动点击完成项目。</p>
                        <button
                            onClick={handleCompleteProject}
                            disabled={!allMilestonesAchieved || processing}
                            className={`px-4 py-2 rounded-md font-medium ${allMilestonesAchieved ? "bg-success text-success-foreground" : "bg-muted text-muted-foreground cursor-not-allowed"}`}
                        >
                            完成项目
                        </button>
                    </AlertDescription>
                </Alert>
            )}

            {/* AI Analysis (If available) */}
            {
                project.ai_analysis && (
                    <div className="bg-card border border-border rounded-lg p-6">
                        <h2 className="font-medium mb-2">AI 可行性分析</h2>
                        <p className="text-muted-foreground whitespace-pre-wrap">{project.ai_analysis}</p>
                    </div>
                )
            }

            {/* Details */}
            <div className="bg-card border border-border rounded-lg p-6">
                <div className="flex items-center justify-between mb-4">
                    <h2 className="font-medium">项目详情</h2>
                    <button
                        onClick={() => setIsEditing(true)}
                        className="px-3 py-1 text-sm bg-card border border-input rounded-md font-medium hover:bg-accent hover:text-accent-foreground flex items-center gap-1"
                    >
                        <Edit2 className="w-3.5 h-3.5" />
                        编辑
                    </button>
                </div>

                <div className="space-y-4">
                    <div>
                        <span className="text-sm text-muted-foreground">描述</span>
                        <p className="mt-1 whitespace-pre-wrap">{project.description}</p>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                            <span className="text-sm text-muted-foreground">成功标准</span>
                            <p className="mt-1">{project.success_criteria || "-"}</p>
                        </div>
                        <div>
                            <span className="text-sm text-muted-foreground">失败惩罚</span>
                            <p className="mt-1 text-red-500">{project.failure_criteria || "-"}</p>
                        </div>
                    </div>
                    {/* Color Display */}
                    {project.color && (
                        <div>
                            <span className="text-sm text-muted-foreground">项目颜色</span>
                            <div className="mt-1 flex items-center gap-2">
                                <div className="w-4 h-4 rounded-full" style={{ backgroundColor: project.color }}></div>
                                <span className="text-sm text-slate-600">{project.color}</span>
                            </div>
                        </div>
                    )}
                </div>
            </div>

            <EditProjectModal
                isOpen={isEditing}
                onClose={() => setIsEditing(false)}
                project={project}
                onSuccess={() => reloadProject()}
            />

            {/* Milestones */}
            <div className="space-y-4">
                <div className="flex items-center justify-between">
                    <h2 className="font-semibold text-lg flex items-center gap-2">
                        <Flag className="w-5 h-5" />
                        里程碑计划
                    </h2>
                    {(project.status === "PROPOSED" || true) && ( // Allow adding even if active (user request)
                        <button
                            onClick={() => {
                                setMilestoneSort(prev => prev === 'asc' ? 'desc' : 'asc');
                            }}
                            className="text-xs text-muted-foreground hover:text-foreground mr-2"
                        >
                            {/* Sort logic could go here, or just Add button */}
                        </button>
                    )}
                    <button
                        onClick={() => setIsAddingMilestone(true)}
                        className="text-sm px-3 py-1 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 flex items-center gap-1"
                    >
                        <Plus className="w-4 h-4" />
                        添加里程碑
                    </button>
                </div>

                {isAddingMilestone && (
                    <div className="p-4 border border-primary/20 bg-primary/5 rounded-lg mb-4">
                        <h3 className="font-medium mb-3">新里程碑</h3>
                        <MilestoneForm
                            initialData={{ title: "", description: "", is_critical: false }}
                            onSave={async (data) => {
                                await handleAddMilestone(data);
                                setIsAddingMilestone(false);
                            }}
                            onCancel={() => setIsAddingMilestone(false)}
                            isProcessing={processing}
                        />
                    </div>
                )}

                <div className="grid gap-4">

{orderedMilestones.map((milestone, index) => {
    const visual = getMilestoneVisual(milestone, index);
    const metrics = getMilestoneMetrics(milestone.id);
    const milestoneTasks = metrics.list;

    return (
        <div
            key={milestone.id}
            className={`p-4 rounded-2xl border milestone-card-hover ${visual.isCurrent ? "milestone-current-glow" : ""}`}
            style={visual.cardStyle}
        >
            {editingMilestoneId === milestone.id ? (
                <MilestoneForm
                    initialData={milestone}
                    onSave={async (data) => {
                        await handleUpdateMilestone(milestone.id, data);
                        setEditingMilestoneId(null);
                    }}
                    onCancel={() => setEditingMilestoneId(null)}
                    isProcessing={processing}
                />
            ) : (
                <div className="flex items-start justify-between gap-3">
                    <div className="flex items-start gap-3 flex-1 min-w-0">
                        <div
                            className="mt-1 w-1 self-stretch rounded-full min-h-[32px]"
                            style={{ backgroundColor: visual.isDone ? "#22c55e" : (visual.isLocked ? "#D1D5DB" : visual.accent) }}
                        />
                        <div
                            className="mt-1 flex items-center justify-center w-7 h-7 rounded-full text-xs font-bold border shrink-0"
                            style={{
                                backgroundColor: visual.isDone ? alpha("#22c55e", 0.12) : (visual.isLocked ? "#F1F5F9" : alpha(visual.accent, 0.12)),
                                color: visual.isDone ? "#15803d" : (visual.isLocked ? "#64748b" : visual.accent),
                                borderColor: visual.isDone ? alpha("#22c55e", 0.22) : (visual.isLocked ? "#E2E8F0" : alpha(visual.accent, 0.25)),
                            }}
                        >
                            {index + 1}
                        </div>
                        <div className="flex-1 min-w-0">
                            <h3 className={`font-medium flex flex-wrap items-center gap-2 ${milestone.status === "ACHIEVED" ? "line-through text-muted-foreground" : ""}`}>
                                {milestone.title}
                                {milestone.is_critical && <span className="text-xs bg-red-100 text-red-600 px-1.5 py-0.5 rounded">关键</span>}
                                {visual.isDone ? (
                                    <span className="text-xs px-1.5 py-0.5 rounded inline-flex items-center gap-1 border bg-green-50 text-green-700 border-green-200">
                                        <CheckCircle className="w-3 h-3" />
                                        已完成
                                    </span>
                                ) : visual.isLocked ? (
                                    <span className="text-xs bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded inline-flex items-center gap-1 border border-slate-200">
                                        <Lock className="w-3 h-3" />
                                        未解锁
                                    </span>
                                ) : (
                                    <span
                                        className="text-xs px-1.5 py-0.5 rounded inline-flex items-center gap-1 border"
                                        style={{
                                            color: visual.accent,
                                            borderColor: alpha(visual.accent, 0.25),
                                            backgroundColor: alpha(visual.accent, 0.08),
                                        }}
                                    >
                                        {visual.isCurrent ? "进行中" : "已解锁"}
                                    </span>
                                )}
                            </h3>
                            <p className={`text-sm mt-1 ${visual.isLocked ? "text-slate-500" : "text-muted-foreground"}`}>{milestone.description}</p>
                            <div className="mt-2 space-y-1">
                                <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
                                    <span>已完成 {metrics.done}/{metrics.total || 0}</span>
                                    {milestone.target_date && milestone.is_unlocked !== false && (
                                        <span>截止：{new Date(milestone.target_date).toLocaleDateString()}</span>
                                    )}
                                </div>
                                <div
                                    className="relative h-2.5 rounded-full overflow-hidden"
                                    style={{ backgroundColor: visual.isLocked ? "#E5E7EB" : alpha(visual.accent, 0.14) }}
                                >
                                    <div
                                        className="milestone-progress-fill h-full rounded-full"
                                        style={{
                                            width: `${Math.max(0, Math.min(metrics.percent, 100))}%`,
                                            background: visual.isLocked
                                                ? "#CBD5E1"
                                                : (visual.isDone
                                                    ? "linear-gradient(90deg, #22c55e 0%, #16a34a 100%)"
                                                    : `linear-gradient(90deg, ${alpha(visual.accent, 0.82)} 0%, ${visual.accent} 100%)`),
                                            boxShadow: visual.isDone ? "0 0 14px rgba(34,197,94,0.18)" : undefined,
                                        }}
                                    />
                                </div>
                            </div>
                            {milestone.target_date && milestone.is_unlocked !== false && (
                                <p className="text-xs text-muted-foreground mt-1 flex items-center gap-1">
                                    <Calendar className="w-3 h-3" />
                                    目标日期: {new Date(milestone.target_date).toLocaleDateString()}
                                </p>
                            )}
                            {milestoneTasks.length ? (
                                <div className="mt-3 space-y-2">
                                    <div className="text-xs text-muted-foreground">里程碑任务（{milestoneTasks.length}）</div>
                                    {milestoneTasks.map((task) => {
                                        const taskLocked = isTaskEffectivelyLocked(task);
                                        return (
                                            <div
                                                key={task.id}
                                                className="rounded-xl border px-3 py-2"
                                                style={{
                                                    backgroundColor: taskLocked ? "#F8FAFC" : alpha(visual.accent, 0.05),
                                                    borderColor: taskLocked ? "#E5E7EB" : alpha(visual.accent, 0.14),
                                                }}
                                            >
                                                <div className="flex items-center justify-between gap-2">
                                                    <div className={`text-sm font-medium truncate ${taskLocked ? "text-slate-500" : ""}`}>{task.title}</div>
                                                    {taskLocked ? (
                                                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-sm text-xs font-medium border bg-slate-100 text-slate-600 border-slate-200">
                                                            未解锁
                                                        </span>
                                                    ) : (
                                                        <StatusBadge status={getTaskVisualStatus(task)} type="task" />
                                                    )}
                                                </div>
                                                {task.description && (
                                                    <div className={`text-xs mt-1 line-clamp-2 ${taskLocked ? "text-slate-400" : "text-muted-foreground"}`}>
                                                        {task.description}
                                                    </div>
                                                )}
                                                {task.deadline && !shouldHideTaskSchedule(task) && (
                                                    <div className="text-xs text-muted-foreground mt-1">
                                                        截止：{new Date(task.deadline).toLocaleString()}
                                                    </div>
                                                )}
                                                {shouldHideTaskSchedule(task) && (
                                                    <div className="text-xs text-slate-400 mt-1">解锁后自动排期</div>
                                                )}
                                                <div className="mt-2 flex items-center gap-2">
                                                    {project.status === "PROPOSED" && (
                                                        <button
                                                            onClick={() => setEditingTask(task)}
                                                            className="text-xs px-2 py-1 border border-border rounded hover:bg-muted"
                                                        >
                                                            编辑任务
                                                        </button>
                                                    )}
                                                    <Link
                                                        href={`/tasks/${task.id}`}
                                                        className="text-xs px-2 py-1 border border-border rounded hover:bg-muted"
                                                    >
                                                        查看任务
                                                    </Link>
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>
                            ) : null}
                        </div>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                        {project.status === "PROPOSED" && (
                            <button
                                onClick={() => {
                                    setCreateTaskMilestoneId(milestone.id);
                                    setIsAddingTask(true);
                                }}
                                className="text-xs px-2 py-1 border border-border rounded hover:bg-muted"
                                title="添加里程碑任务"
                            >
                                + 任务
                            </button>
                        )}
                        {project.status === "ACTIVE" && milestone.status !== "ACHIEVED" && milestoneTasks.length === 0 && (
                            <button
                                className="text-sm px-2 py-1 border border-border rounded hover:bg-muted"
                                onClick={() => markAchieved(milestone.id)}
                                title="标记为达成"
                            >
                                <CheckCircle className="w-4 h-4 text-muted-foreground hover:text-success" />
                            </button>
                        )}
                        <button
                            onClick={() => setEditingMilestoneId(milestone.id)}
                            className="p-1 text-muted-foreground hover:text-foreground"
                            title="编辑"
                        >
                            <Edit2 className="w-4 h-4" />
                        </button>
                        <button
                            onClick={() => handleDeleteMilestone(milestone.id)}
                            className="p-1 text-muted-foreground hover:text-red-500"
                            title="删除"
                        >
                            <Trash2 className="w-4 h-4" />
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
})}

                    {orderedMilestones.length === 0 && !isAddingMilestone && (
                        <div className="text-center py-8 text-muted-foreground">
                            暂无里程碑
                        </div>
                    )}
                </div>
            </div>

            {/* Long Tasks */}
            <div className="space-y-4">
                <div className="flex items-center justify-between">
                    <h2 className="font-semibold text-lg flex items-center gap-2">
                        <ListTodo className="w-5 h-5" />
                        长期任务
                    </h2>
                </div>

                {longTaskTemplates && longTaskTemplates.length > 0 ? (
                    <div className="grid gap-3">
                        {longTaskTemplates.map((t) => (
                            <div
                                key={t.id}
                                className="p-4 rounded-lg border bg-card flex items-start justify-between"
                            >
                                <div className="flex-1">
                                    <div className="font-medium">{t.title}</div>
                                    <div className="text-xs text-muted-foreground mt-1 flex flex-wrap gap-2">
                                        <span className="bg-slate-100 px-2 py-0.5 rounded">
                                            {formatLongTaskFrequency(t)}
                                        </span>
                                        <span className="bg-slate-100 px-2 py-0.5 rounded">
                                            总周期 {t.total_cycle_days} 天
                                        </span>
                                    </div>
                                </div>
                                <div className="flex items-center gap-2">
                                    {project.status === "PROPOSED" && (
                                        <button
                                            onClick={() => setEditingLongTask(t)}
                                            className="text-xs px-2 py-1 border border-border rounded hover:bg-muted"
                                        >
                                            编辑
                                        </button>
                                    )}
                                    <button
                                        onClick={() => handleHideLongTask(t.id)}
                                        className="text-xs px-2 py-1 border border-border rounded hover:bg-muted"
                                    >
                                        隐藏
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                ) : (
                    <div className="text-center py-8 text-muted-foreground border border-dashed rounded-lg">
                        暂无长期任务
                    </div>
                )}
            </div>

            {/* Related Tasks */}
            <div className="space-y-4">
                <div className="flex items-center justify-between">
                    <h2 className="font-semibold text-lg flex items-center gap-2">
                        <ListTodo className="w-5 h-5" />
                        相关任务
                    </h2>
                    <div className="flex items-center gap-2">
                        <button
                            onClick={() => setIsAddingLongTask(true)}
                            className="text-sm px-3 py-1 bg-card border border-input rounded-md hover:bg-accent hover:text-accent-foreground flex items-center gap-1"
                        >
                            <Plus className="w-4 h-4" />
                            添加长期任务
                        </button>
                        <button
                            onClick={() => {
                                setCreateTaskMilestoneId(null);
                                setIsAddingTask(true);
                            }}
                            className="text-sm px-3 py-1 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 flex items-center gap-1"
                        >
                            <Plus className="w-4 h-4" />
                            添加相关任务
                        </button>
                    </div>
                </div>

                {allProjectTasks.length > 0 ? (
                    <div className="grid gap-3">
                        {allProjectTasks.map((task) => (
                            <div
                                key={task.id}
                                className="p-4 rounded-lg border bg-card hover:bg-muted/50 transition-colors"
                            >
                                <div className="flex items-start justify-between">
                                    <div className="flex-1">
                                        <h3 className="font-medium">{task.title}</h3>
                                        {task.description && (
                                            <p className="text-sm text-muted-foreground mt-1 line-clamp-2">
                                                {task.description}
                                            </p>
                                        )}
                                        {task.milestone_id && milestoneLookup[task.milestone_id] && (
                                            <p className="text-xs text-muted-foreground mt-2">
                                                所属里程碑：{(milestoneLookup[task.milestone_id].order_index ?? 0) + 1} · {milestoneLookup[task.milestone_id].title}
                                            </p>
                                        )}
                                        {task.deadline && !shouldHideTaskSchedule(task) && (
                                            <p className="text-xs text-muted-foreground mt-2">
                                                截止：{new Date(task.deadline).toLocaleString()}
                                            </p>
                                        )}
                                        {shouldHideTaskSchedule(task) && (
                                            <p className="text-xs text-slate-400 mt-2">解锁后自动排期</p>
                                        )}
                                    </div>
                                    <div className="flex items-center gap-2">
                                        {isTaskEffectivelyLocked(task) ? (
                                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-sm text-xs font-medium border bg-slate-100 text-slate-600 border-slate-200">
                                                未解锁
                                            </span>
                                        ) : (
                                            <StatusBadge status={getTaskVisualStatus(task)} type="task" />
                                        )}
                                        {project.status === "PROPOSED" && (
                                            <button
                                                onClick={() => setEditingTask(task)}
                                                className="p-1 text-muted-foreground hover:text-foreground"
                                                title="编辑"
                                            >
                                                <Edit2 className="w-4 h-4" />
                                            </button>
                                        )}
                                        <Link
                                            href={`/tasks/${task.id}`}
                                            className="p-1 text-muted-foreground hover:text-foreground"
                                            title="查看"
                                        >
                                            <ArrowLeft className="w-4 h-4 rotate-180" />
                                        </Link>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                ) : (
                    <div className="text-center py-8 text-muted-foreground border border-dashed rounded-lg">
                        暂无相关任务
                    </div>
                )}
            </div>

            <CreateTaskModal
                isOpen={isAddingTask}
                onClose={() => {
                    setIsAddingTask(false);
                    setCreateTaskMilestoneId(null);
                }}
                defaultProjectId={id}
                defaultMilestoneId={createTaskMilestoneId}
                milestones={orderedMilestones}
                onSuccess={() => reloadTasks()}
            />

            <CreateLongTaskModal
                isOpen={isAddingLongTask}
                onClose={() => setIsAddingLongTask(false)}
                projectId={id}
                onSuccess={() => reloadLongTaskTemplates()}
            />

            {editingTask && (
                <EditTaskModal
                    task={editingTask}
                    onClose={() => setEditingTask(null)}
                    onSave={handleUpdateTask}
                    milestones={orderedMilestones}
                />
            )}

            {editingLongTask && (
                <EditLongTaskModal
                    template={editingLongTask}
                    onClose={() => setEditingLongTask(null)}
                    onSave={handleUpdateLongTaskTemplate}
                />
            )}
        </div >
    );
}

function MilestoneForm({ initialData, onSave, onCancel, isProcessing }: MilestoneFormProps) {
    const [form, setForm] = useState({
        title: initialData.title || "",
        description: initialData.description || "",
        is_critical: initialData.is_critical || false,
        target_date: initialData.target_date ? new Date(initialData.target_date).toISOString().split('T')[0] : ""
    });

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        onSave(form);
    };

    return (
        <form onSubmit={handleSubmit} className="space-y-3">
            <div>
                <input
                    type="text"
                    required
                    placeholder="里程碑标题"
                    value={form.title}
                    onChange={e => setForm({ ...form, title: e.target.value })}
                    className="w-full p-2 border rounded-md text-sm"
                />
            </div>
            <div>
                <textarea
                    placeholder="描述 (可选)"
                    value={form.description}
                    onChange={e => setForm({ ...form, description: e.target.value })}
                    className="w-full p-2 border rounded-md text-sm min-h-[60px]"
                />
            </div>
            <div className="flex gap-4">
                <div className="flex items-center gap-2">
                    <input
                        type="date"
                        value={form.target_date}
                        onChange={e => setForm({ ...form, target_date: e.target.value })}
                        className="p-1 border rounded text-sm"
                    />
                    <span className="text-xs text-muted-foreground">目标日期</span>
                </div>
                <label className="flex items-center gap-2 text-sm cursor-pointer">
                    <input
                        type="checkbox"
                        checked={form.is_critical}
                        onChange={e => setForm({ ...form, is_critical: e.target.checked })}
                    />
                    关键里程碑
                </label>
            </div>
            <div className="flex justify-end gap-2 pt-2">
                <button
                    type="button"
                    onClick={onCancel}
                    disabled={isProcessing}
                    className="px-3 py-1 text-sm bg-muted text-muted-foreground rounded hover:bg-muted/80"
                >
                    取消
                </button>
                <button
                    type="submit"
                    disabled={isProcessing}
                    className="px-3 py-1 text-sm bg-primary text-primary-foreground rounded hover:bg-primary/90"
                >
                    保存
                </button>
            </div>
        </form>
    );
}
