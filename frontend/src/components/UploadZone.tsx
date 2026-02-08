import { useCallback, useState } from 'react';
import { Upload, Loader2, CheckCircle, XCircle } from 'lucide-react';
import { uploadCatalog } from '../services/api';

interface Props {
  onUploadComplete: () => void;
}

export default function UploadZone({ onUploadComplete }: Props) {
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [status, setStatus] = useState<'idle' | 'success' | 'error'>('idle');
  const [message, setMessage] = useState('');

  const handleFiles = useCallback(
    async (files: FileList | null) => {
      if (!files || files.length === 0) return;

      const pdfFiles = Array.from(files).filter((f) =>
        f.name.toLowerCase().endsWith('.pdf')
      );

      if (pdfFiles.length === 0) {
        setStatus('error');
        setMessage('Please select PDF files only');
        return;
      }

      setUploading(true);
      setStatus('idle');

      try {
        for (const file of pdfFiles) {
          await uploadCatalog(file);
        }
        setStatus('success');
        setMessage(
          `${pdfFiles.length} catalog${pdfFiles.length > 1 ? 's' : ''} uploaded successfully`
        );
        onUploadComplete();
      } catch (err) {
        setStatus('error');
        setMessage(err instanceof Error ? err.message : 'Upload failed');
      } finally {
        setUploading(false);
        setTimeout(() => {
          setStatus('idle');
          setMessage('');
        }, 4000);
      }
    },
    [onUploadComplete]
  );

  return (
    <div
      className={`relative border-2 border-dashed rounded-xl p-8 text-center transition-colors ${
        dragOver
          ? 'border-blue-400 bg-blue-50'
          : 'border-gray-300 hover:border-gray-400'
      }`}
      onDragOver={(e) => {
        e.preventDefault();
        setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragOver(false);
        handleFiles(e.dataTransfer.files);
      }}
    >
      <input
        type="file"
        accept=".pdf"
        multiple
        className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
        onChange={(e) => handleFiles(e.target.files)}
        disabled={uploading}
      />

      {uploading ? (
        <div className="flex flex-col items-center gap-2">
          <Loader2 className="h-10 w-10 animate-spin text-blue-500" />
          <p className="text-sm text-gray-600">Uploading and processing...</p>
        </div>
      ) : status === 'success' ? (
        <div className="flex flex-col items-center gap-2">
          <CheckCircle className="h-10 w-10 text-green-500" />
          <p className="text-sm text-green-600">{message}</p>
        </div>
      ) : status === 'error' ? (
        <div className="flex flex-col items-center gap-2">
          <XCircle className="h-10 w-10 text-red-500" />
          <p className="text-sm text-red-600">{message}</p>
        </div>
      ) : (
        <div className="flex flex-col items-center gap-2">
          <Upload className="h-10 w-10 text-gray-400" />
          <p className="text-sm text-gray-600">
            <span className="font-medium text-blue-600">Click to upload</span> or
            drag and drop PDF catalogs
          </p>
          <p className="text-xs text-gray-400">PDF files up to 100MB</p>
        </div>
      )}
    </div>
  );
}
