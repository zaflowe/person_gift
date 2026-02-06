"use client";

import { useState } from "react";
import { X } from "lucide-react";
import { createProjectLongTaskTemplate } from "@/lib/api/project-long-tasks";
import { mutate } from "swr";
import { cn } from "@/lib/utils";

interface CreateLongTaskModalProps {
    isOpen: boolean;
    onClose: () => void;
    projectId: string;
    onSuccess?: () => void;
}

const WEEKDAYS = ["一", "二", "三", "四", "五", "六", "日"]; // 0=Mon
const PRESET_CYCLES = [7, 28, 365];

export function CreateLongTaskModal({ isOpen, onClose, projectId, onSuccess }: CreateLongTaskModalProps) {
    const [loading, setLoading] = useState(false);
    const [form, setForm] = useState({
        title: "",
        frequency_mode: "interval" as "interval" | "specific_days",
        interval_days: 1,
        days_of_week: [] as number[],
        default_start_time: "",
        default_end_time: "",
        evidence_type: "none",
        evidence_criteria: "",
        total_cycle_days: 28,
    });

    if (!isOpen) return null;

    const toggleDay = (day: number) => {
        setForm(prev => {
            const exists = prev.days_of_week.includes(day);
            return {
                ...prev,
                days_of_week: exists
                    ? prev.days_of_week.filter(d => d !== day)
                    : [...prev.days_of_week, day].sort(),
            };
        });
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!form.title.trim()) return;
        if (!form.total_cycle_days || form.total_cycle_days < 1) return;

        setLoading(true);
        try {
            await createProjectLongTaskTemplate(projectId, {
                title: form.title.trim(),
                frequency_mode: form.frequency_mode,
                interval_days: form.frequency_mode === "interval" ? form.interval_days : 1,
                days_of_week: form.frequency_mode === "specific_days" ? form.days_of_week : [],
                default_start_time: form.default_start_time || undefined,
                default_end_time: form.default_end_time || undefined,
                evidence_type: form.evidence_type as any,
                evidence_criteria: form.evidence_type !== "none" ? form.evidence_criteria : undefined,
                total_cycle_days: form.total_cycle_days,
            });

            mutate(`/api/projects/${projectId}/long-task-templates`);
            mutate(`/api/tasks?project_id=${projectId}`);
            mutate("/api/tasks");
            onSuccess?.();
            onClose();

            setForm({
                title: "",
                frequency_mode: "interval",
                interval_days: 1,
                days_of_week: [],
                default_start_time: "",
                default_end_time: "",
                evidence_type: "none",
                evidence_criteria: "",
                total_cycle_days: 28,
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
                    <h2 className="text-lg font-bold text-slate-800">新增长期任务</h2>
                    <button onClick={onClose} className="text-slate-400 hover:text-slate-600 transition-colors">
                        <X className="w-5 h-5" />
                    </button>
                </div>

                <form onSubmit={handleSubmit} className="p-6 space-y-5 overflow-y-auto">
                    <div>
                        <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">任务标题</label>
                        <input
                            type="text"
                            required
                            value={form.title}
                            onChange={e => setForm({ ...form, title: e.target.value })}
                            className="w-full text-base font-semibold placeholder:text-slate-300 border border-slate-200 rounded-lg px-3 py-2 focus:border-indigo-500 focus:outline-none transition-colors"
                            placeholder="例如：背单词打卡"
                        />
                    </div>

                    <div>
                        <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">频率</label>
                        <div className="flex gap-2">
                            <button
                                type="button"
                                onClick={() => setForm({ ...form, frequency_mode: "interval" })}
                                className={cn(
                                    "flex-1 py-1.5 text-xs rounded border transition-colors",
                                    form.frequency_mode === "interval"
                                        ? "bg-indigo-600 text-white border-indigo-600"
                                        : "bg-white border-slate-200 hover:bg-slate-50"
                                )}
                            >
                                间隔模式
                            </button>
                            <button
                                type="button"
                                onClick={() => setForm({ ...form, frequency_mode: "specific_days" })}
                                className={cn(
                                    "flex-1 py-1.5 text-xs rounded border transition-colors",
                                    form.frequency_mode === "specific_days"
                                        ? "bg-indigo-600 text-white border-indigo-600"
                                        : "bg-white border-slate-200 hover:bg-slate-50"
                                )}
                            >
                                指定星期
                            </button>
                        </div>
                    </div>

                    {form.frequency_mode === "interval" ? (
                        <div className="space-y-2 bg-slate-50 p-3 rounded-md">
                            <label className="text-xs text-slate-500">每 N 天一次 (1=每天)</label>
                            <input
                                type="number"
                                min="1"
                                max="3650"
                                value={form.interval_days}
                                onChange={e => setForm({ ...form, interval_days: parseInt(e.target.value) || 1 })}
                                className="w-full border border-slate-200 rounded px-2 py-1.5 text-sm"
                            />
                        </div>
                    ) : (
                        <div className="space-y-2 bg-slate-50 p-3 rounded-md">
                            <label className="text-xs text-slate-500">选择生效星期</label>
                            <div className="flex justify-between">
                                {WEEKDAYS.map((d, i) => (
                                    <button
                                        key={i}
                                        type="button"
                                        onClick={() => toggleDay(i)}
                                        className={cn(
                                            "w-8 h-8 rounded-full text-xs font-medium transition-colors border",
                                            form.days_of_week.includes(i)
                                                ? "bg-indigo-600 text-white border-indigo-600"
                                                : "bg-white text-slate-600 border-slate-200 hover:border-indigo-600"
                                        )}
                                    >
                                        {d}
                                    </button>
                                ))}
                            </div>
                        </div>
                    )}

                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">开始时间 (可选)</label>
                            <input
                                type="time"
                                value={form.default_start_time}
                                onChange={e => setForm({ ...form, default_start_time: e.target.value })}
                                className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none transition-colors"
                            />
                        </div>
                        <div>
                            <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">结束时间 (可选)</label>
                            <input
                                type="time"
                                value={form.default_end_time}
                                onChange={e => setForm({ ...form, default_end_time: e.target.value })}
                                className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none transition-colors"
                            />
                        </div>
                    </div>

                    <div>
                        <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">总周期天数</label>
                        <div className="flex gap-2 mb-2">
                            {PRESET_CYCLES.map(v => (
                                <button
                                    key={v}
                                    type="button"
                                    onClick={() => setForm({ ...form, total_cycle_days: v })}
                                    className={cn(
                                        "px-3 py-1 text-xs rounded border",
                                        form.total_cycle_days === v
                                            ? "bg-indigo-600 text-white border-indigo-600"
                                            : "bg-white border-slate-200 hover:bg-slate-50"
                                    )}
                                >
                                    {v} 天
                                </button>
                            ))}
                        </div>
                        <input
                            type="number"
                            min="1"
                            max="36500"
                            value={form.total_cycle_days}
                            onChange={e => setForm({ ...form, total_cycle_days: parseInt(e.target.value) || 1 })}
                            className="w-full border border-slate-200 rounded px-2 py-1.5 text-sm"
                        />
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
                            {loading ? "处理中..." : "创建长期任务"}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
