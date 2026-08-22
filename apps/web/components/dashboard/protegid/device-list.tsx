import { DeviceCard } from "@/components/dashboard/protegid/device-card";
import { DeviceEmptyState } from "@/components/dashboard/protegid/device-empty-state";
import type { DeviceQrStatusState, PublicAccessStatusState } from "@/components/dashboard/protegid/use-protegid-devices";
import type { Device } from "@/types/device";

export interface DeviceListProps {
  devices: Device[];
  publicAccessByDeviceId: Record<string, PublicAccessStatusState>;
  qrStatusByDeviceId: Record<string, DeviceQrStatusState>;
  canManageQr: boolean;
  isAdmin: boolean;
  emailVerified: boolean;
  onGenerateQr: (device: Device) => void;
  onDownloadQr: (device: Device) => void;
}

export function DeviceList({
  devices,
  publicAccessByDeviceId,
  qrStatusByDeviceId,
  canManageQr,
  isAdmin,
  emailVerified,
  onGenerateQr,
  onDownloadQr,
}: DeviceListProps) {
  if (devices.length === 0) {
    return <DeviceEmptyState />;
  }

  return (
    <div className="grid gap-4 md:grid-cols-2">
      {devices.map((device) => (
        <DeviceCard
          canManageQr={canManageQr}
          device={device}
          emailVerified={emailVerified}
          isAdmin={isAdmin}
          key={device.id}
          onDownloadQr={onDownloadQr}
          onGenerateQr={onGenerateQr}
          publicAccessState={publicAccessByDeviceId[device.id]}
          qrStatusState={qrStatusByDeviceId[device.id]}
        />
      ))}
    </div>
  );
}
