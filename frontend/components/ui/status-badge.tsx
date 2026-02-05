"use client";

import { TaskStatus, ProjectStatus } from "@/types";
import { TASK_STATUS_MAP, PROJECT_STATUS_MAP, cn } from "@/lib/utils";

interface StatusBadgeProps {
    status: TaskStatus | ProjectStatus;
    type: "task" | "project";
    className?: string;
}

const colorClasses = {
    success: "bg-success/10 text-success-muted border-success/20",
    error: "bg-error/10 text-error-muted border-error/20",
    warning: "bg-warning/10 text-warning-muted border-warning/20",
    info: "bg-info/10 text-info-muted border-info/20",
    purple: "bg-purple/10 text-purple-muted border-purple/20",
    muted: "bg-muted text-muted-foreground border-border",
};

export function StatusBadge({ status, type, className }: StatusBadgeProps) {
    const config = type === "task"
        ? TASK_STATUS_MAP[status as TaskStatus]
        : PROJECT_STATUS_MAP[status as ProjectStatus];

    if (!config) return null;

    const colorClass = colorClasses[config.color as keyof typeof colorClasses] || colorClasses.muted;

    return (
        <span
            className={cn(
                "inline-flex items-center px-2.5 py-0.5 rounded-sm text-xs font-medium border font-mono tracking-tight",
                colorClass,
                className
            )}
        >
            {config.label}
        </span>
    );
}
