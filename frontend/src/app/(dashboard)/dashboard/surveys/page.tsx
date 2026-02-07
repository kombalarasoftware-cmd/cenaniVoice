'use client';

import { useState, useEffect } from 'react';
import { toast } from 'sonner';
import {
  ClipboardList,
  ChevronRight,
  Calendar,
  CheckCircle2,
  XCircle,
  Clock,
  BarChart3,
  MessageSquare,
  User,
  Phone,
  Loader2,
  TrendingUp,
  Filter,
} from 'lucide-react';
import Link from 'next/link';

interface SurveyResponse {
  id: number;
  call_id: number | null;
  agent_id: number;
  agent_name: string | null;
  campaign_id: number | null;
  respondent_phone: string | null;
  respondent_name: string | null;
  status: string;
  answers: Array<{
    question_id: string;
    question_text: string;
    question_type: string;
    answer: string;
    answer_value?: number;
  }>;
  questions_answered: number;
  total_questions: number;
  completion_rate: number;
  started_at: string | null;
  completed_at: string | null;
  duration_seconds: number | null;
  created_at: string | null;
}

interface SurveyStats {
  period_days: number;
  total_responses: number;
  completed: number;
  in_progress: number;
  abandoned: number;
  completion_rate: number;
  avg_duration_seconds: number;
  question_stats: Array<{
    question_id: string;
    question_text: string;
    question_type: string;
    total_answers: number;
    answers: Record<string, number>;
    numeric_stats?: {
      average: number | null;
      min: number | null;
      max: number | null;
      count: number;
    };
  }>;
}

export default function SurveysPage() {
  const [responses, setResponses] = useState<SurveyResponse[]>([]);
  const [stats, setStats] = useState<SurveyStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [selectedResponse, setSelectedResponse] = useState<SurveyResponse | null>(null);

  useEffect(() => {
    fetchSurveys();
    fetchStats();
  }, [page, statusFilter]);

  const fetchSurveys = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const headers: Record<string, string> = { 'Content-Type': 'application/json' };
      if (token) headers['Authorization'] = `Bearer ${token}`;

      let url = `http://localhost:8000/api/v1/surveys/?page=${page}&per_page=20`;
      if (statusFilter) url += `&status=${statusFilter}`;

      const response = await fetch(url, { headers });
      if (!response.ok) throw new Error('Failed to fetch surveys');

      const data = await response.json();
      setResponses(data.items || []);
      setTotalPages(data.total_pages || 1);
    } catch (error) {
      console.error('Fetch error:', error);
      toast.error('Failed to load survey responses');
    } finally {
      setIsLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const headers: Record<string, string> = { 'Content-Type': 'application/json' };
      if (token) headers['Authorization'] = `Bearer ${token}`;

      const response = await fetch('http://localhost:8000/api/v1/surveys/stats?days=30', { headers });
      if (!response.ok) return;

      const data = await response.json();
      setStats(data);
    } catch (error) {
      console.error('Stats fetch error:', error);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return (
          <span className="flex items-center gap-1 px-2.5 py-0.5 text-xs rounded-full bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400">
            <CheckCircle2 className="h-3 w-3" />
            Completed
          </span>
        );
      case 'in_progress':
        return (
          <span className="flex items-center gap-1 px-2.5 py-0.5 text-xs rounded-full bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400">
            <Clock className="h-3 w-3" />
            In Progress
          </span>
        );
      case 'abandoned':
        return (
          <span className="flex items-center gap-1 px-2.5 py-0.5 text-xs rounded-full bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400">
            <XCircle className="h-3 w-3" />
            Cancelled
          </span>
        );
      default:
        return (
          <span className="flex items-center gap-1 px-2.5 py-0.5 text-xs rounded-full bg-gray-100 text-gray-700 dark:bg-gray-900/30 dark:text-gray-400">
            Not Started
          </span>
        );
    }
  };

  const formatDuration = (seconds: number | null) => {
    if (!seconds) return '-';
    if (seconds < 60) return `${seconds}s`;
    return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <Loader2 className="h-8 w-8 animate-spin text-primary-500" />
      </div>
    );
  }

  return (
    <div className="min-h-screen p-6 bg-background">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold flex items-center gap-3">
          <ClipboardList className="h-7 w-7" />
          Survey Responses
        </h1>
        <p className="text-muted-foreground mt-1">
          View and analyze survey responses collected in AI conversations
        </p>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-card rounded-xl p-4 border border-border">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-primary-100 dark:bg-primary-900/30 rounded-lg">
                <BarChart3 className="h-5 w-5 text-primary-600 dark:text-primary-400" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Total Responses</p>
                <p className="text-2xl font-bold">{stats.total_responses}</p>
              </div>
            </div>
          </div>
          
          <div className="bg-card rounded-xl p-4 border border-border">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-green-100 dark:bg-green-900/30 rounded-lg">
                <CheckCircle2 className="h-5 w-5 text-green-600 dark:text-green-400" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Completed</p>
                <p className="text-2xl font-bold">{stats.completed}</p>
              </div>
            </div>
          </div>
          
          <div className="bg-card rounded-xl p-4 border border-border">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
                <TrendingUp className="h-5 w-5 text-blue-600 dark:text-blue-400" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Completion Rate</p>
                <p className="text-2xl font-bold">{stats.completion_rate}%</p>
              </div>
            </div>
          </div>
          
          <div className="bg-card rounded-xl p-4 border border-border">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-purple-100 dark:bg-purple-900/30 rounded-lg">
                <Clock className="h-5 w-5 text-purple-600 dark:text-purple-400" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Avg. Duration</p>
                <p className="text-2xl font-bold">{formatDuration(stats.avg_duration_seconds)}</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Filter Bar */}
      <div className="flex items-center gap-4 mb-6">
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-muted-foreground" />
          <span className="text-sm text-muted-foreground">Filter:</span>
        </div>
        <select
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
          className="px-3 py-1.5 text-sm bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
        >
          <option value="">All Statuses</option>
          <option value="completed">Completed</option>
          <option value="in_progress">In Progress</option>
          <option value="abandoned">Cancelled</option>
        </select>
      </div>

      {/* Responses Table */}
      <div className="bg-card rounded-xl border border-border overflow-hidden">
        <table className="w-full">
          <thead className="bg-muted/50 border-b border-border">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Respondent</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Agent</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Status</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Progress</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Duration</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Date</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {responses.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-muted-foreground">
                  No survey responses found yet.
                </td>
              </tr>
            ) : (
              responses.map((response) => (
                <tr key={response.id} className="hover:bg-muted/30 transition-colors">
                  <td className="px-4 py-4">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-muted flex items-center justify-center">
                        <User className="h-4 w-4 text-muted-foreground" />
                      </div>
                      <div>
                        <p className="font-medium text-sm">{response.respondent_name || 'Anonymous'}</p>
                        <p className="text-xs text-muted-foreground flex items-center gap-1">
                          <Phone className="h-3 w-3" />
                          {response.respondent_phone || '-'}
                        </p>
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-4 text-sm">{response.agent_name || '-'}</td>
                  <td className="px-4 py-4">{getStatusBadge(response.status)}</td>
                  <td className="px-4 py-4">
                    <div className="flex items-center gap-2">
                      <div className="w-20 h-2 bg-muted rounded-full overflow-hidden">
                        <div
                          className={`h-full transition-all ${
                            response.completion_rate === 100 ? 'bg-green-500' :
                            response.completion_rate > 50 ? 'bg-yellow-500' : 'bg-red-500'
                          }`}
                          style={{ width: `${response.completion_rate}%` }}
                        />
                      </div>
                      <span className="text-xs text-muted-foreground">
                        {response.questions_answered}/{response.total_questions}
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-4 text-sm">{formatDuration(response.duration_seconds)}</td>
                  <td className="px-4 py-4 text-sm text-muted-foreground">
                    {response.created_at ? new Date(response.created_at).toLocaleString('en-US') : '-'}
                  </td>
                  <td className="px-4 py-4">
                    <button
                      onClick={() => setSelectedResponse(response)}
                      className="p-1.5 hover:bg-muted rounded-lg transition-colors"
                    >
                      <ChevronRight className="h-4 w-4" />
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 mt-6">
          <button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-4 py-2 text-sm bg-muted rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-muted/80 transition-colors"
          >
            Previous
          </button>
          <span className="text-sm text-muted-foreground">
            Page {page} / {totalPages}
          </span>
          <button
            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="px-4 py-2 text-sm bg-muted rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-muted/80 transition-colors"
          >
            Next
          </button>
        </div>
      )}

      {/* Response Detail Modal */}
      {selectedResponse && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="bg-card rounded-xl border border-border w-full max-w-2xl max-h-[80vh] overflow-hidden shadow-2xl">
            <div className="flex items-center justify-between p-4 border-b border-border">
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <MessageSquare className="h-5 w-5" />
                Survey Responses
              </h3>
              <button
                onClick={() => setSelectedResponse(null)}
                className="p-1.5 hover:bg-muted rounded-lg transition-colors"
              >
                ✕
              </button>
            </div>
            
            <div className="p-4 overflow-y-auto max-h-[60vh]">
              {/* Respondent Info */}
              <div className="flex items-center gap-4 mb-6 pb-4 border-b border-border">
                <div className="w-12 h-12 rounded-full bg-muted flex items-center justify-center">
                  <User className="h-6 w-6 text-muted-foreground" />
                </div>
                <div>
                  <p className="font-medium">{selectedResponse.respondent_name || 'Anonymous'}</p>
                  <p className="text-sm text-muted-foreground">{selectedResponse.respondent_phone || 'No phone'}</p>
                </div>
                <div className="ml-auto text-right">
                  {getStatusBadge(selectedResponse.status)}
                  <p className="text-xs text-muted-foreground mt-1">
                    {selectedResponse.created_at ? new Date(selectedResponse.created_at).toLocaleString('en-US') : ''}
                  </p>
                </div>
              </div>
              
              {/* Answers */}
              <div className="space-y-4">
                {selectedResponse.answers.length === 0 ? (
                  <p className="text-center text-muted-foreground py-4">No answers yet.</p>
                ) : (
                  selectedResponse.answers.map((answer, index) => (
                    <div key={answer.question_id} className="bg-muted/30 rounded-lg p-4">
                      <div className="flex items-start justify-between mb-2">
                        <span className="text-xs font-mono text-muted-foreground">{answer.question_id}</span>
                        <span className={`text-xs px-2 py-0.5 rounded ${
                          answer.question_type === 'yes_no' ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400' :
                          answer.question_type === 'rating' ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400' :
                          answer.question_type === 'multiple_choice' ? 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400' :
                          'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                        }`}>
                          {answer.question_type === 'yes_no' ? 'Yes/No' :
                           answer.question_type === 'rating' ? 'Rating' :
                           answer.question_type === 'multiple_choice' ? 'Multiple Choice' : 'Open-Ended'}
                        </span>
                      </div>
                      <p className="text-sm font-medium mb-2">{answer.question_text}</p>
                      <div className="flex items-center gap-2">
                        <span className="text-sm">Answer:</span>
                        {answer.question_type === 'rating' ? (
                          <span className="text-lg font-bold text-primary-500">
                            {answer.answer_value ?? answer.answer}/10
                          </span>
                        ) : answer.question_type === 'yes_no' ? (
                          <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                            answer.answer.toLowerCase().includes('yes') || answer.answer.toLowerCase().includes('evet')
                              ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                              : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                          }`}>
                            {answer.answer.toLowerCase().includes('yes') || answer.answer.toLowerCase().includes('evet') ? '✓ Yes' : '✗ No'}
                          </span>
                        ) : (
                          <span className="text-sm font-medium bg-muted px-3 py-1 rounded-lg">
                            {answer.answer}
                          </span>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
            
            <div className="flex items-center justify-between p-4 border-t border-border bg-muted/30">
              <span className="text-sm text-muted-foreground">
                {selectedResponse.questions_answered}/{selectedResponse.total_questions} questions answered
                ({selectedResponse.completion_rate}%)
              </span>
              <button
                onClick={() => setSelectedResponse(null)}
                className="px-4 py-2 text-sm bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
