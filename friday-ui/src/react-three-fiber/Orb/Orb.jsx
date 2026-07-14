import { useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import { Color } from 'three';
import { useOrbState } from '../../hooks/useOrbState';
import { useMouse } from '../../hooks/useMouse';
import vertSrc from '../../shaders/orb.vert.glsl?raw';
import fragSrc from '../../shaders/orb.frag.glsl?raw';

export default function Orb() {
    const meshRef = useRef();
    const matRef  = useRef();
    const { uniforms, isHovered, setIsHovered } = useOrbState();
    const mouse = useMouse();

    useFrame(({ clock }) => {
        if (!matRef.current || !meshRef.current) return;
        const u = uniforms.current;
        const t = clock.getElapsedTime();

        matRef.current.uniforms.u_time.value         = t;
        matRef.current.uniforms.u_color.value.setRGB(...u.color);
        matRef.current.uniforms.u_bloomStrength.value = u.bloom;
        matRef.current.uniforms.u_audioLevel.value   = u.audioLevel;

        const breathe = 1 + 0.02 * Math.sin(t * 1.2);
        const targetBase = isHovered ? 0.80 : 0.66;
        const targetScale = targetBase * breathe;

        meshRef.current.scale.x += (targetScale - meshRef.current.scale.x) * 0.08;
        meshRef.current.scale.y += (targetScale - meshRef.current.scale.y) * 0.08;
        meshRef.current.scale.z += (targetScale - meshRef.current.scale.z) * 0.08;

        meshRef.current.rotation.y += (mouse.current.dx * 0.42 - meshRef.current.rotation.y) * 0.05;
        meshRef.current.rotation.x += (mouse.current.dy * 0.26 - meshRef.current.rotation.x) * 0.05;
    });

    return (
        <group>
            <mesh 
                ref={meshRef}
                onPointerOver={() => setIsHovered(true)}
                onPointerOut={() => setIsHovered(false)}
            >
                <sphereGeometry args={[1.0, 64, 64]} />
                <shaderMaterial
                    ref={matRef}
                    vertexShader={vertSrc}
                    fragmentShader={fragSrc}
                    transparent
                    depthWrite={false}
                    blending={2}
                    uniforms={{
                        u_time:          { value: 0 },
                        u_color:         { value: new Color(0.0, 0.55, 1.0) },
                        u_bloomStrength: { value: 1.0 },
                        u_audioLevel:    { value: 0 },
                    }}
                />
            </mesh>

            <mesh scale={[1.18, 1.18, 1.18]}>
                <sphereGeometry args={[1.02, 64, 64]} />
                <meshBasicMaterial
                    color={new Color(0.06, 0.55, 1.0)}
                    transparent
                    opacity={0.08}
                    toneMapped={false}
                    depthWrite={false}
                />
            </mesh>

            <mesh scale={[0.92, 0.92, 0.92]}>
                <sphereGeometry args={[0.88, 64, 64]} />
                <meshBasicMaterial
                    color={new Color(0.16, 0.78, 1.0)}
                    transparent
                    opacity={0.12}
                    toneMapped={false}
                    depthWrite={false}
                />
            </mesh>

            <mesh>
                <sphereGeometry args={[0.032, 32, 32]} />
                <meshBasicMaterial 
                    color={new Color(0.8, 1.0, 1.0)}
                    toneMapped={false}
                />
            </mesh>
        </group>
    );
}
