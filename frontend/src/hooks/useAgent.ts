"use client";

import { useCallback, useState } from "react";

import type { OutlineNode } from "@/components/outline/OutlineEditor";

export type OutlineAgentResult = OutlineNode[];

const normalizeOutlineNode = (node: unknown, fallbackId: string): OutlineNode => {
  if (!node || typeof node !== "object") {
    return {
      id: fallbackId,
      title: "New section",
      level: 1,
      children: [],
    };
  }

  const source = node as Record<string, unknown>;
  const children = Array.isArray(source.children)
    ? source.children.map((child, index) => normalizeOutlineNode(child, `${fallbackId}.${index + 1}`))
    : [];

  return {
    id: typeof source.id === "string" ? source.id : fallbackId,
    title: typeof source.title === "string" && source.title.trim() ? source.title : "New section",
    level: typeof source.level === "number" ? source.level : Math.max(1, 1 + (children.length > 0 ? 1 : 0)),
    children,
  };
};

export function isValidOutline(data: unknown): data is OutlineNode[] {
  if (!Array.isArray(data)) {
    return false;
  }

  return data.every((item) => {
    if (!item || typeof item !== "object") {
      return false;
    }

    const record = item as Record<string, unknown>;
    if (typeof record.title !== "string" || !record.title.trim()) {
      return false;
    }

    if (record.children !== undefined && !Array.isArray(record.children)) {
      return false;
    }

    return Array.isArray(record.children) ? isValidOutline(record.children) : true;
  });
}

export function useAgent() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<OutlineNode[] | null>(null);

  const generateOutline = useCallback(async (request: string): Promise<OutlineNode[] | null> => {
    setIsLoading(true);
    setError(null);

    try {
      const cleanedRequest = request.trim();
      if (!cleanedRequest) {
        throw new Error("Vui lòng nhập yêu cầu để tạo outline.");
      }

      const configuredUrl = process.env.NEXT_PUBLIC_OUTLINE_API_URL;
      if (!configuredUrl) {
        throw new Error(
          "Outline API contract is not configured yet. BE1/Agent1 must provide the real backend endpoint and response schema."
        );
      }

      const payload = {
        prompt: cleanedRequest,
        model: "openrouter/auto",
      };

      const response = await fetch(configuredUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error("Không thể tạo outline từ AI agent. API chưa sẵn sàng hoặc trả về lỗi.");
      }

      const data = (await response.json()) as unknown;
      const candidate = data && typeof data === "object" && "outline" in data ? (data as Record<string, unknown>).outline : data;
      const outlineCandidate = Array.isArray(candidate)
        ? candidate
        : candidate && typeof candidate === "object" && "children" in candidate
          ? [candidate as Record<string, unknown>]
          : null;

      if (!outlineCandidate || !isValidOutline(outlineCandidate)) {
        throw new Error("API trả về schema outline không hợp lệ. Cần contract từ BE1/Agent1.");
      }

      const normalizedResult = outlineCandidate.map((node, index) => normalizeOutlineNode(node, `node-${index + 1}`));
      setResult(normalizedResult);
      return normalizedResult;
    } catch (err) {
      const message = err instanceof Error ? err.message : "Đã xảy ra lỗi khi tạo outline.";
      setError(message);
      setResult(null);
      return null;
    } finally {
      setIsLoading(false);
    }
  }, []);

  return {
    isLoading,
    error,
    result,
    generateOutline,
  };
}
