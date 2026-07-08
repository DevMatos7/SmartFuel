import { Link } from "react-router-dom";

export function ForbiddenPage() {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-8 text-center">
      <h1 className="text-2xl font-semibold">Acesso negado</h1>
      <p className="mt-2 text-slate-600">Você não possui permissão para acessar esta área.</p>
      <div className="mt-6 flex justify-center gap-3">
        <button type="button" className="rounded border border-slate-300 px-4 py-2" onClick={() => history.back()}>
          Voltar
        </button>
        <Link to="/" className="rounded bg-slate-900 px-4 py-2 text-white">
          Ir para a página inicial
        </Link>
      </div>
    </div>
  );
}
