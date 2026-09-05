'use client';
import React, { useState } from 'react';

export function CreditBalance() {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="relative">
      <button 
        onClick={() => setIsOpen(true)}
        className="bg-yellow-100 border border-yellow-300 text-yellow-700 px-4 py-2 rounded-full font-bold hover:bg-yellow-200 transition"
      >
        💎 Số dư: 150 Credits
      </button>

      {isOpen && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-xl shadow-lg w-[400px]">
            <h2 className="text-xl font-bold mb-4 text-center">Nạp thêm Credit</h2>
            <p className="text-gray-500 text-sm mb-4 text-center">(Giao diện Mockup)</p>
            
            <div className="flex flex-col gap-3">
              <button className="border-2 border-gray-200 text-gray-700 p-3 rounded-lg hover:border-blue-500 hover:text-blue-600 transition">
                Gói Cơ bản: 50.000đ = 100 Credits
              </button>
              <button className="bg-blue-600 text-white p-3 rounded-lg hover:bg-blue-700 transition font-bold">
                Gói Pro: 100.000đ = 250 Credits (Khuyên dùng)
              </button>
            </div>

            <button 
              onClick={() => setIsOpen(false)}
              className="mt-6 w-full text-gray-500 hover:text-gray-800 underline"
            >
              Đóng lại
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default CreditBalance;