import { useAuth } from "../auth/AuthProvider";

export function HomePage() {
  const { user } = useAuth();
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-6">
      <h1 className="text-2xl font-semibold">Bem-vindo, {user?.name}</h1>
      <p className="mt-2 text-slate-600">
        Use o menu lateral para gerenciar organização, postos e usuários conforme suas permissões.
      </p>
    </div>
  );
}
