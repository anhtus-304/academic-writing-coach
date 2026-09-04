import { Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";

type AIBubbleMenuProps = {
	onAskAI: () => void;
};

export function AIBubbleMenu({ onAskAI }: AIBubbleMenuProps) {
	return (
		<Button
			type="button"
			variant="ghost"
			size="sm"
			className="h-8 gap-1.5 px-2"
			onClick={onAskAI}
			aria-label="Hỏi AI về đoạn văn bản đã chọn"
		>
			<Sparkles className="h-4 w-4" />
			Hỏi AI
		</Button>
	);
}
