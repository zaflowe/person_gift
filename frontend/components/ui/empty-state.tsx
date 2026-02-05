"use client";

import { ReactNode } from "react";
import { Inbox } from "lucide-react";

interface EmptyStateProps {
    icon?: ReactNode;
    title: string;
    description?: string;
    action?: ReactNode;
}

export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
    return (
        <div className="flex flex-col items-center justify-center py-16 px-4 text-center">
            <div className="text-muted-foreground mb-4">
                {icon || <Inbox className="w-12 h-12" />}
            </div>
            <h3 className="text-lg font-medium mb-2">{title}</h3>
            {description && (
                <p className="text-sm text-muted-foreground max-w-md mb-6">{description}</p>
            )}
            {action}
        </div>
    );
}

export function LoadingSkeleton({ count = 3 }: { count?: number }) {
    return (
        <div className="space-y-3">
            {Array.from({ length: count }).map((_, i) => (
                <div key={i} className="animate-pulse">
                    <div className="h-24 bg-muted rounded-lg"></div>
                </div>
            ))}
        </div>
    );
}

export function LoadingSpinner({ className }: { className?: string }) {
    return (
        <div className={className}>
            <div className="animate-spin rounded-full h-8 w-8 border-2 border-muted border-t-foreground"></div>
        </div>
    );
}

// Custom Skeletons

export function TasksSkeleton() {
    return (
        <div className="space-y-4">
            {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="p-4 border rounded-lg animate-pulse flex justify-between items-start">
                    <div className="space-y-2 flex-1">
                        <div className="h-5 w-1/3 bg-slate-200 rounded"></div>
                        <div className="h-4 w-2/3 bg-slate-100 rounded"></div>
                        <div className="flex gap-2 pt-1">
                            <div className="h-3 w-16 bg-slate-100 rounded"></div>
                            <div className="h-3 w-16 bg-slate-100 rounded"></div>
                        </div>
                    </div>
                    <div className="h-6 w-16 bg-slate-200 rounded-full ml-4"></div>
                </div>
            ))}
        </div>
    );
}

export function ProjectsSkeleton() {
    return (
        <div className="space-y-8">
            <div className="space-y-3">
                <div className="h-4 w-20 bg-slate-200 rounded animate-pulse mb-2"></div>
                {Array.from({ length: 2 }).map((_, i) => (
                    <div key={i} className="p-4 border rounded-lg animate-pulse flex justify-between">
                        <div className="space-y-2 flex-1">
                            <div className="h-5 w-1/4 bg-slate-200 rounded"></div>
                            <div className="h-4 w-1/2 bg-slate-100 rounded"></div>
                        </div>
                        <div className="h-6 w-16 bg-slate-200 rounded-full ml-4"></div>
                    </div>
                ))}
            </div>
            <div className="space-y-3">
                <div className="h-4 w-20 bg-slate-200 rounded animate-pulse mb-2"></div>
                <div className="p-4 border rounded-lg animate-pulse h-24"></div>
            </div>
        </div>
    );
}

export function ExemptionsSkeleton() {
    return (
        <div className="space-y-6">
            <div className="p-6 border rounded-lg animate-pulse">
                <div className="h-5 w-24 bg-slate-200 rounded mb-6"></div>
                <div className="grid grid-cols-2 gap-8">
                    <div className="space-y-3">
                        <div className="h-3 w-32 bg-slate-100 rounded"></div>
                        <div className="h-12 w-16 bg-slate-200 rounded"></div>
                        <div className="h-3 w-24 bg-slate-100 rounded"></div>
                    </div>
                    <div className="space-y-3">
                        <div className="h-3 w-32 bg-slate-100 rounded"></div>
                        <div className="h-12 w-16 bg-slate-200 rounded"></div>
                        <div className="h-3 w-24 bg-slate-100 rounded"></div>
                    </div>
                </div>
            </div>
        </div>
    );
}

export function ScheduleSkeleton() {
    return (
        <div className="flex h-full bg-slate-50">
            {/* Header placeholder - not strictly needed as page header might be outside, but let's match internal structure */}

            {/* Main Layout: Row */}
            <div className="flex-1 flex overflow-hidden">
                {/* Scrollable Schedule Grid Skeleton */}
                <div className="flex-1 flex overflow-x-auto bg-white border-r border-slate-200">
                    {/* Time Labels Column */}
                    <div className="w-16 shrink-0 flex flex-col pt-12 border-r border-slate-100 bg-white sticky left-0 z-20">
                        {Array.from({ length: 9 }).map((_, i) => (
                            <div key={i} className="flex-1 min-h-[80px] border-b border-transparent relative">
                                <div className="absolute -top-3 right-2 h-3 w-8 bg-slate-100 rounded"></div>
                            </div>
                        ))}
                    </div>

                    {/* Day Columns */}
                    {Array.from({ length: 5 }).map((_, i) => (
                        <div key={i} className="flex-none w-60 flex flex-col border-r border-slate-100/50 shrink-0 bg-white">
                            {/* Date Header */}
                            <div className="h-12 flex items-center justify-center border-b border-slate-200/50">
                                <div className="flex flex-col items-center space-y-1">
                                    <div className="h-2 w-8 bg-slate-100 rounded"></div>
                                    <div className="h-4 w-6 bg-slate-200 rounded"></div>
                                </div>
                            </div>
                            {/* Time Blocks */}
                            <div className="flex-1 flex flex-col">
                                {Array.from({ length: 9 }).map((_, j) => (
                                    <div key={j} className="border-b border-slate-100/50 p-1.5 flex-1 min-h-[80px] flex flex-col space-y-2">
                                        {/* Random skeleton tasks */}
                                        {Math.random() > 0.7 && (
                                            <div className="h-8 bg-slate-50 border border-slate-100 rounded w-full"></div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        </div>
                    ))}
                </div>

                {/* Right Sidebar Skeleton (Fixed 380px) */}
                <div className="w-[380px] shrink-0 border-l border-slate-200 bg-white flex flex-col z-20">
                    {/* Upper Half: Habits */}
                    <div className="h-1/2 overflow-hidden flex flex-col p-4 space-y-4">
                        <div className="flex justify-between items-center">
                            <div className="h-6 w-24 bg-slate-200 rounded"></div>
                            <div className="h-8 w-8 bg-slate-100 rounded"></div>
                        </div>
                        <div className="space-y-2">
                            {Array.from({ length: 3 }).map((_, i) => (
                                <div key={i} className="h-16 bg-slate-50 border border-slate-100 rounded-lg"></div>
                            ))}
                        </div>
                    </div>

                    {/* Lower Half: Fixed Blocks */}
                    <div className="h-1/2 overflow-hidden flex flex-col border-t border-slate-200 p-4 space-y-4">
                        <div className="flex justify-between items-center">
                            <div className="h-6 w-24 bg-slate-200 rounded"></div>
                            <div className="h-8 w-8 bg-slate-100 rounded"></div>
                        </div>
                        <div className="space-y-2">
                            {Array.from({ length: 2 }).map((_, i) => (
                                <div key={i} className="h-16 bg-slate-50 border border-slate-100 rounded-lg"></div>
                            ))}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
