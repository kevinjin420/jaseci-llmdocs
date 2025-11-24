import type { Model, Variant } from "@/utils/types";

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
	smallSuite: boolean;
	setSmallSuite: (small: boolean) => void;
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
	smallSuite,
	setSmallSuite,
	isRunning,
	onRun,
	onCancel,
}: Props) {
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
		return parseInt(b.substring(1)) - parseInt(a.substring(1));
	});

	const isImageModel = (m: Model) => {
		const id = m.id.toLowerCase();
		const name = m.name.toLowerCase();
		if (id.includes("image") || name.includes("image")) return true;
		const outputs = m.architecture?.output_modalities || [];
		return outputs.includes("image") && !outputs.includes("text");
	};

	const textModels = models.filter((m) => !isImageModel(m));
	const findModel = (patterns: string[], exclude: string[] = []) =>
		textModels.find((m) =>
			patterns.every((p) => m.id.includes(p)) &&
			exclude.every((e) => !m.id.includes(e))
		);
	const popular = [
		findModel(["claude", "sonnet"]),
		findModel(["claude", "haiku"]),
		findModel(["gemini", "pro"]),
		findModel(["gemini", "flash"]),
		findModel(["openai", "gpt-5"]),
		findModel(["openai", "4o-mini"], ["audio", "search"]),
		findModel(["openai", "4o"], ["mini", "audio", "search"]),
	].filter(Boolean) as Model[];
	const otherModels = textModels.filter((m) => !popular.includes(m));

	return (
		<div className="flex gap-3 items-center justify-between">
			<div className="flex gap-3 items-center flex-wrap">
				<select
					value={selectedModel}
					onChange={(e) => setSelectedModel(e.target.value)}
					disabled={isRunning}
					className="flex-1 max-w-[400px] px-3 py-2 bg-zinc-900 border border-terminal-border rounded text-gray-300 text-sm min-w-[120px] focus:outline-none focus:border-terminal-accent disabled:opacity-50 disabled:cursor-not-allowed"
				>
					<optgroup label="Popular">
						{popular.map((m) => (
							<option key={m.id} value={m.id}>
								{m.name}
							</option>
						))}
					</optgroup>
					<optgroup label="All Models">
						{otherModels.map((m) => (
							<option key={m.id} value={m.id}>
								{m.name}
							</option>
						))}
					</optgroup>
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
								<option key={v.name} value={v.name} className="bg-zinc-900 text-gray-300">
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
					disabled={isRunning}
					className="w-16 px-2 py-2 bg-zinc-900 border border-terminal-border rounded text-gray-300 text-sm focus:outline-none focus:border-terminal-accent disabled:opacity-50 disabled:cursor-not-allowed text-center"
					title="Tests per batch"
				/>

				<label className="flex items-center gap-2 px-3 py-2 bg-zinc-900 border border-terminal-border rounded text-gray-300 text-sm cursor-pointer hover:border-gray-600">
					<input
						type="checkbox"
						checked={smallSuite}
						onChange={(e) => setSmallSuite(e.target.checked)}
						disabled={isRunning}
						className="cursor-pointer"
					/>
					<span>Small Suite</span>
				</label>
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
