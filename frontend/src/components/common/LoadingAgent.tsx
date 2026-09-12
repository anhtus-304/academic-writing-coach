'use client';
import React from 'react';
import { motion } from 'framer-motion';

export default function LoadingAgent({ text = "AI đang suy nghĩ..." }: { text?: string }) {
  return (
    <div className="flex flex-col items-center justify-center p-6 space-y-4 bg-purple-50/50 rounded-xl border border-purple-100 my-4">
      <div className="flex space-x-2">
        {[0, 1, 2].map((index) => (
          <motion.div
            key={index}
            className="w-3 h-3 bg-purple-500 rounded-full"
            animate={{ y: ["0%", "-50%", "0%"] }}
            transition={{
              duration: 0.6,
              repeat: Infinity,
              ease: "easeInOut",
              delay: index * 0.15,
            }}
          />
        ))}
      </div>
      <p className="text-sm font-medium text-purple-700 animate-pulse">{text}</p>
    </div>
  );
}