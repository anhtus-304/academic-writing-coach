"use client";

import { useEffect, useState, Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import {
  projectApi,
  outlineApi,
  authApi,
  literatureApi,
  citationApi,
  ProjectData,
  OutlineData,
  UserProfile,
  CitationCheckResponse,
  CitationSuggestion,
} from "@/lib/api";
import { OutlineEditor, OutlineNode } from "@/components/outline/OutlineEditor";
import { TiptapEditor } from "@/components/editor/TiptapEditor";
import { AIResponsePanel } from "@/components/editor/AIResponsePanel";
import { LiteratureList } from "@/components/literature/LiteratureList";
import { SearchFilters } from "@/components/literature/SearchFilters";
import { CreditBalance } from "@/components/CreditBalance";
import { formatAuthors, type LiteraturePaper, type LiteratureFilters, type SelectedPaperItem } from "@/components/literature/types";
import { BibliographyView } from "@/components/citation/BibliographyView";
import { AgentStepper } from "@/components/agents/AgentStepper";

import { Trash2, BookOpen, Search, ShieldAlert, Sparkles, FileCheck, ExternalLink } from "lucide-react";

interface RawSubSection {
  title?: string;
  key_points?: string[];
}
interface RawSection {
  title?: string;
  subsections?: RawSubSection[];
}
interface RawOutlineChapters {
  sections?: RawSection[];
}

function transformBackendOutlineToNodes(chapters: unknown): OutlineNode[] {
  if (!chapters) return [];
  if (Array.isArray(chapters)) return chapters as OutlineNode[];

  const obj = chapters as RawOutlineChapters;
  if (obj.sections && Array.isArray(obj.sections)) {
    return obj.sections.map((sec: RawSection, secIdx: number) => ({
      id: `sec-${secIdx + 1}`,
      title: sec.title || `Chương ${secIdx + 1}`,
      level: 1,
      children: (sec.subsections || []).map((sub: RawSubSection, subIdx: number) => ({
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

function escapeHtml(value: string) {
  return value.replace(/[&<>"']/g, (character) => {
    const entities: Record<string, string> = {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    };
    return entities[character];
  });
}

function outlineNodesToHtml(nodes: OutlineNode[]): string {
  return nodes
    .map((node) => {
      const title = escapeHtml(node.title.replace(/^•\s*/, ""));
      const heading = node.level === 1 ? "h2" : node.level === 2 ? "h3" : "p";
      const children = node.children?.length ? outlineNodesToHtml(node.children) : "";
      return `<${heading}>${title}</${heading}>${children}`;
    })
    .join("");
}

function WorkspaceContent() {
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
  const [rightPanelTab, setRightPanelTab] = useState<"literature" | "assistant">("literature");
  const [literatureSubTab, setLiteratureSubTab] = useState<"search" | "saved">("search");
  const [editorContent, setEditorContent] = useState("");
  const [selectedText, setSelectedText] = useState("");
  const [isAIResponsePanelOpen, setIsAIResponsePanelOpen] = useState(false);
  const [creditTrigger, setCreditTrigger] = useState(0);

  // Literature Search State
  const [literatureQuery, setLiteratureQuery] = useState("");
  const [submittedLiteratureQuery, setSubmittedLiteratureQuery] = useState("");
  const [expandedQueries, setExpandedQueries] = useState<string[]>([]);
  const [literatureFilters, setLiteratureFilters] = useState<LiteratureFilters>({
    year: "",
    publicationType: "",
    source: "",
  });
  const [selectedPaper, setSelectedPaper] = useState<LiteraturePaper | null>(null);
  const [literaturePapers, setLiteraturePapers] = useState<LiteraturePaper[]>([]);
  const [literatureLoading, setLiteratureLoading] = useState(false);
  const [literatureError, setLiteratureError] = useState<string | null>(null);
  const [summaryLoadingPaperId, setSummaryLoadingPaperId] = useState<string | null>(null);
  const [summaryError, setSummaryError] = useState<string | null>(null);
  const [insertReferenceHtml, setInsertReferenceHtml] = useState<string | null>(null);
  const [searchModeBadge, setSearchModeBadge] = useState<{ text: string; isCache: boolean } | null>(null);

  // Selected Papers Persistent State
  const [selectedPapers, setSelectedPapers] = useState<SelectedPaperItem[]>([]);
  const [selectingPaperId, setSelectingPaperId] = useState<string | null>(null);

  // Citation Agent State (Tuần 3)
  const [checkingCitations, setCheckingCitations] = useState(false);
  const [citationResult, setCitationResult] = useState<CitationCheckResponse | null>(null);
  const [isCitationModalOpen, setIsCitationModalOpen] = useState(false);
  const [citationSuggestion, setCitationSuggestion] = useState<{ originalText: string; suggestedText: string } | null>(null);

  // Load project, outline, selected papers and recent search data
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
          const [projData, outlineRes, selectedRes, recentRes] = await Promise.all([
            projectApi.get(targetProjectId).catch(() => null),
            outlineApi.get(targetProjectId).catch(() => ({ success: false, outline: null })),
            literatureApi.getSelectedPapers(targetProjectId).catch(() => ({ total: 0, selected_papers: [] })),
            literatureApi.getRecentSearch(targetProjectId).catch(() => null),
          ]);

          if (projData) setProject(projData);

          if (outlineRes.success && outlineRes.outline) {
            setOutline(outlineRes.outline);
            const nodes = transformBackendOutlineToNodes(outlineRes.outline.chapters);
            setOutlineNodes(nodes);
            setEditorContent(outlineNodesToHtml(nodes));
          }

          // Khôi phục danh sách tài liệu đã chọn từ Database
          if (selectedRes && selectedRes.selected_papers) {
            setSelectedPapers(selectedRes.selected_papers);
          }

          // Khôi phục phiên tìm kiếm gần nhất còn hạn 48h
          if (recentRes && recentRes.has_recent && recentRes.papers?.length > 0) {
            setLiteraturePapers(recentRes.papers);
            setLiteratureQuery(recentRes.query || "");
            setSubmittedLiteratureQuery(recentRes.query || "");
            setSearchModeBadge({
              text: "⚡ Khôi phục từ bộ nhớ đệm 48h (0 Credit)",
              isCache: true,
            });
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

  // Handle Project-scoped Literature Search with 48h cache & Credit deduction
  const handleSearchLiterature = async () => {
    const nextQuery = literatureQuery.trim();
    if (!nextQuery) {
      setLiteraturePapers([]);
      setExpandedQueries([]);
      setLiteratureError(null);
      setSubmittedLiteratureQuery("");
      setSearchModeBadge(null);
      return;
    }

    if (!project) return;

    setLiteratureLoading(true);
    setLiteratureError(null);
    setSubmittedLiteratureQuery(nextQuery);

    try {
      const response = await literatureApi.searchInProject(project.id, nextQuery, {
        year: literatureFilters.year,
        publicationType: literatureFilters.publicationType,
        source: literatureFilters.source,
      });

      setLiteraturePapers(response.papers || []);
      setExpandedQueries(response.expanded_queries || []);

      if (response.cached) {
        setSearchModeBadge({
          text: "⚡ Trong bộ nhớ đệm (0 Credit)",
          isCache: true,
        });
      } else {
        setSearchModeBadge({
          text: "🔍 Tìm kiếm mới (-1 Credit)",
          isCache: false,
        });
        setCreditTrigger((c) => c + 1); // Cập nhật số dư Header real-time!
      }
    } catch (error: Error | unknown) {
      setLiteraturePapers([]);
      setExpandedQueries([]);
      const message = error instanceof Error ? error.message : "Không thể tải danh sách tài liệu từ các nguồn học thuật.";
      setLiteratureError(message);
    } finally {
      setLiteratureLoading(false);
    }
  };

  // Chọn tài liệu lưu vĩnh viễn vào Database
  const handleSelectPaper = async (paper: LiteraturePaper) => {
    if (!project) return;
    setSelectingPaperId(paper.id);
    try {
      const res = await literatureApi.selectPaper(project.id, {
        paper,
        cached_paper_id: paper.id.length > 20 ? paper.id : undefined,
      });

      setSelectedPapers((current) => {
        const exists = current.some((p) => p.id === res.id || p.cached_paper_id === res.cached_paper_id);
        if (exists) return current;
        return [res, ...current];
      });
      setSelectedPaper(paper);
    } catch (error: unknown) {
      alert("Không thể lưu tài liệu: " + (error instanceof Error ? error.message : "Đã có lỗi xảy ra"));
    } finally {
      setSelectingPaperId(null);
    }
  };

  // Bỏ chọn / Xóa tài liệu khỏi đề tài
  const handleRemoveSelectedPaper = async (selectedId: string) => {
    if (!project) return;
    try {
      await literatureApi.removeSelectedPaper(project.id, selectedId);
      setSelectedPapers((current) => current.filter((p) => p.id !== selectedId));
      if (selectedPaper?.id === selectedId) {
        setSelectedPaper(null);
      }
    } catch (error: unknown) {
      alert("Xóa tài liệu thất bại: " + (error instanceof Error ? error.message : ""));
    }
  };

  // Tóm tắt tài liệu bằng AI
  const handleSummarizePaper = async (paper: LiteraturePaper) => {
    setSummaryLoadingPaperId(paper.id);
    setSummaryError(null);

    try {
      const response = await literatureApi.summarize(paper);
      const updatedPaper = { ...paper, summaryVi: response.summary_vi };
      setSelectedPaper(updatedPaper);
      setLiteraturePapers((current) => current.map((item) => (item.id === paper.id ? updatedPaper : item)));
    } catch (error: unknown) {
      setSummaryError(
        error instanceof Error
          ? error.message
          : "Không thể tóm tắt tài liệu bằng AI. Vui lòng thử lại sau."
      );
    } finally {
      setSummaryLoadingPaperId(null);
    }
  };

  // Chèn trích dẫn vào Tiptap Editor
  const handleInsertPaperReference = (paper: LiteraturePaper, customCitation?: string) => {
    let reference = "";
    if (customCitation) {
      reference = `<p class="citation-entry">${escapeHtml(customCitation)}</p>`;
    } else {
      const authors = formatAuthors(paper.authors);
      const year = paper.year || "n.d.";
      reference = `<p><strong>${escapeHtml(paper.title)}</strong> (${escapeHtml(authors)}, ${year}). ${paper.url ? `<a href="${paper.url}" target="_blank" rel="noreferrer">${paper.url}</a>` : ""}</p>`;
    }
    setInsertReferenceHtml(reference);
  };

  // Chèn toàn bộ danh mục tài liệu tham khảo đã chọn vào cuối bài
  const handleInsertFullBibliography = () => {
    if (selectedPapers.length === 0) return;
    const entries = selectedPapers
      .map((sp, idx) => {
        const text = sp.citation_formatted || `${sp.paper?.title} (${sp.paper?.year || "n.d."})`;
        return `<p>${project?.citation_style === "ieee" ? `[${idx + 1}] ` : ""}${escapeHtml(text)}</p>`;
      })
      .join("");
    const bibHtml = `<h2>TÀI LIỆU THAM KHẢO</h2>${entries}`;
    setInsertReferenceHtml(bibHtml);
  };

  // Kiểm tra trích dẫn toàn bài (Citation Agent - Tuần 3)
  const handleCheckCitations = async () => {
    if (!project) return;
    if (!editorContent || editorContent.trim().length < 20) {
      alert("Nội dung bài viết còn quá ngắn để quét trích dẫn. Vui lòng soạn thảo thêm.");
      return;
    }

    setCheckingCitations(true);
    try {
      const res = await citationApi.checkCitations(project.id, editorContent, project.citation_style);
      setCitationResult(res);
      setIsCitationModalOpen(true);
      setCreditTrigger((c) => c + 1); // Trừ 2 Credits và cập nhật số dư tức thì!
    } catch (err: unknown) {
      alert("Kiểm tra trích dẫn thất bại: " + (err instanceof Error ? err.message : "Vui lòng kiểm tra lại số dư"));
    } finally {
      setCheckingCitations(false);
    }
  };

  const handleAcceptCitationSuggestion = (suggestion: CitationSuggestion) => {
    if (!suggestion.suggested_text) return;
    setCitationSuggestion({
      originalText: suggestion.original_text,
      suggestedText: suggestion.suggested_text,
    });
  };

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
        setEditorContent(outlineNodesToHtml(nodes));
        setSaveStatus("Đã lưu dàn ý mới");
        setCreditTrigger((c) => c + 1);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Đã có lỗi xảy ra";
      alert("Không thể sinh dàn ý AI: " + msg);
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
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Đã có lỗi xảy ra";
      alert("Lưu thất bại: " + msg);
    } finally {
      setSaving(false);
    }
  };

  const handleOutlineChange = (nextNodes: OutlineNode[]) => {
    setOutlineNodes(nextNodes);
    setEditorContent(outlineNodesToHtml(nextNodes));
    setSaveStatus("Chưa lưu...");
  };

  const selectedPaperIds = selectedPapers.map((sp) => sp.cached_paper_id || sp.id);

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

        <div className="flex items-center space-x-3">
          {/* Nút Kiểm tra trích dẫn toàn bài (2 Credits) */}
          <button
            onClick={handleCheckCitations}
            disabled={checkingCitations}
            className="bg-purple-50 hover:bg-purple-100 text-purple-700 border border-purple-200 text-xs px-3 py-1.5 rounded-md font-medium transition flex items-center shadow-2xs"
            title="Quét câu khẳng định thiếu nguồn & đối soát tài liệu (Chi phí: 2 Credits)"
          >
            {checkingCitations ? (
              <>
                <div className="w-3.5 h-3.5 border-2 border-purple-600 border-t-transparent rounded-full animate-spin mr-1.5" />
                Đang quét...
              </>
            ) : (
              <>
                <FileCheck className="w-3.5 h-3.5 mr-1.5 text-purple-600" />
                Kiểm tra trích dẫn (2 Credits)
              </>
            )}
          </button>

          <button
            onClick={handleSaveOutline}
            disabled={saving}
            className="bg-gray-100 hover:bg-gray-200 text-gray-700 text-xs px-3 py-1.5 rounded-md font-medium transition flex items-center"
          >
            {saving ? "Đang lưu..." : "💾 Lưu dàn ý"}
          </button>
          <CreditBalance initialBalance={user?.credits} refreshTrigger={creditTrigger} />
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
                    Nhấn nút bên dưới để AI tự động sinh cấu trúc dàn ý chuẩn cho đề tài này (Chi phí: 2 Credits).
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
                        {String(outline.suggestions.research_methodology_suggestion || "Chưa có gợi ý.")}
                      </p>
                    </div>

                    <div className="bg-white p-3 rounded-lg border border-gray-200 shadow-sm">
                      <div className="text-xs font-bold text-gray-800 mb-2 flex items-center">
                        <span className="mr-1.5">🏷️</span> Từ khóa học thuật
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        {(Array.isArray(outline.suggestions.key_academic_keywords)
                          ? (outline.suggestions.key_academic_keywords as string[])
                          : []
                        ).map((kw: string, i: number) => (
                          <span
                            key={i}
                            className="bg-purple-50 text-purple-700 border border-purple-100 text-[11px] px-2 py-0.5 rounded-full"
                          >
                            {String(kw)}
                          </span>
                        ))}
                      </div>
                    </div>

                    <div className="bg-white p-3 rounded-lg border border-gray-200 shadow-sm">
                      <div className="text-xs font-bold text-gray-800 mb-1 flex items-center">
                        <span className="mr-1.5">💡</span> Hướng dẫn viết bài
                      </div>
                      <p className="text-xs text-gray-600 leading-relaxed">
                        {String(outline.suggestions.writing_guidelines || "Chưa có hướng dẫn.")}
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
        <main className="flex min-w-0 flex-1 flex-col overflow-hidden bg-white">
          <div className="flex-1 overflow-y-auto p-4 sm:p-8 lg:p-12">
            <div className="mx-auto w-full max-w-4xl">
              <AgentStepper
                steps={[
                  { label: "Outline Agent", status: outline ? "success" : "pending" },
                  { label: "Literature Agent", status: selectedPapers.length > 0 ? "success" : "pending" },
                  { label: "Citation Agent", status: checkingCitations ? "running" : citationResult ? "success" : "pending" },
                  { label: "Citation Formatter", status: citationResult?.bibliography?.length ? "success" : "pending" },
                  { label: "Hoàn tất", status: citationResult ? "success" : "pending" },
                ]}
              />
              <h1 className="mb-8 text-center text-2xl font-bold uppercase leading-snug text-gray-900">
                {project?.topic}
              </h1>
              <TiptapEditor
                value={editorContent}
                onChange={setEditorContent}
                placeholder="Bắt đầu viết nội dung nghiên cứu..."
                insertReferenceHtml={insertReferenceHtml}
                onReferenceInserted={() => setInsertReferenceHtml(null)}
                highlightedSentences={citationResult?.missing_claims.map((claim) => claim.sentence) || []}
                citationSuggestion={citationSuggestion}
                onCitationSuggestionApplied={() => setCitationSuggestion(null)}
                onAskAI={(text) => {
                  setSelectedText(text);
                  setIsAIResponsePanelOpen(true);
                  setRightPanelTab("assistant");
                }}
              />
            </div>
          </div>
        </main>

        {/* Right Sidebar: Literature Search & Persistent Selected Papers / AI Assistant */}
        <aside className="hidden w-full shrink-0 flex-col border-l border-gray-200 bg-gray-50/70 md:flex md:w-80 lg:w-96">
          <div className="flex shrink-0 border-b border-gray-200 bg-white p-2">
            <button
              type="button"
              onClick={() => setRightPanelTab("literature")}
              className={`flex-1 rounded-md px-3 py-2 text-xs font-medium transition ${
                rightPanelTab === "literature" ? "bg-purple-100 text-purple-700" : "text-gray-600 hover:bg-gray-100"
              }`}
            >
              Tài liệu ({selectedPapers.length})
            </button>
            <button
              type="button"
              onClick={() => setRightPanelTab("assistant")}
              className={`flex-1 rounded-md px-3 py-2 text-xs font-medium transition ${
                rightPanelTab === "assistant" ? "bg-purple-100 text-purple-700" : "text-gray-600 hover:bg-gray-100"
              }`}
            >
              AI Assistant
            </button>
          </div>

          <div className="min-h-0 flex-1 overflow-y-auto">
            {rightPanelTab === "literature" ? (
              <>
                {/* Sub-tabs: Tìm kiếm học thuật vs Tài liệu đề tài */}
                <div className="flex border-b border-gray-200 bg-gray-100/70 p-1.5 gap-1 text-xs">
                  <button
                    type="button"
                    onClick={() => setLiteratureSubTab("search")}
                    className={`flex-1 py-1.5 px-2 rounded font-medium flex items-center justify-center gap-1.5 transition ${
                      literatureSubTab === "search" ? "bg-white text-purple-700 shadow-2xs" : "text-gray-600 hover:bg-gray-200/60"
                    }`}
                  >
                    <Search className="w-3.5 h-3.5" />
                    <span>Tìm kiếm học thuật</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setLiteratureSubTab("saved")}
                    className={`flex-1 py-1.5 px-2 rounded font-medium flex items-center justify-center gap-1.5 transition ${
                      literatureSubTab === "saved" ? "bg-white text-purple-700 shadow-2xs" : "text-gray-600 hover:bg-gray-200/60"
                    }`}
                  >
                    <BookOpen className="w-3.5 h-3.5" />
                    <span>Tài liệu đề tài ({selectedPapers.length})</span>
                  </button>
                </div>

                {literatureSubTab === "search" ? (
                  <>
                    <SearchFilters
                      query={literatureQuery}
                      filters={literatureFilters}
                      onQueryChange={setLiteratureQuery}
                      onFiltersChange={setLiteratureFilters}
                      onSearch={handleSearchLiterature}
                      loading={literatureLoading}
                      hasSearched={submittedLiteratureQuery.length > 0}
                      hasResults={literaturePapers.length > 0}
                    />

                    {/* Huy hiệu hiển thị trạng thái Cache 48h vs Tìm mới */}
                    {searchModeBadge ? (
                      <div className="mx-3 mt-2">
                        <span
                          className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-medium border ${
                            searchModeBadge.isCache
                              ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                              : "bg-blue-50 text-blue-700 border-blue-200"
                          }`}
                        >
                          {searchModeBadge.text}
                        </span>
                      </div>
                    ) : null}

                    {expandedQueries && expandedQueries.length > 0 ? (
                      <div className="mx-3 mt-2 rounded-xl border border-purple-100 bg-purple-50/60 p-2.5 text-xs">
                        <div className="font-semibold text-purple-900 mb-1.5 flex items-center gap-1.5">
                          <Sparkles className="w-3.5 h-3.5 text-purple-600" />
                          <span>Từ khóa học thuật đã mở rộng:</span>
                        </div>
                        <div className="flex flex-wrap gap-1.5">
                          {expandedQueries.map((eq, idx) => (
                            <span
                              key={idx}
                              className="bg-white border border-purple-200 text-purple-700 px-2.5 py-0.5 rounded-full text-[11px] font-medium shadow-2xs"
                            >
                              {eq}
                            </span>
                          ))}
                        </div>
                      </div>
                    ) : null}

                    {literatureError ? (
                      <div className="m-3 rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-700">
                        {literatureError}
                      </div>
                    ) : null}

                    <LiteratureList
                      papers={literaturePapers}
                      loading={literatureLoading}
                      error={literatureError}
                      selectedPaperId={selectedPaper?.id}
                      selectedPaperIds={selectedPaperIds}
                      selectingPaperId={selectingPaperId}
                      onSelectPaper={handleSelectPaper}
                    />

                    {selectedPaper ? (
                      <div className="space-y-3 border-t border-gray-200 bg-white p-3">
                        <div className="rounded-lg border border-purple-200 bg-purple-50 p-3">
                          <div className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-purple-700">
                            Tài liệu đang xem
                          </div>
                          <h4 className="text-sm font-semibold text-gray-900">{selectedPaper.title}</h4>
                          <p className="mt-1 text-[11px] text-gray-600">{formatAuthors(selectedPaper.authors)}</p>
                          {selectedPaper.abstract ? (
                            <p className="mt-2 line-clamp-4 text-[11px] leading-5 text-gray-600">{selectedPaper.abstract}</p>
                          ) : null}

                          <div className="mt-3 flex flex-wrap gap-2">
                            <button
                              type="button"
                              onClick={() => handleSummarizePaper(selectedPaper)}
                              disabled={summaryLoadingPaperId === selectedPaper.id}
                              className="rounded-md bg-purple-600 px-2.5 py-1.5 text-[11px] font-medium text-white disabled:cursor-not-allowed disabled:opacity-70"
                            >
                              {summaryLoadingPaperId === selectedPaper.id ? "Đang tóm tắt..." : "Tóm tắt tiếng Việt"}
                            </button>
                            <button
                              type="button"
                              onClick={() => handleInsertPaperReference(selectedPaper)}
                              className="rounded-md border border-gray-300 bg-white px-2.5 py-1.5 text-[11px] font-medium text-gray-700 hover:bg-gray-50"
                            >
                              Chèn vào bài viết
                            </button>
                          </div>

                          {summaryError ? (
                            <div className="mt-3 rounded-md border border-red-200 bg-red-50 px-2 py-2 text-[11px] text-red-700">
                              {summaryError}
                            </div>
                          ) : null}

                          {selectedPaper.summaryVi ? (
                            <div className="mt-3 rounded-md border border-gray-200 bg-white p-2.5 text-[11px] leading-5 text-gray-700">
                              {selectedPaper.summaryVi}
                            </div>
                          ) : null}
                        </div>
                      </div>
                    ) : null}
                  </>
                ) : (
                  /* Sub-tab: Danh sách tài liệu đã chọn lưu vĩnh viễn */
                  <div className="p-3 space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="text-xs text-gray-500 font-medium">
                        {selectedPapers.length} tài liệu đã lưu vĩnh viễn theo đề tài
                      </div>
                      {selectedPapers.length > 0 ? (
                        <button
                          type="button"
                          onClick={handleInsertFullBibliography}
                          className="text-[11px] text-purple-700 hover:underline font-semibold flex items-center gap-1"
                          title="Chèn toàn bộ danh mục tài liệu tham khảo theo đúng chuẩn của đề tài"
                        >
                          📋 Chèn mục lục
                        </button>
                      ) : null}
                    </div>

                    {selectedPapers.length === 0 ? (
                      <div className="text-center py-12 px-4 border border-dashed border-gray-300 rounded-xl bg-white/50">
                        <BookOpen className="w-8 h-8 text-gray-300 mx-auto mb-2" />
                        <h4 className="text-xs font-bold text-gray-800 mb-1">Chưa có tài liệu được chọn</h4>
                        <p className="text-[11px] text-gray-500 mb-3">
                          Hãy chuyển sang tab &quot;Tìm kiếm học thuật&quot; và bấm nút &quot;Chọn tài liệu&quot; để lưu trữ vĩnh viễn cho đề tài này.
                        </p>
                        <button
                          type="button"
                          onClick={() => setLiteratureSubTab("search")}
                          className="bg-purple-600 hover:bg-purple-700 text-white text-xs font-medium py-1.5 px-3 rounded-md transition shadow-sm"
                        >
                          🔍 Đi tới tìm kiếm
                        </button>
                      </div>
                    ) : (
                      <div className="space-y-3">
                        {selectedPapers.map((sp) => {
                          const p = sp.paper;
                          return (
                            <div key={sp.id} className="bg-white border border-gray-200 rounded-lg p-3 shadow-2xs space-y-2">
                              <div className="flex items-start justify-between gap-2">
                                <h4 className="text-xs font-semibold text-gray-900 leading-snug">
                                  {p?.title || "Tài liệu nghiên cứu"}
                                </h4>
                                <button
                                  type="button"
                                  onClick={() => handleRemoveSelectedPaper(sp.id)}
                                  className="text-gray-400 hover:text-red-600 transition p-1"
                                  title="Xóa khỏi tài liệu đề tài"
                                >
                                  <Trash2 className="w-3.5 h-3.5" />
                                </button>
                              </div>

                              <p className="text-[11px] text-gray-500">
                                {formatAuthors(p?.authors)}
                                {p?.year ? ` (${p.year})` : ""}
                              </p>

                              {sp.citation_formatted ? (
                                <div className="bg-purple-50/70 border border-purple-100 rounded p-2 text-[11px] text-purple-900 font-serif leading-relaxed">
                                  {sp.citation_formatted}
                                </div>
                              ) : null}

                              <div className="flex items-center justify-between pt-1 text-[11px]">
                                {p?.doi || p?.url ? (
                                  <a
                                    href={p.url || `https://doi.org/${p.doi}`}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="text-purple-600 hover:underline flex items-center gap-1 truncate max-w-[140px]"
                                  >
                                    <ExternalLink className="w-3 h-3 shrink-0" />
                                    <span>{p.doi || "Link gốc"}</span>
                                  </a>
                                ) : <span />}

                                <button
                                  type="button"
                                  onClick={() => p && handleInsertPaperReference(p, sp.citation_formatted)}
                                  className="text-gray-700 bg-gray-100 hover:bg-gray-200 px-2 py-1 rounded text-[11px] font-medium transition"
                                >
                                  Chèn vào bài
                                </button>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                )}
              </>
            ) : isAIResponsePanelOpen || rightPanelTab === "assistant" ? (
              <AIResponsePanel
                selectedText={selectedText || "Hãy bôi đen một câu hoặc đoạn văn bản trong Editor để AI Coach phân tích, giải thích thuật ngữ hoặc viết lại theo chuẩn học thuật."}
                projectId={project?.id}
                onCreditDeducted={() => setCreditTrigger((c) => c + 1)}
                onClose={() => {
                  setIsAIResponsePanelOpen(false);
                  setSelectedText("");
                  setRightPanelTab("literature");
                }}
              />
            ) : (
              <div className="p-4 text-sm text-gray-500">
                Chọn một đoạn văn bản trong editor rồi bấm &quot;Hỏi AI&quot; để bắt đầu.
              </div>
            )}
          </div>
        </aside>
      </div>

      {/* Modal Báo Cáo Kiểm Tra Trích Dẫn (Tuần 3) */}
      {isCitationModalOpen && citationResult ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[85vh] flex flex-col overflow-hidden border border-gray-200 animate-in fade-in zoom-in-95 duration-150">
            <div className="p-4 border-b border-gray-200 flex items-center justify-between bg-purple-50/50">
              <div className="flex items-center gap-2">
                <ShieldAlert className="w-5 h-5 text-purple-600" />
                <h3 className="font-bold text-gray-900 text-sm">
                  Báo Cáo Kiểm Tra Trích Dẫn Toàn Bài (Citation Agent)
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setIsCitationModalOpen(false)}
                className="text-gray-400 hover:text-gray-700 text-sm font-semibold p-1"
              >
                ✕
              </button>
            </div>

            <div className="p-4 overflow-y-auto space-y-4 text-xs">
              <div className="grid grid-cols-3 gap-3">
                <div className="bg-gray-50 p-3 rounded-lg border border-gray-200 text-center">
                  <div className="text-lg font-bold text-gray-800">{citationResult.total_issues}</div>
                  <div className="text-[11px] text-gray-500">Tổng điểm cần lưu ý</div>
                </div>
                <div className="bg-amber-50 p-3 rounded-lg border border-amber-200 text-center">
                  <div className="text-lg font-bold text-amber-700">{citationResult.missing_claims.length}</div>
                  <div className="text-[11px] text-amber-600">Câu thiếu dẫn nguồn</div>
                </div>
                <div className="bg-emerald-50 p-3 rounded-lg border border-emerald-200 text-center">
                  <div className="text-lg font-bold text-emerald-700">{citationResult.verified_count}</div>
                  <div className="text-[11px] text-emerald-600">Trích dẫn đã khớp</div>
                </div>
              </div>

              {citationResult.missing_claims.length > 0 ? (
                <div className="space-y-2">
                  <div className="font-semibold text-gray-900 text-xs flex items-center gap-1.5">
                    <span className="text-amber-500">⚠️</span> Các câu khẳng định/số liệu thiếu dẫn chứng:
                  </div>
                  <div className="space-y-2">
                    {citationResult.missing_claims.map((claim, idx) => (
                      <div key={idx} className="bg-amber-50/50 border border-amber-200 rounded-lg p-3 space-y-1">
                        <div className="text-gray-800 font-medium italic">
                          &quot;{claim.sentence}&quot;
                        </div>
                        <div className="text-amber-800 text-[11px]">
                          <strong>Lý do:</strong> {claim.reason}
                        </div>
                        <div className="text-gray-600 text-[11px]">
                          <strong>Gợi ý:</strong> {claim.suggested_action}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-3 text-emerald-800 text-center">
                  ✓ Không phát hiện câu khẳng định hoặc số liệu định lượng nào thiếu nguồn!
                </div>
              )}

              {citationResult.invalid_citations && citationResult.invalid_citations.length > 0 ? (
                <div className="space-y-2">
                  <div className="font-semibold text-red-700 text-xs">
                    ❌ Sai lệch danh mục tài liệu tham khảo:
                  </div>
                  <div className="space-y-1.5">
                    {citationResult.invalid_citations.map((errText, idx) => (
                      <div key={idx} className="bg-red-50 border border-red-200 rounded p-2 text-red-700 text-[11px]">
                        • {errText}
                      </div>
                    ))}

                    {citationResult.suggestions?.length ? (
                      <div className="space-y-2">
                        <div className="font-semibold text-gray-900 text-xs">Gợi ý thay thế từ AI:</div>
                        {citationResult.suggestions.map((suggestion, index) => (
                          <div key={`${suggestion.original_text}-${index}`} className="rounded-lg border border-purple-200 bg-purple-50/60 p-3 text-[11px]">
                            <p className="text-gray-700">{suggestion.reason}</p>
                            {suggestion.suggested_text ? (
                              <button
                                type="button"
                                onClick={() => handleAcceptCitationSuggestion(suggestion)}
                                className="mt-2 rounded-md bg-purple-600 px-2.5 py-1.5 font-semibold text-white hover:bg-purple-700"
                              >
                                Chấp nhận gợi ý AI
                              </button>
                            ) : <p className="mt-2 text-amber-700">Chưa có tài liệu đã chọn để đề xuất nguồn.</p>}
                          </div>
                        ))}
                      </div>
                    ) : null}

                    <BibliographyView
                      citations={citationResult.bibliography || []}
                      style={project?.citation_style || "apa7"}
                    />
                  </div>
                </div>
              ) : null}
            </div>

            <div className="p-3 border-t border-gray-200 bg-gray-50 flex justify-end">
              <button
                type="button"
                onClick={() => setIsCitationModalOpen(false)}
                className="bg-purple-600 hover:bg-purple-700 text-white text-xs font-medium px-4 py-2 rounded-lg transition"
              >
                Đã hiểu & Tiếp tục viết bài
              </button>
            </div>
          </div>
        </div>
      ) : null}
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