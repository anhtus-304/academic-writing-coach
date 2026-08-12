import Link from 'next/link';

export default function PricingPage() {
  return (
    <div className="bg-gray-800/40 min-h-screen flex items-center justify-center p-4 backdrop-blur-sm">
      {/* Modal Box */}
      <div className="bg-white w-full max-w-2xl rounded-2xl shadow-2xl border border-gray-100 overflow-hidden relative">
        
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-gray-100 flex justify-between items-center bg-gray-50/50">
          <h2 className="text-lg font-bold text-gray-900 flex items-center">
            <span className="mr-2 text-xl">🪙</span> Nạp thêm Credit
          </h2>
          <Link href="/dashboard" className="text-gray-400 hover:text-gray-600 transition">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12"></path>
            </svg>
          </Link>
        </div>

        {/* Modal Body */}
        <div className="p-6">
          <p className="text-gray-600 text-sm mb-6 text-center">
            Credit được sử dụng để gọi các Tác nhân AI (Outline, Literature, Citation).<br />
            1 Lần gọi Agent = 10 Credits.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* Package 1 */}
            <div className="border-2 border-gray-200 rounded-xl p-5 hover:border-purple-500 cursor-pointer transition relative">
              <h3 className="font-semibold text-gray-900 text-lg mb-1">Gói Cơ Bản</h3>
              <div className="text-purple-600 font-bold text-2xl mb-3">50.000đ</div>
              <ul className="text-sm text-gray-600 space-y-2 mb-4">
                <li className="flex items-center">
                  <svg className="w-4 h-4 text-green-500 mr-2 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7"></path>
                  </svg> 
                  500 Credits
                </li>
                <li className="flex items-center">
                  <svg className="w-4 h-4 text-green-500 mr-2 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7"></path>
                  </svg> 
                  Khoảng 50 lần gọi AI
                </li>
              </ul>
              <button className="w-full bg-gray-100 text-gray-800 py-2 rounded-lg text-sm font-medium hover:bg-gray-200 transition">
                Chọn gói này
              </button>
            </div>

            {/* Package 2 (Popular) */}
            <div className="border-2 border-purple-500 rounded-xl p-5 cursor-pointer bg-purple-50/30 relative shadow-sm">
              <div className="absolute -top-3 right-4 bg-purple-600 text-white text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider">
                Khuyên dùng
              </div>
              <h3 className="font-semibold text-gray-900 text-lg mb-1">Gói Chuyên Sâu</h3>
              <div className="text-purple-600 font-bold text-2xl mb-3">120.000đ</div>
              <ul className="text-sm text-gray-600 space-y-2 mb-4">
                <li className="flex items-center">
                  <svg className="w-4 h-4 text-green-500 mr-2 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7"></path>
                  </svg> 
                  1500 Credits
                </li>
                <li className="flex items-center">
                  <svg className="w-4 h-4 text-green-500 mr-2 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7"></path>
                  </svg> 
                  Tặng kèm AI Use Log Export
                </li>
              </ul>
              <button className="w-full bg-purple-600 text-white py-2 rounded-lg text-sm font-medium hover:bg-purple-700 shadow-sm transition">
                Chọn gói này
              </button>
            </div>
          </div>

          <div className="mt-6 flex justify-center items-center space-x-2 text-xs text-gray-400">
            <span>Hỗ trợ thanh toán qua:</span>
            <span className="font-semibold text-gray-600 border px-2 py-1 rounded bg-gray-50">MoMo</span>
            <span className="font-semibold text-gray-600 border px-2 py-1 rounded bg-gray-50">VNPay</span>
          </div>
        </div>

      </div>
    </div>
  );
}