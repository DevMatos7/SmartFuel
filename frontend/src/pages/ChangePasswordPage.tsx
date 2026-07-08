import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { changePassword } from "../api/auth";
import { useAuth } from "../auth/AuthProvider";

export function ChangePasswordPage() {
  const { refreshUser } = useAuth();
  const navigate = useNavigate();
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await changePassword({
        current_password: currentPassword,
        new_password: newPassword,
        new_password_confirmation: confirmation,
      });
      await refreshUser();
      navigate("/", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Não foi possível alterar a senha.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-lg rounded-lg border border-slate-200 bg-white p-6">
      <h1 className="text-xl font-semibold">Alterar senha</h1>
      <p className="mt-1 text-sm text-slate-500">É necessário definir uma nova senha para continuar.</p>
      {error && (
        <p className="mt-4 rounded bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">
          {error}
        </p>
      )}
      <form onSubmit={handleSubmit} className="mt-6 space-y-4">
        <div>
          <label htmlFor="current" className="text-sm font-medium">
            Senha atual
          </label>
          <input
            id="current"
            type="password"
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            required
          />
        </div>
        <div>
          <label htmlFor="new" className="text-sm font-medium">
            Nova senha
          </label>
          <input
            id="new"
            type="password"
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            required
          />
        </div>
        <div>
          <label htmlFor="confirm" className="text-sm font-medium">
            Confirmar nova senha
          </label>
          <input
            id="confirm"
            type="password"
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
            value={confirmation}
            onChange={(e) => setConfirmation(e.target.value)}
            required
          />
        </div>
        <button
          type="submit"
          disabled={loading}
          className="rounded bg-slate-900 px-4 py-2 text-white disabled:opacity-60"
        >
          {loading ? "Salvando..." : "Salvar nova senha"}
        </button>
      </form>
    </div>
  );
}
