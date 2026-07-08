import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { fetchUsers } from "../api/users";
import { useAuth } from "../auth/AuthProvider";

export function UsersPage() {
  const { hasPermission } = useAuth();
  const canWrite = hasPermission("users.write");
  const { data, isLoading } = useQuery({
    queryKey: ["users"],
    queryFn: () => fetchUsers({ page: 1, page_size: 50 }),
  });

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold">Usuários</h1>
          <p className="text-sm text-slate-500">Gestão de acessos e perfis.</p>
        </div>
        {canWrite && (
          <Link to="/users/new" className="rounded bg-slate-900 px-4 py-2 text-sm text-white">
            Novo usuário
          </Link>
        )}
      </div>

      {isLoading ? (
        <p className="mt-6">Carregando...</p>
      ) : (
        <div className="mt-6 overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="border-b border-slate-200 text-slate-500">
              <tr>
                <th className="px-2 py-2">Usuário</th>
                <th className="px-2 py-2">E-mail</th>
                <th className="px-2 py-2">Perfis</th>
                <th className="px-2 py-2">Status</th>
                {canWrite && <th className="px-2 py-2">Ações</th>}
              </tr>
            </thead>
            <tbody>
              {data?.items.map((user) => (
                <tr key={user.id} className="border-b border-slate-100">
                  <td className="px-2 py-2">{user.name}</td>
                  <td className="px-2 py-2">{user.email}</td>
                  <td className="px-2 py-2">{user.role_codes.join(", ")}</td>
                  <td className="px-2 py-2">{user.active ? "Ativo" : "Inativo"}</td>
                  {canWrite && (
                    <td className="px-2 py-2">
                      <Link to={`/users/${user.id}`} className="text-slate-900 underline">
                        Editar
                      </Link>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
