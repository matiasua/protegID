import { StatusBadge } from "@/components/ui/status-badge";
import { getDeviceStatusDescription, getDeviceStatusLabel, getDeviceStatusVariant } from "@/components/dashboard/protegid/types";
import type { DeviceStatus } from "@/types/device";

export interface DeviceStatusRowProps {
  status: DeviceStatus;
}

export function DeviceStatusRow({ status }: DeviceStatusRowProps) {
  return (
    <div className="rounded-lg border border-border bg-surface-muted p-4">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <h4 className="text-sm font-semibold text-foreground">Estado del ProtegID</h4>
        <StatusBadge label={getDeviceStatusLabel(status)} variant={getDeviceStatusVariant(status)} />
      </div>
      <p className="mt-2 text-sm leading-6 text-muted-foreground">{getDeviceStatusDescription(status)}</p>
    </div>
  );
}
