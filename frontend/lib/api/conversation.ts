// Conversation API client functions

const API_BASE =
    process.env.NEXT_PUBLIC_API_BASE ||
    process.env.NEXT_PUBLIC_API_URL ||
    "";

export interface ChatMessage {
    role: "user" | "assistant";
    content: string;
}

export interface ChatRequest {
    conversation_id?: string;  // undefined for new conversation
    message: string;
}

export interface ChatResponse {
    conversation_id: string;
    action_type: "ask_more" | "create_task" | "create_project" | "reply" | "review_task" | "confirm_brief" | "update_plan";
    message: string;
    plan?: Record<string, unknown>;
    task?: Record<string, unknown>;  // task data (draft or created)
    planning_session_id?: string;
    stage: string;
    intent?: string;
}

export interface LoginGreetingResponse {
    message: {
        role: "assistant";
        content: string;
        timestamp?: string;
        type?: string;
    };
}

export async function sendChatMessage(
    message: string,
    token: string,
    conversationId?: string
): Promise<ChatResponse> {
    const response = await fetch(`${API_BASE}/conversation/chat`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
            conversation_id: conversationId,
            message,
        }),
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "对话失败");
    }

    return response.json();
}

export async function requestLoginGreeting(token: string): Promise<LoginGreetingResponse> {
    const response = await fetch(`${API_BASE}/conversation/login-greeting`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({}),
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || "登录问候生成失败");
    }

    return response.json();
}
