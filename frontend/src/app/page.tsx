import Link from 'next/link';
import StepperBar from '@/components/StepperBar';
import CreditBalance from '@/components/CreditBalance';
import AIUseLog from '@/components/AIUseLog';
import { TiptapEditor } from '@/components/editor/TiptapEditor';

export default function LandingPage() {
  return (
    <div className="bg-white text-gray-800 antialiased overflow-x-hidden min-h-screen flex flex-col">
      {/* Navbar */}
      <nav className="fixed w-full z-50 top-0 bg-white/80 backdrop-blur-md border-b border-gray-100">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex justify-between items-center h-16">
          <div className="flex items-center space-x-2">
            <div className="w-8 h-8 bg-purple-600 rounded flex items-center justify-center text-white">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"></path>
              </svg>
            </div>
            <span className="font-bold text-xl text-gray-900">Agentic Writer</span>
          </div>
          <div className="hidden md:flex space-x-8 text-sm font-medium text-gray-600">
            <Link href="#" className="hover:text-purple-600 transition">Tính năng</Link>
            <Link href="/pricing" className="hover:text-purple-600 transition">Bảng giá</Link>
            <Link href="#" className="hover:text-purple-600 transition">Tài liệu hướng dẫn</Link>
          </div>
          
          <div className="flex items-center space-x-4">
            <CreditBalance />
            <Link href="/auth/signin" className="text-sm font-medium text-gray-600 hover:text-gray-900 transition">Đăng nhập</Link>
            <Link href="/auth/signup" className="bg-purple-600 text-white px-5 py-2 rounded-full text-sm font-medium hover:bg-purple-700 transition shadow-md hover:shadow-lg">Bắt đầu miễn phí</Link>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="pt-32 pb-10 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto flex flex-col items-center text-center flex-grow">
        <div className="inline-flex items-center bg-purple-50 text-purple-700 px-3 py-1 rounded-full text-sm font-medium mb-6 border border-purple-100">
          <span className="flex h-2 w-2 relative mr-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-purple-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-purple-500"></span>
          </span>
          Trợ lý AI Đa tác nhân dành riêng cho sinh viên Việt Nam
        </div>
        <h1 className="text-5xl md:text-6xl font-extrabold text-gray-900 tracking-tight leading-tight mb-6 max-w-4xl">
          Nghiên cứu khoa học dễ dàng hơn với <span className="text-transparent bg-clip-text bg-gradient-to-r from-purple-600 to-pink-500">AI Academic Coach</span>
        </h1>
        <p className="text-lg md:text-xl text-gray-500 mb-10 max-w-2xl">
          Không làm thay bạn, nhưng sẽ hướng dẫn bạn. Từ việc lập dàn ý, tra cứu tài liệu học thuật cho đến chuẩn hóa trích dẫn, hệ thống Multi-Agent sẽ giúp bạn hoàn thành luận văn với điểm số cao nhất.
        </p>
      </section>

      {/* KHU VỰC DEMO GIAO DIỆN (NỐI CODE FE1 & FE2) */}
      <section className="py-12 bg-white">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col gap-6 p-8 border-2 border-dashed border-purple-200 rounded-2xl bg-purple-50/30">
          <div className="text-center mb-4">
            <h2 className="text-2xl font-bold text-purple-800">Khu vực Demo Giao Diện (Task 14 & 15)</h2>
            <p className="text-gray-500 text-sm">Kết hợp Thanh tiến trình và Trình soạn thảo văn bản Tiptap</p>
          </div>
          
          {/* Thanh Stepper Bar (Của Vi) */}
          <StepperBar />

          {/* Trình soạn thảo văn bản (Của Bảo Châu) - Được bọc khung trắng bo góc */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden my-4 min-h-[300px]">
             <TiptapEditor />
          </div>

          {/* Bảng Lịch sử AI Use Log (Của Vi) */}
          <AIUseLog />
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20 bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-gray-900 mb-4">Quy trình 3 bước với hệ thống Đa tác nhân</h2>
            <p className="text-gray-500 max-w-2xl mx-auto">Mỗi tác nhân đảm nhiệm một vai trò chuyên biệt, phối hợp nhịp nhàng dưới sự kiểm soát của bạn.</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="bg-white p-8 rounded-2xl shadow-sm border border-gray-100 hover:shadow-md transition">
              <h3 className="text-xl font-bold text-gray-900 mb-3">Outline Agent</h3>
              <p className="text-gray-500 text-sm leading-relaxed mb-4">Tự động sinh dàn ý chuẩn hóa dựa trên đề tài và quy định của từng trường đại học.</p>
            </div>
            <div className="bg-white p-8 rounded-2xl shadow-sm border border-gray-100 hover:shadow-md transition">
              <h3 className="text-xl font-bold text-gray-900 mb-3">Literature Agent</h3>
              <p className="text-gray-500 text-sm leading-relaxed mb-4">Tìm kiếm và tổng hợp tài liệu tham khảo từ các nguồn học thuật uy tín thật 100%.</p>
            </div>
            <div className="bg-white p-8 rounded-2xl shadow-sm border border-gray-100 hover:shadow-md transition">
              <h3 className="text-xl font-bold text-gray-900 mb-3">Citation Agent</h3>
              <p className="text-gray-500 text-sm leading-relaxed mb-4">Quét toàn bộ bản nháp để tự động định dạng trích dẫn theo chuẩn (APA 7, IEEE).</p>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}