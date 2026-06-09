'use client';
import { useState, useEffect } from 'react';
import { Activity, DollarSign, Clock, Hash, Search, Loader2 } from 'lucide-react';

export default function AdminSidebar() {
  const [metrics, setMetrics] = useState<any>(null);
  const [resetting, setResetting] = useState(false);

  // Poll metrics every 5 seconds
  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        const res = await fetch(`${apiUrl}/api/admin/metrics`);
        if (res.ok) {
          const data = await res.json();
          setMetrics(data);
        }
      } catch (err) {
        console.error("Failed to fetch metrics", err);
      }
    };

    fetchMetrics();
    const interval = setInterval(fetchMetrics, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleResetMetrics = async () => {
    setResetting(true);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const res = await fetch(`${apiUrl}/api/admin/metrics/reset`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setMetrics(data.metrics);
      }
    } catch (err) {
      console.error("Failed to reset metrics", err);
    }
    setResetting(false);
  };

  return (
    <div className="w-80 border-r border-slate-200 bg-white min-h-full flex flex-col shadow-sm">
      <div className="p-6 border-b border-slate-100 flex-1">
        <h2 className="text-sm font-bold uppercase tracking-wider text-slate-500 mb-6">OpenTelemetry Stats</h2>

        <div className="space-y-4">
          <MetricRow icon={<Hash />} label="Policies Ingested" value={metrics?.total_policies_ingested ?? 0} />
          <MetricRow icon={<Hash />} label="Claims Processed" value={metrics?.total_claims_processed ?? 0} />
          <MetricRow icon={<Clock />} label="Total LLM Latency" value={metrics ? `${Math.round(metrics.total_llm_latency_ms)} ms` : '0 ms'} />
          <MetricRow icon={<Activity />} label="Total Tokens Used" value={metrics?.total_llm_tokens ?? 0} />
          <MetricRow icon={<DollarSign />} label="Total Est. Cost" value={metrics ? `$${metrics.total_llm_cost_usd.toFixed(5)}` : '$0.00'} />
        </div>

        <div className="mt-8 pt-6 border-t border-slate-100">
          <button
            onClick={handleResetMetrics}
            disabled={resetting}
            className="w-full bg-slate-50 hover:bg-red-50 text-slate-600 hover:text-red-600 font-semibold py-2.5 rounded-lg flex justify-center items-center space-x-2 disabled:opacity-50 transition-colors border border-slate-200 hover:border-red-200"
          >
            {resetting ? <Loader2 className="w-4 h-4 animate-spin" /> : <span>Reset Telemetry</span>}
          </button>
        </div>
      </div>
    </div>
  );
}

function MetricRow({ icon, label, value }: { icon: any, label: string, value: string | number }) {
  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center space-x-3 text-slate-600">
        <div className="w-5 h-5 text-slate-400">{icon}</div>
        <span className="text-sm font-medium">{label}</span>
      </div>
      <span className="text-sm font-bold text-slate-800">{value}</span>
    </div>
  );
}
