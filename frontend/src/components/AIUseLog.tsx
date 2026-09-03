import React from 'react';

export function AIUseLog() {
  const logs = [
    { id: 1, time: "03/09/2026 10:00", action: "Tóm tắt văn bản", credit: "-5", status: "Thành công" },
    { id: 2, time: "03/09/2026 09:15", action: "Hỏi AI giải thích", credit: "-2", status: "Thành công" },
    { id: 3, time: "02/09/2026 15:30", action: "Tìm kiếm tài liệu", credit: "-10", status: "Thành công" },
  ];

  return (
    <div className="p-6 bg-white rounded-lg shadow-sm border mt-6 w-full">
      <h2 className="text-lg font-bold mb-4">Lịch sử sử dụng AI (Báo cáo minh bạch)</h2>
      <div className="overflow-x-auto">
        <table className="w-full border-collapse">
          <thead>
            <tr className="bg-gray-100 text-left">
              <th className="p-3 border-b">Thời gian</th>
              <th className="p-3 border-b">Hành động</th>
              <th className="p-3 border-b">Credit đã dùng</th>
              <th className="p-3 border-b">Trạng thái</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((log) => (
              <tr key={log.id} className="border-b hover:bg-gray-50 transition">
                <td className="p-3 text-gray-600">{log.time}</td>
                <td className="p-3 font-medium">{log.action}</td>
                <td className="p-3 text-red-500 font-bold">{log.credit}</td>
                <td className="p-3 text-green-600">{log.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default AIUseLog;