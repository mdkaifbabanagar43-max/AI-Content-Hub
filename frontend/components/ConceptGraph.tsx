import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Sparkles, Zap, Eye, Video, ShieldAlert, Layers } from 'lucide-react';

interface ConceptNode {
  id: number;
  title: string;
  hook: string;
  mood?: string;
}

interface ConceptGraphProps {
  topic: string;
  concepts: ConceptNode[];
  onSelectConcept: (concept: ConceptNode) => void;
}

export const ConceptGraph: React.FC<ConceptGraphProps> = ({ topic, concepts, onSelectConcept }) => {
  const [activeNodeId, setActiveNodeId] = useState<number | null>(null);

  // Layout math for 4 radial nodes around a central topic node
  const centerX = 350;
  const centerY = 250;
  const radius = 170;

  const nodes = concepts.map((c, idx) => {
    const angle = (idx * (2 * Math.PI)) / Math.max(concepts.length, 1) - Math.PI / 2;
    const x = centerX + radius * Math.cos(angle);
    const y = centerY + radius * Math.sin(angle);
    return { ...c, x, y };
  });

  return (
    <div className="w-full bg-zinc-950/80 border border-zinc-800/80 rounded-3xl p-6 relative overflow-hidden shadow-2xl backdrop-blur-xl flex flex-col items-center">
      {/* Background Glows */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-purple-600/10 rounded-full blur-3xl pointer-events-none animate-pulse" />
      <div className="absolute top-1/4 left-1/3 w-64 h-64 bg-pink-500/10 rounded-full blur-3xl pointer-events-none" />

      <div className="w-full flex justify-between items-center mb-4 z-10">
        <div className="flex items-center gap-2">
          <Layers className="text-purple-400" size={20} />
          <h3 className="text-lg font-bold text-white tracking-tight">Interactive Concept Graph</h3>
        </div>
        <span className="text-xs text-zinc-500 font-mono">Click a node to generate script</span>
      </div>

      <div className="relative w-full max-w-[700px] h-[500px] flex items-center justify-center">
        <svg className="absolute inset-0 w-full h-full pointer-events-none">
          {/* Connecting Lines */}
          {nodes.map((node) => (
            <g key={`edge-${node.id}`}>
              <line
                x1={centerX}
                y1={centerY}
                x2={node.x}
                y2={node.y}
                stroke={activeNodeId === node.id ? "#c084fc" : "#3f3f46"}
                strokeWidth={activeNodeId === node.id ? "3" : "1.5"}
                strokeDasharray="4 4"
                className="transition-all duration-300"
              />
              {/* Pulse particle along line */}
              <circle r="3" fill="#a855f7">
                <animateMotion
                  path={`M${centerX},${centerY} L${node.x},${node.y}`}
                  dur={`${2 + node.id * 0.5}s`}
                  repeatCount="indefinite"
                />
              </circle>
            </g>
          ))}
        </svg>

        {/* Central Topic Node */}
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          className="absolute -translate-x-1/2 -translate-y-1/2 z-20"
          style={{ left: centerX, top: centerY }}
        >
          <div className="w-32 h-32 rounded-full bg-gradient-to-br from-purple-600 via-indigo-600 to-pink-600 p-[2px] shadow-[0_0_30px_rgba(168,85,247,0.3)]">
            <div className="w-full h-full bg-zinc-950 rounded-full flex flex-col items-center justify-center p-3 text-center">
              <Sparkles size={20} className="text-purple-400 mb-1 animate-spin" style={{ animationDuration: '8s' }} />
              <span className="text-[11px] font-bold text-zinc-300 line-clamp-2 uppercase tracking-wider">{topic || "Topic Core"}</span>
            </div>
          </div>
        </motion.div>

        {/* Concept Nodes */}
        {nodes.map((node) => {
          const isSelected = activeNodeId === node.id;
          return (
            <motion.div
              key={node.id}
              initial={{ scale: 0, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ delay: node.id * 0.1 }}
              whileHover={{ scale: 1.08 }}
              onHoverStart={() => setActiveNodeId(node.id)}
              onHoverEnd={() => setActiveNodeId(null)}
              onClick={() => onSelectConcept(node)}
              className="absolute -translate-x-1/2 -translate-y-1/2 z-30 cursor-pointer"
              style={{ left: node.x, top: node.y }}
            >
              <div className={`w-44 p-4 rounded-2xl border backdrop-blur-md transition-all duration-300 shadow-xl ${
                isSelected 
                  ? 'bg-purple-950/80 border-purple-500 shadow-[0_0_25px_rgba(168,85,247,0.4)] text-white' 
                  : 'bg-zinc-900/90 border-zinc-800 hover:border-zinc-700 text-zinc-300'
              }`}>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[10px] font-black uppercase px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-300 border border-purple-500/30">
                    Angle #{node.id}
                  </span>
                  {node.mood && (
                    <span className="text-[10px] text-zinc-400 font-medium">
                      {node.mood}
                    </span>
                  )}
                </div>
                <h4 className="text-xs font-bold leading-tight mb-1 text-white line-clamp-2">{node.title}</h4>
                <p className="text-[10px] text-zinc-400 italic line-clamp-2">"{node.hook}"</p>
                
                <div className="mt-3 pt-2 border-t border-zinc-800/80 flex items-center justify-between text-[10px] text-purple-400 font-bold">
                  <span>Generate Script</span>
                  <Zap size={12} fill="currentColor" />
                </div>
              </div>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
};
