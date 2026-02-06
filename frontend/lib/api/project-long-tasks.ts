import { fetcher, apiPost, apiPatch } from "@/lib/utils";

export interface ProjectLongTaskTemplate {
    id: string;
    user_id: string;
    project_id: string;
    title: string;
    frequency_mode: "interval" | "specific_days";
    interval_days: number;
    days_of_week: number[];
    default_due_time?: string;
    default_start_time?: string;
    default_end_time?: string;
    evidence_type: "none" | "image" | "text" | "number";
    evidence_criteria?: string;
    total_cycle_days: number;
    started_at: string;
    is_hidden: boolean;
    created_at: string;
    updated_at: string;
}

export const getProjectLongTaskTemplates = async (
    projectId: string,
    includeHidden: boolean = false
): Promise<ProjectLongTaskTemplate[]> => {
    const query = includeHidden ? "?include_hidden=true" : "";
    return fetcher<ProjectLongTaskTemplate[]>(`/api/projects/${projectId}/long-task-templates${query}`);
};

export const createProjectLongTaskTemplate = async (
    projectId: string,
    data: Partial<ProjectLongTaskTemplate> & { total_cycle_days: number; title: string }
): Promise<ProjectLongTaskTemplate> => {
    return apiPost<ProjectLongTaskTemplate>(`/api/projects/${projectId}/long-task-templates`, data);
};

export const updateProjectLongTaskTemplate = async (
    projectId: string,
    id: string,
    data: Partial<ProjectLongTaskTemplate>
): Promise<ProjectLongTaskTemplate> => {
    return apiPatch<ProjectLongTaskTemplate>(`/api/projects/${projectId}/long-task-templates/${id}`, data);
};

export const hideProjectLongTaskTemplate = async (
    projectId: string,
    id: string
): Promise<ProjectLongTaskTemplate> => {
    return apiPost<ProjectLongTaskTemplate>(`/api/projects/${projectId}/long-task-templates/${id}/hide`, {});
};
