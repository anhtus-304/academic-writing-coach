'use client';
import React, { useState, useEffect } from 'react';
import dynamic from 'next/dynamic';

// @ts-ignore
const Joyride = dynamic(() => import('react-joyride'), { ssr: false }) as any;

export default function TourGuide() {
  const [isMounted, setIsMounted] = useState(false);
  const [runTour, setRunTour] = useState(false);

  useEffect(() => {
    setIsMounted(true);
    
    // Bắt hệ thống chờ đúng 1 giây (1000ms) để tải xong HTML rồi mới bật Tour
    const timer = setTimeout(() => {
      setRunTour(true);
    }, 1000);
    
    // Dọn dẹp bộ đếm khi tắt
    return () => clearTimeout(timer);
  }, []);

  const steps: any = [
    {
      target: '.tour-step-1',
      content: 'Chào mừng bạn! Đây là thanh tiến trình 3 bước để hoàn thành luận văn.',
      disableBeacon: true,
    },
    {
      target: '.tour-step-2',
      content: 'Khung soạn thảo thông minh tích hợp AI đa tác nhân.',
    },
    {
      target: '.tour-step-3',
      content: 'Bấm vào đây để nạp thêm Credit khi cần nhé!',
    }
  ];

  if (!isMounted) return null;

  return (
    <Joyride
      steps={steps}
      run={runTour}
      continuous={true}
      showSkipButton={true}
      styles={{
        options: {
          primaryColor: '#9333ea', 
          zIndex: 10000, // Tăng mức độ ưu tiên hiển thị lên cao nhất để không bị Navbar đè lên
        }
      }}
      locale={{
        last: 'Hoàn thành',
        next: 'Tiếp theo',
        skip: 'Bỏ qua',
        back: 'Quay lại'
      }}
    />
  );
}