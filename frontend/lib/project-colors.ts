export const STRATEGIC_COLORS = [
    { name: 'indigo', label: 'Indigo', bg: 'bg-indigo-500', bgLight: 'bg-indigo-50', text: 'text-indigo-700', border: 'border-indigo-200' },
    { name: 'emerald', label: 'Emerald', bg: 'bg-emerald-500', bgLight: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200' },
    { name: 'amber', label: 'Amber', bg: 'bg-amber-500', bgLight: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200' },
];

// Palette for non-strategic projects (avoiding Indigo, Emerald, Amber)
export const HASH_PALETTE = [
    { name: 'sky', bg: 'bg-sky-500', bgLight: 'bg-sky-50', text: 'text-sky-700', border: 'border-sky-200' },
    { name: 'rose', bg: 'bg-rose-500', bgLight: 'bg-rose-50', text: 'text-rose-700', border: 'border-rose-200' },
    { name: 'teal', bg: 'bg-teal-500', bgLight: 'bg-teal-50', text: 'text-teal-700', border: 'border-teal-200' },
    { name: 'violet', bg: 'bg-violet-500', bgLight: 'bg-violet-50', text: 'text-violet-700', border: 'border-violet-200' },
    { name: 'orange', bg: 'bg-orange-500', bgLight: 'bg-orange-50', text: 'text-orange-700', border: 'border-orange-200' },
    { name: 'cyan', bg: 'bg-cyan-500', bgLight: 'bg-cyan-50', text: 'text-cyan-700', border: 'border-cyan-200' },
    { name: 'fuchsia', bg: 'bg-fuchsia-500', bgLight: 'bg-fuchsia-50', text: 'text-fuchsia-700', border: 'border-fuchsia-200' },
    { name: 'lime', bg: 'bg-lime-500', bgLight: 'bg-lime-50', text: 'text-lime-700', border: 'border-lime-200' },
];

export const NO_PROJECT_COLOR = {
    name: 'slate',
    bg: 'bg-slate-200',
    bgLight: 'bg-slate-50',
    text: 'text-slate-600',
    border: 'border-slate-200'
};

// Simple string hash function
function hashCode(str: string) {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
        const char = str.charCodeAt(i);
        hash = ((hash << 5) - hash) + char;
        hash = hash & hash; // Convert to 32bit integer
    }
    return Math.abs(hash);
}

export function getProjectColor(projectId: string | undefined | null, isStrategic: boolean = false, strategicIndex: number = -1) {
    if (!projectId) return NO_PROJECT_COLOR;

    // Strategic Projects (Fixed)
    if (isStrategic && strategicIndex >= 0) {
        // Recycle colors if more than 3 strategic projects (though usually strictly 3)
        return STRATEGIC_COLORS[strategicIndex % STRATEGIC_COLORS.length];
    }

    // Hash for others
    const index = hashCode(projectId) % HASH_PALETTE.length;
    return HASH_PALETTE[index];
}

// Helper for charts (returns hex code approximately matching tailwind 500)
// Simplified map for MVP - ideally use computed styles or full map
export function getProjectColorHex(projectId: string | undefined | null, isStrategic: boolean = false, strategicIndex: number = -1, customColor?: string): string {
    // 0. Custom Color (if provided by project)
    if (customColor) return customColor;

    // Special case for 'Other' category or 'none'
    if (!projectId || projectId === 'Other' || projectId === 'other') {
        return '#cbd5e1'; // slate-300 (Neutral nice grey)
    }

    const color = getProjectColor(projectId, isStrategic, strategicIndex);
    const colorName = color.name;

    const hexMap: Record<string, string> = {
        'indigo': '#6366f1',
        'emerald': '#10b981',
        'amber': '#f59e0b',
        'sky': '#0ea5e9',
        'rose': '#f43f5e',
        'teal': '#14b8a6',
        'violet': '#8b5cf6',
        'orange': '#f97316',
        'cyan': '#06b6d4',
        'fuchsia': '#d946ef',
        'lime': '#84cc16',
        'slate': '#94a3b8'
    };

    return hexMap[colorName] || '#94a3b8';
}
