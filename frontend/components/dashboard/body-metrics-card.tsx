"use client";

import { useState } from "react";
import { AppCard } from "@/components/ui/app-card";
import { Activity, Plus, TrendingDown, TrendingUp, Minus } from "lucide-react";
import useSWR, { useSWRConfig } from "swr";
import { fetcher, apiPost } from "@/lib/utils";
import { ResponsiveContainer, LineChart, Line, YAxis, ReferenceLine } from "recharts";
import {
    Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter
} from "@/components/ui/dialog";

const TARGET_WEIGHT = 85.0;
const TARGET_FAT = 18.0;

export function BodyMetricsCard() {
    const { mutate } = useSWRConfig();
    const { data: weightHistory } = useSWR<any[]>("/api/metrics/history?metric_type=weight&days=30", fetcher);
    const { data: fatHistory } = useSWR<any[]>("/api/metrics/history?metric_type=bodyfat&days=30", fetcher);

    const [isAdding, setIsAdding] = useState(false);
    const [newWeight, setNewWeight] = useState("");
    const [newFat, setNewFat] = useState("");

    // Process Data
    const latestWeight = weightHistory?.[0]?.value || 0;
    const latestFat = fatHistory?.[0]?.value || 0;

    // Sort for chart (oldest first)
    const weightData = [...(weightHistory || [])].reverse().map(d => ({ value: d.value }));
    const fatData = [...(fatHistory || [])].reverse().map(d => ({ value: d.value }));

    const handleAddEntry = async () => {
        try {
            if (newWeight) {
                await apiPost("/api/metrics/entry", {
                    metric_type: "weight",
                    value: parseFloat(newWeight)
                });
            }
            if (newFat) {
                await apiPost("/api/metrics/entry", {
                    metric_type: "bodyfat",
                    value: parseFloat(newFat)
                });
            }
            // Refresh data
            mutate("/api/metrics/history?metric_type=weight&days=30");
            mutate("/api/metrics/history?metric_type=bodyfat&days=30");
            setIsAdding(false);
            setNewWeight("");
            setNewFat("");
        } catch (e) {
            console.error(e);
            alert("Record failed");
        }
    };

    return (
        <AppCard className="flex flex-row items-center justify-between gap-4 h-full p-4">

            {/* Left: Metrics & Targets */}
            <div className="flex gap-6 flex-1">
                {/* Weight */}
                <div className="flex flex-col justify-center gap-1">
                    <div className="text-xs text-[var(--muted)] flex items-center gap-1">
                        体重 <span className="text-[var(--border)]">|</span> 目标 {TARGET_WEIGHT}kg
                    </div>
                    <div className="flex items-baseline gap-2">
                        <span className="text-2xl font-bold font-mono">{latestWeight > 0 ? latestWeight : "--"}</span>
                        <span className="text-xs text-[var(--muted)]">kg</span>
                        {latestWeight > 0 && (
                            <span className={`text-xs ${latestWeight <= TARGET_WEIGHT ? 'text-[var(--success)]' : 'text-[var(--warning)]'}`}>
                                {latestWeight <= TARGET_WEIGHT ? <TrendingDown className="w-3 h-3" /> : `${(latestWeight - TARGET_WEIGHT).toFixed(1)}`}
                            </span>
                        )}
                    </div>
                    <div className="h-8 w-24 opacity-50">
                        <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={weightData}>
                                <Line type="monotone" dataKey="value" stroke="var(--primary)" strokeWidth={2} dot={false} />
                                <ReferenceLine y={TARGET_WEIGHT} stroke="var(--success)" strokeDasharray="3 3" />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                <div className="w-px bg-[var(--border)] h-10 self-center" />

                {/* Body Fat */}
                <div className="flex flex-col justify-center gap-1">
                    <div className="text-xs text-[var(--muted)] flex items-center gap-1">
                        体脂 <span className="text-[var(--border)]">|</span> 目标 {TARGET_FAT}%
                    </div>
                    <div className="flex items-baseline gap-2">
                        <span className="text-2xl font-bold font-mono">{latestFat > 0 ? latestFat : "--"}</span>
                        <span className="text-xs text-[var(--muted)]">%</span>
                        {latestFat > 0 && (
                            <span className={`text-xs ${latestFat <= TARGET_FAT ? 'text-[var(--success)]' : 'text-[var(--warning)]'}`}>
                                {latestFat <= TARGET_FAT ? <TrendingDown className="w-3 h-3" /> : `${(latestFat - TARGET_FAT).toFixed(1)}`}
                            </span>
                        )}
                    </div>
                    <div className="h-8 w-24 opacity-50">
                        <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={fatData}>
                                <Line type="monotone" dataKey="value" stroke="var(--accent)" strokeWidth={2} dot={false} />
                                <ReferenceLine y={TARGET_FAT} stroke="var(--success)" strokeDasharray="3 3" />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            </div>

            {/* Right: Add Button */}
            <Dialog open={isAdding} onOpenChange={setIsAdding}>
                <DialogTrigger asChild>
                    <button className="h-10 w-10 flex items-center justify-center rounded-full bg-[var(--surface-hover)] hover:bg-[var(--primary)] hover:text-white transition group">
                        <Plus className="w-5 h-5 text-[var(--muted)] group-hover:text-white" />
                    </button>
                </DialogTrigger>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>记录身体指标</DialogTitle>
                    </DialogHeader>
                    <div className="grid gap-4 py-4">
                        <div className="grid grid-cols-4 items-center gap-4">
                            <label className="text-right text-sm">体重 (kg)</label>
                            <input
                                className="col-span-3 p-2 border rounded bg-[var(--background)]"
                                type="number"
                                step="0.1"
                                placeholder={latestWeight.toString()}
                                value={newWeight}
                                onChange={(e) => setNewWeight(e.target.value)}
                            />
                        </div>
                        <div className="grid grid-cols-4 items-center gap-4">
                            <label className="text-right text-sm">体脂 (%)</label>
                            <input
                                className="col-span-3 p-2 border rounded bg-[var(--background)]"
                                type="number"
                                step="0.1"
                                placeholder={latestFat.toString()}
                                value={newFat}
                                onChange={(e) => setNewFat(e.target.value)}
                            />
                        </div>
                    </div>
                    <DialogFooter>
                        <button
                            className="px-4 py-2 bg-[var(--primary)] text-white rounded"
                            onClick={handleAddEntry}
                        >
                            保存记录
                        </button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

        </AppCard>
    );
}
