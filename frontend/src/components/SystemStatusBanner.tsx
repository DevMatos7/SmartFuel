import type { UiStatus } from "../types/health";

const COPY: Record<
  UiStatus,
  { title: string; description: string; tone: string; icon: string }
> = {
  loading: {
    title: "Verificando os serviços",
    description: "Aguarde enquanto consultamos a API e as dependências.",
    tone: "bg-ink-700 text-white/70",
    icon: "◌",
  },
  healthy: {
    title: "Todos os serviços estão operacionais",
    description: "API, banco, cache e armazenamento responderam corretamente.",
    tone: "bg-fuel-600/25 text-fuel-400",
    icon: "✓",
  },
  degraded: {
    title: "Sistema disponível com instabilidade",
    description: "A API responde, mas algum serviço secundário está indisponível.",
    tone: "bg-amber-900/40 text-amber-signal ring-1 ring-amber-signal/30",
    icon: "!",
  },
  unavailable: {
    title: "Não foi possível conectar ao servidor",
    description: "Verifique se o Docker Compose está em execução e tente novamente.",
    tone: "bg-red-900/50 text-red-300",
    icon: "✕",
  },
};

type SystemStatusBannerProps = {
  status: UiStatus;
};

export function SystemStatusBanner({ status }: SystemStatusBannerProps) {
  const copy = COPY[status];
  return (
    <div
      className={`flex items-start gap-3 rounded-xl px-4 py-3 ${copy.tone}`}
      role="status"
      aria-live="polite"
    >
      <span className="font-display text-xl leading-none" aria-hidden="true">
        {copy.icon}
      </span>
      <div>
        <p className="font-display font-semibold">{copy.title}</p>
        <p className="mt-1 text-sm opacity-90">{copy.description}</p>
      </div>
    </div>
  );
}
