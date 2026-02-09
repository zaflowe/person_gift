"use client";

import { useState } from "react";
import { X } from "lucide-react";
import { Task } from "@/types";

interface EditTaskModalProps {
    task: Task;
    onClose: () => void;
    onSave: (taskId: string, payload: any) => Promise<void>;
}

function toLocalInput(value?: string | null) {
    if (!value) return "";
    const d = new Date(value);
    const local = new Date(d.getTime() - d.getTimezoneOffset() * 60000);
    return local.toISOString().slice(0, 16);
}

export function EditTaskModal({ task, onClose, onSave }: EditTaskModalProps) {
    const [loading, setLoading] = useState(false);
    const [form, setForm] = useState({
        title: task.title || "",
        description: task.description || "",
        deadline: toLocalInput(task.deadline as any),
        scheduled_time: toLocalInput(task.scheduled_time as any),
        evidence_type: task.evidence_type || "none",
        evidence_criteria: task.evidence_criteria || "",
    });

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        try {
            await onSave(task.id, {
                title: form.title,
                description: form.description,
                deadline: form.deadline ? new Date(form.deadline).toISOString() : null,
                scheduled_time: form.scheduled_time ? new Date(form.scheduled_time).toISOString() : null,
                evidence_type: form.evidence_type,
                evidence_criteria: form.evidence_type === "none" ? null : form.evidence_criteria,
            });
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
            <div className="bg-white border border-slate-200 rounded-xl shadow-xl w-full max-w-lg flex flex-col max-h-[90vh] overflow-hidden">
                <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
                    <h2 className="text-lg font-bold text-slate-800">编辑任务</h2>
                    <button onClick={onClose} className="text-slate-400 hover:text-slate-600 transition-colors">
                        <X className="w-5 h-5" />
                    </button>
                </div>

                <form onSubmit={handleSubmit} className="p-6 space-y-6 overflow-y-auto">
                    <div>
                        <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">任务标题</label>
                        <input
                            type="text"
                            required
                            value={form.title}
                            onChange={e => setForm({ ...form, title: e.target.value })}
                            className="w-full text-base font-semibold placeholder:text-slate-300 border border-slate-200 rounded-lg px-3 py-2 focus:border-indigo-500 focus:outline-none transition-colors"
                        />
                    </div>

                    <div>
                        <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">描述 (可选)</label>
                        <textarea
                            value={form.description}
                            onChange={e => setForm({ ...form, description: e.target.value })}
                            className="w-full min-h-[80px] text-sm border border-slate-200 rounded-lg px-3 py-2 resize-none focus:border-indigo-500 focus:outline-none placeholder:text-slate-300"
                        />
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">开始时间</label>
                            <input
                                type="datetime-local"
                                value={form.scheduled_time}
                                onChange={e => setForm({ ...form, scheduled_time: e.target.value })}
                                className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none transition-colors"
                            />
                        </div>
                        <div>
                            <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">截止时间</label>
                            <input
                                type="datetime-local"
                                value={form.deadline}
                                onChange={e => setForm({ ...form, deadline: e.target.value })}
                                className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none transition-colors"
                            />
                        </div>
                    </div>

                    <div>
                        <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">验收方式</label>
                        <select
                            value={form.evidence_type}
                            onChange={e => setForm({ ...form, evidence_type: e.target.value })}
                            className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none transition-colors appearance-none"
                        >
                            <option value="none">自觉完成 (无强制)</option>
                            <option value="image">拍照打卡 (AI 审核)</option>
                            <option value="text">文字总结</option>
                            <option value="number">数值记录</option>
                        </select>
                    </div>

                    {form.evidence_type !== "none" && (
                        <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
                            <textarea
                                value={form.evidence_criteria}
                                onChange={e => setForm({ ...form, evidence_criteria: e.target.value })}
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
                            className="w-full py-2.5 bg-indigo-600 text-white hover:bg-indigo-700 active:bg-indigo-800 rounded-lg font-medium shadow-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {loading ? "处理中..." : "保存修改"}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
