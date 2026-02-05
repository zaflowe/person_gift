"use client";

import { useState } from "react";
import { apiPost } from "@/lib/utils";
import { X, Plus, Trash } from "lucide-react";
import { mutate } from "swr";

interface CreateProjectModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSuccess?: () => void;
}

export function CreateProjectModal({ isOpen, onClose, onSuccess }: CreateProjectModalProps) {
    const [loading, setLoading] = useState(false);
    const [step, setStep] = useState(1);
    const [formData, setFormData] = useState({
        title: "",
        description: "",
        success_criteria: "",
        failure_criteria: "",
        deadline: "",
        color: ""
    });
    const [milestones, setMilestones] = useState<{ title: string, description: string, is_critical: boolean }[]>([]);
    const [aiAnalysisInProgess, setAiAnalysisInProgress] = useState(false);

    if (!isOpen) return null;

    const addMilestone = () => {
        setMilestones([...milestones, { title: "", description: "", is_critical: false }]);
    };

    const updateMilestone = (index: number, field: string, value: any) => {
        const newMilestones = [...milestones];
        // @ts-ignore
        newMilestones[index][field] = value;
        setMilestones(newMilestones);
    };

    const removeMilestone = (index: number) => {
        const newMilestones = [...milestones];
        newMilestones.splice(index, 1);
        setMilestones(newMilestones);
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        try {
            // Create Project
            const projectPayload = {
                ...formData,
                deadline: formData.deadline ? new Date(formData.deadline).toISOString() : null,
            };

            const projectRes = await apiPost<{ id: string }>("/api/projects", projectPayload);

            // Create Milestones
            if (milestones.length > 0) {
                // Assuming there is a bulk create or loop. For now, loop.
                // Actually, usually project creation might include milestones, but our API probably expects separate calls
                // Let's create them one by one
                for (const m of milestones) {
                    await apiPost(`/api/projects/${projectRes.id}/milestones`, m);
                }
            }

            mutate("/api/projects");
            onSuccess?.();
            onClose();

            // Reset
            setFormData({
                title: "",
                description: "",
                success_criteria: "",
                failure_criteria: "",
                deadline: "",
                color: ""
            });
            setMilestones([]);
            setStep(1);
        } catch (err: any) {
            alert(err.message || "创建失败");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
            <div className="bg-card border border-border rounded-lg shadow-lg w-full max-w-2xl flex flex-col max-h-[90vh]">
                <div className="flex items-center justify-between p-4 border-b border-border">
                    <h2 className="text-lg font-semibold">新增项目 (Step {step}/2)</h2>
                    <button onClick={onClose} className="text-muted-foreground hover:text-foreground">
                        <X className="w-5 h-5" />
                    </button>
                </div>

                <form onSubmit={handleSubmit} className="p-4 space-y-4 overflow-y-auto flex-1">
                    {step === 1 && (
                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium mb-1">项目名称</label>
                                <input
                                    type="text"
                                    required
                                    value={formData.title}
                                    onChange={e => setFormData({ ...formData, title: e.target.value })}
                                    className="w-full p-2 bg-background border border-border rounded-md"
                                    placeholder="例如：学习 Rust 语言"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium mb-1">目标描述</label>
                                <textarea
                                    required
                                    value={formData.description}
                                    onChange={e => setFormData({ ...formData, description: e.target.value })}
                                    className="w-full p-2 bg-background border border-border rounded-md h-20"
                                    placeholder="为什么要开启这个项目？"
                                />
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm font-medium mb-1">成功标准</label>
                                    <textarea
                                        value={formData.success_criteria}
                                        onChange={e => setFormData({ ...formData, success_criteria: e.target.value })}
                                        className="w-full p-2 bg-background border border-border rounded-md h-20"
                                        placeholder="如何定义成功？"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium mb-1">失败惩罚</label>
                                    <textarea
                                        value={formData.failure_criteria}
                                        onChange={e => setFormData({ ...formData, failure_criteria: e.target.value })}
                                        className="w-full p-2 bg-background border border-border rounded-md h-20"
                                        placeholder="如果失败，会有什么后果？"
                                    />
                                </div>
                            </div>
                            <div>
                                <label className="block text-sm font-medium mb-1">截止日期 (可选)</label>
                                <input
                                    type="datetime-local"
                                    value={formData.deadline}
                                    onChange={e => setFormData({ ...formData, deadline: e.target.value })}
                                    className="w-full p-2 bg-background border border-border rounded-md"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium mb-2">项目颜色 (可选)</label>
                                <div className="flex flex-wrap gap-2">
                                    {[
                                        "#ef4444", "#f97316", "#f59e0b", "#22c55e", "#14b8a6",
                                        "#3b82f6", "#6366f1", "#8b5cf6", "#d946ef", "#f43f5e"
                                    ].map((color) => (
                                        <button
                                            key={color}
                                            type="button"
                                            onClick={() => setFormData({ ...formData, color: formData.color === color ? "" : color })}
                                            className={`w-6 h-6 rounded-full border-2 transition-all ${formData.color === color ? 'border-slate-800 scale-110' : 'border-transparent hover:scale-105'}`}
                                            style={{ backgroundColor: color }}
                                            title={color}
                                        />
                                    ))}
                                    <button
                                        type="button"
                                        onClick={() => setFormData({ ...formData, color: "" })}
                                        className={`w-6 h-6 rounded-full border-2 flex items-center justify-center text-[10px] text-slate-500 bg-slate-100 ${!formData.color ? 'border-slate-800' : 'border-transparent'}`}
                                        title="默认"
                                    >
                                        Auto
                                    </button>
                                </div>
                            </div>
                        </div>
                    )}

                    {step === 2 && (
                        <div className="space-y-4">
                            <div className="flex items-center justify-between">
                                <label className="block text-sm font-medium">规划里程碑</label>
                                <button
                                    type="button"
                                    onClick={addMilestone}
                                    className="text-xs flex items-center gap-1 text-primary hover:underline"
                                >
                                    <Plus className="w-3 h-3" /> 添加里程碑
                                </button>
                            </div>

                            {milestones.length === 0 && <div className="text-center text-sm text-muted-foreground py-4">暂无里程碑</div>}

                            <div className="space-y-2">
                                {milestones.map((m, idx) => (
                                    <div key={idx} className="p-3 bg-muted/30 rounded border border-border relative group">
                                        <button
                                            type="button"
                                            onClick={() => removeMilestone(idx)}
                                            className="absolute right-2 top-2 text-muted-foreground hover:text-destructive opacity-0 group-hover:opacity-100 transition-opacity"
                                        >
                                            <Trash className="w-4 h-4" />
                                        </button>
                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-2 pr-6">
                                            <input
                                                type="text"
                                                placeholder="里程碑标题"
                                                value={m.title}
                                                onChange={e => updateMilestone(idx, "title", e.target.value)}
                                                className="p-1.5 bg-background border border-border rounded text-sm"
                                                required
                                            />
                                            <div className="flex items-center gap-2">
                                                <span className="text-xs whitespace-nowrap">关键节点?</span>
                                                <input
                                                    type="checkbox"
                                                    checked={m.is_critical}
                                                    onChange={e => updateMilestone(idx, "is_critical", e.target.checked)}
                                                />
                                            </div>
                                            <input
                                                type="text"
                                                placeholder="描述"
                                                value={m.description}
                                                onChange={e => updateMilestone(idx, "description", e.target.value)}
                                                className="p-1.5 bg-background border border-border rounded text-sm col-span-2"
                                            />
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    <div className="flex justify-end gap-3 pt-4 border-t border-border mt-auto">
                        {step === 2 && (
                            <button
                                type="button"
                                onClick={() => setStep(1)}
                                className="px-4 py-2 text-sm font-medium hover:bg-muted rounded-md"
                            >
                                上一步
                            </button>
                        )}

                        {step === 1 ? (
                            <button
                                type="button"
                                onClick={() => setStep(2)}
                                className="px-4 py-2 bg-foreground text-background rounded-md text-sm font-medium hover:bg-foreground/90"
                            >
                                下一步: 规划里程碑
                            </button>
                        ) : (
                            <button
                                type="submit"
                                disabled={loading}
                                className="px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 disabled:opacity-50"
                            >
                                {loading ? "创建中..." : "完成创建"}
                            </button>
                        )}
                    </div>
                </form>
            </div>
        </div>
    );
}
