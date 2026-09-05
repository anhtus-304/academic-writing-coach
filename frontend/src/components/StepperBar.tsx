import React from 'react';

export function StepperBar() {
  return (
    <div className="flex items-center justify-center gap-2 p-4 my-4 bg-white rounded-lg border shadow-sm">
      <div className="flex items-center text-blue-600 font-bold">
        <span className="w-8 h-8 flex items-center justify-center bg-blue-100 rounded-full mr-2">1</span>
        Dàn ý
      </div>
      <div className="w-12 h-[2px] bg-gray-300 mx-2"></div>
      <div className="flex items-center text-gray-500 font-medium">
        <span className="w-8 h-8 flex items-center justify-center bg-gray-100 rounded-full mr-2">2</span>
        Tài liệu
      </div>
      <div className="w-12 h-[2px] bg-gray-300 mx-2"></div>
      <div className="flex items-center text-gray-500 font-medium">
        <span className="w-8 h-8 flex items-center justify-center bg-gray-100 rounded-full mr-2">3</span>
        Viết & Trích dẫn
      </div>
    </div>
  );
}

export default StepperBar;