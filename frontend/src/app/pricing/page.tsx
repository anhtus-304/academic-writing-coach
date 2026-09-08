'use client';

import React from 'react';
import { useRouter } from 'next/navigation';

export default function PricingPage() {
  const router = useRouter();

  const handleGoBack = () => {
    if (typeof window !== 'undefined' && window.history.length > 1) {
      router.back();
    } else {
      router.push('/dashboard');
    }
  };

  return (
    <div className="bg-slate-900/50 min-h-screen flex items-center justify-center p-4 backdrop-blur-sm">
      {/* Pricing Modal Box */}
      <div className="bg-white w-full max-w-4xl rounded-2xl shadow-2xl border border-gray-100 overflow-hidden relative">
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-gray-100 flex justify-between items-center bg-gray-50/70">
          <div className="flex items-center space-x-2">
            <button
              type="button"
              onClick={handleGoBack}
              className="p-1 rounded-lg hover:bg-gray-200 text-gray-500 transition mr-2"
              title="Quay lại"
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
            onClick={handleGoBack}
            className="text-gray-400 hover:text-gray-600 transition p-1 rounded-lg"
            title="Đóng"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 md:p-8">
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
                ⚡ Cache 48h: <span className="font-bold text-emerald-600">0 Credit (Miễn phí)</span>
              </div>
              <div className="bg-white/80 rounded-lg p-2 border border-purple-100">
                ✨ Hỏi AI / Viết lại: <span className="font-bold text-purple-700">1 Credit</span>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            {/* Package 1 */}
            <div className="border border-gray-200 rounded-xl p-5 hover:border-purple-300 transition flex flex-col justify-between">
              <div>
                <h3 className="font-semibold text-gray-900 text-base mb-1">Gói Tiểu Luận</h3>
                <p className="text-xs text-gray-500 mb-3">Phù hợp môn học & bài tập lớn</p>
                <div className="text-purple-600 font-bold text-3xl mb-4">39.000đ</div>
                <ul className="text-xs text-gray-600 space-y-2.5 mb-6">
                  <li className="flex items-center">
                    <span className="text-emerald-500 font-bold mr-2">✓</span>
                    <strong className="text-gray-800 mr-1">150 Credits</strong> cộng ngay
                  </li>
                  <li className="flex items-center">
                    <span className="text-emerald-500 font-bold mr-2">✓</span>
                    Khoảng 75+ lần gọi AI
                  </li>
                  <li className="flex items-center">
                    <span className="text-emerald-500 font-bold mr-2">✓</span>
                    Tự động mở rộng từ khóa quốc tế
                  </li>
                </ul>
              </div>
              <button
                type="button"
                onClick={() => alert('Chức năng tích hợp cổng thanh toán Sandbox MoMo/VNPay đang được chuẩn bị. Vui lòng liên hệ Admin để nhận mã voucher nạp thử nghiệm!')}
                className="w-full bg-gray-100 text-gray-800 py-2.5 rounded-lg text-xs font-semibold hover:bg-gray-200 transition"
              >
                Chọn Gói Này
              </button>
            </div>

            {/* Package 2 (Popular) */}
            <div className="border-2 border-purple-600 rounded-xl p-5 bg-purple-50/20 relative shadow-md flex flex-col justify-between">
              <div className="absolute -top-3 right-4 bg-purple-600 text-white text-[10px] font-bold px-2.5 py-0.5 rounded-full uppercase tracking-wider">
                Khuyên Dùng
              </div>
              <div>
                <h3 className="font-semibold text-gray-900 text-base mb-1">Gói Khóa Luận</h3>
                <p className="text-xs text-gray-500 mb-3">Tốt nhất cho đồ án & khóa luận tốt nghiệp</p>
                <div className="text-purple-600 font-bold text-3xl mb-4">79.000đ</div>
                <ul className="text-xs text-gray-600 space-y-2.5 mb-6">
                  <li className="flex items-center">
                    <span className="text-emerald-500 font-bold mr-2">✓</span>
                    <strong className="text-gray-800 mr-1">350 Credits</strong> cộng ngay
                  </li>
                  <li className="flex items-center">
                    <span className="text-emerald-500 font-bold mr-2">✓</span>
                    Khoảng 200+ lần gọi AI
                  </li>
                  <li className="flex items-center">
                    <span className="text-emerald-500 font-bold mr-2">✓</span>
                    Đầy đủ 3 nguồn arXiv, Scholar, OpenAlex
                  </li>
                  <li className="flex items-center">
                    <span className="text-emerald-500 font-bold mr-2">✓</span>
                    Báo cáo minh bạch AI Use Log
                  </li>
                </ul>
              </div>
              <button
                type="button"
                onClick={() => alert('Chức năng tích hợp cổng thanh toán Sandbox MoMo/VNPay đang được chuẩn bị. Vui lòng liên hệ Admin để nhận mã voucher nạp thử nghiệm!')}
                className="w-full bg-purple-600 text-white py-2.5 rounded-lg text-xs font-semibold hover:bg-purple-700 shadow-sm transition"
              >
                Nạp Ngay (79k)
              </button>
            </div>

            {/* Package 3 */}
            <div className="border border-gray-200 rounded-xl p-5 hover:border-purple-300 transition flex flex-col justify-between">
              <div>
                <h3 className="font-semibold text-gray-900 text-base mb-1">Gói Luận Văn</h3>
                <p className="text-xs text-gray-500 mb-3">Dành cho học viên cao học & nghiên cứu sinh</p>
                <div className="text-purple-600 font-bold text-3xl mb-4">149.000đ</div>
                <ul className="text-xs text-gray-600 space-y-2.5 mb-6">
                  <li className="flex items-center">
                    <span className="text-emerald-500 font-bold mr-2">✓</span>
                    <strong className="text-gray-800 mr-1">800 Credits</strong> cộng ngay
                  </li>
                  <li className="flex items-center">
                    <span className="text-emerald-500 font-bold mr-2">✓</span>
                    Không giới hạn số lượng dự án
                  </li>
                  <li className="flex items-center">
                    <span className="text-emerald-500 font-bold mr-2">✓</span>
                    Ưu tiên hàng chờ xử lý Agent
                  </li>
                </ul>
              </div>
              <button
                type="button"
                onClick={() => alert('Chức năng tích hợp cổng thanh toán Sandbox MoMo/VNPay đang được chuẩn bị. Vui lòng liên hệ Admin để nhận mã voucher nạp thử nghiệm!')}
                className="w-full bg-gray-100 text-gray-800 py-2.5 rounded-lg text-xs font-semibold hover:bg-gray-200 transition"
              >
                Chọn Gói Này
              </button>
            </div>
          </div>

          <div className="mt-8 flex justify-center items-center space-x-3 text-xs text-gray-400">
            <span>Thanh toán an toàn qua:</span>
            <span className="font-semibold text-gray-600 border px-2.5 py-1 rounded bg-gray-50">MoMo QR</span>
            <span className="font-semibold text-gray-600 border px-2.5 py-1 rounded bg-gray-50">VNPay QR</span>
            <span className="font-semibold text-gray-600 border px-2.5 py-1 rounded bg-gray-50">Chuyển khoản 24/7</span>
          </div>
        </div>
      </div>
    </div>
  );
}