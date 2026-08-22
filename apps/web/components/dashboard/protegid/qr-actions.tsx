import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/ui/status-badge";
import { isDeviceOperational } from "@/components/dashboard/protegid/types";
import type { DeviceQrStatusState } from "@/components/dashboard/protegid/use-protegid-devices";
import type { Device } from "@/types/device";

export interface QrActionsProps {
  device: Device;
  qrStatusState: DeviceQrStatusState | undefined;
  canManageQr: boolean;
  emailVerified: boolean;
  onGenerate: (device: Device) => void;
  onDownload: (device: Device) => void;
}

function getQrStatusLabel(state: DeviceQrStatusState | undefined): string {
  if (state?.isGenerating) {
    return "Generando QR...";
  }

  if (!state || state.isLoading) {
    return "Consultando QR...";
  }

  if (state.hasError) {
    return "QR no disponible";
  }

  return state.status?.exists ? "QR generado" : "QR pendiente";
}

function getQrStatusVariant(state: DeviceQrStatusState | undefined): "neutral" | "info" | "success" | "warning" {
  if (state?.isGenerating || !state || state.isLoading) {
    return "info";
  }

  if (state.hasError) {
    return "neutral";
  }

  return state.status?.exists ? "success" : "warning";
}

export function QrActions({ device, qrStatusState, canManageQr, emailVerified, onGenerate, onDownload }: QrActionsProps) {
  const canOperateDevice = isDeviceOperational(device.status);
  const generateLabel = qrStatusState?.isGenerating ? "Generando QR..." : qrStatusState?.status?.exists ? "Regenerar QR" : "Generar QR";
  const downloadLabel = qrStatusState?.isDownloading ? "Descargando QR..." : "Descargar QR";

  const isGenerateDisabled =
    !canManageQr || !canOperateDevice || !qrStatusState || qrStatusState.isLoading || qrStatusState.isGenerating || qrStatusState.isDownloading;
  const isDownloadDisabled =
    !canManageQr ||
    !canOperateDevice ||
    !qrStatusState ||
    qrStatusState.isLoading ||
    qrStatusState.isGenerating ||
    qrStatusState.isDownloading ||
    qrStatusState.hasError ||
    !qrStatusState.status?.exists;

  const shouldShowDownloadHelp =
    canOperateDevice && qrStatusState !== undefined && !qrStatusState.isLoading && !qrStatusState.hasError && !qrStatusState.status?.exists;

  return (
    <div className="rounded-lg border border-border bg-surface-muted p-4">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <h4 className="text-sm font-semibold text-foreground">Gestión de QR</h4>
        <StatusBadge label={getQrStatusLabel(qrStatusState)} variant={getQrStatusVariant(qrStatusState)} />
      </div>

      <p className="mt-2 text-xs leading-5 text-muted-foreground">
        El QR solo contiene la URL pública del perfil. La visualización depende de que el perfil esté marcado como público.
      </p>

      {!emailVerified ? (
        <p className="mt-3 rounded-lg border border-warning/30 bg-warning-muted px-3 py-2 text-sm font-medium text-warning">
          Debes verificar tu correo antes de realizar esta acción.
        </p>
      ) : null}

      {qrStatusState?.actionMessage ? (
        <p
          className={`mt-3 rounded-lg border px-3 py-2 text-sm ${
            qrStatusState.actionMessage.kind === "success"
              ? "border-success/30 bg-success-muted text-success"
              : "border-danger/30 bg-danger-muted text-danger"
          }`}
          role={qrStatusState.actionMessage.kind === "error" ? "alert" : "status"}
        >
          {qrStatusState.actionMessage.text}
        </p>
      ) : null}

      <div className="mt-3 flex flex-col gap-2 sm:flex-row">
        <Button className="w-full sm:w-auto" disabled={isGenerateDisabled} onClick={() => onGenerate(device)} type="button" variant="outline">
          {generateLabel}
        </Button>
        <Button className="w-full sm:w-auto" disabled={isDownloadDisabled} onClick={() => onDownload(device)} type="button" variant="outline">
          {downloadLabel}
        </Button>
      </div>

      {shouldShowDownloadHelp ? <p className="mt-2 text-xs text-muted-foreground">Genera el QR antes de descargarlo.</p> : null}
    </div>
  );
}
