
import React, { useState } from 'react';
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, ResponsiveContainer, PolarRadiusAxis } from 'recharts';
import { AssessmentData, DomainAnalysis } from './types';
import { CEFR_LEVELS, COLORS } from './constants.tsx';

const assessmentData: AssessmentData = {
  "session_id": "9aead39e-e3bf-43ee-8ad2-5fe97029cfff",
  "timestamp": "2026-01-29T14:59:40.433116",
  "report": {
    "proficiency_level": "B1 (Intermediate)",
    "ceiling_phase": "Probe",
    "ceiling_analysis": "The breakdown occurred during the Probe phase, specifically when discussing the impact of social media on communication.",
    "domain_analyses": [
      {
        "domain": "Fluency",
        "rating": 4,
        "observation": "The student demonstrates good fluency with minimal hesitation. Responses are generally coherent.",
        "evidence": "“저는 사람에 따라서 다 다르다고 생각을 하고요...”"
      },
      {
        "domain": "Grammar",
        "rating": 3,
        "observation": "Some grammatical inaccuracies are present, particularly in complex sentence structures.",
        "evidence": "“굳이 하나를 뽑자면 대면 근무하는 것이 사무실에서 좋다고 생각합니다.”"
      },
      {
        "domain": "Lexical",
        "rating": 3,
        "observation": "The student uses appropriate vocabulary but occasionally resorts to generic terms.",
        "evidence": "“그렇게 쓰고 싶은데가 없어서 아내가 원하는 것들 사주거나...”"
      },
      {
        "domain": "Phonology",
        "rating": 4,
        "observation": "Pronunciation is clear, with minor issues that do not impede understanding.",
        "evidence": "“부산 스타일의 국밥이었고 가격도 싸고 굉장히 맛있어서...”"
      },
      {
        "domain": "Coherence",
        "rating": 3,
        "observation": "Ideas are generally linked, but transitions could be smoother, especially in more complex ideas.",
        "evidence": "“특히 팀 단위로 일할 때는 대면하면서 부딪히면서 일하는 것이...”"
      }
    ],
    "starting_module": "Module focusing on complex sentence structures and abstract vocabulary.",
    "optimization_strategy": "Implement a 'Shadowing' exercise where the student listens to and repeats complex sentences from native speakers, focusing on structure and vocabulary precision."
  },
  "verbal_summary": "Based on our conversation, I've assessed your Korean proficiency at B1 (Intermediate) level.",
  "conversation_length": 18
};

const Header: React.FC<{ sessionId: string; timestamp: string }> = ({ sessionId, timestamp }) => (
  <header className="mb-8 md:mb-12 flex flex-col md:flex-row md:items-end justify-between border-b border-white/10 pb-6">
    <div>
      <h1 className="text-2xl md:text-4xl font-bold tracking-tight text-white mb-2">Proficiency Report</h1>
      <p className="text-violet-400 font-medium text-sm md:text-base">Korean Assessment • {new Date(timestamp).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}</p>
    </div>
    <div className="mt-2 md:mt-0 text-[10px] md:text-sm text-slate-500 font-mono">
      REF: {sessionId.split('-')[0]}
    </div>
  </header>
);

const BadgeSection: React.FC<{ level: string }> = ({ level }) => {
  const shortLevel = level.split(' ')[0];
  const levelIndex = CEFR_LEVELS.findIndex(l => shortLevel === l);

  return (
    <div className="flex flex-col items-center bg-card rounded-3xl p-6 md:p-10 border border-white/5 shadow-2xl relative overflow-hidden">
      <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-blue-600 to-violet-500"></div>
      <div className="relative group mb-4">
        <div className="absolute -inset-2 md:-inset-4 bg-violet-600/30 rounded-full blur-xl md:blur-2xl transition duration-1000"></div>
        <div className="relative w-28 h-28 md:w-40 md:h-40 rounded-full bg-slate-900 border-2 border-violet-500/50 flex items-center justify-center flex-col shadow-[0_0_20px_rgba(139,92,246,0.2)]">
          <span className="text-5xl md:text-7xl font-black text-transparent bg-clip-text bg-gradient-to-br from-white to-violet-400">
            {shortLevel}
          </span>
        </div>
      </div>
      <div className="text-center">
        <h3 className="text-base md:text-xl font-semibold text-white tracking-wide uppercase">{level}</h3>
      </div>
      
      <div className="w-full mt-6 space-y-3">
         <div className="flex justify-between px-1">
          {CEFR_LEVELS.map((lvl, idx) => (
            <span key={lvl} className={`text-[10px] font-bold ${idx === levelIndex ? 'text-violet-400 scale-110' : 'text-slate-600'}`}>
              {lvl}
            </span>
          ))}
        </div>
        <div className="relative h-1 bg-white/5 rounded-full overflow-hidden">
          <div 
            className="absolute h-full bg-violet-500 transition-all duration-1000 ease-out"
            style={{ width: `${((levelIndex + 1) / CEFR_LEVELS.length) * 100}%` }}
          />
        </div>
      </div>
    </div>
  );
};

const IntegratedSkillSection: React.FC<{ domains: DomainAnalysis[] }> = ({ domains }) => {
  const [expandedDomain, setExpandedDomain] = useState<string | null>(null);

  const chartData = domains.map(d => ({
    subject: d.domain,
    A: d.rating,
    fullMark: 5,
  }));

  const toggleDomain = (domain: string) => {
    setExpandedDomain(expandedDomain === domain ? null : domain);
  };

  return (
    <div className="bg-card rounded-3xl p-4 md:p-8 border border-white/5 shadow-2xl">
      <div className="flex items-center gap-3 mb-6 px-2">
        <div className="w-1.5 h-6 bg-violet-500 rounded-full"></div>
        <h3 className="text-lg font-bold text-white uppercase tracking-wider">Skill Analysis</h3>
      </div>

      <div className="w-full h-[280px] md:h-[350px] mb-8">
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart cx="50%" cy="50%" outerRadius="80%" data={chartData}>
            <PolarGrid stroke="#ffffff15" />
            <PolarAngleAxis dataKey="subject" tick={{ fill: '#94A3B8', fontSize: 11, fontWeight: 500 }} />
            <PolarRadiusAxis angle={30} domain={[0, 5]} tick={false} axisLine={false} />
            <Radar
              name="Student"
              dataKey="A"
              stroke={COLORS.neonViolet}
              fill={COLORS.violet}
              fillOpacity={0.25}
            />
          </RadarChart>
        </ResponsiveContainer>
      </div>

      <div className="space-y-3">
        {domains.map((analysis) => {
          const isExpanded = expandedDomain === analysis.domain;
          return (
            <div 
              key={analysis.domain}
              onClick={() => toggleDomain(analysis.domain)}
              className={`cursor-pointer transition-all duration-300 rounded-2xl border ${
                isExpanded 
                  ? 'bg-violet-500/10 border-violet-500/40 p-5' 
                  : 'bg-white/5 border-white/5 p-4 hover:bg-white/10'
              }`}
            >
              <div className="flex justify-between items-center">
                <div className="flex items-center gap-3">
                  <span className={`text-sm font-bold tracking-wide transition-colors ${isExpanded ? 'text-violet-400' : 'text-slate-200'}`}>
                    {analysis.domain}
                  </span>
                  <div className="flex gap-0.5">
                    {[1, 2, 3, 4, 5].map((s) => (
                      <div 
                        key={s} 
                        className={`w-3 h-0.5 rounded-full ${s <= analysis.rating ? (isExpanded ? 'bg-violet-400' : 'bg-violet-500/60') : 'bg-white/10'}`} 
                      />
                    ))}
                  </div>
                </div>
                <div className={`transition-transform duration-300 ${isExpanded ? 'rotate-180 text-violet-400' : 'text-slate-500'}`}>
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </div>
              </div>

              {isExpanded && (
                <div className="mt-4 animate-in fade-in slide-in-from-top-2 duration-300">
                  <p className="text-slate-300 text-sm leading-relaxed mb-4">{analysis.observation}</p>
                  <div className="bg-black/30 p-3 rounded-xl border-l-2 border-violet-500/50">
                    <p className="text-[10px] text-slate-500 mb-1 uppercase font-bold tracking-[0.2em]">Live Evidence</p>
                    <p className="text-slate-200 text-sm font-['Noto_Sans_KR'] leading-relaxed">{analysis.evidence}</p>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

const StrategySection: React.FC<{ strategy: string; module: string }> = ({ strategy, module }) => (
  <div className="mt-8 group">
    <div className="relative overflow-hidden bg-gradient-to-br from-violet-900/30 to-slate-900 rounded-3xl p-6 md:p-10 border border-violet-500/20 shadow-xl">
      <div className="relative z-10">
        <span className="inline-block px-3 py-1 rounded-full bg-violet-600/20 text-violet-300 text-[9px] font-black uppercase tracking-widest mb-4 border border-violet-500/30">
          Optimization Focus
        </span>
        <h2 className="text-xl md:text-3xl font-bold text-white mb-4">Recommended Strategy</h2>
        <p className="text-base md:text-lg text-slate-300 leading-relaxed mb-8">
          {strategy}
        </p>
        
        <div className="flex flex-col md:flex-row gap-6 items-start md:items-center pt-6 border-t border-white/5">
          <div className="flex-1">
            <p className="text-[10px] text-violet-400 font-bold uppercase tracking-widest mb-1">Target Curriculum</p>
            <p className="text-slate-300 text-sm md:text-base font-medium">{module}</p>
          </div>
          <button className="w-full md:w-auto px-6 py-3 rounded-xl bg-violet-600 text-white font-bold hover:bg-violet-500 transition-all shadow-lg shadow-violet-600/20 active:scale-95">
            Begin Path
          </button>
        </div>
      </div>
    </div>
  </div>
);

const App: React.FC = () => {
  return (
    <div className="min-h-screen pb-12 pt-6 px-4 md:px-8 max-w-4xl mx-auto selection:bg-violet-500/30">
      <Header sessionId={assessmentData.session_id} timestamp={assessmentData.timestamp} />

      <main className="space-y-6 md:space-y-8">
        <div className="grid grid-cols-1 md:grid-cols-12 gap-6 md:gap-8">
          <div className="md:col-span-5">
            <BadgeSection level={assessmentData.report.proficiency_level} />
            
            {/* Ceiling Analysis (Compact) */}
            <div className="mt-6 bg-white/5 rounded-3xl p-6 border border-white/5">
              <div className="flex items-center gap-2 mb-3">
                <span className="text-[10px] font-bold text-blue-400 bg-blue-400/10 px-2 py-0.5 rounded border border-blue-400/20">CEILING: {assessmentData.report.ceiling_phase}</span>
              </div>
              <p className="text-slate-400 text-sm italic leading-relaxed">
                "{assessmentData.report.ceiling_analysis}"
              </p>
            </div>
          </div>
          
          <div className="md:col-span-7">
            <IntegratedSkillSection domains={assessmentData.report.domain_analyses} />
          </div>
        </div>

        <StrategySection 
          strategy={assessmentData.report.optimization_strategy} 
          module={assessmentData.report.starting_module} 
        />

        <footer className="pt-8 text-center text-slate-600 text-[10px] uppercase tracking-widest">
          <p>Seoul Night • Language Assessment Engine</p>
        </footer>
      </main>
    </div>
  );
};

export default App;
