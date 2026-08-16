'use client';

import Link from 'next/link';

export default function WorkspacePage() {
  return (
    <div className="bg-white h-screen flex flex-col overflow-hidden text-gray-800 font-sans">
      {/* Top Navigation */}
      <header className="h-14 border-b border-gray-200 flex items-center justify-between px-4 shrink-0">
        <div className="flex items-center space-x-4">
          <Link href="/dashboard" className="w-8 h-8 bg-gray-200 rounded flex items-center justify-center hover:bg-gray-300 transition">
            <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"></path>
            </svg>
          </Link>
          <div className="font-semibold">KLTN</div>
          <div className="text-sm text-gray-400 bg-gray-100 px-2 py-1 rounded">Đã lưu</div>
        </div>
        <div className="flex items-center space-x-4">
          <div className="text-sm text-gray-500">
            <span className="font-medium text-gray-800">0 credit còn lại</span> / 0
          </div>
          <Link href="/pricing" className="bg-purple-600 text-white px-4 py-1.5 rounded-full text-sm font-medium hover:bg-purple-700 transition">
            Nâng cấp
          </Link>
          <button className="text-gray-500 hover:text-gray-800 transition">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path>
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
            </svg>
          </button>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        
        {/* Left Sidebar: Outline Agent */}
        <aside className="w-64 border-r border-gray-200 flex flex-col bg-gray-50/50 shrink-0">
          <div className="p-4 flex items-center justify-between border-b border-gray-100">
            <span className="font-semibold">Mục lục</span>
            <div className="flex space-x-2">
              <button className="text-xs bg-gray-100 px-2 py-1 rounded border hover:bg-gray-200 transition">Copy All</button>
              <button className="text-xs bg-purple-600 text-white px-2 py-1 rounded hover:bg-purple-700 transition">Dàn ý</button>
            </div>
          </div>
          <div className="flex-1 overflow-y-auto p-2 text-sm">
            <div className="py-1 px-2 text-gray-500 font-medium">Introduction</div>
            
            {/* Active Item */}
            <div className="bg-purple-50 border border-purple-200 rounded-lg p-2 mb-2 shadow-sm">
              <div className="flex items-center text-purple-700 font-semibold mb-2">
                <span className="mr-2">📄</span> 1. Tính cấp thiết của đề tài
              </div>
              <div className="bg-white rounded p-2 border border-purple-100">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-purple-600 font-medium text-xs">Luận điểm</span>
                  <button className="bg-purple-600 text-white text-[10px] px-2 py-0.5 rounded flex items-center hover:bg-purple-700 transition">✨ Tạo</button>
                </div>
                <ul className="text-gray-600 space-y-2 text-xs">
                  <li>1. TÍNH CẤP THIẾT CỦA ĐỀ TÀI</li>
                  <li>1.1. Bối cảnh chuyển đổi số...</li>
                </ul>
              </div>
            </div>

            <div className="py-1.5 px-2 text-gray-600 hover:bg-gray-100 rounded cursor-pointer flex items-center"><span className="mr-2">📄</span> 2. Mục tiêu nghiên cứu</div>
            <div className="py-1.5 px-2 text-gray-600 hover:bg-gray-100 rounded cursor-pointer flex items-center"><span className="mr-2">📄</span> 3. Đối tượng và phạm vi</div>
            <div className="py-1.5 px-2 text-gray-600 hover:bg-gray-100 rounded cursor-pointer flex items-center"><span className="mr-2">📄</span> 4. Phương pháp nghiên cứu</div>
          </div>

          {/* Bottom Settings */}
          <div className="p-4 border-t border-gray-200 text-sm">
            <div className="font-semibold flex items-center justify-between mb-3 text-purple-700 cursor-pointer">
              Thiết lập dự án
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7"></path></svg>
            </div>
            <ul className="space-y-2 text-gray-600">
              <li className="flex items-center cursor-pointer hover:text-gray-900"><span className="mr-2">🎯</span> Nền tảng</li>
              <li className="flex items-center cursor-pointer hover:text-gray-900"><span className="mr-2">📝</span> Phong cách</li>
              <li className="flex items-center cursor-pointer hover:text-gray-900"><span className="mr-2">📚</span> Danh sách tài liệu</li>
            </ul>
          </div>
        </aside>

        {/* Center: Tiptap Editor */}
        <main className="flex-1 flex flex-col bg-white overflow-hidden">
          {/* Toolbar */}
          <div className="h-12 border-b border-gray-200 flex items-center px-4 space-x-4 shrink-0 bg-white">
            <select className="text-sm border-gray-300 rounded border px-2 py-1 outline-none text-gray-600">
              <option>Times New Roman</option>
            </select>
            <div className="flex items-center border rounded px-2 py-1 space-x-2">
              <button className="text-gray-500 hover:text-gray-800">-</button>
              <span className="text-sm">13</span>
              <button className="text-gray-500 hover:text-gray-800">+</button>
            </div>
            <div className="flex items-center space-x-3 text-gray-500">
              <button className="font-bold hover:text-gray-800">B</button>
              <button className="italic hover:text-gray-800">I</button>
              <button className="underline hover:text-gray-800">U</button>
              <button className="line-through hover:text-gray-800">S</button>
            </div>
            <div className="flex-1"></div>
            <div className="text-xs text-gray-400">3584 từ</div>
          </div>

          {/* Editor Content */}
          <div className="flex-1 overflow-y-auto p-12 px-24">
            <h1 className="text-2xl font-bold text-center mb-8 uppercase">Giải pháp nâng cao hình ảnh thương hiệu số của Duolingo tại thị trường học ngôn ngữ toàn cầu</h1>

            <h2 className="text-lg font-bold mb-4">1. Tính cấp thiết của đề tài</h2>
            <p className="mb-4 leading-relaxed text-gray-700 text-[15px] text-justify">
              Trong thập niên vừa qua, thế giới đã chứng kiến sự chuyển dịch vũ bão của giáo dục từ mô hình truyền thống sang các nền tảng ưu tiên công nghệ số (Digital-first), đặc biệt rõ nét trong lĩnh vực đào tạo ngôn ngữ. Không còn bị giới hạn bởi không gian lớp học vật lý, sự phổ cập của điện thoại thông minh và mạng internet đã thúc đẩy quá trình &quot;dân chủ hóa giáo dục&quot;, cho phép hàng tỷ người dùng tiếp cận tri thức mọi lúc, mọi nơi. Những số liệu thực chứng mới nhất cho thấy quy mô thị trường học ngôn ngữ số toàn cầu đã đạt hơn 26 tỷ USD vào năm 2024 và được dự báo sẽ vượt mốc 108 đến 116 tỷ USD vào giai đoạn 2033 - 2034, với tốc độ tăng trưởng kép hàng năm (CAGR) luôn duy trì ở mức trên 17% <span className="text-blue-600">(Astute Analytica, 2025)</span>.
            </p>
            <p className="mb-4 leading-relaxed text-gray-700 text-[15px] text-justify">
              Trong sự mở rộng thị trường này, phân khúc cá nhân hóa thông qua ứng dụng di động chiếm tới 65,1% thị phần, phản ánh nhu cầu cá nhân hóa việc học ngôn ngữ đang tăng cao <span className="text-blue-600">(Market.us, 2025)</span>. Sự bùng nổ này không chỉ tạo ra vô số cơ hội bứt phá về doanh thu mà còn biến EdTech trở thành một chiến trường cạnh tranh khốc liệt. Ở đó, công nghệ tiên tiến hay thuật toán lõi đã dần trở thành yếu tố bắt buộc (hygiene factor) thay vì lợi thế cạnh tranh độc tôn. Thay vào đó, sức mạnh thương hiệu trong không gian số (Digital Brand Equity) đang nổi lên như một vũ khí sắc bén nhất để các doanh nghiệp thiết lập định vị, thu hút sự chú ý của người dùng và xây dựng rào cản chuyển đổi.
            </p>
          </div>
        </main>

        {/* Right Sidebar: Literature Agent */}
        <aside className="w-[340px] border-l border-gray-200 flex flex-col bg-gray-50/50 shrink-0">
          {/* Tabs */}
          <div className="flex p-2 gap-1 bg-white border-b">
            <button className="flex-1 py-1.5 text-sm rounded text-gray-500 font-medium hover:bg-gray-100 transition">Nhận xét</button>
            <button className="flex-1 py-1.5 text-sm rounded bg-purple-600 text-white font-medium shadow-sm flex items-center justify-center">
              <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
              Nghiên cứu
            </button>
          </div>

          {/* Search */}
          <div className="p-4 border-b border-gray-200">
            <div className="text-sm font-semibold mb-2">Tra cứu nguồn tham khảo</div>
            <div className="relative">
              <svg className="w-4 h-4 text-gray-400 absolute left-3 top-2.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
              <input type="text" defaultValue="Hình ảnh thương hiệu số" className="w-full text-sm border border-gray-300 rounded-full pl-9 pr-10 py-2 outline-none focus:border-purple-500 text-gray-800" />
              <button className="absolute right-2 top-1.5 bg-gray-100 p-1 rounded-full text-gray-500 hover:bg-gray-200 transition">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7"></path></svg>
              </button>
            </div>
          </div>

          {/* Results */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-semibold">Kết quả nghiên cứu</span>
              <span className="text-xs bg-gray-200 text-gray-600 px-2 py-0.5 rounded">5 nguồn</span>
            </div>

            {/* Card 1 */}
            <div className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm hover:border-purple-300 transition">
              <div className="flex justify-between items-start mb-2">
                <h3 className="font-semibold text-sm leading-snug pr-2">The Role of Gamification and Social Media Marketing on Brand Loyalty...</h3>
                <span className="bg-black text-white text-[10px] font-bold px-1.5 py-0.5 rounded shrink-0">High</span>
              </div>
              <div className="text-xs text-gray-500 mb-2">
                Unknown, (2024)<br />
                <span className="text-blue-500">Transpublika</span>
              </div>
              <p className="text-xs text-gray-600 line-clamp-3 mb-3">
                Nghiên cứu sử dụng phân tích mô hình phương trình cấu trúc (PLS-SEM) và phân tích cảm xúc (sentiment...
              </p>
              <div className="flex space-x-2">
                <button className="flex-1 border border-gray-300 rounded py-1 text-xs font-medium hover:bg-gray-50 flex items-center justify-center transition">
                  <span className="mr-1">+</span> Chèn
                </button>
                <button className="flex-1 border border-gray-300 rounded py-1 text-xs font-medium hover:bg-gray-50 flex items-center justify-center transition">
                  <svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path></svg>
                  Xem trước
                </button>
              </div>
            </div>

            {/* Card 2 */}
            <div className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm hover:border-purple-300 transition">
              <div className="flex justify-between items-start mb-2">
                <h3 className="font-semibold text-sm leading-snug pr-2">Whoo&apos;s laughing now? A qualitative study of User Responses...</h3>
                <span className="bg-black text-white text-[10px] font-bold px-1.5 py-0.5 rounded shrink-0">High</span>
              </div>
              <div className="text-xs text-gray-500 mb-2">
                Ebba Keller, Lovisa Käll, (2023)<br />
                <span className="text-blue-500">Lund University Publications</span>
              </div>
              <p className="text-xs text-gray-600 line-clamp-3 mb-3">
                Nghiên cứu định tính thông qua phân tích nội dung đánh giá của người dùng...
              </p>
            </div>
          </div>
        </aside>

      </div>
    </div>
  );
}