"use client";

import { RequireAuth } from "@/lib/auth-context";
import { AppLayout } from "@/components/layout/app-layout";
import { StatusBadge } from "@/components/ui/status-badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { apiPost, fetcher } from "@/lib/utils";
import { Task } from "@/types";
import { ArrowLeft, CheckCircle, Clock, Shield, Upload, AlertTriangle, FileText } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import useSWR from "swr";

export default function TaskDetailPage() {
    return (
        <RequireAuth>
            <AppLayout>
                <TaskDetailContent />
            </AppLayout>
        </RequireAuth>
    );
}

function TaskDetailContent() {
    const params = useParams();
    const router = useRouter();
    const id = params.id as string;
    const { data: task, error, mutate: reloadTask } = useSWR<Task>(id ? `/api/tasks/${id}` : null, fetcher);

    const [submitting, setSubmitting] = useState(false);
    const [evidenceContent, setEvidenceContent] = useState("");
    const [evidenceFile, setEvidenceFile] = useState<File | null>(null);
    const [submitResult, setSubmitResult] = useState<{ result: string, reason: string } | null>(null);

    if (error) return <div className="p-6 text-red-500">Loading failed</div>;
    if (!task) return <div className="p-6">Loading...</div>;

    const isReviewable = task.status === "OPEN" || task.status === "OVERDUE" || task.status === "EVIDENCE_SUBMITTED";

    // Handle Evidence Submission
    const handleSubmitEvidence = async (e: React.FormEvent) => {
        e.preventDefault();
        setSubmitting(true);
        setSubmitResult(null);

        try {
            const formData = new FormData();
            formData.append("evidence_type", task.evidence_type || "text");
            if (evidenceContent) formData.append("content", evidenceContent);
            if (evidenceFile) formData.append("image", evidenceFile);

            // Note: apiPost helper might not handle FormData with files correctly if not tweaked, 
            // so we use raw fetch for multipart/form-data to be safe or ensure apiPost handles it.
            // Here using the auth-context style fetch logic for safety.
            const token = localStorage.getItem("token");
            const res = await fetch(`/api/tasks/${id}/submit-evidence`, {
                method: "POST",
                headers: {
                    "Authorization": `Bearer ${token}`
                },
                body: formData
            });

            if (!res.ok) {
                const err = await res.json();
                let errorMessage = err.detail || "提交失败";

                // Handle Pydantic validation errors (arrays/objects)
                if (typeof errorMessage === 'object') {
                    errorMessage = JSON.stringify(errorMessage, null, 2);
                }

                throw new Error(errorMessage);
            }

            const result = await res.json();
            // result is TaskEvidence, possibly containing ai_result
            setSubmitResult({
                result: result.ai_result || "pending",
                reason: result.ai_reason || "等待 AI 审核...",
            });

            // Clear inputs
            setEvidenceContent("");
            setEvidenceFile(null);
            reloadTask();
        } catch (err: any) {
            alert(err.message);
        } finally {
            setSubmitting(false);
        }
    };

    // Handle Direct Completion (No Evidence)
    const handleComplete = async () => {
        if (!confirm("确认完成此任务？")) return;
        setSubmitting(true);
        try {
            await apiPost(`/api/tasks/${id}/complete`, {});
            reloadTask();
            router.push("/tasks");
        } catch (err: any) {
            alert(err.message);
        } finally {
            setSubmitting(false);
        }
    };

    // Handle Exemption (Day Pass)
    const handleUsePass = async () => {
        if (!confirm("确认消耗一张 Day Pass 来豁免此任务？")) return;
        try {
            await apiPost("/api/exemptions/use", {
                exemption_type: "day_pass",
                task_id: id,
                reason: "Manual exemption via Day Pass"
            });
            reloadTask();
        } catch (err: any) {
            alert(err.message);
        }
    };

    return (
        <div className="max-w-4xl mx-auto p-6 space-y-6">
            {/* Header */}
            <div className="flex items-center gap-4">
                <Link href="/tasks" className="p-2 hover:bg-muted rounded-full">
                    <ArrowLeft className="w-5 h-5" />
                </Link>
                <div>
                    <h1 className="text-2xl font-bold break-all">{task.title}</h1>
                    <div className="flex items-center gap-2 text-muted-foreground mt-1">
                        <Clock className="w-4 h-4" />
                        <span className="text-sm">Deadline: {task.deadline ? new Date(task.deadline).toLocaleString() : "None"}</span>
                    </div>
                </div>
                <div className="ml-auto">
                    <StatusBadge status={task.status} type="task" className="text-lg px-3 py-1" />
                </div>
            </div>

            {/* Description */}
            <div className="bg-card border border-border rounded-lg p-6">
                <h2 className="font-medium mb-2">任务描述</h2>
                <p className="text-muted-foreground whitespace-pre-wrap">{task.description || "无描述"}</p>

                <div className="mt-6 grid grid-cols-2 gap-4 text-sm">
                    <div className="p-3 bg-muted/50 rounded">
                        <span className="text-muted-foreground block mb-1">证据要求</span>
                        <span className="font-medium">{task.evidence_type === "none" ? "无需证据" : task.evidence_type}</span>
                    </div>
                    <div className="p-3 bg-muted/50 rounded">
                        <span className="text-muted-foreground block mb-1">审核标准</span>
                        <span className="font-medium">{task.evidence_criteria || "自动审核"}</span>
                    </div>
                </div>
            </div>

            {/* AI Feedback Area */}
            {submitResult && (
                <Alert variant={submitResult.result === "pass" ? "default" : "destructive"} className={submitResult.result === "pass" ? "border-success/50 bg-success/10" : ""}>
                    {submitResult.result === "pass" ? <CheckCircle className="h-4 w-4 text-success" /> : <AlertTriangle className="h-4 w-4" />}
                    <AlertTitle>{submitResult.result === "pass" ? "审核通过" : "审核拒绝"}</AlertTitle>
                    <AlertDescription>
                        AI 意见: {submitResult.reason}
                    </AlertDescription>
                </Alert>
            )}

            {/* Action Area */}
            {isReviewable && (
                <div className="bg-card border border-border rounded-lg p-6 shadow-sm">
                    <h2 className="font-semibold mb-4 flex items-center gap-2">
                        <Upload className="w-5 h-5" />
                        {task.evidence_type === "none" ? "完成任务" : "提交证据"}
                        <div className="ml-auto">
                            {/* Exemption Button */}
                            <button
                                onClick={handleUsePass}
                                className="text-sm text-muted-foreground hover:text-primary flex items-center gap-1"
                            >
                                <Shield className="w-4 h-4" />
                                使用 Day Pass
                            </button>
                        </div>
                    </h2>

                    {task.evidence_type === "none" ? (
                        <button
                            onClick={handleComplete}
                            disabled={submitting}
                            className="w-full py-3 bg-primary text-primary-foreground hover:bg-primary/90 rounded-md font-medium transition-colors disabled:opacity-50"
                        >
                            {submitting ? "处理中..." : "直接完成任务"}
                        </button>
                    ) : (
                        <form onSubmit={handleSubmitEvidence} className="space-y-4">
                            {(task.evidence_type === "text" || task.evidence_type === "number") && (
                                <div>
                                    <label className="block text-sm font-medium mb-1">
                                        {task.evidence_type === "number" ? "数值" : "文本内容"}
                                    </label>
                                    <textarea
                                        value={evidenceContent}
                                        onChange={e => setEvidenceContent(e.target.value)}
                                        className="w-full p-2 bg-background border border-border rounded-md min-h-[100px]"
                                        placeholder="在此输入证据内容(AI 将会审核)"
                                        required
                                    />
                                </div>
                            )}

                            {task.evidence_type === "image" && (
                                <div>
                                    <label className="block text-sm font-medium mb-1">上传图片证据</label>
                                    <div className="border-2 border-dashed border-input rounded-md p-6 text-center hover:bg-muted/50 transition-colors">
                                        <input
                                            type="file"
                                            accept="image/*"
                                            onChange={e => setEvidenceFile(e.target.files?.[0] || null)}
                                            className="hidden"
                                            id="evidence-file"
                                            required
                                        />
                                        <label htmlFor="evidence-file" className="cursor-pointer flex flex-col items-center gap-2">
                                            <Upload className="w-8 h-8 text-muted-foreground" />
                                            <span className="text-sm text-muted-foreground">
                                                {evidenceFile ? evidenceFile.name : "点击上传或拖拽图片"}
                                            </span>
                                        </label>
                                    </div>
                                </div>
                            )}

                            <button
                                type="submit"
                                disabled={submitting}
                                className="w-full py-2 bg-primary text-primary-foreground hover:bg-primary/90 rounded-md font-medium transition-colors disabled:opacity-50"
                            >
                                {submitting ? "正在提交 AI 审核..." : "提交并审核"}
                            </button>
                        </form>
                    )}
                </div>
            )}
        </div>
    );
}
