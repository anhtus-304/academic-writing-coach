"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { authApi, projectApi, clearAuthToken, UserProfile, ProjectData } from "@/lib/api";

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<UserProfile | null>(null);
  const [projects, setProjects] = useState<ProjectData[]>([]);
  const [loading, setLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [modalError, setModalError] = useState<string | null>(null);

  // New Project Form state
  const [topic, setTopic] = useState("");
  const [documentType, setDocumentType] = useState<"tieu_luan" | "khoa_luan" | "luan_van">("tieu_luan");
  const [field, setField] = useState("");
  const [university, setUniversity] = useState("");
  const [citationStyle, setCitationStyle] = useState<"apa7" | "ieee" | "bgddt">("apa7");
  const [additionalRequirements, setAdditionalRequirements] = useState("");

  useEffect(() => {
    async function loadDashboardData() {
      try {
        // Fetch authenticated user via HttpOnly cookie (or authorization header)
        const me = await authApi.getMe();
        setUser(me);

        // Fetch user's project list
        const projectList = await projectApi.list().catch(() => []);
        setProjects(projectList);
      } catch (err) {
        console.warn("Chưa xác thực hoặc phiên đăng nhập hết hạn, chuyển hướng tới signin:", err);
        router.push("/auth/signin");
      } finally {
        setLoading(false);
      }
    }

    loadDashboardData();
  }, [router]);

  const handleLogout = async () => {
    try {
      await authApi.logout();
    } catch {
      clearAuthToken();
    }
    router.push("/auth/signin");
  };

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!topic.trim()) {
      setModalError("Vui lòng nhập tên đề tài nghiên cứu");
      return;
    }

    setCreating(true);
    setModalError(null);

    try {
      const newProj = await projectApi.create({
        topic: topic.trim(),
        document_type: documentType,
        field: field.trim() || undefined,
        university: university.trim() || undefined,
        citation_style: citationStyle,
        additional_requirements: additionalRequirements.trim() || undefined,
      });

      setIsModalOpen(false);
      router.push(`/workspace?projectId=${newProj.id}`);
    } catch (err: any) {
      setModalError(err.message || "Không thể tạo dự án. Hãy thử lại.");
      setCreating(false);
    }
  };

  const handleDeleteProject = async (projectId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm("Bạn có chắc chắn muốn xóa dự án này?")) return;
    try {
      await projectApi.delete(projectId);
      setProjects((prev) => prev.filter((p) => p.id !== projectId));
    } catch (err: any) {
      alert("Xóa thất bại: " + err.message);
    }
  };

  const getDocTypeBadge = (type: string) => {
    switch (type) {
      case "khoa_luan":
        return <span className="bg-blue-100 text-blue-700 text-xs font-semibold px-2.5 py-1 rounded-md inline-block">Khóa luận</span>;
      case "luan_van":
        return <span className="bg-amber-100 text-amber-700 text-xs font-semibold px-2.5 py-1 rounded-md inline-block">Luận văn</span>;
      default:
        return <span className="bg-purple-100 text-purple-700 text-xs font-semibold px-2.5 py-1 rounded-md inline-block">Tiểu luận</span>;
    }
  };

  return (
    <div className="bg-gray-50 min-h-screen flex flex-col font-sans text-gray-800">
      {/* Top Navigation */}
      <header className="bg-white h-16 border-b border-gray-200 flex items-center justify-between px-8 sticky top-0 z-30">
        <div className="flex items-center space-x-3">
          <Link href="/" className="flex items-center space-x-3">
            <div className="w-9 h-9 bg-purple-600 rounded-lg flex items-center justify-center text-white shadow-sm">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"></path>
              </svg>
            </div>
            <span className="font-bold text-lg text-gray-900 tracking-tight">AI Academic Coach</span>
          </Link>
        </div>

        <div className="flex items-center space-x-6">
          <Link href="/pricing" className="bg-purple-50 text-purple-700 px-3.5 py-1.5 rounded-full text-sm font-medium flex items-center hover:bg-purple-100 transition border border-purple-200/50">
            <span className="mr-2">🪙</span> {user ? user.credits : 120} Credits
          </Link>
          <div className="flex items-center space-x-3 border-l border-gray-200 pl-6">
            <div className="text-right">
              <div className="text-sm font-semibold text-gray-900">{user?.name || "Người dùng"}</div>
              <div className="text-xs text-gray-500">{user?.email || "student@edu.vn"}</div>
            </div>
            <div className="w-10 h-10 bg-gradient-to-tr from-purple-500 to-pink-500 rounded-full border-2 border-white shadow flex items-center justify-center text-white font-bold">
              {user?.name ? user.name.charAt(0).toUpperCase() : "U"}
            </div>
            <button
              onClick={handleLogout}
              title="Đăng xuất"
              className="text-gray-400 hover:text-gray-600 p-1 rounded-lg hover:bg-gray-100 transition ml-2"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
              </svg>
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 p-8 max-w-6xl mx-auto w-full">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Dự án nghiên cứu của bạn</h1>
            <p className="text-gray-500 text-sm mt-1">Quản lý tiểu luận, khóa luận và luận văn đang thực hiện cùng AI Coach.</p>
          </div>
          <button
            onClick={() => setIsModalOpen(true)}
            className="bg-purple-600 hover:bg-purple-700 text-white px-5 py-2.5 rounded-lg text-sm font-medium shadow-sm flex items-center justify-center transition active:scale-95"
          >
            <span className="mr-2 text-lg leading-none">+</span> Tạo dự án mới
          </button>
        </div>

        {loading ? (
          <div className="flex flex-col items-center justify-center py-20">
            <div className="w-10 h-10 border-4 border-purple-600 border-t-transparent rounded-full animate-spin mb-3"></div>
            <p className="text-sm text-gray-500">Đang tải danh sách dự án...</p>
          </div>
        ) : projects.length === 0 ? (
          <div className="bg-white border-2 border-dashed border-gray-200 rounded-2xl p-12 text-center max-w-lg mx-auto mt-8">
            <div className="w-16 h-16 bg-purple-50 rounded-2xl flex items-center justify-center text-purple-600 mx-auto mb-4 text-2xl">
              📝
            </div>
            <h3 className="text-lg font-bold text-gray-900 mb-2">Chưa có dự án nào</h3>
            <p className="text-sm text-gray-500 mb-6">
              Bắt đầu bài nghiên cứu đầu tiên của bạn. AI Coach sẽ hỗ trợ bạn xây dựng đề cương, dàn ý chi tiết và tra cứu tài liệu học thuật.
            </p>
            <button
              onClick={() => setIsModalOpen(true)}
              className="bg-purple-600 hover:bg-purple-700 text-white px-6 py-2.5 rounded-lg text-sm font-medium shadow-sm transition"
            >
              + Tạo dự án đầu tiên
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {projects.map((proj) => (
              <div
                key={proj.id}
                onClick={() => router.push(`/workspace?projectId=${proj.id}`)}
                className="bg-white border border-gray-200 rounded-xl p-5 hover:shadow-md transition cursor-pointer relative group flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between mb-3">
                    {getDocTypeBadge(proj.document_type)}
                    <button
                      onClick={(e) => handleDeleteProject(proj.id, e)}
                      title="Xóa dự án"
                      className="text-gray-300 hover:text-red-500 p-1 transition opacity-0 group-hover:opacity-100"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  </div>
                  <h3 className="font-bold text-gray-900 text-base mb-2 leading-snug line-clamp-2">
                    {proj.topic}
                  </h3>
                  {proj.field && (
                    <p className="text-xs text-purple-600 font-medium mb-3">
                      Ngành: {proj.field}
                    </p>
                  )}
                </div>

                <div>
                  <div className="w-full bg-gray-100 rounded-full h-1.5 mb-3 mt-4">
                    <div
                      className={`h-1.5 rounded-full ${
                        proj.status === "completed" ? "bg-green-500 w-full" : "bg-purple-500 w-1/3"
                      }`}
                    ></div>
                  </div>
                  <div className="flex justify-between text-xs text-gray-500">
                    <span>{proj.status === "completed" ? "Hoàn thành" : "Bước 1: Dàn ý"}</span>
                    <span>{new Date(proj.created_at).toLocaleDateString("vi-VN")}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>

      {/* Modal Tạo Dự Án Mới */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-fadeIn">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-gray-100">
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-lg font-bold text-gray-900">Tạo dự án nghiên cứu mới</h2>
              <button
                onClick={() => setIsModalOpen(false)}
                className="text-gray-400 hover:text-gray-600 text-xl font-bold p-1"
              >
                ×
              </button>
            </div>

            {modalError && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 text-xs rounded-lg">
                {modalError}
              </div>
            )}

            <form onSubmit={handleCreateProject} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">
                  Tên đề tài nghiên cứu <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  placeholder="VD: Nghiên cứu ứng dụng Blockchain trong Truy xuất nguồn gốc nông sản"
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm outline-none focus:border-purple-500 focus:ring-1 focus:ring-purple-500 text-gray-900"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-gray-700 mb-1">Loại bài viết</label>
                  <select
                    value={documentType}
                    onChange={(e: any) => setDocumentType(e.target.value)}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm outline-none focus:border-purple-500 text-gray-800 bg-white"
                  >
                    <option value="tieu_luan">Tiểu luận (15-25 trang)</option>
                    <option value="khoa_luan">Khóa luận tốt nghiệp (40-60 trang)</option>
                    <option value="luan_van">Luận văn thạc sĩ (70-100 trang)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-gray-700 mb-1">Chuẩn trích dẫn</label>
                  <select
                    value={citationStyle}
                    onChange={(e: any) => setCitationStyle(e.target.value)}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm outline-none focus:border-purple-500 text-gray-800 bg-white"
                  >
                    <option value="apa7">APA 7th Edition</option>
                    <option value="ieee">IEEE Standard</option>
                    <option value="bgddt">Bộ GD & ĐT Việt Nam</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-gray-700 mb-1">Chuyên ngành / Lĩnh vực</label>
                  <input
                    type="text"
                    placeholder="VD: CNTT, Quản trị kinh doanh..."
                    value={field}
                    onChange={(e) => setField(e.target.value)}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm outline-none focus:border-purple-500 text-gray-900"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-gray-700 mb-1">Trường đại học</label>
                  <input
                    type="text"
                    placeholder="VD: ĐH Sư Phạm, ĐH Bách Khoa..."
                    value={university}
                    onChange={(e) => setUniversity(e.target.value)}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm outline-none focus:border-purple-500 text-gray-900"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">Yêu cầu bổ sung của giảng viên (nếu có)</label>
                <textarea
                  rows={2}
                  placeholder="VD: Phải có chương khảo sát thực trạng năm 2024-2025..."
                  value={additionalRequirements}
                  onChange={(e) => setAdditionalRequirements(e.target.value)}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm outline-none focus:border-purple-500 text-gray-900 resize-none"
                />
              </div>

              <div className="flex items-center justify-end space-x-3 pt-4 border-t border-gray-100">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition"
                >
                  Hủy
                </button>
                <button
                  type="submit"
                  disabled={creating}
                  className="bg-purple-600 hover:bg-purple-700 text-white px-5 py-2 text-sm font-medium rounded-lg shadow-sm transition active:scale-95 flex items-center"
                >
                  {creating ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></div>
                      Đang khởi tạo...
                    </>
                  ) : (
                    "Bắt đầu dự án"
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}