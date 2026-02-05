"use client";

import { useState, useEffect } from "react";
import { apiPost, apiPatch } from "@/lib/utils";
import { X, Plus, Trash } from "lucide-react";
import { mutate } from "swr";
import { Project } from "@/types";

interface EditProjectModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSuccess?: () => void;
    project: Project;
}

export function EditProjectModal({ isOpen, onClose, onSuccess, project }: EditProjectModalProps) {
    const [loading, setLoading] = useState(false);
    const [formData, setFormData] = useState({
        title: "",
        description: "",
        success_criteria: "",
        failure_criteria: "",
        deadline: "",
        color: "",
        is_strategic: false
    });

    useEffect(() => {
        if (project) {
            setFormData({
                title: project.title,
                description: project.description,
                success_criteria: project.success_criteria || "",
                failure_criteria: project.failure_criteria || "",
                deadline: project.deadline ? new Date(project.deadline).toISOString().slice(0, 16) : "",
                color: project.color || "",
                is_strategic: project.is_strategic || false
            });
        }
    }, [project, isOpen]);

    if (!isOpen) return null;

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        try {
            const payload = {
                title: formData.title,
                description: formData.description,
                success_criteria: formData.success_criteria || null,
                failure_criteria: formData.failure_criteria || null,
                is_strategic: formData.is_strategic,
                color: formData.color || null,
                // Only send deadline if it's changed or valid? 
                // Creating simplified payload
            };

            await apiPatch(`/api/projects/${project.id}`, payload);
            mutate("/api/projects");
            mutate(`/api/projects/${project.id}`);
            onSuccess?.();
            onClose();
        } catch (err: any) {
            alert(err.message || "更新失败");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
            <div className="bg-card border border-border rounded-lg shadow-lg w-full max-w-2xl flex flex-col max-h-[90vh]">
                <div className="flex items-center justify-between p-4 border-b border-border">
                    <h2 className="text-lg font-semibold">编辑项目</h2>
                    <button onClick={onClose} className="text-muted-foreground hover:text-foreground">
                        <X className="w-5 h-5" />
                    </button>
                </div>

                <form onSubmit={handleSubmit} className="p-4 space-y-4 overflow-y-auto flex-1">
                    <div className="space-y-4">
                        <div>
                            <label className="block text-sm font-medium mb-1">项目名称</label>
                            <input
                                type="text"
                                required
                                value={formData.title}
                                onChange={e => setFormData({ ...formData, title: e.target.value })}
                                className="w-full p-2 bg-background border border-border rounded-md"
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium mb-1">目标描述</label>
                            <textarea
                                required
                                value={formData.description}
                                onChange={e => setFormData({ ...formData, description: e.target.value })}
                                className="w-full p-2 bg-background border border-border rounded-md h-20"
                            />
                        </div>

                        {/* Strategic Toggle */}
                        <div className="flex items-center gap-2">
                            <input
                                type="checkbox"
                                id="is_strategic"
                                checked={formData.is_strategic}
                                onChange={e => setFormData({ ...formData, is_strategic: e.target.checked })}
                                className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                            />
                            <label htmlFor="is_strategic" className="text-sm font-medium">设为战略项目 (Strategic)</label>
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="block text-sm font-medium mb-1">成功标准</label>
                                <textarea
                                    value={formData.success_criteria}
                                    onChange={e => setFormData({ ...formData, success_criteria: e.target.value })}
                                    className="w-full p-2 bg-background border border-border rounded-md h-20"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium mb-1">失败惩罚</label>
                                <textarea
                                    value={formData.failure_criteria}
                                    onChange={e => setFormData({ ...formData, failure_criteria: e.target.value })}
                                    className="w-full p-2 bg-background border border-border rounded-md h-20"
                                />
                            </div>
                        </div>

                        <div>
                            <label className="block text-sm font-medium mb-2">项目颜色</label>
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

                    <div className="flex justify-end pt-4 border-t border-border mt-auto">
                        <button
                            type="submit"
                            disabled={loading}
                            className="px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 disabled:opacity-50"
                        >
                            {loading ? "保存中..." : "保存修改"}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
