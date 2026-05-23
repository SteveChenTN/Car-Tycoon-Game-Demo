import { useRef, useMemo } from 'react';
import { motion } from 'framer-motion';

interface Node {
  id: string;
  x: number;
  y: number;
  label: string;
  size: number;
  activity: number; // 0-1, for pulse effect
}

interface Link {
  source: string;
  target: string;
  strength: number; // 0-1, for glow effect
}

interface NetworkTopologyProps {
  nodes?: Node[];
  links?: Link[];
  className?: string;
}

// Mock data generator
function generateMockNetwork(): { nodes: Node[]; links: Link[] } {
  const regions = ['NA', 'EU', 'AS', 'SA', 'AF', 'OC'];
  const nodes: Node[] = regions.map((region, i) => {
    const angle = (i / regions.length) * Math.PI * 2;
    const radius = 35; // Percentage from center
    return {
      id: region,
      x: 50 + Math.cos(angle) * radius,
      y: 50 + Math.sin(angle) * radius,
      label: region,
      size: Math.random() * 4 + 6,
      activity: Math.random(),
    };
  });

  const links: Link[] = [];
  for (let i = 0; i < nodes.length; i++) {
    const nextIdx = (i + 1) % nodes.length;
    links.push({
      source: nodes[i].id,
      target: nodes[nextIdx].id,
      strength: Math.random() * 0.5 + 0.3,
    });

    // Add some cross-links
    if (Math.random() > 0.5) {
      const randomIdx = Math.floor(Math.random() * nodes.length);
      if (randomIdx !== i) {
        links.push({
          source: nodes[i].id,
          target: nodes[randomIdx].id,
          strength: Math.random() * 0.3 + 0.2,
        });
      }
    }
  }

  return { nodes, links };
}

export function NetworkTopology({ nodes: propNodes, links: propLinks, className = '' }: NetworkTopologyProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  
  // Use provided data or generate mock data
  const { nodes, links } = useMemo(() => {
    if (propNodes && propLinks) {
      return { nodes: propNodes, links: propLinks };
    }
    return generateMockNetwork();
  }, [propNodes, propLinks]);

  // Create node lookup map
  const nodeMap = useMemo(() => {
    const map = new Map<string, Node>();
    nodes.forEach(node => map.set(node.id, node));
    return map;
  }, [nodes]);

  return (
    <div className={`relative w-full h-full bg-slate-950/50 rounded-lg overflow-hidden ${className}`}>
      {/* Grid Background */}
      <div className="absolute inset-0 opacity-20">
        <svg className="w-full h-full">
          <defs>
            <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
              <path
                d="M 40 0 L 0 0 0 40"
                fill="none"
                stroke="rgba(6, 182, 212, 0.1)"
                strokeWidth="0.5"
              />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#grid)" />
        </svg>
      </div>

      {/* Main Network SVG */}
      <svg
        ref={svgRef}
        className="absolute inset-0 w-full h-full"
        viewBox="0 0 100 100"
        preserveAspectRatio="xMidYMid meet"
      >
        <defs>
          {/* Glow filter for links */}
          <filter id="glow">
            <feGaussianBlur stdDeviation="0.5" result="coloredBlur" />
            <feMerge>
              <feMergeNode in="coloredBlur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>

          {/* Radial gradient for nodes */}
          <radialGradient id="nodeGradient">
            <stop offset="0%" stopColor="#06b6d4" stopOpacity="1" />
            <stop offset="70%" stopColor="#0891b2" stopOpacity="0.8" />
            <stop offset="100%" stopColor="#0e7490" stopOpacity="0.6" />
          </radialGradient>
        </defs>

        {/* Links */}
        <g className="links">
          {links.map((link, i) => {
            const sourceNode = nodeMap.get(link.source);
            const targetNode = nodeMap.get(link.target);
            
            if (!sourceNode || !targetNode) return null;

            return (
              <motion.line
                key={`${link.source}-${link.target}-${i}`}
                x1={sourceNode.x}
                y1={sourceNode.y}
                x2={targetNode.x}
                y2={targetNode.y}
                stroke="#06b6d4"
                strokeWidth={0.3 + link.strength * 0.5}
                strokeOpacity={0.3 + link.strength * 0.3}
                filter="url(#glow)"
                initial={{ pathLength: 0, opacity: 0 }}
                animate={{
                  pathLength: 1,
                  opacity: 0.3 + link.strength * 0.3,
                }}
                transition={{
                  duration: 2,
                  delay: i * 0.1,
                }}
              />
            );
          })}
        </g>

        {/* Nodes */}
        <g className="nodes">
          {nodes.map((node, i) => (
            <g key={node.id}>
              {/* Outer pulse ring */}
              <motion.circle
                cx={node.x}
                cy={node.y}
                r={node.size}
                fill="none"
                stroke="#06b6d4"
                strokeWidth="0.3"
                strokeOpacity="0.6"
                animate={{
                  r: [node.size, node.size * 1.5, node.size],
                  strokeOpacity: [0.6, 0, 0.6],
                }}
                transition={{
                  duration: 3 + node.activity * 2,
                  repeat: Infinity,
                  ease: 'easeInOut',
                  delay: i * 0.3,
                }}
              />

              {/* Main node circle */}
              <motion.circle
                cx={node.x}
                cy={node.y}
                r={node.size * 0.6}
                fill="url(#nodeGradient)"
                filter="url(#glow)"
                initial={{ scale: 0, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{
                  duration: 0.5,
                  delay: i * 0.1,
                }}
                whileHover={{ scale: 1.2 }}
              />

              {/* Inner dot */}
              <motion.circle
                cx={node.x}
                cy={node.y}
                r={node.size * 0.2}
                fill="#ffffff"
                animate={{
                  opacity: [1, 0.3, 1],
                }}
                transition={{
                  duration: 2 + node.activity * 1.5,
                  repeat: Infinity,
                  ease: 'easeInOut',
                  delay: i * 0.2,
                }}
              />

              {/* Label */}
              <motion.text
                x={node.x}
                y={node.y + node.size + 3}
                textAnchor="middle"
                fill="#06b6d4"
                fontSize="3"
                fontFamily="monospace"
                fontWeight="bold"
                initial={{ opacity: 0 }}
                animate={{ opacity: 0.8 }}
                transition={{ duration: 0.5, delay: i * 0.1 + 0.5 }}
              >
                {node.label}
              </motion.text>
            </g>
          ))}
        </g>
      </svg>

      {/* Title Overlay */}
      <div className="absolute top-4 left-4 z-10">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 bg-cyan-400 rounded-full animate-pulse" />
          <span className="text-xs font-mono text-cyan-400 uppercase tracking-wider">
            Global Network
          </span>
        </div>
      </div>

      {/* Stats Overlay */}
      <div className="absolute bottom-4 left-4 z-10 space-y-1">
        <div className="text-xs font-mono text-slate-400">
          <span className="text-slate-500">Nodes:</span>{' '}
          <span className="text-cyan-400">{nodes.length}</span>
        </div>
        <div className="text-xs font-mono text-slate-400">
          <span className="text-slate-500">Routes:</span>{' '}
          <span className="text-cyan-400">{links.length}</span>
        </div>
      </div>
    </div>
  );
}


