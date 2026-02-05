"use client";

import { RequireAuth } from "@/lib/auth-context";
import { AppLayout } from "@/components/layout/app-layout";
import { LoadingSkeleton, ExemptionsSkeleton } from "@/components/ui/empty-state";
import useSWR from "swr";
import { fetcher } from "@/lib/utils";
import { ExemptionQuota } from "@/types";
import { Shield, Calendar } from "lucide-react";

export default function ExemptionsPage() {
    return (
        <RequireAuth>
            <AppLayout>
                <ExemptionsContent />
            </AppLayout>
        </RequireAuth>
    );
}

function ExemptionsContent() {
    const { data: quota, error } = useSWR<ExemptionQuota>("/api/exemptions/quota", fetcher);
    const loading = !quota && !error;

    return (
        <div className="p-6 max-w-3xl mx-auto space-y-6">
            <div className="flex items-center gap-3">
                <Shield className="w-8 h-8" />
                <h1 className="text-2xl font-bold">豁免中心</h1>
            </div>

            {loading ? (
                <ExemptionsSkeleton />
            ) : quota ? (
                <>
                    <div className="bg-card border border-border rounded-lg p-6">
                        <h2 className="text-sm font-medium text-muted-foreground mb-4 flex items-center gap-2">
                            <Calendar className="w-4 h-4" />
                            本周额度
                        </h2>
                        <div className="grid grid-cols-2 gap-8">
                            <div>
                                <p className="text-xs text-muted-foreground mb-2">Day Pass (暂停逾期判定24h)</p>
                                <p className="text-5xl font-mono font-bold mb-1">
                                    {quota.day_pass_total - quota.day_pass_used}
                                </p>
                                <p className="text-sm text-muted-foreground">剩余 / 共 {quota.day_pass_total} 次</p>
                            </div>
                            <div>
                                <p className="text-xs text-muted-foreground mb-2">Rule Break (转任务为EXCUSED)</p>
                                <p className="text-5xl font-mono font-bold mb-1">
                                    {quota.rule_break_total - quota.rule_break_used}
                                </p>
                                <p className="text-sm text-muted-foreground">剩余 / 共 {quota.rule_break_total} 次</p>
                            </div>
                        </div>
                    </div>

                    <div className="bg-warning/5 border border-warning/30 rounded-lg p-4">
                        <p className="text-sm text-warning-muted">
                            <strong>提示：</strong>使用豁免会永久记录并扣除额度。请谨慎使用，避免滥用。
                        </p>
                    </div>
                </>
            ) : null}
        </div>
    );
}
