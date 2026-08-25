"use client";

import { useEffect, useState, Suspense } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { projectApi, outlineApi, authApi, ProjectData, OutlineData, UserProfile } from "@/lib/api";
import { OutlineEditor, OutlineNode } from "@/components/outline/OutlineEditor";

function transformBackendOutlineToNodes(chapters: any): OutlineNode[] {
  if (!chapters) return [];
  if (Array.isArray(chapters)) return chapters;

  if (chapters.sections && Array.isArray(chapters.sections)) {
    return chapters.sections.map((sec: any, secIdx: number) => ({
      id: `sec-${secIdx + 1}`,
      title: sec.title || `Chương ${secIdx + 1}`,
      level: 1,
      children: (sec.subsections || []).map((sub: any, subIdx: number) => ({
        id: `sub-${secIdx + 1}-${subIdx + 1}`,
        title: sub.title || `Mục ${secIdx + 1}.${subIdx + 1}`,
        level: 2,
        children: (sub.key_points || []).map((kp: string, kpIdx: number) => ({
          id: `kp-${secIdx + 1}-${subIdx + 1}-${kpIdx + 1}`,
          title: `• ${kp}`,
          level: 3,
          children: [],
        })),
      })),
    }));
  }

  return [];
}

function WorkspaceContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const projectId = searchParams.get("projectId");

  const [user, setUser] = useState<UserProfile | null>(null);
  const [project, setProject] = useState<ProjectData | null>(null);
  const [outline, setOutline] = useState<OutlineData | null>(null);
  const [outlineNodes, setOutlineNodes] = useState<OutlineNode[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState<string>("Đã lưu");
  const [activeTab, setActiveTab] = useState<"outline" | "suggestions">("outline");

  // Load project and outline data
  useEffect(() => {
    async function loadData() {
      try {
        const me = await authApi.getMe().catch(() => null);
        if (me) setUser(me);

        let targetProjectId = projectId;

        if (!targetProjectId) {
          const list = await projectApi.list().catch(() => []);
          if (list.length > 0) {
            targetProjectId = list[0].id;
          } else {
            // Create demo project if none exists
            const created = await projectApi.create({
              topic: "Nghiên cứu ứng dụng Blockchain trong Nông nghiệp thông minh",
              document_type: "tieu_luan",
              field: "Công nghệ Thông tin",
              citation_style: "apa7",
            });
            targetProjectId = created.id;
          }
        }

        if (targetProjectId) {
          const [projData, outlineRes] = await Promise.all([
            projectApi.get(targetProjectId).catch(() => null),
            outlineApi.get(targetProjectId).catch(() => ({ success: false, outline: null })),
          ]);

          if (projData) setProject(projData);

          if (outlineRes.success && outlineRes.outline) {
            setOutline(outlineRes.outline);
            const nodes = transformBackendOutlineToNodes(outlineRes.outline.chapters);
            setOutlineNodes(nodes);
          }
        }
      } catch (err) {
        console.error("Failed to load workspace:", err);
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, [projectId]);

  // Generate AI Outline
  const handleGenerateOutline = async () => {
    if (!project) return;
    setGenerating(true);
    try {
      const res = await outlineApi.generate(project.id);
      if (res.success && res.outline) {
        setOutline(res.outline);
        const nodes = transformBackendOutlineToNodes(res.outline.chapters);
        setOutlineNodes(nodes);
        setSaveStatus("Đã lưu dàn ý mới");
      }
    } catch (err: any) {
      alert("Không thể sinh dàn ý AI: " + err.message);
    } finally {
      setGenerating(false);
    }
  };

  // Save modified outline
  const handleSaveOutline = async () => {
    if (!project) return;
    setSaving(true);
    try {
      const res = await outlineApi.update(project.id, outlineNodes, outline?.suggestions);
      if (res.success && res.outline) {
        setOutline(res.outline);
        setSaveStatus("Đã lưu");
      }
    } catch (err: any) {
      alert("Lưu thất bại: " + err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleOutlineChange = (nextNodes: OutlineNode[]) => {
    setOutlineNodes(nextNodes);
    setSaveStatus("Chưa lưu...");
  };

  if (loading) {
    return (
      <div className="h-screen flex flex-col items-center justify-center bg-gray-50 text-gray-700">
        <div className="w-10 h-10 border-4 border-purple-600 border-t-transparent rounded-full animate-spin mb-3"></div>
        <p className="text-sm font-medium">Đang tải không gian làm việc...</p>
      </div>
    );
  }

  return (
    <div className="bg-white h-screen flex flex-col overflow-hidden text-gray-800 font-sans">
      {/* Top Navigation */}
      <header className="h-14 border-b border-gray-200 flex items-center justify-between px-4 shrink-0 bg-white z-20">
        <div className="flex items-center space-x-4">
          <Link
            href="/dashboard"
            className="w-8 h-8 bg-gray-100 rounded-lg flex items-center justify-center hover:bg-gray-200 transition text-gray-600"
            title="Về Dashboard"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 19l-7-7m0 0l7-7m-7 7h18"></path>
            </svg>
          </Link>
          <div className="font-semibold text-gray-900 text-sm max-w-md truncate">
            {project?.topic || "Dự án nghiên cứu"}
          </div>
          <div className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
            {saveStatus}
          </div>
        </div>

        <div className="flex items-center space-x-4">
          <button
            onClick={handleSaveOutline}
            disabled={saving}
            className="bg-gray-100 hover:bg-gray-200 text-gray-700 text-xs px-3 py-1.5 rounded-md font-medium transition flex items-center"
          >
            {saving ? "Đang lưu..." : "💾 Lưu dàn ý"}
          </button>
          <div className="text-sm text-gray-500">
            <span className="font-medium text-gray-800">🪙 {user ? user.credits : 120} credits</span>
          </div>
          <Link
            href="/pricing"
            className="bg-purple-600 text-white px-3.5 py-1.5 rounded-full text-xs font-medium hover:bg-purple-700 transition"
          >
            Nâng cấp
          </Link>
        </div>
      </header>

      {/* Main Workspace Layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Sidebar: Outline Agent & Editor */}
        <aside className="w-80 border-r border-gray-200 flex flex-col bg-gray-50/70 shrink-0">
          <div className="p-3 flex items-center justify-between border-b border-gray-200 bg-white">
            <div className="flex space-x-1">
              <button
                onClick={() => setActiveTab("outline")}
                className={`text-xs px-2.5 py-1 rounded-md font-medium transition ${
                  activeTab === "outline" ? "bg-purple-100 text-purple-700" : "text-gray-600 hover:bg-gray-100"
                }`}
              >
                Mục lục Dàn ý
              </button>
              <button
                onClick={() => setActiveTab("suggestions")}
                className={`text-xs px-2.5 py-1 rounded-md font-medium transition ${
                  activeTab === "suggestions" ? "bg-purple-100 text-purple-700" : "text-gray-600 hover:bg-gray-100"
                }`}
              >
                Gợi ý AI
              </button>
            </div>
            <button
              onClick={handleGenerateOutline}
              disabled={generating}
              className="text-xs bg-purple-600 text-white px-2.5 py-1 rounded-md hover:bg-purple-700 transition shadow-sm font-medium flex items-center active:scale-95"
            >
              {generating ? (
                <>
                  <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin mr-1"></div>
                  Đang sinh...
                </>
              ) : (
                "✨ Sinh dàn ý AI"
              )}
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-3">
            {generating ? (
              <div className="py-16 text-center space-y-3">
                <div className="w-8 h-8 border-3 border-purple-600 border-t-transparent rounded-full animate-spin mx-auto"></div>
                <p className="text-xs font-semibold text-purple-700">AI Outline Agent đang xử lý...</p>
                <p className="text-[11px] text-gray-500 px-4">
                  Phân tích đề tài &quot;{project?.topic}&quot; và cấu trúc các chương theo chuẩn học thuật.
                </p>
              </div>
            ) : activeTab === "outline" ? (
              outlineNodes.length === 0 ? (
                <div className="text-center py-12 px-4 border border-dashed border-gray-300 rounded-xl bg-white/50">
                  <div className="text-2xl mb-2">📑</div>
                  <h4 className="text-xs font-bold text-gray-800 mb-1">Chưa có Dàn ý</h4>
                  <p className="text-[11px] text-gray-500 mb-4">
                    Nhấn nút bên dưới để AI tự động sinh cấu trúc dàn ý chuẩn cho đề tài này.
                  </p>
                  <button
                    onClick={handleGenerateOutline}
                    className="w-full bg-purple-600 hover:bg-purple-700 text-white text-xs font-medium py-2 rounded-lg transition shadow-sm"
                  >
                    ✨ Tạo Dàn Ý bằng AI
                  </button>
                </div>
              ) : (
                <div className="space-y-2">
                  <div className="text-[11px] text-gray-500 font-semibold uppercase px-1 tracking-wider mb-2 flex items-center justify-between">
                    <span>Cấu trúc đề tài</span>
                    <span className="text-purple-600 font-normal lowercase">{outlineNodes.length} chương</span>
                  </div>
                  <OutlineEditor
                    outline={outlineNodes}
                    onChange={handleOutlineChange}
                    title="Chỉnh sửa dàn ý"
                  />
                </div>
              )
            ) : (
              <div className="space-y-4">
                {outline?.suggestions ? (
                  <>
                    <div className="bg-white p-3 rounded-lg border border-gray-200 shadow-sm">
                      <div className="text-xs font-bold text-gray-800 mb-1 flex items-center">
                        <span className="mr-1.5">🔬</span> Gợi ý Phương pháp nghiên cứu
                      </div>
                      <p className="text-xs text-gray-600 leading-relaxed">
                        {outline.suggestions.research_methodology_suggestion || "Chưa có gợi ý."}
                      </p>
                    </div>

                    <div className="bg-white p-3 rounded-lg border border-gray-200 shadow-sm">
                      <div className="text-xs font-bold text-gray-800 mb-2 flex items-center">
                        <span className="mr-1.5">🏷️</span> Từ khóa học thuật
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        {(outline.suggestions.key_academic_keywords || []).map((kw: string, i: number) => (
                          <span
                            key={i}
                            className="bg-purple-50 text-purple-700 border border-purple-100 text-[11px] px-2 py-0.5 rounded-full"
                          >
                            {kw}
                          </span>
                        ))}
                      </div>
                    </div>

                    <div className="bg-white p-3 rounded-lg border border-gray-200 shadow-sm">
                      <div className="text-xs font-bold text-gray-800 mb-1 flex items-center">
                        <span className="mr-1.5">💡</span> Hướng dẫn viết bài
                      </div>
                      <p className="text-xs text-gray-600 leading-relaxed">
                        {outline.suggestions.writing_guidelines || "Chưa có hướng dẫn."}
                      </p>
                    </div>
                  </>
                ) : (
                  <div className="text-center py-8 text-xs text-gray-500">
                    Hãy sinh dàn ý AI để nhận các gợi ý phương pháp & từ khóa học thuật.
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Project Details Footer */}
          <div className="p-3 border-t border-gray-200 bg-white text-xs text-gray-600">
            <div className="flex justify-between items-center mb-1">
              <span className="text-gray-400">Loại văn bản:</span>
              <span className="font-semibold text-gray-800 capitalize">
                {project?.document_type?.replace("_", " ")}
              </span>
            </div>
            <div className="flex justify-between items-center mb-1">
              <span className="text-gray-400">Chuẩn trích dẫn:</span>
              <span className="font-semibold text-purple-700 uppercase">
                {project?.citation_style}
              </span>
            </div>
            {project?.field && (
              <div className="flex justify-between items-center">
                <span className="text-gray-400">Chuyên ngành:</span>
                <span className="font-medium text-gray-800 truncate max-w-[150px]">
                  {project.field}
                </span>
              </div>
            )}
          </div>
        </aside>

        {/* Center: Interactive Editor Area */}
        <main className="flex-1 flex flex-col bg-white overflow-hidden">
          {/* Editor Toolbar */}
          <div className="h-12 border-b border-gray-200 flex items-center px-4 space-x-4 shrink-0 bg-white">
            <select className="text-sm border-gray-300 rounded border px-2 py-1 outline-none text-gray-600">
              <option>Times New Roman</option>
              <option>Arial</option>
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
            </div>
            <div className="flex-1"></div>
            <div className="text-xs text-gray-400">
              Dự kiến: {outline?.suggestions?.total_estimated_pages || "20 trang"}
            </div>
          </div>

          {/* Editor Document Canvas */}
          <div className="flex-1 overflow-y-auto p-12 px-20 max-w-4xl mx-auto w-full">
            <h1 className="text-2xl font-bold text-center mb-8 uppercase text-gray-900 leading-snug">
              {project?.topic}
            </h1>

            {outlineNodes.length > 0 ? (
              <div className="space-y-6">
                {outlineNodes.map((section, idx) => (
                  <div key={section.id} className="border-b border-gray-100 pb-4">
                    <h2 className="text-lg font-bold text-gray-800 mb-2">
                      {section.title}
                    </h2>
                    {section.children && section.children.length > 0 && (
                      <div className="pl-4 space-y-2 mt-2">
                        {section.children.map((sub) => (
                          <div key={sub.id} className="text-sm font-semibold text-gray-700">
                            {sub.title}
                            {sub.children && sub.children.length > 0 && (
                              <ul className="list-disc pl-5 mt-1 text-xs text-gray-600 font-normal space-y-1">
                                {sub.children.map((point) => (
                                  <li key={point.id}>{point.title.replace(/^•\s*/, "")}</li>
                                ))}
                              </ul>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-20 text-gray-400">
                <p className="text-sm">Hãy sinh dàn ý ở thanh công cụ bên trái để bắt đầu soạn thảo nội dung.</p>
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}

export default function WorkspacePage() {
  return (
    <Suspense
      fallback={
        <div className="h-screen flex items-center justify-center bg-gray-50">
          <div className="w-10 h-10 border-4 border-purple-600 border-t-transparent rounded-full animate-spin"></div>
        </div>
      }
    >
      <WorkspaceContent />
    </Suspense>
  );
}