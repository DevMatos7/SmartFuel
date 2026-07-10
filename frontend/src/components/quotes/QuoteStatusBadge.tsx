const STATUS_LABELS: Record<string, string> = {
  DRAFT: "Rascunho",
  ACTIVE: "Ativa",
  EXPIRED: "Expirada",
  CANCELLED: "Cancelada",
  SUPERSEDED: "Substituída",
};

const STATUS_CLASSES: Record<string, string> = {
  DRAFT: "bg-slate-100 text-slate-700",
  ACTIVE: "bg-emerald-100 text-emerald-800",
  EXPIRED: "bg-amber-100 text-amber-800",
  CANCELLED: "bg-rose-100 text-rose-800",
  SUPERSEDED: "bg-violet-100 text-violet-800",
};

type Props = {
  status: string;
  effectiveStatus?: string;
};

export function QuoteStatusBadge({ status, effectiveStatus }: Props) {
  const display = effectiveStatus && effectiveStatus !== status ? effectiveStatus : status;
  const label = STATUS_LABELS[display] ?? display;
  const className = STATUS_CLASSES[display] ?? "bg-slate-100 text-slate-700";
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${className}`}>
      {label}
      {effectiveStatus && effectiveStatus !== status && (
        <span className="ml-1 text-[10px] opacity-70">({STATUS_LABELS[status]})</span>
      )}
    </span>
  );
}
