export type DeviceStatus = "pending_activation" | "active" | "disabled" | "lost";

export type Device = {
  id: string;
  user_id: string | null;
  public_id: string;
  label: string | null;
  status: DeviceStatus;
  device_type: string;
  activated_at: string | null;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
};
