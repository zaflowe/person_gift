"use client";

import { ReactNode, useState } from "react";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

interface ConfirmDialogProps {
    trigger: ReactNode;
    title: string;
    description: string;
    consequence?: string;
    confirmText?: string;
    cancelText?: string;
    onConfirm: () => void | Promise<void>;
    variant?: "default" | "danger";
}

export function ConfirmDialog({
    trigger,
    title,
    description,
    consequence,
    confirmText = "确认",
    cancelText = "取消",
    onConfirm,
    variant = "default",
}: ConfirmDialogProps) {
    const [open, setOpen] = useState(false);
    const [loading, setLoading] = useState(false);

    const handleConfirm = async () => {
        setLoading(true);
        try {
            await onConfirm();
            setOpen(false);
        } catch (error) {
            console.error(error);
        } finally {
            setLoading(false);
        }
    };

    return (
        <>
            <div onClick={() => setOpen(true)}>{trigger}</div>

            {open && (
                <div className="fixed inset-0 z-50 flex items-center justify-center animate-fade-in">
                    {/* Backdrop */}
                    <div
                        className="absolute inset-0 bg-gray-950/50 backdrop-blur-sm"
                        onClick={() => !loading && setOpen(false)}
                    />

                    {/* Dialog */}
                    <div className="relative bg-card border border-border rounded-lg shadow-2xl max-w-md w-full mx-4 animate-slide-up">
                        {/* Header */}
                        <div className="flex items-center justify-between p-5 border-b border-border">
                            <h3 className="text-lg font-semibold">{title}</h3>
                            <button
                                onClick={() => !loading && setOpen(false)}
                                className="text-muted-foreground hover:text-foreground transition-colors"
                                disabled={loading}
                            >
                                <X className="w-5 h-5" />
                            </button>
                        </div>

                        {/* Content */}
                        <div className="p-5 space-y-3">
                            <p className="text-sm text-muted-foreground leading-relaxed">
                                {description}
                            </p>
                            {consequence && (
                                <div className={cn(
                                    "p-3 rounded-sm border text-xs font-mono",
                                    variant === "danger"
                                        ? "bg-error/5 border-error/20 text-error-muted"
                                        : "bg-warning/5 border-warning/20 text-warning-muted"
                                )}>
                                    <span className="font-bold">后果：</span> {consequence}
                                </div>
                            )}
                        </div>

                        {/* Actions */}
                        <div className="flex items-center gap-3 p-5 border-t border-border">
                            <button
                                onClick={() => setOpen(false)}
                                disabled={loading}
                                className="flex-1 px-4 py-2 text-sm font-medium border border-border rounded-sm hover:bg-muted transition-colors disabled:opacity-50"
                            >
                                {cancelText}
                            </button>
                            <button
                                onClick={handleConfirm}
                                disabled={loading}
                                className={cn(
                                    "flex-1 px-4 py-2 text-sm font-medium rounded-sm transition-colors disabled:opacity-50",
                                    variant === "danger"
                                        ? "bg-error text-white hover:bg-error-muted"
                                        : "bg-foreground text-background hover:bg-gray-700"
                                )}
                            >
                                {loading ? "处理中..." : confirmText}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </>
    );
}
