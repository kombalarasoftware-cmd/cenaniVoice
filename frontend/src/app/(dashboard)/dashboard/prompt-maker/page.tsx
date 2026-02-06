'use client';

import { Header } from '@/components/layout/header';
import { cn } from '@/lib/utils';
import { useState } from 'react';
import {
  Sparkles,
  Copy,
  Wand2,
  Save,
  Play,
  ChevronRight,
  MessageSquare,
  BookOpen,
  Settings2,
  Wrench,
  Shield,
  AlertCircle,
  Globe,
  Lightbulb,
  FileText,
  Star,
  Clock,
  Check,
} from 'lucide-react';

interface Template {
  id: string;
  name: string;
  description: string;
  category: string;
  rating: number;
  usageCount: number;
  sections: {
    role: string;
    personality: string;
    language: string;
    flow: string;
    tools: string;
    safety: string;
    rules: string;
  };
}

const templates: Template[] = [
  {
    id: 'payment-reminder',
    name: 'Payment Reminder',
    description: 'Professional payment reminder with escalation options',
    category: 'Collections',
    rating: 4.8,
    usageCount: 2340,
    sections: {
      role: `You are a professional customer service representative for {{company_name}}.
Your primary objective is to remind customers about their pending payments and help them find a solution.`,
      personality: `Tone: Professional, understanding, and solution-oriented
- Be empathetic but firm
- Never threaten or use aggressive language
- Focus on helping the customer resolve the issue`,
      language: `Primary language: {{language}}
- Use formal address (siz/vous/Sie)
- Be clear and concise`,
      flow: `1. Greeting and identification
2. State purpose of call
3. Verify customer identity
4. Provide payment details
5. Ask about payment intention
6. Offer solutions if needed
7. Summarize and close`,
      tools: `Available functions:
- get_customer_info(phone)
- get_payment_status(customer_id)
- create_payment_promise(customer_id, date, amount)
- schedule_callback(customer_id, datetime, notes)
- transfer_to_human(reason)`,
      safety: `Escalate to human when:
- Customer explicitly requests human
- Customer is angry after 2 attempts
- Complex account issues
- Legal disputes`,
      rules: `- Verify identity before sharing details
- Max call duration: 5 minutes
- Max retries: 3 per day
- Record all payment promises`,
    },
  },
  {
    id: 'appointment-reminder',
    name: 'Appointment Reminder',
    description: 'Friendly reminder for upcoming appointments',
    category: 'Healthcare',
    rating: 4.9,
    usageCount: 1856,
    sections: {
      role: `You are a friendly appointment reminder assistant for {{company_name}}.
Your goal is to remind patients/customers of their upcoming appointments and confirm attendance.`,
      personality: `Tone: Warm, friendly, and helpful
- Be clear about appointment details
- Offer to reschedule if needed
- Keep the conversation brief`,
      language: `Primary language: {{language}}
- Use a friendly but professional tone`,
      flow: `1. Greet and introduce yourself
2. Mention the appointment date/time
3. Confirm if they can attend
4. If not, offer rescheduling
5. Provide contact info for questions
6. Friendly closing`,
      tools: `Available functions:
- get_appointment_details(phone)
- confirm_appointment(appointment_id)
- reschedule_appointment(appointment_id, new_datetime)
- cancel_appointment(appointment_id, reason)`,
      safety: `Escalate when:
- Customer has concerns about the procedure
- Billing questions
- Emergency situations`,
      rules: `- Call 24-48 hours before appointment
- Respect privacy (don't mention medical details)
- Keep calls under 2 minutes`,
    },
  },
  {
    id: 'customer-survey',
    name: 'Customer Survey',
    description: 'Collect feedback and satisfaction scores',
    category: 'Research',
    rating: 4.7,
    usageCount: 1234,
    sections: {
      role: `You are conducting a customer satisfaction survey on behalf of {{company_name}}.
Your goal is to collect honest feedback about recent experiences.`,
      personality: `Tone: Neutral, professional, and appreciative
- Thank customers for their time
- Be patient with responses
- Don't influence answers`,
      language: `Primary language: {{language}}
- Use clear, simple language for questions`,
      flow: `1. Introduction and time estimate
2. Confirm consent to proceed
3. Ask survey questions
4. Allow open feedback
5. Thank and close`,
      tools: `Available functions:
- record_survey_response(customer_id, question_id, answer)
- record_nps_score(customer_id, score)
- record_open_feedback(customer_id, feedback)`,
      safety: `Escalate when:
- Customer has a complaint to report
- Customer requests to speak with someone`,
      rules: `- Keep survey under 3 minutes
- Don't ask leading questions
- Thank customer regardless of feedback`,
    },
  },
];

const categories = ['All', 'Collections', 'Healthcare', 'Research', 'Sales', 'Support'];

export default function PromptMakerPage() {
  const [selectedTemplate, setSelectedTemplate] = useState<Template | null>(null);
  const [activeCategory, setActiveCategory] = useState('All');
  const [customPrompt, setCustomPrompt] = useState({
    role: '',
    personality: '',
    language: '',
    flow: '',
    tools: '',
    safety: '',
    rules: '',
  });
  const [activeSection, setActiveSection] = useState<keyof typeof customPrompt>('role');
  const [showPreview, setShowPreview] = useState(false);

  const sections = [
    { key: 'role' as const, label: 'Role & Objective', icon: BookOpen },
    { key: 'personality' as const, label: 'Personality & Tone', icon: MessageSquare },
    { key: 'language' as const, label: 'Language', icon: Globe },
    { key: 'flow' as const, label: 'Conversation Flow', icon: Wand2 },
    { key: 'tools' as const, label: 'Tools & Functions', icon: Wrench },
    { key: 'safety' as const, label: 'Safety & Escalation', icon: Shield },
    { key: 'rules' as const, label: 'Rules & Constraints', icon: AlertCircle },
  ];

  const applyTemplate = (template: Template) => {
    setSelectedTemplate(template);
    setCustomPrompt(template.sections);
  };

  const filteredTemplates = templates.filter(
    (t) => activeCategory === 'All' || t.category === activeCategory
  );

  const totalCharacters = Object.values(customPrompt).join('').length;

  return (
    <div className="min-h-screen">
      <Header
        title="Prompt Maker"
        description="Create optimized prompts for your voice agents"
        action={{
          label: 'Save Prompt',
          onClick: () => {},
        }}
      />

      <div className="p-6">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Templates sidebar */}
          <div className="lg:col-span-1 space-y-4">
            <div className="p-4 rounded-xl bg-card border border-border">
              <h3 className="font-semibold mb-4 flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-primary-500" />
                Templates
              </h3>

              {/* Category filter */}
              <div className="flex flex-wrap gap-2 mb-4">
                {categories.map((cat) => (
                  <button
                    key={cat}
                    onClick={() => setActiveCategory(cat)}
                    className={cn(
                      'px-2 py-1 rounded text-xs font-medium transition-colors',
                      activeCategory === cat
                        ? 'bg-primary-500 text-white'
                        : 'bg-muted hover:bg-muted/80'
                    )}
                  >
                    {cat}
                  </button>
                ))}
              </div>

              {/* Template list */}
              <div className="space-y-2">
                {filteredTemplates.map((template) => (
                  <button
                    key={template.id}
                    onClick={() => applyTemplate(template)}
                    className={cn(
                      'w-full text-left p-3 rounded-lg border transition-all',
                      selectedTemplate?.id === template.id
                        ? 'border-primary-500 bg-primary-500/5'
                        : 'border-border hover:border-primary-500/50'
                    )}
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <p className="font-medium text-sm">{template.name}</p>
                        <p className="text-xs text-muted-foreground line-clamp-2">
                          {template.description}
                        </p>
                      </div>
                      <ChevronRight className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                    </div>
                    <div className="flex items-center gap-3 mt-2">
                      <div className="flex items-center gap-1 text-xs text-muted-foreground">
                        <Star className="h-3 w-3 text-warning-500 fill-warning-500" />
                        {template.rating}
                      </div>
                      <div className="flex items-center gap-1 text-xs text-muted-foreground">
                        <FileText className="h-3 w-3" />
                        {template.usageCount}
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* Tips */}
            <div className="p-4 rounded-xl bg-card border border-border">
              <h4 className="font-medium mb-3 flex items-center gap-2">
                <Lightbulb className="h-4 w-4 text-warning-500" />
                Best Practices
              </h4>
              <ul className="space-y-2 text-xs text-muted-foreground">
                <li className="flex items-start gap-2">
                  <Check className="h-3 w-3 text-success-500 mt-0.5 flex-shrink-0" />
                  Be specific about the AI's role and boundaries
                </li>
                <li className="flex items-start gap-2">
                  <Check className="h-3 w-3 text-success-500 mt-0.5 flex-shrink-0" />
                  Define clear escalation criteria
                </li>
                <li className="flex items-start gap-2">
                  <Check className="h-3 w-3 text-success-500 mt-0.5 flex-shrink-0" />
                  Use variables for personalization
                </li>
                <li className="flex items-start gap-2">
                  <Check className="h-3 w-3 text-success-500 mt-0.5 flex-shrink-0" />
                  Include example responses
                </li>
                <li className="flex items-start gap-2">
                  <Check className="h-3 w-3 text-success-500 mt-0.5 flex-shrink-0" />
                  Test thoroughly before deployment
                </li>
              </ul>
            </div>
          </div>

          {/* Main editor */}
          <div className="lg:col-span-2 space-y-4">
            {/* Section tabs */}
            <div className="flex flex-wrap gap-2 p-2 rounded-xl bg-card border border-border">
              {sections.map((section) => (
                <button
                  key={section.key}
                  onClick={() => setActiveSection(section.key)}
                  className={cn(
                    'flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
                    activeSection === section.key
                      ? 'bg-primary-500 text-white'
                      : 'text-muted-foreground hover:text-foreground hover:bg-muted'
                  )}
                >
                  <section.icon className="h-4 w-4" />
                  {section.label}
                </button>
              ))}
            </div>

            {/* Editor */}
            <div className="p-6 rounded-xl bg-card border border-border">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="font-semibold">
                    {sections.find((s) => s.key === activeSection)?.label}
                  </h3>
                  <p className="text-sm text-muted-foreground">
                    {activeSection === 'role' && 'Define who the AI is and its main purpose'}
                    {activeSection === 'personality' && 'Set the communication style and tone'}
                    {activeSection === 'language' && 'Configure language preferences'}
                    {activeSection === 'flow' && 'Define conversation structure'}
                    {activeSection === 'tools' && 'Available actions and functions'}
                    {activeSection === 'safety' && 'Escalation and safety rules'}
                    {activeSection === 'rules' && 'Specific rules and constraints'}
                  </p>
                </div>
                <button
                  className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm bg-secondary-500/10 text-secondary-500 hover:bg-secondary-500/20 transition-colors"
                >
                  <Sparkles className="h-4 w-4" />
                  AI Generate
                </button>
              </div>

              <textarea
                value={customPrompt[activeSection]}
                onChange={(e) =>
                  setCustomPrompt((prev) => ({
                    ...prev,
                    [activeSection]: e.target.value,
                  }))
                }
                placeholder="Enter prompt content for this section..."
                rows={12}
                className={cn(
                  'w-full px-4 py-3 rounded-lg bg-background border border-border',
                  'focus:border-primary-500 focus:outline-none transition-colors',
                  'resize-y font-mono text-sm',
                  'placeholder:text-muted-foreground/50'
                )}
              />

              {/* Variables */}
              <div className="flex items-center gap-2 mt-4 flex-wrap">
                <span className="text-xs text-muted-foreground">Insert:</span>
                {[
                  '{{customer_name}}',
                  '{{company_name}}',
                  '{{language}}',
                  '{{amount}}',
                  '{{date}}',
                ].map((variable) => (
                  <button
                    key={variable}
                    onClick={() =>
                      setCustomPrompt((prev) => ({
                        ...prev,
                        [activeSection]: prev[activeSection] + variable,
                      }))
                    }
                    className="px-2 py-1 rounded text-xs font-mono bg-secondary-500/10 text-secondary-500 hover:bg-secondary-500/20 transition-colors"
                  >
                    {variable}
                  </button>
                ))}
              </div>
            </div>

            {/* Actions */}
            <div className="flex items-center justify-between p-4 rounded-xl bg-card border border-border">
              <div className="flex items-center gap-4 text-sm text-muted-foreground">
                <span>{totalCharacters.toLocaleString('en-US')} characters</span>
                <span>~{Math.ceil(totalCharacters / 4)} tokens</span>
              </div>
              <div className="flex items-center gap-2">
                <button className="flex items-center gap-2 px-4 py-2 rounded-lg bg-muted hover:bg-muted/80 text-sm font-medium transition-colors">
                  <Copy className="h-4 w-4" />
                  Copy
                </button>
                <button className="flex items-center gap-2 px-4 py-2 rounded-lg bg-secondary-500 hover:bg-secondary-600 text-white text-sm font-medium transition-colors">
                  <Play className="h-4 w-4" />
                  Test
                </button>
                <button className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary-500 hover:bg-primary-600 text-white text-sm font-medium transition-colors">
                  <Save className="h-4 w-4" />
                  Save as Template
                </button>
              </div>
            </div>
          </div>

          {/* Preview */}
          <div className="lg:col-span-1">
            <div className="sticky top-24 p-4 rounded-xl bg-card border border-border">
              <h3 className="font-semibold mb-4">Full Prompt Preview</h3>
              <div className="max-h-[600px] overflow-auto custom-scrollbar">
                <div className="p-4 rounded-lg bg-muted/30 font-mono text-xs space-y-4">
                  {sections.map((section) =>
                    customPrompt[section.key] ? (
                      <div key={section.key}>
                        <p className="text-primary-500 font-semibold mb-1">
                          ## {section.label}
                        </p>
                        <p className="whitespace-pre-wrap text-muted-foreground">
                          {customPrompt[section.key]}
                        </p>
                      </div>
                    ) : null
                  )}
                  {!Object.values(customPrompt).some((v) => v) && (
                    <p className="text-muted-foreground text-center py-8">
                      Start typing or select a template to see preview
                    </p>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
