'use client';
import { useEffect, useState } from 'react';
import { restaurantApi, queueApi, type Restaurant, type QueueEntry, type JoinQueueData } from '@/lib/api';
import QueueList from '@/components/QueueList';
import { useRouter } from 'next/navigation';

interface Props { params: { id: string } }

export default function RestaurantDetailPage({ params }: Props) {
  const [restaurant, setRestaurant] = useState<Restaurant | null>(null);
  const [queue, setQueue] = useState<QueueEntry[]>([]);
  const [form, setForm] = useState<JoinQueueData>({ customer_name: '', customer_phone: '', party_size: 2 });
  const [myEntry, setMyEntry] = useState<QueueEntry | null>(null);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const router = useRouter();

  useEffect(() => {
    restaurantApi.get(params.id).then(d => setRestaurant(d.restaurant));
    const refresh = () => queueApi.list(params.id, 'WAITING').then(d => setQueue(d.queue)).catch(() => {});
    refresh();
    const iv = setInterval(refresh, 7000);
    return () => clearInterval(iv);
  }, [params.id]);

  async function handleJoin(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    try {
      const { queue_entry } = await queueApi.join(params.id, form);
      setMyEntry(queue_entry);
      setSuccess(`Você está na posição #${queue_entry.position ?? 1}! Tempo estimado: ~${queue_entry.estimated_wait_minutes ?? 15} min`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Erro ao entrar na fila');
    }
  }

  if (!restaurant) return <div className="flex min-h-screen items-center justify-center">Carregando...</div>;

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <button onClick={() => router.back()} className="mb-4 text-blue-600 hover:underline">← Voltar</button>
      <h1 className="mb-1 text-3xl font-bold text-gray-800">{restaurant.name}</h1>
      <p className="mb-6 text-gray-500">{restaurant.address}</p>

      <div className="mb-6 grid gap-4 sm:grid-cols-2">
        <div className="rounded-xl bg-white p-4 shadow">
          <p className="text-sm text-gray-500">🧍 Na fila agora</p>
          <p className="text-3xl font-bold text-gray-800">{queue.length}</p>
        </div>
      </div>

      {myEntry ? (
        <div className={`mb-6 rounded-xl p-6 shadow ${myEntry.status === 'CALLED' ? 'bg-blue-100 border-2 border-blue-400 animate-pulse' : 'bg-white'}`}>
          <h2 className="text-xl font-bold">
            {myEntry.status === 'CALLED' ? '📣 Sua mesa está pronta!' : `Sua posição: #${myEntry.position ?? '—'}`}
          </h2>
          <p className="text-gray-600">
            {myEntry.status === 'WAITING' && `Tempo estimado: ~${myEntry.estimated_wait_minutes ?? 15} min`}
            {myEntry.status === 'CALLED' && 'Dirija-se à recepção!'}
          </p>
          <button onClick={() => queueApi.cancel(myEntry.id).then(() => setMyEntry(null))}
            className="mt-3 text-sm text-red-500 hover:underline">Cancelar</button>
        </div>
      ) : (
        <div className="mb-6 rounded-xl bg-white p-6 shadow">
          <h2 className="mb-4 text-xl font-semibold text-gray-800">Entrar na Fila</h2>
          {success && <p className="mb-3 text-green-600 font-semibold">{success}</p>}
          {error && <p className="mb-3 text-red-500">{error}</p>}
          <form onSubmit={handleJoin} className="space-y-3">
            <input type="text" placeholder="Seu nome" required value={form.customer_name}
              onChange={e => setForm({ ...form, customer_name: e.target.value })}
              className="w-full rounded-lg border border-gray-300 px-3 py-2" />
            <input type="tel" placeholder="Seu telefone" required value={form.customer_phone}
              onChange={e => setForm({ ...form, customer_phone: e.target.value })}
              className="w-full rounded-lg border border-gray-300 px-3 py-2" />
            <div className="flex items-center gap-3">
              <label className="text-sm text-gray-700">Pessoas:</label>
              <input type="number" min={1} max={20} value={form.party_size}
                onChange={e => setForm({ ...form, party_size: parseInt(e.target.value) })}
                className="w-20 rounded-lg border border-gray-300 px-3 py-2" />
            </div>
            <button type="submit"
              className="w-full rounded-lg bg-green-600 py-2 font-bold text-white hover:bg-green-700">
              ✅ Entrar na Fila
            </button>
          </form>
        </div>
      )}

      <h2 className="mb-3 text-xl font-semibold text-gray-700">Fila Atual</h2>
      <QueueList entries={queue} />
    </div>
  );
}
