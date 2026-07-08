import type { MasterDataImportRow } from "../../api/master-data";

const STATUS_LABELS: Record<string, string> = {
  VALID: "Válido",
  INVALID: "Inválido",
  SKIPPED: "Ignorado",
  PROCESSED: "Processado",
  FAILED: "Falhou",
};

const ACTION_LABELS: Record<string, string> = {
  INSERT: "Inserir",
  UPDATE: "Atualizar",
  UNCHANGED: "Sem alteração",
  SKIP: "Ignorar",
};

type ImportPreviewTableProps = {
  rows: MasterDataImportRow[];
};

export function ImportPreviewTable({ rows }: ImportPreviewTableProps) {
  if (!rows.length) {
    return <p className="text-sm text-slate-500">Nenhuma linha para exibir.</p>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-left text-sm">
        <thead className="border-b border-slate-200 text-slate-500">
          <tr>
            <th className="px-2 py-2">Linha</th>
            <th className="px-2 py-2">Identificador</th>
            <th className="px-2 py-2">Ação</th>
            <th className="px-2 py-2">Status</th>
            <th className="px-2 py-2">Dados</th>
            <th className="px-2 py-2">Erros</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id} className="border-b border-slate-100 align-top">
              <td className="px-2 py-2">{row.row_number}</td>
              <td className="px-2 py-2 font-mono text-xs">{row.external_identifier ?? "—"}</td>
              <td className="px-2 py-2">{ACTION_LABELS[row.action] ?? row.action}</td>
              <td className="px-2 py-2">
                <span
                  className={`rounded px-2 py-0.5 text-xs ${
                    row.status === "VALID" || row.status === "PROCESSED"
                      ? "bg-green-50 text-green-800"
                      : row.status === "INVALID" || row.status === "FAILED"
                        ? "bg-red-50 text-red-800"
                        : "bg-slate-100 text-slate-700"
                  }`}
                >
                  {STATUS_LABELS[row.status] ?? row.status}
                </span>
              </td>
              <td className="max-w-xs px-2 py-2">
                <pre className="max-h-24 overflow-auto text-xs text-slate-600">
                  {JSON.stringify(row.normalized_data ?? row.raw_data, null, 2)}
                </pre>
              </td>
              <td className="max-w-xs px-2 py-2">
                {row.validation_errors ? (
                  <pre className="max-h-24 overflow-auto text-xs text-red-700">
                    {JSON.stringify(row.validation_errors, null, 2)}
                  </pre>
                ) : (
                  "—"
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
