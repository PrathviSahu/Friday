export default function Glow({ state = 'idle' }){
  // state can be: 'idle' | 'listening' | 'thinking' | 'speaking' | 'verified'
  const cls = `main-glow glow-${state}`;
  return (<div className={cls} aria-hidden />)
}
