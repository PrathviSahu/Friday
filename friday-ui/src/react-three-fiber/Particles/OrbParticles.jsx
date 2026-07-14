import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import { Color, AdditiveBlending } from 'three';

const COUNT = 420;

export default function OrbParticles() {
    const ref = useRef();

    const [positions, angles, radii] = useMemo(() => {
        const pos  = new Float32Array(COUNT * 3);
        const ang  = new Float32Array(COUNT);
        const rad  = new Float32Array(COUNT);
        for (let i = 0; i < COUNT; i++) {
            const theta = Math.random() * Math.PI * 2;
            const phi   = Math.acos(2 * Math.random() - 1);
            const r     = 1.05 + Math.random() * 1.1;
            const z     = r * Math.cos(phi);
            const xy    = Math.sqrt(Math.max(r * r - z * z, 0.0));

            pos[i * 3]     = xy * Math.cos(theta);
            pos[i * 3 + 1] = z * 0.08;
            pos[i * 3 + 2] = xy * Math.sin(theta);

            ang[i]  = theta;
            rad[i]  = xy;
        }
        return [pos, ang, rad];
    }, []);

    useFrame(({ clock }) => {
        if (!ref.current) return;
        const pos = ref.current.geometry.attributes.position.array;
        const time = clock.getElapsedTime();

        for (let i = 0; i < COUNT; i++) {
            const idx = i * 3;
            const rotation = angles[i] + time * (0.28 + (i % 6) * 0.009);
            pos[idx]     = Math.cos(rotation) * radii[i];
            pos[idx + 2] = Math.sin(rotation) * radii[i];
            pos[idx + 1] = 0.06 * Math.sin(time * 1.6 + angles[i] * 2.6);
        }

        ref.current.geometry.attributes.position.needsUpdate = true;
    });

    return (
        <points ref={ref}>
            <bufferGeometry>
                <bufferAttribute
                    attach="attributes-position"
                    args={[positions, 3]}
                />
            </bufferGeometry>
            <pointsMaterial
                color={new Color(1.0, 0.68, 0.22)}
                size={0.012}
                transparent
                opacity={0.9}
                sizeAttenuation
                depthWrite={false}
                blending={AdditiveBlending}
            />
            {/* fine cyan micro-sparks */}
            <points>
                <bufferGeometry>
                    <bufferAttribute attach="attributes-position" args={[positions, 3]} />
                </bufferGeometry>
                <pointsMaterial
                    color={new Color(0.0, 0.95, 1.0)}
                    size={0.006}
                    transparent
                    opacity={0.75}
                    sizeAttenuation
                    depthWrite={false}
                    blending={AdditiveBlending}
                />
            </points>
        </points>
    );
}
