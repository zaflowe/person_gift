"use client";

import { useState, useEffect } from "react";
import { Play, Pause, Square, AlertCircle, RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";

interface FocusTimerProps {
    durationSec: number;
    isPaused: boolean;
    onPause: () => void;
    onResume: () => void;
    onComplete: () => void;
    onAbandon: () => void;
    contextLabel: string; // Project Name > Task Title or Label
    subContextLabel?: string; // Task Title (if project is main)
}

export function FocusTimer({
    durationSec,
    isPaused,
    onPause,
    onResume,
    onComplete,
    onAbandon,
    contextLabel,
    subContextLabel,
}: FocusTimerProps) {

    // Format H:MM:SS
    const formatTime = (totalSec: number) => {
        const h = Math.floor(totalSec / 3600);
        const m = Math.floor((totalSec % 3600) / 60);
        const s = totalSec % 60;

        if (h > 0) {
            return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
        }
        return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
    };

    return (
        <div className="flex flex-col items-center justify-between h-full max-w-2xl mx-auto py-12 px-6">

            {/* Header / Context */}
            <div className="text-center space-y-2 animate-fade-in">
                <h2 className="text-sm font-medium text-muted-foreground uppercase tracking-widest">
                    Focus Mode
                </h2>
                <div className="space-y-1">
                    <h1 className="text-2xl md:text-3xl font-bold text-foreground">
                        {contextLabel}
                    </h1>
                    {subContextLabel && (
                        <p className="text-lg text-primary">
                            {subContextLabel}
                        </p>
                    )}
                </div>
            </div>

            {/* Timer Display */}
            <div className="flex-1 flex items-center justify-center w-full my-12">
                <div className={cn(
                    "relative font-mono text-[15vw] md:text-[180px] leading-none tracking-tighter transition-colors duration-500 select-none",
                    isPaused ? "text-muted-foreground opacity-50" : "text-foreground"
                )}>
                    {formatTime(durationSec)}

                    {/* Pulsing indicator when running */}
                    {!isPaused && (
                        <div className="absolute -right-4 top-1/2 -translate-y-1/2 w-2 h-2 md:w-4 md:h-4 bg-primary rounded-full animate-pulse" />
                    )}
                </div>
            </div>

            {/* Controls */}
            <div className="w-full max-w-md space-y-8 animate-slide-up">

                {/* Main Action */}
                <div className="flex justify-center gap-6">
                    {!isPaused ? (
                        <button
                            onClick={onPause}
                            className="w-24 h-24 rounded-full bg-surface border border-border flex items-center justify-center hover:bg-muted hover:scale-105 transition-all duration-200 group"
                        >
                            <Pause className="w-8 h-8 md:w-10 md:h-10 text-foreground group-hover:text-primary transition-colors" />
                        </button>
                    ) : (
                        <button
                            onClick={onResume}
                            className="w-24 h-24 rounded-full bg-primary text-background flex items-center justify-center hover:bg-primary/90 hover:scale-105 transition-all duration-200 shadow-lg shadow-primary/20"
                        >
                            <Play className="w-8 h-8 md:w-10 md:h-10 ml-1" fill="currentColor" />
                        </button>
                    )}
                </div>

                {/* Secondary Actions */}
                <div className="flex justify-between items-center pt-8 border-t border-dashed border-border/50">
                    <button
                        onClick={onAbandon}
                        className="flex items-center gap-2 text-sm text-muted-foreground hover:text-error transition-colors px-4 py-2 rounded hover:bg-error/5"
                    >
                        <AlertCircle className="w-4 h-4" />
                        放弃 (Abandon)
                    </button>

                    <button
                        onClick={onComplete}
                        className="flex items-center gap-2 text-sm font-medium bg-foreground text-background px-6 py-2.5 rounded-full hover:bg-gray-700 transition-colors shadow-sm"
                    >
                        <Square className="w-4 h-4 fill-current" />
                        结束并记录 (Finish)
                    </button>
                </div>
            </div>

        </div>
    );
}
