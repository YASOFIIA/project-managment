import { useEffect, useId, useRef, type ReactNode } from 'react';
import { X } from 'lucide-react';

interface Props {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
}

// Native <dialog>: focus handling, Esc and top layer come from the browser
export function Modal({ open, onClose, title, children }: Props) {
  const ref = useRef<HTMLDialogElement>(null);
  const titleId = useId();

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  // Light dismiss fallback where `closedby` is not supported (Safari)
  useEffect(() => {
    const dialog = ref.current;
    if (!dialog || 'closedBy' in HTMLDialogElement.prototype) return;
    let pressedOutside = false;
    const outside = (e: PointerEvent) => {
      const r = dialog.getBoundingClientRect();
      return e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom;
    };
    const down = (e: PointerEvent) => (pressedOutside = outside(e));
    const up = (e: PointerEvent) => {
      if (pressedOutside && outside(e)) dialog.close();
    };
    dialog.addEventListener('pointerdown', down);
    dialog.addEventListener('pointerup', up);
    return () => {
      dialog.removeEventListener('pointerdown', down);
      dialog.removeEventListener('pointerup', up);
    };
  }, []);

  return (
    <dialog
      ref={ref}
      className="pm-dialog"
      aria-labelledby={titleId}
      onClose={onClose}
      {...({ closedby: 'any' } as object)}
    >
      {open && (
        <div className="glass rounded-card border border-line p-6 shadow-pop">
          <div className="mb-4 flex items-start justify-between gap-4">
            <h2 id={titleId} className="text-lg">
              {title}
            </h2>
            <button
              type="button"
              onClick={() => ref.current?.close()}
              aria-label="Закрити"
              className="rounded-btn p-1 text-ink-soft transition-colors hover:bg-black/5 hover:text-ink"
            >
              <X size={18} strokeWidth={1.5} />
            </button>
          </div>
          {children}
        </div>
      )}
    </dialog>
  );
}
