"use client";

import { useState, useEffect } from "react";
import { Plus, MoreHorizontal, Check, Loader2, Trash2 } from "lucide-react";
import { HabitTemplate, getHabitTemplates, createHabitTemplate, updateHabitTemplate, deleteHabitTemplate } from "@/lib/api/habits";
import { getToken, cn } from "@/lib/utils";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";

export function HabitSidebar({ className }: { className?: string }) {
    const [habits, setHabits] = useState<HabitTemplate[]>([]);
    const [loading, setLoading] = useState(false);
    const [isCreateOpen, setIsCreateOpen] = useState(false);

    // Create Form State
    const [title, setTitle] = useState("");
    const [freqMode, setFreqMode] = useState<"interval" | "specific_days">("interval");
    const [interval, setInterval] = useState(1);
    const [specificDays, setSpecificDays] = useState<number[]>([]);
    const [startTime, setStartTime] = useState("");
    const [endTime, setEndTime] = useState("");
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        loadHabits();
    }, []);

    const loadHabits = async () => {
        setLoading(true);
        try {
            const data = await getHabitTemplates();
            setHabits(data);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    const handleCreate = async () => {
        if (!title.trim()) return;

        setSaving(true);
        try {
            await createHabitTemplate({
                title,
                frequency_mode: freqMode,
                interval_days: freqMode === "interval" ? interval : 1,
                days_of_week: freqMode === "specific_days" ? specificDays : [],
                default_start_time: startTime || undefined,
                default_end_time: endTime || undefined,
                enabled: true
            });
            setIsCreateOpen(false);
            resetForm();
            loadHabits();
        } catch (e) {
            console.error(e);
        } finally {
            setSaving(false);
        }
    };

    const handleToggle = async (habit: HabitTemplate) => {
        // Optimistic update
        const newVal = !habit.enabled;
        setHabits(prev => prev.map(h => h.id === habit.id ? { ...h, enabled: newVal } : h));

        try {
            await updateHabitTemplate(habit.id, { enabled: newVal });
        } catch (e) {
            // Revert
            setHabits(prev => prev.map(h => h.id === habit.id ? { ...h, enabled: !newVal } : h));
        }
    };

    const handleDelete = async (id: string) => {
        if (!confirm("确认删除此习惯模板？")) return;

        try {
            await deleteHabitTemplate(id);
            setHabits(prev => prev.filter(h => h.id !== id));
        } catch (e) {
            console.error(e);
        }
    };

    const resetForm = () => {
        setTitle("");
        setFreqMode("interval");
        setInterval(1);
        setInterval(1);
        setSpecificDays([]);
        setStartTime("");
        setEndTime("");
    };

    const toggleDay = (day: number) => {
        if (specificDays.includes(day)) {
            setSpecificDays(prev => prev.filter(d => d !== day));
        } else {
            setSpecificDays(prev => [...prev, day].sort());
        }
    };

    const WEEKDAYS = ["一", "二", "三", "四", "五", "六", "日"]; // 0=Mon

    return (
        <div className={cn("flex flex-col h-full bg-white border-b border-slate-200/60", className)}>
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100 flex-none bg-white z-10">
                <h3 className="font-bold text-sm text-slate-800">习惯 (Habits)</h3>
                <button
                    onClick={() => setIsCreateOpen(true)}
                    className="p-1 hover:bg-slate-100 rounded-full transition-colors text-slate-500 hover:text-primary"
                >
                    <Plus className="w-4 h-4" />
                </button>
            </div>

            {/* List */}
            <div className="flex-1 overflow-y-auto px-2 py-2 space-y-1 custom-scrollbar">
                {loading && habits.length === 0 ? (
                    <div className="flex justify-center py-4"><Loader2 className="w-4 h-4 animate-spin text-slate-300" /></div>
                ) : habits.length === 0 ? (
                    <div className="text-center py-8 text-xs text-slate-400">
                        还没有习惯，点击 + 号添加
                    </div>
                ) : (
                    habits.map(habit => (
                        <div key={habit.id} className={cn(
                            "group flex items-center justify-between p-2 rounded-lg hover:bg-slate-50 transition-colors border border-transparent hover:border-slate-100",
                            !habit.enabled && "opacity-60 grayscale"
                        )}>
                            <div className="min-w-0 flex-1 mr-2">
                                <div className="font-medium text-[13px] text-slate-700 truncate">{habit.title}</div>
                                <div className="text-[10px] text-slate-400 mt-0.5 flex items-center gap-1.5">
                                    <span className="bg-slate-100 px-1 py-0.5 rounded text-slate-500">
                                        {habit.frequency_mode === "interval"
                                            ? (habit.interval_days === 1 ? "每天" : `每 ${habit.interval_days} 天`)
                                            : `每周 ${habit.days_of_week?.map(d => WEEKDAYS[d]).join(" ")}`
                                        }
                                    </span>
                                    {habit.default_due_time && <span>{habit.default_due_time} 截止</span>}
                                </div>
                            </div>

                            <div className="flex items-center gap-1">
                                <button
                                    onClick={() => handleToggle(habit)}
                                    className={cn(
                                        "w-8 h-4 rounded-full relative transition-colors duration-200",
                                        habit.enabled ? "bg-primary" : "bg-slate-200"
                                    )}
                                >
                                    <div className={cn(
                                        "absolute top-0.5 w-3 h-3 bg-white rounded-full shadow-sm transition-transform duration-200",
                                        habit.enabled ? "left-4.5 translate-x-0" : "left-0.5"
                                    )} />
                                </button>
                                <button
                                    onClick={() => handleDelete(habit.id)}
                                    className="opacity-0 group-hover:opacity-100 p-1 text-slate-300 hover:text-red-500 transition-all"
                                >
                                    <Trash2 className="w-3.5 h-3.5" />
                                </button>
                            </div>
                        </div>
                    ))
                )}
            </div>

            {/* Create Dialog */}
            <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>新建习惯</DialogTitle>
                    </DialogHeader>
                    <div className="space-y-4 py-2">
                        <div className="space-y-1.5">
                            <label className="text-xs font-medium text-slate-500">习惯名称</label>
                            <input
                                value={title}
                                onChange={(e) => setTitle(e.target.value)}
                                className="w-full border border-slate-200 rounded-md px-3 py-2 text-sm focus:ring-2 focus:ring-primary/20 outline-none"
                                placeholder="例如：背单词、冥想..."
                            />
                        </div>

                        <div className="space-y-1.5">
                            <label className="text-xs font-medium text-slate-500">频率</label>
                            <div className="flex gap-2">
                                <button
                                    onClick={() => setFreqMode("interval")}
                                    className={cn(
                                        "flex-1 py-1.5 text-xs rounded border transition-colors",
                                        freqMode === "interval" ? "bg-primary text-white border-primary" : "bg-white border-slate-200 hover:bg-slate-50"
                                    )}
                                >
                                    间隔模式 (Interval)
                                </button>
                                <button
                                    onClick={() => setFreqMode("specific_days")}
                                    className={cn(
                                        "flex-1 py-1.5 text-xs rounded border transition-colors",
                                        freqMode === "specific_days" ? "bg-primary text-white border-primary" : "bg-white border-slate-200 hover:bg-slate-50"
                                    )}
                                >
                                    指定星期 (Weekly)
                                </button>
                            </div>
                        </div>

                        {freqMode === "interval" ? (
                            <div className="space-y-1.5 bg-slate-50 p-3 rounded-md">
                                <label className="text-xs text-slate-500">每 N 天一次 (1=每天)</label>
                                <input
                                    type="number"
                                    min="1" max="365"
                                    value={interval}
                                    onChange={(e) => setInterval(parseInt(e.target.value) || 1)}
                                    className="w-full border border-slate-200 rounded px-2 py-1.5 text-sm"
                                />
                            </div>
                        ) : (
                            <div className="space-y-1.5 bg-slate-50 p-3 rounded-md">
                                <label className="text-xs text-slate-500">选择生效星期</label>
                                <div className="flex justify-between">
                                    {WEEKDAYS.map((d, i) => (
                                        <button
                                            key={i}
                                            onClick={() => toggleDay(i)}
                                            className={cn(
                                                "w-8 h-8 rounded-full text-xs font-medium transition-colors border",
                                                specificDays.includes(i) ? "bg-primary text-white border-primary" : "bg-white text-slate-600 border-slate-200 hover:border-primary"
                                            )}
                                        >
                                            {d}
                                        </button>
                                    ))}
                                </div>
                            </div>
                        )}

                        <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-1.5">
                                <label className="text-xs font-medium text-slate-500">开始时间 (可选)</label>
                                <input
                                    type="time"
                                    value={startTime}
                                    onChange={(e) => setStartTime(e.target.value)}
                                    className="w-full border border-slate-200 rounded px-2 py-1.5 text-sm"
                                />
                            </div>
                            <div className="space-y-1.5">
                                <label className="text-xs font-medium text-slate-500">结束时间 (可选)</label>
                                <input
                                    type="time"
                                    value={endTime}
                                    onChange={(e) => setEndTime(e.target.value)}
                                    className="w-full border border-slate-200 rounded px-2 py-1.5 text-sm"
                                />
                            </div>
                        </div>
                    </div>
                    <DialogFooter>
                        <button
                            onClick={() => setIsCreateOpen(false)}
                            className="px-4 py-2 text-sm text-slate-500 bg-slate-100 rounded-md hover:bg-slate-200"
                        >
                            取消
                        </button>
                        <button
                            onClick={handleCreate}
                            disabled={!title.trim() || saving}
                            className="px-4 py-2 text-sm text-white bg-primary rounded-md hover:bg-primary/90 disabled:opacity-50"
                        >
                            {saving ? "创建中..." : "创建"}
                        </button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}
