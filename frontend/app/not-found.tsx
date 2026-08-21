import Link from 'next/link';
import { WifiOff } from 'lucide-react';

export default function NotFound() {
    return (
        <div className="min-h-screen bg-[#030303] flex flex-col items-center justify-center text-center p-6 font-sans selection:bg-red-500/30">

            <div className="mb-8 relative">
                <h1 className="text-[150px] font-mono font-bold text-white/5 leading-none select-none">404</h1>
                <div className="absolute inset-0 flex items-center justify-center text-red-500 animate-pulse">
                    <WifiOff size={64} />
                </div>
            </div>

            <h2 className="text-3xl font-bold text-white mb-2 tracking-tight">Signal Lost.</h2>
            <p className="text-zinc-500 max-w-md mb-10">
                The page you are looking for has been hallucinated or removed from the matrix.
            </p>

            <Link
                href="/"
                className="px-8 py-3 bg-white text-black font-bold rounded-full hover:bg-zinc-200 transition-colors shadow-lg shadow-white/10"
            >
                Return to Dashboard
            </Link>
        </div>
    );
}
