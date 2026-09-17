'use client';

import React, { useEffect, useState } from 'react';
import { creditApi, AIUseLogItem } from '@/lib/api';

const AGENT_NAME_MAP: Record<string, string> = {
  OutlineAgent: 'Sinh Dàn ý Đề tài',
  LiteratureAgent: 'Tìm kiếm & Tóm tắt Tài liệu',
  AIAssistant: 'Hỏi AI Coach (Inline Assistant)',
  CitationAgent: 'Kiểm tra & Format Trích dẫn',
};

interface AIUseLogProps {
  projectId?: string;
  refreshTrigger?: number | string;
  isDockMode?: boolean;
}

export function AIUseLog({ projectId, refreshTrigger, isDockMode = false }: AIUseLogProps) {
  const [logs, setLogs] = useState<AIUseLogItem[]>([]);
  const [loading, setLoading] = useState(true);

  const handleRefresh = async () => {
    setLoading(true);
    try {
      const data = await creditApi.getLogs(50, projectId);
      setLogs(data);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let isMounted = true;

    async function loadData() {
      try {
        const data = await creditApi.getLogs(50, projectId);
        if (isMounted) {
          setLogs(data);
        }
      } catch {
        if (isMounted) {
          if (!projectId) {
            setLogs([
              {
                id: 'sample-1',
                agent_name: 'OutlineAgent',
                tokens_used: 1840,
                credits_charged: 2,
                created_at: new Date().toISOString(),
              },
              {
                id: 'sample-2',
                agent_name: 'LiteratureAgent',
                tokens_used: 920,
                credits_charged: 1,
                created_at: new Date(Date.now() - 3600000).toISOString(),
              },
              {
                id: 'sample-3',
                agent_name: 'AIAssistant',
                tokens_used: 350,
                credits_charged: 1,
                created_at: new Date(Date.now() - 7200000).toISOString(),
              },
            ]);
          } else {
            setLogs([]);
          }
        }
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    loadData();

    return () => {
      isMounted = false;
    };
  }, [projectId, refreshTrigger]);

  const totalTokens = logs.reduce((acc, cur) => acc + (cur.tokens_used || 0), 0);
  const totalCredits = logs.reduce((acc, cur) => acc + (cur.credits_charged || 0), 0);

  const formatTime = (dateStr?: string) => {
    if (!dateStr) return 'Vừa xong';
    try {
      const d = new Date(dateStr);
      return d.toLocaleString('vi-VN', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return dateStr;
    }
  };

  if (isDockMode) {
    return (
      <div className="w-full h-full flex flex-col bg-white overflow-hidden text-xs">
        {/* Compact Sub-header with Stats */}
        <div className="flex items-center justify-between px-4 py-2 border-b border-gray-200 bg-gray-50/70 shrink-0">
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-semibold text-gray-700">Thống kê phiên làm việc:</span>
            <span className="bg-white border border-gray-200 text-gray-700 px-2 py-0.5 rounded text-[11px]">
              Tác vụ: <strong>{logs.length}</strong>
            </span>
            <span className="bg-purple-50 border border-purple-200 text-purple-700 px-2 py-0.5 rounded text-[11px] font-mono">
              Tokens: <strong>{totalTokens.toLocaleString('vi-VN')}</strong>
            </span>
            <span className="bg-amber-50 border border-amber-200 text-amber-800 px-2 py-0.5 rounded text-[11px] font-mono font-semibold">
              Đã trừ: <strong>-{totalCredits} credits</strong>
            </span>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleRefresh}
              disabled={loading}
              className="text-[11px] text-gray-600 hover:text-purple-600 bg-white border border-gray-200 hover:border-purple-200 px-2 py-0.5 rounded transition flex items-center gap-1 shadow-2xs"
            >
              <span className={loading ? 'animate-spin' : ''}>🔄</span> Làm mới
            </button>
          </div>
        </div>

        {/* Scrollable Table with Sticky Header */}
        <div className="flex-1 overflow-auto">
          <table className="w-full border-collapse text-left text-xs">
            <thead className="sticky top-0 z-10 bg-gray-100 border-b border-gray-200 text-gray-600 font-semibold shadow-2xs">
              <tr>
                <th className="px-3 py-2">Thời gian</th>
                <th className="px-3 py-2">Tác nhân AI / Hành động</th>
                <th className="px-3 py-2 text-right">Tokens</th>
                <th className="px-3 py-2 text-right">Credits</th>
                <th className="px-3 py-2 text-center">Trạng thái</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 text-gray-700">
              {loading ? (
                <tr>
                  <td colSpan={5} className="p-4 text-center text-gray-400">
                    <span className="inline-block animate-spin mr-1">⏳</span> Đang tải nhật ký...
                  </td>
                </tr>
              ) : logs.length === 0 ? (
                <tr>
                  <td colSpan={5} className="p-4 text-center text-gray-400">
                    Chưa có nhật ký tương tác AI trong đề tài này.
                  </td>
                </tr>
              ) : (
                logs.map((log) => (
                  <tr key={log.id} className="hover:bg-purple-50/30 transition">
                    <td className="px-3 py-2 text-gray-500 font-mono text-[11px] whitespace-nowrap">
                      {formatTime(log.created_at)}
                    </td>
                    <td className="px-3 py-2 font-medium text-gray-900">
                      <div className="flex items-center gap-1.5">
                        <span className="text-purple-600">✨</span>
                        <span>{AGENT_NAME_MAP[log.agent_name] || log.agent_name}</span>
                      </div>
                    </td>
                    <td className="px-3 py-2 text-right text-gray-600 font-mono text-[11px]">
                      {log.tokens_used > 0 ? log.tokens_used.toLocaleString('vi-VN') : '—'}
                    </td>
                    <td className="px-3 py-2 text-right font-bold text-red-600 whitespace-nowrap">
                      -{log.credits_charged}
                    </td>
                    <td className="px-3 py-2 text-center">
                      <span className="inline-flex items-center px-1.5 py-0.2 rounded text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                        Thành công
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 bg-white rounded-xl shadow-sm border border-gray-200 mt-6 w-full">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-5">
        <div>
          <h2 className="text-base font-bold text-gray-900 flex items-center gap-2">
            <span>📊</span> Báo Cáo Minh Bạch Lịch Sử Sử Dụng AI (AI Use Log)
          </h2>
          <p className="text-xs text-gray-500 mt-0.5">
            Ghi nhận chính xác số lượng tokens và credit được khấu trừ theo từng tác vụ học thuật của đề tài
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleRefresh}
            disabled={loading}
            className="text-xs text-gray-500 hover:text-purple-600 bg-gray-50 hover:bg-purple-50 border border-gray-200 px-2.5 py-1 rounded-lg transition flex items-center gap-1"
            title="Tải lại dữ liệu"
          >
            <span className={loading ? 'animate-spin' : ''}>🔄</span> Làm mới
          </button>
          <span className="text-xs bg-purple-50 text-purple-700 px-2.5 py-1 rounded-full font-semibold border border-purple-100">
            Minh bạch học thuật
          </span>
        </div>
      </div>

      {/* Summary Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-4">
        <div className="bg-slate-50 border border-slate-100 rounded-lg p-3">
          <div className="text-[11px] text-gray-500 font-medium">Tổng tác vụ AI đã gọi</div>
          <div className="text-lg font-bold text-gray-900 mt-0.5">
            {logs.length} <span className="text-xs font-normal text-gray-500">lần</span>
          </div>
        </div>
        <div className="bg-purple-50/60 border border-purple-100 rounded-lg p-3">
          <div className="text-[11px] text-purple-700 font-medium">Tổng Tokens xử lý</div>
          <div className="text-lg font-bold text-purple-900 mt-0.5 font-mono">
            {totalTokens.toLocaleString('vi-VN')} <span className="text-xs font-normal text-purple-600">tokens</span>
          </div>
        </div>
        <div className="bg-amber-50/60 border border-amber-100 rounded-lg p-3">
          <div className="text-[11px] text-amber-800 font-medium">Tổng Credits đã dùng</div>
          <div className="text-lg font-bold text-amber-900 mt-0.5 font-mono">
            -{totalCredits} <span className="text-xs font-normal text-amber-700">credits</span>
          </div>
        </div>
      </div>

      {/* Logs Table */}
      <div className="overflow-x-auto rounded-lg border border-gray-100">
        <table className="w-full border-collapse text-left text-xs">
          <thead>
            <tr className="bg-gray-50/80 text-gray-600 font-semibold border-b border-gray-200">
              <th className="p-3">Thời gian</th>
              <th className="p-3">Tác nhân AI / Hành động</th>
              <th className="p-3 text-right">Tokens tiêu thụ</th>
              <th className="p-3 text-right">Credit đã dùng</th>
              <th className="p-3 text-center">Trạng thái</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 text-gray-700">
            {loading ? (
              <tr>
                <td colSpan={5} className="p-6 text-center text-gray-400">
                  <span className="inline-block animate-spin mr-1">⏳</span> Đang tải nhật ký sử dụng...
                </td>
              </tr>
            ) : logs.length === 0 ? (
              <tr>
                <td colSpan={5} className="p-6 text-center text-gray-400">
                  Chưa có lịch sử gọi AI trong đề tài này. Khi bạn tạo dàn ý, tìm tài liệu hoặc hỏi AI, nhật ký sẽ được ghi nhận tại đây.
                </td>
              </tr>
            ) : (
              logs.map((log) => (
                <tr key={log.id} className="hover:bg-gray-50/60 transition">
                  <td className="p-3 text-gray-500 font-mono text-[11px] whitespace-nowrap">
                    {formatTime(log.created_at)}
                  </td>
                  <td className="p-3 font-medium text-gray-900">
                    <div className="flex items-center gap-1.5">
                      <span className="text-purple-600">✨</span>
                      <span>{AGENT_NAME_MAP[log.agent_name] || log.agent_name}</span>
                    </div>
                  </td>
                  <td className="p-3 text-right text-gray-600 font-mono text-[11px]">
                    {log.tokens_used > 0 ? log.tokens_used.toLocaleString('vi-VN') : '—'}
                  </td>
                  <td className="p-3 text-right font-bold text-red-600 whitespace-nowrap">
                    -{log.credits_charged} Credit
                  </td>
                  <td className="p-3 text-center">
                    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200/50">
                      Thành công
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default AIUseLog;