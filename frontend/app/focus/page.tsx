import { FocusController } from "@/components/focus/focus-controller";
import { RequireAuth } from "@/lib/auth-context";

export default function FocusPage() {
    return (
        <RequireAuth>
            <FocusController />
        </RequireAuth>
    );
}
