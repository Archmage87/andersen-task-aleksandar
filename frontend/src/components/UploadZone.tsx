import React, { useState } from 'react';
import { UploadCloud, CheckCircle, Loader2 } from 'lucide-react';

interface UploadZoneProps {
  label: string;
  accept: string;
  onUploadSuccess: (data: any) => void;
  onRemove?: () => Promise<void>;
  endpoint: string;
}

export default function UploadZone({ label, accept, onUploadSuccess, onRemove, endpoint }: UploadZoneProps) {
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [uploadedFileName, setUploadedFileName] = useState<string | null>(null);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files?.[0]) return;
    const file = e.target.files[0];
    
    setLoading(true);
    setSuccess(false);
    setErrorMsg(null);
    setUploadedFileName(file.name);
    
    const formData = new FormData();
    formData.append('file', file);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}${endpoint}`, {
        method: 'POST',
        body: formData,
      });
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.detail || "Upload failed");
      }
      
      setSuccess(true);
      onUploadSuccess(data);
    } catch (err: any) {
      console.error("Upload error:", err);
      setErrorMsg(err.message || "Failed to process file");
      setSuccess(false);
    } finally {
      setLoading(false);
    }
  };

  const handleRemoveClick = async () => {
    setLoading(true);
    try {
      if (onRemove) {
        await onRemove();
      }
      setSuccess(false);
      setUploadedFileName(null);
      setErrorMsg(null);
    } catch (err: any) {
      setErrorMsg("Failed to remove file");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={`relative flex flex-col items-center justify-center border-2 border-dashed rounded-xl p-8 text-center transition-all duration-300 ease-in-out group ${
      success ? 'border-teal-500 bg-teal-50/50' : 'border-slate-300 hover:border-teal-500 hover:bg-slate-50'
    }`}>
      
      {success ? (
        <CheckCircle className="w-12 h-12 text-teal-500 mb-4 transition-transform scale-100" />
      ) : loading ? (
        <Loader2 className="w-12 h-12 text-teal-500 mb-4 animate-spin" />
      ) : (
        <UploadCloud className="w-12 h-12 text-slate-400 group-hover:text-teal-500 mb-4 transition-colors" />
      )}
      
      <p className="text-base font-semibold text-slate-700 mb-2">{label}</p>
      <p className="text-sm text-slate-500 mb-2">Supports: {accept}</p>
      {errorMsg && <p className="text-sm font-bold text-red-500 mb-4 bg-red-50 py-1 px-3 rounded-md">{errorMsg}</p>}
      
      {success ? (
        <div className="flex flex-col items-center mt-2">
          <p className="text-sm font-medium text-teal-700 mb-4 bg-teal-100/50 px-4 py-1.5 rounded-full border border-teal-200">
            {uploadedFileName}
          </p>
          <button 
            onClick={handleRemoveClick}
            disabled={loading}
            className={`cursor-pointer inline-flex items-center px-5 py-2.5 text-sm font-medium rounded-lg shadow-sm transition-colors bg-white text-red-600 border border-red-200 hover:bg-red-50 ${loading && 'opacity-50 cursor-not-allowed'}`}
          >
            {loading ? 'Removing...' : 'Remove File'}
          </button>
        </div>
      ) : (
        <>
          <input 
            type="file" 
            accept={accept} 
            onChange={handleFileChange} 
            className="hidden" 
            id={`file-${label}`} 
            disabled={loading}
          />
          <label 
            htmlFor={`file-${label}`} 
            className={`cursor-pointer inline-flex items-center px-5 py-2.5 text-sm font-medium rounded-lg shadow-sm transition-colors bg-teal-600 text-white hover:bg-teal-700 ${loading && 'opacity-70 cursor-not-allowed pointer-events-none'}`}
          >
            {loading ? 'Processing Document...' : 'Select Document'}
          </label>
        </>
      )}
    </div>
  );
}
