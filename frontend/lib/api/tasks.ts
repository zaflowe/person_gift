// Tasks API client functions

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "";

export interface QuickTaskRequest {
    title: string;
    description?: string;
    deadline: string; // ISO string
    evidence_type?: string;
}

export interface QuickTaskResponse {
    task_id: string;
    title: string;
    deadline: string;
}

export async function createQuickTask(
    data: QuickTaskRequest,
    token: string
): Promise<QuickTaskResponse> {
    const response = await fetch(`${API_BASE}/conversation/tasks/quick-create`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(data),
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "创建任务失败");
    }

    return response.json();
}
