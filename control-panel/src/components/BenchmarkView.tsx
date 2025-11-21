import { useState, useEffect } from "react";
import { io, Socket } from "socket.io-client";

interface Model {
	id: string;
	name: string;
	context_length: number;
	pricing?: {
		prompt: string | number;
		completion: string | number;
	};
	architecture?: {
		tokenizer?: string;
		input_modalities?: string[];
		output_modalities?: string[];
	};
}

interface Variant {
	name: string;
	file: string;
	size: number;
	size_kb: number;
}

interface TestFile {
	name: string;
	path: string;
	size: number;
	modified: number;
}

interface BenchmarkStatus {
	status: "idle" | "running" | "completed" | "failed";
	progress?: string;
	result?: any;
	error?: string;
	completed?: number;
	total?: number;
	tests_completed?: number;
	tests_total?: number;
	batch_num?: number;
	num_batches?: number;
	batches_completed_global?: number;
	batches_total_global?: number;
	current_batch_global?: number;
}

interface Props {
	models: Model[];
	variants: Variant[];
	testFiles: TestFile[];
	onBenchmarkComplete: () => void;
}

const API_BASE = "http://localhost:5050/api";
const WS_BASE = "http://localhost:5050";

let socket: Socket | null = null;

export default function BenchmarkView({
	models,
	variants,
	testFiles,
	onBenchmarkComplete,
}: Props) {
	const [selectedModel, setSelectedModel] = useState(() => {
		const saved = localStorage.getItem("benchmarkModel");
		return saved || models[0]?.id || "";
	});
	const [selectedVariant, setSelectedVariant] = useState(() => {
		const saved = localStorage.getItem("benchmarkVariant");
		return saved || variants[0]?.name || "";
	});
	const [temperature, setTemperature] = useState(() => {
		const saved = localStorage.getItem("benchmarkTemperature");
		return saved ? parseFloat(saved) : 0.1;
	});
	const [smallSuite, setSmallSuite] = useState(() => {
		const saved = localStorage.getItem("benchmarkSmallSuite");
		return saved === "true";
	});
	const [queueSize, setQueueSize] = useState(() => {
		const saved = localStorage.getItem("benchmarkQueueSize");
		return saved ? parseInt(saved) : 1;
	});
	const [status, setStatus] = useState<BenchmarkStatus | null>(() => {
		const saved = localStorage.getItem("benchmarkStatus");
		return saved ? JSON.parse(saved) : null;
	});
	const [runId, setRunId] = useState<string | null>(() => {
		return localStorage.getItem("benchmarkRunId");
	});
	const [selectedFile, setSelectedFile] = useState<string | null>(null);
	const [results, setResults] = useState<any>(null);

	useEffect(() => {
		localStorage.setItem("benchmarkModel", selectedModel);
	}, [selectedModel]);

	useEffect(() => {
		localStorage.setItem("benchmarkVariant", selectedVariant);
	}, [selectedVariant]);

	useEffect(() => {
		localStorage.setItem("benchmarkTemperature", temperature.toString());
	}, [temperature]);

	useEffect(() => {
		localStorage.setItem("benchmarkSmallSuite", smallSuite.toString());
	}, [smallSuite]);

	useEffect(() => {
		localStorage.setItem("benchmarkQueueSize", queueSize.toString());
	}, [queueSize]);

	useEffect(() => {
		if (status) {
			localStorage.setItem("benchmarkStatus", JSON.stringify(status));
		} else {
			localStorage.removeItem("benchmarkStatus");
		}
	}, [status]);

	useEffect(() => {
		if (runId) {
			localStorage.setItem("benchmarkRunId", runId);
		} else {
			localStorage.removeItem("benchmarkRunId");
		}
	}, [runId]);

	useEffect(() => {
		if (!socket) {
			socket = io(WS_BASE, {
				transports: ["polling", "websocket"],
				reconnection: true,
				reconnectionDelay: 1000,
				reconnectionAttempts: 5,
			});
		}

		return () => {
			if (socket) {
				socket.disconnect();
				socket = null;
			}
		};
	}, []);

	const runBenchmark = async () => {
		setStatus({
			status: "running",
			progress: "Starting queue...",
			completed: 0,
			total: queueSize,
		});

		let totalBatchesGlobal = 0;
		let batchesCompletedGlobal = 0;
		let jobsCompleted = 0;

		for (let i = 0; i < queueSize; i++) {
			try {
				const payload: any = {
					model: selectedModel,
					variant: selectedVariant,
					temperature,
				};

				if (smallSuite) {
					payload.test_limit = 40;
				}

				setStatus({
					status: "running",
					progress: `Starting run ${i + 1}/${queueSize}...`,
					completed: jobsCompleted,
					total: queueSize,
					batches_completed_global: batchesCompletedGlobal,
					batches_total_global: totalBatchesGlobal || undefined,
				});

				const res = await fetch(`${API_BASE}/benchmark/run`, {
					method: "POST",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify(payload),
				});

				const data = await res.json();
				const currentRunId = data.run_id;
				setRunId(currentRunId);

				await new Promise<void>((resolve, reject) => {
					if (!socket) {
						reject(new Error("WebSocket not connected"));
						return;
					}

					let timeoutId: ReturnType<typeof setTimeout> | null = null;
					let currentJobBatches = 0;

					const handleUpdate = (data: any) => {
						if (data.run_id === currentRunId) {
							if (data.num_batches) {
								currentJobBatches = data.num_batches;
								if (totalBatchesGlobal === 0) {
									totalBatchesGlobal =
										data.num_batches * queueSize;
								}
							}

							const currentBatchInJob = data.batch_num || 0;
							const batchesCompletedInCurrentJob =
								currentBatchInJob > 0
									? currentBatchInJob - 1
									: 0;
							const currentBatchGlobal =
								currentBatchInJob > 0
									? batchesCompletedGlobal + currentBatchInJob
									: 0;

							setStatus({
								status: data.status,
								progress: `Run ${i + 1}/${queueSize}: ${
									data.progress || ""
								}`,
								result: data.result,
								error: data.error,
								completed: jobsCompleted,
								total: queueSize,
								tests_completed: data.tests_completed,
								tests_total: data.tests_total,
								batch_num: data.batch_num,
								num_batches: data.num_batches,
								batches_completed_global:
									batchesCompletedGlobal +
									batchesCompletedInCurrentJob,
								batches_total_global: totalBatchesGlobal,
								current_batch_global: currentBatchGlobal,
							});

							if (
								data.status === "completed" ||
								data.status === "failed"
							) {
								batchesCompletedGlobal += currentJobBatches;
								jobsCompleted++;
								cleanup();
								resolve();
							}
						}
					};

					const cleanup = () => {
						socket?.off("benchmark_update", handleUpdate);
						if (timeoutId) clearTimeout(timeoutId);
					};

					socket.on("benchmark_update", handleUpdate);

					timeoutId = setTimeout(() => {
						cleanup();
						reject(new Error("Benchmark timeout after 10 minutes"));
					}, 600000);
				});

				onBenchmarkComplete();
			} catch (error) {
				console.error(`Error running benchmark ${i + 1}:`, error);
				setStatus({
					status: "failed",
					progress: `Failed at run ${i + 1}/${queueSize}`,
					completed: jobsCompleted,
					total: queueSize,
				});
				setRunId(null);
				return;
			}
		}

		setStatus({
			status: "completed",
			progress: "All runs completed",
			completed: queueSize,
			total: queueSize,
		});
		setRunId(null);
		onBenchmarkComplete();
	};

	const cancelBenchmark = () => {
		if (socket) {
			socket.off("benchmark_update");
		}
		setRunId(null);
		setStatus({ status: "idle", progress: "Idle", completed: 0, total: 0 });
		localStorage.removeItem("benchmarkRunId");
		localStorage.removeItem("benchmarkStatus");
	};

	const handleFileClick = async (filePath: string) => {
		setSelectedFile(filePath);
		try {
			const res = await fetch(`${API_BASE}/evaluate`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ file: filePath }),
			});
			const data = await res.json();
			setResults(data);
		} catch (error) {
			console.error("Failed to evaluate file:", error);
		}
	};

	const handleDeleteFile = async (filePath: string, e: React.MouseEvent) => {
		e.stopPropagation();

		if (!confirm(`Delete ${filePath.split("/").pop()}?`)) return;

		try {
			await fetch(`${API_BASE}/delete-file`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ file_path: filePath }),
			});

			if (selectedFile === filePath) {
				setSelectedFile(null);
				setResults(null);
			}

			onBenchmarkComplete();
		} catch (error) {
			console.error("Failed to delete file:", error);
			alert("Failed to delete file");
		}
	};

	const isRunning = status?.status === "running";
	const statusDisplay = status || {
		status: "idle",
		progress: "Idle",
		completed: 0,
		total: 0,
	};

	const groupedVariants = variants.reduce(
		(groups: Record<string, Variant[]>, variant) => {
			const match = variant.name.match(/[_-]v(\d+)/);
			const version = match ? `v${match[1]}` : "other";
			if (!groups[version]) groups[version] = [];
			groups[version].push(variant);
			return groups;
		},
		{}
	);

	const sortedVersions = Object.keys(groupedVariants).sort((a, b) => {
		if (a === "other") return 1;
		if (b === "other") return -1;
		const numA = parseInt(a.substring(1));
		const numB = parseInt(b.substring(1));
		return numB - numA;
	});

	return (
		<div className="flex flex-col gap-6">
			<div className="p-4 bg-terminal-surface border border-terminal-border rounded">
				<div className="flex gap-3 items-center justify-between">
					<div className="flex gap-3 items-center flex-wrap">
						<select
							value={selectedModel}
							onChange={(e) => setSelectedModel(e.target.value)}
							disabled={isRunning}
							className="flex-1 max-w-[400px] px-3 py-2 bg-zinc-900 border border-terminal-border rounded text-gray-300 text-sm min-w-[120px] focus:outline-none focus:border-terminal-accent disabled:opacity-50 disabled:cursor-not-allowed"
						>
							{models.map((m) => (
								<option key={m.id} value={m.id}>
									{m.name}
								</option>
							))}
						</select>

						<select
							value={selectedVariant}
							onChange={(e) => setSelectedVariant(e.target.value)}
							disabled={isRunning}
							className="flex-1 max-w-[200px] px-3 py-2 bg-zinc-900 border border-terminal-border rounded text-gray-300 text-sm min-w-[120px] focus:outline-none focus:border-terminal-accent disabled:opacity-50 disabled:cursor-not-allowed"
						>
							{sortedVersions.map((version) => (
								<optgroup
									key={version}
									label={version.toUpperCase()}
									className="bg-zinc-900 text-terminal-accent font-semibold text-sm"
								>
									{groupedVariants[version].map((v) => (
										<option
											key={v.name}
											value={v.name}
											className="bg-zinc-900 text-gray-300"
										>
											{v.name} ({v.size_kb} KB)
										</option>
									))}
								</optgroup>
							))}
						</select>

						<span>temp</span>

						<input
							type="number"
							min="0"
							max="2"
							step="0.1"
							value={temperature}
							onChange={(e) =>
								setTemperature(parseFloat(e.target.value))
							}
							disabled={isRunning}
							className="w-20 px-3 py-2 bg-zinc-900 border border-terminal-border rounded text-gray-300 text-sm focus:outline-none focus:border-terminal-accent disabled:opacity-50 disabled:cursor-not-allowed"
							placeholder="Temp"
						/>

						<span>#</span>

						<input
							type="number"
							min="1"
							max="20"
							step="1"
							value={queueSize}
							onChange={(e) =>
								setQueueSize(parseInt(e.target.value) || 1)
							}
							disabled={isRunning}
							className="w-16 px-2 py-2 bg-zinc-900 border border-terminal-border rounded text-gray-300 text-sm focus:outline-none focus:border-terminal-accent disabled:opacity-50 disabled:cursor-not-allowed text-center"
							title="Number of runs to queue"
						/>

						<label className="flex items-center gap-2 px-3 py-2 bg-zinc-900 border border-terminal-border rounded text-gray-300 text-sm cursor-pointer hover:border-gray-600">
							<input
								type="checkbox"
								checked={smallSuite}
								onChange={(e) =>
									setSmallSuite(e.target.checked)
								}
								disabled={isRunning}
								className="cursor-pointer"
							/>
							<span>Small Suite</span>
						</label>
					</div>

					<div className="flex gap-3 items-center">
						{!isRunning ? (
							<button
								onClick={runBenchmark}
								disabled={!selectedModel || !selectedVariant}
								className="px-6 py-2 bg-terminal-accent text-black rounded text-sm font-semibold whitespace-nowrap hover:bg-green-500 disabled:bg-terminal-border disabled:text-gray-600 disabled:cursor-not-allowed cursor-pointer"
							>
								Run {queueSize}
							</button>
						) : (
							<button
								onClick={cancelBenchmark}
								className="px-6 py-2 bg-red-600 text-white rounded text-sm font-semibold whitespace-nowrap hover:bg-red-700 cursor-pointer"
							>
								Cancel
							</button>
						)}
					</div>
				</div>

				<div
					className={`mt-3 px-4 py-3 rounded ${
						statusDisplay.status === "running"
							? "bg-blue-950 border border-blue-600"
							: statusDisplay.status === "completed"
							? "bg-green-950 border border-terminal-accent"
							: statusDisplay.status === "failed"
							? "bg-red-950 border border-red-600"
							: "bg-zinc-900 border border-terminal-border"
					}`}
				>
					<div className="flex items-center justify-between mb-2">
						<span
							className={`text-xs font-semibold uppercase ${
								statusDisplay.status === "running"
									? "text-blue-400"
									: statusDisplay.status === "completed"
									? "text-terminal-accent"
									: statusDisplay.status === "failed"
									? "text-red-500"
									: "text-gray-400"
							}`}
						>
							{statusDisplay.status}
						</span>
						<div className="flex items-center gap-3 text-xs">
							{(statusDisplay.total ?? 0) > 0 && (
								<span className="text-gray-400">
									Run: {statusDisplay.completed}/
									{statusDisplay.total}
								</span>
							)}
							{statusDisplay.current_batch_global &&
								statusDisplay.batches_total_global && (
									<span className="text-gray-400">
										Batch:{" "}
										{statusDisplay.current_batch_global}/
										{statusDisplay.batches_total_global}
									</span>
								)}
							{statusDisplay.tests_completed !== undefined &&
								statusDisplay.tests_total && (
									<span className="text-gray-400">
										Tests: {statusDisplay.tests_completed}/
										{statusDisplay.tests_total}
									</span>
								)}
						</div>
					</div>
					<div className="w-full bg-zinc-800 rounded-full h-2 overflow-hidden">
						<div
							className="bg-terminal-accent h-full transition-all duration-300"
							style={{
								width:
									statusDisplay.status === "idle" ||
									statusDisplay.status === "completed"
										? "100%"
										: statusDisplay.batches_completed_global !==
												undefined &&
										  statusDisplay.batches_total_global
										? `${
												(statusDisplay.batches_completed_global /
													statusDisplay.batches_total_global) *
												100
										  }%`
										: "0%",
							}}
						/>
					</div>
				</div>
			</div>

			<div className="grid grid-cols-[280px_1fr] gap-6 min-h-[600px]">
				<div className="bg-terminal-surface border border-terminal-border rounded flex flex-col">
					<div className="flex justify-between items-center p-4 border-b border-terminal-border">
						<h3 className="text-terminal-accent text-base m-0">
							Test Results
						</h3>
						<span className="text-xs text-gray-500 bg-zinc-900 px-2 py-1 rounded">
							{testFiles.length} files
						</span>
					</div>
					<div className="flex-1 overflow-y-auto p-2">
						{testFiles.length === 0 ? (
							<div className="flex items-center justify-center h-full text-gray-600 text-sm">
								<p>No test files yet</p>
							</div>
						) : (
							[...testFiles]
								.sort((a, b) => b.modified - a.modified)
								.map((file) => (
									<div
										key={file.path}
										className={`p-3 mb-2 rounded border cursor-pointer transition-all ${
											selectedFile === file.path
												? "bg-green-950 border-terminal-accent"
												: "bg-zinc-900 border-terminal-border hover:bg-zinc-800 hover:border-gray-600"
										}`}
										onClick={() =>
											handleFileClick(file.path)
										}
									>
										<div className="flex justify-between items-start gap-2">
											<div className="flex-1 min-w-0">
												<div className="text-gray-300 text-sm mb-1 break-all">
													{file.name}
												</div>
												<div className="text-gray-500 text-xs">
													{(file.size / 1024).toFixed(
														1
													)}{" "}
													KB
												</div>
											</div>
											<button
												onClick={(e) =>
													handleDeleteFile(
														file.path,
														e
													)
												}
												className="shrink-0 p-1 text-red-500 hover:text-red-400 hover:bg-red-950 rounded transition-colors"
												title="Delete file"
											>
												<svg
													className="w-4 h-4"
													fill="none"
													stroke="currentColor"
													viewBox="0 0 24 24"
												>
													<path
														strokeLinecap="round"
														strokeLinejoin="round"
														strokeWidth={2}
														d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
													/>
												</svg>
											</button>
										</div>
									</div>
								))
						)}
					</div>
				</div>

				<div className="bg-terminal-surface border border-terminal-border rounded p-6 overflow-y-auto">
					{!results ? (
						<div className="flex items-center justify-center h-full text-gray-600 text-base">
							<p>Select a test file to view results</p>
						</div>
					) : (
						<>
							{!results.results && results.summary && (
								<>
									<div className="grid grid-cols-[auto_1fr] gap-8 p-6 bg-zinc-900 rounded mb-6 items-center">
										<div className="relative w-25 h-25">
											<svg
												viewBox="0 0 100 100"
												className="w-full h-full -rotate-90"
											>
												<circle
													cx="50"
													cy="50"
													r="45"
													fill="none"
													stroke="#333"
													strokeWidth="6"
												/>
												<circle
													cx="50"
													cy="50"
													r="45"
													fill="none"
													stroke="#00cc00"
													strokeWidth="6"
													strokeDasharray="283"
													className="transition-all duration-700"
													style={{
														strokeDashoffset:
															283 -
															(283 *
																results.summary
																	.overall_percentage) /
																100,
													}}
												/>
											</svg>
											<div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 text-center">
												<span className="block text-2xl font-bold text-terminal-accent">
													{results.summary.overall_percentage.toFixed(
														1
													)}
													%
												</span>
												<span className="block text-xs text-gray-400 uppercase">
													Score
												</span>
											</div>
										</div>

										<div className="flex flex-col gap-2">
											<div className="flex justify-between px-3 py-2 bg-terminal-surface rounded border-l-2 border-terminal-accent">
												<span className="text-gray-400 text-sm">
													Total Score
												</span>
												<span className="text-terminal-accent font-semibold text-sm">
													{
														results.summary
															.total_score
													}{" "}
													/{" "}
													{results.summary.total_max}
												</span>
											</div>
											<div className="flex justify-between px-3 py-2 bg-terminal-surface rounded border-l-2 border-terminal-accent">
												<span className="text-gray-400 text-sm">
													Tests
												</span>
												<span className="text-terminal-accent font-semibold text-sm">
													{
														results.summary
															.tests_completed
													}
												</span>
											</div>
											{results.summary.patched_count >
												0 && (
												<div className="flex justify-between px-3 py-2 bg-terminal-surface rounded border-l-2 border-orange-500">
													<span className="text-gray-400 text-sm">
														Patched
													</span>
													<span className="text-terminal-accent font-semibold text-sm">
														{
															results.summary
																.patched_count
														}
													</span>
												</div>
											)}
										</div>
									</div>

									<div className="mb-6">
										<h3 className="text-terminal-accent text-base mb-4 pb-2 border-b border-terminal-border">
											Category Breakdown
										</h3>
										<div className="flex flex-col gap-3">
											{Object.entries(
												results.summary
													.category_breakdown || {}
											).map(
												([name, data]: [
													string,
													any
												]) => (
													<div
														key={name}
														className="bg-zinc-900 p-3 rounded border border-terminal-border"
													>
														<div className="flex justify-between mb-2">
															<span className="text-gray-300 text-sm">
																{name}
															</span>
															<span className="text-terminal-accent text-xs">
																{data.score.toFixed(
																	2
																)}{" "}
																/ {data.max} (
																{data.percentage.toFixed(
																	1
																)}
																%)
															</span>
														</div>
														<div className="h-1.5 bg-terminal-border rounded overflow-hidden mb-1">
															<div
																className="h-full bg-terminal-accent transition-all duration-500"
																style={{
																	width: `${data.percentage}%`,
																}}
															></div>
														</div>
														<div className="flex justify-end text-xs text-gray-500">
															{data.count} tests
														</div>
													</div>
												)
											)}
										</div>
									</div>

									<div className="mb-6">
										<h3 className="text-terminal-accent text-base mb-4 pb-2 border-b border-terminal-border">
											Difficulty Levels
										</h3>
										<div className="flex flex-col gap-3">
											{Object.entries(
												results.summary
													.level_breakdown || {}
											)
												.sort(([levelA], [levelB]) => {
													const numA = parseInt(
														levelA.replace(
															/\D/g,
															""
														)
													);
													const numB = parseInt(
														levelB.replace(
															/\D/g,
															""
														)
													);
													return numA - numB;
												})
												.map(
													([level, data]: [
														string,
														any
													]) => (
														<div
															key={level}
															className="bg-zinc-900 p-3 rounded border border-terminal-border"
														>
															<div className="flex justify-between mb-2">
																<span className="text-gray-300 text-sm">
																	{level}
																</span>
																<span className="text-terminal-accent text-xs">
																	{data.score.toFixed(
																		2
																	)}{" "}
																	/ {data.max}{" "}
																	(
																	{data.percentage.toFixed(
																		1
																	)}
																	%)
																</span>
															</div>
															<div className="h-1.5 bg-terminal-border rounded overflow-hidden mb-1">
																<div
																	className="h-full bg-terminal-accent transition-all duration-500"
																	style={{
																		width: `${data.percentage}%`,
																	}}
																></div>
															</div>
															<div className="flex justify-end text-xs text-gray-500">
																{data.count}{" "}
																tests
															</div>
														</div>
													)
												)}
										</div>
									</div>
								</>
							)}

							{results.results && (
								<div>
									<h3 className="text-terminal-accent text-base mb-4">
										Multi-Variant Comparison
									</h3>
									<div className="grid grid-cols-[repeat(auto-fit,minmax(150px,1fr))] gap-3">
										{Object.entries(results.results).map(
											([variant, data]: [
												string,
												any
											]) => (
												<div
													key={variant}
													className="bg-zinc-900 p-4 rounded border border-terminal-border text-center"
												>
													<div className="text-gray-400 text-xs uppercase mb-2">
														{variant}
													</div>
													<div className="text-3xl font-bold text-terminal-accent mb-1">
														{data.summary.overall_percentage.toFixed(
															1
														)}
														%
													</div>
													<div className="flex flex-col gap-0.5 text-xs text-gray-500">
														<span>
															{
																data.summary
																	.total_score
															}{" "}
															/{" "}
															{
																data.summary
																	.total_max
															}
														</span>
														<span>
															{data.file_size}{" "}
															bytes
														</span>
													</div>
												</div>
											)
										)}
									</div>
								</div>
							)}
						</>
					)}
				</div>
			</div>
		</div>
	);
}
