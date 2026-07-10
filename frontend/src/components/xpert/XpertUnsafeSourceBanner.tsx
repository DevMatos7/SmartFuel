export function XpertUnsafeSourceBanner({ securityStatus }: { securityStatus?: string | null }) {
  if (securityStatus !== "UNSAFE") return null;
  return (
    <div className="rounded-lg border border-red-300 bg-red-50 p-4 text-sm text-red-900" role="alert">
      <p className="font-semibold">Fonte XPERT insegura — homologação com usuário administrativo</p>
      <p className="mt-1">
        A aplicação executará apenas consultas SELECT validadas, porém a conta configurada possui
        privilégios de escrita no banco do ERP. Esta configuração não está aprovada para produção.
        A agenda automática está bloqueada.
      </p>
    </div>
  );
}
