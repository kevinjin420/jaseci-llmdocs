import type { Model, Variant } from "@/utils/types";
import ModelSelector from "./ModelSelector";
import DocumentationSelector from "./DocumentationSelector";

interface Props {
	models: Model[];
	variants: Variant[];
	selectedModel: string;
	setSelectedModel: (model: string) => void;
	selectedVariant: string;
	setSelectedVariant: (variant: string) => void;
	temperature: number;
	setTemperature: (temp: number) => void;
	queueSize: number;
	setQueueSize: (size: number) => void;
	batchSize: number;
	setBatchSize: (size: number) => void;
	customBatchSizes: string;
	setCustomBatchSizes: (sizes: string) => void;
	isRunning: boolean;
	onRun: () => void;
	onCancel: () => void;
}

export default function BenchmarkControls({
	models,
	variants,
	selectedModel,
	setSelectedModel,
	selectedVariant,
	setSelectedVariant,
	temperature,
	setTemperature,
	queueSize,
	setQueueSize,
	batchSize,
	setBatchSize,
	customBatchSizes,
	setCustomBatchSizes,
	isRunning,
	onRun,
	onCancel,
}: Props) {
	return (
		<div className="flex gap-3 items-center justify-between">
			<div className="flex gap-3 items-center flex-wrap">
				<div className="flex-1 min-w-[300px]">
					<ModelSelector
						models={models}
						selectedModel={selectedModel}
						onSelect={setSelectedModel}
						disabled={isRunning}
					/>
				</div>

				<div className="flex-1 min-w-[250px]">
					<DocumentationSelector
						variants={variants}
						selectedVariant={selectedVariant}
						onSelect={setSelectedVariant}
						disabled={isRunning}
					/>
				</div>

				<span>temp</span>
				<input
					type="number"
					min="0"
					max="2"
					step="0.1"
					value={temperature}
					onChange={(e) => setTemperature(parseFloat(e.target.value))}
					disabled={isRunning}
					className="w-20 px-3 py-2 bg-zinc-900 border border-terminal-border rounded text-gray-300 text-sm focus:outline-none focus:border-terminal-accent disabled:opacity-50 disabled:cursor-not-allowed"
				/>

				<span>#</span>
				<input
					type="number"
					min="1"
					max="20"
					step="1"
					value={queueSize}
					onChange={(e) => setQueueSize(parseInt(e.target.value) || 1)}
					disabled={isRunning}
					className="w-16 px-2 py-2 bg-zinc-900 border border-terminal-border rounded text-gray-300 text-sm focus:outline-none focus:border-terminal-accent disabled:opacity-50 disabled:cursor-not-allowed text-center"
					title="Number of runs to queue"
				/>

				<span>batch</span>
				<input
					type="number"
					min="1"
					max="100"
					step="1"
					value={batchSize || ""}
					onChange={(e) => setBatchSize(e.target.value === "" ? 0 : parseInt(e.target.value))}
					onBlur={(e) => { if (!e.target.value || parseInt(e.target.value) < 1) setBatchSize(45); }}
					disabled={isRunning || customBatchSizes.trim() !== ""}
					className="w-16 px-2 py-2 bg-zinc-900 border border-terminal-border rounded text-gray-300 text-sm focus:outline-none focus:border-terminal-accent disabled:opacity-50 disabled:cursor-not-allowed text-center"
					title="Tests per batch"
				/>

				<span>custom</span>
				<input
					type="text"
					value={customBatchSizes}
					onChange={(e) => setCustomBatchSizes(e.target.value)}
					disabled={isRunning}
					placeholder="30,30,30,15,15"
					className="w-32 px-2 py-2 bg-zinc-900 border border-terminal-border rounded text-gray-300 text-sm focus:outline-none focus:border-terminal-accent disabled:opacity-50 disabled:cursor-not-allowed text-center"
					title="Custom batch sizes (comma-separated)"
				/>
			</div>

			<div className="flex gap-3 items-center">
				{!isRunning ? (
					<button
						onClick={onRun}
						disabled={!selectedModel || !selectedVariant}
						className="px-6 py-2 bg-terminal-accent text-black rounded text-sm font-semibold whitespace-nowrap hover:bg-green-500 disabled:bg-terminal-border disabled:text-gray-600 disabled:cursor-not-allowed cursor-pointer"
					>
						Run {queueSize}
					</button>
				) : (
					<button
						onClick={onCancel}
						className="px-6 py-2 bg-red-600 text-white rounded text-sm font-semibold whitespace-nowrap hover:bg-red-700 cursor-pointer"
					>
						Cancel
					</button>
				)}
			</div>
		</div>
	);
}
