"use client";

import { useParams, useRouter } from "next/navigation";
import { useState } from "react";

import { useToast } from "@/components/Toast";
import { api } from "@/lib/api";
import { minutesLabel } from "@/lib/format";
import { usePolling } from "@/lib/hooks";
import type { QueueTicket, RestaurantPublic } from "@/lib/types";

export default function RestaurantPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const toast = useToast();
  const restaurantId = params.id;

  const { data, error } = usePolling<RestaurantPublic>(
    () => api.get<RestaurantPublic>(`/restaurants/${restaurantId}`),
    10000,
  );

  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [partySize, setPartySize] = useState(2);
  const [busy, setBusy] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  async function join(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setFormError(null);
    try {
      const ticket = await api.post<QueueTicket>(`/restaurants/${restaurantId}/queue`, {
        customer_name: name,
        customer_phone: phone,
        party_size: partySize,
      });
      toast.show("Voce entrou na fila!", "success");
      router.push(`/fila/${ticket.id}`);
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Nao foi possivel entrar na fila.");
    } finally {
      setBusy(false);
    }
  }

  if (error) return <p className="error">{error}</p>;
  if (!data) return <p className="muted">Carregando...</p>;

  return (
    <section>
      <h1>{data.name}</h1>
      <p className="subtitle">{data.address}</p>

      <div className="metrics">
        <div className="metric">
          <strong data-testid="waiting-groups">{data.waiting_groups}</strong>
          <span>grupos aguardando</span>
        </div>
        <div className="metric">
          <strong>{minutesLabel(data.estimated_wait_minutes)}</strong>
          <span>espera estimada</span>
        </div>
      </div>

      <h2>Entrar na fila</h2>
      <form className="form card" onSubmit={join}>
        <label>
          Seu nome
          <input
            name="customer_name"
            required
            minLength={2}
            maxLength={120}
            value={name}
            onChange={(event) => setName(event.target.value)}
          />
        </label>
        <label>
          Telefone (com DDD)
          <input
            name="customer_phone"
            required
            inputMode="tel"
            placeholder="+5511999998888"
            value={phone}
            onChange={(event) => setPhone(event.target.value)}
          />
        </label>
        <label>
          Numero de pessoas
          <input
            name="party_size"
            type="number"
            min={1}
            max={20}
            required
            value={partySize}
            onChange={(event) => setPartySize(Number(event.target.value))}
          />
        </label>
        {formError ? <p className="error">{formError}</p> : null}
        <button type="submit" className="btn btn-primary" disabled={busy} data-testid="entrar-fila">
          {busy ? "Entrando..." : "Entrar na fila"}
        </button>
        <p className="muted">
          Usamos seu telefone apenas para avisar quando a mesa estiver pronta.
        </p>
      </form>
    </section>
  );
}
