"use client";

import { useEffect, useMemo, useState } from "react";
import { apiPost, fetcher } from "@/lib/utils";
import { X } from "lucide-react";
import { mutate } from "swr";
import useSWR from "swr";
import { Milestone, Project } from "@/types";

interface CreateTaskModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSuccess?: () => void;
    defaultProjectId?: string;
    defaultMilestoneId?: string | null;
    milestones?: Milestone[];
}

export function CreateTaskModal({
    isOpen,
    onClose,
    onSuccess,
    defaultProjectId,
    defaultMilestoneId = null,
    milestones,
}: CreateTaskModalProps) {
    const [loading, setLoading] = useState(false);
    const [formData, setFormData] = useState({
        title: "",
        description: "",
        deadline: "",
        scheduled_time: "",
        evidence_type: "none",
        evidence_criteria: "",
        project_id: defaultProjectId || "",
        milestone_id: defaultMilestoneId || "",
    });

    useEffect(() => {
        if (!isOpen) return;
        setFormData(prev => ({
            ...prev,
            project_id: defaultProjectId || prev.project_id || "",
            milestone_id: defaultMilestoneId || "",
        }));
    }, [isOpen, defaultProjectId, defaultMilestoneId]);

    // Fetch projects for selection
    const { data: projects } = useSWR<Project[]>("/api/projects", fetcher);
    const selectedProjectId = formData.project_id || defaultProjectId || "";
    const { data: fetchedMilestones } = useSWR<Milestone[]>(
        !milestones && selectedProjectId ? `/api/projects/${selectedProjectId}/milestones` : null,
        fetcher
    );
    const availableMilestones = useMemo(
        () => (milestones || fetchedMilestones || []).slice().sort((a, b) => (a.order_index ?? 0) - (b.order_index ?? 0)),
        [milestones, fetchedMilestones]
    );

    // Auto-parse tags from description
    const tags = formData.description.match(/#[\w\u4e00-\u9fa5]+/g) || [];
    const cleanDescription = formData.description.replace(/#[\w\u4e00-\u9fa5]+/g, "").trim();

    if (!isOpen) return null;

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        try {
            // Process tags: remove # and deduplicate
            const processedTags = Array.from(new Set(tags.map(t => t.substring(1))));

            const payload = {
                title: formData.title,
                description: cleanDescription, // Store polished description
                tags: processedTags,
                deadline: formData.deadline ? new Date(formData.deadline).toISOString() : null,
                scheduled_time: formData.scheduled_time ? new Date(formData.scheduled_time).toISOString() : null,
                evidence_type: formData.evidence_type,
                evidence_criteria: formData.evidence_criteria,
                project_id: formData.project_id || null,
                milestone_id: formData.milestone_id || null,
            };

            await apiPost("/api/tasks", payload);
            mutate("/api/tasks"); // Refresh task list
            onSuccess?.();
            onClose();
            // Reset form
            setFormData({
                title: "",
                description: "",
                deadline: "",
                scheduled_time: "",
                evidence_type: "none",
                evidence_criteria: "",
                project_id: defaultProjectId || "",
                milestone_id: defaultMilestoneId || "",
            });
        } catch (err: any) {
            alert(err.message || "创建失败");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
            <div className="bg-white border border-slate-200 rounded-xl shadow-xl w-full max-w-lg flex flex-col max-h-[90vh] overflow-hidden">
                <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
                    <h2 className="text-lg font-bold text-slate-800">新增任务</h2>
                    <button onClick={onClose} className="text-slate-400 hover:text-slate-600 transition-colors">
                        <X className="w-5 h-5" />
                    </button>
                </div>

                <form onSubmit={handleSubmit} className="p-6 space-y-6 overflow-y-auto">
                    {/* Title */}
                    <div>
                        <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">任务标题</label>
                        <input
                            type="text"
                            required
                            autoFocus
                            value={formData.title}
                            onChange={e => setFormData({ ...formData, title: e.target.value })}
                            className="w-full text-base font-semibold placeholder:text-slate-300 border border-slate-200 rounded-lg px-3 py-2 focus:border-indigo-500 focus:outline-none transition-colors"
                            placeholder="例如：完成微积分第三章复习"
                        />
                    </div>

                    {/* Description & Tags */}
                    <div>
                        <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">描述 (可选)</label>
                        <div className="space-y-2">
                            <textarea
                                value={formData.description}
                                onChange={e => setFormData({ ...formData, description: e.target.value })}
                                className="w-full min-h-[80px] text-sm border border-slate-200 rounded-lg px-3 py-2 resize-none focus:border-indigo-500 focus:outline-none placeholder:text-slate-300"
                                placeholder="输入 #标签 可以自动识别..."
                            />
                            {tags.length > 0 && (
                                <div className="flex flex-wrap gap-2">
                                    {tags.map((tag, i) => (
                                        <span key={i} className="text-xs bg-indigo-50 text-indigo-600 px-2 py-1 rounded-full font-medium border border-indigo-100">
                                            {tag}
                                        </span>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>

                    <div className="h-px bg-slate-100" />

                    {/* Time Config (Single Row) */}
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">开始时间</label>
                            <input
                                type="datetime-local"
                                value={formData.scheduled_time}
                                onChange={e => {
                                    const start = e.target.value;
                                    // Auto-set deadline to start + 1h if empty
                                    if (start && !formData.deadline) {
                                        const d = new Date(start);
                                        d.setHours(d.getHours() + 1);
                                        const localIso = new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
                                        setFormData(prev => ({ ...prev, scheduled_time: start, deadline: localIso }));
                                    } else {
                                        setFormData({ ...formData, scheduled_time: start });
                                    }
                                }}
                                className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none transition-colors"
                            />
                        </div>
                        <div>
                            <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">截止时间</label>
                            <input
                                type="datetime-local"
                                value={formData.deadline}
                                onChange={e => setFormData({ ...formData, deadline: e.target.value })}
                                className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none transition-colors"
                            />
                        </div>
                    </div>

                    {/* Project Selection */}
                    <div>
                        <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">所属项目 (可选)</label>
                        <select
                            value={formData.project_id}
                            onChange={e => setFormData({ ...formData, project_id: e.target.value, milestone_id: "" })}
                            className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none transition-colors appearance-none"
                        >
                            <option value="">📁 无项目</option>
                            {projects?.map((p: Project) => (
                                <option key={p.id} value={p.id}>📁 {p.title}</option>
                            ))}
                        </select>
                    </div>

                    {formData.project_id && (
                        <div>
                            <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">所属里程碑 (可选)</label>
                            <select
                                value={formData.milestone_id}
                                onChange={e => setFormData({ ...formData, milestone_id: e.target.value })}
                                className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none transition-colors appearance-none"
                            >
                                <option value="">无（放在相关任务）</option>
                                {availableMilestones.map((m) => (
                                    <option key={m.id} value={m.id}>
                                        里程碑 {(m.order_index ?? 0) + 1} · {m.title}
                                    </option>
                                ))}
                            </select>
                        </div>
                    )}

                    {/* Evidence Type */}
                    <div>
                        <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">验收方式</label>
                        <select
                            value={formData.evidence_type}
                            onChange={e => setFormData({ ...formData, evidence_type: e.target.value })}
                            className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none transition-colors appearance-none"
                        >
                            <option value="none">自觉完成 (无强制)</option>
                            <option value="image">拍照打卡 (AI 审核)</option>
                            <option value="text">文字总结</option>
                            <option value="number">数值记录</option>
                        </select>
                    </div>

                    {formData.evidence_type !== "none" && (
                        <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
                            <textarea
                                value={formData.evidence_criteria}
                                onChange={e => setFormData({ ...formData, evidence_criteria: e.target.value })}
                                className="w-full bg-transparent border-none text-xs focus:ring-0 p-0 placeholder:text-slate-400"
                                placeholder="输入 AI 审核标准 (Prompts)..."
                                rows={2}
                            />
                        </div>
                    )}

                    <div className="pt-2">
                        <button
                            type="submit"
                            disabled={loading}
                            className="w-full py-2.5 bg-indigo-600 text-white hover:bg-indigo-700 active:bg-indigo-800 rounded-lg font-medium shadow-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                        >
                            {loading ? "处理中..." : "创建任务"}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
