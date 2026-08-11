import type { QueueStatus, TableStatus } from "./types";

export const TABLE_LABEL: Record<TableStatus, string> = {
  AVAILABLE: "Livre",
  OCCUPIED: "Ocupada",
  CLEANING: "Limpeza",
  RESERVED: "Reservada",
};

export const QUEUE_LABEL: Record<QueueStatus, string> = {
  WAITING: "Aguardando",
  CALLED: "Chamado",
  SEATED: "Sentado",
  CANCELLED: "Cancelado",
  EXPIRED: "Expirado",
};

export function minutesLabel(minutes: number | null): string {
  if (minutes === null || minutes <= 0) return "Sem espera";
  return `${minutes} ${minutes === 1 ? "minuto" : "minutos"}`;
}

export function timeLabel(iso: string | null): string {
  if (!iso) return "-";
  const value = new Date(iso);
  if (Number.isNaN(value.getTime())) return "-";
  return value.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
}
