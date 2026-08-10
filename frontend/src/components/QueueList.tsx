import type { QueueEntry } from '@/lib/api';
import clsx from 'clsx';

const STATUS_LABELS = {
  WAITING: { label: 'Aguardando', color: 'text-gray-700', bg: 'bg-gray-100' },
  CALLED:  { label: '📣 Chamado!', color: 'text-blue-700', bg: 'bg-blue-100' },
  SEATED:  { label: 'Sentado',    color: 'text-green-700', bg: 'bg-green-100' },
  CANCELLED:{ label: 'Cancelado', color: 'text-red-700',   bg: 'bg-red-100'   },
  EXPIRED: { label: 'Expirado',   color: 'text-gray-400',  bg: 'bg-gray-50'   },
};

interface QueueListProps {
  entries: QueueEntry[];
  onCancel?: (id: string) => void;
  isStaff?: boolean;
}

export default function QueueList({ entries, onCancel, isStaff }: QueueListProps) {
  if (entries.length === 0) {
    return <p className="text-center text-gray-400 py-8">Fila vazia</p>;
  }

  return (
    <div className="space-y-3">
      {entries.map((entry, idx) => {
        const cfg = STATUS_LABELS[entry.status];
        const isHighlighted = entry.status === 'CALLED';
        return (
          <div
            key={entry.id}
            data-testid={`queue-entry-${entry.id}`}
            className={clsx(
              'rounded-xl border p-4 transition-all',
              cfg.bg,
              isHighlighted ? 'border-blue-400 ring-2 ring-blue-300 shadow-lg animate-pulse' : 'border-gray-200'
            )}
          >
            <div className="flex items-center justify-between">
              <div>
                {entry.status === 'WAITING' && (
                  <span className="text-2xl font-bold text-gray-500">#{idx + 1}</span>
                )}
                <p className="font-semibold text-gray-800">{entry.customer_name}</p>
                <p className="text-sm text-gray-500">
                  👥 {entry.party_size} pessoa{entry.party_size > 1 ? 's' : ''}
                  {entry.estimated_wait_minutes != null && entry.status === 'WAITING' && (
                    <> · ⏱ ~{entry.estimated_wait_minutes} min</>
                  )}
                </p>
              </div>
              <div className="text-right">
                <span className={clsx('rounded-full px-3 py-1 text-xs font-bold', cfg.color, cfg.bg)}>
                  {cfg.label}
                </span>
                {(isStaff || entry.status === 'WAITING') && onCancel && (
                  <button
                    onClick={() => onCancel(entry.id)}
                    className="mt-2 block text-xs text-red-500 hover:underline"
                  >
                    Cancelar
                  </button>
                )}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
