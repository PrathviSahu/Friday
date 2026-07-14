import { Bloom, EffectComposer, ChromaticAberration, Noise } from '@react-three/postprocessing';
import { BlendFunction } from 'postprocessing';
import { useOrbState } from '../../hooks/useOrbState';

export default function PostFX() {
    const { uniforms } = useOrbState();
    const bloom = uniforms.current.bloom ?? 0.9;

    return (
        <EffectComposer>
            <Bloom
                luminanceThreshold={0.18}
                luminanceSmoothing={0.15}
                intensity={0.72}
                mipmapBlur
            />
            <ChromaticAberration
                blendFunction={BlendFunction.NORMAL}
                offset={[0.00008, 0.00008]}
            />
            <Noise
                blendFunction={BlendFunction.SOFT_LIGHT}
                opacity={0.01}
            />
        </EffectComposer>
    );
}
