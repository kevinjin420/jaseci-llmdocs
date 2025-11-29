import { useState, useEffect } from "react";
import { io } from "socket.io-client";
import type { Socket } from "socket.io-client";
import BenchmarkControls from "@/components/BenchmarkControls";
import ProgressBar from "@/components/ProgressBar";
import TestFileList from "@/components/TestFileList";
import ResultsView from "@/components/ResultsView";
import { API_BASE, WS_BASE } from "@/utils/types";
import type { Model, Variant, TestFile, BenchmarkStatus, BatchStatus } from "@/utils/types";

interface Props {
	models: Model[];
	variants: Variant[];
	testFiles: TestFile[];
	onBenchmarkComplete: () => void;
}

let socket: Socket | null = null;

export default function BenchmarkView({ models, variants, testFiles, onBenchmarkComplete }: Props) {
	const [selectedModel, setSelectedModel] = useState(() => {
		return localStorage.getItem("benchmarkModel") || models[0]?.id || "";
	});
	const [selectedVariant, setSelectedVariant] = useState(() => {
		return localStorage.getItem("benchmarkVariant") || variants[0]?.name || "";
	});
	const [temperature, setTemperature] = useState(() => {
		const saved = localStorage.getItem("benchmarkTemperature");
		return saved ? parseFloat(saved) : 0.1;
	});
	const [queueSize, setQueueSize] = useState(() => {
		const saved = localStorage.getItem("benchmarkQueueSize");
		return saved ? parseInt(saved) : 1;
	});
	const [batchSize, setBatchSize] = useState(() => {
		const saved = localStorage.getItem("benchmarkBatchSize");
		return saved ? parseInt(saved) : 45;
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
	const [rerunningBatches, setRerunningBatches] = useState<Set<string>>(new Set());

	useEffect(() => localStorage.setItem("benchmarkModel", selectedModel), [selectedModel]);
	useEffect(() => localStorage.setItem("benchmarkVariant", selectedVariant), [selectedVariant]);
	useEffect(() => localStorage.setItem("benchmarkTemperature", temperature.toString()), [temperature]);
	useEffect(() => localStorage.setItem("benchmarkQueueSize", queueSize.toString()), [queueSize]);
	useEffect(() => localStorage.setItem("benchmarkBatchSize", batchSize.toString()), [batchSize]);
	useEffect(() => {
		status ? localStorage.setItem("benchmarkStatus", JSON.stringify(status)) : localStorage.removeItem("benchmarkStatus");
	}, [status]);
	useEffect(() => {
		runId ? localStorage.setItem("benchmarkRunId", runId) : localStorage.removeItem("benchmarkRunId");
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

		const checkRunning = async () => {
			try {
				const res = await fetch(`${API_BASE}/running`);
				const data = await res.json();
				const runs = data.runs || {};
				const activeRuns = Object.keys(runs);
				if (activeRuns.length > 0) {
					const savedRunIds = localStorage.getItem("benchmarkRunIds");
					const runIds = savedRunIds ? JSON.parse(savedRunIds) : activeRuns;
					setupSocketListener(runIds, runs, onBenchmarkComplete);
				} else if (status?.status === "running") {
					setStatus({ status: "idle", progress: "Idle", completed: 0, total: 0 });
					localStorage.removeItem("benchmarkRunIds");
				}
			} catch (e) {
				console.error("Failed to check running benchmarks:", e);
			}
		};

		const setupSocketListener = (runIds: string[], initialRuns: Record<string, any>, onComplete: () => void) => {
			const runState: Record<string, { batches: number; completed: number; done: boolean; failed: boolean; evaluating: boolean; index: number }> = {};
			let totalBatches = 0, completedBatches = 0, runsCompleted = 0, runsFailed = 0;
			let allBatchStatuses: Record<string, BatchStatus> = {};

			const prefixBatchStatuses = (statuses: Record<string, BatchStatus>, runIndex: number) => {
				const prefixed: Record<string, BatchStatus> = {};
				for (const [key, value] of Object.entries(statuses)) {
					prefixed[`${runIndex + 1}.${key}`] = value;
				}
				return prefixed;
			};

			runIds.forEach((id: string, index: number) => {
				const run = initialRuns[id];
				const numBatches = run?.num_batches || 0;
				const batchNum = run?.batch_num || 0;
				runState[id] = { batches: numBatches, completed: batchNum, done: false, failed: false, evaluating: false, index };
				totalBatches += numBatches;
				completedBatches += batchNum;
				if (run?.batch_statuses) {
					allBatchStatuses = { ...allBatchStatuses, ...prefixBatchStatuses(run.batch_statuses, index) };
				}
			});

			setStatus({
				status: "running",
				progress: `${completedBatches}/${totalBatches || "?"}`,
				completed: 0,
				total: runIds.length,
				batches_completed_global: completedBatches,
				batches_total_global: totalBatches || undefined,
				batch_statuses: allBatchStatuses,
				total_evaluations: runIds.length,
				completed_evaluations: 0,
			});

			const handleUpdate = (updateData: any) => {
				if (!runIds.includes(updateData.run_id)) return;
				const state = runState[updateData.run_id];
				if (!state || state.done) return;

				if (updateData.num_batches && state.batches === 0) {
					state.batches = updateData.num_batches;
					totalBatches += updateData.num_batches;
				}
				if (updateData.batch_num) {
					const delta = updateData.batch_num - state.completed;
					if (delta > 0) { completedBatches += delta; state.completed = updateData.batch_num; }
				}
				if (updateData.batch_statuses) {
					allBatchStatuses = { ...allBatchStatuses, ...prefixBatchStatuses(updateData.batch_statuses, state.index) };
				}
				
				if (updateData.status === "evaluating") {
					state.evaluating = true;
				}

				if (updateData.status === "completed" || updateData.status === "failed") {
					if (!state.done) {
						state.done = true;
						state.evaluating = false;
						runsCompleted++;
						if (updateData.status === "failed") { state.failed = true; runsFailed++; }
						onComplete();
					}
				}

				const evaluatingCount = Object.values(runState).filter(s => s.evaluating).length;
				const anyEvaluating = evaluatingCount > 0;
				
				// Only show "evaluating" as main status if everything is done generating
				// (i.e. all runs are either completed, failed, or evaluating)
				const allGenerationsDone = runIds.every(id => {
					const s = runState[id];
					return s.done || s.evaluating;
				});

				const finalStatus = runsCompleted === runIds.length
					? (runsFailed > 0 ? "failed" : "completed")
					: (allGenerationsDone && anyEvaluating) ? "evaluating" : "running";

				setStatus({
					status: finalStatus,
					progress: `${completedBatches}/${totalBatches || "?"}`,
					completed: runsCompleted,
					total: runIds.length,
					batches_completed_global: completedBatches,
					batches_total_global: totalBatches || undefined,
					batch_statuses: allBatchStatuses,
					evaluating_count: evaluatingCount,
					total_evaluations: runIds.length,
					completed_evaluations: runsCompleted,
				});

				if (runsCompleted === runIds.length) {
					socket?.off("benchmark_update", handleUpdate);
					localStorage.removeItem("benchmarkRunIds");
					setRunId(null);
				}
			};

			socket?.on("benchmark_update", handleUpdate);
		};

		checkRunning();
		return () => { if (socket) { socket.disconnect(); socket = null; } };
	}, []);

	const runBenchmark = async () => {
		setStatus({
			status: "running",
			progress: "Starting all runs...",
			completed: 0,
			total: queueSize,
			total_evaluations: queueSize,
			completed_evaluations: 0,
		});

		const payload: any = { model: selectedModel, variant: selectedVariant, temperature, batch_size: batchSize };

		const runIds: string[] = [];
		const runState: Record<string, { batches: number; completed: number; done: boolean; failed: boolean; evaluating: boolean; index: number }> = {};
		let totalBatches = 0, completedBatches = 0, runsCompleted = 0, runsFailed = 0;
		const currentEvalStatuses: Record<string, "pending" | "running" | "completed" | "failed"> = {};

		const startPromises = Array.from({ length: queueSize }, async (_, i) => {
			const res = await fetch(`${API_BASE}/benchmark/run`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify(payload),
			});
			const data = await res.json();
			runIds[i] = data.run_id;
			runState[data.run_id] = { batches: 0, completed: 0, done: false, failed: false, evaluating: false, index: i };
			currentEvalStatuses[(i + 1).toString()] = "pending";
			return data.run_id;
		});

		await Promise.all(startPromises);
		setRunId(runIds[0]);
		localStorage.setItem("benchmarkRunIds", JSON.stringify(runIds));

		await new Promise<void>((resolve) => {
			if (!socket) { resolve(); return; }

			const timeoutId = setTimeout(() => { cleanup(); resolve(); }, 600000);
			let allBatchStatuses: Record<string, BatchStatus> = {};

			const prefixBatchStatuses = (statuses: Record<string, BatchStatus>, runIndex: number) => {
				const prefixed: Record<string, BatchStatus> = {};
				for (const [key, value] of Object.entries(statuses)) {
					prefixed[`${runIndex + 1}.${key}`] = value;
				}
				return prefixed;
			};

			const handleUpdate = (data: any) => {
				if (!runIds.includes(data.run_id)) return;
				const state = runState[data.run_id];
				if (!state || state.done) return;

				if (data.num_batches && state.batches === 0) { state.batches = data.num_batches; totalBatches += data.num_batches; }
				if (data.batch_num) {
					const delta = data.batch_num - state.completed;
					if (delta > 0) { completedBatches += delta; state.completed = data.batch_num; }
				}
				if (data.batch_statuses) {
					allBatchStatuses = { ...allBatchStatuses, ...prefixBatchStatuses(data.batch_statuses, state.index) };
				}
				
				const evalKey = (state.index + 1).toString();
				if (data.status === "evaluating") {
					state.evaluating = true;
					currentEvalStatuses[evalKey] = "running";
				}

				if (data.status === "completed" || data.status === "failed") {
					if (!state.done) {
						state.done = true;
						state.evaluating = false;
						runsCompleted++;
						if (data.status === "failed") { 
							state.failed = true; 
							runsFailed++; 
							currentEvalStatuses[evalKey] = "failed";
						} else {
							currentEvalStatuses[evalKey] = "completed";
						}
						onBenchmarkComplete();
					}
				}

				const evaluatingCount = Object.values(runState).filter(s => s.evaluating).length;
				const anyEvaluating = evaluatingCount > 0;

				const allGenerationsDone = runIds.every(id => {
					const s = runState[id];
					return s.done || s.evaluating;
				});

				const finalStatus = runsCompleted === queueSize
					? (runsFailed > 0 ? "failed" : "completed")
					: (allGenerationsDone && anyEvaluating) ? "evaluating" : "running";

				setStatus({
					status: finalStatus,
					progress: `${completedBatches}/${totalBatches || "?"}`,
					completed: runsCompleted,
					total: queueSize,
					batches_completed_global: completedBatches,
					batches_total_global: totalBatches || undefined,
					batch_statuses: allBatchStatuses,
					evaluating_count: evaluatingCount,
					total_evaluations: queueSize,
					completed_evaluations: runsCompleted,
					evaluation_statuses: { ...currentEvalStatuses },
				});

				if (runsCompleted === queueSize) { cleanup(); resolve(); }
			};

			const cleanup = () => { socket?.off("benchmark_update", handleUpdate); clearTimeout(timeoutId); };
			socket.on("benchmark_update", handleUpdate);
		});

		setStatus({
			status: runsFailed > 0 ? "failed" : "completed",
			progress: runsFailed > 0 ? `${runsFailed} run(s) failed` : "All runs completed",
			completed: queueSize,
			total: queueSize,
			batches_completed_global: completedBatches,
			batches_total_global: totalBatches,
			total_evaluations: queueSize,
			completed_evaluations: queueSize,
			evaluation_statuses: { ...currentEvalStatuses },
		});
		setRunId(null);
		localStorage.removeItem("benchmarkRunIds");
	};

	const cancelBenchmark = () => {
		socket?.off("benchmark_update");
		setRunId(null);
		setStatus({ status: "idle", progress: "Idle", completed: 0, total: 0 });
		localStorage.removeItem("benchmarkRunId");
		localStorage.removeItem("benchmarkRunIds");
		localStorage.removeItem("benchmarkStatus");
	};

	const rerunBatch = async (batchKey: string) => {
		const savedRunIds = localStorage.getItem("benchmarkRunIds");
		const runIds = savedRunIds ? JSON.parse(savedRunIds) : [runId];

		const parts = batchKey.split(".");
		let targetRunId: string;
		let batchNum: number;

		if (parts.length === 2) {
			const runIndex = parseInt(parts[0]) - 1;
			batchNum = parseInt(parts[1]);
			targetRunId = runIds[runIndex];
		} else {
			batchNum = parseInt(batchKey);
			targetRunId = runIds[0];
		}

		if (!targetRunId) {
			console.error("No run ID found for batch rerun");
			return;
		}

		setRerunningBatches(prev => new Set(prev).add(batchKey));

		try {
			const res = await fetch(`${API_BASE}/benchmark/rerun-batch`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ run_id: targetRunId, batch_num: batchNum }),
			});
			const data = await res.json();

			if (!res.ok) {
				console.error("Failed to start batch rerun:", data.error);
				setRerunningBatches(prev => {
					const next = new Set(prev);
					next.delete(batchKey);
					return next;
				});
				return;
			}

			const handleRerunUpdate = (updateData: any) => {
				if (updateData.batch_num !== batchNum) return;

				if (updateData.status === "completed" || updateData.status === "failed") {
					setRerunningBatches(prev => {
						const next = new Set(prev);
						next.delete(batchKey);
						return next;
					});

					if (updateData.status === "completed") {
						setStatus(prev => {
							if (!prev?.batch_statuses) return prev;
							const newStatuses = { ...prev.batch_statuses };
							newStatuses[batchKey] = { status: "completed", retry: 0, max_retries: 3 };
							return { ...prev, batch_statuses: newStatuses };
						});
					}

					socket?.off("batch_rerun_update", handleRerunUpdate);
					onBenchmarkComplete();
				}
			};

			socket?.on("batch_rerun_update", handleRerunUpdate);
		} catch (e) {
			console.error("Failed to rerun batch:", e);
			setRerunningBatches(prev => {
				const next = new Set(prev);
				next.delete(batchKey);
				return next;
			});
		}
	};

	const handleFileClick = async (filePath: string) => {
		setSelectedFile(filePath);
		try {
			const res = await fetch(`${API_BASE}/evaluate`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ file: filePath }),
			});
			setResults(await res.json());
		} catch (e) {
			console.error("Failed to evaluate file:", e);
		}
	};

	const handleDeleteFile = async (filePath: string, e: React.MouseEvent) => {
		e.stopPropagation();
		try {
			await fetch(`${API_BASE}/delete-file`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ file_path: filePath }),
			});
			if (selectedFile === filePath) { setSelectedFile(null); setResults(null); }
			onBenchmarkComplete();
		} catch (e) {
			console.error("Failed to delete file:", e);
		}
	};

	const isRunning = status?.status === "running";
	const statusDisplay = status || { status: "idle", progress: "Idle", completed: 0, total: 0 };

	return (
		<div className="flex flex-col gap-6">
			<div className="p-4 bg-terminal-surface border border-terminal-border rounded">
				<BenchmarkControls
					models={models}
					variants={variants}
					selectedModel={selectedModel}
					setSelectedModel={setSelectedModel}
					selectedVariant={selectedVariant}
					setSelectedVariant={setSelectedVariant}
					temperature={temperature}
					setTemperature={setTemperature}
					queueSize={queueSize}
					setQueueSize={setQueueSize}
					batchSize={batchSize}
					setBatchSize={setBatchSize}
					isRunning={isRunning}
					onRun={runBenchmark}
					onCancel={cancelBenchmark}
				/>
				<ProgressBar
					status={statusDisplay}
					onBatchClick={rerunBatch}
					rerunningBatches={rerunningBatches}
				/>
			</div>

			<div className="grid grid-cols-[280px_1fr] gap-6 min-h-[600px]">
				<TestFileList
					files={testFiles}
					selectedFile={selectedFile}
					onFileClick={handleFileClick}
					onFileDelete={handleDeleteFile}
				/>
				<ResultsView results={results} />
			</div>
		</div>
	);
}
