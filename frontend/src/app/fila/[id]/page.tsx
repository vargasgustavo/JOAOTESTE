"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";

import { useToast } from "@/components/Toast";
import { api } from "@/lib/api";
import { QUEUE_LABEL, minutesLabel, timeLabel } from "@/lib/format";
import { usePolling } from "@/lib/hooks";
import type { QueueTicket } from "@/lib/types";

const POLL_MS = 7000;

export default function TicketPage() {
  const params = useParams<{ id: string }>();
  const toast = useToast();
  const [busy, setBusy] = useState(false);

  const { data, error, refresh } = usePolling<QueueTicket>(
    () => api.get<QueueTicket>(`/queue/${params.id}`),
    POLL_MS,
  );

  async function cancel() {
    setBusy(true);
    try {
      await api.post(`/queue/${params.id}/cancel`);
      toast.show("Voce saiu da fila.", "info");
      await refresh();
    } catch (err) {
      toast.show(err instanceof Error ? err.message : "Falha ao cancelar.", "error");
    } finally {
      setBusy(false);
    }
  }

  if (error) return <p className="error">{error}</p>;
  if (!data) return <p className="muted">Carregando...</p>;

  const called = data.status === "CALLED";
  const open = data.status === "WAITING" || called;

  return (
    <section>
      <h1>{data.restaurant_name}</h1>
      <p className="subtitle">
        Ola, {data.customer_name}! Grupo de {data.party_size} pessoa(s).
      </p>

      <div className={`card${called ? " ticket-highlight" : ""}`} data-testid="ticket-status">
        <div className="row">
          <span className={`badge${called ? " badge-called" : ""}`}>
            {QUEUE_LABEL[data.status]}
          </span>
          <span className="muted">Entrou as {timeLabel(data.joined_at)}</span>
        </div>

        {called ? (
          <>
            <h2 data-testid="called-title">Sua mesa esta pronta!</h2>
            <p>
              Dirija-se a recepcao
              {data.assigned_table_number ? ` - mesa ${data.assigned_table_number}` : ""}.
            </p>
          </>
        ) : null}

        {data.status === "WAITING" ? (
          <>
            <h2 data-testid="ticket-position">Sua posicao: #{data.position ?? "-"}</h2>
            <p data-testid="ticket-estimate">
              Tempo estimado: {minutesLabel(data.estimated_wait_minutes)}
            </p>
          </>
        ) : null}

        {data.status === "SEATED" ? <p>Bom apetite!</p> : null}
        {data.status === "CANCELLED" ? <p>Esta entrada foi cancelada.</p> : null}
        {data.status === "EXPIRED" ? <p>Esta entrada expirou.</p> : null}
      </div>

      <div className="btn-row">
        {open ? (
          <button type="button" className="btn btn-danger" onClick={cancel} disabled={busy}>
            {busy ? "Cancelando..." : "Sair da fila"}
          </button>
        ) : null}
        <Link className="btn" href="/">
          Ver restaurantes
        </Link>
      </div>

      <p className="muted" style={{ marginTop: 16 }}>
        Esta pagina atualiza sozinha. Guarde o link para acompanhar.
      </p>
    </section>
  );
}
