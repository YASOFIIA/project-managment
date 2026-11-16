import { useRef, useState, type DragEvent } from 'react';
import { UploadCloud } from 'lucide-react';
import { ACCEPT_ATTR } from '../../utils/fileType';

interface Props {
  onFiles: (files: File[]) => void;
  disabled?: boolean;
  multiple?: boolean;
}

export function FileDropZone({ onFiles, disabled, multiple = true }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  const handleDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragging(false);
    if (disabled) return;
    const files = Array.from(e.dataTransfer.files);
    if (files.length) onFiles(multiple ? files : files.slice(0, 1));
  };

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        if (!disabled) setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      className={`flex flex-col items-center justify-center rounded-card border-2 border-dashed px-6 py-8 text-center transition-colors duration-150 ${
        dragging ? 'border-accent bg-accent-soft' : 'border-black/10 bg-white/50'
      } ${disabled ? 'opacity-60' : ''}`}
    >
      <UploadCloud size={28} strokeWidth={1.5} className="mb-2 text-accent" aria-hidden />
      <p className="text-sm font-medium">Drop files here</p>
      <p className="mt-0.5 text-xs text-ink-soft">PDF, DOCX, PNG, JPG · up to 50 MB</p>
      <button
        type="button"
        disabled={disabled}
        onClick={() => inputRef.current?.click()}
        className="mt-3 rounded-btn bg-white px-3 py-1.5 text-[13px] font-medium shadow-card transition-colors hover:bg-white/80 disabled:cursor-not-allowed"
      >
        Upload File
      </button>
      <input
        ref={inputRef}
        type="file"
        hidden
        multiple={multiple}
        accept={ACCEPT_ATTR}
        onChange={(e) => {
          const files = Array.from(e.target.files ?? []);
          if (files.length) onFiles(files);
          e.target.value = '';
        }}
      />
    </div>
  );
}
