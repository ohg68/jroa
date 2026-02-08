import type { Catalog, Dashboard, Product } from '../types';

const BASE_URL = '/api';

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${url}`, options);
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || 'Request failed');
  }
  return res.json();
}

// Dashboard
export const getDashboard = () => request<Dashboard>('/catalogs/dashboard');

// Catalogs
export const getCatalogs = (status?: string) => {
  const params = status ? `?status=${status}` : '';
  return request<Catalog[]>(`/catalogs/${params}`);
};

export const getCatalog = (id: number) => request<Catalog>(`/catalogs/${id}`);

export const uploadCatalog = async (file: File): Promise<Catalog> => {
  const formData = new FormData();
  formData.append('file', file);
  const res = await fetch(`${BASE_URL}/catalogs/upload`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || 'Upload failed');
  }
  return res.json();
};

export const reprocessCatalog = (id: number) =>
  request<{ message: string }>(`/catalogs/${id}/reprocess`, { method: 'POST' });

export const optimizeCatalog = (id: number) =>
  request<{ message: string; original_size: number; optimized_size: number }>(
    `/catalogs/${id}/optimize`,
    { method: 'POST' }
  );

export const deleteCatalog = (id: number) =>
  request<{ message: string }>(`/catalogs/${id}`, { method: 'DELETE' });

export const deleteAllCatalogs = () =>
  request<{ message: string }>('/catalogs/', { method: 'DELETE' });

// Products
export const getProducts = (params: {
  catalog_id?: number;
  needs_review?: boolean;
  missing_price?: boolean;
  search?: string;
  page?: number;
  per_page?: number;
}) => {
  const searchParams = new URLSearchParams();
  if (params.catalog_id !== undefined) searchParams.set('catalog_id', String(params.catalog_id));
  if (params.needs_review !== undefined) searchParams.set('needs_review', String(params.needs_review));
  if (params.missing_price) searchParams.set('missing_price', 'true');
  if (params.search) searchParams.set('search', params.search);
  if (params.page) searchParams.set('page', String(params.page));
  if (params.per_page) searchParams.set('per_page', String(params.per_page));

  const qs = searchParams.toString();
  return request<Product[]>(`/products/${qs ? `?${qs}` : ''}`);
};

export const updateProduct = (id: number, data: Partial<Product>) =>
  request<Product>(`/products/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });

export const deleteProduct = (id: number) =>
  request<{ message: string }>(`/products/${id}`, { method: 'DELETE' });

// Export
export const exportAllCsvUrl = (params?: { needs_review?: boolean; missing_price?: boolean }) => {
  const searchParams = new URLSearchParams();
  if (params?.needs_review !== undefined) searchParams.set('needs_review', String(params.needs_review));
  if (params?.missing_price) searchParams.set('missing_price', 'true');
  const qs = searchParams.toString();
  return `${BASE_URL}/export/csv${qs ? `?${qs}` : ''}`;
};

export const exportCatalogCsvUrl = (catalogId: number) =>
  `${BASE_URL}/export/csv/${catalogId}`;
