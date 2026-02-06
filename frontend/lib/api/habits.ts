import { fetcher, apiPost, apiPatch, apiDelete } from "@/lib/utils";

export interface HabitTemplate {
    id: string;
    title: string;
    enabled: boolean;
    frequency_mode: "interval" | "specific_days";
    interval_days: number;
    days_of_week: number[];
    default_due_time?: string;
    default_start_time?: string;
    default_end_time?: string;
    evidence_type: "none" | "image" | "text" | "number";
    evidence_schema?: string;
    evidence_criteria?: string;
}

export interface FixedBlock {
    id: string;
    title: string;
    start_time: string;
    end_time: string;
    days_of_week: number[];
    color?: string;
}

export const getHabitTemplates = async (): Promise<HabitTemplate[]> => {
    return fetcher<HabitTemplate[]>("/api/habits/templates");
};

export const createHabitTemplate = async (data: Partial<HabitTemplate>): Promise<HabitTemplate> => {
    return apiPost<HabitTemplate>("/api/habits/templates", data);
};

export const updateHabitTemplate = async (id: string, data: Partial<HabitTemplate>): Promise<HabitTemplate> => {
    return apiPatch<HabitTemplate>(`/api/habits/templates/${id}`, data);
};

export const deleteHabitTemplate = async (id: string): Promise<void> => {
    return apiDelete(`/api/habits/templates/${id}`);
};


export const getFixedBlocks = async (): Promise<FixedBlock[]> => {
    return fetcher<FixedBlock[]>("/api/habits/fixed-blocks");
};

export const createFixedBlock = async (data: Partial<FixedBlock>): Promise<FixedBlock> => {
    return apiPost<FixedBlock>("/api/habits/fixed-blocks", data);
};

export const deleteFixedBlock = async (id: string): Promise<void> => {
    return apiDelete(`/api/habits/fixed-blocks/${id}`);
};

export const checkDailyHabits = async (): Promise<{ created_count: number }> => {
    return apiPost<{ created_count: number }>("/api/habits/check-today", {});
};
