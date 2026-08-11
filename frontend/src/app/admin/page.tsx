"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { TableCard, TableLegend } from "@/components/TableCard";
import { useToast } from "@/components/Toast";
import { api } from "@/lib/api";
import { QUEUE_LABEL, minutesLabel, timeLabel } from "@/lib/format";
import { usePolling, useSession } from "@/lib/hooks";
import type { DashboardMetrics, Paginated, QueueEntry, Table } from "@/lib/types";

const POLL_MS = 8000;

interface AdminData {
  metrics: DashboardMetrics;
  tables: Table[];
  queue: QueueEntry[];
}

export default function AdminPage() {
  const { user, loading: loadingUser } = useSession();
  const toast = useToast();
  const restaurantId = user?.restaurant_id ?? null;

  const [number, setNumber] = useState("");
  const [capacity, setCapacity] = useState(4);
  const [busy, setBusy] = useState(false);

  const { data, error, refresh } = usePolling<AdminData | null>(async () => {
    if (!restaurantId) return null;
    const [metrics, tables, queue] = await Promise.all([
      api.get<DashboardMetrics>(`/restaurants/${restaurantId}/dashboard`),
      api.get<Paginated<Table>>(`/restaurants/${restaurantId}/tables`),
      api.get<Paginated<QueueEntry>>(`/restaurants/${restaurantId}/queue`),
    ]);
    return { metrics, tables: tables.items, queue: queue.items };
  }, POLL_MS);

  const tables = useMemo(
    () =>
      [...(data?.tables ?? [])].sort((a, b) =>
        a.number.localeCompare(b.number, "pt-BR", { numeric: true }),
      ),
    [data],
  );

  async function createTable(event: React.FormEvent) {
    event.preventDefault();
    if (!restaurantId) return;
    setBusy(true);
    try {
      await api.post(`/restaurants/${restaurantId}/tables`, {
        number,
        capacity,
        pos_x: 0,
        pos_y: 0,
      });
      toast.show(`Mesa ${number} criada.`, "success");
      setNumber("");
      await refresh();
    } catch (err) {
      toast.show(err instanceof Error ? err.message : "Falha ao criar mesa.", "error");
    } finally {
      setBusy(false);
    }
  }

  async function updateCapacity(table: Table, nextCapacity: number) {
    if (nextCapacity === table.capacity || Number.isNaN(nextCapacity)) return;
    try {
      await api.put(`/tables/${table.id}`, { capacity: nextCapacity });
      toast.show(`Mesa ${table.number} agora tem ${nextCapacity} lugares.`, "success");
      await refresh();
    } catch (err) {
      toast.show(err instanceof Error ? err.message : "Falha ao atualizar mesa.", "error");
    }
  }

  if (loadingUser) return <p className="muted">Carregando...</p>;

  if (!user) {
    return (
      <div className="card">
        <h1>Painel administrativo</h1>
        <p className="muted">Entre com sua conta de administrador.</p>
        <Link className="btn btn-primary" href="/login?next=/admin">
          Fazer login
        </Link>
      </div>
    );
  }

  if (user.role !== "RESTAURANT_ADMIN") {
    return (
      <div className="card">
        <h1>Acesso restrito</h1>
        <p className="muted">Somente administradores do restaurante acessam este painel.</p>
        <Link className="btn" href="/staff">
          Ir para o salao
        </Link>
      </div>
    );
  }

  const metrics = data?.metrics;

  return (
    <section>
      <h1>Painel</h1>
      <p className="subtitle">Metricas, mapa do salao e fila em tempo quase real.</p>
      {error ? <p className="error">{error}</p> : null}

      <div className="metrics" data-testid="dashboard-metrics">
        <div className="metric">
          <strong>{metrics?.total_tables ?? "-"}</strong>
          <span>mesas no total</span>
        </div>
        <div className="metric">
          <strong>{metrics?.occupied_tables ?? "-"}</strong>
          <span>ocupadas</span>
        </div>
        <div className="metric">
          <strong>{metrics?.cleaning_tables ?? "-"}</strong>
          <span>em limpeza</span>
        </div>
        <div className="metric">
          <strong>{metrics?.available_tables ?? "-"}</strong>
          <span>disponiveis</span>
        </div>
        <div className="metric">
          <strong>{metrics?.waiting_customers ?? "-"}</strong>
          <span>clientes na fila</span>
        </div>
        <div className="metric">
          <strong>{metrics ? minutesLabel(metrics.average_wait_minutes) : "-"}</strong>
          <span>espera media</span>
        </div>
      </div>

      <h2>Mapa do salao</h2>
      <div className="grid">
        {tables.map((table) => (
          <TableCard key={table.id} table={table} />
        ))}
      </div>
      <TableLegend />

      <h2>Fila</h2>
      <div className="card">
        <table className="data">
          <thead>
            <tr>
              <th>#</th>
              <th>Cliente</th>
              <th>Pessoas</th>
              <th>Status</th>
              <th>Entrou</th>
              <th>Mesa</th>
            </tr>
          </thead>
          <tbody>
            {(data?.queue ?? []).map((entry) => (
              <tr key={entry.id}>
                <td>{entry.position ?? "-"}</td>
                <td>{entry.customer_name}</td>
                <td>{entry.party_size}</td>
                <td>{QUEUE_LABEL[entry.status]}</td>
                <td>{timeLabel(entry.joined_at)}</td>
                <td>{entry.assigned_table_number ?? "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {(data?.queue ?? []).length === 0 ? <p className="muted">Fila vazia.</p> : null}
      </div>

      <h2>Mesas</h2>
      <form className="form card" onSubmit={createTable}>
        <label>
          Numero da mesa
          <input
            required
            maxLength={16}
            value={number}
            onChange={(event) => setNumber(event.target.value)}
          />
        </label>
        <label>
          Capacidade
          <input
            type="number"
            min={1}
            max={50}
            required
            value={capacity}
            onChange={(event) => setCapacity(Number(event.target.value))}
          />
        </label>
        <button type="submit" className="btn btn-primary" disabled={busy}>
          {busy ? "Criando..." : "Adicionar mesa"}
        </button>
      </form>

      <div className="card">
        <table className="data">
          <thead>
            <tr>
              <th>Mesa</th>
              <th>Capacidade</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {tables.map((table) => (
              <tr key={table.id}>
                <td>{table.number}</td>
                <td>
                  <input
                    type="number"
                    min={1}
                    max={50}
                    defaultValue={table.capacity}
                    style={{ width: 80 }}
                    onBlur={(event) => updateCapacity(table, Number(event.target.value))}
                  />
                </td>
                <td>{table.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
