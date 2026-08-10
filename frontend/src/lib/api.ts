const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000/api';

type HttpMethod = 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';

function getCsrfToken(): string {
  if (typeof document === 'undefined') return '';
  const match = document.cookie.match(/csrf_token=([^;]+)/);
  return match ? match[1] : '';
}

async function request<T>(
  path: string,
  method: HttpMethod = 'GET',
  body?: unknown
): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  if (['POST', 'PUT', 'DELETE', 'PATCH'].includes(method)) {
    const csrf = getCsrfToken();
    if (csrf) headers['X-CSRF-Token'] = csrf;
  }

  const res = await fetch(`${API_URL}${path}`, {
    method,
    headers,
    credentials: 'include',
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ error: 'Request failed' }));
    throw new Error(error.error || 'Request failed');
  }

  return res.json();
}

export const api = {
  get: <T>(path: string) => request<T>(path, 'GET'),
  post: <T>(path: string, body?: unknown) => request<T>(path, 'POST', body),
  put: <T>(path: string, body?: unknown) => request<T>(path, 'PUT', body),
  delete: <T>(path: string) => request<T>(path, 'DELETE'),
};

// Auth
export const authApi = {
  login: (phone: string, password: string) =>
    api.post<{ user: User; message: string }>('/auth/login', { phone, password }),
  register: (data: RegisterData) =>
    api.post<{ user: User; message: string }>('/auth/register', data),
  logout: () => api.post('/auth/logout'),
  me: () => api.get<{ user: User }>('/auth/me'),
  refresh: () => api.post('/auth/refresh'),
};

// Restaurants
export const restaurantApi = {
  list: () => api.get<{ restaurants: Restaurant[] }>('/restaurants/'),
  get: (id: string) => api.get<{ restaurant: Restaurant }>(`/restaurants/${id}`),
  create: (data: Partial<Restaurant>) =>
    api.post<{ restaurant: Restaurant }>('/restaurants/', data),
  update: (id: string, data: Partial<Restaurant>) =>
    api.put<{ restaurant: Restaurant }>(`/restaurants/${id}`, data),
};

// Tables
export const tableApi = {
  list: (restaurantId: string) =>
    api.get<{ tables: Table[] }>(`/restaurants/${restaurantId}/tables`),
  create: (restaurantId: string, data: Partial<Table>) =>
    api.post<{ table: Table }>(`/restaurants/${restaurantId}/tables`, data),
  release: (tableId: string) => api.post<{ table: Table }>(`/tables/${tableId}/release`),
  cleaning: (tableId: string) => api.post<{ table: Table }>(`/tables/${tableId}/cleaning`),
  occupy: (tableId: string) => api.post<{ table: Table }>(`/tables/${tableId}/occupy`),
  update: (tableId: string, data: Partial<Table>) =>
    api.put<{ table: Table }>(`/tables/${tableId}`, data),
};

// Queue
export const queueApi = {
  list: (restaurantId: string, status?: string) =>
    api.get<{ queue: QueueEntry[] }>(
      `/restaurants/${restaurantId}/queue${status ? `?status=${status}` : ''}`
    ),
  join: (restaurantId: string, data: JoinQueueData) =>
    api.post<{ queue_entry: QueueEntry }>(`/restaurants/${restaurantId}/queue`, data),
  get: (entryId: string) => api.get<{ queue_entry: QueueEntry }>(`/queue/${entryId}`),
  cancel: (entryId: string) =>
    api.post<{ queue_entry: QueueEntry }>(`/queue/${entryId}/cancel`),
};

// Dashboard
export const dashboardApi = {
  get: (restaurantId: string) =>
    api.get<{ dashboard: DashboardData }>(`/restaurants/${restaurantId}/dashboard`),
};

// Types
export interface User {
  id: string;
  name: string;
  phone: string;
  email?: string;
  role: 'CUSTOMER' | 'RESTAURANT_ADMIN' | 'STAFF';
  restaurant_id?: string;
  created_at: string;
}

export interface RegisterData {
  name: string;
  phone: string;
  password: string;
  email?: string;
  role?: string;
}

export interface Restaurant {
  id: string;
  name: string;
  address: string;
  phone: string;
  opening_hours?: Record<string, string>;
  is_active: boolean;
  created_at: string;
}

export interface Table {
  id: string;
  restaurant_id: string;
  number: number;
  capacity: number;
  pos_x?: number;
  pos_y?: number;
  status: 'AVAILABLE' | 'RESERVED' | 'OCCUPIED' | 'CLEANING';
  created_at: string;
  updated_at: string;
}

export interface QueueEntry {
  id: string;
  restaurant_id: string;
  customer_id?: string;
  customer_name: string;
  customer_phone: string;
  party_size: number;
  status: 'WAITING' | 'CALLED' | 'SEATED' | 'CANCELLED' | 'EXPIRED';
  position?: number;
  assigned_table_id?: string;
  joined_at: string;
  called_at?: string;
  seated_at?: string;
  cancelled_at?: string;
  estimated_wait_minutes?: number;
}

export interface JoinQueueData {
  customer_name: string;
  customer_phone: string;
  party_size: number;
}

export interface DashboardData {
  restaurant_id: string;
  restaurant_name: string;
  total_tables: number;
  occupied_tables: number;
  cleaning_tables: number;
  available_tables: number;
  reserved_tables: number;
  queue_count: number;
  avg_wait_minutes: number;
}
