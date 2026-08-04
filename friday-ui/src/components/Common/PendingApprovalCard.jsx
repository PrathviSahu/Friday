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
      <div className="rounded-2xl border border-[#00B7FF]/40 bg-[#001018]/95 p-5 shadow-[0_0_60px_rgba(0,183,255,0.25)] backdrop-blur-xl">
        <div className="flex items-center justify-between mb-3">
          <span className="font-orbitron text-[9px] tracking-[0.4em] text-[#00D9FF] uppercase">
            {title}
          </span>
          <button
            onClick={onCancel}
            disabled={busy}
            className="text-[#DFFAFF]/40 hover:text-[#DFFAFF] text-sm leading-none"
          >
            ✕
          </button>
        </div>

        <div className="font-grotesk text-[12px] text-[#DFFAFF]/80 space-y-1.5 mb-4">
          {rows.map((row, i) => (
            <div key={i} style={{ wordBreak: 'break-word' }}>
              <span className="text-[#00B7FF]">{row.label}:</span> {row.value}
            </div>
          ))}
          {body ? (
            <div className="border-t border-[#00B7FF]/20 pt-2 text-[#DFFAFF]/60 leading-5 whitespace-pre-wrap max-h-28 overflow-y-auto">
              {body}
            </div>
          ) : null}
        </div>

        <div className="flex items-center justify-between gap-3">
          <span className="font-grotesk text-[9px] text-[#DFFAFF]/40 uppercase tracking-[0.2em]">
            {hint}
          </span>
          <div className="flex gap-2">
            <button
              onClick={onCancel}
              disabled={busy}
              className="px-4 py-2 rounded-lg border border-[#ff4d6d]/40 text-[#ff8fa3] text-[10px] uppercase tracking-[0.2em] hover:bg-[#ff4d6d]/10 disabled:opacity-40"
            >
              {cancelLabel}
            </button>
            <button
              onClick={onConfirm}
              disabled={busy}
              className="px-5 py-2 rounded-lg bg-[#00B7FF] text-[#001018] text-[10px] font-bold uppercase tracking-[0.2em] hover:bg-[#00d1ff] disabled:opacity-40"
            >
              {busy ? 'Working…' : confirmLabel}
            </button>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
