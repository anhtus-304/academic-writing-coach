"use client";

import { useEffect, useState, useRef, Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import {
  projectApi,
  outlineApi,
  authApi,
  literatureApi,
  citationApi,
  documentApi,
  ProjectData,
  OutlineData,
  UserProfile,
  CitationCheckResponse,
  CitationSuggestion,
} from "@/lib/api";
import { OutlineEditor, OutlineNode, generateTableOfContentsHtml } from "@/components/outline/OutlineEditor";
import { TiptapEditor } from "@/components/editor/TiptapEditor";
import { AIResponsePanel } from "@/components/editor/AIResponsePanel";
import { LiteratureList } from "@/components/literature/LiteratureList";
import { SearchFilters } from "@/components/literature/SearchFilters";
import { CreditBalance } from "@/components/CreditBalance";
import { ExportDropdown } from "@/components/workspace/ExportDropdown";
import { ImportModal } from "@/components/workspace/ImportModal";
import AIUseLog from "@/components/AIUseLog";
import { formatAuthors, type LiteraturePaper, type LiteratureFilters, type SelectedPaperItem } from "@/components/literature/types";
import { BibliographyView } from "@/components/citation/BibliographyView";
import { AgentStepper } from "@/components/agents/AgentStepper";
import {
  Check,
  Trash2,
  BookOpen,
  Search,
  ShieldAlert,
  Sparkles,
  FileCheck,
  ExternalLink,
  Pencil,
  UploadCloud,
  X,
  PanelLeftClose,
  PanelLeftOpen,
  PanelRightClose,
  PanelRightOpen,
  Terminal,
  ChevronDown,
  ChevronUp,
  ChevronLeft,
  ChevronRight,
  Maximize2,
  Minimize2,
  PanelLeft,
  PanelRight,
} from "lucide-react";

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

  // Topic Edit state (Yêu cầu 3)
  const [isEditingTopic, setIsEditingTopic] = useState(false);
  const [editingTopicValue, setEditingTopicValue] = useState("");

  // Import Modal state (Yêu cầu 5)
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);

  // Cuộn đến tiêu đề tương ứng khi click vào Dàn ý
  const [scrollToHeadingText, setScrollToHeadingText] = useState<string | null>(null);
  const isFirstMount = useRef(true);

  // Citation Agent State (Tuần 3)
  const [checkingCitations, setCheckingCitations] = useState(false);
  const [citationResult, setCitationResult] = useState<CitationCheckResponse | null>(null);
  const [isCitationModalOpen, setIsCitationModalOpen] = useState(false);
  const [citationSuggestion, setCitationSuggestion] = useState<{ originalText: string; suggestedText: string } | null>(null);

  // Layout states: Resizable 3-columns and IDE bottom terminal
  const [leftWidth, setLeftWidth] = useState(320);
  const [isLeftCollapsed, setIsLeftCollapsed] = useState(false);
  const [rightWidth, setRightWidth] = useState(380);
  const [isRightCollapsed, setIsRightCollapsed] = useState(false);
  const [bottomHeight, setBottomHeight] = useState(260);
  const [isBottomOpen, setIsBottomOpen] = useState(false);
  const [isBottomMaximized, setIsBottomMaximized] = useState(false);

  const isResizingLeft = useRef(false);
  const isResizingRight = useRef(false);
  const isResizingBottom = useRef(false);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (isResizingLeft.current) {
        const newWidth = Math.min(Math.max(e.clientX, 220), 500);
        setLeftWidth(newWidth);
      } else if (isResizingRight.current) {
        const newWidth = Math.min(Math.max(window.innerWidth - e.clientX, 260), 620);
        setRightWidth(newWidth);
      } else if (isResizingBottom.current) {
        const newHeight = Math.min(Math.max(window.innerHeight - e.clientY - 32, 140), 550);
        setBottomHeight(newHeight);
      }
    };

    const handleMouseUp = () => {
      if (isResizingLeft.current || isResizingRight.current || isResizingBottom.current) {
        isResizingLeft.current = false;
        isResizingRight.current = false;
        isResizingBottom.current = false;
        document.body.style.cursor = "";
        document.body.style.userSelect = "";
      }
    };

    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, []);

  const startResizingLeft = (e: React.MouseEvent) => {
    e.preventDefault();
    isResizingLeft.current = true;
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
  };

  const startResizingRight = (e: React.MouseEvent) => {
    e.preventDefault();
    isResizingRight.current = true;
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
  };

  const startResizingBottom = (e: React.MouseEvent) => {
    e.preventDefault();
    isResizingBottom.current = true;
    document.body.style.cursor = "row-resize";
    document.body.style.userSelect = "none";
  };

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
          const [projData, outlineRes, selectedRes, recentRes, draftRes] = await Promise.all([
            projectApi.get(targetProjectId).catch(() => null),
            outlineApi.get(targetProjectId).catch(() => ({ success: false, outline: null })),
            literatureApi.getSelectedPapers(targetProjectId).catch(() => ({ total: 0, selected_papers: [] })),
            literatureApi.getRecentSearch(targetProjectId).catch(() => null),
            documentApi.get(targetProjectId).catch(() => ({ success: false, document: null })),
          ]);

          if (projData) setProject(projData);

          let initialEditorHtml = "";
          // 1. Ưu tiên cao nhất: Bản nháp đã lưu trên Database (Yêu cầu 2)
          if (draftRes && draftRes.success && draftRes.document && draftRes.document.html) {
            initialEditorHtml = draftRes.document.html;
          } else if (typeof window !== "undefined") {
            // 2. Dự phòng khẩn cấp: LocalStorage
            const cachedLocal = localStorage.getItem("draft_doc_" + targetProjectId);
            if (cachedLocal && cachedLocal.trim()) {
              initialEditorHtml = cachedLocal;
            }
          }

          if (outlineRes.success && outlineRes.outline) {
            setOutline(outlineRes.outline);
            const nodes = transformBackendOutlineToNodes(outlineRes.outline.chapters);
            setOutlineNodes(nodes);
            // 3. Nếu chưa từng có bài viết thì mới khởi tạo từ Dàn ý
            if (!initialEditorHtml) {
              initialEditorHtml = outlineNodesToHtml(nodes);
            }
          }

          if (initialEditorHtml) {
            setEditorContent(initialEditorHtml);
            setSaveStatus("Đã lưu");
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

  // Cơ chế Tự động lưu ngầm (Debounce 2000ms Auto-save - Yêu cầu 2)
  useEffect(() => {
    if (isFirstMount.current) {
      isFirstMount.current = false;
      return;
    }
    if (!project || !editorContent) return;

    // Backup tức thì vào LocalStorage
    try {
      localStorage.setItem("draft_doc_" + project.id, editorContent);
    } catch {
      // ignore
    }

    const timer = setTimeout(async () => {
      try {
        setSaveStatus("Đang lưu...");
        await documentApi.save(project.id, editorContent);
        const timeStr = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
        setSaveStatus(`Đã lưu lúc ${timeStr}`);
      } catch (e) {
        console.warn("Auto-save draft failed:", e);
        setSaveStatus("Lỗi lưu tự động");
      }
    }, 2000);

    return () => clearTimeout(timer);
  }, [editorContent, project]);

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

  // Chèn trích dẫn nội văn vào vị trí con trỏ (In-text citation - thuần văn bản, không thẻ giao diện)
  const handleInsertInTextCitation = (paper: LiteraturePaper, index: number) => {
    let inText = "";
    if (project?.citation_style === "ieee" || project?.citation_style === "bgddt") {
      inText = `[${index}]`;
    } else {
      // APA 7th edition: (Author, Year)
      const authors = paper.authors || [];
      if (authors.length === 0) {
        inText = `(Tài liệu học thuật, ${paper.year || "n.d."})`;
      } else {
        const getSurname = (name: string) => {
          if (name.includes(",")) return name.split(",")[0].trim();
          const parts = name.trim().split(/\s+/);
          return parts[parts.length - 1];
        };
        if (authors.length === 1) {
          inText = `(${getSurname(authors[0])}, ${paper.year || "n.d."})`;
        } else if (authors.length === 2) {
          inText = `(${getSurname(authors[0])} & ${getSurname(authors[1])}, ${paper.year || "n.d."})`;
        } else {
          inText = `(${getSurname(authors[0])} et al., ${paper.year || "n.d."})`;
        }
      }
    }
    // Chèn thuần text với một khoảng trắng phía trước, không bọc trong <span> hay thẻ HTML
    setInsertReferenceHtml(` ${inText} `);
  };

  const handleInsertSnippetFromModal = (snippet: string) => {
    // Chèn thuần text từ modal, không thẻ HTML
    setInsertReferenceHtml(` ${snippet.trim()} `);
  };

  // Chèn 1 dòng danh mục tài liệu tham khảo đầy đủ (Bibliography entry)
  const handleInsertPaperReference = (paper: LiteraturePaper, customCitation?: string) => {
    let reference = "";
    if (customCitation) {
      reference = `<p class="citation-entry">${escapeHtml(customCitation)}</p>`;
    } else {
      const authors = formatAuthors(paper.authors);
      const year = paper.year || "n.d.";
      reference = `<p class="citation-entry"><strong>${escapeHtml(paper.title)}</strong> (${escapeHtml(authors)}, ${year}). ${paper.url ? `<a href="${paper.url}" target="_blank" rel="noreferrer">${paper.url}</a>` : ""}</p>`;
    }
    setInsertReferenceHtml(reference);
  };

  // Chèn toàn bộ danh mục tài liệu tham khảo đã chọn vào cuối bài (Sắp xếp chuẩn theo chuẩn trích dẫn đề tài)
  const handleInsertFullBibliography = async () => {
    if (!project || selectedPapers.length === 0) return;

    try {
      // Gọi API backend để lấy danh mục đã được sắp xếp chính xác theo chuẩn của đề tài
      // (APA7: sắp A-Z theo họ tác giả đầu; IEEE: đánh số thứ tự tăng dần; BGDDT: tiếng Việt trước theo tên, tiếng nước ngoài theo họ)
      const res = await citationApi.getProjectBibliography(project.id, project.citation_style);
      if (res && res.bibliography && res.bibliography.length > 0) {
        const entries = res.bibliography
          .map((entry) => `<p class="citation-entry">${escapeHtml(entry)}</p>`)
          .join("");
        const bibHtml = `<h2>TÀI LIỆU THAM KHẢO</h2>${entries}`;
        setInsertReferenceHtml(bibHtml);
        return;
      }
    } catch (err) {
      console.warn("Lấy danh mục tài liệu tham khảo từ API gặp lỗi, dùng fallback nội bộ:", err);
    }

    // Fallback nội bộ nếu mất mạng hoặc API gặp sự cố
    const entries = selectedPapers
      .map((sp, idx) => {
        let text = sp.citation_formatted || `${sp.paper?.title} (${sp.paper?.year || "n.d."})`;
        // Tránh lặp số [1] [1] nếu đã có sẵn số thứ tự ở đầu chuỗi
        if ((project?.citation_style === "ieee" || project?.citation_style === "bgddt") && !text.trim().startsWith("[")) {
          text = `[${idx + 1}] ${text}`;
        }
        return `<p class="citation-entry">${escapeHtml(text)}</p>`;
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
      if (!res.bibliography || res.bibliography.length === 0) {
        try {
          const bibRes = await citationApi.getProjectBibliography(project.id, project.citation_style);
          if (bibRes && bibRes.bibliography) {
            res.bibliography = bibRes.bibliography;
          }
        } catch (bibErr) {
          console.warn("Could not fetch project bibliography:", bibErr);
        }
      }
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

  // Lưu cả Dàn ý và Bài viết (Yêu cầu 2)
  const handleSaveAll = async () => {
    if (!project) return;
    setSaving(true);
    setSaveStatus("Đang lưu...");
    try {
      await Promise.all([
        outlineNodes.length > 0 ? outlineApi.update(project.id, outlineNodes, outline?.suggestions) : Promise.resolve(),
        documentApi.save(project.id, editorContent),
      ]);
      const timeStr = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
      setSaveStatus(`Đã lưu lúc ${timeStr}`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Đã có lỗi xảy ra";
      alert("Lưu thất bại: " + msg);
      setSaveStatus("Lưu thất bại");
    } finally {
      setSaving(false);
    }
  };

  // Chỉnh sửa tên đề tài trực tiếp (Yêu cầu 3)
  const handleStartEditTopic = () => {
    setEditingTopicValue(project?.topic || "");
    setIsEditingTopic(true);
  };

  const handleSaveTopic = async () => {
    const trimmed = editingTopicValue.trim();
    if (!project || !trimmed) {
      setIsEditingTopic(false);
      return;
    }
    try {
      const updated = await projectApi.update(project.id, { topic: trimmed });
      setProject((prev) => (prev ? { ...prev, topic: updated.topic } : prev));
      setIsEditingTopic(false);
    } catch (err: unknown) {
      alert("Đổi tên đề tài thất bại: " + (err instanceof Error ? err.message : ""));
    }
  };

  // Xử lý Import Dàn ý (Yêu cầu 5A)
  const handleImportOutline = async (newNodes: OutlineNode[], mode: "replace" | "append") => {
    if (!project) return;
    let finalNodes: OutlineNode[] = [];
    if (mode === "replace" || outlineNodes.length === 0) {
      finalNodes = newNodes;
    } else {
      finalNodes = [...outlineNodes, ...newNodes];
    }
    setOutlineNodes(finalNodes);
    try {
      await outlineApi.update(project.id, finalNodes, outline?.suggestions);
      setSaveStatus("Đã nhập dàn ý mới");
    } catch (e) {
      console.warn("Failed to auto-save imported outline:", e);
    }
  };

  // Xử lý Import Bài viết (Yêu cầu 5B)
  const handleImportDocument = (html: string, mode: "replace" | "insert") => {
    if (mode === "replace") {
      setEditorContent(html);
    } else {
      setInsertReferenceHtml(html);
    }
  };

  const handleOutlineChange = (nextNodes: OutlineNode[]) => {
    setOutlineNodes(nextNodes);
    setSaveStatus("Chưa lưu...");
  };

  const selectedPaperIds = selectedPapers.map((sp) => sp.cached_paper_id || sp.id);

  const wordCount = editorContent
    ? editorContent.replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim().split(/\s+/).filter(Boolean).length
    : 0;
  const pageEstimate = Math.max(1, Math.ceil(wordCount / 350));

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
        <div className="flex items-center space-x-3">
          <Link
            href="/dashboard"
            className="w-8 h-8 bg-gray-100 rounded-lg flex items-center justify-center hover:bg-gray-200 transition text-gray-600 shrink-0"
            title="Về Dashboard"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 19l-7-7m0 0l7-7m-7 7h18"></path>
            </svg>
          </Link>

          {/* Chỉnh sửa Tên đề tài trực tiếp (Yêu cầu 3) */}
          {isEditingTopic ? (
            <div className="flex items-center gap-1.5">
              <input
                type="text"
                value={editingTopicValue}
                onChange={(e) => setEditingTopicValue(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") handleSaveTopic();
                  if (e.key === "Escape") setIsEditingTopic(false);
                }}
                autoFocus
                className="text-xs border border-purple-300 rounded px-2.5 py-1 font-medium text-gray-900 focus:outline-none focus:ring-1 focus:ring-purple-500 max-w-sm w-72"
              />
              <button
                type="button"
                onClick={handleSaveTopic}
                className="text-green-600 hover:text-green-700 p-1"
                title="Lưu tên đề tài (Enter)"
              >
                <Check className="w-4 h-4" />
              </button>
              <button
                type="button"
                onClick={() => setIsEditingTopic(false)}
                className="text-gray-400 hover:text-gray-600 p-1"
                title="Hủy (Esc)"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-1.5 group max-w-md">
              <span className="font-semibold text-gray-900 text-sm truncate" title={project?.topic}>
                {project?.topic || "Dự án nghiên cứu"}
              </span>
              <button
                type="button"
                onClick={handleStartEditTopic}
                className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-purple-600 transition p-1 shrink-0"
                title="Chỉnh sửa tên đề tài"
              >
                <Pencil className="w-3.5 h-3.5" />
              </button>
            </div>
          )}

          <div className="text-[11px] text-gray-500 bg-gray-100 px-2 py-1 rounded shrink-0">
            {saveStatus}
          </div>
        </div>

        <div className="flex items-center space-x-2">
          {/* Nút Nhập tệp (Import - Yêu cầu 5) */}
          <button
            type="button"
            onClick={() => setIsImportModalOpen(true)}
            className="inline-flex items-center gap-1.5 bg-white hover:bg-gray-50 text-gray-700 border border-gray-200 text-xs px-3 py-1.5 rounded-md font-medium transition shadow-2xs active:scale-95"
            title="Nhập dàn ý hoặc tài liệu từ Word (.docx) hoặc Markdown (.md)"
          >
            <UploadCloud className="w-3.5 h-3.5 text-purple-600" />
            <span>Nhập tệp</span>
          </button>

          {/* Nút Xuất file (Export - Yêu cầu 4) */}
          <ExportDropdown
            projectId={project?.id || ""}
            topic={project?.topic}
            editorContent={editorContent}
          />

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

          {/* Nút Lưu bài viết & dàn ý (Yêu cầu 2) */}
          <button
            onClick={handleSaveAll}
            disabled={saving}
            className="bg-gray-100 hover:bg-gray-200 text-gray-700 text-xs px-3 py-1.5 rounded-md font-medium transition flex items-center"
            title="Lưu đồng bộ cả dàn ý và bài viết vào cơ sở dữ liệu"
          >
            {saving ? "Đang lưu..." : "💾 Lưu bài viết"}
          </button>

          <div className="h-5 w-px bg-gray-200 mx-0.5" />

          {/* Nút Điều Khiển Bố Cục (Layout Panels: Trái / Terminal / Phải) */}
          <div className="flex items-center bg-gray-100/90 rounded-lg p-0.5 border border-gray-200/80">
            <button
              type="button"
              onClick={() => setIsLeftCollapsed(!isLeftCollapsed)}
              className={`p-1.5 rounded transition ${
                !isLeftCollapsed ? "bg-white text-purple-700 shadow-2xs font-semibold" : "text-gray-500 hover:text-gray-900"
              }`}
              title={isLeftCollapsed ? "Mở Cột Trái (Dàn ý)" : "Thu gọn Cột Trái (Dàn ý)"}
            >
              <PanelLeft className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              onClick={() => setIsBottomOpen(!isBottomOpen)}
              className={`p-1.5 rounded transition ${
                isBottomOpen ? "bg-white text-purple-700 shadow-2xs font-semibold" : "text-gray-500 hover:text-gray-900"
              }`}
              title={isBottomOpen ? "Đóng Terminal AI Use Log" : "Mở Terminal AI Use Log"}
            >
              <Terminal className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              onClick={() => setIsRightCollapsed(!isRightCollapsed)}
              className={`p-1.5 rounded transition ${
                !isRightCollapsed ? "bg-white text-purple-700 shadow-2xs font-semibold" : "text-gray-500 hover:text-gray-900"
              }`}
              title={isRightCollapsed ? "Mở Cột Phải (Tài liệu & AI)" : "Thu gọn Cột Phải (Tài liệu & AI)"}
            >
              <PanelRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="h-5 w-px bg-gray-200 mx-0.5" />

          <CreditBalance initialBalance={user?.credits} refreshTrigger={creditTrigger} />
        </div>
      </header>

      {/* Main Workspace Layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Sidebar: Outline Agent & Editor */}
        {isLeftCollapsed ? (
          <div className="w-9 border-r border-gray-200 bg-gray-50 flex flex-col items-center py-3 shrink-0 select-none">
            <button
              type="button"
              onClick={() => setIsLeftCollapsed(false)}
              className="p-1.5 text-gray-500 hover:text-purple-600 hover:bg-purple-50 rounded-md transition"
              title="Mở rộng Dàn ý (Cột Trái)"
            >
              <PanelLeftOpen className="w-4 h-4" />
            </button>
            <span className="mt-8 text-[11px] font-bold text-gray-400 uppercase tracking-widest [writing-mode:vertical-lr] rotate-180">
              Mục lục Dàn ý
            </span>
          </div>
        ) : (
          <aside
            style={{ width: `${leftWidth}px` }}
            className="border-r border-gray-200 flex flex-col bg-gray-50/70 shrink-0 relative"
          >
            {/* Left Resize Handle */}
            <div
              onMouseDown={startResizingLeft}
              className="absolute -right-1 top-0 bottom-0 w-2 cursor-col-resize hover:bg-purple-500/50 z-20 transition select-none"
              title="Kéo sang trái/phải để chỉnh độ rộng Cột Dàn ý"
            />
            <div className="p-2.5 flex items-center justify-between border-b border-gray-200 bg-white">
              <div className="flex space-x-1">
                <button
                  onClick={() => setActiveTab("outline")}
                  className={`text-xs px-2 py-1 rounded-md font-medium transition ${
                    activeTab === "outline" ? "bg-purple-100 text-purple-700" : "text-gray-600 hover:bg-gray-100"
                  }`}
                >
                  Mục lục Dàn ý
                </button>
                <button
                  onClick={() => setActiveTab("suggestions")}
                  className={`text-xs px-2 py-1 rounded-md font-medium transition ${
                    activeTab === "suggestions" ? "bg-purple-100 text-purple-700" : "text-gray-600 hover:bg-gray-100"
                  }`}
                >
                  Gợi ý AI
                </button>
              </div>
              <div className="flex items-center gap-1">
                <button
                  onClick={handleGenerateOutline}
                  disabled={generating}
                  className="text-xs bg-purple-600 text-white px-2 py-1 rounded-md hover:bg-purple-700 transition shadow-xs font-medium flex items-center active:scale-95"
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
                <button
                  type="button"
                  onClick={() => setIsLeftCollapsed(true)}
                  className="p-1 text-gray-400 hover:text-gray-700 rounded hover:bg-gray-100 transition"
                  title="Thu gọn Cột Trái"
                >
                  <PanelLeftClose className="w-3.5 h-3.5" />
                </button>
              </div>
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
                    title="Cấu trúc dàn ý"
                    onNavigateToSection={(sectionTitle) => {
                      setScrollToHeadingText(sectionTitle);
                    }}
                    onInsertTableOfContents={(tocHtml) => {
                      setInsertReferenceHtml(tocHtml);
                    }}
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
        )}

        {/* Center: Interactive Editor Area */}
        <main className="flex min-w-0 flex-1 flex-col overflow-hidden bg-white">
          <div className="flex-1 overflow-y-auto p-3 sm:p-6 lg:p-8">
            <div className="mx-auto w-full max-w-4xl space-y-4">
              <AgentStepper
                steps={[
                  { label: "Outline Agent", status: outline ? "success" : "pending" },
                  { label: "Literature Agent", status: selectedPapers.length > 0 ? "success" : "pending" },
                  { label: "Citation Agent", status: checkingCitations ? "running" : citationResult ? "success" : "pending" },
                  { label: "Citation Formatter", status: citationResult?.bibliography?.length ? "success" : "pending" },
                  { label: "Hoàn tất", status: citationResult ? "success" : "pending" },
                ]}
              />
              <h1 className="pt-2 text-center text-2xl font-bold uppercase leading-snug text-gray-900">
                {project?.topic}
              </h1>
              <TiptapEditor
                value={editorContent}
                onChange={(content) => {
                  setEditorContent(content);
                  setSaveStatus("Đang gõ...");
                }}
                placeholder="Bắt đầu viết nội dung nghiên cứu..."
                insertReferenceHtml={insertReferenceHtml}
                onReferenceInserted={() => setInsertReferenceHtml(null)}
                scrollToHeadingText={scrollToHeadingText}
                onInsertToc={() => {
                  const tocHtml = generateTableOfContentsHtml(outlineNodes);
                  setInsertReferenceHtml(tocHtml);
                }}
                highlightedSentences={citationResult?.missing_claims.map((claim) => claim.sentence) || []}
                citationSuggestion={citationSuggestion}
                onCitationSuggestionApplied={() => setCitationSuggestion(null)}
                onAskAI={(text) => {
                  setSelectedText(text);
                  setIsAIResponsePanelOpen(true);
                  setRightPanelTab("assistant");
                  if (isRightCollapsed) setIsRightCollapsed(false);
                }}
              />
            </div>
          </div>

          {/* IDE-style Bottom Terminal Panel: AI Use Log Dock */}
          {isBottomOpen && (
            <div
              style={{ height: isBottomMaximized ? "75vh" : `${bottomHeight}px` }}
              className="border-t-2 border-purple-600 bg-white flex flex-col shrink-0 shadow-lg relative transition-all duration-75"
            >
              {/* Drag handle */}
              {!isBottomMaximized && (
                <div
                  onMouseDown={startResizingBottom}
                  className="absolute -top-1 left-0 right-0 h-2 cursor-row-resize hover:bg-purple-500/40 z-20"
                  title="Kéo lên/xuống để chỉnh độ cao Terminal"
                />
              )}

              {/* Terminal Header */}
              <div className="flex items-center justify-between px-3 py-1.5 bg-gray-900 text-gray-200 text-xs shrink-0 select-none">
                <div className="flex items-center gap-2 font-mono">
                  <Terminal className="w-3.5 h-3.5 text-purple-400" />
                  <span className="font-semibold text-white">AI USE LOG & TRANSPARENCY</span>
                  <span className="text-[10px] bg-gray-800 text-purple-300 px-1.5 py-0.5 rounded border border-gray-700">
                    Terminal Dock
                  </span>
                </div>

                <div className="flex items-center gap-1">
                  <button
                    type="button"
                    onClick={() => setIsBottomMaximized(!isBottomMaximized)}
                    className="p-1 text-gray-400 hover:text-white rounded hover:bg-gray-800 transition"
                    title={isBottomMaximized ? "Thu nhỏ về độ cao mặc định" : "Mở rộng toàn màn hình"}
                  >
                    {isBottomMaximized ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
                  </button>
                  <button
                    type="button"
                    onClick={() => setIsBottomOpen(false)}
                    className="p-1 text-gray-400 hover:text-white rounded hover:bg-gray-800 transition"
                    title="Đóng Terminal"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              {/* Terminal Content */}
              <div className="flex-1 overflow-hidden">
                <AIUseLog
                  projectId={project?.id}
                  refreshTrigger={creditTrigger}
                  isDockMode={true}
                />
              </div>
            </div>
          )}

          {/* Academic Workspace Status Bar */}
          <div className="h-7 border-t border-gray-200 bg-gray-50/90 px-3 flex items-center justify-between text-[11px] text-gray-500 shrink-0 select-none">
            <div className="flex items-center gap-3">
              <span>{wordCount.toLocaleString('vi-VN')} từ</span>
              <span className="text-gray-300">•</span>
              <span>~{pageEstimate} trang A4</span>
              <span className="text-gray-300">•</span>
              <span className="text-purple-700 font-medium">Chuẩn {project?.citation_style?.toUpperCase()}</span>
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setIsBottomOpen(!isBottomOpen)}
                className={`flex items-center gap-1 px-2 py-0.5 rounded transition ${
                  isBottomOpen
                    ? "bg-purple-100 text-purple-800 font-semibold"
                    : "hover:bg-gray-200 text-gray-600"
                }`}
                title="Bật/Tắt Terminal Nhật ký tương tác AI"
              >
                <Terminal className="w-3 h-3 text-purple-600" />
                <span>AI Use Log</span>
                {isBottomOpen ? <ChevronDown className="w-3 h-3" /> : <ChevronUp className="w-3 h-3" />}
              </button>
            </div>
          </div>
        </main>

        {/* Right Sidebar: Literature Search & Persistent Selected Papers / AI Assistant */}
        {isRightCollapsed ? (
          <div className="hidden md:flex w-9 border-l border-gray-200 bg-gray-50 flex-col items-center py-3 shrink-0 select-none">
            <button
              type="button"
              onClick={() => setIsRightCollapsed(false)}
              className="p-1.5 text-gray-500 hover:text-purple-600 hover:bg-purple-50 rounded-md transition"
              title="Mở rộng Tài liệu & AI Assistant (Cột Phải)"
            >
              <PanelRightOpen className="w-4 h-4" />
            </button>
            <span className="mt-8 text-[11px] font-bold text-gray-400 uppercase tracking-widest [writing-mode:vertical-lr] rotate-180">
              Tài liệu & AI
            </span>
          </div>
        ) : (
          <aside
            style={{ width: `${rightWidth}px` }}
            className="hidden md:flex flex-col border-l border-gray-200 bg-gray-50/70 shrink-0 relative"
          >
            {/* Right Resize Handle */}
            <div
              onMouseDown={startResizingRight}
              className="absolute -left-1 top-0 bottom-0 w-2 cursor-col-resize hover:bg-purple-500/50 z-20 transition select-none"
              title="Kéo sang trái/phải để chỉnh độ rộng Cột Tài liệu"
            />
            <div className="flex shrink-0 border-b border-gray-200 bg-white p-2 items-center">
              <button
                type="button"
                onClick={() => setRightPanelTab("literature")}
                className={`flex-1 rounded-md px-3 py-1.5 text-xs font-medium transition ${
                  rightPanelTab === "literature" ? "bg-purple-100 text-purple-700" : "text-gray-600 hover:bg-gray-100"
                }`}
              >
                Tài liệu ({selectedPapers.length})
              </button>
              <button
                type="button"
                onClick={() => setRightPanelTab("assistant")}
                className={`flex-1 rounded-md px-3 py-1.5 text-xs font-medium transition ${
                  rightPanelTab === "assistant" ? "bg-purple-100 text-purple-700" : "text-gray-600 hover:bg-gray-100"
                }`}
              >
                AI Assistant
              </button>
              <button
                type="button"
                onClick={() => setIsRightCollapsed(true)}
                className="p-1.5 text-gray-400 hover:text-gray-700 rounded hover:bg-gray-100 transition ml-1"
                title="Thu gọn Cột Phải"
              >
                <PanelRightClose className="w-3.5 h-3.5" />
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
                        {selectedPapers.map((sp, idx) => {
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

                              {p?.doi || p?.url ? (
                                <div className="pt-0.5 text-[11px]">
                                  <a
                                    href={p.url || `https://doi.org/${p.doi}`}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="text-purple-600 hover:underline inline-flex items-center gap-1 truncate max-w-full font-sans"
                                    title={p.doi || p.url || "Link gốc"}
                                  >
                                    <ExternalLink className="w-3 h-3 shrink-0 text-purple-500" />
                                    <span className="truncate">{p.doi ? `DOI: ${p.doi}` : "Xem bài báo gốc"}</span>
                                  </a>
                                </div>
                              ) : null}

                              <div className="grid grid-cols-2 gap-2 pt-2 border-t border-gray-100 text-[11px]">
                                <button
                                  type="button"
                                  onClick={() => p && handleInsertInTextCitation(p, idx + 1)}
                                  className="h-8 px-2 rounded-md font-medium text-purple-700 bg-purple-50 hover:bg-purple-100 border border-purple-200 transition flex items-center justify-center text-center truncate whitespace-nowrap shadow-2xs active:scale-98"
                                  title="Chèn mã trích dẫn nội văn vào vị trí con trỏ (ví dụ [1] hoặc (Author, Year))"
                                >
                                  + Trích dẫn trong bài
                                </button>
                                <button
                                  type="button"
                                  onClick={() => p && handleInsertPaperReference(p, sp.citation_formatted)}
                                  className="h-8 px-2 rounded-md font-medium text-gray-700 bg-gray-50 hover:bg-gray-100 border border-gray-200 transition flex items-center justify-center text-center truncate whitespace-nowrap shadow-2xs active:scale-98"
                                  title="Chèn dòng thư mục đầy đủ vào bài viết"
                                >
                                  Dòng thư mục
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
        )}
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
              <div className="grid grid-cols-4 gap-2">
                <div className="bg-gray-50 p-2.5 rounded-lg border border-gray-200 text-center">
                  <div className="text-base font-bold text-gray-800">{citationResult.total_issues}</div>
                  <div className="text-[10px] text-gray-500">Tổng điểm lưu ý</div>
                </div>
                <div className="bg-amber-50 p-2.5 rounded-lg border border-amber-200 text-center">
                  <div className="text-base font-bold text-amber-700">{citationResult.missing_claims.length}</div>
                  <div className="text-[10px] text-amber-600">Câu thiếu nguồn</div>
                </div>
                <div className="bg-emerald-50 p-2.5 rounded-lg border border-emerald-200 text-center">
                  <div className="text-base font-bold text-emerald-700">{citationResult.verified_count}</div>
                  <div className="text-[10px] text-emerald-600">Trích dẫn đã khớp</div>
                </div>
                <div className="bg-blue-50 p-2.5 rounded-lg border border-blue-200 text-center">
                  <div className="text-base font-bold text-blue-700">{citationResult.uncited_papers?.length || 0}</div>
                  <div className="text-[10px] text-blue-600">Chưa dùng trong bài</div>
                </div>
              </div>

              {/* Nhóm 1: Câu thiếu dẫn nguồn */}
              {citationResult.missing_claims.length > 0 ? (
                <div className="space-y-2">
                  <div className="font-semibold text-gray-900 text-xs flex items-center gap-1.5">
                    <span className="text-amber-500">⚠️</span> Các câu khẳng định/số liệu thiếu dẫn chứng ({citationResult.missing_claims.length}):
                  </div>
                  <div className="space-y-2">
                    {citationResult.missing_claims.map((claim, idx) => (
                      <div key={idx} className="bg-amber-50/50 border border-amber-200 rounded-lg p-3 space-y-1.5">
                        <div className="text-gray-800 font-medium italic">
                          &quot;{claim.sentence}&quot;
                        </div>
                        <div className="text-amber-800 text-[11px]">
                          <strong>Lý do:</strong> {claim.reason}
                        </div>
                        <div className="text-gray-600 text-[11px]">
                          <strong>Gợi ý:</strong> {claim.suggested_action}
                        </div>

                        {/* Gợi ý bài báo phù hợp trong đề tài */}
                        {claim.recommended_paper_title ? (
                          <div className="bg-purple-50 border border-purple-200 rounded p-2 flex items-center justify-between gap-2 mt-1">
                            <div className="text-[11px] text-purple-900 truncate">
                              💡 <strong>Gợi ý từ đề tài:</strong> {claim.recommended_paper_title}
                            </div>
                            <div className="flex items-center gap-1.5 shrink-0">
                              {claim.in_text_suggestion ? (
                                <>
                                  <button
                                    type="button"
                                    onClick={() => handleInsertSnippetFromModal(claim.in_text_suggestion!)}
                                    className="bg-white border border-purple-300 hover:bg-purple-100 text-purple-700 px-2 py-0.5 rounded text-[10px] font-medium transition cursor-pointer"
                                    title="Chèn mã trích dẫn này vào văn bản tại vị trí con trỏ"
                                  >
                                    Chèn tại con trỏ
                                  </button>
                                  <button
                                    type="button"
                                    onClick={() => {
                                      const orig = claim.sentence;
                                      const code = claim.in_text_suggestion!;
                                      let replaced = orig;
                                      if (orig.endsWith(".")) {
                                        replaced = orig.slice(0, -1).trim() + " " + code + ".";
                                      } else {
                                        replaced = orig.trim() + " " + code;
                                      }
                                      handleAcceptCitationSuggestion({
                                        original_text: orig,
                                        suggested_text: replaced,
                                        reason: claim.reason,
                                      });
                                    }}
                                    className="bg-purple-600 hover:bg-purple-700 text-white px-2.5 py-0.5 rounded text-[10px] font-medium transition cursor-pointer"
                                    title="Tự động thay thế câu này trong Tiptap Editor với mã trích dẫn được gợi ý"
                                  >
                                    Chấp nhận gợi ý AI
                                  </button>
                                </>
                              ) : null}
                            </div>
                          </div>
                        ) : null}
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-3 text-emerald-800 text-center">
                  ✓ Không phát hiện câu khẳng định hoặc số liệu định lượng nào thiếu nguồn!
                </div>
              )}

              {/* Nhóm 2: Cảnh báo chuẩn định dạng trích dẫn */}
              {citationResult.citation_warnings && citationResult.citation_warnings.length > 0 ? (
                <div className="space-y-2">
                  <div className="font-semibold text-amber-700 text-xs flex items-center gap-1.5">
                    <span>⚡</span> Cảnh báo chuẩn trích dẫn ({citationResult.citation_warnings.length}):
                  </div>
                  <div className="space-y-1.5">
                    {citationResult.citation_warnings.map((warnText, idx) => (
                      <div key={idx} className="bg-amber-50/80 border border-amber-200 rounded p-2 text-amber-900 text-[11px]">
                        • {warnText}
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}

              {/* Nhóm 3: Lỗi sai lệch danh mục trích dẫn */}
              {citationResult.invalid_citations && citationResult.invalid_citations.length > 0 ? (
                <div className="space-y-2">
                  <div className="font-semibold text-red-700 text-xs flex items-center gap-1.5">
                    <span>❌</span> Sai lệch danh mục tài liệu tham khảo ({citationResult.invalid_citations.length}):
                  </div>
                  <div className="space-y-1.5">
                    {citationResult.invalid_citations.map((errText, idx) => (
                      <div key={idx} className="bg-red-50 border border-red-200 rounded p-2 text-red-700 text-[11px]">
                        • {errText}
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}

              {/* Gợi ý thay thế từ AI (nếu có) */}
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
                      ) : (
                        <p className="mt-2 text-amber-700">Chưa có tài liệu đã chọn để đề xuất nguồn.</p>
                      )}
                    </div>
                  ))}
                </div>
              ) : null}

              {/* Nhóm 4: Tài liệu đề tài chưa được trích dẫn */}
              {citationResult.uncited_papers && citationResult.uncited_papers.length > 0 ? (
                <div className="space-y-2">
                  <div className="font-semibold text-blue-700 text-xs flex items-center gap-1.5">
                    <span>📚</span> Tài liệu đề tài chưa được trích dẫn ({citationResult.uncited_papers.length}):
                  </div>
                  <div className="space-y-1.5 max-h-48 overflow-y-auto">
                    {citationResult.uncited_papers.map((paper, idx) => (
                      <div key={idx} className="bg-blue-50/60 border border-blue-200 rounded p-2 flex items-center justify-between gap-2 text-[11px]">
                        <div className="truncate pr-2">
                          <span className="font-semibold text-gray-900">{paper.title}</span>
                          <span className="text-gray-500 ml-1">({paper.year || "n.d."})</span>
                        </div>
                        {paper.in_text_code ? (
                          <button
                            type="button"
                            onClick={() => handleInsertSnippetFromModal(paper.in_text_code!)}
                            className="shrink-0 bg-blue-600 hover:bg-blue-700 text-white px-2 py-0.5 rounded text-[10px] font-medium transition cursor-pointer"
                            title="Chèn mã trích dẫn này vào văn bản tại vị trí con trỏ"
                          >
                            Chèn {paper.in_text_code}
                          </button>
                        ) : null}
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}

              {/* Danh mục tài liệu tham khảo theo chuẩn (FE 2 Component) */}
              {citationResult.bibliography && citationResult.bibliography.length > 0 ? (
                <div className="pt-2 border-t border-gray-200">
                  <BibliographyView
                    citations={citationResult.bibliography}
                    style={(project?.citation_style as any) || "apa7"}
                  />
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

      {/* Modal Nhập Tệp Tin Học Thuật (Yêu cầu 5) */}
      <ImportModal
        isOpen={isImportModalOpen}
        onClose={() => setIsImportModalOpen(false)}
        projectId={project?.id || ""}
        onImportOutline={handleImportOutline}
        onImportDocument={handleImportDocument}
      />
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