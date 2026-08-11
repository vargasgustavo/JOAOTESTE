"use client";

import Link from "next/link";

import { minutesLabel } from "@/lib/format";
import { api } from "@/lib/api";
import { usePolling } from "@/lib/hooks";
import type { Paginated, RestaurantPublic } from "@/lib/types";

export default function HomePage() {
  const { data, error, loading } = usePolling<Paginated<RestaurantPublic>>(
    () => api.get<Paginated<RestaurantPublic>>("/restaurants"),
    15000,
  );

  const restaurants = data?.items ?? [];

  return (
    <section>
      <h1>Restaurantes</h1>
      <p className="subtitle">Escolha um restaurante e entre na fila pelo celular.</p>

      {error ? <p className="error">{error}</p> : null}
      {loading ? <p className="muted">Carregando...</p> : null}

      <ul className="list" data-testid="restaurant-list">
        {restaurants.map((restaurant) => (
          <li key={restaurant.id} className="card">
            <div className="row">
              <div>
                <strong>{restaurant.name}</strong>
                <p className="muted" style={{ margin: "4px 0 0" }}>
                  {restaurant.address}
                </p>
              </div>
              <div style={{ textAlign: "right" }}>
                <p style={{ margin: 0 }}>
                  {restaurant.waiting_groups} grupo(s) na fila
                </p>
                <p className="muted" style={{ margin: "4px 0 0" }}>
                  Espera: {minutesLabel(restaurant.estimated_wait_minutes)}
                </p>
              </div>
            </div>
            <div className="btn-row">
              <Link className="btn btn-primary" href={`/restaurantes/${restaurant.id}`}>
                Ver e entrar na fila
              </Link>
            </div>
          </li>
        ))}
      </ul>

      {!loading && restaurants.length === 0 ? (
        <p className="muted">Nenhum restaurante disponivel no momento.</p>
      ) : null}
    </section>
  );
}
