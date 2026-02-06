'use client';

import { cn } from '@/lib/utils';
import { useState } from 'react';
import {
  Sparkles,
  Copy,
  Wand2,
  ChevronDown,
  ChevronUp,
  Plus,
  Trash2,
  GripVertical,
  Lightbulb,
  AlertCircle,
  MessageSquare,
  Settings2,
  Wrench,
  Shield,
  BookOpen,
} from 'lucide-react';

interface PromptEditorProps {
  onChange: () => void;
}

interface PromptSection {
  id: string;
  title: string;
  description: string;
  icon: any;
  placeholder: string;
  value: string;
  expanded: boolean;
}

const initialSections: PromptSection[] = [
  {
    id: 'role',
    title: 'Role & Objective',
    description: 'Define who the AI is and its main purpose',
    icon: BookOpen,
    placeholder: `You are a professional customer service representative for [Company Name].

Your primary objective is to:
- Call customers to remind them about pending payments
- Provide clear and accurate payment information
- Assist with payment processing when requested
- Schedule callbacks if the customer is unavailable`,
    value: '',
    expanded: true,
  },
  {
    id: 'personality',
    title: 'Personality & Tone',
    description: 'Set the communication style and emotional tone',
    icon: MessageSquare,
    placeholder: `Tone: Professional yet friendly and understanding
Communication style: Clear, concise, and empathetic

Key personality traits:
- Patient and understanding of customer concerns
- Professional but not robotic
- Solution-oriented and helpful
- Respectful of customer's time

Always address the customer by name when provided.`,
    value: '',
    expanded: false,
  },
  {
    id: 'language',
    title: 'Language & Localization',
    description: 'Configure language preferences and cultural adaptations',
    icon: Settings2,
    placeholder: `Primary language: Turkish (Türkçe)
Fallback language: English

Cultural considerations:
- Use formal "siz" form unless customer prefers informal
- Respect local business hours and holidays
- Be aware of cultural sensitivities around financial topics`,
    value: '',
    expanded: false,
  },
  {
    id: 'flow',
    title: 'Conversation Flow',
    description: 'Define the structure and stages of the conversation',
    icon: Wand2,
    placeholder: `Opening:
1. Greet the customer warmly
2. Introduce yourself and the company
3. State the purpose of the call briefly

Main conversation:
1. Verify customer identity (last 4 digits of ID or phone)
2. Provide payment details (amount, due date)
3. Ask if they can make the payment today
4. If yes: Guide through payment options
5. If no: Understand the reason and offer solutions

Closing:
1. Summarize any agreements or next steps
2. Thank the customer for their time
3. Provide contact information for follow-up`,
    value: '',
    expanded: false,
  },
  {
    id: 'tools',
    title: 'Tools & Functions',
    description: 'Define available actions the AI can take',
    icon: Wrench,
    placeholder: `Available functions:
1. get_customer_info(phone_number) - Retrieve customer details
2. get_payment_status(customer_id) - Check payment status
3. create_payment_promise(customer_id, date, amount) - Record payment promise
4. schedule_callback(customer_id, datetime, notes) - Schedule follow-up call
5. transfer_to_human(reason) - Transfer to human agent

Use these functions when:
- Customer needs specific account information
- Customer agrees to make a payment
- Customer requests to speak with a human`,
    value: '',
    expanded: false,
  },
  {
    id: 'safety',
    title: 'Safety & Escalation',
    description: 'Set boundaries and escalation rules',
    icon: Shield,
    placeholder: `Escalate to human agent when:
- Customer explicitly requests to speak with a human
- Customer is angry or upset after 2 de-escalation attempts
- Customer has complex account issues requiring investigation
- Customer disputes the debt validity

Never:
- Threaten or use aggressive language
- Provide legal advice
- Make promises outside your authority
- Share information with unauthorized persons
- Continue if customer refuses to speak`,
    value: '',
    expanded: false,
  },
  {
    id: 'rules',
    title: 'Rules & Constraints',
    description: 'Define specific rules and limitations',
    icon: AlertCircle,
    placeholder: `Strict rules:
1. Always verify customer identity before discussing account details
2. Maximum call duration: 5 minutes
3. Maximum retry attempts: 3 per day
4. Do not call before 9 AM or after 8 PM local time
5. Record all payment promises in the system
6. Never share full account numbers verbally

Compliance requirements:
- Follow KVKK data protection regulations
- Announce that the call may be recorded
- Respect customer's right to opt-out`,
    value: '',
    expanded: false,
  },
];

const quickInserts = [
  { label: '{{customer_name}}', description: 'Customer name' },
  { label: '{{payment_amount}}', description: 'Payment amount' },
  { label: '{{due_date}}', description: 'Due date' },
  { label: '{{company_name}}', description: 'Company name' },
  { label: '{{agent_name}}', description: 'Agent name' },
];

export function PromptEditor({ onChange }: PromptEditorProps) {
  const [sections, setSections] = useState<PromptSection[]>(initialSections);
  const [showAISuggestions, setShowAISuggestions] = useState(false);

  const toggleSection = (id: string) => {
    setSections((prev) =>
      prev.map((section) =>
        section.id === id ? { ...section, expanded: !section.expanded } : section
      )
    );
  };

  const updateSectionValue = (id: string, value: string) => {
    setSections((prev) =>
      prev.map((section) =>
        section.id === id ? { ...section, value } : section
      )
    );
    onChange();
  };

  const insertVariable = (variable: string, sectionId: string) => {
    const textarea = document.getElementById(`prompt-${sectionId}`) as HTMLTextAreaElement;
    if (textarea) {
      const start = textarea.selectionStart;
      const end = textarea.selectionEnd;
      const currentValue = sections.find((s) => s.id === sectionId)?.value || '';
      const newValue = currentValue.substring(0, start) + variable + currentValue.substring(end);
      updateSectionValue(sectionId, newValue);
    }
  };

  const totalCharacters = sections.reduce((acc, s) => acc + (s.value?.length || 0), 0);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
      {/* Main editor */}
      <div className="lg:col-span-3 space-y-4">
        {/* Toolbar */}
        <div className="flex items-center justify-between p-4 rounded-xl bg-card border border-border">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setShowAISuggestions(!showAISuggestions)}
              className={cn(
                'flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors',
                showAISuggestions
                  ? 'bg-primary-500 text-white'
                  : 'bg-primary-500/10 text-primary-500 hover:bg-primary-500/20'
              )}
            >
              <Sparkles className="h-4 w-4" />
              AI Suggestions
            </button>
            <button
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium bg-muted hover:bg-muted/80 transition-colors"
            >
              <Wand2 className="h-4 w-4" />
              Auto-Generate
            </button>
          </div>
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <span>{totalCharacters.toLocaleString('en-US')} characters</span>
          </div>
        </div>

        {/* Sections */}
        <div className="space-y-3">
          {sections.map((section, index) => (
            <div
              key={section.id}
              className={cn(
                'rounded-xl border border-border bg-card overflow-hidden',
                'transition-all duration-200'
              )}
            >
              {/* Section header */}
              <button
                onClick={() => toggleSection(section.id)}
                className="flex items-center justify-between w-full p-4 hover:bg-muted/50 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary-500/10">
                    <section.icon className="h-4 w-4 text-primary-500" />
                  </div>
                  <div className="text-left">
                    <p className="font-medium">{section.title}</p>
                    <p className="text-sm text-muted-foreground">
                      {section.description}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {section.value && (
                    <span className="text-xs text-muted-foreground">
                      {section.value.length} chars
                    </span>
                  )}
                  {section.expanded ? (
                    <ChevronUp className="h-5 w-5 text-muted-foreground" />
                  ) : (
                    <ChevronDown className="h-5 w-5 text-muted-foreground" />
                  )}
                </div>
              </button>

              {/* Section content */}
              {section.expanded && (
                <div className="px-4 pb-4">
                  <textarea
                    id={`prompt-${section.id}`}
                    value={section.value}
                    onChange={(e) => updateSectionValue(section.id, e.target.value)}
                    placeholder={section.placeholder}
                    rows={8}
                    className={cn(
                      'w-full px-4 py-3 rounded-lg bg-background border border-border',
                      'focus:border-primary-500 focus:outline-none transition-colors',
                      'resize-y font-mono text-sm',
                      'placeholder:text-muted-foreground/50'
                    )}
                  />

                  {/* Quick inserts */}
                  <div className="flex items-center gap-2 mt-3 flex-wrap">
                    <span className="text-xs text-muted-foreground">Insert:</span>
                    {quickInserts.map((item) => (
                      <button
                        key={item.label}
                        onClick={() => insertVariable(item.label, section.id)}
                        className={cn(
                          'px-2 py-1 rounded text-xs font-mono',
                          'bg-secondary-500/10 text-secondary-500 hover:bg-secondary-500/20',
                          'transition-colors'
                        )}
                        title={item.description}
                      >
                        {item.label}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Sidebar */}
      <div className="space-y-4">
        {/* Tips */}
        <div className="p-4 rounded-xl bg-card border border-border">
          <div className="flex items-center gap-2 mb-3">
            <Lightbulb className="h-5 w-5 text-warning-500" />
            <h3 className="font-medium">Best Practices</h3>
          </div>
          <ul className="space-y-2 text-sm text-muted-foreground">
            <li className="flex items-start gap-2">
              <span className="text-primary-500">•</span>
              Be specific about the AI's role and boundaries
            </li>
            <li className="flex items-start gap-2">
              <span className="text-primary-500">•</span>
              Define clear escalation criteria
            </li>
            <li className="flex items-start gap-2">
              <span className="text-primary-500">•</span>
              Use variables for personalization
            </li>
            <li className="flex items-start gap-2">
              <span className="text-primary-500">•</span>
              Include example responses when helpful
            </li>
            <li className="flex items-start gap-2">
              <span className="text-primary-500">•</span>
              Test thoroughly before deployment
            </li>
          </ul>
        </div>

        {/* Templates */}
        <div className="p-4 rounded-xl bg-card border border-border">
          <h3 className="font-medium mb-3">Quick Templates</h3>
          <div className="space-y-2">
            {[
              'Payment Reminder',
              'Appointment Confirmation',
              'Customer Survey',
              'Lead Qualification',
            ].map((template) => (
              <button
                key={template}
                className={cn(
                  'w-full text-left px-3 py-2 rounded-lg text-sm',
                  'hover:bg-muted transition-colors'
                )}
              >
                {template}
              </button>
            ))}
          </div>
        </div>

        {/* Preview */}
        <div className="p-4 rounded-xl bg-card border border-border">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-medium">Preview</h3>
            <button className="text-sm text-primary-500 hover:text-primary-600">
              <Copy className="h-4 w-4" />
            </button>
          </div>
          <div className="p-3 rounded-lg bg-muted/50 text-xs font-mono max-h-48 overflow-auto custom-scrollbar">
            {sections
              .filter((s) => s.value)
              .map((s) => (
                <div key={s.id} className="mb-2">
                  <span className="text-primary-500">## {s.title}</span>
                  <br />
                  {s.value.substring(0, 100)}
                  {s.value.length > 100 && '...'}
                </div>
              ))}
            {!sections.some((s) => s.value) && (
              <span className="text-muted-foreground">
                Start typing to see preview...
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
