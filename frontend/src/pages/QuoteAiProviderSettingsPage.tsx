import { Link } from "react-router-dom";

export function QuoteAiProviderSettingsPage() {
  return (
    <div className="space-y-4">
      <Link className="text-sm underline" to="/quotes/ai">
        ← Importar com IA
      </Link>
      <h1 className="text-xl font-semibold">Configuração do provedor de IA</h1>
      <p className="text-sm text-slate-600">
        Credenciais somente via secret_ref. allow_training_usage=false por padrão. Produção depende de
        homologação de custo, segurança e qualidade.
      </p>
      <ul className="list-disc pl-5 text-sm">
        <li>MockQuoteExtractionProvider — homologação sintética</li>
        <li>OpenAIQuoteExtractionProvider — stub até secret_ref homologado</li>
        <li>Canais e-mail/WhatsApp Business: flags desligadas</li>
      </ul>
    </div>
  );
}
