"use client";

import { useState, useEffect } from "react";
import { Plus, Trash2, Loader2, Clock } from "lucide-react";
import { FixedBlock, getFixedBlocks, createFixedBlock, deleteFixedBlock } from "@/lib/api/habits";
import { getToken, cn } from "@/lib/utils";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";

export function FixedBlockSidebar({ className }: { className?: string }) {
    const [blocks, setBlocks] = useState<FixedBlock[]>([]);
    const [loading, setLoading] = useState(false);
    const [isCreateOpen, setIsCreateOpen] = useState(false);
    const [saving, setSaving] = useState(false);

    // Form
    const [title, setTitle] = useState("");
    const [startTime, setStartTime] = useState("09:00");
    const [endTime, setEndTime] = useState("18:00");
    // Default weekdays
    const [selectedDays, setSelectedDays] = useState<number[]>([0, 1, 2, 3, 4]);

    useEffect(() => {
        loadBlocks();
    }, []);

    const loadBlocks = async () => {
        setLoading(true);
        try {
            const data = await getFixedBlocks();
            // Sort by start time
            data.sort((a, b) => a.start_time.localeCompare(b.start_time));
            setBlocks(data);
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
            await createFixedBlock({
                title,
                start_time: startTime,
                end_time: endTime,
                days_of_week: selectedDays,
                color: "#E2E8F0" // Default slate-200
            });
            setIsCreateOpen(false);
            resetForm();
            loadBlocks();
        } catch (e) {
            console.error(e);
        } finally {
            setSaving(false);
        }
    };

    const handleDelete = async (id: string) => {
        if (!confirm("删除此固定块？")) return;
        try {
            await deleteFixedBlock(id);
            setBlocks(prev => prev.filter(b => b.id !== id));
        } catch (e) {
            console.error(e);
        }
    };

    const resetForm = () => {
        setTitle("");
        setStartTime("09:00");
        setEndTime("18:00");
        setSelectedDays([0, 1, 2, 3, 4]);
    };

    const WEEKDAYS = ["一", "二", "三", "四", "五", "六", "日"];
    const toggleDay = (d: number) => {
        if (selectedDays.includes(d)) setSelectedDays(prev => prev.filter(x => x !== d));
        else setSelectedDays(prev => [...prev, d].sort());
    };

    // Calculate position for timeline? Or just simple list
    // User requested "Mini Timeline" + "List"
    // Let's implement a simple list first, maybe stylized

    return (
        <div className={cn("flex flex-col h-full bg-white", className)}>
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100 flex-none bg-white z-10">
                <h3 className="font-bold text-sm text-slate-800">固定时间 (Fixed)</h3>
                <button
                    onClick={() => setIsCreateOpen(true)}
                    className="p-1 hover:bg-slate-100 rounded-full transition-colors text-slate-500 hover:text-primary"
                >
                    <Plus className="w-4 h-4" />
                </button>
            </div>

            <div className="flex-1 overflow-y-auto px-4 py-3 space-y-4 custom-scrollbar">
                {/* Timeline Visualization (Simple Vertical) */}
                <div className="relative pl-4 border-l-2 border-slate-100 space-y-6">
                    {loading && blocks.length === 0 ? (
                        <div className="flex justify-center"><Loader2 className="w-4 h-4 animate-spin text-slate-300" /></div>
                    ) : blocks.length === 0 ? (
                        <div className="text-xs text-slate-400 pl-2">尚未配置固定时间</div>
                    ) : (
                        blocks.map(block => (
                            <div key={block.id} className="relative pl-4 group">
                                {/* Dot */}
                                <div className="absolute -left-[21px] top-0 w-3 h-3 rounded-full bg-slate-200 border-2 border-white shadow-sm group-hover:bg-primary transition-colors"></div>

                                <div className="bg-slate-50 rounded-lg p-2.5 border border-slate-100 hover:border-slate-300 transition-colors group-hover:shadow-sm">
                                    <div className="flex justify-between items-start">
                                        <div>
                                            <div className="text-[13px] font-medium text-slate-700">{block.title}</div>
                                            <div className="text-[11px] text-slate-400 font-mono mt-0.5 flex items-center gap-1">
                                                <Clock className="w-3 h-3" />
                                                {block.start_time} - {block.end_time}
                                            </div>
                                            <div className="text-[9px] text-slate-400 mt-1 flex gap-0.5">
                                                {WEEKDAYS.map((d, i) => (
                                                    <span key={i} className={cn(
                                                        "px-1 rounded-sm",
                                                        block.days_of_week?.includes(i) ? "bg-slate-200 text-slate-600" : "opacity-30"
                                                    )}>{d}</span>
                                                ))}
                                            </div>
                                        </div>
                                        <button
                                            onClick={() => handleDelete(block.id)}
                                            className="opacity-0 group-hover:opacity-100 p-1 text-slate-300 hover:text-red-500 transition-all"
                                        >
                                            <Trash2 className="w-3.5 h-3.5" />
                                        </button>
                                    </div>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </div>

            {/* Create Dialog */}
            <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>新建固定时间块</DialogTitle>
                    </DialogHeader>
                    <div className="space-y-4 py-2">
                        <div className="space-y-1.5">
                            <label className="text-xs font-medium text-slate-500">名称</label>
                            <input
                                value={title}
                                onChange={(e) => setTitle(e.target.value)}
                                className="w-full border border-slate-200 rounded-md px-3 py-2 text-sm focus:ring-2 focus:ring-primary/20 outline-none"
                                placeholder="例如：上班、通勤、午休..."
                            />
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                            <div className="space-y-1.5">
                                <label className="text-xs font-medium text-slate-500">开始时间</label>
                                <input
                                    type="time"
                                    value={startTime}
                                    onChange={e => setStartTime(e.target.value)}
                                    className="w-full border border-slate-200 rounded-md px-2 py-2 text-sm"
                                />
                            </div>
                            <div className="space-y-1.5">
                                <label className="text-xs font-medium text-slate-500">结束时间</label>
                                <input
                                    type="time"
                                    value={endTime}
                                    onChange={e => setEndTime(e.target.value)}
                                    className="w-full border border-slate-200 rounded-md px-2 py-2 text-sm"
                                />
                            </div>
                        </div>
                        <div className="space-y-1.5 bg-slate-50 p-3 rounded-md">
                            <label className="text-xs text-slate-500">生效星期</label>
                            <div className="flex justify-between">
                                {WEEKDAYS.map((d, i) => (
                                    <button
                                        key={i}
                                        onClick={() => toggleDay(i)}
                                        className={cn(
                                            "w-8 h-8 rounded-full text-xs font-medium transition-colors border",
                                            selectedDays.includes(i) ? "bg-primary text-white border-primary" : "bg-white text-slate-600 border-slate-200 hover:border-primary"
                                        )}
                                    >
                                        {d}
                                    </button>
                                ))}
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
                            {saving ? "创建" : "创建"}
                        </button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}
