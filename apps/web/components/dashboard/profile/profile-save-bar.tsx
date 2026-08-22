import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { ProfileSaveStatus } from "@/components/dashboard/profile/use-emergency-profile-form";

export interface ProfileSaveBarProps {
  status: ProfileSaveStatus;
  errorMessage: string | null;
  disabled: boolean;
  onSave: () => void;
}

const STATUS_LABEL: Record<ProfileSaveStatus, string> = {
  initial: "Sin cambios",
  dirty: "Cambios sin guardar",
  saving: "Guardando...",
  saved: "Guardado",
  error: "Error al guardar",
};

const STATUS_CLASS: Record<ProfileSaveStatus, string> = {
  initial: "text-muted-foreground",
  dirty: "text-warning",
  saving: "text-primary",
  saved: "text-success",
  error: "text-danger",
};

export function ProfileSaveBar({ status, errorMessage, disabled, onSave }: ProfileSaveBarProps) {
  const isSaveDisabled = disabled || status === "saving" || status === "initial" || status === "saved";

  return (
    <div
      className={cn(
        "sticky bottom-[calc(env(safe-area-inset-bottom)+64px)] z-10 rounded-lg border border-border bg-surface/95 p-4 shadow-md backdrop-blur",
        "md:bottom-0",
      )}
    >
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className={cn("text-sm font-semibold", STATUS_CLASS[status])}>{STATUS_LABEL[status]}</p>
          {status === "error" && errorMessage ? <p className="mt-1 text-xs text-danger">{errorMessage}</p> : null}
        </div>
        <Button className="w-full sm:w-auto" disabled={isSaveDisabled} onClick={onSave} type="button">
          {status === "saving" ? "Guardando..." : "Guardar cambios"}
        </Button>
      </div>
    </div>
  );
}
