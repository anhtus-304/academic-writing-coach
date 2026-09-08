'use client';

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { creditApi } from '@/lib/api';

interface CreditBalanceProps {
  initialBalance?: number;
  refreshTrigger?: number | string;
}

export function CreditBalance({ initialBalance, refreshTrigger }: CreditBalanceProps) {
  const router = useRouter();
  const [balance, setBalance] = useState<number | null>(initialBalance !== undefined ? initialBalance : null);
  const [loading, setLoading] = useState(initialBalance === undefined);

  useEffect(() => {
    let isMounted = true;
    async function fetchBalance() {
      try {
        const res = await creditApi.getBalance();
        if (isMounted) {
          setBalance(res.balance);
        }
      } catch {
        // Fallback to default initial or 0 if unauthenticated
        if (isMounted) {
          setBalance((prev) => (prev === null ? 100 : prev));
        }
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    fetchBalance();
    return () => {
      isMounted = false;
    };
  }, [refreshTrigger]);

  const handleNavigateToPricing = () => {
    router.push('/pricing');
  };

  return (
    <button
      onClick={handleNavigateToPricing}
      title="Bấm để xem các gói nạp thêm Credit"
      className="inline-flex items-center gap-1.5 bg-amber-50 border border-amber-200 text-amber-800 hover:bg-amber-100 px-3.5 py-1.5 rounded-full text-xs font-semibold shadow-sm transition active:scale-95"
    >
      <span className="text-sm">🪙</span>
      <span>{loading ? 'Đang tải...' : `${balance ?? 0} Credits`}</span>
      <span className="text-[10px] bg-amber-200/70 text-amber-900 px-1.5 py-0.5 rounded-full font-medium ml-1">
        + Nạp
      </span>
    </button>
  );
}

export default CreditBalance;