import "./AICore.css";
import Rings from "./Rings";
import Satellites from "./Satellites";
import Glow from "./Glow";
import { useOrbState } from '../../hooks/useOrbState';

export default function AICore() {
    const { appState } = useOrbState();
    const map = {
      BOOTING: 'alert',
      IDLE: 'idle',
      LISTENING: 'listening',
      THINKING: 'thinking',
      VERIFYING: 'thinking',
      UNLOCKING: 'verified',
      UNLOCKED: 'verified',
      SPEAKING: 'speaking',
    };
    const state = map[appState] || 'idle';

    return (

        <div className={`ai-core state-${state}`}>

            <Glow state={state} />

            <Rings state={state} />

            <div className="energy-shell">
                <div className="inner-halo" aria-hidden />
                <div className="flow flow-outer"></div>
                <div className="flow flow-mid"></div>
                <div className="plasma">
                    <div className="plasma-glow"></div>
                    <div className="white-core"></div>
                    <div className="tiny-center"></div>
                </div>
            </div>

            <div className="pulse-wave" aria-hidden />
            <div className="spark-layer" aria-hidden>
                {Array.from({ length: 7 }).map((_, i) => (
                    <div key={i} className={`spark spark-${i + 1}`} />
                ))}
            </div>

            <div className={`energy-pulse pulse-${state}`} aria-hidden></div>

            <Satellites state={state} />

        </div>

    );

}
