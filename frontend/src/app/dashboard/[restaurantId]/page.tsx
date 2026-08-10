'use client';
import StaffView from '@/components/StaffView';

interface Props { params: { restaurantId: string } }

export default function DashboardPage({ params }: Props) {
  return <StaffView restaurantId={params.restaurantId} />;
}
