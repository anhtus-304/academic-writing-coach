"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { authApi, setAuthToken } from "@/lib/api";

export default function SignInPage() {
  const router = useRouter();
  const [email, setEmail] = useState("thuyvi@student.edu.vn");
  const [name, setName] = useState("Thúy Vi");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleGoogleLogin = () => {
    window.location.href = authApi.getGoogleLoginUrl();
  };

  const handleDevLogin = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await authApi.devLogin(email, name);
      setAuthToken(res.access_token);
      router.push("/dashboard");
    } catch (err: any) {
      setError(err.message || "Đăng nhập thất bại. Hãy kiểm tra Backend server đang chạy.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-gray-50 min-h-screen flex items-center justify-center p-4">
      <div className="bg-white w-full max-w-md rounded-2xl shadow-lg border border-gray-100 p-8">
        {/* Logo */}
        <div className="flex justify-center mb-6">
          <Link href="/">
            <div className="w-12 h-12 bg-purple-100 rounded-xl flex items-center justify-center cursor-pointer hover:bg-purple-200 transition">
              <svg className="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
                ></path>
              </svg>
            </div>
          </Link>
        </div>

        <h1 className="text-2xl font-bold text-center text-gray-900 mb-2">Chào mừng trở lại</h1>
        <p className="text-sm text-gray-500 text-center mb-6">
          Đăng nhập vào AI Academic Writing Coach để tiếp tục hoàn thiện luận văn của bạn.
        </p>

        {error && (
          <div className="mb-6 p-3 bg-red-50 border border-red-200 text-red-700 text-xs rounded-lg">
            {error}
          </div>
        )}

        {/* Google OAuth Button */}
        <button
          type="button"
          onClick={handleGoogleLogin}
          className="w-full flex items-center justify-center space-x-2 border border-gray-300 rounded-lg py-2.5 px-4 hover:bg-gray-50 transition mb-4 shadow-sm"
        >
          <svg className="w-5 h-5" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
            <path
              d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
              fill="#4285F4"
            />
            <path
              d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
              fill="#34A853"
            />
            <path
              d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
              fill="#FBBC05"
            />
            <path
              d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
              fill="#EA4335"
            />
          </svg>
          <span className="text-sm font-medium text-gray-700">Đăng nhập bằng Google</span>
        </button>

        {/* Dev Quick Login Button */}
        <button
          type="button"
          onClick={() => handleDevLogin()}
          disabled={loading}
          className="w-full flex items-center justify-center space-x-2 bg-purple-50 hover:bg-purple-100 text-purple-700 border border-purple-200 rounded-lg py-2.5 px-4 transition mb-6 text-sm font-medium"
        >
          <span>⚡</span>
          <span>{loading ? "Đang đăng nhập..." : "Đăng nhập nhanh (Chế độ Thử nghiệm)"}</span>
        </button>

        <div className="relative flex items-center py-2 mb-6">
          <div className="flex-grow border-t border-gray-200"></div>
          <span className="flex-shrink-0 mx-4 text-gray-400 text-xs uppercase">Hoặc Email</span>
          <div className="flex-grow border-t border-gray-200"></div>
        </div>

        {/* Form đăng nhập */}
        <form className="space-y-4" onSubmit={handleDevLogin}>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Tên hiển thị</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm outline-none focus:border-purple-500 focus:ring-1 focus:ring-purple-500 text-gray-900"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Email sinh viên / nghiên cứu</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm outline-none focus:border-purple-500 focus:ring-1 focus:ring-purple-500 text-gray-900"
              required
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-purple-600 text-white rounded-lg py-2.5 text-sm font-medium hover:bg-purple-700 transition block text-center shadow-sm"
          >
            {loading ? "Đang xử lý..." : "Vào trang quản lý"}
          </button>
        </form>

        <p className="text-center text-sm text-gray-600 mt-6">
          Chưa có tài khoản?{" "}
          <Link href="/auth/signup" className="text-purple-600 font-medium hover:underline">
            Đăng ký ngay
          </Link>
        </p>
      </div>
    </div>
  );
}