
"use client";

import { useState, useEffect } from "react";
import { X, Calendar, Clock } from "lucide-react";
import { apiPatch } from "@/lib/utils";
import { mutate } from "swr";
import { Task } from "@/types";

interface ScheduleDrawerProps {
    isOpen: boolean;
    onClose: () => void;
    task: Task | null;
}

export function ScheduleDrawer({ isOpen, onClose, task }: ScheduleDrawerProps) {
    const [loading, setLoading] = useState(false);
    const [start, setStart] = useState("");
    const [deadline, setDeadline] = useState("");

    // Initialize state when task opens
    useEffect(() => {
        if (isOpen && task) {
            // Default: Now rounded to next hour or existing scheduled time
            if (task.scheduled_time) {
                setStart(new Date(task.scheduled_time).toISOString().slice(0, 16));
            } else {
                const now = new Date();
                now.setMinutes(0, 0, 0);
                now.setHours(now.getHours() + 1);
                // Adjust for timezone - simple local iso string hack
                const localIso = new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
                setStart(localIso);
            }

            if (task.deadline) {
                setDeadline(new Date(task.deadline).toISOString().slice(0, 16));
            } else {
                setDeadline("");
            }
        }
    }, [isOpen, task]);

    // Auto-set deadline when start changes (default +1h)
    const handleStartChange = (val: string) => {
        setStart(val);
        if (val && !deadline) {
            const d = new Date(val);
            d.setHours(d.getHours() + 1);
            const localIso = new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
            setDeadline(localIso);
        }
    };

    const handleSave = async () => {
        if (!task) return;
        setLoading(true);
        try {
            await apiPatch(`/api/tasks/${task.id}`, {
                scheduled_time: start ? new Date(start).toISOString() : null,
                deadline: deadline ? new Date(deadline).toISOString() : null,
                // If scheduled, duration is implied or can be calced. For now keep simple.
            });
            mutate("/api/tasks");
            onClose();
        } catch (err: any) {
            alert("安排失败: " + err.message);
        } finally {
            setLoading(false);
        }
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex justify-end">
            {/* Backdrop */}
            <div
                className="absolute inset-0 bg-black/20 backdrop-blur-sm transition-opacity"
                onClick={onClose}
            />

            {/* Drawer Panel */}
            <div className="relative w-full max-w-sm bg-white h-full shadow-2xl flex flex-col animate-in slide-in-from-right duration-300">
                <div className="flex items-center justify-between p-6 border-b border-slate-100">
                    <h2 className="font-bold text-lg text-slate-800">快速安排</h2>
                    <button onClick={onClose} className="p-2 hover:bg-slate-100 rounded-full text-slate-400 hover:text-slate-600 transition-colors">
                        <X className="w-5 h-5" />
                    </button>
                </div>

                <div className="p-6 flex-1 overflow-y-auto">
                    <div className="mb-6 p-4 bg-slate-50 rounded-lg border border-slate-100">
                        <h3 className="font-semibold text-slate-900 mb-1 line-clamp-2">{task?.title}</h3>
                        <p className="text-sm text-slate-500 line-clamp-1">{task?.description || "无描述"}</p>
                    </div>

                    <div className="space-y-6">
                        <div>
                            <label className="flex items-center gap-2 text-sm font-semibold text-slate-700 mb-2">
                                <Clock className="w-4 h-4 text-indigo-500" />
                                开始时间
                            </label>
                            <input
                                type="datetime-local"
                                value={start}
                                onChange={(e) => handleStartChange(e.target.value)}
                                className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2.5 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500/20 transition-all shadow-sm"
                            />
                        </div>

                        <div>
                            <label className="flex items-center gap-2 text-sm font-semibold text-slate-700 mb-2">
                                <Calendar className="w-4 h-4 text-red-500" />
                                截止时间 (Deadline)
                            </label>
                            <input
                                type="datetime-local"
                                value={deadline}
                                onChange={(e) => setDeadline(e.target.value)}
                                className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2.5 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500/20 transition-all shadow-sm"
                            />
                        </div>
                    </div>
                </div>

                <div className="p-6 border-t border-slate-100 bg-slate-50/50">
                    <button
                        onClick={handleSave}
                        disabled={loading}
                        className="w-full py-3 bg-indigo-600 text-white font-medium rounded-xl hover:bg-indigo-700 active:bg-indigo-800 disabled:opacity-50 transition-all shadow-md shadow-indigo-600/20"
                    >
                        {loading ? "保存中..." : "确认安排"}
                    </button>
                </div>
            </div>
        </div>
    );
}
