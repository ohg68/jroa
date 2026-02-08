import { useEffect, useState } from 'react';
import { FileText, Package, CheckCircle, AlertTriangle, Loader2 } from 'lucide-react';
import { getDashboard } from '../services/api';
import type { Dashboard as DashboardType } from '../types';

export default function Dashboard() {
  const [data, setData] = useState<DashboardType | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchDashboard = async () => {
    try {
      const d = await getDashboard();
      setData(d);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboard();
    const interval = setInterval(fetchDashboard, 5000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
      </div>
    );
  }

  if (!data) return null;

  const cards = [
    {
      label: 'Catalogs Processed',
      value: `${data.processed_catalogs}/${data.total_catalogs}`,
      sub: data.pending_catalogs > 0 ? `${data.pending_catalogs} pending` : undefined,
      icon: FileText,
      color: 'text-blue-600',
      bg: 'bg-blue-50',
    },
    {
      label: 'Products Extracted',
      value: data.total_products,
      icon: Package,
      color: 'text-indigo-600',
      bg: 'bg-indigo-50',
    },
    {
      label: 'Valid Products',
      value: data.valid_products,
      sub: data.total_products > 0
        ? `${Math.round((data.valid_products / data.total_products) * 100)}%`
        : undefined,
      icon: CheckCircle,
      color: 'text-green-600',
      bg: 'bg-green-50',
    },
    {
      label: 'Need Review',
      value: data.review_products,
      sub: data.error_catalogs > 0 ? `${data.error_catalogs} catalog errors` : undefined,
      icon: AlertTriangle,
      color: 'text-amber-600',
      bg: 'bg-amber-50',
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {cards.map((card) => (
        <div
          key={card.label}
          className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm"
        >
          <div className="flex items-center gap-3">
            <div className={`${card.bg} p-2.5 rounded-lg`}>
              <card.icon className={`h-5 w-5 ${card.color}`} />
            </div>
            <div>
              <p className="text-sm text-gray-500">{card.label}</p>
              <p className="text-2xl font-semibold text-gray-900">{card.value}</p>
              {card.sub && <p className="text-xs text-gray-400">{card.sub}</p>}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
