"use client";

import React, { useState } from "react";
import {
  Sparkles,
  User,
  Copy,
  Check,
  Zap,
  Clock,
  Terminal,
  ArrowDownToLine,
  Replace,
} from "lucide-react";
import { cn } from "@/lib/utils";

export interface ChatMessageProps {
  id?: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp?: string;
  tokensUsed?: number;
  creditsCharged?: number;
  actionType?: string;
  className?: string;
  onInsertAtCursor?: (content: string) => void;
  onReplaceSelection?: (content: string) => void;
}

export function ChatMessage({
  role,
  content,
  timestamp,
  tokensUsed,
  creditsCharged,
  actionType,
  className,
  onInsertAtCursor,
  onReplaceSelection,
}: ChatMessageProps) {
  const [copied, setCopied] = useState(false);
  const [inserted, setInserted] = useState(false);
  const [replaced, setReplaced] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleInsert = () => {
    if (onInsertAtCursor) {
      onInsertAtCursor(content);
      setInserted(true);
      setTimeout(() => setInserted(false), 2000);
    }
  };

  const handleReplace = () => {
    if (onReplaceSelection) {
      onReplaceSelection(content);
      setReplaced(true);
      setTimeout(() => setReplaced(false), 2000);
    }
  };

  const isUser = role === "user";
  const isSystem = role === "system";

  return (
    <div
      className={cn(
        "flex gap-2.5 text-xs transition-opacity duration-150",
        isUser ? "flex-row-reverse" : "flex-row",
        className
      )}
    >
      {/* Avatar */}
      <div
        className={cn(
          "flex h-7 w-7 shrink-0 items-center justify-center rounded-xl text-white shadow-2xs",
          isUser
            ? "bg-purple-600"
            : isSystem
            ? "bg-gray-700"
            : "bg-linear-to-br from-indigo-500 to-purple-600"
        )}
      >
        {isUser ? (
          <User className="h-3.5 w-3.5" />
        ) : isSystem ? (
          <Terminal className="h-3.5 w-3.5" />
        ) : (
          <Sparkles className="h-3.5 w-3.5" />
        )}
      </div>

      {/* Bubble container */}
      <div
        className={cn(
          "max-w-[85%] rounded-2xl p-3 shadow-2xs space-y-1.5",
          isUser
            ? "bg-purple-600 text-white rounded-tr-none"
            : isSystem
            ? "bg-gray-100 text-gray-800 rounded-tl-none border border-gray-200"
            : "bg-card text-foreground rounded-tl-none border border-border"
        )}
      >
        {/* Header meta */}
        <div
          className={cn(
            "flex items-center justify-between gap-3 text-[10px]",
            isUser ? "text-purple-200" : "text-muted-foreground"
          )}
        >
          <span className="font-semibold">
            {isUser ? "Bạn" : isSystem ? "Hệ thống" : "AI Coach"}
            {actionType ? ` • ${actionType}` : ""}
          </span>

          <div className="flex items-center gap-1.5">
            {creditsCharged !== undefined && creditsCharged > 0 && (
              <span className="inline-flex items-center gap-0.5 font-medium">
                <Zap className="h-2.5 w-2.5 fill-current" />
                {creditsCharged} cr
              </span>
            )}
            {timestamp && <span>{timestamp}</span>}
          </div>
        </div>

        {/* Message body */}
        <div
          className={cn(
            "whitespace-pre-wrap leading-relaxed text-[11.5px] font-sans break-words",
            isUser ? "text-white" : "text-gray-900"
          )}
        >
          {content}
        </div>

        {/* Footer actions */}
        {!isUser && (
          <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-gray-100 mt-1">
            <div className="text-[10px] text-muted-foreground">
              {tokensUsed ? `${tokensUsed} tokens` : ""}
            </div>
            
            <div className="flex items-center gap-2">
              {onInsertAtCursor && (
                <button
                  type="button"
                  onClick={handleInsert}
                  className="text-[10.5px] text-purple-600 hover:text-purple-800 bg-purple-50 hover:bg-purple-100 px-2 py-0.5 rounded-md font-medium flex items-center gap-1 transition"
                  title="Chèn nội dung này vào vị trí con trỏ trong bài viết"
                >
                  {inserted ? (
                    <>
                      <Check className="h-3 w-3 text-emerald-600" />
                      <span className="text-emerald-600">Đã chèn</span>
                    </>
                  ) : (
                    <>
                      <ArrowDownToLine className="h-3 w-3" />
                      <span>Chèn vào bài</span>
                    </>
                  )}
                </button>
              )}

              {onReplaceSelection && (
                <button
                  type="button"
                  onClick={handleReplace}
                  className="text-[10.5px] text-blue-600 hover:text-blue-800 bg-blue-50 hover:bg-blue-100 px-2 py-0.5 rounded-md font-medium flex items-center gap-1 transition"
                  title="Thay thế đoạn văn bản đang bôi đen bằng nội dung này"
                >
                  {replaced ? (
                    <>
                      <Check className="h-3 w-3 text-emerald-600" />
                      <span className="text-emerald-600">Đã thay</span>
                    </>
                  ) : (
                    <>
                      <Replace className="h-3 w-3" />
                      <span>Thay thế</span>
                    </>
                  )}
                </button>
              )}

              <button
                type="button"
                onClick={handleCopy}
                className="text-[10.5px] text-muted-foreground hover:text-foreground flex items-center gap-1 transition px-1 py-0.5"
                title="Sao chép câu trả lời"
              >
                {copied ? (
                  <>
                    <Check className="h-3 w-3 text-emerald-600" />
                    <span className="text-emerald-600">Đã chép</span>
                  </>
                ) : (
                  <>
                    <Copy className="h-3 w-3" />
                    <span>Sao chép</span>
                  </>
                )}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default ChatMessage;
