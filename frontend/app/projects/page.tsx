"use client";

import { RequireAuth } from "@/lib/auth-context";
import { AppLayout } from "@/components/layout/app-layout";
import { StatusBadge } from "@/components/ui/status-badge";
import { LoadingSkeleton, EmptyState, ProjectsSkeleton } from "@/components/ui/empty-state";
import useSWR from "swr";
import { fetcher } from "@/lib/utils";
import { Project } from "@/types";
import Link from "next/link";
import { Plus } from "lucide-react";
import { useState } from "react";
import { CreateProjectModal } from "@/components/modals/create-project-modal";

export default function ProjectsPage() {
    return (
        <RequireAuth>
            <AppLayout>
                <ProjectsContent />
            </AppLayout>
        </RequireAuth>
    );
}

function ProjectsContent() {
    const { data: projects, error } = useSWR<Project[]>("/api/projects", fetcher);
    const loading = !projects && !error;

    const proposed = projects?.filter(p => p.status === "PROPOSED") || [];
    const active = projects?.filter(p => p.status === "ACTIVE") || [];
    const resolved = projects?.filter(p => p.status === "SUCCESS" || p.status === "FAILURE") || [];

    const [isCreateOpen, setIsCreateOpen] = useState(false);

    return (
        <div className="p-6 max-w-7xl mx-auto space-y-6">
            <div className="flex items-center justify-between">
                <h1 className="text-2xl font-bold">项目</h1>
                <button
                    onClick={() => setIsCreateOpen(true)}
                    className="flex items-center gap-2 px-4 py-2 bg-foreground text-background rounded-sm hover:bg-gray-700 transition-colors"
                >
                    <Plus className="w-4 h-4" />
                    发起项目
                </button>
            </div>

            <CreateProjectModal isOpen={isCreateOpen} onClose={() => setIsCreateOpen(false)} />

            {loading ? (
                <ProjectsSkeleton />
            ) : (
                <>
                    {/* Just pass a handler to children if needed, or implement Edit in Detail page mainly. 
                        The user wanted "color consistency" primarily. 
                        Let's keep the Edit in the detail page for simplicity, OR add a small edit button here.
                        Actually, I'll add the modal here so we can support quick edit if we wanted, 
                        but for now I just updated the list appearance. 
                        Wait, I need to allow editing existing projects. 
                        Let's put the Edit logic in the Project Detail page as planned in the previous turn's thought process,
                        BUT update the visual here. 
                        I will ALSO add it here for convenience? No, let's stick to Detail Page for editing to avoid clutter.
                    */}
                    <ProjectGroup title="提案中" projects={proposed} />
                    <ProjectGroup title="执行中" projects={active} />
                    <ProjectGroup title="已完成" projects={resolved} collapsed />
                </>
            )}
        </div>
    );
}

function ProjectGroup({ title, projects, collapsed = false }: { title: string; projects: Project[]; collapsed?: boolean }) {
    if (projects.length === 0) return null;

    return (
        <div>
            <h2 className="text-sm font-medium text-muted-foreground mb-3 uppercase">{title}</h2>
            <div className="space-y-2">
                {projects.map(project => {
                    const color = (project.color || "#cbd5e1"); // Default to slate if no color
                    return (
                        <div key={project.id} className="group relative">
                            <Link href={`/projects/${project.id}`}>
                                <div className="bg-card border border-border rounded-lg p-4 hover:border-foreground/20 transition-colors pl-5 relative overflow-hidden">
                                    {/* Color Stripe */}
                                    <div className="absolute left-0 top-0 bottom-0 w-1.5" style={{ backgroundColor: color }} />

                                    <div className="flex items-start justify-between">
                                        <div className="flex-1">
                                            <h3 className="font-medium mb-1">{project.title}</h3>
                                            <p className="text-sm text-muted-foreground line-clamp-2">{project.description}</p>
                                        </div>
                                        <StatusBadge status={project.status} type="project" className="ml-3" />
                                    </div>
                                </div>
                            </Link>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
