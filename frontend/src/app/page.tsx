import Link from 'next/link';
import { Bot, ArrowRight, Phone, Brain, Zap, Shield, Globe } from 'lucide-react';

export default function Home() {
  return (
    <main className="min-h-screen bg-background">
      {/* Hero Section */}
      <div className="relative overflow-hidden">
        {/* Background gradient */}
        <div className="absolute inset-0 bg-gradient-to-br from-primary-500/10 via-transparent to-secondary-500/10" />
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[800px] bg-primary-500/20 rounded-full blur-3xl opacity-20" />

        <div className="relative max-w-7xl mx-auto px-6 py-24 lg:py-32">
          {/* Logo */}
          <div className="flex items-center gap-3 mb-12">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-primary-500 to-secondary-500">
              <Bot className="h-7 w-7 text-white" />
            </div>
            <span className="font-bold text-2xl gradient-text">VoiceAI</span>
          </div>

          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div>
              <h1 className="text-4xl lg:text-6xl font-bold tracking-tight mb-6">
                Enterprise
                <span className="gradient-text block">AI Voice Agents</span>
              </h1>
              <p className="text-xl text-muted-foreground mb-8 max-w-xl">
                Transform your outbound calling with intelligent AI agents. 
                50 concurrent calls, multi-language support, real-time transcription.
              </p>

              <div className="flex flex-col sm:flex-row gap-4">
                <Link
                  href="/dashboard"
                  className="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-primary-500 hover:bg-primary-600 text-white font-medium transition-colors"
                >
                  Open Dashboard
                  <ArrowRight className="h-5 w-5" />
                </Link>
                <Link
                  href="#features"
                  className="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-muted hover:bg-muted/80 font-medium transition-colors"
                >
                  Learn More
                </Link>
              </div>
            </div>

            {/* Feature illustration */}
            <div className="relative">
              <div className="aspect-square max-w-md mx-auto">
                {/* Animated circles */}
                <div className="absolute inset-0 flex items-center justify-center">
                  <div className="h-64 w-64 rounded-full border border-primary-500/20 animate-orbit" />
                  <div className="absolute h-48 w-48 rounded-full border border-secondary-500/20 animate-orbit" style={{ animationDuration: '8s', animationDirection: 'reverse' }} />
                  <div className="absolute h-32 w-32 rounded-full border border-accent-500/20 animate-orbit" style={{ animationDuration: '6s' }} />
                </div>

                {/* Center icon */}
                <div className="absolute inset-0 flex items-center justify-center">
                  <div className="h-24 w-24 rounded-2xl bg-gradient-to-br from-primary-500 to-secondary-500 flex items-center justify-center shadow-2xl shadow-primary-500/30">
                    <Phone className="h-12 w-12 text-white" />
                  </div>
                </div>

                {/* Floating features */}
                <div className="absolute top-8 left-8 p-3 rounded-xl bg-card border border-border shadow-lg animate-float">
                  <Brain className="h-6 w-6 text-primary-500" />
                </div>
                <div className="absolute top-8 right-8 p-3 rounded-xl bg-card border border-border shadow-lg animate-float" style={{ animationDelay: '0.5s' }}>
                  <Globe className="h-6 w-6 text-secondary-500" />
                </div>
                <div className="absolute bottom-8 left-8 p-3 rounded-xl bg-card border border-border shadow-lg animate-float" style={{ animationDelay: '1s' }}>
                  <Zap className="h-6 w-6 text-accent-500" />
                </div>
                <div className="absolute bottom-8 right-8 p-3 rounded-xl bg-card border border-border shadow-lg animate-float" style={{ animationDelay: '1.5s' }}>
                  <Shield className="h-6 w-6 text-success-500" />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Features Section */}
      <section id="features" className="py-24 bg-muted/30">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="text-3xl lg:text-4xl font-bold mb-4">
              Powerful Features
            </h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              Everything you need to run intelligent voice campaigns at scale
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            {[
              {
                icon: Phone,
                title: '50 Concurrent Calls',
                description: 'Scale your outbound campaigns with support for up to 50 simultaneous calls',
                color: 'primary',
              },
              {
                icon: Brain,
                title: 'AI-Powered Conversations',
                description: 'OpenAI Realtime API for natural, context-aware voice conversations',
                color: 'secondary',
              },
              {
                icon: Globe,
                title: 'Multi-Language',
                description: 'Support for all OpenAI-supported languages with automatic detection',
                color: 'accent',
              },
              {
                icon: Zap,
                title: 'Real-time Transcription',
                description: 'Live transcription and sentiment analysis during calls',
                color: 'success',
              },
              {
                icon: Shield,
                title: 'Human Transfer',
                description: 'Seamless escalation to human agents when needed',
                color: 'warning',
              },
              {
                icon: Bot,
                title: 'Prompt Builder',
                description: 'Visual prompt designer with templates and best practices',
                color: 'error',
              },
            ].map((feature, index) => (
              <div
                key={index}
                className="p-6 rounded-2xl bg-card border border-border hover:shadow-lg transition-all duration-300 group"
              >
                <div
                  className={`inline-flex h-12 w-12 items-center justify-center rounded-xl mb-4 bg-${feature.color}-500/10`}
                >
                  <feature.icon className={`h-6 w-6 text-${feature.color}-500`} />
                </div>
                <h3 className="text-lg font-semibold mb-2">{feature.title}</h3>
                <p className="text-muted-foreground">{feature.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-24">
        <div className="max-w-4xl mx-auto px-6 text-center">
          <h2 className="text-3xl lg:text-4xl font-bold mb-6">
            Ready to Transform Your Calling?
          </h2>
          <p className="text-lg text-muted-foreground mb-8">
            Start creating intelligent voice agents today
          </p>
          <Link
            href="/dashboard"
            className="inline-flex items-center justify-center gap-2 px-8 py-4 rounded-xl bg-gradient-to-r from-primary-500 to-secondary-500 hover:from-primary-600 hover:to-secondary-600 text-white font-medium text-lg transition-all shadow-lg shadow-primary-500/25"
          >
            Get Started
            <ArrowRight className="h-5 w-5" />
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border py-8">
        <div className="max-w-7xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <Bot className="h-5 w-5 text-primary-500" />
            <span className="font-semibold">VoiceAI Platform</span>
          </div>
          <p className="text-sm text-muted-foreground">
            © 2024 VoiceAI. All rights reserved.
          </p>
        </div>
      </footer>
    </main>
  );
}
