import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { useNavigate, useParams } from "react-router-dom";
import { z } from "zod";
import {
  createProduct,
  deactivateProduct,
  fetchProduct,
  reactivateProduct,
  updateProduct,
} from "../api/master-data";
import { useAuth } from "../auth/AuthProvider";

const schema = z.object({
  code: z.string().min(1, "Código obrigatório").max(60),
  name: z.string().min(1, "Nome obrigatório").max(150),
  fuel_family: z.string().min(1, "Família obrigatória"),
  commercial_variant: z.string().min(1, "Variante obrigatória"),
  unit: z.string().default("LITER"),
  regulatory_code: z.string().optional(),
  purchasable: z.boolean(),
  sellable: z.boolean(),
  display_order: z.coerce.number().int().min(0),
  active: z.boolean(),
});

type FormValues = z.infer<typeof schema>;

export function ProductFormPage() {
  const { productId } = useParams();
  const isNew = !productId || productId === "new";
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { hasPermission } = useAuth();
  const canDeactivate = hasPermission("products.deactivate");

  const { data: product } = useQuery({
    queryKey: ["product", productId],
    queryFn: () => fetchProduct(productId!),
    enabled: !isNew,
  });

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      code: "",
      name: "",
      fuel_family: "GASOLINE_C",
      commercial_variant: "COMMON",
      unit: "LITER",
      regulatory_code: "",
      purchasable: true,
      sellable: true,
      display_order: 0,
      active: true,
    },
  });

  useEffect(() => {
    if (product) {
      reset({
        code: product.code,
        name: product.name,
        fuel_family: product.fuel_family,
        commercial_variant: product.commercial_variant,
        unit: product.unit,
        regulatory_code: product.regulatory_code ?? "",
        purchasable: product.purchasable,
        sellable: product.sellable,
        display_order: product.display_order,
        active: product.active,
      });
    }
  }, [product, reset]);

  const saveMutation = useMutation({
    mutationFn: (values: FormValues) => {
      const payload = {
        ...values,
        regulatory_code: values.regulatory_code || null,
      };
      if (isNew) return createProduct(payload);
      return updateProduct(productId!, payload);
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["products"] });
      navigate("/products");
    },
  });

  const deactivateMutation = useMutation({
    mutationFn: (reason: string) => deactivateProduct(productId!, reason),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["products"] });
      navigate("/products");
    },
  });

  const reactivateMutation = useMutation({
    mutationFn: () => reactivateProduct(productId!),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["products", productId] });
    },
  });

  const onSubmit = handleSubmit((values) => saveMutation.mutate(values));

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-6">
      <h1 className="text-xl font-semibold">{isNew ? "Novo produto" : "Editar produto"}</h1>

      {(saveMutation.error || deactivateMutation.error) && (
        <p className="mt-4 rounded bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">
          {(saveMutation.error ?? deactivateMutation.error)?.message}
        </p>
      )}

      <form className="mt-6 grid gap-4 md:grid-cols-2" onSubmit={onSubmit}>
        <div>
          <label className="text-sm font-medium" htmlFor="code">
            Código
          </label>
          <input
            id="code"
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2 disabled:bg-slate-50"
            disabled={!isNew && product?.code_locked}
            {...register("code")}
          />
          {errors.code && <p className="mt-1 text-xs text-red-600">{errors.code.message}</p>}
        </div>
        <div>
          <label className="text-sm font-medium" htmlFor="name">
            Nome
          </label>
          <input id="name" className="mt-1 w-full rounded border border-slate-300 px-3 py-2" {...register("name")} />
          {errors.name && <p className="mt-1 text-xs text-red-600">{errors.name.message}</p>}
        </div>
        <div>
          <label className="text-sm font-medium" htmlFor="fuel_family">
            Família
          </label>
          <select id="fuel_family" className="mt-1 w-full rounded border border-slate-300 px-3 py-2" {...register("fuel_family")}>
            <option value="ETHANOL">Etanol</option>
            <option value="GASOLINE_C">Gasolina C</option>
            <option value="DIESEL_B_S10">Diesel B S10</option>
            <option value="DIESEL_B_S500">Diesel B S500</option>
          </select>
        </div>
        <div>
          <label className="text-sm font-medium" htmlFor="commercial_variant">
            Variante comercial
          </label>
          <select
            id="commercial_variant"
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
            {...register("commercial_variant")}
          >
            <option value="COMMON">Comum</option>
            <option value="ADDITIVATED">Aditivado</option>
          </select>
        </div>
        <div>
          <label className="text-sm font-medium" htmlFor="unit">
            Unidade
          </label>
          <input id="unit" className="mt-1 w-full rounded border border-slate-300 px-3 py-2" {...register("unit")} />
        </div>
        <div>
          <label className="text-sm font-medium" htmlFor="regulatory_code">
            Código regulatório
          </label>
          <input
            id="regulatory_code"
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
            {...register("regulatory_code")}
          />
        </div>
        <div>
          <label className="text-sm font-medium" htmlFor="display_order">
            Ordem de exibição
          </label>
          <input
            id="display_order"
            type="number"
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
            {...register("display_order")}
          />
        </div>
        <div className="flex flex-col gap-2 pt-6">
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" {...register("purchasable")} />
            Comprável
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" {...register("sellable")} />
            Vendável
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" {...register("active")} />
            Ativo
          </label>
        </div>

        <div className="md:col-span-2">
          <button
            type="submit"
            className="rounded bg-slate-900 px-4 py-2 text-white disabled:opacity-60"
            disabled={saveMutation.isPending}
          >
            {saveMutation.isPending ? "Salvando..." : "Salvar"}
          </button>
        </div>
      </form>

      {!isNew && product && (
        <div className="mt-8 border-t border-slate-200 pt-6">
          {product.active ? (
            canDeactivate && (
              <div>
                <h2 className="font-medium">Desativar produto</h2>
                <button
                  type="button"
                  className="mt-3 rounded border border-red-300 px-4 py-2 text-sm text-red-700"
                  disabled={deactivateMutation.isPending}
                  onClick={() => {
                    const reason = window.prompt("Informe o motivo da desativação (mín. 3 caracteres):");
                    if (reason && reason.length >= 3) deactivateMutation.mutate(reason);
                  }}
                >
                  Desativar
                </button>
              </div>
            )
          ) : (
            <div>
              <h2 className="font-medium">Reativar produto</h2>
              <button
                type="button"
                className="mt-3 rounded border border-slate-300 px-4 py-2 text-sm"
                disabled={reactivateMutation.isPending}
                onClick={() => reactivateMutation.mutate()}
              >
                Reativar
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
