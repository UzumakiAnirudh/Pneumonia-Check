import { useDropzone, type FileRejection } from 'react-dropzone';
import { useState } from 'react';
import { FileImage, UploadCloud } from 'lucide-react';
import { ACCEPTED_IMAGE_TYPES, MAX_UPLOAD_BYTES } from '@/utils/image';
import { cn } from '@/utils/cn';

interface UploadZoneProps {
  onFile: (file: File) => void;
  disabled?: boolean;
  compact?: boolean;
}

function rejectionMessage(rejections: FileRejection[]): string {
  const code = rejections[0]?.errors[0]?.code;
  if (code === 'file-too-large') return 'That file is larger than 25 MB.';
  if (code === 'file-invalid-type')
    return 'Unsupported file type. Please upload a PNG, JPEG or DICOM (.dcm) image.';
  if (code === 'too-many-files') return 'Please upload one image at a time.';
  return 'That file could not be used.';
}

export function UploadZone({ onFile, disabled, compact }: UploadZoneProps) {
  const [error, setError] = useState<string | null>(null);
  const { getRootProps, getInputProps, isDragActive, open } = useDropzone({
    accept: ACCEPTED_IMAGE_TYPES as unknown as Record<string, string[]>,
    maxFiles: 1,
    multiple: false,
    maxSize: MAX_UPLOAD_BYTES,
    disabled,
    noClick: compact,
    onDropAccepted: (files) => {
      setError(null);
      onFile(files[0]);
    },
    onDropRejected: (r) => setError(rejectionMessage(r)),
  });

  if (compact) {
    return (
      <div {...getRootProps()}>
        <input {...getInputProps()} aria-label="Choose a different chest X-ray image" />
        <button
          type="button"
          onClick={open}
          disabled={disabled}
          className="inline-flex items-center gap-2 rounded-lg px-2.5 py-1.5 text-xs font-medium text-slate-300 hover:bg-viewer-line hover:text-white disabled:opacity-50"
        >
          <UploadCloud className="h-3.5 w-3.5" aria-hidden /> Replace image
        </button>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      <div
        {...getRootProps()}
        className={cn(
          'group relative flex flex-1 cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed px-6 py-12 text-center transition-colors',
          isDragActive
            ? 'border-accent bg-accent/10'
            : 'border-viewer-line hover:border-accent/60 hover:bg-viewer-panel',
          disabled && 'pointer-events-none opacity-60',
        )}
      >
        <input {...getInputProps()} aria-label="Upload a chest X-ray image" />
        <div
          className="bg-grid pointer-events-none absolute inset-0 rounded-xl opacity-40"
          aria-hidden
        />
        <span
          className={cn(
            'relative mb-5 grid h-16 w-16 place-items-center rounded-2xl border border-viewer-line bg-viewer-panel text-accent transition-transform',
            isDragActive ? 'scale-110' : 'group-hover:scale-105',
          )}
        >
          {isDragActive ? (
            <FileImage className="h-7 w-7" aria-hidden />
          ) : (
            <UploadCloud className="h-7 w-7" aria-hidden />
          )}
        </span>
        <p className="relative text-lg font-semibold text-white">
          {isDragActive ? 'Drop the X-ray here' : 'Drag & drop a chest X-ray'}
        </p>
        <p className="relative mt-1.5 text-sm text-slate-400">
          or{' '}
          <span className="font-medium text-accent underline-offset-4 group-hover:underline">
            browse files
          </span>{' '}
          — PNG, JPEG or DICOM, up to 25 MB
        </p>
        <p className="relative mt-4 text-xs text-slate-500">Frontal (PA/AP) views work best</p>
      </div>
      {error && (
        <p
          role="alert"
          className="mt-3 rounded-lg border border-pneumonia/40 bg-pneumonia/10 px-3 py-2 text-sm text-red-300"
        >
          {error}
        </p>
      )}
    </div>
  );
}
