"use client";

import { createContext, useContext, useState, useEffect, ReactNode, useCallback } from "react";
import { useRouter } from "next/navigation";
import { User } from "@/types";
import { getToken, setToken as saveToken, clearToken, fetcher, apiPost } from "@/lib/utils";

interface AuthContextValue {
    user: User | null;
    loading: boolean;
    login: (username: string, password: string) => Promise<void>;
    logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function useAuth() {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error("useAuth must be used within AuthProvider");
    }
    return context;
}

export function AuthProvider({ children }: { children: ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const [loading, setLoading] = useState(true);
    const router = useRouter();

    const fetchUser = useCallback(async () => {
        const token = getToken();
        if (!token) {
            setLoading(false);
            return;
        }

        try {
            const userData = await fetcher<User>("/api/auth/me");
            setUser(userData);
        } catch (error) {
            clearToken();
            setUser(null);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchUser();
    }, [fetchUser]);

    const login = async (username: string, password: string) => {
        const formData = new FormData();
        formData.append("username", username);
        formData.append("password", password);

        const data = await apiPost<{ access_token: string, token_type: string }>("/api/auth/login", formData);
        saveToken(data.access_token);
        await fetchUser();
        router.push("/dashboard");
    };

    const logout = () => {
        clearToken();
        setUser(null);
        router.push("/login");
    };

    return (
        <AuthContext.Provider value={{ user, loading, login, logout }}>
            {children}
        </AuthContext.Provider>
    );
}



export function RequireAuth({ children }: { children: ReactNode }) {
    const { user, loading } = useAuth();
    const router = useRouter();

    useEffect(() => {
        if (!loading && !user) {
            router.push("/login");
        }
    }, [user, loading, router]);

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="animate-spin rounded-full h-12 w-12 border-2 border-muted border-t-foreground"></div>
            </div>
        );
    }

    if (!user) {
        return null;
    }

    return <>{children}</>;
}
