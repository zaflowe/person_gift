"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { MessageCircle, X, Send, Loader2, RotateCcw } from "lucide-react";
import { AppCard } from "@/components/ui/app-card";
import { getToken, cn, fetcher, apiPost, API_BASE_URL } from "@/lib/utils";
import { sendChatMessage, requestLoginGreeting } from "@/lib/api/conversation";
import { commitPlan } from "@/lib/api/planner";
import { createQuickTask } from "@/lib/api/tasks";

type Message = {
    role: "user" | "assistant";
    content: string;
};

interface ConversationState {
    conversation_id: string;
    messages: Message[];
    stage: string;
    intent: string | null;
    planning_session_id?: string | null;
}

interface PlanTask {
    title: string;
    due_at: string;
    description?: string;
    [key: string]: unknown;
}

interface PlanMilestone {
    title: string;
    due_at?: string;
    description?: string;
    [key: string]: unknown;
}

interface PlanLongTask {
    title: string;
    frequency_mode?: string;
    interval_days?: number;
    days_of_week?: number[];
    total_cycle_days?: number;
    default_start_time?: string;
    default_end_time?: string;
    evidence_type?: string;
    evidence_criteria?: string;
    [key: string]: unknown;
}

interface ProjectPlan {
    project: {
        title: string;
        description?: string;
        [key: string]: unknown;
    };
    tasks: PlanTask[];
    milestones?: PlanMilestone[];
    long_tasks?: PlanLongTask[];
}

interface PlanSession {
    session_id: string;
    plan: ProjectPlan;
}

interface QuickTaskDraft {
    title: string;
    description?: string;
    deadline?: string;
    evidence_type?: string;
    [key: string]: unknown;
}

interface ProjectBrief {
    goal?: string;
    user_answer?: string;
    deadline?: string;
    [key: string]: unknown;
}

export default function ChatPlanner({ embedded = false, className }: { embedded?: boolean; className?: string }) {
    const router = useRouter();
    const [isOpen, setIsOpen] = useState(embedded);
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState("");
    const inputRef = useRef<HTMLTextAreaElement | null>(null);
    const [loading, setLoading] = useState(false);
    const [conversationId, setConversationId] = useState<string | undefined>();
    const [currentPlan, setCurrentPlan] = useState<PlanSession | null>(null);
    const [draftTask, setDraftTask] = useState<QuickTaskDraft | null>(null);
    const [projectBrief, setProjectBrief] = useState<ProjectBrief | null>(null);
    const [error, setError] = useState<string | null>(null);
    const messagesRef = useRef<HTMLDivElement | null>(null);

    const safePlan = currentPlan?.plan ?? { project: { title: "", description: "" }, tasks: [] as PlanTask[] };
    const safeProject = safePlan.project ?? { title: "", description: "" };
    const safeTasks = Array.isArray(safePlan.tasks) ? safePlan.tasks : [];
    const safeMilestones = Array.isArray(safePlan.milestones) ? safePlan.milestones : [];
    const safeLongTasks = Array.isArray(safePlan.long_tasks) ? safePlan.long_tasks : [];

    const normalizePlanSession = (session: PlanSession | null): PlanSession | null => {
        if (!session || !session.plan) return null;
        const rawPlan = session.plan as unknown as Record<string, unknown>;
        const rawProject = (rawPlan as any).project || {};
        const safeProject = {
            ...rawProject,
            title: rawProject.title || (rawPlan as any).project_title || (rawPlan as any).title || "",
            description: rawProject.description || (rawPlan as any).description || "",
        };
        const safeTasks = Array.isArray((rawPlan as any).tasks)
            ? (rawPlan as any).tasks.map((task: any) => ({
                ...task,
                due_at: task?.due_at || task?.deadline || "",
            }))
            : [];
        const safeMilestones = Array.isArray((rawPlan as any).milestones)
            ? (rawPlan as any).milestones.map((m: any) => ({
                ...m,
                due_at: m?.due_at || m?.deadline || "",
            }))
            : [];
        const safeLongTasks = Array.isArray((rawPlan as any).long_tasks) ? (rawPlan as any).long_tasks : [];
        return {
            ...session,
            plan: {
                ...(rawPlan as any),
                project: safeProject,
                tasks: safeTasks,
                milestones: safeMilestones,
                long_tasks: safeLongTasks,
            },
        };
    };

    // Initial Load - Persistence
    useEffect(() => {
        if (!isOpen) return;

        const loadConversation = async () => {
            const token = getToken();
            if (!token) return;

            try {
                const data = await fetcher<ConversationState>("/api/conversation/current");
                setConversationId(data.conversation_id);
                setMessages(data.messages);

                // Restore plan draft if we are in planning stage
                if (data.stage === "planning") {
                    try {
                        const planUrl = data.planning_session_id
                            ? `${API_BASE_URL}/planner/${data.planning_session_id}`
                            : `${API_BASE_URL}/planner/latest`;
                        const res = await fetch(planUrl, {
                            headers: { Authorization: `Bearer ${token}` }
                        });
                        if (res.ok) {
                            const planData = await res.json();
                            setCurrentPlan(normalizePlanSession(planData));
                        }
                    } catch {
                        // Ignore if no plan found
                    }
                }

                // Inject a random greeting on each login/open
                if (token) {
                    try {
                        const greeting = await requestLoginGreeting(token);
                        setMessages(prev => [...prev, greeting.message]);
                    } catch {
                        // Non-blocking
                    }
                }
            } catch (e) {
                console.error("Failed to load conversation", e);
            }
        };

        loadConversation();
    }, [isOpen]);

    useEffect(() => {
        if (!messagesRef.current) return;
        messagesRef.current.scrollTop = messagesRef.current.scrollHeight;
    }, [messages.length, isOpen]);

    const autosizeInput = () => {
        const el = inputRef.current;
        if (!el) return;
        const minHeight = 48;
        const maxHeight = 120; // ~5 lines at 20px line-height
        el.style.height = "0px";
        const next = Math.min(Math.max(el.scrollHeight, minHeight), maxHeight);
        el.style.height = `${next}px`;
        el.style.overflowY = el.scrollHeight > maxHeight ? "auto" : "hidden";
    };

    useEffect(() => {
        autosizeInput();
    }, [input]);


    const handleSend = async () => {
        if (!input.trim() || loading) return;

        const userMessage = input.trim();
        setInput("");
        setError(null);
        setLoading(true);

        // Add user message locally
        setMessages(prev => [...prev, { role: "user", content: userMessage }]);

        try {
            const token = getToken();
            if (!token) {
                throw new Error("请先登录");
            }

            // Call conversation API
            const response = await sendChatMessage(userMessage, token, conversationId);

            // Update conversation ID
            if (!conversationId) {
                setConversationId(response.conversation_id);
            }

            // Add assistant message
            setMessages(prev => [
                ...prev,
                {
                    role: "assistant",
                    content: response.message,
                },
            ]);

            // Handle actions
            if (response.action_type === "create_task") {
                setCurrentPlan(null); setDraftTask(null); setProjectBrief(null);
            } else if (response.action_type === "review_task") {
                setDraftTask(response.task as unknown as QuickTaskDraft);
                setCurrentPlan(null); setProjectBrief(null);
            } else if (response.action_type === "confirm_brief") {
                setProjectBrief(response.plan as unknown as ProjectBrief);
                setCurrentPlan(null); setDraftTask(null);
            } else if (response.action_type === "create_project") {
                const planSessionId = response.planning_session_id || response.conversation_id;
                setCurrentPlan(normalizePlanSession({ session_id: planSessionId, plan: response.plan as unknown as ProjectPlan }));
                setDraftTask(null); setProjectBrief(null);
            } else if (response.action_type === "update_plan") {
                // Update existing plan with refined version
                setCurrentPlan((prev) => {
                    const planSessionId = response.planning_session_id || response.conversation_id;
                    const nextSession = {
                        session_id: planSessionId,
                        plan: response.plan as unknown as ProjectPlan,
                    };
                    if (!prev) return normalizePlanSession(nextSession);
                    return normalizePlanSession({
                        ...prev,
                        plan: response.plan as unknown as ProjectPlan,
                        session_id: planSessionId,
                    });
                });
                setDraftTask(null); setProjectBrief(null);
            } else {
                setCurrentPlan(null); setDraftTask(null); setProjectBrief(null);
            }
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : "对话失败";
            setError(msg);
            setMessages(prev => [...prev, { role: "assistant", content: `❌ ${msg}` }]);
        } finally {
            setLoading(false);
        }
    };

    const handleConfirmBrief = async () => {
        if (!projectBrief) return;
        const confirmMsg = "确认简报无误，请生成方案";
        setInput(confirmMsg);
        setLoading(true);
        setMessages(prev => [...prev, { role: "user", content: confirmMsg }]);

        try {
            const token = getToken();
            if (!token) throw new Error("请先登录");
            const response = await sendChatMessage(confirmMsg, token, conversationId);
            setMessages(prev => [...prev, { role: "assistant", content: response.message }]);

            if (response.action_type === "create_project") {
                const planSessionId = response.planning_session_id || response.conversation_id;
                setCurrentPlan(normalizePlanSession({ session_id: planSessionId, plan: response.plan as unknown as ProjectPlan }));
                setProjectBrief(null);
            }
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : "确认失败";
            setError(msg);
        } finally {
            setLoading(false);
        }
    };

    const handleConfirmTask = async () => {
        if (!draftTask) return;
        setLoading(true);
        try {
            const token = getToken();
            if (!token) throw new Error("请先登录");

            await createQuickTask({
                title: draftTask.title,
                description: draftTask.description,
                deadline: draftTask.deadline || "",
                evidence_type: draftTask.evidence_type
            }, token);

            setMessages(prev => [...prev, { role: "assistant", content: `✅ 已创建任务: ${draftTask.title}` }]);
            setDraftTask(null);
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : "创建失败";
            setError(msg);
        } finally {
            setLoading(false);
        }
    };

    const handleUpdateDraft = (field: string, value: string) => {
        if (!draftTask) return;
        setDraftTask({ ...draftTask, [field]: value });
    };

    const handleUpdatePlan = (field: string, value: string) => {
        if (!currentPlan) return;
        const existingPlan = currentPlan.plan || { project: { title: "", description: "" }, tasks: [] as PlanTask[] };
        const existingProject = existingPlan.project || { title: "", description: "" };
        setCurrentPlan({
            ...currentPlan,
            plan: {
                ...existingPlan,
                project: {
                    ...existingProject,
                    [field]: value
                }
            }
        });
    };

    const handleUpdatePlanTask = (index: number, field: string, value: string) => {
        if (!currentPlan) return;
        const existingPlan = currentPlan.plan || { project: { title: "", description: "" }, tasks: [] as PlanTask[] };
        const existingTasks = Array.isArray(existingPlan.tasks) ? existingPlan.tasks : [];
        const newTasks = [...existingTasks];
        newTasks[index] = { ...newTasks[index], [field]: value };

        setCurrentPlan({
            ...currentPlan,
            plan: {
                ...existingPlan,
                tasks: newTasks
            }
        });
    };

    const handleUpdateMilestone = (index: number, field: string, value: string) => {
        if (!currentPlan) return;
        const existingPlan = currentPlan.plan || { project: { title: "", description: "" }, tasks: [] as PlanTask[] };
        const existingMilestones = Array.isArray(existingPlan.milestones) ? existingPlan.milestones : [];
        const newMilestones = [...existingMilestones];
        newMilestones[index] = { ...newMilestones[index], [field]: value };

        setCurrentPlan({
            ...currentPlan,
            plan: {
                ...existingPlan,
                milestones: newMilestones
            }
        });
    };

    const handleUpdateLongTask = (index: number, field: string, value: string) => {
        if (!currentPlan) return;
        const existingPlan = currentPlan.plan || { project: { title: "", description: "" }, tasks: [] as PlanTask[] };
        const existingLongTasks = Array.isArray(existingPlan.long_tasks) ? existingPlan.long_tasks : [];
        const newLongTasks = [...existingLongTasks];
        newLongTasks[index] = { ...newLongTasks[index], [field]: value };

        setCurrentPlan({
            ...currentPlan,
            plan: {
                ...existingPlan,
                long_tasks: newLongTasks
            }
        });
    };

    const handleCommit = async (): Promise<void> => {
        if (!currentPlan) return;
        setLoading(true);
        setError(null);
        try {
            const token = getToken();
            if (!token) throw new Error("请先登录");

            const result = await commitPlan(currentPlan.session_id, currentPlan.plan, token);
            router.push(`/projects/${result.project_id}`);
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : "创建失败";
            setError(msg);
            setMessages(prev => [...prev, { role: "assistant", content: `❌ ${msg}` }]);
        } finally {
            setLoading(false);
        }
    };

    const handleCancel = () => {
        setCurrentPlan(null);
        setDraftTask(null);
        setProjectBrief(null);
        setMessages(prev => [...prev, { role: "assistant", content: "已取消规划。还有什么我能帮到你的吗？" }]);
        // End planning session on backend to avoid stale drafts
        apiPost<ConversationState>("/api/conversation/reset", {})
            .then((data) => {
                setConversationId(data.conversation_id);
                setMessages([]);
            })
            .catch(() => {
                // Non-blocking
            });
    };

    const handleReset = async () => {
        if (!confirm("确定要开启新对话吗？当前内容将归档。")) return;

        try {
            setLoading(true);
            const data = await apiPost<ConversationState>("/api/conversation/reset", {});
            setConversationId(data.conversation_id);
            setMessages([]);
            setCurrentPlan(null);
            setDraftTask(null);
            setProjectBrief(null);
            setError(null);
        } catch (_e) {
            setError("重置失败");
        } finally {
            setLoading(false);
        }
    };

    return (
        <>
            {!embedded && !isOpen && (
                <button
                    onClick={() => setIsOpen(true)}
                    className="fixed bottom-6 right-6 w-14 h-14 bg-foreground text-background rounded-full shadow-lg hover:bg-gray-700 transition-colors flex items-center justify-center z-50"
                    aria-label="打开规划助手"
                >
                    <MessageCircle className="w-6 h-6" />
                </button>
            )}

            {(isOpen || embedded) && (
                <AppCard
                    className={cn(
                        embedded ? "w-full h-full flex flex-col shadow-none border-0 !bg-transparent" : "fixed bottom-6 right-6 w-96 h-[600px] flex flex-col z-50",
                        className
                    )}
                    noPadding
                >
                    {/* Header */}
                    <div className="flex items-center justify-between px-5 py-4 border-b border-[var(--border)] bg-[var(--surface)] rounded-t-[var(--radius)]">
                        <div className="flex items-center gap-3">
                            <div className="relative">
                                <div className="w-10 h-10 rounded-full bg-[var(--primary-bg)] flex items-center justify-center border border-[var(--primary)]/10">
                                    <MessageCircle className="w-5 h-5 text-[var(--primary)]" />
                                </div>
                                <div className="absolute bottom-0 right-0 w-3 h-3 bg-[var(--success)] border-2 border-[var(--surface)] rounded-full"></div>
                            </div>
                            <div>
                                <h3 className="font-bold text-[var(--text)] text-[15px] leading-tight">研言 (Yan Yan)</h3>
                                <p className="text-[11px] text-[var(--muted)] font-medium">Top-tier Human Engineer</p>
                            </div>
                        </div>
                        <div className="flex items-center gap-1">
                            <button
                                onClick={handleReset}
                                className="p-2 text-[var(--muted)] hover:text-[var(--text)] hover:bg-[var(--surface-hover)] rounded-full transition-colors"
                                title="新对话 (Reset)"
                            >
                                <RotateCcw className="w-4 h-4" />
                            </button>
                            {!embedded && (
                                <button
                                    onClick={() => setIsOpen(false)}
                                    className="p-2 text-[var(--muted)] hover:text-[var(--text)] hover:bg-[var(--surface-hover)] rounded-full transition-colors"
                                >
                                    <X className="w-5 h-5" />
                                </button>
                            )}
                        </div>
                    </div>

                    {/* Messages */}
                    <div ref={messagesRef} className="flex-1 overflow-y-auto p-5 space-y-5 bg-[var(--surface)] custom-scrollbar">
                        {messages.length === 0 && (
                            <div className="flex flex-col h-full justify-center max-w-sm mx-auto animate-fade-in">
                                <div className="mb-6 text-center md:text-left">
                                    <h4 className="text-[20px] font-bold text-[var(--text)] mb-2">👋 下午好，我是研言</h4>
                                    <p className="text-[var(--muted)] text-[14px]">我可以帮你规划任务、拆解目标，或者仅仅是聊聊你的想法。</p>
                                </div>

                                <div className="space-y-3">
                                    <p className="text-[11px] font-bold text-[var(--muted)] uppercase tracking-wider text-center md:text-left">快捷操作</p>
                                    <div className="flex flex-wrap gap-2 justify-center md:justify-start">
                                        <button
                                            onClick={() => setInput("明天早上9点开会")}
                                            className="px-4 py-2 bg-[var(--surface-hover)] hover:bg-[var(--primary-bg)] hover:text-[var(--primary)] border border-[var(--border)] hover:border-[var(--primary)]/20 rounded-full text-[13px] transition-colors"
                                        >
                                            + 快速创建任务
                                        </button>
                                        <button
                                            onClick={() => setInput("帮我规划三个月学完微积分")}
                                            className="px-4 py-2 bg-[var(--surface-hover)] hover:bg-[var(--primary-bg)] hover:text-[var(--primary)] border border-[var(--border)] hover:border-[var(--primary)]/20 rounded-full text-[13px] transition-colors"
                                        >
                                            + 复杂项目规划
                                        </button>
                                        <button
                                            onClick={() => setInput("查看今天的日程安排")}
                                            className="px-4 py-2 bg-[var(--surface-hover)] hover:bg-[var(--primary-bg)] hover:text-[var(--primary)] border border-[var(--border)] hover:border-[var(--primary)]/20 rounded-full text-[13px] transition-colors"
                                        >
                                            查看今日日程
                                        </button>
                                    </div>
                                </div>
                            </div>
                        )}

                        {messages.map((msg, idx) => (
                            <div
                                key={idx}
                                className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"} animate-slide-up`}
                            >
                                <div
                                    className={`max-w-[85%] px-4 py-3 rounded-[18px] text-[14px] leading-relaxed whitespace-pre-wrap shadow-sm ${msg.role === "user"
                                        ? "bg-[var(--primary)] text-white rounded-br-none"
                                        : "bg-[var(--surface-hover)] text-[var(--text)] border border-[var(--border)] rounded-bl-none"
                                        }`}
                                >
                                    {msg.content}
                                </div>
                            </div>
                        ))}

                        {/* Task Draft Card */}
                        {draftTask && (
                            <div className="bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius-md)] p-4 space-y-3 shadow-sm ml-1 animate-scale-in">
                                <div className="flex items-center gap-2 mb-1">
                                    <div className="w-1 h-4 bg-[var(--warning)] rounded-full"></div>
                                    <h4 className="font-bold text-[13px] text-[var(--text)]">任务草稿 (待确认)</h4>
                                </div>

                                <div className="space-y-3">
                                    <div>
                                        <label className="text-[11px] text-[var(--muted)] font-medium mb-1 block">标题</label>
                                        <input
                                            value={draftTask.title}
                                            onChange={(e) => handleUpdateDraft("title", e.target.value)}
                                            className="w-full bg-[var(--surface-hover)] border border-[var(--border)] rounded-md px-3 py-2 text-xs focus:ring-2 focus:ring-[var(--primary)] outline-none transition-all"
                                        />
                                    </div>
                                    <div className="grid grid-cols-2 gap-3">
                                        <div>
                                            <label className="text-[11px] text-[var(--muted)] font-medium mb-1 block">截止时间</label>
                                            <input
                                                type="datetime-local"
                                                value={draftTask.deadline ? new Date(draftTask.deadline).toISOString().slice(0, 16) : ""}
                                                onChange={(e) => handleUpdateDraft("deadline", new Date(e.target.value).toISOString())}
                                                className="w-full bg-[var(--surface-hover)] border border-[var(--border)] rounded-md px-3 py-2 text-xs focus:ring-2 focus:ring-[var(--primary)] outline-none transition-all"
                                            />
                                        </div>
                                    </div>
                                    <div>
                                        <label className="text-[11px] text-[var(--muted)] font-medium mb-1 block">描述</label>
                                        <textarea
                                            value={draftTask.description || ""}
                                            onChange={(e) => handleUpdateDraft("description", e.target.value)}
                                            className="w-full bg-[var(--surface-hover)] border border-[var(--border)] rounded-md px-3 py-2 text-xs min-h-[60px] focus:ring-2 focus:ring-[var(--primary)] outline-none transition-all resize-none"
                                        />
                                    </div>
                                </div>

                                <div className="flex gap-3 pt-2">
                                    <button
                                        onClick={handleConfirmTask}
                                        disabled={loading}
                                        className="flex-1 px-4 py-2 bg-[var(--success)] text-white rounded-full hover:shadow-lg hover:shadow-[var(--success)]/20 transition-all disabled:opacity-50 text-xs font-bold"
                                    >
                                        {loading ? "写入中..." : "确认写入"}
                                    </button>
                                    <button
                                        onClick={handleCancel}
                                        disabled={loading}
                                        className="px-4 py-2 bg-[var(--surface-hover)] text-[var(--muted)] hover:text-[var(--text)] rounded-full transition-colors disabled:opacity-50 text-xs font-medium"
                                    >
                                        取消
                                    </button>
                                </div>
                            </div>
                        )}

                        {/* Project Brief Card */}
                        {projectBrief && (
                            <div className="bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius-md)] p-4 space-y-3 shadow-sm ml-1 animate-scale-in">
                                <div className="flex items-center gap-2 mb-1">
                                    <div className="w-1 h-4 bg-[var(--info)] rounded-full"></div>
                                    <h4 className="font-bold text-[13px] text-[var(--text)]">项目简报 (待确认)</h4>
                                </div>
                                <div className="text-xs space-y-2 p-3 bg-[var(--surface-hover)] rounded-md border border-[var(--border)]">
                                    <p><strong className="text-[var(--text)]">目标:</strong> <span className="text-[var(--muted-foreground)]">{projectBrief.goal || projectBrief.user_answer}</span></p>
                                    {projectBrief.deadline && <p><strong className="text-[var(--text)]">截止:</strong> <span className="text-[var(--muted-foreground)]">{projectBrief.deadline}</span></p>}
                                </div>
                                <div className="flex gap-3 pt-2">
                                    <button
                                        onClick={handleConfirmBrief}
                                        disabled={loading}
                                        className="flex-1 px-4 py-2 bg-[var(--primary)] text-white rounded-full hover:shadow-lg hover:shadow-[var(--primary)]/30 transition-all disabled:opacity-50 text-xs font-bold"
                                    >
                                        {loading ? "生成中..." : "确认并规划"}
                                    </button>
                                    <button
                                        onClick={handleCancel}
                                        disabled={loading}
                                        className="px-4 py-2 bg-[var(--surface-hover)] text-[var(--muted)] hover:text-[var(--text)] rounded-full transition-colors disabled:opacity-50 text-xs font-medium"
                                    >
                                        取消
                                    </button>
                                </div>
                            </div>
                        )}

                        {/* Plan Preview (Editable) */}
                        {currentPlan && (
                            <div className="bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius-md)] p-4 space-y-3 shadow-sm ml-1 animate-scale-in">
                                <div>
                                    <div className="flex items-center justify-between mb-1">
                                        <h4 className="font-bold text-[14px]">项目规划 (Refinement Mode)</h4>
                                        <span className="text-[10px] bg-[var(--info)]/10 text-[var(--info)] px-2 py-0.5 rounded-full">
                                            可直接修改，或打字让AI调整
                                        </span>
                                    </div>
                                    <input
                                        value={safeProject.title || ""}
                                        onChange={(e) => handleUpdatePlan("title", e.target.value)}
                                        className="w-full bg-[var(--surface-hover)] border border-[var(--border)] rounded-md px-2 py-1.5 text-[13px] font-medium text-[var(--text)] focus:ring-2 focus:ring-[var(--primary)] outline-none"
                                        placeholder="项目标题"
                                    />
                                    <textarea
                                        value={safeProject.description || ""}
                                        onChange={(e) => handleUpdatePlan("description", e.target.value)}
                                        className="w-full mt-2 bg-[var(--surface-hover)] border border-[var(--border)] rounded-md px-2 py-1.5 text-[12px] text-[var(--muted-foreground)] focus:ring-2 focus:ring-[var(--primary)] outline-none resize-none"
                                        placeholder="描述..."
                                    />
                                </div>

                                <div className="space-y-2">
                                    <div className="flex items-center justify-between text-[11px] text-[var(--muted)] mb-1">
                                        <span>里程碑 {safeMilestones.length} 个 (点击修改)</span>
                                    </div>
                                    <div className="space-y-2 max-h-44 overflow-y-auto pr-1 custom-scrollbar">
                                        {safeMilestones.map((milestone: PlanMilestone, idx: number) => (
                                            <div
                                                key={idx}
                                                className="bg-[var(--surface-hover)] rounded-md p-2 text-xs border border-[var(--border)]/50 group hover:border-[var(--primary)]/30 transition-colors"
                                            >
                                                <div className="flex flex-col gap-1.5">
                                                    <div className="flex items-center gap-2">
                                                        <span className="text-[var(--muted)] font-mono w-4">{idx + 1}.</span>
                                                        <input
                                                            value={milestone.title || ""}
                                                            onChange={(e) => handleUpdateMilestone(idx, "title", e.target.value)}
                                                            className="flex-1 bg-transparent border-b border-transparent focus:border-[var(--primary)] outline-none font-medium text-[var(--text)]"
                                                        />
                                                    </div>
                                                    <div className="flex items-center gap-2 pl-6">
                                                        <input
                                                            type="datetime-local"
                                                            value={milestone.due_at ? new Date(milestone.due_at).toISOString().slice(0, 16) : ""}
                                                            onChange={(e) => handleUpdateMilestone(idx, "due_at", new Date(e.target.value).toISOString())}
                                                            className="text-[10px] bg-[var(--surface)] border border-[var(--border)] rounded px-1.5 py-0.5 text-[var(--muted)] focus:text-[var(--text)] outline-none"
                                                        />
                                                    </div>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>

                                <div className="space-y-2">
                                    <div className="flex items-center justify-between text-[11px] text-[var(--muted)] mb-1">
                                        <span>包含 {safeTasks.length} 个任务 (点击修改)</span>
                                    </div>
                                    <div className="space-y-2 max-h-60 overflow-y-auto pr-1 custom-scrollbar">
                                        {safeTasks.map((task: PlanTask, idx: number) => (
                                            <div
                                                key={idx}
                                                className="bg-[var(--surface-hover)] rounded-md p-2 text-xs border border-[var(--border)]/50 group hover:border-[var(--primary)]/30 transition-colors"
                                            >
                                                <div className="flex flex-col gap-1.5">
                                                    <div className="flex items-center gap-2">
                                                        <span className="text-[var(--muted)] font-mono w-4">{idx + 1}.</span>
                                                        <input
                                                            value={task.title}
                                                            onChange={(e) => handleUpdatePlanTask(idx, "title", e.target.value)}
                                                            className="flex-1 bg-transparent border-b border-transparent focus:border-[var(--primary)] outline-none font-medium text-[var(--text)]"
                                                        />
                                                    </div>
                                                    <div className="flex items-center gap-2 pl-6">
                                                        <input
                                                            type="datetime-local"
                                                            value={task.due_at ? new Date(task.due_at).toISOString().slice(0, 16) : ""}
                                                            onChange={(e) => handleUpdatePlanTask(idx, "due_at", new Date(e.target.value).toISOString())}
                                                            className="text-[10px] bg-[var(--surface)] border border-[var(--border)] rounded px-1.5 py-0.5 text-[var(--muted)] focus:text-[var(--text)] outline-none"
                                                        />
                                                    </div>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>

                                <div className="space-y-2">
                                    <div className="flex items-center justify-between text-[11px] text-[var(--muted)] mb-1">
                                        <span>长期任务 {safeLongTasks.length} 个 (可调整)</span>
                                    </div>
                                    <div className="space-y-2 max-h-60 overflow-y-auto pr-1 custom-scrollbar">
                                        {safeLongTasks.map((lt: PlanLongTask, idx: number) => (
                                            <div
                                                key={idx}
                                                className="bg-[var(--surface-hover)] rounded-md p-2 text-xs border border-[var(--border)]/50 group hover:border-[var(--primary)]/30 transition-colors"
                                            >
                                                <div className="flex flex-col gap-2">
                                                    <div className="flex items-center gap-2">
                                                        <span className="text-[var(--muted)] font-mono w-4">{idx + 1}.</span>
                                                        <input
                                                            value={lt.title || ""}
                                                            onChange={(e) => handleUpdateLongTask(idx, "title", e.target.value)}
                                                            className="flex-1 bg-transparent border-b border-transparent focus:border-[var(--primary)] outline-none font-medium text-[var(--text)]"
                                                        />
                                                    </div>
                                                    <div className="flex flex-wrap items-center gap-2 pl-6">
                                                        <select
                                                            value={lt.frequency_mode || "interval"}
                                                            onChange={(e) => handleUpdateLongTask(idx, "frequency_mode", e.target.value)}
                                                            className="text-[10px] bg-[var(--surface)] border border-[var(--border)] rounded px-1.5 py-0.5 text-[var(--muted)] focus:text-[var(--text)] outline-none"
                                                        >
                                                            <option value="interval">间隔</option>
                                                            <option value="specific_days">指定星期</option>
                                                        </select>
                                                        <input
                                                            type="number"
                                                            min={1}
                                                            value={lt.interval_days ?? 1}
                                                            onChange={(e) => handleUpdateLongTask(idx, "interval_days", e.target.value)}
                                                            className="w-20 text-[10px] bg-[var(--surface)] border border-[var(--border)] rounded px-1.5 py-0.5 text-[var(--muted)] focus:text-[var(--text)] outline-none"
                                                        />
                                                        <input
                                                            type="number"
                                                            min={1}
                                                            value={lt.total_cycle_days ?? 28}
                                                            onChange={(e) => handleUpdateLongTask(idx, "total_cycle_days", e.target.value)}
                                                            className="w-24 text-[10px] bg-[var(--surface)] border border-[var(--border)] rounded px-1.5 py-0.5 text-[var(--muted)] focus:text-[var(--text)] outline-none"
                                                        />
                                                        <input
                                                            type="time"
                                                            value={lt.default_start_time || ""}
                                                            onChange={(e) => handleUpdateLongTask(idx, "default_start_time", e.target.value)}
                                                            className="text-[10px] bg-[var(--surface)] border border-[var(--border)] rounded px-1.5 py-0.5 text-[var(--muted)] focus:text-[var(--text)] outline-none"
                                                        />
                                                        <input
                                                            type="time"
                                                            value={lt.default_end_time || ""}
                                                            onChange={(e) => handleUpdateLongTask(idx, "default_end_time", e.target.value)}
                                                            className="text-[10px] bg-[var(--surface)] border border-[var(--border)] rounded px-1.5 py-0.5 text-[var(--muted)] focus:text-[var(--text)] outline-none"
                                                        />
                                                    </div>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>

                                <div className="flex gap-3 pt-2">
                                    <button
                                        onClick={handleCommit}
                                        disabled={loading}
                                        className="flex-1 px-4 py-2 bg-[var(--success)] text-white rounded-full hover:shadow-lg hover:shadow-[var(--success)]/20 transition-all disabled:opacity-50 text-xs font-bold"
                                    >
                                        {loading ? "创建中..." : "确认并创建 (Commit)"}
                                    </button>
                                    <button
                                        onClick={handleCancel}
                                        disabled={loading}
                                        className="px-4 py-2 bg-[var(--surface-hover)] text-[var(--muted)] hover:text-[var(--text)] rounded-full transition-colors disabled:opacity-50 text-xs font-medium"
                                    >
                                        取消
                                    </button>
                                </div>
                            </div>
                        )}

                        {loading && (
                            <div className="flex justify-center py-4">
                                <div className="flex items-center gap-2 px-4 py-2 bg-[var(--surface-hover)] rounded-full border border-[var(--border)] animate-pulse">
                                    <Loader2 className="w-4 h-4 animate-spin text-[var(--primary)]" />
                                    <span className="text-xs text-[var(--muted)]">研言思考中...</span>
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Input */}
                    <div className="p-5 border-t border-[var(--border)] bg-[var(--surface)] rounded-b-[var(--radius)]">
                        {error && (
                            <div className="text-xs text-[var(--danger)] mb-2 px-2 flex items-center gap-1">
                                <span className="block w-1.5 h-1.5 rounded-full bg-[var(--danger)]"></span>
                                {error}
                            </div>
                        )}
                        <div className="flex gap-3 items-center relative">
                            <textarea
                                ref={inputRef}
                                rows={1}
                                value={input}
                                onChange={(e) => setInput(e.target.value)}
                                onKeyDown={(e) => {
                                    if (e.key === "Enter" && !e.shiftKey) {
                                        e.preventDefault();
                                        handleSend();
                                    }
                                }}
                                placeholder="输入你的想法..."
                                disabled={loading}
                                className="flex-1 min-h-[48px] max-h-[120px] px-5 py-3 bg-[var(--surface-hover)] border border-[var(--border)] rounded-2xl text-[14px] leading-5 focus:outline-none focus:ring-2 focus:ring-[var(--primary)]/20 focus:border-[var(--primary)] transition-all disabled:opacity-50 placeholder-[var(--muted)] shadow-inner resize-none"
                            />
                            <button
                                onClick={handleSend}
                                disabled={!input.trim() || loading}
                                className="h-12 w-12 flex items-center justify-center bg-[var(--primary)] text-white rounded-full hover:shadow-lg hover:shadow-[var(--primary)]/30 hover:-translate-y-0.5 active:translate-y-0 transition-all disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:translate-y-0 disabled:hover:shadow-none"
                            >
                                <Send className="w-5 h-5 ml-0.5" />
                            </button>
                        </div>
                    </div>
                </AppCard>
            )}
        </>
    );
}
