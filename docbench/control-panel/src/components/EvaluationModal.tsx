import { useRef, useState } from "react";
import { toBlob } from "html-to-image";
import { API_BASE, MODEL_DISPLAY_NAMES } from "@/utils/types";

interface EvaluationResult {
	status: string;
	directory: string;
	files_evaluated: number;
	stashName?: string;
	results: {
		[filename: string]: {
			error?: string;
			summary?: {
				overall_percentage: number;
				total_score: number;
				total_max: number;
				tests_completed: number;
				category_breakdown?: {
					[category: string]: {
						percentage: number;
						score: number;
						max: number;
						count: number;
					};
				};
			};
		};
	};
}

interface Props {
	isOpen: boolean;
	onClose: () => void;
	results: EvaluationResult | null;
}

export default function EvaluationModal({ isOpen, onClose, results }: Props) {
	const captureRef = useRef<HTMLDivElement>(null);
	const fileRefsRef = useRef<Map<string, HTMLDivElement>>(new Map());
	const [copying, setCopying] = useState(false);
	const [copied, setCopied] = useState(false);
	const [copiedFiles, setCopiedFiles] = useState<Set<string>>(new Set());

	if (!isOpen || !results) return null;

	const fileResults = Object.entries(results.results || {}).filter(
		([_, result]: [string, any]) => result.summary && !result.error
	);

	// Parse metadata from filenames (format: model-variant-timestamp)
	// Example: claude-sonnet-mini_v3-20251116_230045
	const fileMetadata = Object.keys(results.results || {})
		.map((filename) => {
			const parts = filename.split("-");

			if (parts.length >= 3) {
				// Find timestamp (last part with underscore)
				const timestampIdx = parts.length - 1;
				if (parts[timestampIdx].includes("_")) {
					const variant = parts[timestampIdx - 1];
					const model = parts.slice(0, timestampIdx - 1).join("-");
					return { variant, model };
				}
			}
			return null;
		})
		.filter(Boolean);

	// Check if all files have the same metadata
	const allSameMetadata =
		fileMetadata.length > 0 &&
		fileMetadata.every(
			(m) =>
				m?.variant === fileMetadata[0]?.variant &&
				m?.model === fileMetadata[0]?.model
		);

	const commonMetadata =
		allSameMetadata && fileMetadata.length > 0 ? fileMetadata[0] : null;

	const getDisplayModel = (model: string) =>
		MODEL_DISPLAY_NAMES[model] || model;
	const getDisplayVariant = (variant: string) => {
		// Convert mini_v3 -> Mini v3, core_v2 -> Core v2
		return variant
			.replace(/_/g, " ")
			.replace(/\b\w/g, (l) => l.toUpperCase());
	};

	const percentages = fileResults.map(([_, result]: [string, any]) =>
		result.summary.overall_percentage
	);

	const totalStats = fileResults.reduce(
		(acc, [_, result]: [string, any]) => {
			const summary = result.summary;
			return {
				totalScore: acc.totalScore + summary.total_score,
				totalMax: acc.totalMax + summary.total_max,
				totalTests: acc.totalTests + summary.tests_completed,
				count: acc.count + 1,
			};
		},
		{ totalScore: 0, totalMax: 0, totalTests: 0, count: 0 }
	);

	const averagePercentage =
		totalStats.totalMax > 0
			? (totalStats.totalScore / totalStats.totalMax) * 100
			: 0;

	const coeffOfVariation = (() => {
		if (percentages.length < 2) return 0;
		const mean = percentages.reduce((a, b) => a + b, 0) / percentages.length;
		const squaredDiffs = percentages.map((p) => Math.pow(p - mean, 2));
		const variance =
			squaredDiffs.reduce((a, b) => a + b, 0) / percentages.length;
		const stdDev = Math.sqrt(variance);
		return (stdDev / mean) * 100;
	})();

	// Aggregate category statistics across all files
	const categoryStats = fileResults.reduce(
		(acc: any, [_, result]: [string, any]) => {
			const breakdown = result.summary?.category_breakdown || {};
			Object.entries(breakdown).forEach(
				([category, data]: [string, any]) => {
					if (!acc[category]) {
						acc[category] = { score: 0, max: 0, count: 0 };
					}
					acc[category].score += data.score;
					acc[category].max += data.max;
					acc[category].count += data.count;
				}
			);
			return acc;
		},
		{}
	);

	// Calculate percentages and sort to find worst categories
	const categoryPercentages = Object.entries(categoryStats)
		.map(([category, data]: [string, any]) => ({
			category,
			percentage: data.max > 0 ? (data.score / data.max) * 100 : 0,
			score: data.score,
			max: data.max,
			count: data.count,
		}))
		.sort((a, b) => a.percentage - b.percentage);

	const worstCategories = categoryPercentages.slice(0, 5);

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
		if (!results?.stashName) return;
		try {
			const res = await fetch(`${API_BASE}/graph/evaluation?format=${format}`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ collection: results.stashName }),
			});
			const blob = await res.blob();
			const link = document.createElement("a");
			link.href = URL.createObjectURL(blob);
			link.download = `${results.stashName}-evaluation.${format}`;
			link.click();
			URL.revokeObjectURL(link.href);
		} catch (err) {
			console.error("Failed to export graph:", err);
		}
	};

	const copyFileResult = async (filename: string) => {
		const element = fileRefsRef.current.get(filename);
		if (!element || copiedFiles.has(filename)) return;

		try {
			const blob = await toBlob(element, {
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
					setCopiedFiles(new Set([...copiedFiles, filename]));
					setTimeout(() => {
						setCopiedFiles((prev) => {
							const next = new Set(prev);
							next.delete(filename);
							return next;
						});
					}, 2000);
				} catch (err) {
					console.error("Failed to copy to clipboard:", err);
				}
			}
		} catch (err) {
			console.error("Failed to capture image:", err);
		}
	};

	return (
		<div
			className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50 p-4"
			onClick={onClose}
		>
			<div
				className="bg-terminal-surface border-2 border-terminal-accent rounded-lg max-w-5xl w-auto max-h-[90vh] overflow-y-auto"
				onClick={(e) => e.stopPropagation()}
			>
				<div className="sticky top-0 bg-terminal-surface border-b border-terminal-border p-6 flex justify-between items-center">
					<div className="flex-1">
						<div className="flex items-center gap-3">
							<h2 className="text-terminal-accent text-2xl font-bold m-0">
								Evaluation Results
							</h2>
							{commonMetadata && (
								<div className="flex items-center gap-2 text-sm text-gray-400">
									<span>-</span>
									<span className="text-blue-400 font-semibold">
										{getDisplayModel(commonMetadata.model)}
									</span>
									<span>-</span>
									<span className="text-purple-400 font-semibold">
										{getDisplayVariant(
											commonMetadata.variant
										)}
									</span>
									<span>-</span>
									<span className="text-terminal-accent font-semibold">
										x{results.files_evaluated}
									</span>
								</div>
							)}
						</div>
						<p className="text-gray-400 text-sm mt-1">
							{results.stashName
								? `Stash: ${results.stashName}`
								: "Current Directory"}{" "}
							• {results.files_evaluated} files
						</p>
					</div>
					<div className="flex gap-3 items-center">
						{results?.stashName && (
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
						)}
						<button
							onClick={copyToClipboard}
							className="p-2 border border-terminal-accent text-terminal-accent rounded hover:bg-terminal-accent hover:text-black cursor-pointer transition-colors relative overflow-hidden"
							title="Copy evaluation as image"
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
					{totalStats.count > 1 && (
						<div className="mb-8 p-6 bg-linear-to-r from-zinc-800 to-zinc-900 border-2 border-terminal-accent rounded-lg">
							<h3 className="text-terminal-accent text-xl font-bold mb-4">
								Total Summary
							</h3>
							<div className="grid grid-cols-2 gap-6 mb-6">
								<div>
									<div className="text-gray-400 text-sm mb-2">
										Average Performance
									</div>
									<div className="flex items-baseline gap-3">
										<div className="text-terminal-accent text-4xl font-bold">
											{averagePercentage.toFixed(1)}%
										</div>
										<div className="text-gray-500 text-lg">
											{totalStats.totalScore.toFixed(1)} /{" "}
											{totalStats.totalMax}
										</div>
										{coeffOfVariation > 0 && (
											<div className="text-gray-500 text-sm mt-1">
												CV: {coeffOfVariation.toFixed(2)}%
											</div>
										)}
									</div>
								</div>
								<div className="grid grid-cols-2 gap-3">
									<div className="bg-terminal-surface p-3 rounded border border-terminal-border">
										<div className="text-gray-500 uppercase text-xs mb-1">
											Total Tests
										</div>
										<div className="text-terminal-accent font-bold text-2xl">
											{totalStats.totalTests}
										</div>
									</div>
									<div className="bg-terminal-surface p-3 rounded border border-terminal-border">
										<div className="text-gray-500 uppercase text-xs mb-1">
											Files Evaluated
										</div>
										<div className="text-terminal-accent font-bold text-2xl">
											{totalStats.count}
										</div>
									</div>
								</div>
							</div>

							{worstCategories.length > 0 && (
								<div className="border-t border-terminal-border pt-4">
									<h4 className="text-red-400 text-sm font-bold mb-3 uppercase">
										Five Worst Categories
									</h4>
									<div className="space-y-2">
										{worstCategories.map((cat, idx) => (
											<div
												key={cat.category}
												className="flex items-center gap-3"
											>
												<div className="w-6 h-6 flex items-center justify-center bg-red-950 border border-red-600 rounded text-red-400 text-xs font-bold shrink-0">
													{idx + 1}
												</div>
												<div className="flex-1 bg-terminal-surface rounded p-2 border border-red-900">
													<div className="flex justify-between items-center mb-1">
														<span className="text-gray-300 text-sm font-medium">
															{cat.category}
														</span>
														<span className="text-red-400 text-sm font-bold">
															{cat.percentage.toFixed(
																1
															)}
															%
														</span>
													</div>
													<div className="flex items-center gap-2 text-xs text-gray-500">
														<span>
															{cat.score.toFixed(
																1
															)}{" "}
															/ {cat.max}
														</span>
														<span>•</span>
														<span>
															{cat.count} tests
														</span>
													</div>
													<div className="mt-1 h-1 bg-red-950 rounded overflow-hidden">
														<div
															className="h-full bg-red-500"
															style={{
																width: `${cat.percentage}%`,
															}}
														/>
													</div>
												</div>
											</div>
										))}
									</div>
								</div>
							)}

							{categoryPercentages.length > 0 && (
								<div className="border-t border-terminal-border pt-4 mt-4">
									<h4 className="text-terminal-accent text-sm font-bold mb-3 uppercase">
										All Category Averages
									</h4>
									<div className="grid grid-cols-2 gap-2">
										{categoryPercentages
											.sort((a, b) => b.percentage - a.percentage)
											.map((cat) => (
												<div
													key={cat.category}
													className="bg-terminal-surface p-2 rounded border border-terminal-border"
												>
													<div className="flex justify-between items-center mb-1">
														<span className="text-gray-300 text-sm font-medium truncate mr-2">
															{cat.category}
														</span>
														<span className="text-terminal-accent text-sm font-bold shrink-0">
															{cat.percentage.toFixed(1)}%
														</span>
													</div>
													<div className="flex items-center gap-2 text-xs text-gray-500 mb-1">
														<span>
															{cat.score.toFixed(1)} / {cat.max}
														</span>
														<span>•</span>
														<span>{cat.count} tests</span>
													</div>
													<div className="h-1 bg-terminal-border rounded overflow-hidden">
														<div
															className="h-full bg-terminal-accent"
															style={{
																width: `${cat.percentage}%`,
															}}
														/>
													</div>
												</div>
											))}
									</div>
								</div>
							)}
						</div>
					)}

					{Object.entries(results.results || {}).map(
						([filename, result]: [string, any]) => {
							if (result.error) {
								return (
									<div
										key={filename}
										className="mb-4 p-4 bg-red-950 border border-red-600 rounded"
									>
										<div className="text-red-400 font-semibold">
											{filename}
										</div>
										<div className="text-red-300 text-sm mt-1">
											Error: {result.error}
										</div>
									</div>
								);
							}

							if (!result.summary) return null;

							const isFileCopied = copiedFiles.has(filename);

							return (
								<div
									key={filename}
									ref={(el) => {
										if (el) {
											fileRefsRef.current.set(filename, el);
										}
									}}
									className="mb-6 p-4 bg-zinc-900 border border-terminal-border rounded"
								>
									<div className="flex justify-between items-start mb-3">
										<div className="text-gray-300 font-semibold">
											{filename}
										</div>
										<div className="flex items-center gap-3">
											<div className="flex items-center gap-2">
												<div className="text-terminal-accent text-2xl font-bold">
													{result.summary.overall_percentage.toFixed(
														1
													)}
													%
												</div>
												<div className="text-gray-500 text-sm">
													{result.summary.total_score} /{" "}
													{result.summary.total_max}
												</div>
											</div>
											<button
												onClick={() =>
													copyFileResult(filename)
												}
												className="p-1.5 border border-terminal-accent text-terminal-accent rounded hover:bg-terminal-accent hover:text-black cursor-pointer transition-colors relative overflow-hidden"
												title="Copy file result as image"
											>
												<svg
													className={`h-4 w-4 ${
														isFileCopied
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
													className={`h-4 w-4 absolute inset-0 m-auto ${
														isFileCopied
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
										</div>
									</div>

									<div className="grid grid-cols-3 gap-3 text-xs">
										<div className="bg-terminal-surface p-3 rounded border border-terminal-border">
											<div className="text-gray-500 uppercase mb-1">
												Tests
											</div>
											<div className="text-terminal-accent font-bold text-lg">
												{result.summary.tests_completed}
											</div>
										</div>
									</div>

									{result.summary.category_breakdown &&
										Object.keys(
											result.summary.category_breakdown
										).length > 0 && (
											<div className="mt-3">
												<div className="text-gray-400 text-xs uppercase mb-2">
													Categories
												</div>
												<div className="grid grid-cols-2 gap-2">
													{Object.entries(
														result.summary
															.category_breakdown
													).map(
														([cat, data]: [
															string,
															any
														]) => (
															<div
																key={cat}
																className="bg-terminal-surface p-2 rounded text-xs"
															>
																<div className="flex justify-between mb-1">
																	<span className="text-gray-400">
																		{cat}
																	</span>
																	<span className="text-terminal-accent">
																		{data.percentage.toFixed(
																			1
																		)}
																		%
																	</span>
																</div>
																<div className="h-1 bg-terminal-border rounded overflow-hidden">
																	<div
																		className="h-full bg-terminal-accent"
																		style={{
																			width: `${data.percentage}%`,
																		}}
																	></div>
																</div>
															</div>
														)
													)}
												</div>
											</div>
										)}
								</div>
							);
						}
					)}
				</div>
			</div>
		</div>
	);
}
