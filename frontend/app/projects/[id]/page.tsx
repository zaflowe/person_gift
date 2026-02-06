"use client";

import { RequireAuth } from "@/lib/auth-context";
import { AppLayout } from "@/components/layout/app-layout";
import { StatusBadge } from "@/components/ui/status-badge";
import { apiPost, fetcher, apiPatch, apiDelete } from "@/lib/utils";
import { Project, Milestone, Task } from "@/types";
import { ArrowLeft, CheckCircle, Flag, Lock, Play, Target, ListTodo, Edit2, Trash2, Plus, Calendar } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import useSWR, { mutate } from "swr";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { useToast } from "@/components/ui/toast";
import { CreateTaskModal } from "@/components/modals/create-task-modal";
import { CreateLongTaskModal } from "@/components/modals/create-long-task-modal";
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
    const { data: tasks } = useSWR<Task[]>(id ? `/api/tasks?project_id=${id}` : null, fetcher);
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
    const [milestoneSort, setMilestoneSort] = useState<'asc' | 'desc'>('asc'); // Not used yet but requested
    const [showColorPicker, setShowColorPicker] = useState(false);
    const [editForm, setEditForm] = useState({
        description: "",
        success_criteria: "",
        failure_criteria: ""
    });

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

    return (
        <div className="max-w-4xl mx-auto p-6 space-y-6">
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
                    {milestones?.map((milestone, index) => (
                        <div
                            key={milestone.id}
                            className={`p-4 rounded-lg border ${milestone.status === "ACHIEVED" ? "bg-success/5 border-success/20" : "bg-card border-border"}`}
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
                                <div className="flex items-start justify-between">
                                    <div className="flex items-start gap-4 flex-1">
                                        <div className={`mt-1 flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold ${milestone.status === "ACHIEVED" ? "bg-success text-success-foreground" : "bg-muted text-muted-foreground"}`}>
                                            {index + 1}
                                        </div>
                                        <div className="flex-1">
                                            <h3 className={`font-medium flex items-center gap-2 ${milestone.status === "ACHIEVED" ? "line-through text-muted-foreground" : ""}`}>
                                                {milestone.title}
                                                {milestone.is_critical && <span className="text-xs bg-red-100 text-red-600 px-1.5 py-0.5 rounded">关键</span>}
                                            </h3>
                                            <p className="text-sm text-muted-foreground mt-1">{milestone.description}</p>
                                            {milestone.target_date && (
                                                <p className="text-xs text-muted-foreground mt-1 flex items-center gap-1">
                                                    <Calendar className="w-3 h-3" />
                                                    目标日期: {new Date(milestone.target_date).toLocaleDateString()}
                                                </p>
                                            )}
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        {project.status === "ACTIVE" && milestone.status !== "ACHIEVED" && (
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
                    ))}

                    {(!milestones || milestones.length === 0) && !isAddingMilestone && (
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
                            onClick={() => setIsAddingTask(true)}
                            className="text-sm px-3 py-1 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 flex items-center gap-1"
                        >
                            <Plus className="w-4 h-4" />
                            添加相关任务
                        </button>
                    </div>
                </div>

                {tasks && tasks.length > 0 ? (
                    <div className="grid gap-3">
                        {tasks.map((task) => (
                            <Link
                                key={task.id}
                                href={`/tasks/${task.id}`}
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
                                        {task.deadline && (
                                            <p className="text-xs text-muted-foreground mt-2">
                                                截止：{new Date(task.deadline).toLocaleString()}
                                            </p>
                                        )}
                                    </div>
                                    <StatusBadge status={task.status} type="task" />
                                </div>
                            </Link>
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
                onClose={() => setIsAddingTask(false)}
                defaultProjectId={id}
            />

            <CreateLongTaskModal
                isOpen={isAddingLongTask}
                onClose={() => setIsAddingLongTask(false)}
                projectId={id}
                onSuccess={() => reloadLongTaskTemplates()}
            />
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
