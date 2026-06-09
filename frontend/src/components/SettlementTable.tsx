import React from 'react';
import { AlertCircle, CheckCircle2 } from 'lucide-react';

interface LineItem {
  service: string;
  claimed_amount: number;
  approved_amount: number;
  reason: string;
}

interface SettlementData {
  settlement_id: string;
  status: string;
  total_claimed: number;
  total_approved: number;
  total_patient_responsibility: number;
  line_items: LineItem[];
}

export default function SettlementTable({ data }: { data: SettlementData }) {
  const formatCurrency = (amount: number) =>
    new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount);

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden animate-in fade-in slide-in-from-bottom-4 duration-500">
      {/* Header Section */}
      <div className="p-6 border-b border-slate-200 bg-slate-50/50">
        <div className="flex justify-between items-start mb-6">
          <div>
            <h2 className="text-xl font-bold text-slate-800">Settlement Statement</h2>
            <p className="text-sm text-slate-500 mt-1">ID: {data.settlement_id}</p>
          </div>
        </div>

        {/* Summary Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm">
            <p className="text-sm font-medium text-slate-500 mb-1">Total Claimed</p>
            <p className="text-2xl font-bold text-slate-800">{formatCurrency(data.total_claimed)}</p>
          </div>
          <div className="bg-white p-4 rounded-lg border border-emerald-200 shadow-sm ring-1 ring-emerald-50">
            <p className="text-sm font-medium text-emerald-600 mb-1">Total Approved</p>
            <p className="text-2xl font-bold text-emerald-700">{formatCurrency(data.total_approved)}</p>
          </div>
          <div className="bg-white p-4 rounded-lg border border-orange-200 shadow-sm ring-1 ring-orange-50">
            <p className="text-sm font-medium text-orange-600 mb-1">Patient Responsibility</p>
            <p className="text-2xl font-bold text-orange-700">{formatCurrency(data.total_patient_responsibility)}</p>
          </div>
        </div>
      </div>

      {/* Line Items Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm text-left">
          <thead className="bg-slate-50 text-slate-600 font-medium border-b border-slate-200">
            <tr>
              <th className="px-6 py-4">Service Rendered</th>
              <th className="px-6 py-4 text-right">Claimed</th>
              <th className="px-6 py-4 text-right">Approved</th>
              <th className="px-6 py-4">Adjudication Reason</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 text-slate-700">
            {data.line_items.map((item, index) => (
              <tr key={index} className="hover:bg-slate-50/50 transition-colors">
                <td className="px-6 py-4 font-medium text-slate-800">{item.service}</td>
                <td className="px-6 py-4 text-right">{formatCurrency(item.claimed_amount)}</td>
                <td className="px-6 py-4 text-right font-medium text-emerald-600">
                  {formatCurrency(item.approved_amount)}
                </td>
                <td className="px-6 py-4">
                  {item.claimed_amount !== item.approved_amount ? (
                    <div className="inline-flex items-center text-orange-600 text-xs font-medium bg-orange-50 px-2.5 py-1 rounded-md">
                      <AlertCircle className="w-3.5 h-3.5 mr-1.5" />
                      {item.reason}
                    </div>
                  ) : (
                    <span className="text-slate-400 text-xs">Standard approval</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
