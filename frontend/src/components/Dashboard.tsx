import type { DashboardData } from '@/lib/api';

interface DashboardProps {
  data: DashboardData;
}

export default function Dashboard({ data }: DashboardProps) {
  const cards = [
    { label: 'Total de Mesas', value: data.total_tables, color: 'bg-gray-100', text: 'text-gray-800' },
    { label: '🔴 Ocupadas',    value: data.occupied_tables,  color: 'bg-red-100',    text: 'text-red-800'    },
    { label: '🟡 Em Limpeza', value: data.cleaning_tables,  color: 'bg-yellow-100', text: 'text-yellow-800' },
    { label: '🟢 Disponíveis',value: data.available_tables, color: 'bg-green-100',  text: 'text-green-800'  },
    { label: '🔵 Reservadas', value: data.reserved_tables,  color: 'bg-blue-100',   text: 'text-blue-800'   },
    { label: '👥 Na Fila',    value: data.queue_count,      color: 'bg-purple-100', text: 'text-purple-800' },
  ];

  return (
    <div>
      <div className="mb-2 text-sm text-gray-500">
        ⏱ Tempo médio de espera: ~{data.avg_wait_minutes} min/turno
      </div>
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
        {cards.map(c => (
          <div key={c.label} className={`rounded-xl p-4 ${c.color}`}>
            <p className="text-sm text-gray-600">{c.label}</p>
            <p className={`text-3xl font-bold ${c.text}`}>{c.value}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
