"use client";

import { useState, FormEvent } from "react";
import { useAuth } from "@/lib/auth-context";
import { useToast } from "@/components/ui/toast";
import { LogIn } from "lucide-react";

export default function LoginPage() {
    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");
    const [loading, setLoading] = useState(false);
    const { login } = useAuth();
    const { showToast } = useToast();

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault();
        setLoading(true);

        try {
            await login(username, password);
            showToast("success", "登录成功");
        } catch (error: any) {
            showToast("error", error.message || "登录失败");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center bg-background px-4">
            <div className="w-full max-w-md space-y-8">
                {/* Header */}
                <div className="text-center">
                    <div className="inline-flex items-center justify-center w-14 h-14 bg-foreground text-background rounded-lg mb-4">
                        <LogIn className="w-7 h-7" />
                    </div>
                    <h1 className="text-2xl font-bold">个人主权系统</h1>
                    <p className="text-sm text-muted-foreground mt-2">强约束执行 - 任务与项目管理</p>
                </div>

                {/* Form */}
                <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                        <label htmlFor="username" className="block text-sm font-medium mb-2">
                            用户名
                        </label>
                        <input
                            id="username"
                            type="text"
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                            required
                            className="w-full px-4 py-2.5 bg-input border border-border rounded-sm text-sm focus:outline-none focus:ring-2 focus:ring-ring transition-shadow"
                            placeholder="输入用户名"
                            disabled={loading}
                        />
                    </div>

                    <div>
                        <label htmlFor="password" className="block text-sm font-medium mb-2">
                            密码
                        </label>
                        <input
                            id="password"
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            required
                            className="w-full px-4 py-2.5 bg-input border border-border rounded-sm text-sm focus:outline-none focus:ring-2 focus:ring-ring transition-shadow"
                            placeholder="输入密码"
                            disabled={loading}
                        />
                    </div>

                    <button
                        type="submit"
                        disabled={loading}
                        className="w-full px-4 py-2.5 bg-foreground text-background font-medium rounded-sm hover:bg-gray-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        {loading ? "登录中..." : "登录"}
                    </button>


                </form>

                {/* Footer */}
                <div className="text-center text-xs text-muted-foreground">
                    <p>V1.0.0 - 冷面克制，规则优先</p>
                </div>
            </div>
        </div>
    );
}
