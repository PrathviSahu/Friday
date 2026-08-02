export function SkeletonLine({ w = '100%', h = 14, mb = 8 }) {
  return (
    <div style={{
      width: w, height: h, borderRadius: 6, marginBottom: mb,
      background: 'linear-gradient(90deg, rgba(255,255,255,0.04) 25%, rgba(255,255,255,0.08) 50%, rgba(255,255,255,0.04) 75%)',
      backgroundSize: '200% 100%',
      animation: 'skeletonShimmer 1.4s infinite',
    }} />
  );
}
export function SkeletonCard({ lines = 3 }) {
  return (
    <div style={{ padding: 16, borderRadius: 10, border: '1px solid rgba(255,255,255,0.06)', marginBottom: 8 }}>
      {Array.from({ length: lines }).map((_, i) => (
        <SkeletonLine key={i} w={i === 0 ? '60%' : i === lines - 1 ? '40%' : '90%'} />
      ))}
    </div>
  );
}
export default function Skeleton({ count = 4 }) {
  return (
    <div>
      <style>{`@keyframes skeletonShimmer{0%{background-position:200% 0}100%{background-position:-200% 0}}`}</style>
      {Array.from({ length: count }).map((_, i) => <SkeletonCard key={i} lines={3} />)}
    </div>
  );
}
