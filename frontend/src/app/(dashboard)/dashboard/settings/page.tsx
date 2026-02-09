'use client';

import { Header } from '@/components/layout/header';
import { cn } from '@/lib/utils';
import { useState } from 'react';
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
} from 'lucide-react';

type SettingsTab = 'general' | 'sip' | 'api' | 'webhooks' | 'notifications' | 'security';

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<SettingsTab>('general');
  const [showApiKey, setShowApiKey] = useState(false);

  const tabs = [
    { id: 'general' as SettingsTab, label: 'General', icon: Settings },
    { id: 'sip' as SettingsTab, label: 'SIP Trunk', icon: Phone },
    { id: 'api' as SettingsTab, label: 'API Keys', icon: Key },
    { id: 'webhooks' as SettingsTab, label: 'Webhooks', icon: Webhook },
    { id: 'notifications' as SettingsTab, label: 'Notifications', icon: Bell },
    { id: 'security' as SettingsTab, label: 'Security', icon: Shield },
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
                        defaultValue="My Company"
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
                          defaultValue="tr"
                          className={cn(
                            'w-full px-4 py-2.5 rounded-lg bg-background border border-border',
                            'focus:border-primary-500 focus:outline-none transition-colors'
                          )}
                        >
                          <option value="tr">Türkçe</option>
                          <option value="en">English</option>
                          <option value="de">Deutsch</option>
                        </select>
                      </div>
                      <div>
                        <label className="block text-sm font-medium mb-2">Timezone</label>
                        <select
                          defaultValue="Europe/Istanbul"
                          className={cn(
                            'w-full px-4 py-2.5 rounded-lg bg-background border border-border',
                            'focus:border-primary-500 focus:outline-none transition-colors'
                          )}
                        >
                          <option value="Europe/Istanbul">Europe/Istanbul (UTC+3)</option>
                          <option value="Europe/London">Europe/London (UTC+0)</option>
                          <option value="America/New_York">America/New York (UTC-5)</option>
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
                          defaultValue="sk-proj-xxxxxxxxxxxxxxxxxxxxx"
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
                        defaultValue="gpt-realtime-mini"
                        className={cn(
                          'w-full px-4 py-2.5 rounded-lg bg-background border border-border',
                          'focus:border-primary-500 focus:outline-none transition-colors'
                        )}
                      >
                        <option value="gpt-realtime-mini">gpt-realtime-mini (OpenAI)</option>
                        <option value="gpt-realtime">gpt-realtime (OpenAI)</option>
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
                      <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-success-500/10 text-success-500 text-sm font-medium">
                        <CheckCircle className="h-4 w-4" />
                        Connected
                      </span>
                    </div>
                  </div>

                  <div className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium mb-2">SIP Server</label>
                        <input
                          type="text"
                          defaultValue="sip.example.com"
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
                          defaultValue="5060"
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
                          defaultValue="voiceai_trunk"
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
                          defaultValue="••••••••"
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
                        defaultValue="50"
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
                          defaultValue="opus"
                          className={cn(
                            'w-full px-4 py-2.5 rounded-lg bg-background border border-border',
                            'focus:border-primary-500 focus:outline-none transition-colors'
                          )}
                        >
                          <option value="opus">Opus (Recommended)</option>
                          <option value="g711u">G.711 µ-law</option>
                          <option value="g711a">G.711 A-law</option>
                        </select>
                      </div>
                      <div>
                        <label className="block text-sm font-medium mb-2">Transport</label>
                        <select
                          defaultValue="udp"
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
                    <button className="flex items-center gap-2 px-4 py-2 rounded-lg bg-secondary-500/10 text-secondary-500 hover:bg-secondary-500/20 text-sm font-medium transition-colors">
                      <TestTube className="h-4 w-4" />
                      Test Connection
                    </button>
                    <button className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary-500 hover:bg-primary-600 text-white text-sm font-medium transition-colors">
                      <Save className="h-4 w-4" />
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
                    <button className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-primary-500 hover:bg-primary-600 text-white text-sm font-medium transition-colors">
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
                            <button className="flex h-8 w-8 items-center justify-center rounded-lg hover:bg-error-500/10 text-error-500 transition-colors">
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
                    <span>• call.started</span>
                    <span>• call.completed</span>
                    <span>• call.failed</span>
                    <span>• call.transferred</span>
                    <span>• transcription.ready</span>
                    <span>• campaign.started</span>
                    <span>• campaign.completed</span>
                    <span>• recording.ready</span>
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
                    <button className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-primary-500 hover:bg-primary-600 text-white text-sm font-medium transition-colors">
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
                          <button className="flex h-8 w-8 items-center justify-center rounded-lg hover:bg-error-500/10 text-error-500 transition-colors">
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
                    {[
                      { label: 'Campaign completed', description: 'Get notified when a campaign finishes', enabled: true },
                      { label: 'Daily summary', description: 'Receive daily call statistics', enabled: true },
                      { label: 'Error alerts', description: 'Get alerts for system errors', enabled: true },
                      { label: 'Low balance warning', description: 'Alert when credits are running low', enabled: false },
                    ].map((notification, index) => (
                      <div key={index} className="flex items-center justify-between p-4 rounded-lg bg-muted/30">
                        <div>
                          <p className="font-medium">{notification.label}</p>
                          <p className="text-sm text-muted-foreground">{notification.description}</p>
                        </div>
                        <button
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

            {/* Save button */}
            <div className="flex justify-end mt-6">
              <button className="flex items-center gap-2 px-6 py-2.5 rounded-lg bg-primary-500 hover:bg-primary-600 text-white font-medium transition-colors">
                <Save className="h-4 w-4" />
                Save All Changes
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
