"use client";

import React from 'react';
import { User, Zap, Building2, Check, HelpCircle, AlertCircle } from 'lucide-react';
import { usePlan } from '../../context/PlanContext';
import { cn } from '../../lib/utils';
import MockCheckout from '../payment/MockCheckout';
import { useRouter } from 'next/navigation';
import { useAuth } from '../../context/AuthContext';

export default function Pricing() {
    const { userPlan, upgradePlan } = usePlan();
    const { user } = useAuth();
    const router = useRouter();
    const [checkoutPlan, setCheckoutPlan] = React.useState<{ id: string, name: string, price: string, numericCredits: number } | null>(null);
    const [billingCycle, setBillingCycle] = React.useState<'monthly' | 'yearly'>('monthly');

    const handleSelectPlan = (plan: any) => {
        if (!user) {
            router.push('/login');
            return;
        }
        if (userPlan === plan.id) return;
        setCheckoutPlan({
            id: plan.id,
            name: plan.name,
            price: billingCycle === 'yearly' ? plan.yearlyPriceStr : plan.price,
            numericCredits: plan.numericCredits
        });
    };

    const handleCheckoutSuccess = (planId: string) => {
        const selectedPlan = plans.find(p => p.id === planId);
        if (selectedPlan) {
            upgradePlan(planId, selectedPlan.numericCredits);
        }
        setCheckoutPlan(null);
    };

    // 🧠 PRICING STRATEGY: 3 PLANS
    const plans = [
        {
            id: 'starter',
            name: 'Starter',
            price: '$19',
            yearlyPriceStr: '$15',
            description: 'For solopreneurs testing the waters',
            positioning: 'Best for testing the platform & occasional creators',
            credits: '500 Credits / mo',
            numericCredits: 500,
            outputs: [
                '≈ 50 Mins Repurposing',
                'or ≈ 25 Mins Dubbing*'
            ],
            features: [
                'Generous AI Script Generation',
                'Auto-Captions & Subtitles',
                'Viral Templates (Hormozi)',
                '10 Min Video Limit',
                '720p with Watermark'
            ],
            icon: User,
            cta: 'Try Starter'
        },
        {
            id: 'creator',
            name: 'Creator',
            price: '$49',
            yearlyPriceStr: '$39',
            description: 'For consistent content growth',
            positioning: 'Best for daily creators & small teams',
            credits: '2,000 Credits / mo',
            numericCredits: 2000,
            outputs: [
                '≈ 200 Mins Repurposing',
                'or ≈ 100 Mins Dubbing*'
            ],
            features: [
                'Everything in Starter +',
                'Smart Face Tracking (Uses more credits)',
                'Premium "Human" Voices',
                '30 Min Video Limit',
                'No Watermark (1080p)',
                'Priority Rendering'
            ],
            icon: Zap,
            highlight: true,
            cta: 'Get Creator Plan'
        },
        {
            id: 'agency',
            name: 'Agency',
            price: '$199',
            yearlyPriceStr: '$159',
            description: 'For teams & power users',
            credits: '10,000 Credits / mo',
            numericCredits: 10000,
            outputs: [
                '≈ 1000 Mins Repurposing',
                'or ≈ 500 Mins Dubbing*'
            ],
            features: [
                'Everything in Creator +',
                'Bulk Upload & Export',
                '4K Ultra HD Export',
                '60 Min Video Limit',
                '10 Concurrent Jobs',
                'Dedicated Support'
            ],
            protection: 'Designed for teams & agencies. Fair-use limits apply.',
            icon: Building2,
            cta: 'Scale Up'
        }
    ];

    return (
        <div className="py-16 sm:py-24 font-sans">
            <div className="w-full max-w-[1400px] mx-auto px-6 lg:px-8">

                {/* Header */}
                <div className="mx-auto max-w-4xl text-center mb-16">
                    <h2 className="text-xl font-bold text-indigo-400 mb-4 uppercase tracking-wider">Simple Pricing</h2>
                    <p className="text-5xl md:text-7xl font-black tracking-tight text-white mb-6">
                        Pay for outcomes. <br /> Not confusing credits.
                    </p>
                    <div className="bg-indigo-500/10 border border-indigo-500/20 rounded-lg inline-block px-4 py-2 mb-6">
                        <p className="text-lg text-indigo-300 font-bold flex items-center gap-2">
                            ✅ Preview scripts, voices & clips before credits are used.
                        </p>
                    </div>

                    <p className="text-xl text-zinc-400 mb-10 max-w-2xl mx-auto">
                        Transparent pricing designed for creators. No hidden limits.
                    </p>

                    {/* Toggle */}
                    <div className="flex items-center justify-center gap-6 mb-12">
                        <span className={cn("text-lg font-bold transition-colors", billingCycle === 'monthly' ? "text-white" : "text-zinc-500")}>Monthly</span>
                        <button
                            onClick={() => setBillingCycle(billingCycle === 'monthly' ? 'yearly' : 'monthly')}
                            className="relative w-20 h-10 rounded-full bg-zinc-800 border border-zinc-700 transition-colors hover:bg-zinc-700"
                        >
                            <div className={cn(
                                "absolute top-1 left-1 w-8 h-8 rounded-full bg-white shadow-lg transition-transform duration-300",
                                billingCycle === 'yearly' ? "translate-x-10" : "translate-x-0"
                            )} />
                        </button>
                        <span className={cn("text-lg font-bold transition-colors flex items-center gap-2", billingCycle === 'yearly' ? "text-white" : "text-zinc-500")}>
                            Yearly
                            <span className="bg-green-500/20 text-green-400 text-xs px-3 py-1 rounded-full font-bold">SAVE 20%</span>
                        </span>
                    </div>

                    {/* 🧠 CREDIT EXPLANATION (Trust Builder) */}
                    <div className="bg-zinc-900/40 border border-zinc-800 rounded-2xl p-6 md:p-8 max-w-3xl mx-auto backdrop-blur-sm">
                        <div className="flex items-center justify-center gap-3 mb-6">
                            <HelpCircle className="text-indigo-400" size={24} />
                            <h3 className="text-xl font-bold text-white">How do credits work?</h3>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-left">
                            <div className="bg-black/20 p-4 rounded-xl border border-white/5">
                                <p className="text-zinc-500 text-sm font-bold uppercase mb-2">Fair Usage</p>
                                <p className="text-zinc-300 text-sm">Credits are only deducted when you <span className="text-white font-bold">export</span>. Previews & drafting are free.</p>
                            </div>
                            <div className="bg-black/20 p-4 rounded-xl border border-white/5">
                                <p className="text-zinc-500 text-sm font-bold uppercase mb-2">Shorts</p>
                                <p className="text-white font-bold text-lg">1 Short Video</p>
                                <p className="text-zinc-400 text-sm">≈ 5-10 Credits</p>
                            </div>
                            <div className="bg-black/20 p-4 rounded-xl border border-white/5">
                                <p className="text-zinc-500 text-sm font-bold uppercase mb-2">Dubbing</p>
                                <p className="text-white font-bold text-lg">1 Minute Dub</p>
                                <p className="text-zinc-400 text-sm">≈ 10 Credits</p>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Pricing Grid */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start max-w-7xl mx-auto">
                    {plans.map((plan) => (
                        <div
                            key={plan.id}
                            onClick={() => handleSelectPlan(plan)}
                            className={cn(
                                "relative flex flex-col p-8 rounded-[32px] transition-all duration-300 cursor-pointer border",
                                plan.highlight
                                    ? "bg-gradient-to-b from-zinc-900 to-black border-indigo-500 shadow-2xl shadow-indigo-500/10 scale-105 z-10"
                                    : "bg-black/40 border-zinc-800 hover:border-zinc-600 hover:bg-zinc-900/40",
                                userPlan === plan.id ? "ring-2 ring-indigo-500" : ""
                            )}
                        >
                            {plan.highlight && (
                                <div className="absolute -top-4 left-0 right-0 mx-auto w-max px-6 py-1.5 rounded-full bg-indigo-600 text-white text-xs font-bold tracking-widest shadow-lg uppercase">
                                    Most Popular
                                </div>
                            )}

                            {/* Plan Header */}
                            <div className="mb-6">
                                <div className="flex items-center gap-3 mb-4">
                                    <div className={cn("p-3 rounded-xl", plan.highlight ? "bg-indigo-500/20 text-indigo-400" : "bg-zinc-800 text-zinc-400")}>
                                        <plan.icon size={24} />
                                    </div>
                                    <h3 className="text-2xl font-bold text-white">{plan.name}</h3>
                                </div>
                                <p className="text-zinc-400 text-sm min-h-[20px] mb-2">{plan.description}</p>
                                {/* Positioning Text */}
                                {plan.positioning && (
                                    <p className="text-xs text-indigo-400 font-bold uppercase tracking-wide">
                                        {plan.positioning}
                                    </p>
                                )}
                            </div>

                            {/* Price */}
                            <div className="mb-8">
                                <div className="flex items-baseline gap-1">
                                    <span className="text-5xl font-black text-white">
                                        {billingCycle === 'monthly' ? plan.price : plan.yearlyPriceStr}
                                    </span>
                                    <span className="text-zinc-500 font-medium">/ month</span>
                                </div>
                                {billingCycle === 'yearly' && (
                                    <p className="text-sm text-green-400 mt-2 font-medium">Billed yearly</p>
                                )}
                            </div>

                            {/* Credits & Outcomes */}
                            <div className="bg-white/5 rounded-2xl p-6 mb-8 border border-white/5">
                                <p className="text-white font-black text-lg mb-4 flex items-center gap-2">
                                    <Zap size={18} className="text-yellow-400 fill-current" /> {plan.credits}
                                </p>
                                <div className="space-y-2">
                                    {plan.outputs.map((out, i) => (
                                        <p key={i} className="text-zinc-300 text-sm flex items-center gap-2">
                                            <span className="w-1.5 h-1.5 rounded-full bg-indigo-500"></span>
                                            {out}
                                        </p>
                                    ))}
                                </div>
                                {plan.protection && (
                                    <p className="mt-3 text-[10px] text-zinc-500 font-medium italic border-t border-white/5 pt-2">
                                        {plan.protection}
                                    </p>
                                )}
                            </div>

                            {/* Features */}
                            <ul className="space-y-4 mb-8 flex-1">
                                {plan.features.map((feature, i) => (
                                    <li key={i} className="flex items-start gap-3 text-zinc-300 text-sm">
                                        <Check className={cn("w-5 h-5 shrink-0", plan.highlight ? "text-indigo-400" : "text-zinc-500")} />
                                        {feature}
                                    </li>
                                ))}
                            </ul>

                            {/* CTA */}
                            <button
                                onClick={(e) => {
                                    e.stopPropagation();
                                    handleSelectPlan(plan);
                                }}
                                disabled={!!user && userPlan === plan.id}
                                className={cn(
                                    "w-full py-4 rounded-xl font-bold transition-all text-base",
                                    // 1. Current Plan -> Grey & Disabled
                                    (!!user && userPlan === plan.id)
                                        ? "bg-zinc-800 text-zinc-500 border border-zinc-700 opacity-50 cursor-not-allowed"
                                        : plan.highlight
                                            ? "bg-indigo-600 text-white hover:bg-indigo-500 shadow-lg shadow-indigo-600/25"
                                            : "bg-white text-black hover:bg-zinc-200"
                                )}
                            >
                                {(() => {
                                    if (!user) return plan.cta; // Use Custom CTA text
                                    if (userPlan === plan.id) return "Current Plan";
                                    return `Switch to ${plan.name}`;
                                })()}
                            </button>

                            {/* Trust Badge */}
                            <div className="mt-4 flex flex-col items-center justify-center gap-2 text-[11px] text-zinc-500 font-medium">
                                <div className="flex items-center gap-2">
                                    <AlertCircle size={12} />
                                    No hidden fees. Cancel anytime.
                                </div>
                            </div>
                        </div>
                    ))}
                </div>

                {/* Global Bottom Footnote */}
                <div className="max-w-3xl mx-auto text-center mt-12 text-zinc-500 text-sm italic">
                    *Actual credit usage depends on video length, language, voice selection, and processing options.
                </div>
            </div>

            <MockCheckout
                isOpen={!!checkoutPlan}
                planName={checkoutPlan?.name || ''}
                price={checkoutPlan?.price || ''}
                onSuccess={() => handleCheckoutSuccess(checkoutPlan?.id || 'starter')}
                onClose={() => setCheckoutPlan(null)}
            />
        </div>
    );
}
