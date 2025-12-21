import { useRef, useState } from "react";
import { toBlob } from "html-to-image";
import { API_BASE, MODEL_DISPLAY_NAMES } from "@/utils/types";

interface CompareResult {
	status: string;
	stash1: {
		name: string;
		average_score: number;
		std_dev: number;
		scores: number[];
		file_count: number;
		category_averages: { [key: string]: number };
		filenames: string[];
	};
	stash2: {
		name: string;
		average_score: number;
		std_dev: number;
		scores: number[];
		file_count: number;
		category_averages: { [key: string]: number };
		filenames: string[];
	};
	all_categories: string[];
}

interface Props {
	isOpen: boolean;
	onClose: () => void;
	results: CompareResult | null;
}

export default function CompareModal({ isOpen, onClose, results }: Props) {
	const captureRef = useRef<HTMLDivElement>(null);
	const [copying, setCopying] = useState(false);
	const [copied, setCopied] = useState(false);

	if (!isOpen || !results) return null;

	const { stash1, stash2, all_categories } = results;

	const parseMetadata = (filenames: string[]) => {
		if (!filenames || filenames.length === 0) return null;

		const filename = filenames[0];
		const parts = filename.split("-");

		if (parts.length >= 3) {
			const timestampIdx = parts.length - 1;
			if (parts[timestampIdx].includes("_")) {
				const variant = parts[timestampIdx - 1];
				const model = parts.slice(0, timestampIdx - 1).join("-");

				const displayModel = MODEL_DISPLAY_NAMES[model] || model;
				const displayVariant = variant
					.replace(/_/g, " ")
					.replace(/\b\w/g, (l) => l.toUpperCase());

				return {
					model: displayModel,
					variant: displayVariant,
				};
			}
		}
		return null;
	};

	const metadata1 = parseMetadata(stash1.filenames);
	const metadata2 = parseMetadata(stash2.filenames);

	const scoreDiff = stash2.average_score - stash1.average_score;
	const percentDiff =
		stash1.average_score > 0 ? (scoreDiff / stash1.average_score) * 100 : 0;

	// Find categories with biggest differences
	const categoryDifferences = all_categories
		.map((cat) => {
			const score1 = stash1.category_averages[cat] || 0;
			const score2 = stash2.category_averages[cat] || 0;
			const diff = score2 - score1;
			return { category: cat, score1, score2, diff };
		})
		.sort((a, b) => Math.abs(b.diff) - Math.abs(a.diff));

	const topDifferences = categoryDifferences.slice(0, 5);

	const copyToClipboard = async () => {
		if (!captureRef.current || copying || copied) return;

		setCopying(true);
		setCopied(false);
		try {
			const blob = await toBlob(captureRef.current, {
				backgroundColor: "#1a1a1a",
				pixelRatio: 2,
			});

			if (blob) {
				try {
					await navigator.clipboard.write([
						new ClipboardItem({
							"image/png": blob,
						}),
					]);
					setCopied(true);
					setTimeout(() => setCopied(false), 2000);
				} catch (err) {
					console.error("Failed to copy to clipboard:", err);
				}
			}
		} catch (err) {
			console.error("Failed to capture image:", err);
		} finally {
			setCopying(false);
		}
	};

	const exportGraph = async (format: "svg" | "png") => {
		if (!stash1 || !stash2) return;
		try {
			const res = await fetch(`${API_BASE}/graph/compare?format=${format}`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ stash1: stash1.name, stash2: stash2.name }),
			});
			const blob = await res.blob();
			const link = document.createElement("a");
			link.href = URL.createObjectURL(blob);
			link.download = `compare-${stash1.name}-vs-${stash2.name}.${format}`;
			link.click();
			URL.revokeObjectURL(link.href);
		} catch (err) {
			console.error("Failed to export graph:", err);
		}
	};

	return (
		<div
			className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50 p-8"
			onClick={onClose}
		>
			<div
				className="bg-terminal-surface border-2 border-terminal-accent rounded-lg max-w-4xl w-full max-h-[90vh] overflow-y-auto"
				onClick={(e) => e.stopPropagation()}
			>
				<div className="sticky top-0 bg-terminal-surface border-b border-terminal-border p-6 flex justify-between items-center">
					<div>
						<h2 className="text-terminal-accent text-2xl font-bold m-0">
							Comparison Results
						</h2>
						<p className="text-gray-400 text-sm mt-1">
							{stash1.name} vs {stash2.name}
						</p>
					</div>
					<div className="flex gap-3 items-center">
						<div className="flex">
							<button
								onClick={() => exportGraph("svg")}
								className="px-2 py-1 border border-blue-500 text-blue-500 rounded-l hover:bg-blue-500 hover:text-white cursor-pointer transition-colors text-xs font-medium"
								title="Export as SVG"
							>
								SVG
							</button>
							<button
								onClick={() => exportGraph("png")}
								className="px-2 py-1 border border-blue-500 border-l-0 text-blue-500 rounded-r hover:bg-blue-500 hover:text-white cursor-pointer transition-colors text-xs font-medium"
								title="Export as PNG"
							>
								PNG
							</button>
						</div>
						<button
							onClick={copyToClipboard}
							className="p-2 border border-terminal-accent text-terminal-accent rounded hover:bg-terminal-accent hover:text-black cursor-pointer transition-colors relative overflow-hidden"
							title="Copy comparison as image"
						>
							<svg
								className={`h-5 w-5 ${
									copied
										? "opacity-0 scale-0"
										: "opacity-100 scale-100"
								}`}
								fill="none"
								stroke="currentColor"
								viewBox="0 0 24 24"
							>
								<path
									strokeLinecap="round"
									strokeLinejoin="round"
									strokeWidth={2}
									d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
								/>
							</svg>
							<svg
								className={`h-5 w-5 absolute inset-0 m-auto ${
									copied
										? "opacity-100 scale-100"
										: "opacity-0 scale-0"
								}`}
								fill="none"
								stroke="currentColor"
								viewBox="0 0 24 24"
							>
								<path
									strokeLinecap="round"
									strokeLinejoin="round"
									strokeWidth={2}
									d="M5 13l4 4L19 7"
								/>
							</svg>
						</button>
						<button
							onClick={onClose}
							className="w-9 h-9 flex items-center justify-center border border-gray-600 text-gray-400 rounded hover:border-white hover:text-white text-xl leading-none cursor-pointer transition-colors"
						>
							×
						</button>
					</div>
				</div>

				<div ref={captureRef} className="p-6">
					<div className="grid grid-cols-2 gap-6 mb-8">
						<div className="p-6 bg-zinc-900 border border-terminal-border rounded">
							<div className="mb-3">
								<div className="text-gray-400 text-sm mb-1">
									{stash1.name}
								</div>
								{metadata1 && (
									<div className="flex items-center gap-2 text-xs text-gray-400 flex-wrap">
										<span className="text-blue-400 font-semibold">
											{metadata1.model}
										</span>
										<span>-</span>
										<span className="text-purple-400 font-semibold">
											{metadata1.variant}
										</span>
										<span>-</span>
										<span className="text-terminal-accent font-semibold">
											x{stash1.file_count}
										</span>
									</div>
								)}
							</div>
							<div className="text-terminal-accent text-4xl font-bold">
								{stash1.average_score.toFixed(1)}%
							</div>
							{stash1.std_dev > 0 && (
								<div className="text-gray-500 text-sm mt-1">
									SD: {stash1.std_dev.toFixed(2)}
								</div>
							)}
						</div>

						<div className="p-6 bg-zinc-900 border border-terminal-border rounded">
							<div className="mb-3">
								<div className="text-gray-400 text-sm mb-1">
									{stash2.name}
								</div>
								{metadata2 && (
									<div className="flex items-center gap-2 text-xs text-gray-400 flex-wrap">
										<span className="text-blue-400 font-semibold">
											{metadata2.model}
										</span>
										<span>-</span>
										<span className="text-purple-400 font-semibold">
											{metadata2.variant}
										</span>
										<span>-</span>
										<span className="text-terminal-accent font-semibold">
											x{stash2.file_count}
										</span>
									</div>
								)}
							</div>
							<div className="text-terminal-accent text-4xl font-bold">
								{stash2.average_score.toFixed(1)}%
							</div>
							{stash2.std_dev > 0 && (
								<div className="text-gray-500 text-sm mt-1">
									SD: {stash2.std_dev.toFixed(2)}
								</div>
							)}
						</div>
					</div>

					<div className="mb-8 p-6 bg-linear-to-r from-zinc-800 to-zinc-900 border-2 border-terminal-accent rounded-lg">
						<h3 className="text-terminal-accent text-xl font-bold mb-4">
							Difference
						</h3>
						<div className="flex items-baseline gap-3">
							<div
								className={`text-4xl font-bold ${
									scoreDiff >= 0
										? "text-green-500"
										: "text-red-500"
								}`}
							>
								{scoreDiff >= 0 ? "+" : ""}
								{scoreDiff.toFixed(1)}%
							</div>
							<div className="text-gray-400 text-lg">
								({percentDiff >= 0 ? "+" : ""}
								{percentDiff.toFixed(1)}% change)
							</div>
						</div>
						<div className="mt-2 text-gray-400 text-sm">
							{scoreDiff >= 0
								? `${stash2.name} performs better than ${stash1.name}`
								: `${stash1.name} performs better than ${stash2.name}`}
						</div>
					</div>

					{topDifferences.length > 0 && (
						<div>
							<h4 className="text-terminal-accent text-lg font-bold mb-4">
								Top Category Differences
							</h4>
							<div className="space-y-3">
								{topDifferences.map((cat) => (
									<div
										key={cat.category}
										className="p-4 bg-zinc-900 border border-terminal-border rounded"
									>
										<div className="flex justify-between items-center mb-2">
											<span className="text-gray-300 font-medium">
												{cat.category}
											</span>
											<span
												className={`font-bold ${
													cat.diff >= 0
														? "text-green-500"
														: "text-red-500"
												}`}
											>
												{cat.diff >= 0 ? "+" : ""}
												{cat.diff.toFixed(1)}%
											</span>
										</div>
										<div className="grid grid-cols-2 gap-4 text-sm">
											<div>
												<div className="text-gray-500">
													{stash1.name}
												</div>
												<div className="text-gray-300 font-semibold">
													{cat.score1.toFixed(1)}%
												</div>
											</div>
											<div>
												<div className="text-gray-500">
													{stash2.name}
												</div>
												<div className="text-gray-300 font-semibold">
													{cat.score2.toFixed(1)}%
												</div>
											</div>
										</div>
									</div>
								))}
							</div>
						</div>
					)}
				</div>

				<div className="px-6 pb-6">
					<h4 className="text-terminal-accent text-lg font-bold mb-4">
						All Categories
					</h4>
					<div className="grid grid-cols-2 gap-3">
						{all_categories.map((cat) => {
							const score1 = stash1.category_averages[cat] || 0;
							const score2 = stash2.category_averages[cat] || 0;
							const diff = score2 - score1;
							return (
								<div
									key={cat}
									className="p-3 bg-zinc-900 border border-terminal-border rounded text-sm"
								>
									<div className="flex justify-between mb-1">
										<span className="text-gray-400">
											{cat}
										</span>
										<span
											className={`font-semibold ${
												diff >= 0
													? "text-green-500"
													: "text-red-500"
											}`}
										>
											{diff >= 0 ? "+" : ""}
											{diff.toFixed(1)}%
										</span>
									</div>
									<div className="flex gap-2 text-xs text-gray-500">
										<span>{score1.toFixed(1)}%</span>
										<span>→</span>
										<span>{score2.toFixed(1)}%</span>
									</div>
								</div>
							);
						})}
					</div>
				</div>
			</div>
		</div>
	);
}
