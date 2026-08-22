"use client";

import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

const inputClassName =
  "mt-2 w-full min-h-[44px] rounded-lg border border-input bg-background px-3.5 py-2.5 text-sm text-foreground shadow-sm outline-none transition placeholder:text-muted-foreground focus-visible:border-primary focus-visible:ring-4 focus-visible:ring-primary/15 disabled:cursor-not-allowed disabled:opacity-60";

export interface TextFieldProps {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
  required?: boolean;
  placeholder?: string;
  helpText?: string;
  className?: string;
}

export function TextField({ id, label, value, onChange, disabled, required, placeholder, helpText, className }: TextFieldProps) {
  const helpId = helpText ? `${id}-help` : undefined;

  return (
    <div className={className}>
      <label className="text-sm font-medium text-foreground" htmlFor={id}>
        {label}
        {required ? <span aria-hidden="true" className="ml-0.5 text-danger">*</span> : null}
      </label>
      <input
        aria-describedby={helpId}
        aria-required={required}
        className={inputClassName}
        disabled={disabled}
        id={id}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        type="text"
        value={value}
      />
      {helpText ? (
        <p className="mt-1.5 text-xs text-muted-foreground" id={helpId}>
          {helpText}
        </p>
      ) : null}
    </div>
  );
}

export interface TextAreaFieldProps {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
  className?: string;
  none?: {
    id: string;
    checked: boolean;
    label: string;
    onChange: (checked: boolean) => void;
    disabled?: boolean;
  };
}

export function TextAreaField({ id, label, value, onChange, disabled, className, none }: TextAreaFieldProps) {
  const isDisabled = disabled || none?.checked;

  return (
    <div className={className}>
      <label className="text-sm font-medium text-foreground" htmlFor={id}>
        {label}
      </label>
      <textarea
        className={cn(inputClassName, "min-h-28 resize-y")}
        disabled={isDisabled}
        id={id}
        onChange={(event) => onChange(event.target.value)}
        value={value}
      />
      {none ? (
        <CheckboxField
          checked={none.checked}
          className="mt-2"
          disabled={none.disabled}
          id={none.id}
          label={none.label}
          onChange={none.onChange}
        />
      ) : null}
    </div>
  );
}

export interface CheckboxFieldProps {
  id: string;
  label: ReactNode;
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
  className?: string;
  helpText?: string;
}

export function CheckboxField({ id, label, checked, onChange, disabled, className, helpText }: CheckboxFieldProps) {
  const helpId = helpText ? `${id}-help` : undefined;

  return (
    <label
      className={cn(
        "flex min-h-[44px] items-start gap-3 rounded-lg border border-border bg-surface px-3.5 py-3 text-sm text-foreground",
        disabled ? "opacity-60" : undefined,
        className,
      )}
      htmlFor={id}
    >
      <input
        aria-describedby={helpId}
        checked={checked}
        className="mt-0.5 h-4 w-4 shrink-0 rounded border-input text-primary focus-visible:ring-2 focus-visible:ring-ring"
        disabled={disabled}
        id={id}
        onChange={(event) => onChange(event.target.checked)}
        type="checkbox"
      />
      <span>
        {label}
        {helpText ? (
          <span className="mt-1 block text-xs text-muted-foreground" id={helpId}>
            {helpText}
          </span>
        ) : null}
      </span>
    </label>
  );
}
