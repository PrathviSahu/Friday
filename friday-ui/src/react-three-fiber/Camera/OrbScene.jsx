import { Canvas } from '@react-three/fiber';
import { AdaptiveDpr } from '@react-three/drei';
import Orb from '../Orb/Orb';
import Rings from '../Rings/Rings';
import OrbParticles from '../Particles/OrbParticles';
import PostFX from '../Bloom/PostFX';

export default function OrbScene() {
    return (
        <Canvas
            /* Camera pulled further back + wider FOV → orb/rings appear smaller in viewport */
            camera={{ position: [0, 0, 7], fov: 55 }}
            dpr={[1, 1.5]}
            gl={{ antialias: true, alpha: true, powerPreference: 'high-performance' }}
            style={{ background: 'transparent' }}
        >
            <AdaptiveDpr pixelated />

            {/* Minimal lighting — shader handles its own glow */}
            <ambientLight intensity={0.05} />
            <pointLight position={[0, 0, 4]} intensity={1.5} color="#00B7FF" />

            <Orb />
            <Rings />
            <OrbParticles />
            <PostFX />
        </Canvas>
    );
}
