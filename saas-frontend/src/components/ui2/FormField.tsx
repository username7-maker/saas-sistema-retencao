interface FormFieldProps {
  label: string;
  error?: string;
  required?: boolean;
  children: React.ReactNode;
}

export function FormField({ label, error, required = false, children }: FormFieldProps) {
  return (
    <div>
      <label className="mb-1 block text-sm font-medium text-lovable-ink">
        {label} {required ? "*" : null}
      </label>
      {children}
      {error ? <p className="mt-1 text-xs text-[hsl(var(--lovable-danger))]">{error}</p> : null}
    </div>
  );
}
