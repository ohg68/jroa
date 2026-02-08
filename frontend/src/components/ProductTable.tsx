import { useEffect, useState, useCallback } from 'react';
import {
  Search,
  Loader2,
  Save,
  Trash2,
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
  Filter,
  X,
} from 'lucide-react';
import { getProducts, updateProduct, deleteProduct } from '../services/api';
import type { Product } from '../types';

interface Props {
  refreshKey: number;
  onRefresh: () => void;
}

export default function ProductTable({ refreshKey, onRefresh }: Props) {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [filterReview, setFilterReview] = useState(false);
  const [filterMissingPrice, setFilterMissingPrice] = useState(false);
  const [page, setPage] = useState(1);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editData, setEditData] = useState<Partial<Product>>({});
  const [saving, setSaving] = useState(false);

  const perPage = 50;

  const fetchProducts = useCallback(async () => {
    try {
      const data = await getProducts({
        search: search || undefined,
        needs_review: filterReview ? true : undefined,
        missing_price: filterMissingPrice || undefined,
        page,
        per_page: perPage,
      });
      setProducts(data);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, [search, filterReview, filterMissingPrice, page]);

  useEffect(() => {
    setLoading(true);
    fetchProducts();
  }, [fetchProducts, refreshKey]);

  const startEdit = (product: Product) => {
    setEditingId(product.id);
    setEditData({
      name: product.name,
      default_code: product.default_code,
      list_price: product.list_price,
      categ_id: product.categ_id,
      description_sale: product.description_sale,
      brand: product.brand,
      unit: product.unit,
    });
  };

  const saveEdit = async () => {
    if (!editingId) return;
    setSaving(true);
    try {
      await updateProduct(editingId, editData);
      setEditingId(null);
      await fetchProducts();
      onRefresh();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Delete this product?')) return;
    try {
      await deleteProduct(id);
      await fetchProducts();
      onRefresh();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Delete failed');
    }
  };

  const clearFilters = () => {
    setSearch('');
    setFilterReview(false);
    setFilterMissingPrice(false);
    setPage(1);
  };

  const hasFilters = search || filterReview || filterMissingPrice;

  return (
    <div>
      {/* Filters Bar */}
      <div className="flex flex-wrap items-center gap-3 mb-4">
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search products..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            className="w-full pl-9 pr-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        <button
          onClick={() => {
            setFilterReview(!filterReview);
            setPage(1);
          }}
          className={`inline-flex items-center gap-1.5 px-3 py-2 text-sm rounded-lg border transition-colors ${
            filterReview
              ? 'bg-amber-50 border-amber-300 text-amber-700'
              : 'border-gray-300 text-gray-600 hover:bg-gray-50'
          }`}
        >
          <AlertTriangle className="h-3.5 w-3.5" />
          Needs Review
        </button>

        <button
          onClick={() => {
            setFilterMissingPrice(!filterMissingPrice);
            setPage(1);
          }}
          className={`inline-flex items-center gap-1.5 px-3 py-2 text-sm rounded-lg border transition-colors ${
            filterMissingPrice
              ? 'bg-red-50 border-red-300 text-red-700'
              : 'border-gray-300 text-gray-600 hover:bg-gray-50'
          }`}
        >
          <Filter className="h-3.5 w-3.5" />
          Missing Price
        </button>

        {hasFilters && (
          <button
            onClick={clearFilters}
            className="inline-flex items-center gap-1 px-2 py-2 text-sm text-gray-500 hover:text-gray-700"
          >
            <X className="h-3.5 w-3.5" />
            Clear
          </button>
        )}
      </div>

      {loading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
        </div>
      ) : products.length === 0 ? (
        <div className="text-center py-12 text-gray-400">
          <p>No products found</p>
        </div>
      ) : (
        <>
          <div className="overflow-x-auto border border-gray-200 rounded-xl">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="text-left px-4 py-3 font-medium text-gray-500">Product</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-500">SKU</th>
                  <th className="text-right px-4 py-3 font-medium text-gray-500">Price</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-500">Category</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-500">Brand</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-500">Status</th>
                  <th className="text-right px-4 py-3 font-medium text-gray-500">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {products.map((product) => (
                  <tr
                    key={product.id}
                    className={`hover:bg-gray-50 ${product.needs_review ? 'bg-amber-50/50' : ''}`}
                  >
                    {editingId === product.id ? (
                      <>
                        <td className="px-4 py-2">
                          <input
                            className="w-full px-2 py-1 border rounded text-sm"
                            value={editData.name || ''}
                            onChange={(e) => setEditData({ ...editData, name: e.target.value })}
                          />
                        </td>
                        <td className="px-4 py-2">
                          <input
                            className="w-full px-2 py-1 border rounded text-sm"
                            value={editData.default_code || ''}
                            onChange={(e) => setEditData({ ...editData, default_code: e.target.value })}
                          />
                        </td>
                        <td className="px-4 py-2">
                          <input
                            type="number"
                            step="0.01"
                            className="w-24 px-2 py-1 border rounded text-sm text-right"
                            value={editData.list_price ?? ''}
                            onChange={(e) =>
                              setEditData({
                                ...editData,
                                list_price: e.target.value ? parseFloat(e.target.value) : null,
                              })
                            }
                          />
                        </td>
                        <td className="px-4 py-2">
                          <input
                            className="w-full px-2 py-1 border rounded text-sm"
                            value={editData.categ_id || ''}
                            onChange={(e) => setEditData({ ...editData, categ_id: e.target.value })}
                          />
                        </td>
                        <td className="px-4 py-2">
                          <input
                            className="w-full px-2 py-1 border rounded text-sm"
                            value={editData.brand || ''}
                            onChange={(e) => setEditData({ ...editData, brand: e.target.value })}
                          />
                        </td>
                        <td className="px-4 py-2" />
                        <td className="px-4 py-2 text-right">
                          <div className="flex justify-end gap-1">
                            <button
                              onClick={saveEdit}
                              disabled={saving}
                              className="p-1 text-green-600 hover:bg-green-50 rounded"
                            >
                              {saving ? (
                                <Loader2 className="h-4 w-4 animate-spin" />
                              ) : (
                                <Save className="h-4 w-4" />
                              )}
                            </button>
                            <button
                              onClick={() => setEditingId(null)}
                              className="p-1 text-gray-400 hover:bg-gray-100 rounded"
                            >
                              <X className="h-4 w-4" />
                            </button>
                          </div>
                        </td>
                      </>
                    ) : (
                      <>
                        <td className="px-4 py-3">
                          <button
                            onClick={() => startEdit(product)}
                            className="text-left hover:text-blue-600 cursor-pointer"
                            title="Click to edit"
                          >
                            <span className="font-medium text-gray-900">{product.name}</span>
                            {product.description_sale && (
                              <p className="text-xs text-gray-400 truncate max-w-xs">
                                {product.description_sale}
                              </p>
                            )}
                          </button>
                        </td>
                        <td className="px-4 py-3 text-gray-600 font-mono text-xs">
                          {product.default_code || '-'}
                        </td>
                        <td className="px-4 py-3 text-right font-medium">
                          {product.list_price != null ? (
                            <span className="text-gray-900">
                              ${product.list_price.toFixed(2)}
                            </span>
                          ) : (
                            <span className="text-red-400">-</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-gray-600 text-xs">
                          {product.categ_id || '-'}
                        </td>
                        <td className="px-4 py-3 text-gray-600 text-xs">
                          {product.brand || '-'}
                        </td>
                        <td className="px-4 py-3">
                          {product.needs_review ? (
                            <span className="inline-flex items-center gap-1 text-xs text-amber-600">
                              <AlertTriangle className="h-3 w-3" />
                              {product.review_reason}
                            </span>
                          ) : (
                            <span className="text-xs text-green-600">Valid</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <div className="flex justify-end gap-1">
                            <button
                              onClick={() => startEdit(product)}
                              className="p-1 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded"
                              title="Edit"
                            >
                              <Save className="h-4 w-4" />
                            </button>
                            <button
                              onClick={() => handleDelete(product.id)}
                              className="p-1 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded"
                              title="Delete"
                            >
                              <Trash2 className="h-4 w-4" />
                            </button>
                          </div>
                        </td>
                      </>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="flex justify-between items-center mt-4">
            <p className="text-sm text-gray-500">
              Page {page} &middot; {products.length} products shown
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="inline-flex items-center gap-1 px-3 py-1.5 text-sm border rounded-lg disabled:opacity-50 hover:bg-gray-50"
              >
                <ChevronLeft className="h-4 w-4" />
                Previous
              </button>
              <button
                onClick={() => setPage((p) => p + 1)}
                disabled={products.length < perPage}
                className="inline-flex items-center gap-1 px-3 py-1.5 text-sm border rounded-lg disabled:opacity-50 hover:bg-gray-50"
              >
                Next
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
