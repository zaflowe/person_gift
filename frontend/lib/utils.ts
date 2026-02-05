import { TaskStatus, ProjectStatus } from "@/types";
import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

// Tailwind class merger
export function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}

// 状态映射：Task
export const TASK_STATUS_MAP: Record<TaskStatus, { label: string; color: string }> = {
    OPEN: { label: "进行中", color: "info" },
    EVIDENCE_SUBMITTED: { label: "已提交证据", color: "purple" },
    OVERDUE: { label: "已逾期", color: "error" },
    DONE: { label: "已完成", color: "success" },
    EXCUSED: { label: "已豁免", color: "warning" },
};

// 状态映射：Project
export const PROJECT_STATUS_MAP: Record<ProjectStatus, { label: string; color: string }> = {
    PROPOSED: { label: "提案中", color: "muted" },
    ACTIVE: { label: "执行中", color: "info" },
    SUCCESS: { label: "成功", color: "success" },
    FAILURE: { label: "失败", color: "error" },
};

// 日期格式化
export function formatDate(dateString: string | undefined): string {
    if (!dateString) return "-";
    const date = new Date(dateString);
    return new Intl.DateTimeFormat("zh-CN", {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
    }).format(date);
}

export function formatDateTime(dateString: string | undefined): string {
    if (!dateString) return "-";
    const date = new Date(dateString);
    return new Intl.DateTimeFormat("zh-CN", {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
    }).format(date);
}

// 计算距离现在的时间差
export function timeFromNow(dateString: string): string {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now.getTime() - date.getTime();

    const seconds = Math.floor(diff / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);

    if (days > 0) return `${days}天前`;
    if (hours > 0) return `${hours}小时前`;
    if (minutes > 0) return `${minutes}分钟前`;
    return "刚刚";
}

// 检查是否逾期
export function isOverdue(deadline: string | undefined): boolean {
    if (!deadline) return false;
    return new Date(deadline) < new Date();
}

// API 基础 URL
// Use relative path to leverage Next.js Rewrites (Proxy)
export const API_BASE_URL = "";

// Token 管理
export function getToken(): string | null {
    if (typeof window === "undefined") return null;
    return localStorage.getItem("token") || localStorage.getItem("auth_token");
}

export function setToken(token: string): void {
    localStorage.setItem("token", token);
    localStorage.setItem("auth_token", token);
}

export function clearToken(): void {
    localStorage.removeItem("token");
    localStorage.removeItem("auth_token");
}

// API Fetcher (for SWR)
export async function fetcher<T>(url: string): Promise<T> {
    const token = getToken();
    console.log(`[Fetcher] Requesting ${API_BASE_URL}${url} with token: ${token ? 'YES' : 'NO'}`);

    try {
        const res = await fetch(`${API_BASE_URL}${url}`, {
            headers: token ? { Authorization: `Bearer ${token}` } : {},
        });

        if (!res.ok) {
            if (res.status === 401) {
                console.warn("[Fetcher] 401 Unauthorized - Clearing token");
                clearToken();
                if (typeof window !== "undefined") {
                    // Check if not already on login page to avoid loops if login API returns 401
                    if (!window.location.pathname.includes("/login")) {
                        window.location.href = "/login";
                    }
                }
            }
            const text = await res.text();
            console.error(`[Fetcher] Error ${res.status}: ${text}`);
            // Try parsing JSON
            try {
                const error = JSON.parse(text);
                let errorMessage = error.detail || `请求失败: ${res.status}`;

                // Handle Pydantic array errors or object errors
                if (typeof errorMessage === 'object') {
                    errorMessage = JSON.stringify(errorMessage);
                }

                throw new Error(errorMessage);
            } catch (e: unknown) {
                // If parsing failed or we just threw above
                if (e instanceof Error) {
                    if (e.message && e.message.startsWith("请求失败")) throw e;
                    if (e.message && (e.message.startsWith("[") || e.message.startsWith("{"))) throw e; // Already stringified
                }
                throw new Error(`请求失败 (${res.status}): ${text.substring(0, 100)}`);
            }
        }

        return res.json();
    } catch (err: unknown) {
        if (err instanceof Error && err.message.includes("401")) {
            // Already handled above? No, throw propagates.
            // But we already redirected.
        }
        console.error("[Fetcher] Network/System Error:", err);
        throw err;
    }
}

// POST/PUT/DELETE helpers
export async function apiPost<T>(url: string, data?: unknown): Promise<T> {
    const token = getToken();
    const isFormData = data instanceof FormData || data instanceof URLSearchParams;
    if (isFormData && !(data instanceof URLSearchParams)) {
        // If plain FormData, fetch adds multipart header (but OAuth2 usually wants urlencoded)
        // But here we might want urlencoded for login.
    }

    const headers: HeadersInit = isFormData
        ? (token ? { Authorization: `Bearer ${token}` } : {})
        : {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
        };

    const res = await fetch(`${API_BASE_URL}${url}`, {
        method: "POST",
        headers,
        body: isFormData ? data : (data ? JSON.stringify(data) : undefined),
    });

    if (!res.ok) {
        if (res.status === 401) {
            console.warn("[apiPost] 401 Unauthorized - Clearing token");
            clearToken();
            if (typeof window !== "undefined") {
                if (!window.location.pathname.includes("/login")) {
                    window.location.href = "/login";
                }
            }
        }
        const error = await res.json().catch(() => ({ detail: "请求失败" }));
        throw new Error(error.detail || "请求失败");
    }

    return res.json();
}

export async function apiPut<T>(url: string, data?: unknown): Promise<T> {
    const token = getToken();
    const res = await fetch(`${API_BASE_URL}${url}`, {
        method: "PUT",
        headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: data ? JSON.stringify(data) : undefined,
    });

    if (!res.ok) {
        const error = await res.json().catch(() => ({ detail: "请求失败" }));
        throw new Error(error.detail || "请求失败");
    }

    return res.json();
}

export async function apiPatch<T>(url: string, data?: unknown): Promise<T> {
    const token = getToken();
    const res = await fetch(`${API_BASE_URL}${url}`, {
        method: "PATCH",
        headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: data ? JSON.stringify(data) : undefined,
    });

    if (!res.ok) {
        if (res.status === 401) {
            console.warn("[apiPatch] 401 Unauthorized - Clearing token");
            clearToken();
            if (typeof window !== "undefined") {
                if (!window.location.pathname.includes("/login")) {
                    window.location.href = "/login";
                }
            }
        }
        const error = await res.json().catch(() => ({ detail: "请求失败" }));
        throw new Error(error.detail || "请求失败");
    }

    return res.json();
}

export async function apiDelete(url: string): Promise<void> {
    const token = getToken();
    const res = await fetch(`${API_BASE_URL}${url}`, {
        method: "DELETE",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
    });

    if (!res.ok) {
        const error = await res.json().catch(() => ({ detail: "请求失败" }));
        throw new Error(error.detail || "请求失败");
    }
}

// File upload helper
export async function apiUpload<T>(url: string, formData: FormData): Promise<T> {
    const token = getToken();
    const res = await fetch(`${API_BASE_URL}${url}`, {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: formData,
    });

    if (!res.ok) {
        const error = await res.json().catch(() => ({ detail: "上传失败" }));
        throw new Error(error.detail || "上传失败");
    }

    return res.json();
}
