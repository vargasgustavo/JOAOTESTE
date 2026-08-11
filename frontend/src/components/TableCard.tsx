"use client";

import { TABLE_LABEL } from "@/lib/format";
import type { Table } from "@/lib/types";

interface Props {
  table: Table;
  selected?: boolean;
  onSelect?: (table: Table) => void;
}

/** Vermelho = ocupada, amarelo = limpeza/reservada, verde = livre. */
export function TableCard({ table, selected, onSelect }: Props) {
  const interactive = Boolean(onSelect);
  return (
    <button
      type="button"
      className={`table-card status-${table.status.toLowerCase()}${selected ? " selected" : ""}`}
      onClick={() => onSelect?.(table)}
      disabled={!interactive}
      data-testid={`table-${table.number}`}
      data-status={table.status}
      aria-pressed={selected}
    >
      <span className="table-number">{table.number}</span>
      <span className="table-capacity">{table.capacity} lugares</span>
      <span className="table-status">{TABLE_LABEL[table.status]}</span>
    </button>
  );
}

export function TableLegend() {
  return (
    <ul className="legend">
      <li>
        <span className="dot status-available" /> Livre
      </li>
      <li>
        <span className="dot status-cleaning" /> Limpeza
      </li>
      <li>
        <span className="dot status-reserved" /> Reservada
      </li>
      <li>
        <span className="dot status-occupied" /> Ocupada
      </li>
    </ul>
  );
}
