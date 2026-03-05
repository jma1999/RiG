import React, { useRef, useEffect, useState } from 'react';
import { Send, Sparkles, Terminal, ArrowRight, Zap, Activity, AlertCircle, ChevronDown, ChevronRight, Code2, Brain } from 'lucide-react';

const SUGGESTIONS = [
  { label: "What sensors are in Office1?", icon: Activity },
  { label: "Show the overlay knowledge graph", icon: AlertCircle },
  { label: "How many spaces are on Level 1?", icon: Zap },
];

const ThinkingBlock = ({ thinking, sparqlQuery }) => {
  const [isOpen, setIsOpen] = useState(false);

  if (!thinking || thinking.length === 0) return null;

  const steps = thinking.filter(s => s.step !== 'done');
  const doneStep = thinking.find(s => s.step === 'done');

  return (
    <div className="mt-2 mb-1">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-1.5 text-[11px] text-slate-500 hover:text-slate-300 transition-colors"
      >
        <Brain size={12} className="text-nexus-accent/60" />
        <span className="font-mono">
          {doneStep ? doneStep.content : `${steps.length} reasoning steps`}
        </span>
        {isOpen ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
      </button>

      {isOpen && (
        <div className="mt-2 ml-1 pl-3 border-l border-nexus-700/50 space-y-2">
          {steps.map((step, i) => (
            <div key={i} className="text-[11px]">
              <p className="text-slate-400 font-medium">{step.title}</p>
              {step.step === 'sparql' ? (
                <pre className="mt-1 p-2 bg-nexus-900/70 rounded-md border border-nexus-700/50 text-[10px] text-emerald-400/80 font-mono overflow-x-auto whitespace-pre-wrap">
                  {step.content}
                </pre>
              ) : (
                <p className="text-slate-500">{step.content}</p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

const ChatInterface = ({ messages, onSendMessage, isLoading }) => {
  const [input, setInput] = useState('');
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const handleSend = (text = input) => {
    if (!text.trim() || isLoading) return;
    onSendMessage(text);
    setInput('');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-full bg-nexus-900 border-r border-nexus-700 relative">
      
      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto custom-scrollbar p-6 space-y-8">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col justify-center items-center text-center p-4 animate-in fade-in duration-700">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-nexus-accent to-blue-600 flex items-center justify-center mb-6 shadow-[0_0_30px_rgba(0,240,255,0.2)]">
               <Sparkles className="text-nexus-900 w-8 h-8" />
            </div>
            <h1 className="text-3xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-slate-100 to-slate-400 mb-2">
              Hello, Manager
            </h1>
            <p className="text-slate-500 mb-10 max-w-xs">
              I'm Gemino AI. Ask me anything about your facility — I'll query the knowledge graph and give you grounded answers.
            </p>
            
            <div className="grid gap-3 w-full max-w-sm">
              {SUGGESTIONS.map((s, i) => (
                <button 
                  key={i}
                  onClick={() => handleSend(s.label)}
                  className="group flex items-center justify-between p-4 rounded-xl bg-nexus-800 border border-nexus-700 hover:border-nexus-accent/50 hover:bg-nexus-700 transition-all text-left"
                >
                  <div className="flex items-center gap-3">
                    <s.icon size={18} className="text-nexus-accent opacity-70 group-hover:opacity-100" />
                    <span className="text-sm text-slate-300 group-hover:text-white">{s.label}</span>
                  </div>
                  <ArrowRight size={14} className="text-slate-500 opacity-0 -translate-x-2 group-hover:opacity-100 group-hover:translate-x-0 transition-all" />
                </button>
              ))}
            </div>
          </div>
        ) : (
          <>
            {messages.map((msg) => (
              <div key={msg.id} className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'} animate-in slide-in-from-bottom-2 duration-300`}>
                
                {/* Message Meta */}
                <div className="flex items-center gap-2 mb-1.5 px-1">
                   {msg.role === 'model' && (
                     <div className="flex items-center gap-2">
                       <Sparkles size={12} className="text-nexus-accent" />
                       <span className="text-[10px] font-bold text-nexus-accent tracking-wider uppercase">Gemino AI</span>
                     </div>
                   )}
                   {msg.role === 'user' && (
                     <span className="text-[10px] text-slate-500">You</span>
                   )}
                </div>

                {/* Bubble */}
                <div className={`max-w-[90%] relative group`}>
                   {msg.role === 'user' ? (
                     <div className="bg-nexus-700 text-slate-100 px-5 py-3.5 rounded-2xl rounded-tr-sm text-sm leading-relaxed border border-nexus-600 shadow-sm">
                        {msg.content}
                     </div>
                   ) : (
                     <div className="text-slate-300 text-sm leading-relaxed pl-1">
                        <div className="whitespace-pre-wrap">{msg.content}</div>

                        {/* Thinking/Reasoning steps */}
                        <ThinkingBlock thinking={msg.thinking} sparqlQuery={msg.sparqlQuery} />

                        <div className="flex flex-wrap gap-2 mt-3">
                          {msg.toolInvocation && (
                            <div className="flex items-center gap-2 text-xs font-mono text-slate-500 bg-nexus-800/50 py-1.5 px-3 rounded-lg border border-nexus-700/50 w-fit">
                                <Terminal size={12} />
                                <span>Action: {msg.toolInvocation}</span>
                            </div>
                          )}
                          {msg.evidenceSummary && (
                            <div className="flex items-center gap-2 text-xs font-mono text-nexus-accent/70 bg-nexus-accent/5 py-1.5 px-3 rounded-lg border border-nexus-accent/20 w-fit">
                                <Sparkles size={12} />
                                <span>GraphRAG: {msg.evidenceSummary}</span>
                            </div>
                          )}
                        </div>
                     </div>
                   )}
                </div>
              </div>
            ))}
            
            {/* Loading Indicator */}
            {isLoading && (
               <div className="flex flex-col items-start animate-pulse">
                  <div className="flex items-center gap-2 mb-1.5 px-1">
                     <Sparkles size={12} className="text-nexus-accent" />
                     <span className="text-[10px] font-bold text-nexus-accent tracking-wider uppercase">Gemino AI</span>
                  </div>
                  <div className="pl-1 space-y-1.5">
                    <div className="flex items-center gap-2 text-[11px] text-slate-500">
                      <Brain size={12} className="text-nexus-accent/60 animate-pulse" />
                      <span className="font-mono">Querying knowledge graph...</span>
                    </div>
                    <div className="flex items-center gap-1">
                       <span className="w-2 h-2 rounded-full bg-nexus-accent/50 animate-bounce"></span>
                       <span className="w-2 h-2 rounded-full bg-nexus-accent/50 animate-bounce delay-75"></span>
                       <span className="w-2 h-2 rounded-full bg-nexus-accent/50 animate-bounce delay-150"></span>
                    </div>
                  </div>
               </div>
            )}
            <div ref={endRef} className="h-4" />
          </>
        )}
      </div>

      {/* Input Area */}
      <div className="p-4 bg-nexus-900 border-t border-nexus-700">
        <div className="relative group">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask anything about your facility..."
            className="w-full bg-nexus-800/50 text-slate-200 placeholder:text-slate-500 border border-nexus-700 rounded-xl py-4 pl-5 pr-14 focus:outline-none focus:border-nexus-accent/50 focus:ring-1 focus:ring-nexus-accent/50 focus:bg-nexus-800 transition-all text-sm"
            disabled={isLoading}
          />
          <button
            onClick={() => handleSend()}
            disabled={isLoading || !input.trim()}
            className="absolute right-2 top-2 p-2 rounded-lg bg-nexus-700 text-white opacity-0 group-focus-within:opacity-100 disabled:opacity-0 hover:bg-nexus-accent hover:text-nexus-900 transition-all duration-200"
          >
            <ArrowRight size={18} />
          </button>
        </div>
        <p className="text-center text-[10px] text-slate-600 mt-3 font-mono">
           AI can make mistakes. Verify critical operations.
        </p>
      </div>
    </div>
  );
};

export default ChatInterface;
