// API 类型定义

export interface User {
    id: string;
    username: string;
    created_at: string;
}

export interface Token {
    access_token: string;
    token_type: string;
}

// Task 状态
export type TaskStatus = "OPEN" | "EVIDENCE_SUBMITTED" | "OVERDUE" | "DONE" | "EXCUSED";

export interface Task {
    id: string;
    user_id: string;
    title: string;
    description?: string;
    task_type: string;
    status: TaskStatus;
    deadline?: string;
    periodicity?: string;
    evidence_type?: string;
    evidence_criteria?: string;
    project_id?: string;
    long_task_template_id?: string;
    completed_at?: string;
    created_at: string;
    scheduled_date?: string;
    scheduled_time?: string;
    duration?: number;
    is_time_blocked?: boolean;
    tags?: string[]; // Added tags
}

export interface TaskEvidence {
    id: string;
    task_id: string;
    evidence_type: string;
    content?: string;
    image_url?: string;
    ai_result?: string;
    is_approved: boolean;
    submitted_at: string;
}

// Project 状态
export type ProjectStatus = "PROPOSED" | "ACTIVE" | "SUCCESS" | "FAILURE";

export interface Project {
    id: string;
    user_id: string;
    title: string;
    description: string;
    status: ProjectStatus;
    deadline?: string;
    ai_analysis?: string;
    agreement_hash?: string;
    user_confirmed_at?: string;
    created_at: string;
    success_criteria?: string;
    failure_criteria?: string;
    is_strategic?: boolean;
    color?: string;
}

export interface Milestone {
    id: string;
    project_id: string;
    title: string;
    description?: string;
    is_critical: boolean;
    status: "PENDING" | "ACHIEVED" | "FAILED";
    target_date?: string;
    achieved_at?: string;
}

// Exemption
export interface ExemptionQuota {
    id: string;
    user_id: string;
    week_start: string;
    day_pass_total: number;
    day_pass_used: number;
    rule_break_total: number;
    rule_break_used: number;
}

export interface ExemptionLog {
    id: string;
    user_id: string;
    quota_id: string;
    exemption_type: string;
    task_id?: string;
    used_at: string;
    effective_date?: string;
    reason?: string;
}

// Metrics
export interface MetricEntry {
    id: string;
    user_id: string;
    metric_type: string;
    value: number;
    unit: string;
    task_id?: string;
    evidence_id?: string;
    notes?: string;
    created_at: string;
}

export interface WeeklySnapshot {
    id: string;
    user_id: string;
    week_start: string;
    summary_data: string; // JSON string
    ai_analysis?: string;
    created_at: string;
}

// Dashboard Summary
export interface DashboardSummary {
    done_count: number;
    overdue_count: number;
    excused_count: number;
    open_count: number;
    has_weekly_snapshot: boolean;
    day_pass_remaining: number;
    rule_break_remaining: number;
    active_projects: Project[];
    next_actions: NextAction[];
}

export interface NextAction {
    id: string;
    priority: "high" | "medium" | "low";
    title: string;
    action: string;
    href?: string;
    onClick?: () => void;
}
