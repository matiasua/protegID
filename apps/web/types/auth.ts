export type AuthUser = {
  id: string;
  email: string;
  full_name: string | null;
  role: string;
  status: string;
  email_verified_at: string | null;
  email_verification_sent_at: string | null;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
};

export type LoginRequest = {
  email: string;
  password: string;
};

export type RegisterRequest = {
  email: string;
  password: string;
  full_name: string;
};

export type RegisterResponse = {
  user: AuthUser;
  verification_required: boolean;
};

export type VerifyEmailRequest = {
  token: string;
};

export type VerifyEmailResponse = {
  email_verified: boolean;
};

export type ResendVerificationResponse = {
  verification_required: boolean;
  verification_sent: boolean;
};
