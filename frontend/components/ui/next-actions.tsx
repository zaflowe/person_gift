"use client";

import { ReactNode } from "react";
import { AlertCircle, AlertTriangle, Info } from "lucide-react";
import { cn } from "@/lib/utils";
import { NextAction } from "@/types";
import Link from "next/link";

interface NextActionsProps {
    actions: NextAction[];
}

const priorityConfig = {
    high: {
        icon: AlertCircle,
        bg: "bg-error/5",
        border: "border-error/30",
        text: "text-error-muted",
    },
    medium: {
        icon: AlertTriangle,
        bg: "bg-warning/5",
        border: "border-warning/30",
        text: "text-warning-muted",
    },
    low: {
        icon: Info,
        bg: "bg-muted",
        border: "border-border",
        text: "text-muted-foreground",
    },
};

export function NextActions({ actions }: NextActionsProps) {
    if (actions.length === 0) return null;

    // 最多显示 3 个，按优先级排序
    const displayActions = actions.slice(0, 3);

    return (
        <div className="mb-6 space-y-2">
            <h2 className="text-sm font-medium text-muted-foreground uppercase tracking-wide">
                下一步行动
            </h2>
            <div className="space-y-2">
                {displayActions.map((action) => (
                    <ActionCard key={action.id} action={action} />
                ))}
            </div>
        </div>
    );
}

function ActionCard({ action }: { action: NextAction }) {
    const config = priorityConfig[action.priority];
    const Icon = config.icon;

    const content = (
        <div
            className={cn(
                "flex items-start gap-3 p-4 rounded-lg border transition-all duration-200",
                config.bg,
                config.border,
                (action.href || action.onClick) && "hover:border-foreground/20 hover:shadow-sm cursor-pointer active:scale-[0.99]"
            )}
        >
            <Icon className={cn("w-5 h-5 mt-0.5 flex-shrink-0", config.text)} />
            <div className="flex-1 min-w-0">
                <h3 className="font-medium mb-0.5 text-foreground">{action.title}</h3>
                <p className="text-sm text-muted-foreground">{action.action}</p>
            </div>
            {(action.href || action.onClick) && (
                <div className="self-center">
                    <span className="text-xs text-muted-foreground opacity-50">→</span>
                </div>
            )}
        </div>
    );

    if (action.href) {
        return <Link href={action.href}>{content}</Link>;
    }

    if (action.onClick) {
        return (
            <button className="w-full text-left focus:outline-none" onClick={action.onClick}>
                {content}
            </button>
        );
    }

    return content;
}
