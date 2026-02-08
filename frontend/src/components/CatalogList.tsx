import { useEffect, useState, useCallback } from 'react';
import {
  FileText,
  Loader2,
  RefreshCw,
  Trash2,
  Download,
  Minimize2,
  AlertCircle,
  CheckCircle2,
  Clock,
  RotateCcw,
} from 'lucide-react';
import {
  getCatalogs,
  deleteCatalog,
  deleteAllCatalogs,
  reprocessCatalog,
  optimizeCatalog,
  exportCatalogCsvUrl,
} from '../services/api';
import type { Catalog } from '../types';

interface Props {
  onRefresh: () => void;
  refreshKey: number;
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

function StatusBadge({ status }: { status: string }) {
  const config: Record<string, { icon: typeof Clock; label: string; cls: string }> = {
    pending: { icon: Clock, label: 'Pending', cls: 'bg-gray-100 text-gray-700' },
    processing: { icon: Loader2, label: 'Processing', cls: 'bg-blue-100 text-blue-700' },
    processed: { icon: CheckCircle2, label: 'Processed', cls: 'bg-green-100 text-green-700' },
    error: { icon: AlertCircle, label: 'Error', cls: 'bg-red-100 text-red-700' },
  };
  const c = config[status] || config.pending;
  const Icon = c.icon;

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${c.cls}`}>
      <Icon className={`h-3 w-3 ${status === 'processing' ? 'animate-spin' : ''}`} />
      {c.label}
    </span>
  );
}

export default function CatalogList({ onRefresh, refreshKey }: Props) {
  const [catalogs, setCatalogs] = useState<Catalog[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<Record<number, string>>({});

  const fetchCatalogs = useCallback(async () => {
    try {
      const data = await getCatalogs();
      setCatalogs(data);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCatalogs();
    const interval = setInterval(fetchCatalogs, 5000);
    return () => clearInterval(interval);
  }, [fetchCatalogs, refreshKey]);

  const handleAction = async (id: number, action: string, fn: () => Promise<unknown>) => {
    setActionLoading((prev) => ({ ...prev, [id]: action }));
    try {
      await fn();
      await fetchCatalogs();
      onRefresh();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Action failed');
    } finally {
      setActionLoading((prev) => {
        const next = { ...prev };
        delete next[id];
        return next;
      });
    }
  };

  const handleDeleteAll = async () => {
    if (!confirm('Delete all catalogs and their products?')) return;
    try {
      await deleteAllCatalogs();
      await fetchCatalogs();
      onRefresh();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed');
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
      </div>
    );
  }

  return (
    <div>
      {catalogs.length > 0 && (
        <div className="flex justify-end mb-3">
          <button
            onClick={handleDeleteAll}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm text-red-600 hover:bg-red-50 rounded-lg transition-colors"
          >
            <Trash2 className="h-4 w-4" />
            Delete All
          </button>
        </div>
      )}

      {catalogs.length === 0 ? (
        <div className="text-center py-12 text-gray-400">
          <FileText className="h-12 w-12 mx-auto mb-3 opacity-50" />
          <p>No catalogs uploaded yet</p>
          <p className="text-sm">Upload a PDF catalog to get started</p>
        </div>
      ) : (
        <div className="space-y-3">
          {catalogs.map((catalog) => (
            <div
              key={catalog.id}
              className="bg-white border border-gray-200 rounded-xl p-4 shadow-sm"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-start gap-3 min-w-0">
                  <div className="bg-red-50 p-2 rounded-lg shrink-0">
                    <FileText className="h-5 w-5 text-red-500" />
                  </div>
                  <div className="min-w-0">
                    <h3 className="font-medium text-gray-900 truncate">{catalog.filename}</h3>
                    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-1 text-xs text-gray-500">
                      <StatusBadge status={catalog.status} />
                      <span>{catalog.total_pages} pages</span>
                      <span>{formatBytes(catalog.file_size)}</span>
                      {catalog.optimized_size && (
                        <span className="text-green-600">
                          Optimized: {formatBytes(catalog.optimized_size)}
                        </span>
                      )}
                    </div>
                    {catalog.status === 'processed' && (
                      <div className="flex gap-3 mt-1.5 text-xs">
                        <span className="text-gray-600">
                          {catalog.total_products} products
                        </span>
                        <span className="text-green-600">
                          {catalog.valid_products} valid
                        </span>
                        {catalog.review_products > 0 && (
                          <span className="text-amber-600">
                            {catalog.review_products} need review
                          </span>
                        )}
                      </div>
                    )}
                    {catalog.error_message && (
                      <p className="text-xs text-red-500 mt-1 truncate" title={catalog.error_message}>
                        {catalog.error_message}
                      </p>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-1 shrink-0">
                  {catalog.status === 'processed' && (
                    <a
                      href={exportCatalogCsvUrl(catalog.id)}
                      className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                      title="Export CSV"
                    >
                      <Download className="h-4 w-4" />
                    </a>
                  )}
                  <button
                    onClick={() => handleAction(catalog.id, 'optimize', () => optimizeCatalog(catalog.id))}
                    disabled={!!actionLoading[catalog.id]}
                    className="p-1.5 text-gray-400 hover:text-purple-600 hover:bg-purple-50 rounded-lg transition-colors disabled:opacity-50"
                    title="Optimize PDF"
                  >
                    {actionLoading[catalog.id] === 'optimize' ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Minimize2 className="h-4 w-4" />
                    )}
                  </button>
                  <button
                    onClick={() => handleAction(catalog.id, 'reprocess', () => reprocessCatalog(catalog.id))}
                    disabled={!!actionLoading[catalog.id]}
                    className="p-1.5 text-gray-400 hover:text-green-600 hover:bg-green-50 rounded-lg transition-colors disabled:opacity-50"
                    title="Reprocess"
                  >
                    {actionLoading[catalog.id] === 'reprocess' ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <RotateCcw className="h-4 w-4" />
                    )}
                  </button>
                  <button
                    onClick={() => {
                      if (confirm(`Delete "${catalog.filename}"?`))
                        handleAction(catalog.id, 'delete', () => deleteCatalog(catalog.id));
                    }}
                    disabled={!!actionLoading[catalog.id]}
                    className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50"
                    title="Delete"
                  >
                    {actionLoading[catalog.id] === 'delete' ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Trash2 className="h-4 w-4" />
                    )}
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
