"use client";

import { ReactNode } from "react";
import { formatDateTime } from "@/lib/utils";
import { Circle } from "lucide-react";

export interface TimelineEvent {
    id: string;
    type: "status" | "evidence" | "exemption" | "comment";
    title: string;
    description?: string;
    timestamp: string;
    icon?: ReactNode;
}

interface TimelineProps {
    events: TimelineEvent[];
}

export function Timeline({ events }: TimelineProps) {
    if (events.length === 0) {
        return (
            <div className="text-center py-8 text-sm text-muted-foreground">
                暂无记录
            </div>
        );
    }

    return (
        <div className="space-y-4">
            {events.map((event, index) => (
                <div key={event.id} className="relative flex gap-4">
                    {/* Timeline line */}
                    {index < events.length - 1 && (
                        <div className="absolute left-2 top-8 bottom-0 w-px bg-border" />
                    )}

                    {/* Icon */}
                    <div className="relative flex-shrink-0 w-4 h-4 mt-1">
                        {event.icon || <Circle className="w-4 h-4 text-muted-foreground fill-current" />}
                    </div>

                    {/* Content */}
                    <div className="flex-1 pb-4">
                        <div className="flex items-baseline justify-between mb-1">
                            <h4 className="font-medium text-sm">{event.title}</h4>
                            <time className="text-xs text-muted-foreground font-mono">
                                {formatDateTime(event.timestamp)}
                            </time>
                        </div>
                        {event.description && (
                            <p className="text-sm text-muted-foreground leading-relaxed">
                                {event.description}
                            </p>
                        )}
                    </div>
                </div>
            ))}
        </div>
    );
}
