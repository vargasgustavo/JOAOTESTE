export type TableStatus = "AVAILABLE" | "OCCUPIED" | "CLEANING" | "RESERVED";
export type QueueStatus = "WAITING" | "CALLED" | "SEATED" | "CANCELLED" | "EXPIRED";
export type Role = "CUSTOMER" | "RESTAURANT_ADMIN" | "STAFF";

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: Role;
  restaurant_id: string | null;
}

export interface Table {
  id: string;
  number: string;
  capacity: number;
  pos_x: number;
  pos_y: number;
  status: TableStatus;
  restaurant_id: string;
}

export interface Allocation {
  queue_entry_id: string;
  customer_name: string;
  party_size: number;
  table_id: string;
  table_number: string;
}

export interface TableAction {
  table: Table;
  allocation: Allocation | null;
}

export interface QueueEntry {
  id: string;
  customer_name: string;
  customer_phone: string;
  party_size: number;
  status: QueueStatus;
  position: number | null;
  estimated_wait_minutes: number | null;
  joined_at: string;
  called_at: string | null;
  seated_at: string | null;
  cancelled_at: string | null;
  assigned_table_id: string | null;
  assigned_table_number: string | null;
}

export interface QueueTicket {
  id: string;
  customer_name: string;
  party_size: number;
  status: QueueStatus;
  position: number | null;
  estimated_wait_minutes: number | null;
  joined_at: string;
  called_at: string | null;
  restaurant_name: string;
  assigned_table_number: string | null;
  allocation?: Allocation | null;
  reallocation?: Allocation | null;
}

export interface RestaurantPublic {
  id: string;
  name: string;
  address: string;
  opening_hours: Record<string, unknown>;
  waiting_groups: number;
  estimated_wait_minutes: number;
}

export interface Restaurant extends RestaurantPublic {
  phone: string;
  is_active: boolean;
}

export interface DashboardMetrics {
  restaurant_id: string;
  total_tables: number;
  occupied_tables: number;
  cleaning_tables: number;
  available_tables: number;
  reserved_tables: number;
  waiting_customers: number;
  called_customers: number;
  average_wait_minutes: number;
  average_turnover_minutes: number;
}

export interface Paginated<T> {
  items: T[];
}
