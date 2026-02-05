"use client";

import { AppCard, AppCardHeader } from "@/components/ui/app-card";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip as RechartsTooltip, LineChart, Line, XAxis, YAxis, CartesianGrid, Legend } from "recharts";
import { cn } from "@/lib/utils";

import { getProjectColorHex } from "@/lib/project-colors";

// --- Colors - Logic handled in Chart render now ---

// --- Types ---
interface PieData {
    name: string;
    value: number;
    project_id?: string;
}

export interface TrendData {
    date: string; // MM-DD
    value: number;
    target?: number;
    baseline?: number;
}

// --- Pie Chart ---
interface StudyPieChartProps {
    data: PieData[];
    projects?: any[];
}

export function StudyPieChart({ data, projects }: StudyPieChartProps) {
    // ...
    const hasData = data && data.length > 0 && data.some(d => d.value > 0);

    return (
        <AppCard className="h-80 flex flex-col" noPadding>
            <AppCardHeader className="px-5 pt-5">学习时间分布 (本周)</AppCardHeader>
            <div className="flex-1 min-h-0 relative">
                {hasData ? (
                    <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                            <Pie
                                data={data}
                                cx="50%"
                                cy="50%"
                                innerRadius={60}
                                outerRadius={80}
                                paddingAngle={5}
                                dataKey="value"
                            >
                                {data.map((entry, index) => {
                                    // Robust Color Logic
                                    // 1. Try to find project object using ID
                                    let isStrategic = false;
                                    let strategicIndex = -1;

                                    if (entry.project_id && projects) {
                                        // "Top 3 Strategic" logic: status checks
                                        const activeProjects = projects.filter(p => p.status !== 'SUCCESS' && p.status !== 'FAILURE');
                                        const strategicList = activeProjects.slice(0, 3);

                                        isStrategic = strategicList.some(sp => sp.id === entry.project_id);
                                        strategicIndex = strategicList.findIndex(sp => sp.id === entry.project_id);
                                    }

                                    // 2. Get Color (Fallback to hash by name if ID missing)
                                    const colorKey = entry.project_id || entry.name;
                                    // Pass isStrategic params. If not found, defaults will apply (hash)
                                    const fill = getProjectColorHex(colorKey, isStrategic, strategicIndex);

                                    return <Cell key={`cell-${index}`} fill={fill} stroke="var(--bg)" strokeWidth={2} />;
                                })}
                            </Pie>
                            <RechartsTooltip
                                contentStyle={{ backgroundColor: 'var(--surface)', borderColor: 'var(--border)', borderRadius: '8px' }}
                                itemStyle={{ color: 'var(--text)' }}
                                formatter={(value: any) => {
                                    const val = Number(value);
                                    if (isNaN(val)) return value;
                                    const h = Math.floor(val / 3600);
                                    const m = Math.floor((val % 3600) / 60);
                                    return `${h}h ${m}m`;
                                }}
                            />
                            <Legend
                                verticalAlign="bottom"
                                height={36}
                                iconType="circle"
                                formatter={(value: string) => {
                                    // Truncate long names
                                    if (value.length > 8) {
                                        return `${value.substring(0, 8)}...`;
                                    }
                                    return value;
                                }}
                            />
                        </PieChart>
                    </ResponsiveContainer>
                ) : (
                    <div className="absolute inset-0 flex items-center justify-center text-muted-foreground text-sm">
                        暂无数据
                    </div>
                )}
            </div>
        </AppCard>
    );
}

// --- Line Chart ---
interface MetricTrendChartProps {
    title: string;
    data: TrendData[];
    unit: string;
    color?: string;
}

export function MetricTrendChart({ title, data, unit, color = "#8b5cf6" }: MetricTrendChartProps) {
    const hasData = data && data.length > 0;

    return (
        <AppCard className="h-80 flex flex-col" noPadding>
            <AppCardHeader className="px-5 pt-5">{title} 趋势 (4周)</AppCardHeader>
            <div className="flex-1 min-h-0 relative px-2 pb-2">
                {hasData ? (
                    <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={data} margin={{ top: 20, right: 30, left: 0, bottom: 5 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} opacity={0.5} />
                            <XAxis
                                dataKey="date"
                                tick={{ fontSize: 10, fill: 'var(--muted)' }}
                                axisLine={false}
                                tickLine={false}
                                dy={10}
                            />
                            <YAxis
                                domain={['auto', 'auto']}
                                tick={{ fontSize: 10, fill: 'var(--muted)' }}
                                axisLine={false}
                                tickLine={false}
                                width={30}
                            />
                            <RechartsTooltip
                                contentStyle={{ backgroundColor: 'var(--surface)', borderColor: 'var(--border)', borderRadius: '8px' }}
                                itemStyle={{ color: 'var(--text)' }}
                                formatter={(val: number) => [`${val} ${unit}`, '数值']}
                            />
                            {/* <Legend /> */}
                            {data[0]?.baseline && (
                                <Line type="monotone" dataKey="baseline" stroke="var(--muted)" strokeDasharray="5 5" strokeWidth={1} dot={false} activeDot={false} name="初始" />
                            )}
                            {data[0]?.target && (
                                <Line type="monotone" dataKey="target" stroke="var(--success)" strokeDasharray="3 3" strokeWidth={1} dot={false} activeDot={false} name="目标" />
                            )}
                            <Line
                                type="monotone"
                                dataKey="value"
                                stroke={color}
                                strokeWidth={3}
                                dot={{ fill: color, strokeWidth: 2, r: 4, stroke: 'var(--bg)' }}
                                activeDot={{ r: 6, strokeWidth: 0 }}
                                name="当前"
                            />
                        </LineChart>
                    </ResponsiveContainer>
                ) : (
                    <div className="absolute inset-0 flex items-center justify-center text-muted-foreground text-sm">
                        暂无数据
                    </div>
                )}
            </div>
        </AppCard>
    );
}
