import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { fetchStations, type Station } from "../api/stations";
import {
  createUser,
  fetchUsers,
  resetUserPassword,
  updateUser,
  updateUserRoles,
  updateUserStations,
} from "../api/users";

const ROLES = ["ADMIN", "GESTOR", "COMPRADOR", "FINANCEIRO", "CONSULTA"];

export function UserFormPage() {
  const { userId } = useParams();
  const isNew = !userId || userId === "new";
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data: users } = useQuery({
    queryKey: ["users"],
    queryFn: () => fetchUsers({ page: 1, page_size: 100 }),
    enabled: !isNew,
  });
  const { data: stationsData } = useQuery({
    queryKey: ["stations"],
    queryFn: () => fetchStations({ page: 1, page_size: 100, active: true }),
  });

  const [form, setForm] = useState({
    name: "",
    email: "",
    temporary_password: "",
    role_codes: ["CONSULTA"] as string[],
    station_ids: [] as string[],
    has_all_stations_access: false,
    must_change_password: true,
    active: true,
  });
  const [stationSearch, setStationSearch] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [generatedPassword, setGeneratedPassword] = useState<string | null>(null);

  const isAdmin = form.role_codes.includes("ADMIN");
  const stations = stationsData?.items ?? [];

  const filteredStations = useMemo(() => {
    const term = stationSearch.trim().toLowerCase();
    if (!term) return stations;
    return stations.filter(
      (s) =>
        s.trade_name.toLowerCase().includes(term) ||
        s.corporate_name.toLowerCase().includes(term) ||
        s.cnpj.includes(term),
    );
  }, [stationSearch, stations]);

  useEffect(() => {
    if (!isNew && users?.items.length) {
      const user = users.items.find((u) => u.id === userId);
      if (user) {
        setForm({
          name: user.name,
          email: user.email,
          temporary_password: "",
          role_codes: user.role_codes,
          station_ids: user.station_ids,
          has_all_stations_access: user.has_all_stations_access,
          must_change_password: user.must_change_password,
          active: user.active,
        });
      }
    }
  }, [isNew, userId, users]);

  useEffect(() => {
    if (!isAdmin && form.has_all_stations_access) {
      setForm((f) => ({ ...f, has_all_stations_access: false }));
    }
  }, [isAdmin, form.has_all_stations_access]);

  function toggleStation(stationId: string) {
    setForm((f) => ({
      ...f,
      station_ids: f.station_ids.includes(stationId)
        ? f.station_ids.filter((id) => id !== stationId)
        : [...f.station_ids, stationId],
    }));
  }

  function selectVisibleStations() {
    setForm((f) => ({
      ...f,
      station_ids: Array.from(new Set([...f.station_ids, ...filteredStations.map((s) => s.id)])),
    }));
  }

  function clearStations() {
    setForm((f) => ({ ...f, station_ids: [] }));
  }

  const saveMutation = useMutation({
    mutationFn: async () => {
      if (!form.has_all_stations_access && form.station_ids.length === 0) {
        throw new Error("Selecione ao menos um posto ou ative o acesso total.");
      }
      if (form.has_all_stations_access && !isAdmin) {
        throw new Error("Acesso total aos postos é permitido apenas para ADMIN.");
      }

      if (isNew) {
        return createUser({
          ...form,
          station_ids: form.has_all_stations_access ? [] : form.station_ids,
        });
      }

      await updateUser(userId!, {
        name: form.name,
        email: form.email,
        active: form.active,
        has_all_stations_access: form.has_all_stations_access,
      });
      await updateUserRoles(userId!, form.role_codes);
      return updateUserStations(userId!, {
        station_ids: form.has_all_stations_access ? [] : form.station_ids,
        has_all_stations_access: form.has_all_stations_access,
      });
    },
    onSuccess: async () => {
      setError(null);
      await queryClient.invalidateQueries({ queryKey: ["users"] });
      navigate("/users");
    },
    onError: (err: Error) => setError(err.message),
  });

  const resetMutation = useMutation({
    mutationFn: async () => resetUserPassword(userId!, { must_change_password: true }),
    onSuccess: (data) => setGeneratedPassword(data.temporary_password),
  });

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-6">
      <h1 className="text-xl font-semibold">{isNew ? "Novo usuário" : "Editar usuário"}</h1>

      {error && (
        <p className="mt-4 rounded bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">
          {error}
        </p>
      )}

      <form
        className="mt-6 space-y-8"
        onSubmit={(e) => {
          e.preventDefault();
          saveMutation.mutate();
        }}
      >
        <section className="grid gap-4 md:grid-cols-2">
          <h2 className="md:col-span-2 text-sm font-semibold uppercase tracking-wide text-slate-500">Perfil</h2>
          <div>
            <label className="text-sm font-medium" htmlFor="user-name">
              Nome
            </label>
            <input
              id="user-name"
              className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
              value={form.name}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              required
            />
          </div>
          <div>
            <label className="text-sm font-medium" htmlFor="user-email">
              E-mail
            </label>
            <input
              id="user-email"
              type="email"
              className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
              value={form.email}
              onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
              required
            />
          </div>
          {isNew && (
            <div>
              <label className="text-sm font-medium" htmlFor="user-password">
                Senha temporária
              </label>
              <input
                id="user-password"
                type="password"
                className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
                value={form.temporary_password}
                onChange={(e) => setForm((f) => ({ ...f, temporary_password: e.target.value }))}
              />
            </div>
          )}
        </section>

        <section>
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">Acessos</h2>
          <div className="mt-3 flex flex-wrap gap-3">
            {ROLES.map((role) => (
              <label key={role} className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={form.role_codes.includes(role)}
                  onChange={(e) => {
                    setForm((f) => ({
                      ...f,
                      role_codes: e.target.checked
                        ? [...f.role_codes, role]
                        : f.role_codes.filter((r) => r !== role),
                    }));
                  }}
                />
                {role}
              </label>
            ))}
          </div>

          <label className="mt-4 flex items-start gap-2 text-sm">
            <input
              type="checkbox"
              checked={form.has_all_stations_access}
              disabled={!isAdmin}
              onChange={(e) =>
                setForm((f) => ({
                  ...f,
                  has_all_stations_access: e.target.checked,
                  station_ids: e.target.checked ? f.station_ids : f.station_ids,
                }))
              }
            />
            <span>
              Acesso total aos postos
              {!isAdmin && (
                <span className="mt-1 block text-xs text-amber-700">
                  Disponível apenas para usuários com perfil ADMIN.
                </span>
              )}
            </span>
          </label>

          {!form.has_all_stations_access && (
            <div className="mt-4 rounded border border-slate-200 p-4">
              <div className="flex flex-wrap items-center gap-2">
                <input
                  type="search"
                  placeholder="Buscar postos..."
                  className="rounded border border-slate-300 px-3 py-2 text-sm"
                  value={stationSearch}
                  onChange={(e) => setStationSearch(e.target.value)}
                  aria-label="Buscar postos"
                />
                <button
                  type="button"
                  className="rounded border border-slate-300 px-3 py-2 text-sm"
                  onClick={selectVisibleStations}
                >
                  Selecionar visíveis
                </button>
                <button
                  type="button"
                  className="rounded border border-slate-300 px-3 py-2 text-sm"
                  onClick={clearStations}
                >
                  Limpar seleção
                </button>
              </div>

              <p className="mt-3 text-xs text-slate-500">
                {form.station_ids.length} posto(s) selecionado(s)
              </p>

              <div className="mt-3 max-h-56 space-y-2 overflow-y-auto">
                {filteredStations.map((station: Station) => (
                  <label key={station.id} className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={form.station_ids.includes(station.id)}
                      onChange={() => toggleStation(station.id)}
                    />
                    <span>
                      {station.station_type === "HEADQUARTERS" ? "Matriz — " : ""}
                      {station.trade_name}
                    </span>
                  </label>
                ))}
                {!filteredStations.length && (
                  <p className="text-sm text-slate-500">Nenhum posto encontrado.</p>
                )}
              </div>
            </div>
          )}
        </section>

        <button
          type="submit"
          className="rounded bg-slate-900 px-4 py-2 text-white disabled:opacity-60"
          disabled={saveMutation.isPending}
        >
          {saveMutation.isPending ? "Salvando..." : "Salvar"}
        </button>
      </form>

      {!isNew && (
        <div className="mt-8 border-t border-slate-200 pt-6">
          <h2 className="font-medium">Redefinir senha</h2>
          <button
            type="button"
            className="mt-3 rounded border border-slate-300 px-4 py-2 text-sm"
            onClick={() => resetMutation.mutate()}
            disabled={resetMutation.isPending}
          >
            Gerar senha temporária
          </button>
          {generatedPassword && (
            <p className="mt-3 rounded bg-amber-50 px-3 py-2 text-sm text-amber-900">
              Senha temporária (exibida uma vez): <strong>{generatedPassword}</strong>
            </p>
          )}
        </div>
      )}
    </div>
  );
}
