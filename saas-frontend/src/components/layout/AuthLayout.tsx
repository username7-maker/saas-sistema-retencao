import type { ReactNode } from "react";
import { BRAND_ASSETS, PRODUCT_NAME } from "../../config/brand";

interface AuthLayoutProps {
  children: ReactNode;
}

/**
 * Dark Intelligence auth shell.
 * Provides the atmospheric background + brand mark for login / reset-password pages.
 * Never wraps authenticated routes.
 */
export function AuthLayout({ children }: AuthLayoutProps) {
  return (
    <div className="relative flex min-h-dvh flex-col items-center justify-center overflow-hidden bg-[#0A0B0F] px-4 py-10">
      {/* Ambient radial — blue at top-left, violet at bottom-right */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 z-0"
        style={{
          background:
            "radial-gradient(ellipse 70% 55% at -5% 0%, rgba(59,130,246,0.13) 0%, transparent 60%)," +
            "radial-gradient(ellipse 55% 45% at 105% 105%, rgba(139,92,246,0.09) 0%, transparent 60%)",
        }}
      />

      {/* Subtle dot-grid overlay */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 z-0"
        style={{
          backgroundImage:
            "radial-gradient(circle, rgba(255,255,255,0.045) 1px, transparent 1px)",
          backgroundSize: "32px 32px",
          maskImage:
            "radial-gradient(ellipse 80% 60% at 50% 40%, black 0%, transparent 80%)",
        }}
      />

      {/* Brand watermark — product name top-center */}
      <div className="relative z-10 mb-6 flex flex-col items-center gap-3">
        <div className="flex h-12 w-12 items-center justify-center overflow-hidden rounded-2xl border border-white/[0.10] bg-white/[0.05] shadow-[0_4px_24px_rgba(59,130,246,0.18)]">
          <img src={BRAND_ASSETS.markDark} alt={PRODUCT_NAME} className="h-9 w-9 object-contain" />
        </div>
        <p className="text-[11px] font-bold uppercase tracking-[0.28em] text-white/40">{PRODUCT_NAME}</p>
      </div>

      {/* Auth card */}
      <div className="relative z-10 w-full max-w-md">{children}</div>
    </div>
  );
}
