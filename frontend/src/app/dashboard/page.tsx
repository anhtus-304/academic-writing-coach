import Link from 'next/link';

export default function DashboardPage() {
  return (
    <div className="bg-gray-50 min-h-screen flex flex-col font-sans text-gray-800">
      {/* Top Navigation */}
      <header className="bg-white h-16 border-b border-gray-200 flex items-center justify-between px-8">
        <div className="flex items-center space-x-3">
          <Link href="/" className="flex items-center space-x-3">
            <div className="w-8 h-8 bg-purple-600 rounded flex items-center justify-center text-white">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"></path>
              </svg>
            </div>
            <span className="font-bold text-lg text-gray-900">Agentic Writer</span>
          </Link>
        </div>
        <div className="flex items-center space-x-6">
          <Link href="/pricing" className="bg-purple-50 text-purple-700 px-3 py-1.5 rounded-full text-sm font-medium flex items-center hover:bg-purple-100 transition">
            <span className="mr-2">🪙</span> 120 Credits
          </Link>
          <div className="flex items-center space-x-2 border-l border-gray-200 pl-6">
            <div className="text-right">
              <div className="text-sm font-semibold text-gray-900">Thúy Vi</div>
              <div className="text-xs text-gray-500">Sư phạm Tin học</div>
            </div>
            <div className="w-10 h-10 bg-gradient-to-tr from-purple-400 to-pink-400 rounded-full border-2 border-white shadow"></div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 p-8 max-w-6xl mx-auto w-full">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Dự án của bạn</h1>
            <p className="text-gray-500 text-sm mt-1">Quản lý các tiểu luận, khóa luận và luận văn đang thực hiện.</p>
          </div>
          <Link href="/workspace" className="bg-purple-600 text-white px-5 py-2.5 rounded-lg text-sm font-medium hover:bg-purple-700 shadow-sm flex items-center transition">
            <span className="mr-2 text-lg leading-none">+</span> Tạo dự án mới
          </Link>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Project Card 1 */}
          <div className="bg-white border border-gray-200 rounded-xl p-5 hover:shadow-md transition cursor-pointer relative group">
            <div className="absolute top-5 right-5 text-gray-400 group-hover:text-purple-600">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M14 5l7 7m0 0l-7 7m7-7H3"></path>
              </svg>
            </div>
            <span className="bg-blue-100 text-blue-700 text-xs font-semibold px-2 py-1 rounded mb-3 inline-block">Khóa luận</span>
            <h3 className="font-bold text-gray-900 text-lg mb-2 leading-snug pr-8">Nghiên cứu ứng dụng C++ trong thiết kế bài giảng STEM</h3>
            <div className="w-full bg-gray-100 rounded-full h-1.5 mb-4 mt-4">
              <div className="bg-purple-500 h-1.5 rounded-full" style={{ width: '70%' }}></div>
            </div>
            <div className="flex justify-between text-xs text-gray-500">
              <span>Đang cập nhật (Bước 3)</span>
              <span>Sửa lần cuối: 2 giờ trước</span>
            </div>
          </div>

          {/* Project Card 2 */}
          <div className="bg-white border border-gray-200 rounded-xl p-5 hover:shadow-md transition cursor-pointer relative group">
            <div className="absolute top-5 right-5 text-gray-400 group-hover:text-purple-600">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M14 5l7 7m0 0l-7 7m7-7H3"></path>
              </svg>
            </div>
            <span className="bg-green-100 text-green-700 text-xs font-semibold px-2 py-1 rounded mb-3 inline-block">Tiểu luận</span>
            <h3 className="font-bold text-gray-900 text-lg mb-2 leading-snug pr-8">Giải pháp nâng cao hình ảnh thương hiệu số của Duolingo</h3>
            <div className="w-full bg-gray-100 rounded-full h-1.5 mb-4 mt-4">
              <div className="bg-green-500 h-1.5 rounded-full" style={{ width: '100%' }}></div>
            </div>
            <div className="flex justify-between text-xs text-gray-500">
              <span>Đã hoàn thành</span>
              <span>Sửa lần cuối: 2 ngày trước</span>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}