"use client";

import { CheckCircle2, Calendar, FileText } from "lucide-react";
import type { PlanResponse } from "@/lib/api/planner";

interface PlanPreviewProps {
    plan: PlanResponse["plan"];
    onConfirm: () => void;
    onCancel: () => void;
    loading?: boolean;
}

export default function PlanPreview({ plan, onConfirm, onCancel, loading }: PlanPreviewProps) {
    return (
        <div className="bg-muted/50 border border-border rounded-lg p-4 space-y-3">
            {/* Project */}
            <div>
                <div className="flex items-center gap-2 mb-2">
                    <FileText className="w-4 h-4 text-info" />
                    <h4 className="font-semibold text-sm">项目</h4>
                </div>
                <div className="bg-card border border-border rounded-sm p-3">
                    <p className="font-medium">{plan.project.title}</p>
                    {plan.project.description && (
                        <p className="text-xs text-muted-foreground mt-1">
                            {plan.project.description}
                        </p>
                    )}
                </div>
            </div>

            {/* Tasks */}
            <div>
                <div className="flex items-center gap-2 mb-2">
                    <CheckCircle2 className="w-4 h-4 text-success" />
                    <h4 className="font-semibold text-sm">任务 ({plan.tasks.length})</h4>
                </div>
                <div className="space-y-2 max-h-48 overflow-y-auto">
                    {plan.tasks.map((task, idx) => (
                        <div
                            key={idx}
                            className="bg-card border border-border rounded-sm p-2 text-xs"
                        >
                            <p className="font-medium">{task.title}</p>
                            {task.description && (
                                <p className="text-muted-foreground mt-1 line-clamp-1">
                                    {task.description}
                                </p>
                            )}
                            <div className="flex items-center gap-2 mt-1 text-muted-foreground">
                                <Calendar className="w-3 h-3" />
                                <span>
                                    {new Date(task.due_at).toLocaleDateString("zh-CN", {
                                        month: "short",
                                        day: "numeric",
                                    })}
                                </span>
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* Rationale */}
            {plan.rationale && (
                <div className="text-xs text-muted-foreground italic border-l-2 border-muted pl-2">
                    {plan.rationale}
                </div>
            )}

            {/* Actions */}
            <div className="flex gap-2 pt-2">
                <button
                    onClick={onConfirm}
                    disabled={loading}
                    className="flex-1 px-3 py-2 bg-success text-white rounded-sm hover:bg-opacity-90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium"
                >
                    {loading ? "创建中..." : "确认并创建"}
                </button>
                <button
                    onClick={onCancel}
                    disabled={loading}
                    className="px-3 py-2 bg-muted text-foreground rounded-sm hover:bg-opacity-80 transition-colors disabled:opacity-50 disabled:cursor-not-allowed text-sm"
                >
                    取消
                </button>
            </div>
        </div>
    );
}
