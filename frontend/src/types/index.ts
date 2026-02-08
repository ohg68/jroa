export interface Product {
  id: number;
  catalog_id: number;
  name: string;
  default_code: string | null;
  list_price: number | null;
  categ_id: string | null;
  description_sale: string | null;
  brand: string | null;
  unit: string | null;
  needs_review: boolean;
  review_reason: string | null;
  page_number: number | null;
  created_at: string;
}

export interface Catalog {
  id: number;
  filename: string;
  status: 'pending' | 'processing' | 'processed' | 'error';
  total_pages: number;
  file_size: number;
  optimized_size: number | null;
  error_message: string | null;
  total_products: number;
  valid_products: number;
  review_products: number;
  created_at: string;
  processed_at: string | null;
}

export interface Dashboard {
  total_catalogs: number;
  processed_catalogs: number;
  pending_catalogs: number;
  error_catalogs: number;
  total_products: number;
  valid_products: number;
  review_products: number;
}
