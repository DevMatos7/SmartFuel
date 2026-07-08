import { StatusPill } from "../components/StatusPill";
import { SystemStatusBanner } from "../components/SystemStatusBanner";
import { useHealthStatus } from "../hooks/useHealthStatus";

const FRONTEND_VERSION = import.meta.env.VITE_APP_VERSION ?? "0.1.0";

function formatDateTime(value: Date | null) {
  if (!value) {
    return "—";
  }
  return value.toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function HealthBoard() {
  const { data, uiStatus, lastCheckedAt, verifyAgain, isFetching } = useHealthStatus();
  const pending = uiStatus === "loading" || isFetching;

  return (
    <main className="mx-auto flex min-h-screen max-w-5xl flex-col gap-10 px-6 py-12">
      <header className="space-y-3">
        <p className="font-display text-sm font-semibold uppercase tracking-[0.2em] text-amber-signal">
          Smart Fuel
        </p>
        <h1 className="font-display text-4xl font-bold tracking-tight text-white md:text-5xl">
          Inteligência Auto Postos
        </h1>
        <p className="max-w-2xl text-base text-white/70">
          Plataforma de inteligência de combustíveis — página técnica da Sprint 0 para validar
          API, banco, cache e armazenamento de arquivos.
        </p>
      </header>

      <section className="rounded-2xl border border-white/10 bg-ink-900/70 p-6 backdrop-blur">
        <div className="space-y-6">
          <div>
            <h2 className="font-display text-xl font-semibold text-white">Status geral</h2>
            <p className="text-sm text-white/55">Diagnóstico do ambiente Docker</p>
          </div>

          <SystemStatusBanner status={uiStatus} />

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <StatusPill
              label="API"
              status={pending ? undefined : data ? data.services.api.status : "unhealthy"}
              pending={pending}
            />
            <StatusPill
              label="Banco de dados"
              status={data?.services.database.status}
              pending={pending}
            />
            <StatusPill
              label="Redis"
              status={data?.services.redis.status}
              pending={pending}
            />
            <StatusPill
              label="Arquivos"
              status={data?.services.object_storage.status}
              pending={pending}
            />
          </div>

          <dl className="grid gap-2 border-t border-white/10 pt-4 text-sm text-white/65 sm:grid-cols-2">
            <div>
              <dt className="text-white/40">Última verificação</dt>
              <dd className="font-medium text-white/80">{formatDateTime(lastCheckedAt)}</dd>
            </div>
            <div>
              <dt className="text-white/40">Versão da API</dt>
              <dd className="font-medium text-white/80">{data?.version ?? "—"}</dd>
            </div>
          </dl>

          <button
            type="button"
            onClick={verifyAgain}
            disabled={pending}
            className="inline-flex items-center justify-center rounded-lg bg-fuel-600 px-5 py-2.5 font-display text-sm font-semibold text-white transition hover:bg-fuel-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-fuel-400 disabled:cursor-not-allowed disabled:opacity-60"
          >
            Verificar novamente
          </button>
        </div>
      </section>

      <footer className="flex flex-wrap gap-4 text-sm text-white/40">
        <span>
          Versão frontend: <strong className="text-white/60">{FRONTEND_VERSION}</strong>
        </span>
        <span>
          API docs: <code className="text-white/55">/docs</code>
        </span>
      </footer>
    </main>
  );
}
