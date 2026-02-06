'use client';

import { Header } from '@/components/layout/header';
import { cn } from '@/lib/utils';
import { useState } from 'react';
import {
  Phone,
  Upload,
  FileSpreadsheet,
  Trash2,
  Download,
  Search,
  Plus,
  CheckCircle,
  XCircle,
  Clock,
  Filter,
  MoreVertical,
  RefreshCw,
} from 'lucide-react';

interface NumberList {
  id: string;
  name: string;
  fileName: string;
  totalNumbers: number;
  validNumbers: number;
  invalidNumbers: number;
  duplicates: number;
  uploadedAt: string;
  status: 'processing' | 'ready' | 'error';
}

const mockLists: NumberList[] = [
  {
    id: '1',
    name: 'Ödeme Hatırlatma - Şubat',
    fileName: 'odeme_subat_2024.xlsx',
    totalNumbers: 5234,
    validNumbers: 5000,
    invalidNumbers: 185,
    duplicates: 49,
    uploadedAt: '2024-02-01 14:30',
    status: 'ready',
  },
  {
    id: '2',
    name: 'Müşteri Anketi Q1',
    fileName: 'musteri_anketi_q1.xlsx',
    totalNumbers: 2150,
    validNumbers: 2000,
    invalidNumbers: 120,
    duplicates: 30,
    uploadedAt: '2024-01-28 09:15',
    status: 'ready',
  },
  {
    id: '3',
    name: 'VIP Müşteriler',
    fileName: 'vip_customers.csv',
    totalNumbers: 500,
    validNumbers: 498,
    invalidNumbers: 2,
    duplicates: 0,
    uploadedAt: '2024-02-05 16:45',
    status: 'ready',
  },
  {
    id: '4',
    name: 'Yeni Kampanya Listesi',
    fileName: 'new_campaign_numbers.xlsx',
    totalNumbers: 3000,
    validNumbers: 0,
    invalidNumbers: 0,
    duplicates: 0,
    uploadedAt: '2024-02-06 10:00',
    status: 'processing',
  },
];

export default function NumbersPage() {
  const [dragActive, setDragActive] = useState(false);
  const [selectedList, setSelectedList] = useState<string | null>(null);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    // Handle file upload
    const files = e.dataTransfer.files;
    if (files && files[0]) {
      console.log('File dropped:', files[0].name);
    }
  };

  return (
    <div className="min-h-screen">
      <Header
        title="Number Lists"
        description="Upload and manage phone number lists"
      />

      <div className="p-6">
        {/* Upload area */}
        <div
          className={cn(
            'relative rounded-2xl border-2 border-dashed p-8 mb-6 transition-all',
            dragActive
              ? 'border-primary-500 bg-primary-500/5'
              : 'border-border hover:border-primary-500/50'
          )}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
        >
          <input
            type="file"
            accept=".xlsx,.xls,.csv"
            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) {
                console.log('File selected:', file.name);
              }
            }}
          />
          <div className="text-center">
            <div
              className={cn(
                'flex h-16 w-16 items-center justify-center rounded-2xl mx-auto mb-4',
                dragActive ? 'bg-primary-500/10' : 'bg-muted'
              )}
            >
              <Upload
                className={cn(
                  'h-8 w-8',
                  dragActive ? 'text-primary-500' : 'text-muted-foreground'
                )}
              />
            </div>
            <p className="text-lg font-medium mb-2">
              Drop your Excel or CSV file here
            </p>
            <p className="text-sm text-muted-foreground mb-4">
              or click to browse from your computer
            </p>
            <div className="flex items-center justify-center gap-4">
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <FileSpreadsheet className="h-4 w-4" />
                <span>.xlsx, .xls, .csv</span>
              </div>
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Phone className="h-4 w-4" />
                <span>Max 100,000 numbers</span>
              </div>
            </div>
          </div>
        </div>

        {/* Format guide */}
        <div className="rounded-xl bg-muted/30 p-4 mb-6">
          <h4 className="font-medium mb-2">Required Excel Format</h4>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left py-2 px-3 font-medium">phone</th>
                  <th className="text-left py-2 px-3 font-medium">name</th>
                  <th className="text-left py-2 px-3 font-medium">custom_field_1</th>
                  <th className="text-left py-2 px-3 font-medium">custom_field_2</th>
                </tr>
              </thead>
              <tbody className="text-muted-foreground">
                <tr>
                  <td className="py-2 px-3">+905321234567</td>
                  <td className="py-2 px-3">Ahmet Yılmaz</td>
                  <td className="py-2 px-3">1500 TL</td>
                  <td className="py-2 px-3">15/02/2024</td>
                </tr>
                <tr>
                  <td className="py-2 px-3">+905351234567</td>
                  <td className="py-2 px-3">Ayşe Demir</td>
                  <td className="py-2 px-3">2300 TL</td>
                  <td className="py-2 px-3">20/02/2024</td>
                </tr>
              </tbody>
            </table>
          </div>
          <p className="text-xs text-muted-foreground mt-2">
            * "phone" column is required. Other columns are optional and can be used as variables in your prompts.
          </p>
        </div>

        {/* Lists */}
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold">Uploaded Lists</h3>
          <div className="flex items-center gap-2">
            <button className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-muted hover:bg-muted/80 text-sm transition-colors">
              <Download className="h-4 w-4" />
              Download Template
            </button>
          </div>
        </div>

        <div className="space-y-3">
          {mockLists.map((list) => (
            <div
              key={list.id}
              className={cn(
                'p-4 rounded-xl border bg-card transition-all',
                selectedList === list.id
                  ? 'border-primary-500 shadow-lg'
                  : 'border-border hover:border-primary-500/50'
              )}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div
                    className={cn(
                      'flex h-12 w-12 items-center justify-center rounded-xl',
                      list.status === 'ready' && 'bg-success-500/10',
                      list.status === 'processing' && 'bg-warning-500/10',
                      list.status === 'error' && 'bg-error-500/10'
                    )}
                  >
                    {list.status === 'ready' && (
                      <CheckCircle className="h-6 w-6 text-success-500" />
                    )}
                    {list.status === 'processing' && (
                      <RefreshCw className="h-6 w-6 text-warning-500 animate-spin" />
                    )}
                    {list.status === 'error' && (
                      <XCircle className="h-6 w-6 text-error-500" />
                    )}
                  </div>
                  <div>
                    <p className="font-medium">{list.name}</p>
                    <p className="text-sm text-muted-foreground">
                      {list.fileName} • Uploaded {list.uploadedAt}
                    </p>
                  </div>
                </div>

                {list.status === 'ready' && (
                  <div className="flex items-center gap-6">
                    <div className="flex items-center gap-4 text-sm">
                      <div className="text-center">
                        <p className="font-semibold text-lg">{list.validNumbers.toLocaleString('en-US')}</p>
                        <p className="text-xs text-muted-foreground">Valid</p>
                      </div>
                      <div className="text-center">
                        <p className="font-semibold text-lg text-error-500">{list.invalidNumbers}</p>
                        <p className="text-xs text-muted-foreground">Invalid</p>
                      </div>
                      <div className="text-center">
                        <p className="font-semibold text-lg text-warning-500">{list.duplicates}</p>
                        <p className="text-xs text-muted-foreground">Duplicates</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        className={cn(
                          'flex h-9 w-9 items-center justify-center rounded-lg',
                          'hover:bg-error-500/10 text-error-500 transition-colors'
                        )}
                        title="Delete"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                      <button
                        className={cn(
                          'flex h-9 w-9 items-center justify-center rounded-lg',
                          'hover:bg-muted transition-colors'
                        )}
                      >
                        <MoreVertical className="h-4 w-4 text-muted-foreground" />
                      </button>
                    </div>
                  </div>
                )}

                {list.status === 'processing' && (
                  <div className="flex items-center gap-3">
                    <div className="w-32 h-2 bg-muted rounded-full overflow-hidden">
                      <div className="h-full w-1/3 bg-warning-500 rounded-full animate-pulse" />
                    </div>
                    <span className="text-sm text-muted-foreground">Processing...</span>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
