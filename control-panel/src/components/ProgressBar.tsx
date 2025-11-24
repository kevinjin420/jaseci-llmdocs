import type { BenchmarkStatus } from "@/utils/types";

interface Props {
	status: BenchmarkStatus;
	onBatchClick?: (batchKey: string) => void;
	rerunningBatches?: Set<string>;
}

export default function ProgressBar({ status, onBatchClick, rerunningBatches }: Props) {
	return (
		<div
			className={`mt-3 px-4 py-3 rounded ${
				status.status === "running"
					? "bg-blue-950 border border-blue-600"
					: status.status === "completed"
					? "bg-green-950 border border-terminal-accent"
					: status.status === "failed"
					? "bg-red-950 border border-red-600"
					: "bg-zinc-900 border border-terminal-border"
			}`}
		>
			<div className="flex items-center gap-4">
				<div className="flex-1 bg-zinc-800 rounded-full h-2 overflow-hidden">
					<div
						className={`h-full transition-all duration-300 ${
							status.status === "running" ? "bg-blue-500" : "bg-terminal-accent"
						}`}
						style={{
							width:
								status.status === "idle" || status.status === "completed"
									? "100%"
									: status.batches_completed_global !== undefined &&
									  status.batches_total_global
									? `${(status.batches_completed_global / status.batches_total_global) * 100}%`
									: "0%",
						}}
					/>
				</div>
				<span
					className={`text-xs font-medium shrink-0 ${
						status.status === "running"
							? "text-blue-400"
							: status.status === "completed"
							? "text-terminal-accent"
							: status.status === "failed"
							? "text-red-500"
							: "text-gray-400"
					}`}
				>
					{status.status}
				</span>
				{status.status === "running" && (
					<span className="text-xs text-gray-400 shrink-0">
						{status.batches_completed_global ?? 0}/{status.batches_total_global || "?"}
					</span>
				)}
			</div>
			{status.batch_statuses && Object.keys(status.batch_statuses).length > 0 && (
				<div className="flex gap-2 mt-2 flex-wrap">
					{Object.entries(status.batch_statuses)
						.sort(([a], [b]) => parseInt(a) - parseInt(b))
						.map(([batchNum, bs]) => {
							const isRerunning = rerunningBatches?.has(batchNum);
							const canClick = onBatchClick && bs.status !== "pending" && !isRerunning;
							const getTitle = () => {
								if (isRerunning) return "Rerunning...";
								if (!canClick) return "";
								if (bs.status === "running") return `Click to restart stuck batch ${batchNum}`;
								return `Click to rerun batch ${batchNum}`;
							};
							return (
								<button
									key={batchNum}
									onClick={() => canClick && onBatchClick(batchNum)}
									disabled={!canClick}
									className={`px-2 py-1 rounded text-xs font-mono transition-all ${
										isRerunning
											? "bg-purple-900 text-purple-300 animate-pulse"
											: bs.status === "completed"
											? "bg-green-900 text-green-300"
											: bs.status === "failed"
											? "bg-red-900 text-red-300"
											: bs.status === "running" && bs.retry > 0
											? "bg-yellow-900 text-yellow-300"
											: bs.status === "running"
											? "bg-blue-900 text-blue-300"
											: "bg-zinc-800 text-gray-400"
									} ${canClick ? "cursor-pointer hover:ring-2 hover:ring-white/30" : ""}`}
									title={getTitle()}
								>
									{isRerunning
										? `${batchNum}...`
										: bs.status === "running" && bs.retry > 0
										? `${batchNum}: ${bs.retry}/${bs.max_retries}`
										: batchNum}
								</button>
							);
						})}
				</div>
			)}
		</div>
	);
}
