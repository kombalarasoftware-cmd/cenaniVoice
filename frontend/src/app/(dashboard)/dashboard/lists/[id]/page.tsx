'use client';

import { Header } from '@/components/layout/header';
import { cn } from '@/lib/utils';
import { useState, useEffect, useCallback } from 'react';
import { toast } from 'sonner';
import { api } from '@/lib/api';
import { useParams, useRouter } from 'next/navigation';
import { useDropzone } from 'react-dropzone';
import {
  ArrowLeft,
  Upload,
  FileSpreadsheet,
  Phone,
  Search,
  Plus,
  Trash2,
  RefreshCw,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Loader2,
  Download,
  RotateCcw,
  User,
  Building2,
  Mail,
  Clock,
  X,
  ChevronDown,
} from 'lucide-react';

// ============ Types ============

interface DialList {
  id: number;
  name: string;
  description: string | null;
  status: string;
  total_numbers: number;
  active_numbers: number;
  completed_numbers: number;
  invalid_numbers: number;
  owner_id: number;
  created_at: string;
  updated_at: string;
}

interface DialListEntry {
  id: number;
  list_id: number;
  phone_number: string;
  first_name: string | null;
  last_name: string | null;
  email: string | null;
  company: string | null;
  timezone: string | null;
  priority: number;
  status: string;
  call_attempts: number;
  max_attempts: number;
  last_attempt_at: string | null;
  next_callback_at: string | null;
  dnc_flag: boolean;
  custom_fields: Record<string, unknown> | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

interface PaginatedResponse {
  items: DialListEntry[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

interface UploadResponse {
  total: number;
  success: number;
  errors: number;
  duplicates: number;
  error_details: Array<{ row: number; phone: string; reason: string }> | null;
}

// ============ Entry Status Badge ============

function EntryStatusBadge({ status }: { status: string }): React.ReactElement {
  const config: Record<string, { label: string; className: string }> = {
    new: { label: 'New', className: 'bg-blue-500/10 text-blue-600 dark:text-blue-400' },
    contacted: { label: 'Contacted', className: 'bg-amber-500/10 text-amber-600 dark:text-amber-400' },
    completed: { label: 'Completed', className: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400' },
    callback: { label: 'Callback', className: 'bg-violet-500/10 text-violet-600 dark:text-violet-400' },
    dnc: { label: 'DNC', className: 'bg-red-500/10 text-red-500' },
    invalid: { label: 'Invalid', className: 'bg-zinc-500/10 text-zinc-500' },
    busy: { label: 'Busy', className: 'bg-orange-500/10 text-orange-600 dark:text-orange-400' },
    no_answer: { label: 'No Answer', className: 'bg-yellow-500/10 text-yellow-600 dark:text-yellow-400' },
    failed: { label: 'Failed', className: 'bg-red-500/10 text-red-500' },
  };
  const c = config[status] || { label: status, className: 'bg-zinc-500/10 text-zinc-500' };
  return (
    <span className={cn('inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium', c.className)}>
      {c.label}
    </span>
  );
}

// ============ Upload Section ============

function UploadSection({
  listId,
  onUploadComplete,
}: {
  listId: number;
  onUploadComplete: () => void;
}): React.ReactElement {
  const [isUploading, setIsUploading] = useState(false);
  const [showMapping, setShowMapping] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadResult, setUploadResult] = useState<UploadResponse | null>(null);
  const [columnMapping, setColumnMapping] = useState({
    phone_column: 'A',
    first_name_column: '',
    last_name_column: '',
    email_column: '',
    company_column: '',
    notes_column: '',
  });
  const [countryCode, setCountryCode] = useState('');

  const handleFileDrop = (acceptedFiles: File[]): void => {
    if (acceptedFiles.length > 0) {
      setSelectedFile(acceptedFiles[0]);
      setShowMapping(true);
      setUploadResult(null);
    }
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop: handleFileDrop,
    accept: {
      'text/csv': ['.csv'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls'],
    },
    maxFiles: 1,
    disabled: isUploading,
  });

  const handleUpload = async (): Promise<void> => {
    if (!selectedFile) return;

    setIsUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('phone_column', columnMapping.phone_column || 'A');
      if (columnMapping.first_name_column) formData.append('first_name_column', columnMapping.first_name_column);
      if (columnMapping.last_name_column) formData.append('last_name_column', columnMapping.last_name_column);
      if (columnMapping.email_column) formData.append('email_column', columnMapping.email_column);
      if (columnMapping.company_column) formData.append('company_column', columnMapping.company_column);
      if (columnMapping.notes_column) formData.append('notes_column', columnMapping.notes_column);
      if (countryCode) formData.append('country_code', countryCode);

      const result = await api.upload<UploadResponse>(`/dial-lists/${listId}/upload`, formData);
      setUploadResult(result);
      toast.success(`Uploaded: ${result.success} numbers added`);
      onUploadComplete();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setIsUploading(false);
    }
  };

  const handleCancelMapping = (): void => {
    setShowMapping(false);
    setSelectedFile(null);
    setUploadResult(null);
  };

  const handleDownloadTemplate = (): void => {
    const csvContent =
      'phone,first_name,last_name,email,company,notes\n+905551234567,John,Smith,john@example.com,Acme Corp,Priority customer\n+905559876543,Jane,Doe,jane@example.com,Beta LLC,New lead\n';
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'list_template.csv';
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="mb-6">
      {!showMapping ? (
        <div
          {...getRootProps()}
          className={cn(
            'relative rounded-2xl border-2 border-dashed p-6 transition-all cursor-pointer',
            isDragActive
              ? 'border-primary-500 bg-primary-500/5'
              : 'border-border hover:border-primary-500/50',
            isUploading && 'pointer-events-none opacity-60'
          )}
        >
          <input {...getInputProps()} />
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className={cn(
                'flex h-12 w-12 items-center justify-center rounded-2xl',
                isDragActive ? 'bg-primary-500/10' : 'bg-muted'
              )}>
                <Upload className={cn('h-6 w-6', isDragActive ? 'text-primary-500' : 'text-muted-foreground')} />
              </div>
              <div>
                <p className="font-medium">
                  {isDragActive ? 'Drop file here' : 'Upload Excel or CSV'}
                </p>
                <p className="text-sm text-muted-foreground">
                  .xlsx, .xls, .csv — drag & drop or click to browse
                </p>
              </div>
            </div>
            <button
              onClick={(e) => { e.stopPropagation(); handleDownloadTemplate(); }}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-muted hover:bg-muted/80 text-sm transition-colors"
            >
              <Download className="h-4 w-4" />
              Template
            </button>
          </div>
        </div>
      ) : (
        <div className="rounded-2xl border border-border bg-card p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <FileSpreadsheet className="h-5 w-5 text-primary-500" />
              <div>
                <p className="font-medium">{selectedFile?.name}</p>
                <p className="text-xs text-muted-foreground">
                  {selectedFile && (selectedFile.size / 1024).toFixed(1)} KB
                </p>
              </div>
            </div>
            <button onClick={handleCancelMapping} className="text-muted-foreground hover:text-foreground">
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Column Mapping */}
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 mb-4">
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1">Phone Column *</label>
              <input
                type="text"
                value={columnMapping.phone_column}
                onChange={(e) => setColumnMapping({ ...columnMapping, phone_column: e.target.value })}
                placeholder="A or phone"
                className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/50"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1">First Name</label>
              <input
                type="text"
                value={columnMapping.first_name_column}
                onChange={(e) => setColumnMapping({ ...columnMapping, first_name_column: e.target.value })}
                placeholder="B or first_name"
                className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/50"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1">Last Name</label>
              <input
                type="text"
                value={columnMapping.last_name_column}
                onChange={(e) => setColumnMapping({ ...columnMapping, last_name_column: e.target.value })}
                placeholder="C or last_name"
                className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/50"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1">Email</label>
              <input
                type="text"
                value={columnMapping.email_column}
                onChange={(e) => setColumnMapping({ ...columnMapping, email_column: e.target.value })}
                placeholder="D or email"
                className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/50"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1">Company</label>
              <input
                type="text"
                value={columnMapping.company_column}
                onChange={(e) => setColumnMapping({ ...columnMapping, company_column: e.target.value })}
                placeholder="E or company"
                className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/50"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1">Country Code</label>
              <input
                type="text"
                value={countryCode}
                onChange={(e) => setCountryCode(e.target.value)}
                placeholder="e.g. +90"
                className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/50"
              />
            </div>
          </div>

          <p className="text-xs text-muted-foreground mb-4">
            Enter column letters (A, B, C...) or header names to map your spreadsheet columns.
            Phone column is required. DNC and duplicate checks are automatic.
          </p>

          {/* Upload button */}
          <div className="flex items-center gap-3">
            <button
              onClick={handleUpload}
              disabled={isUploading}
              className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary-500 text-white hover:bg-primary-600 transition-colors text-sm font-medium disabled:opacity-50"
            >
              {isUploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
              {isUploading ? 'Uploading...' : 'Upload & Import'}
            </button>
            <button
              onClick={handleCancelMapping}
              className="px-4 py-2 rounded-xl border border-border hover:bg-muted transition-colors text-sm"
            >
              Cancel
            </button>
          </div>

          {/* Upload Result */}
          {uploadResult && (
            <div className="mt-4 rounded-xl bg-muted/50 p-4">
              <h4 className="font-medium mb-2">Upload Results</h4>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="text-center">
                  <p className="text-lg font-bold">{uploadResult.total}</p>
                  <p className="text-xs text-muted-foreground">Total Rows</p>
                </div>
                <div className="text-center">
                  <p className="text-lg font-bold text-emerald-500">{uploadResult.success}</p>
                  <p className="text-xs text-muted-foreground">Imported</p>
                </div>
                <div className="text-center">
                  <p className="text-lg font-bold text-amber-500">{uploadResult.duplicates}</p>
                  <p className="text-xs text-muted-foreground">Duplicates</p>
                </div>
                <div className="text-center">
                  <p className="text-lg font-bold text-red-500">{uploadResult.errors}</p>
                  <p className="text-xs text-muted-foreground">Errors</p>
                </div>
              </div>
              {uploadResult.error_details && uploadResult.error_details.length > 0 && (
                <div className="mt-3 max-h-32 overflow-y-auto">
                  <p className="text-xs font-medium text-muted-foreground mb-1">Error Details:</p>
                  {uploadResult.error_details.slice(0, 10).map((err, i) => (
                    <p key={i} className="text-xs text-red-500">
                      Row {err.row}: {err.phone} — {err.reason}
                    </p>
                  ))}
                  {uploadResult.error_details.length > 10 && (
                    <p className="text-xs text-muted-foreground">
                      ...and {uploadResult.error_details.length - 10} more
                    </p>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ============ Add Entry Modal ============

function AddEntryModal({
  open,
  listId,
  onClose,
  onAdded,
}: {
  open: boolean;
  listId: number;
  onClose: () => void;
  onAdded: () => void;
}): React.ReactElement | null {
  const [phone, setPhone] = useState('');
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [email, setEmail] = useState('');
  const [company, setCompany] = useState('');
  const [notes, setNotes] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!open) return null;

  const handleSubmit = async (e: React.FormEvent): Promise<void> => {
    e.preventDefault();
    if (!phone.trim()) {
      toast.error('Phone number is required');
      return;
    }

    setIsSubmitting(true);
    try {
      await api.post(`/dial-lists/${listId}/entries`, {
        phone_number: phone.trim(),
        first_name: firstName.trim() || null,
        last_name: lastName.trim() || null,
        email: email.trim() || null,
        company: company.trim() || null,
        notes: notes.trim() || null,
      });
      toast.success('Entry added');
      setPhone(''); setFirstName(''); setLastName('');
      setEmail(''); setCompany(''); setNotes('');
      onClose();
      onAdded();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to add entry');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-card border border-border rounded-2xl shadow-2xl w-full max-w-lg p-6 mx-4">
        <h2 className="text-xl font-semibold mb-4">Add Phone Number</h2>
        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label className="block text-sm font-medium mb-1">Phone Number *</label>
            <input
              type="text"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="+905551234567"
              className="w-full px-4 py-2.5 rounded-xl border border-border bg-background focus:outline-none focus:ring-2 focus:ring-primary-500/50"
              autoFocus
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium mb-1">First Name</label>
              <input
                type="text"
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
                placeholder="John"
                className="w-full px-4 py-2.5 rounded-xl border border-border bg-background focus:outline-none focus:ring-2 focus:ring-primary-500/50"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Last Name</label>
              <input
                type="text"
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
                placeholder="Smith"
                className="w-full px-4 py-2.5 rounded-xl border border-border bg-background focus:outline-none focus:ring-2 focus:ring-primary-500/50"
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium mb-1">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="john@example.com"
                className="w-full px-4 py-2.5 rounded-xl border border-border bg-background focus:outline-none focus:ring-2 focus:ring-primary-500/50"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Company</label>
              <input
                type="text"
                value={company}
                onChange={(e) => setCompany(e.target.value)}
                placeholder="Acme Corp"
                className="w-full px-4 py-2.5 rounded-xl border border-border bg-background focus:outline-none focus:ring-2 focus:ring-primary-500/50"
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Notes</label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Optional notes..."
              rows={2}
              className="w-full px-4 py-2.5 rounded-xl border border-border bg-background focus:outline-none focus:ring-2 focus:ring-primary-500/50 resize-none"
            />
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-xl border border-border hover:bg-muted transition-colors text-sm font-medium"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting || !phone.trim()}
              className="px-4 py-2 rounded-xl bg-primary-500 text-white hover:bg-primary-600 transition-colors text-sm font-medium disabled:opacity-50 flex items-center gap-2"
            >
              {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
              Add Entry
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ============ Main Page ============

export default function ListDetailPage(): React.ReactElement {
  const router = useRouter();
  const params = useParams();
  const listId = Number(params.id);

  const [list, setList] = useState<DialList | null>(null);
  const [entries, setEntries] = useState<DialListEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [isLoadingList, setIsLoadingList] = useState(true);
  const [isLoadingEntries, setIsLoadingEntries] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [showAddModal, setShowAddModal] = useState(false);

  const PAGE_SIZE = 50;

  const fetchList = useCallback(async (): Promise<void> => {
    try {
      const data = await api.get<DialList>(`/dial-lists/${listId}`);
      setList(data);
    } catch (err) {
      console.error('Failed to fetch list:', err);
      toast.error('Failed to load list details');
    } finally {
      setIsLoadingList(false);
    }
  }, [listId]);

  const fetchEntries = useCallback(async (): Promise<void> => {
    setIsLoadingEntries(true);
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: PAGE_SIZE.toString(),
      });
      if (search) params.set('search', search);
      if (statusFilter) params.set('status', statusFilter);

      const data = await api.get<PaginatedResponse>(`/dial-lists/${listId}/entries?${params.toString()}`);
      setEntries(data.items);
      setTotal(data.total);
      setPages(data.pages);
    } catch (err) {
      console.error('Failed to fetch entries:', err);
    } finally {
      setIsLoadingEntries(false);
    }
  }, [listId, page, search, statusFilter]);

  useEffect(() => {
    fetchList();
  }, [fetchList]);

  useEffect(() => {
    fetchEntries();
  }, [fetchEntries]);

  // Debounced search
  const [searchInput, setSearchInput] = useState('');
  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(searchInput);
      setPage(1);
    }, 400);
    return () => clearTimeout(timer);
  }, [searchInput]);

  const handleDeleteEntry = async (entryId: number): Promise<void> => {
    if (!confirm('Delete this entry?')) return;
    try {
      await api.delete(`/dial-lists/${listId}/entries/${entryId}`);
      toast.success('Entry deleted');
      fetchEntries();
      fetchList();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to delete entry');
    }
  };

  const handleResetList = async (): Promise<void> => {
    if (!confirm('Reset all entries to NEW status? This will make all numbers dialable again.')) return;
    try {
      const result = await api.post<{ message: string; reset_count: number }>(`/dial-lists/${listId}/reset`);
      toast.success(`${result.reset_count} entries reset to NEW`);
      fetchEntries();
      fetchList();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to reset list');
    }
  };

  const handleRefreshAll = (): void => {
    fetchList();
    fetchEntries();
  };

  if (isLoadingList) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary-500" />
      </div>
    );
  }

  if (!list) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <XCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold mb-2">List Not Found</h2>
          <button
            onClick={() => router.push('/dashboard/lists')}
            className="text-primary-500 hover:underline text-sm"
          >
            Go back to Lists
          </button>
        </div>
      </div>
    );
  }

  const completionRate = list.total_numbers > 0
    ? Math.round((list.completed_numbers / list.total_numbers) * 100)
    : 0;

  return (
    <div className="min-h-screen">
      <Header
        title={list.name}
        description={list.description || 'List details and phone number management'}
      />

      <div className="p-6">
        {/* Back button + Actions */}
        <div className="flex items-center justify-between mb-6">
          <button
            onClick={() => router.push('/dashboard/lists')}
            className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Lists
          </button>
          <div className="flex items-center gap-2">
            <button
              onClick={handleResetList}
              className="flex items-center gap-2 px-3 py-2 rounded-xl border border-border hover:bg-muted transition-colors text-sm"
              title="Reset all entries to NEW for re-dialing"
            >
              <RotateCcw className="h-4 w-4" />
              Reset All
            </button>
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-5 gap-4 mb-6">
          <div className="rounded-xl border border-border bg-card p-4">
            <div className="flex items-center gap-2 mb-1">
              <Phone className="h-4 w-4 text-muted-foreground" />
              <span className="text-xs text-muted-foreground">Total</span>
            </div>
            <p className="text-2xl font-bold">{list.total_numbers.toLocaleString('en-US')}</p>
          </div>
          <div className="rounded-xl border border-border bg-card p-4">
            <div className="flex items-center gap-2 mb-1">
              <CheckCircle2 className="h-4 w-4 text-emerald-500" />
              <span className="text-xs text-muted-foreground">Active</span>
            </div>
            <p className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">
              {list.active_numbers.toLocaleString('en-US')}
            </p>
          </div>
          <div className="rounded-xl border border-border bg-card p-4">
            <div className="flex items-center gap-2 mb-1">
              <CheckCircle2 className="h-4 w-4 text-blue-500" />
              <span className="text-xs text-muted-foreground">Completed</span>
            </div>
            <p className="text-2xl font-bold text-blue-600 dark:text-blue-400">
              {list.completed_numbers.toLocaleString('en-US')}
            </p>
          </div>
          <div className="rounded-xl border border-border bg-card p-4">
            <div className="flex items-center gap-2 mb-1">
              <XCircle className="h-4 w-4 text-red-500" />
              <span className="text-xs text-muted-foreground">Invalid</span>
            </div>
            <p className="text-2xl font-bold text-red-500">
              {list.invalid_numbers.toLocaleString('en-US')}
            </p>
          </div>
          <div className="rounded-xl border border-border bg-card p-4">
            <div className="flex items-center gap-2 mb-1">
              <AlertTriangle className="h-4 w-4 text-violet-500" />
              <span className="text-xs text-muted-foreground">Completion</span>
            </div>
            <div className="flex items-center gap-2">
              <p className="text-2xl font-bold text-violet-600 dark:text-violet-400">{completionRate}%</p>
              <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
                <div
                  className="h-full bg-violet-500 rounded-full transition-all"
                  style={{ width: `${completionRate}%` }}
                />
              </div>
            </div>
          </div>
        </div>

        {/* Upload Section */}
        <UploadSection listId={listId} onUploadComplete={handleRefreshAll} />

        {/* Entries Table Header */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-4">
          <div className="flex items-center gap-3 w-full sm:w-auto">
            <div className="relative flex-1 sm:w-72">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <input
                type="text"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                placeholder="Search by phone, name, company..."
                className="w-full pl-10 pr-4 py-2 rounded-xl border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/50"
              />
            </div>
            <select
              value={statusFilter}
              onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
              className="px-3 py-2 rounded-xl border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/50"
            >
              <option value="">All Status</option>
              <option value="new">New</option>
              <option value="contacted">Contacted</option>
              <option value="completed">Completed</option>
              <option value="callback">Callback</option>
              <option value="no_answer">No Answer</option>
              <option value="busy">Busy</option>
              <option value="failed">Failed</option>
              <option value="dnc">DNC</option>
              <option value="invalid">Invalid</option>
            </select>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleRefreshAll}
              className="flex items-center gap-2 px-3 py-2 rounded-xl border border-border hover:bg-muted transition-colors text-sm"
            >
              <RefreshCw className="h-4 w-4" />
            </button>
            <button
              onClick={() => setShowAddModal(true)}
              className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary-500 text-white hover:bg-primary-600 transition-colors text-sm font-medium"
            >
              <Plus className="h-4 w-4" />
              Add Number
            </button>
          </div>
        </div>

        {/* Entries Table */}
        {isLoadingEntries ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="h-8 w-8 animate-spin text-primary-500" />
          </div>
        ) : entries.length === 0 ? (
          <div className="text-center py-16 border border-dashed border-border rounded-2xl">
            <Phone className="h-10 w-10 text-muted-foreground mx-auto mb-3" />
            <h3 className="text-lg font-semibold mb-1">No entries yet</h3>
            <p className="text-sm text-muted-foreground mb-4">
              Upload an Excel/CSV file or add numbers manually
            </p>
          </div>
        ) : (
          <>
            <div className="border border-border rounded-2xl overflow-hidden bg-card overflow-x-auto">
              <table className="w-full min-w-[800px]">
                <thead>
                  <tr className="border-b border-border bg-muted/30">
                    <th className="text-left text-xs font-medium text-muted-foreground uppercase tracking-wider px-4 py-3">
                      Phone Number
                    </th>
                    <th className="text-left text-xs font-medium text-muted-foreground uppercase tracking-wider px-4 py-3">
                      Name
                    </th>
                    <th className="text-left text-xs font-medium text-muted-foreground uppercase tracking-wider px-4 py-3">
                      Company
                    </th>
                    <th className="text-left text-xs font-medium text-muted-foreground uppercase tracking-wider px-4 py-3">
                      Status
                    </th>
                    <th className="text-center text-xs font-medium text-muted-foreground uppercase tracking-wider px-4 py-3">
                      Attempts
                    </th>
                    <th className="text-left text-xs font-medium text-muted-foreground uppercase tracking-wider px-4 py-3">
                      Last Attempt
                    </th>
                    <th className="text-right text-xs font-medium text-muted-foreground uppercase tracking-wider px-4 py-3">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {entries.map((entry) => (
                    <tr key={entry.id} className="hover:bg-muted/20 transition-colors">
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <Phone className="h-3.5 w-3.5 text-muted-foreground flex-shrink-0" />
                          <span className="text-sm font-mono">{entry.phone_number}</span>
                          {entry.dnc_flag && (
                            <span className="text-[10px] bg-red-500/10 text-red-500 px-1.5 py-0.5 rounded font-medium">
                              DNC
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <span className="text-sm">
                          {[entry.first_name, entry.last_name].filter(Boolean).join(' ') || '—'}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className="text-sm text-muted-foreground">{entry.company || '—'}</span>
                      </td>
                      <td className="px-4 py-3">
                        <EntryStatusBadge status={entry.status} />
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className="text-sm">
                          {entry.call_attempts}/{entry.max_attempts}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className="text-sm text-muted-foreground">
                          {entry.last_attempt_at
                            ? new Date(entry.last_attempt_at).toLocaleString('en-US', {
                                month: 'short',
                                day: 'numeric',
                                hour: '2-digit',
                                minute: '2-digit',
                              })
                            : '—'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <button
                          onClick={() => handleDeleteEntry(entry.id)}
                          className="inline-flex h-8 w-8 items-center justify-center rounded-lg hover:bg-red-500/10 text-red-500/60 hover:text-red-500 transition-colors"
                          title="Delete"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {pages > 1 && (
              <div className="flex items-center justify-between mt-4 px-2">
                <p className="text-sm text-muted-foreground">
                  Showing {((page - 1) * PAGE_SIZE) + 1}–{Math.min(page * PAGE_SIZE, total)} of {total.toLocaleString('en-US')}
                </p>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setPage(Math.max(1, page - 1))}
                    disabled={page === 1}
                    className="px-3 py-1.5 rounded-lg border border-border text-sm hover:bg-muted disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                  >
                    Previous
                  </button>
                  {Array.from({ length: Math.min(5, pages) }, (_, i) => {
                    let p: number;
                    if (pages <= 5) {
                      p = i + 1;
                    } else if (page <= 3) {
                      p = i + 1;
                    } else if (page >= pages - 2) {
                      p = pages - 4 + i;
                    } else {
                      p = page - 2 + i;
                    }
                    return (
                      <button
                        key={p}
                        onClick={() => setPage(p)}
                        className={cn(
                          'flex h-8 w-8 items-center justify-center rounded-lg text-sm transition-colors',
                          p === page
                            ? 'bg-primary-500 text-white'
                            : 'border border-border hover:bg-muted'
                        )}
                      >
                        {p}
                      </button>
                    );
                  })}
                  <button
                    onClick={() => setPage(Math.min(pages, page + 1))}
                    disabled={page === pages}
                    className="px-3 py-1.5 rounded-lg border border-border text-sm hover:bg-muted disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* Add Entry Modal */}
      <AddEntryModal
        open={showAddModal}
        listId={listId}
        onClose={() => setShowAddModal(false)}
        onAdded={handleRefreshAll}
      />
    </div>
  );
}
