import type { Table } from '@/lib/api';
import clsx from 'clsx';

const STATUS_CONFIG = {
  AVAILABLE: { label: 'Disponível', emoji: '🟢', bg: 'bg-green-100', border: 'border-green-400', text: 'text-green-800' },
  RESERVED:  { label: 'Reservada',  emoji: '🔵', bg: 'bg-blue-100',  border: 'border-blue-400',  text: 'text-blue-800'  },
  OCCUPIED:  { label: 'Ocupada',    emoji: '🔴', bg: 'bg-red-100',   border: 'border-red-400',   text: 'text-red-800'   },
  CLEANING:  { label: 'Limpeza',    emoji: '🟡', bg: 'bg-yellow-100',border: 'border-yellow-400',text: 'text-yellow-800'},
};

interface TableCardProps {
  table: Table;
  onRelease?: (id: string) => void;
  onOccupy?: (id: string) => void;
  onCleaning?: (id: string) => void;
  isStaff?: boolean;
}

export default function TableCard({ table, onRelease, onOccupy, onCleaning, isStaff }: TableCardProps) {
  const cfg = STATUS_CONFIG[table.status];
  return (
    <div
      data-testid={`table-card-${table.id}`}
      className={clsx(
        'rounded-xl border-2 p-4 shadow-sm transition-all hover:shadow-md',
        cfg.bg, cfg.border
      )}
    >
      <div className="flex items-center justify-between">
        <span className="text-2xl">{cfg.emoji}</span>
        <span className={clsx('rounded-full px-2 py-0.5 text-xs font-semibold', cfg.text)}>
          {cfg.label}
        </span>
      </div>
      <h3 className="mt-2 text-lg font-bold text-gray-800">Mesa #{table.number}</h3>
      <p className="text-sm text-gray-500">Capacidade: {table.capacity} pessoas</p>

      {isStaff && (
        <div className="mt-3 space-y-1">
          {table.status === 'OCCUPIED' && (
            <button
              data-testid={`release-btn-${table.id}`}
              onClick={() => onRelease?.(table.id)}
              className="w-full rounded-lg bg-red-600 py-2 text-sm font-bold text-white hover:bg-red-700"
            >
              🧹 LIBERAR MESA
            </button>
          )}
          {table.status === 'CLEANING' && (
            <button
              onClick={() => onCleaning?.(table.id)}
              className="w-full rounded-lg bg-yellow-500 py-2 text-sm font-bold text-white hover:bg-yellow-600"
            >
              ✅ Limpeza Concluída
            </button>
          )}
          {table.status === 'RESERVED' && (
            <button
              onClick={() => onOccupy?.(table.id)}
              className="w-full rounded-lg bg-blue-600 py-2 text-sm font-bold text-white hover:bg-blue-700"
            >
              👥 Sentar Cliente
            </button>
          )}
        </div>
      )}
    </div>
  );
}
