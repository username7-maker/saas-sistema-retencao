import { Toaster, type ToasterProps } from "react-hot-toast";

/**
 * Dark Intelligence themed toaster.
 * Wraps react-hot-toast Toaster with our tokens — call-sites continue using
 * `toast.success(...)`, `toast.error(...)` exactly as before.
 */
export function ThemedToaster(props: ToasterProps) {
  return (
    <Toaster
      position="top-right"
      gutter={8}
      toastOptions={{
        duration: 4000,
        style: {
          background: "rgba(14,16,24,0.97)",
          color: "#F4F5F7",
          border: "1px solid rgba(255,255,255,0.08)",
          borderRadius: "12px",
          padding: "10px 14px",
          fontFamily: "'Inter', 'Barlow', sans-serif",
          fontSize: "13px",
          fontWeight: 500,
          boxShadow: "0 8px 32px rgba(0,0,0,0.48)",
          backdropFilter: "blur(12px)",
        },
        success: {
          iconTheme: {
            primary: "#10B981",
            secondary: "rgba(14,16,24,0.97)",
          },
        },
        error: {
          iconTheme: {
            primary: "#FF3B3B",
            secondary: "rgba(14,16,24,0.97)",
          },
        },
        loading: {
          iconTheme: {
            primary: "#3B82F6",
            secondary: "rgba(14,16,24,0.97)",
          },
        },
      }}
      {...props}
    />
  );
}
