// Conversation API client functions

const API_BASE = "";

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
    stage: string;
    intent?: string;
}

export async function sendChatMessage(
    message: string,
    token: string,
    conversationId?: string
): Promise<ChatResponse> {
    const response = await fetch(`${API_BASE}/api/conversation/chat`, {
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
