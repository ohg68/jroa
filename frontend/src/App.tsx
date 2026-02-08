import { useState } from 'react';
import { Download, FileText, Package } from 'lucide-react';
import Dashboard from './components/Dashboard';
import UploadZone from './components/UploadZone';
import CatalogList from './components/CatalogList';
import ProductTable from './components/ProductTable';
import { exportAllCsvUrl } from './services/api';

type Tab = 'catalogs' | 'products';

export default function App() {
  const [activeTab, setActiveTab] = useState<Tab>('catalogs');
  const [refreshKey, setRefreshKey] = useState(0);

  const refresh = () => setRefreshKey((k) => k + 1);

  const tabs: { key: Tab; label: string; icon: typeof FileText }[] = [
    { key: 'catalogs', label: 'Catalogs', icon: FileText },
    { key: 'products', label: 'Products', icon: Package },
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-3">
              <div className="bg-blue-600 p-2 rounded-lg">
                <FileText className="h-5 w-5 text-white" />
              </div>
              <div>
                <h1 className="text-lg font-semibold text-gray-900">
                  PDF Catalog Extractor
                </h1>
                <p className="text-xs text-gray-500">
                  Extract products &middot; Export to Odoo CSV
                </p>
              </div>
            </div>

            <a
              href={exportAllCsvUrl()}
              className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
            >
              <Download className="h-4 w-4" />
              Export All CSV
            </a>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {/* Dashboard Metrics */}
        <Dashboard key={refreshKey} />

        {/* Upload Zone */}
        <UploadZone onUploadComplete={refresh} />

        {/* Tabs */}
        <div className="border-b border-gray-200">
          <nav className="flex gap-6">
            {tabs.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`inline-flex items-center gap-2 py-3 px-1 border-b-2 text-sm font-medium transition-colors ${
                  activeTab === tab.key
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <tab.icon className="h-4 w-4" />
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        {/* Tab Content */}
        {activeTab === 'catalogs' ? (
          <CatalogList onRefresh={refresh} refreshKey={refreshKey} />
        ) : (
          <ProductTable refreshKey={refreshKey} onRefresh={refresh} />
        )}
      </main>
    </div>
  );
}
