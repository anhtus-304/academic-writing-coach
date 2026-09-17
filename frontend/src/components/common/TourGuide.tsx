'use client';
import React, { useState, useEffect } from 'react';
import dynamic from 'next/dynamic';
import type { Step } from 'react-joyride';

// @ts-expect-error react-joyride type dynamic import
const Joyride = dynamic(() => import('react-joyride'), { ssr: false });

export default function TourGuide() {
  const [isMounted, setIsMounted] = useState(false);
  const [runTour, setRunTour] = useState(false);

  useEffect(() => {
    const frame = requestAnimationFrame(() => {
      setIsMounted(true);
    });

    const timer = setTimeout(() => {
      setRunTour(true);
    }, 1000);

    return () => {
      cancelAnimationFrame(frame);
      clearTimeout(timer);
    };
  }, []);

  const steps: Step[] = [
    {
      target: '.tour-step-1',
      content: 'Chào mừng bạn! Đây là thanh tiến trình 3 bước để hoàn thành luận văn.',
      disableBeacon: true,
    },
    {
      target: '.tour-step-2',
      content: 'Khung soạn thảo thông minh tích hợp AI đa tác nhân.',
    },
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
          zIndex: 10000,
        },
      }}
      locale={{
        last: 'Hoàn thành',
        next: 'Tiếp theo',
        skip: 'Bỏ qua',
        back: 'Quay lại',
      }}
    />
  );
}