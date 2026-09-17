'use client';

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { authApi, UserProfile } from '@/lib/api';
import toast, { Toaster } from 'react-hot-toast';

interface Plan {
  id: string;
  name: string;
  price: string;
  credits: number;
  description: string;
  features: string[];
  isPopular?: boolean;
}

const PLANS: Plan[] = [
  {
    id: 'tieu_luan',
    name: 'Gói Tiểu Luận',
    price: '39.000đ',
    credits: 150,
    description: 'Phù hợp môn học & bài tập lớn',
    features: [
      '150 Credits cộng ngay',
      'Khoảng 75+ lần gọi AI',
      'Tự động mở rộng từ khóa quốc tế',
    ],
  },
  {
    id: 'khoa_luan',
    name: 'Gói Khóa Luận',
    price: '79.000đ',
    credits: 350,
    description: 'Tốt nhất cho đồ án & khóa luận tốt nghiệp',
    features: [
      '350 Credits cộng ngay',
      'Khoảng 200+ lần gọi AI',
      'Đầy đủ 3 nguồn arXiv, Scholar, OpenAlex',
      'Báo cáo minh bạch AI Use Log',
    ],
    isPopular: true,
  },
  {
    id: 'luan_van',
    name: 'Gói Luận Văn',
    price: '149.000đ',
    credits: 800,
    description: 'Dành cho học viên cao học & nghiên cứu sinh',
    features: [
      '800 Credits cộng ngay',
      'Không giới hạn số lượng dự án',
      'Ưu tiên hàng chờ xử lý Agent',
    ],
  },
];

export default function PricingPage() {
  const router = useRouter();
  const [user, setUser] = useState<UserProfile | null>(null);
  const [loadingUser, setLoadingUser] = useState(true);
  const [selectedPlan, setSelectedPlan] = useState<Plan | null>(null);

  useEffect(() => {
    async function checkAuth() {
      try {
        const me = await authApi.getMe();
        setUser(me);
      } catch {
        setUser(null);
      } finally {
        setLoadingUser(false);
      }
    }
    checkAuth();
  }, []);

  const handleCloseToHome = () => {
    router.push('/');
  };

  const handleSelectPlan = (plan: Plan) => {
    if (!user) {
      toast('Vui lòng đăng nhập để tiếp tục chọn gói cước', { icon: '🔐' });
      router.push(`/auth/signin?callbackUrl=/pricing`);
      return;
    }

    setSelectedPlan(plan);
  };

  return (
    <div className="bg-slate-900/60 min-h-screen flex items-center justify-center p-4 backdrop-blur-sm">
      <Toaster position="top-center" />

      {/* Pricing Modal Box */}
      <div className="bg-white w-full max-w-4xl rounded-2xl shadow-2xl border border-gray-100 overflow-hidden relative">
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-gray-100 flex justify-between items-center bg-gray-50/70">
          <div className="flex items-center space-x-2">
            <button
              type="button"
              onClick={handleCloseToHome}
              className="p-1.5 rounded-lg hover:bg-gray-200 text-gray-500 transition mr-1"
              title="Trở về trang chủ"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
            </button>
            <h2 className="text-lg font-bold text-gray-900 flex items-center">
              <span className="mr-2 text-xl">🪙</span> Bảng Giá & Nạp Thêm Credit
            </h2>
          </div>
          <button
            type="button"
            onClick={handleCloseToHome}
            className="text-gray-400 hover:text-gray-600 transition p-1.5 rounded-lg hover:bg-gray-100"
            title="Đóng và trở về trang chủ"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 md:p-8">
          {/* User Status Banner */}
          {user ? (
            <div className="mb-6 flex items-center justify-between bg-emerald-50 border border-emerald-200 rounded-xl p-3 text-xs text-emerald-800">
              <div className="flex items-center gap-2">
                <span className="text-sm">👤</span>
                <span>Tài khoản: <strong>{user.full_name || user.email}</strong></span>
              </div>
              <div className="font-semibold bg-emerald-100 px-2.5 py-1 rounded-full text-emerald-900">
                Số dư hiện tại: {user.credits ?? 0} Credits
              </div>
            </div>
          ) : !loadingUser && (
            <div className="mb-6 flex items-center justify-between bg-purple-50 border border-purple-200 rounded-xl p-3 text-xs text-purple-800">
              <div className="flex items-center gap-2">
                <span className="text-sm">💡</span>
                <span>Bạn chưa đăng nhập. Nhấn chọn gói bất kỳ để chuyển đến trang đăng nhập.</span>
              </div>
              <button
                onClick={() => router.push('/auth/signin?callbackUrl=/pricing')}
                className="font-semibold bg-purple-600 hover:bg-purple-700 text-white px-3 py-1 rounded-lg transition text-[11px]"
              >
                Đăng nhập ngay
              </button>
            </div>
          )}

          {/* Action-based pricing transparency banner */}
          <div className="mb-8 rounded-xl bg-purple-50 border border-purple-100 p-4 text-xs text-purple-900">
            <div className="font-semibold text-sm mb-1 text-purple-950 flex items-center gap-1.5">
              <span>💡</span> Định mức sử dụng minh bạch theo từng tác vụ AI:
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-2 font-medium">
              <div className="bg-white/80 rounded-lg p-2 border border-purple-100">
                📑 Sinh dàn ý: <span className="font-bold text-purple-700">2 Credits</span>
              </div>
              <div className="bg-white/80 rounded-lg p-2 border border-purple-100">
                🔍 Tìm tài liệu mới: <span className="font-bold text-purple-700">1 Credit</span>
              </div>
              <div className="bg-white/80 rounded-lg p-2 border border-purple-100">
                ⚡ Cache 48h: <span className="font-bold text-emerald-600">0 Credit (Free)</span>
              </div>
              <div className="bg-white/80 rounded-lg p-2 border border-purple-100">
                ✨ Hỏi AI / Viết lại: <span className="font-bold text-purple-700">1 Credit</span>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            {PLANS.map((plan) => (
              <div
                key={plan.id}
                className={`rounded-xl p-5 transition flex flex-col justify-between relative ${
                  plan.isPopular
                    ? 'border-2 border-purple-600 bg-purple-50/20 shadow-md'
                    : 'border border-gray-200 hover:border-purple-300'
                }`}
              >
                {plan.isPopular && (
                  <div className="absolute -top-3 right-4 bg-purple-600 text-white text-[10px] font-bold px-2.5 py-0.5 rounded-full uppercase tracking-wider">
                    Khuyên Dùng
                  </div>
                )}
                <div>
                  <h3 className="font-semibold text-gray-900 text-base mb-1">{plan.name}</h3>
                  <p className="text-xs text-gray-500 mb-3">{plan.description}</p>
                  <div className="text-purple-600 font-bold text-3xl mb-4">{plan.price}</div>
                  <ul className="text-xs text-gray-600 space-y-2.5 mb-6">
                    {plan.features.map((feature, idx) => (
                      <li key={idx} className="flex items-center">
                        <span className="text-emerald-500 font-bold mr-2">✓</span>
                        <span>{feature}</span>
                      </li>
                    ))}
                  </ul>
                </div>
                <button
                  type="button"
                  onClick={() => handleSelectPlan(plan)}
                  className={`w-full py-2.5 rounded-lg text-xs font-semibold transition ${
                    plan.isPopular
                      ? 'bg-purple-600 text-white hover:bg-purple-700 shadow-sm'
                      : 'bg-gray-100 text-gray-800 hover:bg-gray-200'
                  }`}
                >
                  {user ? `Chọn Gói (${plan.price})` : 'Đăng nhập & Chọn Gói'}
                </button>
              </div>
            ))}
          </div>

          <div className="mt-8 flex justify-center items-center space-x-3 text-xs text-gray-400">
            <span>Thanh toán an toàn qua:</span>
            <span className="font-semibold text-gray-600 border px-2.5 py-1 rounded bg-gray-50">MoMo QR</span>
            <span className="font-semibold text-gray-600 border px-2.5 py-1 rounded bg-gray-50">VNPay QR</span>
            <span className="font-semibold text-gray-600 border px-2.5 py-1 rounded bg-gray-50">Chuyển khoản 24/7</span>
          </div>
        </div>
      </div>

      {/* Modal Xử Lý Thanh Toán (Sandbox Mockup) */}
      {selectedPlan && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <div className="flex justify-between items-center border-b pb-3">
              <h3 className="font-bold text-gray-900 text-base flex items-center gap-2">
                <span>💳</span> Xác Nhận Thanh Toán
              </h3>
              <button
                onClick={() => setSelectedPlan(null)}
                className="text-gray-400 hover:text-gray-600 text-lg"
              >
                ✕
              </button>
            </div>

            <div className="bg-purple-50 p-4 rounded-xl space-y-2 text-xs text-purple-900">
              <div className="flex justify-between">
                <span>Gói cước đã chọn:</span>
                <strong className="font-bold">{selectedPlan.name}</strong>
              </div>
              <div className="flex justify-between">
                <span>Số Credit nhận được:</span>
                <strong className="text-purple-700 font-bold">+{selectedPlan.credits} Credits</strong>
              </div>
              <div className="flex justify-between text-sm pt-2 border-t border-purple-200 text-purple-950">
                <span className="font-semibold">Tổng thanh toán:</span>
                <span className="font-bold text-purple-700 text-base">{selectedPlan.price}</span>
              </div>
            </div>

            <div className="text-xs text-gray-500 bg-amber-50 border border-amber-200 rounded-lg p-3">
              ℹ️ Cổng thanh toán MoMo / VNPay đang được cấu hình Sandbox. Khi hoàn tất xác nhận, hệ thống webhook sẽ tự động cập nhật số dư cho tài khoản <strong>{user?.email}</strong>.
            </div>

            <div className="flex gap-2 pt-2">
              <button
                type="button"
                onClick={() => setSelectedPlan(null)}
                className="flex-1 py-2.5 rounded-lg border border-gray-200 text-xs font-medium text-gray-600 hover:bg-gray-50"
              >
                Hủy
              </button>
              <button
                type="button"
                onClick={() => {
                  toast.success(`Đã ghi nhận yêu cầu nạp ${selectedPlan.name}! Vui lòng đợi kết nối cổng thanh toán.`);
                  setSelectedPlan(null);
                }}
                className="flex-1 py-2.5 rounded-lg bg-purple-600 hover:bg-purple-700 text-xs font-semibold text-white transition shadow-sm"
              >
                Tiến Hành Thanh Toán
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}