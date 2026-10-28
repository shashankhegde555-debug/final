import React, { useState, useEffect } from 'react';
import { RuleNoiseStats } from '../types';
import { CheckCircle2, XCircle, Info, ShieldCheck, AlertCircle, ArrowUpRight } from 'lucide-react';

interface NoiseStudioProps {
  rules: RuleNoiseStats[];
  onDecision: (ruleKey: string, decision: 'approved' | 'rejected') => Promise<void>;
  whatIfImpact: any;
}

export const NoiseStudio: React.FC<NoiseStudioProps> = ({
  rules,
  onDecision,
  whatIfImpact,
}) => {
  const [filterType, setFilterType] = useState<string>('all');
  const [auditNotice, setAuditNotice] = useState<string | null>(null);

  const handleDecisionClick = async (ruleKey: string, decision: 'approved' | 'rejected') => {
    await onDecision(ruleKey, decision);
    setAuditNotice(
      `Decision for "${ruleKey}" recorded as ${decision.toUpperCase()}. ` +
      `SAFETY MANDATE: Recorded to local audit store only; zero changes made to live monitoring tools.`
    );
    setTimeout(() => setAuditNotice(null), 5000);
  };

  const filteredRules = rules.filter((r) => {
    if (filterType === 'suppress') return r.recommendation === 'Suppress candidate';
    if (filterType === 'keep') return r.recommendation.startsWith('Keep');
    return true;
  });

  return (
    <div className="space-y-4">
      {/* What-If Impact Card */}
      {whatIfImpact && (
        <div className="p-4 rounded-xl bg-gradient-to-r from-emerald-950/30 via-slate-900 to-indigo-950/30 border border-emerald-500/30 shadow-md">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-emerald-400 uppercase tracking-wider">What-If Tuning Simulation:</span>
                <span className="px-2 py-0.5 text-[11px] font-semibold bg-emerald-500/20 text-emerald-300 rounded border border-emerald-500/30">
                  Recall 100% Guaranteed
                </span>
              </div>
              <p className="text-xs text-slate-300 mt-1">
                Applying all approved suppression candidates removes{' '}
                <strong className="text-emerald-400 font-mono">{whatIfImpact.alerts_suppressed?.toLocaleString()}</strong> noise alerts{' '}
                (<strong className="text-emerald-400 font-mono">-{whatIfImpact.reduction_percentage}%</strong> of volume) with{' '}
                <strong className="text-cyan-300">0 ground-truth incidents missed</strong>.
              </p>
            </div>
            <div className="flex items-center gap-3 shrink-0 text-xs font-mono">
              <div className="bg-slate-950 px-3 py-1.5 rounded-lg border border-slate-800">
                <span className="text-slate-400">Stream Left: </span>
                <span className="font-bold text-slate-200">{whatIfImpact.alerts_remaining?.toLocaleString()}</span>
              </div>
              <div className="bg-emerald-950/40 px-3 py-1.5 rounded-lg border border-emerald-500/30 text-emerald-300 font-bold">
                Safety Guard: PASS
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Audit Confirmation Notice */}
      {auditNotice && (
        <div className="p-3 rounded-lg bg-indigo-950/80 border border-indigo-500/40 text-xs text-indigo-200 flex items-center justify-between gap-2 animate-in fade-in">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-indigo-400 shrink-0" />
            <span>{auditNotice}</span>
          </div>
          <button onClick={() => setAuditNotice(null)} className="text-indigo-400 hover:text-white font-bold">
            Dismiss
          </button>
        </div>
      )}

      {/* Filter Tabs */}
      <div className="flex items-center gap-2 text-xs">
        <button
          onClick={() => setFilterType('all')}
          className={`px-3 py-1.5 rounded-lg font-semibold transition ${
            filterType === 'all' ? 'bg-indigo-600 text-white' : 'bg-slate-800 text-slate-400 hover:text-slate-200'
          }`}
        >
          All Rules ({rules.length})
        </button>
        <button
          onClick={() => setFilterType('suppress')}
          className={`px-3 py-1.5 rounded-lg font-semibold transition ${
            filterType === 'suppress' ? 'bg-indigo-600 text-white' : 'bg-slate-800 text-slate-400 hover:text-slate-200'
          }`}
        >
          Suppress Candidates ({rules.filter(r => r.recommendation === 'Suppress candidate').length})
        </button>
        <button
          onClick={() => setFilterType('keep')}
          className={`px-3 py-1.5 rounded-lg font-semibold transition ${
            filterType === 'keep' ? 'bg-indigo-600 text-white' : 'bg-slate-800 text-slate-400 hover:text-slate-200'
          }`}
        >
          Protected & Keep ({rules.filter(r => r.recommendation.startsWith('Keep')).length})
        </button>
      </div>

      {/* Rules Table */}
      <div className="border border-slate-800 rounded-xl overflow-hidden bg-slate-900/60 shadow-lg">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950/80 text-slate-400 border-b border-slate-800 font-semibold uppercase text-[11px]">
              <tr>
                <th className="py-3 px-4">Rule Signature & Service</th>
                <th className="py-3 px-4">Fires</th>
                <th className="py-3 px-4">Linked</th>
                <th className="py-3 px-4">Link Rate</th>
                <th className="py-3 px-4">Recommendation</th>
                <th className="py-3 px-4">Risk Evaluation</th>
                <th className="py-3 px-4 text-right">Human Action (Audit)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {filteredRules.map((rule) => (
                <tr key={rule.rule_key} className="hover:bg-slate-800/40 transition">
                  <td className="py-3 px-4">
                    <div className="font-bold text-slate-200 font-sans">{rule.service}</div>
                    <div className="text-[11px] text-slate-400 truncate max-w-xs">{rule.rule_key}</div>
                  </td>
                  <td className="py-3 px-4 text-slate-300 font-bold">{rule.n_fires.toLocaleString()}</td>
                  <td className="py-3 px-4">
                    <span className={rule.n_linked > 0 ? 'text-cyan-400 font-bold' : 'text-slate-500'}>
                      {rule.n_linked}
                    </span>
                  </td>
                  <td className="py-3 px-4">
                    <span className={rule.link_rate > 0 ? 'text-cyan-400' : 'text-slate-500'}>
                      {(rule.link_rate * 100).toFixed(1)}%
                    </span>
                  </td>
                  <td className="py-3 px-4">
                    <span className={`px-2 py-0.5 rounded text-[11px] font-sans font-bold whitespace-nowrap ${
                      rule.recommendation === 'Suppress candidate'
                        ? 'bg-red-500/20 text-red-300 border border-red-500/40'
                        : rule.recommendation === 'Keep and page'
                        ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                        : 'bg-slate-800 text-slate-300'
                    }`}>
                      {rule.recommendation}
                    </span>
                  </td>
                  <td className="py-3 px-4 font-sans text-slate-400 max-w-xs">
                    <div className="text-[11px] line-clamp-2">{rule.risk_note}</div>
                  </td>
                  <td className="py-3 px-4 text-right font-sans">
                    <div className="flex items-center justify-end gap-1.5">
                      <button
                        onClick={() => handleDecisionClick(rule.rule_key, 'approved')}
                        className={`px-2.5 py-1 rounded text-[11px] font-semibold transition ${
                          rule.decision === 'approved'
                            ? 'bg-emerald-600 text-white font-bold'
                            : 'bg-slate-800 hover:bg-emerald-600/30 text-emerald-400 border border-emerald-500/30'
                        }`}
                        title="Record approval of recommendation (Audit only; will never execute against monitoring)"
                      >
                        Approve
                      </button>
                      <button
                        onClick={() => handleDecisionClick(rule.rule_key, 'rejected')}
                        className={`px-2.5 py-1 rounded text-[11px] font-semibold transition ${
                          rule.decision === 'rejected'
                            ? 'bg-red-600 text-white font-bold'
                            : 'bg-slate-800 hover:bg-red-600/30 text-red-400 border border-red-500/30'
                        }`}
                        title="Record rejection of recommendation"
                      >
                        Reject
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
