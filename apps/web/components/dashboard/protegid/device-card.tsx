import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { deviceDisplayName, formatActivatedAt } from "@/components/dashboard/protegid/types";
import { DeviceStatusRow } from "@/components/dashboard/protegid/device-status-row";
import { PublicAccessStatusRow } from "@/components/dashboard/protegid/public-access-status-row";
import { QrActions } from "@/components/dashboard/protegid/qr-actions";
import type { DeviceQrStatusState, PublicAccessStatusState } from "@/components/dashboard/protegid/use-protegid-devices";
import type { Device } from "@/types/device";

export interface DeviceCardProps {
  device: Device;
  publicAccessState: PublicAccessStatusState | undefined;
  canManageQr: boolean;
  isAdmin: boolean;
  emailVerified: boolean;
  qrStatusState: DeviceQrStatusState | undefined;
  onGenerateQr: (device: Device) => void;
  onDownloadQr: (device: Device) => void;
}

export function DeviceCard({
  device,
  publicAccessState,
  canManageQr,
  isAdmin,
  emailVerified,
  qrStatusState,
  onGenerateQr,
  onDownloadQr,
}: DeviceCardProps) {
  return (
    <Card aria-labelledby={`device-${device.id}-title`}>
      <CardHeader>
        <div className="flex flex-col gap-1 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <CardTitle id={`device-${device.id}-title`}>{deviceDisplayName(device)}</CardTitle>
            <p className="mt-2 w-fit rounded-md border border-border bg-surface-muted px-3 py-2 font-mono text-sm text-foreground">
              {device.public_id}
            </p>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <dl className="grid gap-3 text-sm sm:grid-cols-2">
          <div>
            <dt className="font-medium text-muted-foreground">Tipo</dt>
            <dd className="mt-1 text-foreground">{device.device_type}</dd>
          </div>
          <div>
            <dt className="font-medium text-muted-foreground">Activación</dt>
            <dd className="mt-1 text-foreground">{formatActivatedAt(device.activated_at)}</dd>
          </div>
        </dl>

        <DeviceStatusRow status={device.status} />

        <PublicAccessStatusRow state={publicAccessState} />

        {isAdmin ? (
          <QrActions
            canManageQr={canManageQr}
            device={device}
            emailVerified={emailVerified}
            onDownload={onDownloadQr}
            onGenerate={onGenerateQr}
            qrStatusState={qrStatusState}
          />
        ) : null}

        {publicAccessState?.status?.is_operational ? (
          <Button asChild className="w-full sm:w-auto" variant="outline">
            <Link href={`/p/${device.public_id}`} target="_blank">
              Ver perfil público
            </Link>
          </Button>
        ) : null}
      </CardContent>
    </Card>
  );
}
