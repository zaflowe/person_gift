"use client";

import { cn } from "@/lib/utils";

interface AppCardProps extends React.HTMLAttributes<HTMLDivElement> {
    children: React.ReactNode;
    className?: string;
    noPadding?: boolean;
}

export function AppCard({ children, className, noPadding, ...props }: AppCardProps) {
    return (
        <div
            className={cn(
                "bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius)] shadow-[var(--shadow-card)]",
                "hover:translate-y-[-2px] hover:shadow-[var(--shadow-float)] transition-all duration-200 ease-out",
                !noPadding && "p-5",
                className
            )}
            {...props}
        >
            {children}
        </div>
    );
}

interface AppCardHeaderProps {
    children: React.ReactNode;
    className?: string;
    action?: React.ReactNode;
}

export function AppCardHeader({ children, className, action }: AppCardHeaderProps) {
    return (
        <div className={cn("flex items-center justify-between mb-4", className)}>
            <h3 className="text-[var(--text)] font-semibold text-[16px] tracking-tight truncate">
                {children}
            </h3>
            {action && (
                <div className="shrink-0 ml-2">
                    {action}
                </div>
            )}
        </div>
    );
}
