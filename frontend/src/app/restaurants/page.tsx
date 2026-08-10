'use client';
import { useEffect, useState } from 'react';
import { restaurantApi, type Restaurant } from '@/lib/api';
import { useRouter } from 'next/navigation';

export default function RestaurantsPage() {
  const [restaurants, setRestaurants] = useState<Restaurant[]>([]);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    restaurantApi.list().then(d => {
      setRestaurants(d.restaurants);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  if (loading) return <div className="flex min-h-screen items-center justify-center">Carregando...</div>;

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <h1 className="mb-6 text-3xl font-bold text-gray-800">🍽️ Restaurantes</h1>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {restaurants.map(r => (
          <div key={r.id} className="rounded-2xl bg-white p-6 shadow hover:shadow-md cursor-pointer"
            onClick={() => router.push(`/restaurants/${r.id}`)}>
            <h2 className="text-xl font-bold text-gray-800">{r.name}</h2>
            <p className="text-sm text-gray-500">{r.address}</p>
            <p className="mt-1 text-sm text-gray-500">📞 {r.phone}</p>
            <span className={`mt-3 inline-block rounded-full px-3 py-1 text-xs font-bold ${r.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
              {r.is_active ? 'Aberto' : 'Fechado'}
            </span>
          </div>
        ))}
        {restaurants.length === 0 && (
          <p className="text-gray-400">Nenhum restaurante disponível.</p>
        )}
      </div>
    </div>
  );
}
