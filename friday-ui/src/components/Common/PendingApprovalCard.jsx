import { motion } from 'framer-motion';

/**
 * PendingApprovalCard — shared "approval-first" preview card used on the
 * lock screen for any action with real-world consequences (send email,
 * create calendar event, …). Shows a preview + Confirm/Cancel and a voice hint.
 */
export default function PendingApprovalCard({
  title,
  rows = [],
  body = '',
  hint = 'Say "yes" to confirm · "no" to cancel',
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  busy = false,
  onConfirm,
  onCancel,
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 24 }}
      className="fixed left-1/2 -translate-x-1/2 z-[70] w-[460px] max-w-[92vw]"
      style={{ bottom: 120, pointerEvents: 'auto' }}
    >
      <div className="rounded-2xl border border-slate-600/30 bg-slate-900/95 p-5 shadow-2xl backdrop-blur-xl">
        <div className="flex items-center justify-between mb-3">
          <span className="font-sans text-[10px] tracking-[0.2em] text-slate-300 font-medium uppercase">
            {title}
          </span>
          <button
            onClick={onCancel}
            disabled={busy}
            className="text-slate-400 hover:text-slate-200 text-sm leading-none"
          >
            ✕
          </button>
        </div>

        <div className="font-sans text-[12px] text-slate-200/80 space-y-1.5 mb-4">
          {rows.map((row, i) => (
            <div key={i} style={{ wordBreak: 'break-word' }}>
              <span className="text-blue-400 font-medium">{row.label}:</span> {row.value}
            </div>
          ))}
          {body ? (
            <div className="border-t border-slate-600/20 pt-2 text-slate-300/70 leading-5 whitespace-pre-wrap max-h-28 overflow-y-auto">
              {body}
            </div>
          ) : null}
        </div>

        <div className="flex items-center justify-between gap-3">
          <span className="font-sans text-[9px] text-slate-400/50 uppercase tracking-[0.15em]">
            {hint}
          </span>
          <div className="flex gap-2">
            <button
              onClick={onCancel}
              disabled={busy}
              className="px-4 py-2 rounded-lg border border-slate-600/30 text-slate-300 text-[10px] uppercase tracking-wide hover:bg-slate-700/30 disabled:opacity-40"
            >
              {cancelLabel}
            </button>
            <button
              onClick={onConfirm}
              disabled={busy}
              className="px-5 py-2 rounded-lg bg-blue-500 text-white text-[10px] font-semibold uppercase tracking-wide hover:bg-blue-400 disabled:opacity-40"
            >
              {busy ? 'Working…' : confirmLabel}
            </button>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
