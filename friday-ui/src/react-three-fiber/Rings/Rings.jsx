import { useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import { Color } from 'three';
import { useOrbState } from '../../hooks/useOrbState';

/*
  Restored: 7 premium 3D Torus rings with depth, specular catch, and thickness.
  Radii are kept tight (0.72 to 1.12) around the 0.65 sphere.
*/
const RING_DEFS = [
    { r: 0.70, tube: 0.0020, speed:  0.42, tiltX: 0.0,  tiltZ: 0.0,  opacity: 0.24 },
    { r: 0.80, tube: 0.0025, speed: -0.36, tiltX: 0.24, tiltZ: 0.08, opacity: 0.16 },
    { r: 0.88, tube: 0.0023, speed:  0.64, tiltX: 0.48, tiltZ: 0.0,  opacity: 0.18 },
    { r: 0.96, tube: 0.0028, speed: -0.44, tiltX: 0.84, tiltZ: 0.16, opacity: 0.14 },
    { r: 1.03, tube: 0.0020, speed:  0.26, tiltX: 0.14, tiltZ: 1.02, opacity: 0.12 },
    { r: 1.10, tube: 0.0024, speed: -0.52, tiltX: 1.10, tiltZ: 0.42, opacity: 0.10 },
    { r: 1.18, tube: 0.0020, speed:  0.46, tiltX: 0.36, tiltZ: 0.90, opacity: 0.08 },
    { r: 1.26, tube: 0.0015, speed: -0.28, tiltX: 0.55, tiltZ: 0.25, opacity: 0.06 },
];

function TorusRing({ r, tube, speed, tiltX, tiltZ, speedMult, opacity }) {
    const ref = useRef();
    useFrame((_, delta) => {
        if (ref.current) ref.current.rotation.z += delta * speed * Math.max(speedMult, 0.2);
    });

    return (
        <mesh ref={ref} rotation={[tiltX, 0, tiltZ]}>
            <torusGeometry args={[r, tube, 3, 192]} />
            <meshStandardMaterial
                color={new Color(0.95, 0.72, 0.18)}
                emissive={new Color(0.05, 0.6, 1.0)}
                emissiveIntensity={0.8}
                metalness={0.92}
                roughness={0.18}
                transparent
                opacity={typeof opacity === 'number' ? opacity : 0.12}
                depthWrite={false}
                toneMapped={false}
            />
        </mesh>
    );
}

export default function Rings() {
    const { uniforms, isHovered } = useOrbState();
    const speedMult = uniforms.current.ringSpeed * (isHovered ? 1.8 : 1.0);

    return (
        <group>
            {RING_DEFS.map((d, i) => (
                <TorusRing key={i} {...d} speedMult={speedMult} />
            ))}
        </group>
    );
}
