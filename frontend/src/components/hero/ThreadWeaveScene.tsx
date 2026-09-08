import React, { useRef, useMemo } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { useReducedMotion } from '../../hooks/useReducedMotion';

/**
 * Generates an organic 3-strand textile braid that converges from individual threads
 * into a tightly wound cord across the banner, with natural catenary sag and micro-variations.
 */
function OrganicBraid({ isReducedMotion }: { isReducedMotion: boolean }) {
  const groupRef = useRef<THREE.Group>(null);

  const strands = useMemo(() => {
    // 3 primary fiber strands with distinct weights and hand-dyed textile tones
    const strandConfigs = [
      {
        color: '#34D399', // Verified Emerald silk
        roughness: 0.85,
        metalness: 0.05,
        emissive: '#10B981',
        emissiveIntensity: 0.12,
        radius: 0.072,
        phase: 0,
        subStrands: 2,
      },
      {
        color: '#F4EFE4', // Unbleached Linen / Ledger Paper
        roughness: 0.92,
        metalness: 0.02,
        emissive: '#E5DDCB',
        emissiveIntensity: 0.04,
        radius: 0.068,
        phase: (Math.PI * 2) / 3,
        subStrands: 2,
      },
      {
        color: '#D97706', // Raw amber / golden thread
        roughness: 0.88,
        metalness: 0.08,
        emissive: '#B45309',
        emissiveIntensity: 0.10,
        radius: 0.065,
        phase: (Math.PI * 4) / 3,
        subStrands: 2,
      },
    ];

    const results: { geometry: THREE.TubeGeometry; color: string; roughness: number; metalness: number; emissive: string; emissiveIntensity: number }[] = [];

    strandConfigs.forEach((cfg) => {
      // Main strand + sister micro-fiber for rich textile ply texture
      for (let sub = 0; sub < cfg.subStrands; sub++) {
        const subOffsetAngle = sub * Math.PI;
        const subDist = sub === 0 ? 0 : 0.032;
        const points: THREE.Vector3[] = [];
        const numPoints = 120;

        for (let i = 0; i <= numPoints; i++) {
          const frac = i / numPoints; // 0 to 1
          const x = (frac - 0.5) * 7.2; // span from -3.6 to +3.6

          // Organic catenary sag: natural gravitational dip
          const normX = x / 3.6;
          const sag = -0.38 * (1.0 - normX * normX);

          // Weave frequency: relaxed, luxurious 3-cycle braid across the width
          const freq = 1.95;
          const theta = x * freq + cfg.phase + (sub === 1 ? 0.35 : 0);

          // Amplitude envelope: fibers converge smoothly towards center
          const amp = 0.34;
          const braidY = Math.sin(theta) * amp;
          const braidZ = Math.cos(theta) * (amp * 0.9);

          // Organic hand-spun irregularities
          const organicJitterY = Math.sin(x * 5.2 + cfg.phase) * 0.025;
          const organicJitterZ = Math.cos(x * 4.4 + cfg.phase) * 0.025;

          // Sub-strand ply offset
          const subY = Math.sin(subOffsetAngle) * subDist;
          const subZ = Math.cos(subOffsetAngle) * subDist;

          const y = sag + braidY + organicJitterY + subY;
          const z = braidZ + organicJitterZ + subZ;

          points.push(new THREE.Vector3(x, y, z));
        }

        const curve = new THREE.CatmullRomCurve3(points, false, 'catmullrom', 0.2);
        const radius = sub === 0 ? cfg.radius : cfg.radius * 0.55;
        const geometry = new THREE.TubeGeometry(curve, 140, radius, 12, false);

        results.push({
          geometry,
          color: cfg.color,
          roughness: cfg.roughness,
          metalness: cfg.metalness,
          emissive: cfg.emissive,
          emissiveIntensity: cfg.emissiveIntensity,
        });
      }
    });

    return results;
  }, []);

  // Gentle physical suspended swaying motion
  useFrame((state) => {
    if (isReducedMotion || !groupRef.current) return;
    const t = state.clock.elapsedTime;
    // Gentle natural pendulum sway and breathing under tension
    groupRef.current.rotation.z = Math.sin(t * 0.45) * 0.035;
    groupRef.current.rotation.y = Math.sin(t * 0.32) * 0.06;
    groupRef.current.position.y = Math.sin(t * 0.6) * 0.03;
  });

  return (
    <group ref={groupRef}>
      {strands.map((s, idx) => (
        <mesh key={idx} geometry={s.geometry}>
          <meshStandardMaterial
            color={s.color}
            roughness={s.roughness}
            metalness={s.metalness}
            emissive={s.emissive}
            emissiveIntensity={s.emissiveIntensity}
          />
        </mesh>
      ))}
    </group>
  );
}

export const ThreadWeaveScene: React.FC<{ className?: string }> = ({ className = '' }) => {
  const isReducedMotion = useReducedMotion();

  return (
    <div className={`relative w-full h-[360px] md:h-[420px] pointer-events-none select-none ${className}`}>
      <Canvas
        camera={{ position: [0, -0.05, 4.2], fov: 42 }}
        gl={{ antialias: true, alpha: true, powerPreference: 'high-performance' }}
      >
        <ambientLight intensity={0.85} />
        <directionalLight position={[5, 6, 4]} intensity={1.4} color="#FFFDF7" />
        <directionalLight position={[-4, -3, -2]} intensity={0.4} color="#34D399" />
        <pointLight position={[0, 1, 3]} intensity={0.6} color="#F4EFE4" />
        <OrganicBraid isReducedMotion={isReducedMotion} />
      </Canvas>
    </div>
  );
};

