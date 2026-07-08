import { Link } from "react-router-dom";
import { useAuth } from "../auth/AuthProvider";

export function ProfilePage() {
  const { user } = useAuth();

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-6">
      <h1 className="text-xl font-semibold">Meu perfil</h1>
      <dl className="mt-6 space-y-3 text-sm">
        <div>
          <dt className="text-slate-500">Nome</dt>
          <dd className="font-medium">{user?.name}</dd>
        </div>
        <div>
          <dt className="text-slate-500">E-mail</dt>
          <dd className="font-medium">{user?.email}</dd>
        </div>
        <div>
          <dt className="text-slate-500">Perfis</dt>
          <dd className="font-medium">{user?.roles.join(", ")}</dd>
        </div>
        <div>
          <dt className="text-slate-500">Postos permitidos</dt>
          <dd className="font-medium">
            {user?.has_all_stations_access
              ? "Todos os postos"
              : user?.stations.map((s) => s.trade_name).join(", ")}
          </dd>
        </div>
        <div>
          <dt className="text-slate-500">Último login</dt>
          <dd className="font-medium">
            {user?.last_login_at ? new Date(user.last_login_at).toLocaleString("pt-BR") : "—"}
          </dd>
        </div>
      </dl>
      <Link to="/change-password" className="mt-6 inline-block rounded bg-slate-900 px-4 py-2 text-sm text-white">
        Alterar senha
      </Link>
    </div>
  );
}
