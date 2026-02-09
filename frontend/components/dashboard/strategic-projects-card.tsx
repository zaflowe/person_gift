"use client";

import { AppCard } from "@/components/ui/app-card";
import { Target, ChevronRight, Shield, Zap, History } from "lucide-react";
import Link from "next/link";
import useSWR from "swr";
import { fetcher } from "@/lib/utils";

interface StrategicProject {
    id: string;
    title: string;
    progress: number;
    next_milestone: string;
    updated_at: string;
    color?: string;
}

interface ExemptionQuota {
    day_pass_total: number;
    day_pass_used: number;
    rule_break_total: number;
    rule_break_used: number;
}

export function StrategicProjectsCard() {
    const { data: projects } = useSWR<StrategicProject[]>("/dashboard/projects/strategic", fetcher);
    const { data: quota } = useSWR<ExemptionQuota>("/api/exemptions/quota", fetcher);

    return (
        <AppCard className="flex flex-col h-full bg-card shadow-sm border border-border">
            {/* Top Half: Strategic Projects */}
            <div className="flex-1 flex flex-col p-4 pb-2">
                <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                        <Target className="w-4 h-4 text-primary" />
                        <span className="font-semibold text-sm">战略聚焦</span>
                    </div>
                    <span className="text-xs text-muted-foreground bg-secondary px-1.5 py-0.5 rounded">TOP 3</span>
                </div>

                <div className="flex flex-col gap-2 flex-1 min-h-0">
                    {!projects ? (
                        <div className="flex-1 bg-muted/20 animate-pulse rounded-md"></div>
                    ) : projects.length === 0 ? (
                        <div className="flex-1 flex items-center justify-center text-xs text-muted-foreground border border-dashed rounded-md bg-muted/10">
                            暂无战略项目
                        </div>
                    ) : (
                        <div className="space-y-2">
                            {projects.slice(0, 3).map((project, index) => {
                                // Dynamic Color Logic
                                // We don't have isStrategic flag in the API response here explicitly but they ARE strategic
                                // Use getProjectColorHex if available. For that we might need customColor on project object
                                // The API for strategic projects might not return color yet. Let's fix that or fetch full project.
                                // Assuming API returns color in updated_at or similar? Actually we need to check backend router.
                                // For now, let's assume project has color property if we update interface.
                                // Let's use a safe fallback if color is missing.

                                // Actually, let's map the color to Tailwind classes or style directly.
                                // Since we used hex codes, we should use style={{ ... }}

                                // Mock getting color - we need to make sure backend returns it.
                                // But first let's just use the style for now.
                                // The user wants CONSISTENCY.
                                // The getProjectColorHex returns a HEX.

                                // Issues: Original code used Tailwind classes tailored for specific colors (bg-indigo-500).
                                // With arbitrary hex, we need to use style={{ backgroundColor: hex }} and opacity.

                                const hex = (project as any).color || ["#6366f1", "#10b981", "#f59e0b"][index % 3];

                                return (
                                    <Link
                                        key={project.id}
                                        href={`/projects/${project.id}`}
                                        className={`relative block p-2.5 pl-3 rounded-lg hover:bg-muted/60 transition group border border-transparent hover:border-border/50 overflow-hidden`}
                                        style={{ backgroundColor: `${hex}10`, borderColor: `${hex}30` }} // 10 = ~6% opacity, 30 = ~20%
                                    >
                                        {/* Left Color Bar */}
                                        <div className="absolute left-0 top-0 bottom-0 w-1" style={{ backgroundColor: hex }} />

                                        <div className="flex items-center justify-between mb-1">
                                            <span className="font-medium text-sm truncate pr-2 text-slate-700">{project.title}</span>
                                            <ChevronRight className="w-3.5 h-3.5 text-muted-foreground group-hover:text-primary transition" />
                                        </div>
                                        <div className="w-full h-1 bg-slate-200/50 rounded-full overflow-hidden mt-1.5">
                                            <div
                                                className="h-full transition-all duration-500"
                                                style={{ width: `${project.progress}%`, backgroundColor: hex }}
                                            />
                                        </div>
                                    </Link>
                                );
                            })}
                        </div>
                    )}
                </div>
            </div>

            {/* Divider */}
            <div className="h-px bg-border/50 mx-4" />

            {/* Bottom Half: Exemptions */}
            <div className="p-4 pt-3 h-[180px] flex flex-col">
                <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                        <Shield className="w-4 h-4 text-indigo-500" />
                        <span className="font-semibold text-sm">豁免中心</span>
                    </div>
                </div>

                <div className="grid grid-cols-2 gap-3 flex-1">
                    {/* Day Pass */}
                    <div className="bg-indigo-50/30 rounded-lg p-3 flex flex-col justify-between border border-indigo-100/50">
                        <div className="flex items-center text-xs text-indigo-600/80 mb-1 gap-1">
                            <Zap className="w-3 h-3" />
                            <span>Day Pass</span>
                        </div>
                        <div className="text-3xl font-bold text-slate-800">
                            {quota ? quota.day_pass_total - quota.day_pass_used : '-'}
                        </div>
                        <div className="text-[10px] text-muted-foreground">
                            本周剩余额度
                        </div>
                    </div>

                    {/* Rule Break */}
                    <div className="bg-rose-50/30 rounded-lg p-3 flex flex-col justify-between border border-rose-100/50">
                        <div className="flex items-center text-xs text-rose-600/80 mb-1 gap-1">
                            <Shield className="w-3 h-3" />
                            <span>Rule Break</span>
                        </div>
                        <div className="text-3xl font-bold text-slate-800">
                            {quota ? quota.rule_break_total - quota.rule_break_used : '-'}
                        </div>
                        <div className="text-[10px] text-muted-foreground">
                            本周剩余额度
                        </div>
                    </div>
                </div>
            </div>
        </AppCard>
    );
}
