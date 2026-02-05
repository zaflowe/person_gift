// Planner API client functions

const API_BASE = "";

export interface PlanRequest {
    message: string;
    context?: {
        timezone?: string;
        today?: string;
    };
}

export interface PlanResponse {
    session_id: string;
    plan: {
        project: {
            title: string;
            description?: string;
        };
        tasks: Array<{
            title: string;
            description?: string;
            due_at: string;
            evidence_type?: string;
            tags?: string[];
        }>;
        rationale?: string;
    };
}

export interface CommitRequest {
    session_id: string;
    plan: PlanResponse['plan'];
}

export interface CommitResponse {
    project_id: string;
    task_ids: string[];
}

export async function planTask(
    message: string,
    token: string
): Promise<PlanResponse> {
    const response = await fetch(`${API_BASE}/api/planner/plan`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
            message,
            context: {
                timezone: "Asia/Shanghai",
                today: new Date().toISOString().split('T')[0],
            },
        }),
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "规划生成失败");
    }

    return response.json();
}

export async function commitPlan(
    sessionId: string,
    planData: PlanResponse['plan'],
    token: string
): Promise<CommitResponse> {
    const response = await fetch(`${API_BASE}/api/planner/commit`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
            session_id: sessionId,
            plan: planData,
        }),
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "计划提交失败");
    }

    return response.json();
}
