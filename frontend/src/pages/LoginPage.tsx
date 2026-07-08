import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthProvider";

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const sessionExpired = (location.state as { sessionExpired?: boolean } | null)?.sessionExpired;

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const me = await login(email, password);
      if (me.must_change_password) {
        navigate("/change-password");
      } else {
        const from = (location.state as { from?: { pathname: string } } | null)?.from?.pathname ?? "/";
        navigate(from, { replace: true });
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha no login.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-100 px-4">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-md rounded-xl border border-slate-200 bg-white p-8 shadow-sm"
      >
        <h1 className="text-2xl font-semibold">Inteligência Auto Postos</h1>
        <p className="mt-1 text-sm text-slate-500">Gestão estratégica de combustíveis</p>

        {sessionExpired && (
          <p className="mt-4 rounded bg-amber-50 px-3 py-2 text-sm text-amber-800" role="alert">
            Sua sessão expirou. Entre novamente.
          </p>
        )}
        {error && (
          <p className="mt-4 rounded bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">
            {error}
          </p>
        )}

        <label className="mt-6 block text-sm font-medium" htmlFor="email">
          E-mail
        </label>
        <input
          id="email"
          type="email"
          autoComplete="username"
          className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />

        <label className="mt-4 block text-sm font-medium" htmlFor="password">
          Senha
        </label>
        <div className="mt-1 flex gap-2">
          <input
            id="password"
            type={showPassword ? "text" : "password"}
            autoComplete="current-password"
            className="w-full rounded border border-slate-300 px-3 py-2"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          <button
            type="button"
            className="rounded border border-slate-300 px-3 text-sm"
            onClick={() => setShowPassword((v) => !v)}
            aria-label={showPassword ? "Ocultar senha" : "Mostrar senha"}
          >
            {showPassword ? "Ocultar" : "Ver"}
          </button>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="mt-6 w-full rounded bg-slate-900 px-4 py-2 text-white disabled:opacity-60"
        >
          {loading ? "Entrando..." : "Entrar"}
        </button>

        <p className="mt-6 text-center text-xs text-slate-500">Ambiente interno autorizado</p>
      </form>
    </div>
  );
}
