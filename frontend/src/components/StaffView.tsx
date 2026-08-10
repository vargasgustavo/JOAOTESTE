'use client';
import { useEffect, useState, useCallback } from 'react';
import { tableApi, queueApi, dashboardApi, type Table, type QueueEntry, type DashboardData } from '@/lib/api';
import TableCard from '@/components/TableCard';
import QueueList from '@/components/QueueList';
import DashboardComp from '@/components/Dashboard';

interface StaffViewProps {
  restaurantId: string;
}

export default function StaffView({ restaurantId }: StaffViewProps) {
  const [tables, setTables] = useState<Table[]>([]);
  const [queue, setQueue] = useState<QueueEntry[]>([]);
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [toast, setToast] = useState('');

  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(''), 4000);
  };

  const refresh = useCallback(async () => {
    const [t, q, d] = await Promise.all([
      tableApi.list(restaurantId),
      queueApi.list(restaurantId),
      dashboardApi.get(restaurantId),
    ]);
    setTables(t.tables);
    setQueue(q.queue);
    setDashboard(d.dashboard);
  }, [restaurantId]);

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 7000);
    return () => clearInterval(interval);
  }, [refresh]);

  async function handleRelease(tableId: string) {
    await tableApi.release(tableId);
    showToast('Mesa liberada para limpeza!');
    await refresh();
  }

  async function handleCleaning(tableId: string) {
    await tableApi.cleaning(tableId);
    showToast('Mesa disponível! Verificando fila...');
    await refresh();
  }

  async function handleOccupy(tableId: string) {
    await tableApi.occupy(tableId);
    showToast('Mesa ocupada.');
    await refresh();
  }

  async function handleCancel(entryId: string) {
    await queueApi.cancel(entryId);
    showToast('Entrada cancelada.');
    await refresh();
  }

  return (
    <div className="min-h-screen bg-gray-50 p-4">
      {toast && (
        <div className="fixed top-4 right-4 z-50 rounded-xl bg-green-600 px-6 py-3 text-white shadow-lg">
          {toast}
        </div>
      )}

      <h1 className="mb-4 text-2xl font-bold text-gray-800">🍽️ Painel do Restaurante</h1>

      {dashboard && (
        <div className="mb-6">
          <DashboardComp data={dashboard} />
        </div>
      )}

      <h2 className="mb-3 text-xl font-semibold text-gray-700">Mesas</h2>
      <div className="mb-8 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
        {tables.map(table => (
          <TableCard
            key={table.id}
            table={table}
            isStaff
            onRelease={handleRelease}
            onOccupy={handleOccupy}
            onCleaning={handleCleaning}
          />
        ))}
      </div>

      <h2 className="mb-3 text-xl font-semibold text-gray-700">
        Fila ({queue.filter(e => e.status === 'WAITING' || e.status === 'CALLED').length})
      </h2>
      <QueueList
        entries={queue.filter(e => ['WAITING', 'CALLED'].includes(e.status))}
        onCancel={handleCancel}
        isStaff
      />
    </div>
  );
}
