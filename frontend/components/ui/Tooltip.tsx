'use client';

import React, { useState } from 'react';
import { cn } from '@/lib/utils';

interface TooltipProps {
    children: React.ReactNode;
    content: string;
    side?: 'right' | 'top' | 'bottom' | 'left';
    className?: string;
}

export default function Tooltip({ children, content, side = 'right', className }: TooltipProps) {
    const [isVisible, setIsVisible] = useState(false);

    return (
        <div
            className="relative flex items-center group"
            onMouseEnter={() => setIsVisible(true)}
            onMouseLeave={() => setIsVisible(false)}
        >
            {children}

            {/* Tooltip Content */}
            <div
                className={cn(
                    "absolute z-50 px-3 py-1.5 text-xs font-medium text-white bg-zinc-900 border border-white/10 rounded-md shadow-xl whitespace-nowrap pointer-events-none transition-all duration-200 opacity-0 scale-95 origin-left",
                    isVisible && "opacity-100 scale-100",
                    side === 'right' && "left-full ml-2 top-1/2 -translate-y-1/2",
                    side === 'left' && "right-full mr-2 top-1/2 -translate-y-1/2",
                    side === 'top' && "bottom-full mb-2 left-1/2 -translate-x-1/2",
                    side === 'bottom' && "top-full mt-2 left-1/2 -translate-x-1/2",
                    className
                )}
            >
                {content}
                {/* Arrow */}
                <div
                    className={cn(
                        "absolute w-2 h-2 bg-zinc-900 border-l border-b border-white/10 rotate-45",
                        side === 'right' && "left-[-5px] top-1/2 -translate-y-1/2",
                        side === 'left' && "right-[-5px] top-1/2 -translate-y-1/2 rotate-[225deg]",
                    )}
                />
            </div>
        </div>
    );
}
