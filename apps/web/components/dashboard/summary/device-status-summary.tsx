import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { DeviceAggregation } from "@/components/dashboard/summary/derive-protection-status";

export interface DeviceStatusSummaryProps {
  aggregation: DeviceAggregation;
  isLoadingDevices: boolean;
  devicesErrorMessage: string | null;
}

export function DeviceStatusSummary({ aggregation, isLoadingDevices, devicesErrorMessage }: DeviceStatusSummaryProps) {
  return (
    <Card aria-labelledby="device-summary-title">
      <CardHeader className="flex-row items-center justify-between gap-3 space-y-0">
        <CardTitle id="device-summary-title">Mis ProtegID</CardTitle>
        <Button asChild variant="outline">
          <Link href="/dashboard/protegid">Ver Mis ProtegID</Link>
        </Button>
      </CardHeader>
      <CardContent>
        {isLoadingDevices ? (
          <p className="text-sm text-muted-foreground">Consultando tus identificadores...</p>
        ) : devicesErrorMessage ? (
          <p className="text-sm font-medium text-danger" role="alert">
            No se pudo consultar el estado de tus ProtegID en este momento.
          </p>
        ) : aggregation.total === 0 ? (
          <p className="text-sm text-muted-foreground">Todavía no tienes un ProtegID asociado a tu cuenta.</p>
        ) : (
          <div className="space-y-1.5 text-sm">
            <p className="font-medium text-foreground">
              {aggregation.total} ProtegID{aggregation.total === 1 ? "" : "s"}
            </p>
            <ul className="space-y-1 text-muted-foreground">
              {aggregation.operationalCount > 0 ? (
                <li>
                  {aggregation.operationalCount} disponible{aggregation.operationalCount === 1 ? "" : "s"}
                </li>
              ) : null}
              {aggregation.attentionCount > 0 ? (
                <li>
                  {aggregation.attentionCount} requiere{aggregation.attentionCount === 1 ? "" : "n"} atención
                </li>
              ) : null}
              {aggregation.pendingCount > 0 ? (
                <li>Consultando estado de {aggregation.pendingCount} ProtegID...</li>
              ) : null}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
