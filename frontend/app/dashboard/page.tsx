"use client";

import { useState, useEffect } from "react";
import { RequireAuth } from "@/lib/auth-context";
import { AppLayout } from "@/components/layout/app-layout";
import useSWR from "swr";
import { fetcher, apiPost } from "@/lib/utils";
import ChatPlanner from "@/components/chat-planner";
import { FocusStudyCard } from "@/components/dashboard/focus-study-card";
import { StrategicProjectsCard } from "@/components/dashboard/strategic-projects-card";
import { BodyMetricsCard } from "@/components/dashboard/body-metrics-card";

export default function DashboardPage() {
    return (
        <RequireAuth>
            <AppLayout>
                <DashboardContent />
            </AppLayout>
        </RequireAuth>
    );
}

function DashboardContent() {
    // 1. Data Fetching for Focus Card
    const { data: studyStats } = useSWR<any>("/api/study/stats", fetcher);

    // 2. Daily Reminder Logic
    const [chatKey, setChatKey] = useState(0);

    useEffect(() => {
        const checkAndInjectReminder = async () => {
            const today = new Date().toISOString().split('T')[0];
            const lastReminderDate = localStorage.getItem("lastReminderDate");

            if (lastReminderDate !== today) {
                try {
                    // 1. Check weekly system task (backend will create if missing)
                    await apiPost("/api/system-tasks/weekly-check", {});

                    // 2. Fetch reminder data
                    const reminderData = await fetcher("/dashboard/daily-reminder-data");

                    // 3. Inject message
                    await apiPost("/conversation/inject-reminder", { data: reminderData });

                    // 4. Update local storage
                    localStorage.setItem("lastReminderDate", today);

                    // 5. Refresh ChatPlanner to show new message
                    setChatKey(prev => prev + 1);

                    console.log("Daily reminder injected successfully");
                } catch (e) {
                    console.error("Failed to inject daily reminder", e);
                }
            }
        };

        checkAndInjectReminder();
    }, []);

    const pieData = studyStats?.distribution || [];

    return (
        <div className="flex flex-col h-[calc(100vh-4rem)] p-6 max-w-[1600px] mx-auto gap-6 transition-all duration-300">

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 h-full min-h-0">

                {/* Left Panel: Secondary Cockpit (6 cols) */}
                <div className="lg:col-span-6 flex flex-col gap-6 min-h-0">

                    {/* Row 1: Focus & Strategy (Equal Height) */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 flex-1 min-h-0">
                        {/* Focus Card */}
                        <div className="h-full min-h-[300px]">
                            <FocusStudyCard
                                todaySec={studyStats?.today_total_sec || 0}
                                weekSec={studyStats?.week_total_sec || 0}
                                distribution={pieData}
                            />
                        </div>

                        {/* Strategic Projects */}
                        <div className="h-full min-h-[300px]">
                            <StrategicProjectsCard />
                        </div>
                    </div>

                    {/* Row 2: Body Metrics (Fixed Height) */}
                    <div className="h-40 shrink-0">
                        <BodyMetricsCard />
                    </div>

                </div>

                {/* Right Panel: ChatPlanner (6 cols) */}
                <div className="lg:col-span-6 h-full min-h-0 relative">
                    <div className="absolute inset-0 border border-[var(--border)] shadow-sm rounded-[var(--radius)] bg-[var(--surface)] overflow-hidden">
                        <ChatPlanner embedded={true} className="h-full w-full" key={chatKey} />
                    </div>
                </div>

            </div>
        </div>
    );
}
