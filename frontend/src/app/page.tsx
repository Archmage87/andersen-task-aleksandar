'use client';
import { useState } from 'react';
import UploadZone from '@/components/UploadZone';
import SettlementTable from '@/components/SettlementTable';
import AdminSidebar from '@/components/AdminSidebar';
import { ShieldCheck, Activity, BrainCircuit, Loader2 } from 'lucide-react';

export default function Dashboard() {
  const [policyRules, setPolicyRules] = useState<any>(null);
  const [settlement, setSettlement] = useState<any>(null);
  const [claimsUploaded, setClaimsUploaded] = useState(false);
  const [calculating, setCalculating] = useState(false);

  const handleRemoveData = async (type: "policy" | "claims") => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      await fetch(`${apiUrl}/api/clear-data?type=${type}`, { method: 'POST' });
      
      if (type === "policy") {
        setPolicyRules(null);
        setSettlement(null);
      } else {
        setClaimsUploaded(false);
        setSettlement(null);
      }
    } catch (err) {
      console.error("Failed to clear data:", err);
    }
  };

  const triggerCalculate = async () => {
    setCalculating(true);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const res = await fetch(`${apiUrl}/api/adjudicate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ policy: policyRules, scenario_file_id: "uploaded" })
      });
      const result = await res.json();
      setTimeout(() => {
        setSettlement(result);
        setCalculating(false);
      }, 400);
    } catch (err) {
      console.error(err);
      setCalculating(false);
    }
  };

  return (
    <div className="h-screen bg-slate-50 font-sans selection:bg-teal-200 flex flex-col overflow-hidden">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-10 shadow-sm">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="bg-teal-600 p-2 rounded-lg">
              <ShieldCheck className="w-5 h-5 text-white" />
            </div>
            <h1 className="text-xl font-bold text-slate-800 tracking-tight">
              Anderesen <span className="text-teal-600 font-medium">Claims Service</span>
            </h1>
          </div>
        </div>
      </header>

      {/* App Body Split */}
      <div className="flex flex-1 overflow-hidden">
        <AdminSidebar />

        {/* Main Content */}
        <main className="flex-1 overflow-y-auto px-8 md:px-12 py-12 space-y-12">

          {/* Intro Section */}
          <section className="text-center max-w-2xl mx-auto space-y-4">
            <h2 className="text-3xl md:text-4xl font-extrabold text-slate-800 tracking-tight">
              Automated <span className="text-transparent bg-clip-text bg-gradient-to-r from-teal-600 to-cyan-600">Claims Processing</span>
            </h2>
            <p className="text-lg text-slate-600">
              Update insurance policy, update claims and cross reference to calculate amount covered by insurance.
            </p>
          </section>

          {/* Upload Grid */}
          <section className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
              <div className="flex items-center space-x-2 mb-4">
                <div className="bg-blue-100 p-1.5 rounded-md"><Activity className="w-4 h-4 text-blue-700" /></div>
                <h3 className="font-semibold text-slate-800">1. Ingest Policy Document</h3>
              </div>
              <UploadZone
                label="Upload Policy (PDF/TXT)"
                accept=".pdf,.txt"
                endpoint="/api/ingest-policy"
                onUploadSuccess={(data) => setPolicyRules(data.rules)}
                onRemove={() => handleRemoveData("policy")}
              />
            </div>

            <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
              <div className="flex items-center space-x-2 mb-4">
                <div className="bg-indigo-100 p-1.5 rounded-md"><BrainCircuit className="w-4 h-4 text-indigo-700" /></div>
                <h3 className="font-semibold text-slate-800">2. Ingest Claims Scenario</h3>
              </div>
              <UploadZone
                label="Upload Claims (PDF/CSV)"
                accept=".pdf,.csv,.json"
                endpoint="/api/ingest-claims"
                onUploadSuccess={() => setClaimsUploaded(true)}
                onRemove={() => handleRemoveData("claims")}
              />
            </div>
          </section>

          {/* Action Panel */}
          {policyRules && claimsUploaded && !settlement && (
            <section className="bg-gradient-to-r from-slate-800 to-slate-900 rounded-2xl p-8 shadow-xl text-white flex flex-col md:flex-row items-center justify-between animate-in fade-in slide-in-from-bottom-4 duration-500 border border-slate-700">
              <div className="mb-6 md:mb-0">
                <h3 className="text-xl font-bold flex items-center space-x-2">
                  <CheckCircle className="w-6 h-6 text-emerald-400" />
                  <span>Ready for Processing</span>
                </h3>
                <p className="text-slate-300 mt-2 text-sm max-w-md">
                  Policy rules parsed ({policyRules.plan_name}). Claims scenario cached. Start validation process.
                </p>
              </div>
              <button
                onClick={triggerCalculate}
                disabled={calculating}
                className={`px-6 py-3.5 bg-teal-500 hover:bg-teal-400 text-slate-900 font-bold rounded-xl transition-all shadow-lg shadow-teal-500/20 flex items-center space-x-2 ${calculating ? 'opacity-80 cursor-wait' : 'hover:-translate-y-0.5'}`}
              >
                {calculating ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    <span>Computing Settlement...</span>
                  </>
                ) : (
                  <>
                    <BrainCircuit className="w-5 h-5" />
                    <span>Run Logic Engine</span>
                  </>
                )}
              </button>
            </section>
          )}

          {/* Results Section */}
          {settlement && (
            <section>
              <SettlementTable data={settlement} />
            </section>
          )}

        </main>
      </div>
    </div>
  );
}

function CheckCircle(props: any) {
  return (
    <svg {...props} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
      <polyline points="22 4 12 14.01 9 11.01"></polyline>
    </svg>
  );
}
