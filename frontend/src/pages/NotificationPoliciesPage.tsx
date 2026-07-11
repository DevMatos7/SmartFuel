import { Link } from "react-router-dom";

export function NotificationPoliciesPage() {
  return (
    <div className="space-y-4">
      <Link className="text-sm underline" to="/executive/alerts">
        ← Alertas
      </Link>
      <h1 className="text-xl font-semibold">Políticas de notificação</h1>
      <ul className="space-y-2 text-sm">
        <li className="rounded border p-3">IN_APP · imediato para WARNING+ · ativo</li>
        <li className="rounded border p-3">
          EMAIL · CRITICAL · <strong>não homologado</strong> (desabilitado)
        </li>
      </ul>
    </div>
  );
}
