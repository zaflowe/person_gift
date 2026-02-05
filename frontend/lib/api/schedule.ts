// Schedule API client

const API_BASE = "";

export interface TimeBlock {
    task_id: string;
    title: string;
    scheduled_time: string;
    duration: number;
    status: string;
    evidence_type?: string;
    project_id?: string;
}

export interface DueTask {
    task_id: string;
    title: string;
    status: string;
    deadline: string;
    priority?: string;
    project_id?: string;
}

export interface DailySchedule {
    date: string;
    time_blocks: TimeBlock[];
    due_tasks: DueTask[];
}

export interface WeeklySchedule {
    start_date: string;
    end_date: string;
    daily_schedules: DailySchedule[];
}

export async function getTodaySchedule(token: string): Promise<DailySchedule> {
    const response = await fetch(`${API_BASE}/api/schedule/today`, {
        headers: {
            Authorization: `Bearer ${token}`,
        },
    });

    if (!response.ok) {
        throw new Error("Failed to fetch today's schedule");
    }

    return response.json();
}

export async function getWeekSchedule(token: string, startDate?: string): Promise<WeeklySchedule> {
    const query = startDate ? `?start_date=${startDate}` : "";
    const response = await fetch(`${API_BASE}/api/schedule/week${query}`, {
        headers: {
            Authorization: `Bearer ${token}`,
        },
    });

    if (!response.ok) {
        throw new Error("Failed to fetch week schedule");
    }

    return response.json();
}

export async function scheduleTask(
    taskId: string,
    scheduledDate: string,
    scheduledTime: string,
    duration: number,
    token: string
): Promise<any> {
    const response = await fetch(`${API_BASE}/api/schedule/tasks/${taskId}/schedule`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
            scheduled_date: scheduledDate,
            scheduled_time: scheduledTime,
            duration,
        }),
    });

    if (!response.ok) {
        throw new Error("Failed to schedule task");
    }

    return response.json();
}

export async function unscheduleTask(
    taskId: string,
    token: string
): Promise<void> {
    const response = await fetch(`${API_BASE}/api/schedule/tasks/${taskId}/schedule`, {
        method: "DELETE",
        headers: {
            Authorization: `Bearer ${token}`,
        },
    });

    if (!response.ok) {
        throw new Error("Failed to unschedule task");
    }
}
