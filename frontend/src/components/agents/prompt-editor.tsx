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
    title: 'Personality',
    description: 'Define who the agent is and its character traits',
    icon: BookOpen,
    placeholder: `You are a customer representative for [Company Name].

Character traits:
- Professional and trustworthy
- Friendly but maintains formal boundaries
- Solution-oriented and patient`,
    value: '',
    expanded: true,
  },
  {
    id: 'personality',
    title: 'Environment',
    description: 'Define the context and environment conditions of the conversation',
    icon: Settings2,
    placeholder: `- Phone customer conversation
- Customer is being called for the first time
- Product/service introduction and registration will be done
- Customer's basic information may be available in the system`,
    value: '',
    expanded: false,
  },
  {
    id: 'language',
    title: 'Tone',
    description: 'Set conversation tone, response length and language preferences',
    icon: MessageSquare,
    placeholder: `- Use a warm, professional and concise tone
- Keep each response to 1-2 sentences. This step is important.
- Don't repeat the same confirmation phrases, vary them
- Speak in the configured language
- Address the customer formally`,
    value: '',
    expanded: false,
  },
  {
    id: 'flow',
    title: 'Goal',
    description: 'Define the workflow and goals with numbered steps',
    icon: Wand2,
    placeholder: `1. Greet the customer and introduce yourself
2. Briefly explain the purpose of the call
3. Ask questions to understand the customer's needs. This step is important.
4. Present the appropriate solution and explain details
5. Answer the customer's questions
6. Determine and confirm next steps
7. Thank and close the conversation`,
    value: '',
    expanded: false,
  },
  {
    id: 'safety',
    title: 'Guardrails',
    description: 'Strict rules and restrictions (the model pays extra attention to this section)',
    icon: Shield,
    placeholder: `- Never provide information on out-of-scope topics. This step is important.
- Do not share customer information with third parties
- Do not make negative comments about competitors
- Do not present uncertain information as fact
- When audio is unclear: "Sorry, I didn't quite catch that. Could you repeat?"
- If customer is aggressive or threatening, transfer to human`,
    value: '',
    expanded: false,
  },
  {
    id: 'tools',
    title: 'Tools',
    description: 'Define available tools in When/Parameters/Usage/Error handling format',
    icon: Wrench,
    placeholder: `## save_customer_info
**When to use:** When customer information needs to be saved
**Parameters:** name (full name), phone (phone number), email (email address)
**Usage:**
1. Get the information from the customer
2. Repeat and verify the information
3. Call the tool
**Error handling:** If save fails, ask customer for the information again

## transfer_to_human
**When to use:** When customer requests a human agent or issue can't be resolved after 2 attempts
**Parameters:** reason (transfer reason)
**Usage:**
1. Inform the customer about the transfer
2. Call the tool
**Error handling:** If transfer fails, ask the customer to wait`,
    value: '',
    expanded: false,
  },
  {
    id: 'rules',
    title: 'Character Normalization',
    description: 'Define voice-to-text and text-to-voice format conversion rules',
    icon: AlertCircle,
    placeholder: `Voice ↔ Written format rules:
- Email: "a-t" → "@", "dot" → "."
  Example: "john at gmail dot com" → "john@gmail.com"
- Phone: "five five four" → "554"
  Example: "five zero five three twenty" → "505320"
- Currency: "one thousand two hundred fifty dollars" → "$1,250"
- Dates: "January fifteenth" → "January 15"`,
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
