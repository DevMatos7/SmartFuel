import { useQuery } from "@tanstack/react-query";
import { fetchHealth, fetchRootHealth } from "../services/health";

function StatusPill({ label, value }: { label: string; value?: string }) {
  const ok = value === "ok" || value === "configured";
  const tone = !value
    ? "bg-ink-700 text-white/60"
    : ok
      ? "bg-fuel-600/30 text-fuel-400 ring-1 ring-fuel-500/40"
      : "bg-red-900/40 text-red-300 ring-1 ring-red-500/30";

  return (
    <div className={`rounded-lg px-4 py-3 ${tone}`}>
      <p className="text-xs uppercase tracking-wider opacity-70">{label}</p>
      <p className="mt-1 font-display text-lg font-semibold capitalize">{value ?? "—"}</p>
    </div>
  );
}

export function HealthBoard() {
  const detailed = useQuery({
    queryKey: ["health", "v1"],
    queryFn: fetchHealth,
    refetchInterval: 15_000,
  });

  const root = useQuery({
    queryKey: ["health", "root"],
    queryFn: fetchRootHealth,
    refetchInterval: 15_000,
  });

  const apiOnline = detailed.isSuccess || root.isSuccess;
  const apiError = detailed.isError && root.isError;

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
          Página técnica da Sprint 0 — fundação da API, infraestrutura Docker e checagem de
          serviços. Sem autenticação ou regras de negócio nesta etapa.
        </p>
      </header>

      <section className="rounded-2xl border border-white/10 bg-ink-900/70 p-6 backdrop-blur">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h2 className="font-display text-xl font-semibold text-white">Status da API</h2>
            <p className="text-sm text-white/55">Atualiza a cada 15 segundos</p>
          </div>
          <span
            className={`rounded-full px-4 py-1.5 font-display text-sm font-semibold ${
              apiOnline
                ? "bg-fuel-600/25 text-fuel-400"
                : apiError
                  ? "bg-red-900/50 text-red-300"
                  : "bg-ink-700 text-white/60"
            }`}
          >
            {detailed.isLoading || root.isLoading
              ? "Verificando…"
              : apiOnline
                ? "Online"
                : "Indisponível"}
          </span>
        </div>

        <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <StatusPill label="API" value={apiOnline ? "ok" : apiError ? "unavailable" : undefined} />
          <StatusPill label="PostgreSQL" value={detailed.data?.database} />
          <StatusPill label="Redis" value={detailed.data?.redis} />
          <StatusPill label="MinIO" value={detailed.data?.minio} />
        </div>

        {(detailed.data || root.data) && (
          <dl className="mt-6 grid gap-2 border-t border-white/10 pt-4 text-sm text-white/65 sm:grid-cols-2">
            <div>
              <dt className="text-white/40">Versão</dt>
              <dd className="font-medium text-white/80">
                {detailed.data?.version ?? root.data?.version}
              </dd>
            </div>
            <div>
              <dt className="text-white/40">Ambiente</dt>
              <dd className="font-medium text-white/80">
                {detailed.data?.environment ?? "—"}
              </dd>
            </div>
          </dl>
        )}

        {apiError && (
          <p className="mt-4 text-sm text-red-300">
            Não foi possível contatar o backend. Confirme se o Compose está no ar e se{" "}
            <code className="rounded bg-ink-800 px-1.5 py-0.5">VITE_API_BASE_URL</code> está
            correto.
          </p>
        )}
      </section>

      <footer className="text-sm text-white/40">
        Documentação da API: <code className="text-white/55">/docs</code> · Health:{" "}
        <code className="text-white/55">/health</code> e{" "}
        <code className="text-white/55">/api/v1/health</code>
      </footer>
    </main>
  );
}
