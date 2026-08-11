"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import { TableCard, TableLegend } from "@/components/TableCard";
import { useToast } from "@/components/Toast";
import { api } from "@/lib/api";
import { usePolling, useSession } from "@/lib/hooks";
import type { Paginated, Table, TableAction } from "@/lib/types";

const POLL_MS = 6000;

export default function StaffPage() {
  const router = useRouter();
  const { user, loading: loadingUser } = useSession();
  const toast = useToast();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const restaurantId = user?.restaurant_id ?? null;
  const { data, error, refresh } = usePolling<Paginated<Table>>(
    async () =>
      restaurantId
        ? api.get<Paginated<Table>>(`/restaurants/${restaurantId}/tables`)
        : { items: [] },
    POLL_MS,
  );

  const tables = useMemo(
    () =>
      [...(data?.items ?? [])].sort((a, b) =>
        a.number.localeCompare(b.number, "pt-BR", { numeric: true }),
      ),
    [data],
  );
  const selected = tables.find((table) => table.id === selectedId) ?? null;

  async function act(path: string, successText: string) {
    if (!selected || busy) return;
    setBusy(true);
    try {
      const result = await api.post<TableAction>(`/tables/${selected.id}/${path}`);
      if (result.allocation) {
        toast.show(
          `Mesa ${result.allocation.table_number} para ${result.allocation.customer_name} ` +
            `(${result.allocation.party_size} pessoas). Cliente notificado.`,
          "success",
        );
      } else {
        toast.show(successText, "info");
      }
      await refresh();
    } catch (err) {
      toast.show(err instanceof Error ? err.message : "Falha na operacao.", "error");
    } finally {
      setBusy(false);
    }
  }

  if (loadingUser) return <p className="muted">Carregando...</p>;

  if (!user) {
    return (
      <div className="card">
        <h1>Acesso do salao</h1>
        <p className="muted">Entre com sua conta de staff para operar as mesas.</p>
        <Link className="btn btn-primary" href="/login?next=/staff">
          Fazer login
        </Link>
      </div>
    );
  }

  if (!restaurantId) {
    return (
      <div className="card">
        <h1>Sem restaurante vinculado</h1>
        <p className="muted">
          Sua conta nao esta ligada a um restaurante. Peca ao administrador para vincular.
        </p>
      </div>
    );
  }

  return (
    <section>
      <h1>Salao</h1>
      <p className="subtitle">
        Toque em uma mesa e use o botao grande. A fila anda sozinha depois disso.
      </p>

      {error ? <p className="error">{error}</p> : null}

      <div className="grid" data-testid="floor-grid">
        {tables.map((table) => (
          <TableCard
            key={table.id}
            table={table}
            selected={table.id === selectedId}
            onSelect={(item) => setSelectedId(item.id === selectedId ? null : item.id)}
          />
        ))}
      </div>
      {tables.length === 0 ? <p className="muted">Nenhuma mesa cadastrada ainda.</p> : null}
      <TableLegend />

      <div className="action-panel">
        {selected ? (
          <>
            <div className="row">
              <strong>
                Mesa {selected.number} - {selected.capacity} lugares
              </strong>
              <button type="button" className="btn" onClick={() => setSelectedId(null)}>
                Fechar
              </button>
            </div>
            <button
              type="button"
              className="btn btn-primary btn-huge"
              disabled={busy}
              data-testid="liberar-mesa"
              onClick={() => act("release", `Mesa ${selected.number} livre. Ninguem na fila.`)}
            >
              {busy ? "Liberando..." : "Liberar mesa"}
            </button>
            <div className="btn-row">
              <button
                type="button"
                className="btn"
                disabled={busy}
                onClick={() => act("cleaning", `Mesa ${selected.number} em limpeza.`)}
              >
                Marcar limpeza
              </button>
              <button
                type="button"
                className="btn"
                disabled={busy}
                data-testid="ocupar-mesa"
                onClick={() => act("occupy", `Mesa ${selected.number} ocupada.`)}
              >
                Sentar cliente
              </button>
              <button
                type="button"
                className="btn"
                disabled={busy}
                onClick={() => act("allocate", "Nenhum grupo compativel na fila.")}
              >
                Chamar proximo
              </button>
            </div>
          </>
        ) : (
          <p className="muted">Selecione uma mesa para agir.</p>
        )}
      </div>

      <p className="muted" style={{ marginTop: 16 }}>
        Atualizacao automatica a cada {POLL_MS / 1000} segundos.{" "}
        <button
          type="button"
          className="btn"
          onClick={() => {
            void api.post("/auth/logout").then(() => router.push("/login?next=/staff"));
          }}
        >
          Sair
        </button>
      </p>
    </section>
  );
}
