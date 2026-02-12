'use client';

import { Header } from '@/components/layout/header';
import { cn } from '@/lib/utils';
import { useState, useEffect } from 'react';
import { toast } from 'sonner';
import { api } from '@/lib/api';
import {
  Settings,
  User,
  Building,
  Phone,
  Webhook,
  Database,
  Key,
  Shield,
  Bell,
  Globe,
  Save,
  TestTube,
  CheckCircle,
  AlertCircle,
  Plus,
  Trash2,
  Eye,
  EyeOff,
  Loader2,
  UsersRound,
} from 'lucide-react';

type SettingsTab = 'general' | 'sip' | 'api' | 'webhooks' | 'notifications' | 'security' | 'roles';

interface PagePermissions {
  dashboard: boolean;
  agents: boolean;
  campaigns: boolean;
  numbers: boolean;
  recordings: boolean;
  call_logs: boolean;
  appointments: boolean;
  leads: boolean;
  surveys: boolean;
  reports: boolean;
  settings: boolean;
}

interface RolePermission {
  id: number;
  role: string;
  permissions: PagePermissions;
  description: string;
  updated_at: string;
}

const PAGE_LABELS: Record<keyof PagePermissions, string> = {
  dashboard: 'Dashboard',
  agents: 'Agents',
  campaigns: 'Campaigns',
  numbers: 'Numbers',
  recordings: 'Recordings',
  call_logs: 'Call Logs',
  appointments: 'Appointments',
  leads: 'Leads',
  surveys: 'Surveys',
  reports: 'Reports',
  settings: 'Settings',
};

interface NotificationPref {
  label: string;
  description: string;
  key: string;
  enabled: boolean;
}

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<SettingsTab>('general');
  const [showApiKey, setShowApiKey] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isTesting, setIsTesting] = useState(false);

  // General settings state
  const [companyName, setCompanyName] = useState('My Company');
  const [defaultLanguage, setDefaultLanguage] = useState('en');
  const [timezone, setTimezone] = useState('Europe/Istanbul');
  const [openaiApiKey, setOpenaiApiKey] = useState('sk-proj-xxxxxxxxxxxxxxxxxxxxx');
  const [defaultModel, setDefaultModel] = useState('gpt-realtime-mini');

  // SIP settings state
  const [sipServer, setSipServer] = useState('sip.example.com');
  const [sipPort, setSipPort] = useState('5060');
  const [sipUsername, setSipUsername] = useState('voiceai_trunk');
  const [sipPassword, setSipPassword] = useState('');
  const [concurrentCalls, setConcurrentCalls] = useState('50');
  const [codec, setCodec] = useState('opus');
  const [transport, setTransport] = useState('udp');
  const [sipConnected, setSipConnected] = useState(true);

  // Notifications state
  const [notifications, setNotifications] = useState<NotificationPref[]>([
    { label: 'Campaign completed', description: 'Get notified when a campaign finishes', key: 'campaign_completed', enabled: true },
    { label: 'Daily summary', description: 'Receive daily call statistics', key: 'daily_summary', enabled: true },
    { label: 'Error alerts', description: 'Get alerts for system errors', key: 'error_alerts', enabled: true },
    { label: 'Low balance warning', description: 'Alert when credits are running low', key: 'low_balance', enabled: false },
  ]);

  // IP Whitelist
  const [ipWhitelist, setIpWhitelist] = useState('');

  // Role permissions state
  const [roles, setRoles] = useState<RolePermission[]>([]);
  const [isLoadingRoles, setIsLoadingRoles] = useState(false);
  const [isSavingRoles, setIsSavingRoles] = useState<string | null>(null);

  const fetchRoles = async () => {
    setIsLoadingRoles(true);
    try {
      const data = await api.get<RolePermission[]>('/settings/roles');
      setRoles(data);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to load roles');
    } finally {
      setIsLoadingRoles(false);
    }
  };

  const handleTogglePermission = async (
    roleName: string,
    page: keyof PagePermissions,
    currentValue: boolean
  ) => {
    // Prevent disabling settings for ADMIN
    if (roleName === 'ADMIN' && page === 'settings' && currentValue) {
      toast.error('Cannot disable Settings access for Admin role');
      return;
    }

    const role = roles.find((r) => r.role === roleName);
    if (!role) return;

    const updatedPermissions = { ...role.permissions, [page]: !currentValue };

    // Optimistic update
    setRoles((prev) =>
      prev.map((r) =>
        r.role === roleName ? { ...r, permissions: updatedPermissions } : r
      )
    );

    setIsSavingRoles(roleName);
    try {
      await api.put(`/settings/roles/${roleName}`, {
        permissions: updatedPermissions,
      });
      toast.success(`${roleName} permissions updated`);
    } catch (err) {
      // Revert on error
      setRoles((prev) =>
        prev.map((r) =>
          r.role === roleName ? { ...r, permissions: role.permissions } : r
        )
      );
      toast.error(err instanceof Error ? err.message : 'Failed to update permissions');
    } finally {
      setIsSavingRoles(null);
    }
  };

  useEffect(() => {
    if (activeTab === 'roles') {
      fetchRoles();
    }
  }, [activeTab]);

  const toggleNotification = (index: number) => {
    setNotifications((prev) =>
      prev.map((n, i) => (i === index ? { ...n, enabled: !n.enabled } : n))
    );
  };

  const handleSaveAll = async () => {
    setIsSaving(true);
    try {
      await api.post('/settings', {
        company_name: companyName,
        default_language: defaultLanguage,
        timezone,
        openai_api_key: openaiApiKey,
        default_model: defaultModel,
        sip: {
          server: sipServer,
          port: sipPort,
          username: sipUsername,
          password: sipPassword,
          concurrent_calls: parseInt(concurrentCalls, 10),
          codec,
          transport,
        },
        notifications: notifications.reduce<Record<string, boolean>>((acc, n) => {
          acc[n.key] = n.enabled;
          return acc;
        }, {}),
        ip_whitelist: ipWhitelist,
      });
      toast.success('Settings saved successfully');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to save settings');
    } finally {
      setIsSaving(false);
    }
  };

  const handleTestSip = async () => {
    setIsTesting(true);
    try {
      await api.post('/settings/sip/test', {
        server: sipServer,
        port: sipPort,
        username: sipUsername,
        password: sipPassword,
      });
      toast.success('SIP connection test successful');
      setSipConnected(true);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'SIP connection test failed');
      setSipConnected(false);
    } finally {
      setIsTesting(false);
    }
  };

  const handleGenerateKey = async () => {
    try {
      const data = await api.post<{ key: string; name: string }>('/settings/api-keys/generate');
      toast.success(`New API key generated: ${data.name}`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to generate API key');
    }
  };

  const handleDeleteApiKey = async (keyName: string) => {
    if (!confirm(`Delete API key "${keyName}"?`)) return;
    try {
      await api.delete(`/settings/api-keys/${encodeURIComponent(keyName)}`);
      toast.success('API key deleted');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to delete API key');
    }
  };

  const handleDeleteWebhook = async (index: number) => {
    if (!confirm('Delete this webhook endpoint?')) return;
    try {
      await api.delete(`/settings/webhooks/${index}`);
      toast.success('Webhook deleted');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to delete webhook');
    }
  };

  const tabs = [
    { id: 'general' as SettingsTab, label: 'General', icon: Settings },
    { id: 'sip' as SettingsTab, label: 'SIP Trunk', icon: Phone },
    { id: 'api' as SettingsTab, label: 'API Keys', icon: Key },
    { id: 'webhooks' as SettingsTab, label: 'Webhooks', icon: Webhook },
    { id: 'notifications' as SettingsTab, label: 'Notifications', icon: Bell },
    { id: 'security' as SettingsTab, label: 'Security', icon: Shield },
    { id: 'roles' as SettingsTab, label: 'Roles', icon: UsersRound },
  ];

  return (
    <div className="min-h-screen">
      <Header
        title="Settings"
        description="Configure your VoiceAI platform"
      />

      <div className="p-6">
        <div className="flex flex-col lg:flex-row gap-6">
          {/* Sidebar */}
          <div className="lg:w-64 flex-shrink-0">
            <nav className="space-y-1">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={cn(
                    'flex items-center gap-3 w-full px-4 py-3 rounded-lg text-sm font-medium transition-colors',
                    activeTab === tab.id
                      ? 'bg-primary-500/10 text-primary-500'
                      : 'text-muted-foreground hover:text-foreground hover:bg-muted'
                  )}
                >
                  <tab.icon className="h-5 w-5" />
                  {tab.label}
                </button>
              ))}
            </nav>
          </div>

          {/* Content */}
          <div className="flex-1 max-w-3xl">
            {/* General Settings */}
            {activeTab === 'general' && (
              <div className="space-y-6">
                <div className="p-6 rounded-xl bg-card border border-border">
                  <h3 className="font-semibold mb-6 flex items-center gap-2">
                    <Building className="h-5 w-5 text-primary-500" />
                    Company Information
                  </h3>
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium mb-2">Company Name</label>
                      <input
                        type="text"
                        value={companyName}
                        onChange={(e) => setCompanyName(e.target.value)}
                        className={cn(
                          'w-full px-4 py-2.5 rounded-lg bg-background border border-border',
                          'focus:border-primary-500 focus:outline-none transition-colors'
                        )}
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium mb-2">Default Language</label>
                        <select
                          value={defaultLanguage}
                          onChange={(e) => setDefaultLanguage(e.target.value)}
                          className={cn(
                            'w-full px-4 py-2.5 rounded-lg bg-background border border-border',
                            'focus:border-primary-500 focus:outline-none transition-colors'
                          )}
                        >
                          <option value="en">English</option>
                          <option value="tr">Turkish</option>
                          <option value="de">Deutsch</option>
                          <option value="fr">French</option>
                          <option value="es">Spanish</option>
                        </select>
                      </div>
                      <div>
                        <label className="block text-sm font-medium mb-2">Timezone</label>
                        <select
                          value={timezone}
                          onChange={(e) => setTimezone(e.target.value)}
                          className={cn(
                            'w-full px-4 py-2.5 rounded-lg bg-background border border-border',
                            'focus:border-primary-500 focus:outline-none transition-colors'
                          )}
                        >
                          <option value="Europe/Istanbul">Europe/Istanbul (UTC+3)</option>
                          <option value="Europe/London">Europe/London (UTC+0)</option>
                          <option value="America/New_York">America/New York (UTC-5)</option>
                          <option value="America/Los_Angeles">America/Los Angeles (UTC-8)</option>
                        </select>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="p-6 rounded-xl bg-card border border-border">
                  <h3 className="font-semibold mb-6 flex items-center gap-2">
                    <Globe className="h-5 w-5 text-secondary-500" />
                    OpenAI Configuration
                  </h3>
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium mb-2">OpenAI API Key</label>
                      <div className="relative">
                        <input
                          type={showApiKey ? 'text' : 'password'}
                          value={openaiApiKey}
                          onChange={(e) => setOpenaiApiKey(e.target.value)}
                          className={cn(
                            'w-full px-4 py-2.5 pr-20 rounded-lg bg-background border border-border',
                            'focus:border-primary-500 focus:outline-none transition-colors font-mono'
                          )}
                        />
                        <button
                          onClick={() => setShowApiKey(!showApiKey)}
                          className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                        >
                          {showApiKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                        </button>
                      </div>
                    </div>
                    <div>
                      <label className="block text-sm font-medium mb-2">Default Model</label>
                      <select
                        value={defaultModel}
                        onChange={(e) => setDefaultModel(e.target.value)}
                        className={cn(
                          'w-full px-4 py-2.5 rounded-lg bg-background border border-border',
                          'focus:border-primary-500 focus:outline-none transition-colors'
                        )}
                      >
                        <option value="gpt-realtime-mini">gpt-realtime-mini (OpenAI)</option>
                        <option value="gpt-realtime">gpt-realtime (OpenAI)</option>
                        <option value="grok-2-realtime">grok-2-realtime (xAI)</option>
                        <option value="ultravox-v0.7">ultravox-v0.7 (Ultravox latest)</option>
                        <option value="ultravox-v0.6">ultravox-v0.6</option>
                        <option value="ultravox-v0.6-gemma3-27b">ultravox-v0.6-gemma3-27b</option>
                        <option value="ultravox-v0.6-llama3.3-70b">ultravox-v0.6-llama3.3-70b</option>
                      </select>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* SIP Trunk Settings */}
            {activeTab === 'sip' && (
              <div className="space-y-6">
                <div className="p-6 rounded-xl bg-card border border-border">
                  <div className="flex items-center justify-between mb-6">
                    <h3 className="font-semibold flex items-center gap-2">
                      <Phone className="h-5 w-5 text-primary-500" />
                      SIP Trunk Configuration
                    </h3>
                    <div className="flex items-center gap-2">
                      <span className={cn(
                        'flex items-center gap-1.5 px-2.5 py-1 rounded-full text-sm font-medium',
                        sipConnected
                          ? 'bg-success-500/10 text-success-500'
                          : 'bg-error-500/10 text-error-500'
                      )}>
                        {sipConnected ? (
                          <><CheckCircle className="h-4 w-4" /> Connected</>
                        ) : (
                          <><AlertCircle className="h-4 w-4" /> Disconnected</>
                        )}
                      </span>
                    </div>
                  </div>

                  <div className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium mb-2">SIP Server</label>
                        <input
                          type="text"
                          value={sipServer}
                          onChange={(e) => setSipServer(e.target.value)}
                          className={cn(
                            'w-full px-4 py-2.5 rounded-lg bg-background border border-border',
                            'focus:border-primary-500 focus:outline-none transition-colors font-mono'
                          )}
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium mb-2">Port</label>
                        <input
                          type="text"
                          value={sipPort}
                          onChange={(e) => setSipPort(e.target.value)}
                          className={cn(
                            'w-full px-4 py-2.5 rounded-lg bg-background border border-border',
                            'focus:border-primary-500 focus:outline-none transition-colors font-mono'
                          )}
                        />
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium mb-2">Username</label>
                        <input
                          type="text"
                          value={sipUsername}
                          onChange={(e) => setSipUsername(e.target.value)}
                          className={cn(
                            'w-full px-4 py-2.5 rounded-lg bg-background border border-border',
                            'focus:border-primary-500 focus:outline-none transition-colors font-mono'
                          )}
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium mb-2">Password</label>
                        <input
                          type="password"
                          value={sipPassword}
                          onChange={(e) => setSipPassword(e.target.value)}
                          placeholder="Enter password"
                          className={cn(
                            'w-full px-4 py-2.5 rounded-lg bg-background border border-border',
                            'focus:border-primary-500 focus:outline-none transition-colors font-mono'
                          )}
                        />
                      </div>
                    </div>
                    <div>
                      <label className="block text-sm font-medium mb-2">Concurrent Calls Limit</label>
                      <input
                        type="number"
                        value={concurrentCalls}
                        onChange={(e) => setConcurrentCalls(e.target.value)}
                        className={cn(
                          'w-full px-4 py-2.5 rounded-lg bg-background border border-border',
                          'focus:border-primary-500 focus:outline-none transition-colors'
                        )}
                      />
                      <p className="text-xs text-muted-foreground mt-1">
                        Maximum number of simultaneous outbound calls
                      </p>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium mb-2">Codec Priority</label>
                        <select
                          value={codec}
                          onChange={(e) => setCodec(e.target.value)}
                          className={cn(
                            'w-full px-4 py-2.5 rounded-lg bg-background border border-border',
                            'focus:border-primary-500 focus:outline-none transition-colors'
                          )}
                        >
                          <option value="opus">Opus (Recommended)</option>
                          <option value="g711u">G.711 u-law</option>
                          <option value="g711a">G.711 A-law</option>
                        </select>
                      </div>
                      <div>
                        <label className="block text-sm font-medium mb-2">Transport</label>
                        <select
                          value={transport}
                          onChange={(e) => setTransport(e.target.value)}
                          className={cn(
                            'w-full px-4 py-2.5 rounded-lg bg-background border border-border',
                            'focus:border-primary-500 focus:outline-none transition-colors'
                          )}
                        >
                          <option value="udp">UDP</option>
                          <option value="tcp">TCP</option>
                          <option value="tls">TLS</option>
                        </select>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-3 mt-6 pt-6 border-t border-border">
                    <button
                      onClick={handleTestSip}
                      disabled={isTesting}
                      className="flex items-center gap-2 px-4 py-2 rounded-lg bg-secondary-500/10 text-secondary-500 hover:bg-secondary-500/20 text-sm font-medium transition-colors disabled:opacity-50"
                    >
                      {isTesting ? <Loader2 className="h-4 w-4 animate-spin" /> : <TestTube className="h-4 w-4" />}
                      Test Connection
                    </button>
                    <button
                      onClick={handleSaveAll}
                      disabled={isSaving}
                      className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary-500 hover:bg-primary-600 text-white text-sm font-medium transition-colors disabled:opacity-50"
                    >
                      {isSaving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                      Save Changes
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* Webhooks Settings */}
            {activeTab === 'webhooks' && (
              <div className="space-y-6">
                <div className="p-6 rounded-xl bg-card border border-border">
                  <div className="flex items-center justify-between mb-6">
                    <h3 className="font-semibold flex items-center gap-2">
                      <Webhook className="h-5 w-5 text-primary-500" />
                      Webhook Endpoints
                    </h3>
                    <button
                      onClick={() => toast.info('Webhook creation dialog coming soon')}
                      className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-primary-500 hover:bg-primary-600 text-white text-sm font-medium transition-colors"
                    >
                      <Plus className="h-4 w-4" />
                      Add Webhook
                    </button>
                  </div>

                  <div className="space-y-4">
                    {[
                      { url: 'https://api.example.com/webhooks/call-completed', events: ['call.completed', 'call.failed'], status: 'active' },
                      { url: 'https://api.example.com/webhooks/transcription', events: ['transcription.ready'], status: 'active' },
                    ].map((webhook, index) => (
                      <div key={index} className="p-4 rounded-lg border border-border">
                        <div className="flex items-start justify-between">
                          <div>
                            <p className="font-mono text-sm mb-2">{webhook.url}</p>
                            <div className="flex items-center gap-2">
                              {webhook.events.map((event) => (
                                <span key={event} className="px-2 py-0.5 rounded bg-muted text-xs font-medium">
                                  {event}
                                </span>
                              ))}
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="flex items-center gap-1.5 px-2 py-1 rounded-full bg-success-500/10 text-success-500 text-xs font-medium">
                              <CheckCircle className="h-3 w-3" />
                              Active
                            </span>
                            <button
                              onClick={() => handleDeleteWebhook(index)}
                              className="flex h-8 w-8 items-center justify-center rounded-lg hover:bg-error-500/10 text-error-500 transition-colors"
                            >
                              <Trash2 className="h-4 w-4" />
                            </button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="p-4 rounded-xl bg-muted/30">
                  <h4 className="font-medium mb-2">Available Events</h4>
                  <div className="grid grid-cols-2 gap-2 text-sm text-muted-foreground">
                    <span>call.started</span>
                    <span>call.completed</span>
                    <span>call.failed</span>
                    <span>call.transferred</span>
                    <span>transcription.ready</span>
                    <span>campaign.started</span>
                    <span>campaign.completed</span>
                    <span>recording.ready</span>
                  </div>
                </div>
              </div>
            )}

            {/* API Keys */}
            {activeTab === 'api' && (
              <div className="space-y-6">
                <div className="p-6 rounded-xl bg-card border border-border">
                  <div className="flex items-center justify-between mb-6">
                    <h3 className="font-semibold flex items-center gap-2">
                      <Key className="h-5 w-5 text-primary-500" />
                      API Keys
                    </h3>
                    <button
                      onClick={handleGenerateKey}
                      className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-primary-500 hover:bg-primary-600 text-white text-sm font-medium transition-colors"
                    >
                      <Plus className="h-4 w-4" />
                      Generate Key
                    </button>
                  </div>

                  <div className="space-y-4">
                    {[
                      { name: 'Production Key', key: 'vk_live_xxxxxxxxxxxxx', created: '2024-01-15', lastUsed: '2 hours ago' },
                      { name: 'Development Key', key: 'vk_test_xxxxxxxxxxxxx', created: '2024-01-20', lastUsed: '5 minutes ago' },
                    ].map((apiKey, index) => (
                      <div key={index} className="p-4 rounded-lg border border-border">
                        <div className="flex items-center justify-between mb-2">
                          <p className="font-medium">{apiKey.name}</p>
                          <button
                            onClick={() => handleDeleteApiKey(apiKey.name)}
                            className="flex h-8 w-8 items-center justify-center rounded-lg hover:bg-error-500/10 text-error-500 transition-colors"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                        <p className="font-mono text-sm text-muted-foreground mb-2">{apiKey.key}</p>
                        <div className="flex items-center gap-4 text-xs text-muted-foreground">
                          <span>Created: {apiKey.created}</span>
                          <span>Last used: {apiKey.lastUsed}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Notifications */}
            {activeTab === 'notifications' && (
              <div className="space-y-6">
                <div className="p-6 rounded-xl bg-card border border-border">
                  <h3 className="font-semibold mb-6 flex items-center gap-2">
                    <Bell className="h-5 w-5 text-primary-500" />
                    Notification Preferences
                  </h3>

                  <div className="space-y-4">
                    {notifications.map((notification, index) => (
                      <div key={notification.key} className="flex items-center justify-between p-4 rounded-lg bg-muted/30">
                        <div>
                          <p className="font-medium">{notification.label}</p>
                          <p className="text-sm text-muted-foreground">{notification.description}</p>
                        </div>
                        <button
                          onClick={() => toggleNotification(index)}
                          className={cn(
                            'relative w-12 h-6 rounded-full transition-colors',
                            notification.enabled ? 'bg-primary-500' : 'bg-muted'
                          )}
                        >
                          <div
                            className={cn(
                              'absolute top-1 w-4 h-4 rounded-full bg-white transition-transform',
                              notification.enabled ? 'translate-x-7' : 'translate-x-1'
                            )}
                          />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Security */}
            {activeTab === 'security' && (
              <div className="space-y-6">
                <div className="p-6 rounded-xl bg-card border border-border">
                  <h3 className="font-semibold mb-6 flex items-center gap-2">
                    <Shield className="h-5 w-5 text-primary-500" />
                    Security Settings
                  </h3>

                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium mb-2">Two-Factor Authentication</label>
                      <div className="flex items-center justify-between p-4 rounded-lg bg-muted/30">
                        <div>
                          <p className="font-medium">Enable 2FA</p>
                          <p className="text-sm text-muted-foreground">Add an extra layer of security</p>
                        </div>
                        <button className="px-4 py-2 rounded-lg bg-primary-500 hover:bg-primary-600 text-white text-sm font-medium transition-colors">
                          Enable
                        </button>
                      </div>
                    </div>

                    <div>
                      <label className="block text-sm font-medium mb-2">IP Whitelist</label>
                      <textarea
                        placeholder="Enter IP addresses, one per line..."
                        rows={4}
                        value={ipWhitelist}
                        onChange={(e) => setIpWhitelist(e.target.value)}
                        className={cn(
                          'w-full px-4 py-2.5 rounded-lg bg-background border border-border',
                          'focus:border-primary-500 focus:outline-none transition-colors font-mono text-sm'
                        )}
                      />
                      <p className="text-xs text-muted-foreground mt-1">
                        Leave empty to allow all IPs
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Roles */}
            {activeTab === 'roles' && (
              <div className="space-y-6">
                <div className="p-6 rounded-xl bg-card border border-border">
                  <div className="flex items-center justify-between mb-6">
                    <h3 className="font-semibold flex items-center gap-2">
                      <UsersRound className="h-5 w-5 text-primary-500" />
                      Role Permissions
                    </h3>
                    <p className="text-sm text-muted-foreground">
                      Manage page access for each role
                    </p>
                  </div>

                  {isLoadingRoles ? (
                    <div className="flex items-center justify-center py-12">
                      <Loader2 className="h-8 w-8 animate-spin text-primary-500" />
                    </div>
                  ) : roles.length === 0 ? (
                    <div className="text-center py-12 text-muted-foreground">
                      <UsersRound className="h-12 w-12 mx-auto mb-4 opacity-50" />
                      <p>No roles configured</p>
                    </div>
                  ) : (
                    <div className="space-y-8">
                      {roles.map((role) => (
                        <div key={role.role} className="space-y-4">
                          <div className="flex items-center justify-between">
                            <div>
                              <h4 className="font-semibold text-lg">{role.role}</h4>
                              <p className="text-sm text-muted-foreground">{role.description}</p>
                            </div>
                            {isSavingRoles === role.role && (
                              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                                <Loader2 className="h-4 w-4 animate-spin" />
                                Saving...
                              </div>
                            )}
                          </div>

                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                            {(Object.keys(PAGE_LABELS) as (keyof PagePermissions)[]).map((page) => {
                              const isEnabled = role.permissions[page];
                              const isAdminSettings = role.role === 'ADMIN' && page === 'settings';
                              return (
                                <div
                                  key={page}
                                  className={cn(
                                    'flex items-center justify-between p-3 rounded-lg transition-colors',
                                    isEnabled ? 'bg-primary-500/5' : 'bg-muted/30',
                                    isAdminSettings && 'opacity-60'
                                  )}
                                >
                                  <span className="font-medium text-sm">{PAGE_LABELS[page]}</span>
                                  <button
                                    onClick={() => handleTogglePermission(role.role, page, isEnabled)}
                                    disabled={isAdminSettings}
                                    className={cn(
                                      'relative w-11 h-6 rounded-full transition-colors',
                                      isEnabled ? 'bg-primary-500' : 'bg-muted-foreground/30',
                                      isAdminSettings && 'cursor-not-allowed'
                                    )}
                                  >
                                    <div
                                      className={cn(
                                        'absolute top-1 w-4 h-4 rounded-full bg-white shadow transition-transform',
                                        isEnabled ? 'translate-x-6' : 'translate-x-1'
                                      )}
                                    />
                                  </button>
                                </div>
                              );
                            })}
                          </div>

                          {role.updated_at && (
                            <p className="text-xs text-muted-foreground">
                              Last updated: {new Date(role.updated_at).toLocaleString()}
                            </p>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                <div className="p-4 rounded-xl bg-muted/30">
                  <h4 className="font-medium mb-2">About Roles</h4>
                  <ul className="space-y-1 text-sm text-muted-foreground">
                    <li>• <strong>Admin</strong> — Full access to all pages and system management</li>
                    <li>• <strong>Operator</strong> — Standard access, configurable per page</li>
                    <li>• Toggle switches control which pages each role can access</li>
                    <li>• Admin role always retains Settings access</li>
                  </ul>
                </div>
              </div>
            )}

            {/* Save button */}
            <div className="flex justify-end mt-6">
              <button
                onClick={handleSaveAll}
                disabled={isSaving}
                className="flex items-center gap-2 px-6 py-2.5 rounded-lg bg-primary-500 hover:bg-primary-600 text-white font-medium transition-colors disabled:opacity-50"
              >
                {isSaving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                Save All Changes
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
