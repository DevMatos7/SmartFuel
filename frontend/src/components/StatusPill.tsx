import type { ServiceStatus } from "../types/health";

const LABELS: Record<ServiceStatus, string> = {
  healthy: "Operacional",
  unhealthy: "Indisponível",
};

type StatusPillProps = {
  label: string;
  status?: ServiceStatus;
  pending?: boolean;
};

export function StatusPill({ label, status, pending }: StatusPillProps) {
  const tone = pending
    ? "bg-ink-700 text-white/60 animate-pulse"
    : status === "healthy"
      ? "bg-fuel-600/30 text-fuel-400 ring-1 ring-fuel-500/40"
      : status === "unhealthy"
        ? "bg-red-900/40 text-red-300 ring-1 ring-red-500/30"
        : "bg-ink-700 text-white/60";

  return (
    <div className={`rounded-lg px-4 py-3 ${tone}`} role="status" aria-label={label}>
      <p className="text-xs uppercase tracking-wider opacity-70">{label}</p>
      <p className="mt-1 font-display text-lg font-semibold">
        {pending ? "Verificando…" : status ? LABELS[status] : "—"}
      </p>
    </div>
  );
}
