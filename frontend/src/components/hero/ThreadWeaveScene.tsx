import React, { useRef, useMemo } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { useReducedMotion } from '../../hooks/useReducedMotion';

function WovenCurves({ isReducedMotion }: { isReducedMotion: boolean }) {
  const groupRef = useRef<THREE.Group>(null);

  // Generate 3 elegant flowing thread curves
  const curves = useMemo(() => {
    const threadData = [
      { color: '#34D399', radius: 1.4, speed: 0.6, phase: 0 },
      { color: '#F7F5F0', radius: 1.2, speed: 0.8, phase: Math.PI * 0.66 },
      { color: '#8B8578', radius: 1.0, speed: 0.5, phase: Math.PI * 1.33 },
    ];

    return threadData.map((td) => {
      const points: THREE.Vector3[] = [];
      const numPoints = 80;
      for (let i = 0; i <= numPoints; i++) {
        const t = (i / numPoints) * Math.PI * 4;
        const x = Math.sin(t + td.phase) * td.radius;
        const y = (i / numPoints - 0.5) * 4;
        const z = Math.cos(t * 1.5 + td.phase) * (td.radius * 0.8);
        points.push(new THREE.Vector3(x, y, z));
      }
      const curve = new THREE.CatmullRomCurve3(points);
      const geometry = new THREE.TubeGeometry(curve, 100, 0.035, 8, false);
      return { geometry, color: td.color };
    });
  }, []);

  useFrame((state, delta) => {
    if (isReducedMotion || !groupRef.current) return;
    groupRef.current.rotation.y += delta * 0.25;
    groupRef.current.rotation.x = Math.sin(state.clock.elapsedTime * 0.3) * 0.15;
  });

  return (
    <group ref={groupRef}>
      {curves.map((c, i) => (
        <mesh key={i} geometry={c.geometry}>
          <meshStandardMaterial
            color={c.color}
            roughness={0.3}
            metalness={0.2}
            emissive={c.color}
            emissiveIntensity={c.color === '#34D399' ? 0.2 : 0.05}
          />
        </mesh>
      ))}
    </group>
  );
}

export const ThreadWeaveScene: React.FC<{ className?: string }> = ({ className = '' }) => {
  const isReducedMotion = useReducedMotion();

  return (
    <div className={`relative w-full h-[360px] md:h-[440px] pointer-events-none select-none ${className}`}>
      <Canvas
        camera={{ position: [0, 0, 4.5], fov: 45 }}
        gl={{ antialias: true, alpha: true, powerPreference: 'high-performance' }}
      >
        <ambientLight intensity={0.7} />
        <directionalLight position={[4, 8, 4]} intensity={1.2} />
        <pointLight position={[-3, -3, -2]} intensity={0.5} color="#34D399" />
        <WovenCurves isReducedMotion={isReducedMotion} />
      </Canvas>
    </div>
  );
};
