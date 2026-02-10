'use client';

import { Header } from '@/components/layout/header';
import { cn } from '@/lib/utils';
import { useState, useEffect, useCallback } from 'react';
import { toast } from 'sonner';
import { api } from '@/lib/api';
import { useDropzone } from 'react-dropzone';
import {
  Phone,
  Upload,
  FileSpreadsheet,
  Trash2,
  Download,
  CheckCircle,
  XCircle,
  RefreshCw,
  MoreVertical,
  Loader2,
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

interface ApiNumberList {
  id: number;
  name: string;
  file_name: string;
  total_numbers: number;
  valid_numbers: number;
  invalid_numbers: number;
  duplicates: number;
  uploaded_at: string;
  status: string;
}

function mapNumberList(n: ApiNumberList): NumberList {
  return {
    id: n.id.toString(),
    name: n.name,
    fileName: n.file_name || '',
    totalNumbers: n.total_numbers || 0,
    validNumbers: n.valid_numbers || 0,
    invalidNumbers: n.invalid_numbers || 0,
    duplicates: n.duplicates || 0,
    uploadedAt: n.uploaded_at ? new Date(n.uploaded_at).toLocaleDateString('en-US') : '-',
    status: (n.status?.toLowerCase() || 'ready') as NumberList['status'],
  };
}

export default function NumbersPage() {
  const [selectedList, setSelectedList] = useState<string | null>(null);
  const [lists, setLists] = useState<NumberList[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);

  const fetchLists = useCallback(async () => {
    try {
      const data = await api.get<ApiNumberList[]>('/numbers/lists');
      setLists(data.map(mapNumberList));
    } catch (err) {
      console.error('Failed to fetch number lists:', err);
      setLists([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchLists();
  }, [fetchLists]);

  const handleUpload = async (file: File) => {
    setIsUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      await api.upload('/numbers/upload', formData);
      toast.success(`File "${file.name}" uploaded successfully`);
      fetchLists();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to upload file');
    } finally {
      setIsUploading(false);
    }
  };

  const handleDelete = async (listId: string) => {
    if (!confirm('Are you sure you want to delete this number list?')) return;
    try {
      await api.delete(`/numbers/lists/${listId}`);
      toast.success('Number list deleted');
      setLists((prev) => prev.filter((l) => l.id !== listId));
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to delete list');
    }
  };

  const handleDownloadTemplate = () => {
    const csvContent = 'phone,name,custom_field_1,custom_field_2\n+15551234567,John Smith,$1500,02/15/2024\n+15559876543,Jane Doe,$2300,02/20/2024\n';
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'number_list_template.csv';
    link.click();
    URL.revokeObjectURL(url);
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop: (acceptedFiles) => {
      if (acceptedFiles.length > 0) {
        handleUpload(acceptedFiles[0]);
      }
    },
    accept: {
      'text/csv': ['.csv'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls'],
    },
    maxFiles: 1,
    disabled: isUploading,
  });

  return (
    <div className="min-h-screen">
      <Header
        title="Number Lists"
        description="Upload and manage phone number lists"
      />

      <div className="p-6">
        {/* Upload area */}
        <div
          {...getRootProps()}
          className={cn(
            'relative rounded-2xl border-2 border-dashed p-8 mb-6 transition-all cursor-pointer',
            isDragActive
              ? 'border-primary-500 bg-primary-500/5'
              : 'border-border hover:border-primary-500/50',
            isUploading && 'pointer-events-none opacity-60'
          )}
        >
          <input {...getInputProps()} />
          <div className="text-center">
            <div
              className={cn(
                'flex h-16 w-16 items-center justify-center rounded-2xl mx-auto mb-4',
                isDragActive ? 'bg-primary-500/10' : 'bg-muted'
              )}
            >
              {isUploading ? (
                <Loader2 className="h-8 w-8 text-primary-500 animate-spin" />
              ) : (
                <Upload
                  className={cn(
                    'h-8 w-8',
                    isDragActive ? 'text-primary-500' : 'text-muted-foreground'
                  )}
                />
              )}
            </div>
            <p className="text-lg font-medium mb-2">
              {isUploading ? 'Uploading...' : 'Drop your Excel or CSV file here'}
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
                  <td className="py-2 px-3">+15551234567</td>
                  <td className="py-2 px-3">John Smith</td>
                  <td className="py-2 px-3">$1500</td>
                  <td className="py-2 px-3">02/15/2024</td>
                </tr>
                <tr>
                  <td className="py-2 px-3">+15559876543</td>
                  <td className="py-2 px-3">Jane Doe</td>
                  <td className="py-2 px-3">$2300</td>
                  <td className="py-2 px-3">02/20/2024</td>
                </tr>
              </tbody>
            </table>
          </div>
          <p className="text-xs text-muted-foreground mt-2">
            * &quot;phone&quot; column is required. Other columns are optional and can be used as variables in your prompts.
          </p>
        </div>

        {/* Lists */}
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold">Uploaded Lists</h3>
          <div className="flex items-center gap-2">
            <button
              onClick={handleDownloadTemplate}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-muted hover:bg-muted/80 text-sm transition-colors"
            >
              <Download className="h-4 w-4" />
              Download Template
            </button>
          </div>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-primary-500" />
          </div>
        ) : lists.length === 0 ? (
          <div className="text-center py-12">
            <FileSpreadsheet className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg font-semibold mb-2">No number lists yet</h3>
            <p className="text-sm text-muted-foreground">
              Upload a CSV or Excel file to get started
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {lists.map((list) => (
              <div
                key={list.id}
                className={cn(
                  'p-4 rounded-xl border bg-card transition-all',
                  selectedList === list.id
                    ? 'border-primary-500 shadow-lg'
                    : 'border-border hover:border-primary-500/50'
                )}
                onClick={() => setSelectedList(list.id === selectedList ? null : list.id)}
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
                        {list.fileName} - Uploaded {list.uploadedAt}
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
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDelete(list.id);
                          }}
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
        )}
      </div>
    </div>
  );
}
