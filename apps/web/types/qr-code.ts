export type DeviceQrMetadata = {
  device_id: string;
  public_id: string;
  object_key: string;
  content_type: string;
};

export type DeviceQrStatus = DeviceQrMetadata & {
  exists: boolean;
};
