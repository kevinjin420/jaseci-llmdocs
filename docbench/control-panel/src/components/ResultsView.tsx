interface Props {
	results: any;
}

export default function ResultsView({ results }: Props) {
	if (!results) {
		return (
			<div className="bg-terminal-surface border border-terminal-border rounded p-6 overflow-y-auto">
				<div className="flex items-center justify-center h-full text-gray-600 text-base">
					<p>Select a test file to view results</p>
				</div>
			</div>
		);
	}

	const downloadCsv = () => {
		if (!results?.summary?.category_breakdown) return;

		const headers = [
			"Test ID",
			"Category",
			"Level",
			"Score",
			"Max Score",
			"Percentage",
			"Required Penalty",
			"Forbidden Penalty",
			"Syntax Penalty",
			"Jac Check Penalty",
		];

		const rows: (string | number)[][] = [];
		Object.values(results.summary.category_breakdown).forEach((category: any) => {
			if (category.tests) {
				category.tests.forEach((test: any) => {
					const penalties = test.score_breakdown || {};
					rows.push([
						test.test_id,
						test.category,
						test.level,
						test.score,
						test.max_score,
						test.percentage + "%",
						penalties.required || 0,
						penalties.forbidden || 0,
						penalties.syntax || 0,
						penalties.jac_check || 0,
					]);
				});
			}
		});

		const csvContent =
			"data:text/csv;charset=utf-8," +
			[headers.join(","), ...rows.map((e) => e.join(","))].join("\n");

		const encodedUri = encodeURI(csvContent);
		const link = document.createElement("a");
		link.setAttribute("href", encodedUri);
		link.setAttribute("download", `${results.run_id || "benchmark"}_results.csv`);
		document.body.appendChild(link);
		link.click();
		document.body.removeChild(link);
	};

	// Calculate total penalties for the summary display
	const totalPenaltyBreakdown = {
		required: 0,
		forbidden: 0,
		syntax: 0,
		jac_check: 0,
		functional: 0,
	};
	
	if (!results.results && results.summary && results.summary.category_breakdown) {
		Object.values(results.summary.category_breakdown).forEach((category: any) => {
			if (category.penalties) {
				totalPenaltyBreakdown.required += category.penalties.required || 0;
				totalPenaltyBreakdown.forbidden += category.penalties.forbidden || 0;
				totalPenaltyBreakdown.syntax += category.penalties.syntax || 0;
				totalPenaltyBreakdown.jac_check += category.penalties.jac_check || 0;
				totalPenaltyBreakdown.functional += category.penalties.functional || 0;
			}
		});
	}

	const totalMaxPoints = results.summary?.total_max || 1; // Prevent division by zero
	const totalPenaltyPercentages = {
		required: (totalPenaltyBreakdown.required / totalMaxPoints) * 100,
		forbidden: (totalPenaltyBreakdown.forbidden / totalMaxPoints) * 100,
		syntax: (totalPenaltyBreakdown.syntax / totalMaxPoints) * 100,
		jac_check: (totalPenaltyBreakdown.jac_check / totalMaxPoints) * 100,
		functional: (totalPenaltyBreakdown.functional / totalMaxPoints) * 100,
	};

	return (
		<div className="bg-terminal-surface border border-terminal-border rounded p-6 overflow-y-auto">
			{!results.results && results.summary && (
				<>
					<div className="flex justify-end mb-4">
						<button
							onClick={downloadCsv}
							className="px-3 py-1.5 bg-zinc-800 border border-terminal-border rounded text-xs text-gray-300 hover:bg-zinc-700 hover:text-white transition-colors flex items-center gap-2"
							title="Download results as CSV"
						>
							<svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
							</svg>
							Download CSV
						</button>
					</div>

					<div className="grid grid-cols-[auto_1fr] gap-8 p-6 bg-zinc-900 rounded mb-6 items-center">
						<div className="relative w-25 h-25">
							<svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
								<circle cx="50" cy="50" r="45" fill="none" stroke="#333" strokeWidth="6" />
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
										strokeDashoffset: 283 - (283 * results.summary.overall_percentage) / 100,
									}}
								/>
							</svg>
							<div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 text-center">
								<span className="block text-2xl font-bold text-terminal-accent">
									{results.summary.overall_percentage.toFixed(1)}%
								</span>
								<span className="block text-xs text-gray-400 uppercase">Score</span>
							</div>
						</div>

						<div className="grid grid-cols-2 gap-3 w-full">
							<div className="flex justify-between px-3 py-2 bg-terminal-surface rounded border-l-2 border-terminal-accent">
								<span className="text-gray-400 text-sm">Total Score</span>
								<span className="text-terminal-accent font-semibold text-sm">
									{results.summary.total_score} / {results.summary.total_max}
								</span>
							</div>
							<div className="flex justify-between px-3 py-2 bg-terminal-surface rounded border-l-2 border-terminal-accent">
								<span className="text-gray-400 text-sm">Tests</span>
								<span className="text-terminal-accent font-semibold text-sm">
									{results.summary.tests_completed}
								</span>
							</div>
							{results.batch_size && (
								<div className="flex justify-between px-3 py-2 bg-terminal-surface rounded border-l-2 border-terminal-accent">
									<span className="text-gray-400 text-sm">Batch Size</span>
									<span className="text-terminal-accent font-semibold text-sm">
										{results.batch_size} ({results.num_batches} batches)
									</span>
								</div>
							)}
							{results.temperature !== undefined && (
								<div className="flex justify-between px-3 py-2 bg-terminal-surface rounded border-l-2 border-terminal-accent">
									<span className="text-gray-400 text-sm">Temperature</span>
									<span className="text-terminal-accent font-semibold text-sm">
										{results.temperature}
									</span>
								</div>
							)}
							{results.max_tokens && (
								<div className="flex justify-between px-3 py-2 bg-terminal-surface rounded border-l-2 border-terminal-accent">
									<span className="text-gray-400 text-sm">Max Tokens</span>
									<span className="text-terminal-accent font-semibold text-sm">
										{results.max_tokens}
									</span>
								</div>
							)}
							{results.model && (
								<div className="flex justify-between px-3 py-2 bg-terminal-surface rounded border-l-2 border-terminal-accent">
									<span className="text-gray-400 text-sm">Model</span>
									<span className="text-terminal-accent font-semibold text-sm truncate ml-2" title={results.model_id}>
										{results.model}
									</span>
								</div>
							)}
							{results.variant && (
								<div className="flex justify-between px-3 py-2 bg-terminal-surface rounded border-l-2 border-terminal-accent">
									<span className="text-gray-400 text-sm">Variant</span>
									<span className="text-terminal-accent font-semibold text-sm">
										{results.variant}
									</span>
								</div>
							)}
							{results.created_at && (
								<div className="flex justify-between px-3 py-2 bg-terminal-surface rounded border-l-2 border-terminal-accent">
									<span className="text-gray-400 text-sm">Created</span>
									<span className="text-terminal-accent font-semibold text-sm">
										{new Date(results.created_at * 1000).toLocaleString()}
									</span>
								</div>
							)}
						</div>
					</div>

					<div className="mb-6">
						<h3 className="text-terminal-accent text-base mb-4 pb-2 border-b border-terminal-border">
							Penalty Breakdown
						</h3>
						<div className="grid grid-cols-2 gap-3">
							{Object.entries(totalPenaltyPercentages).map(([key, value]) => {
								const label = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
								let colorClass = 'text-gray-400'; // Default color

								if (value === 0) {
									colorClass = 'text-terminal-accent'; // Green for 0% loss
								} else if (value > 0 && value <= 5) {
									colorClass = 'text-yellow-400'; // Yellow for low loss
								} else if (value > 5 && value <= 15) {
									colorClass = 'text-orange-400'; // Orange for medium loss
								} else {
									colorClass = 'text-red-400'; // Red for high loss
								}
								
								return (
									<div key={key} className="flex justify-between px-3 py-2 bg-zinc-900 rounded border-l-2 border-terminal-border">
										<span className="text-gray-400 text-sm">{label} Lost</span>
										<span className={`${colorClass} font-semibold text-sm`}>-{value.toFixed(1)}%</span>
									</div>
								);
							})}
							{Object.values(totalPenaltyPercentages).every(v => v === 0) && (
								<div className="col-span-2 text-center text-gray-500 text-sm py-2">No penalties applied!</div>
							)}
						</div>
					</div>

					<BreakdownSection
						title="Category Breakdown"
						data={results.summary.category_breakdown}
					/>
					<BreakdownSection
						title="Difficulty Levels"
						data={results.summary.level_breakdown}
						sortByLevel
					/>
				</>
			)}

			{results.results && (
				<div>
					<h3 className="text-terminal-accent text-base mb-4">Multi-Variant Comparison</h3>
					<div className="grid grid-cols-[repeat(auto-fit,minmax(150px,1fr))] gap-3">
						{Object.entries(results.results).map(([variant, data]: [string, any]) => (
							<div
								key={variant}
								className="bg-zinc-900 p-4 rounded border border-terminal-border text-center"
							>
								<div className="text-gray-400 text-xs uppercase mb-2">{variant}</div>
								<div className="text-3xl font-bold text-terminal-accent mb-1">
									{data.summary.overall_percentage.toFixed(1)}%
								</div>
								<div className="flex flex-col gap-0.5 text-xs text-gray-500">
									<span>
										{data.summary.total_score} / {data.summary.total_max}
									</span>
									<span>{data.file_size} bytes</span>
								</div>
							</div>
						))}
					</div>
				</div>
			)}
		</div>
	);
}

function BreakdownSection({
	title,
	data,
	sortByLevel,
}: {
	title: string;
	data: Record<string, any>;
	sortByLevel?: boolean;
}) {
	if (!data) return null;

	let entries = Object.entries(data);
	if (sortByLevel) {
		entries = entries.sort(([a], [b]) => {
			const numA = parseInt(a.replace(/\D/g, ""));
			const numB = parseInt(b.replace(/\D/g, ""));
			return numA - numB;
		});
	}

	return (
		<div className="mb-6">
			<h3 className="text-terminal-accent text-base mb-4 pb-2 border-b border-terminal-border">
				{title}
			</h3>
			<div className="flex flex-col gap-3">
				{entries.map(([name, item]: [string, any]) => (
					<div key={name} className="bg-zinc-900 p-3 rounded border border-terminal-border">
						<div className="flex justify-between mb-2">
							<span className="text-gray-300 text-sm">{name}</span>
							<span className="text-terminal-accent text-xs">
								{item.score.toFixed(2)} / {item.max} ({item.percentage.toFixed(1)}%)
							</span>
						</div>
						<div className="h-1.5 bg-terminal-border rounded overflow-hidden mb-1">
							<div
								className="h-full bg-terminal-accent transition-all duration-500"
								style={{ width: `${item.percentage}%` }}
							/>
						</div>
						
						{item.penalties && (
							<div className="mt-2 pt-2 border-t border-zinc-800 flex flex-wrap gap-x-4 gap-y-1 text-[10px] text-gray-500">
								<span className="font-semibold">Penalties:</span>
								{item.penalties.jac_check > 0 && (
									<span className="text-red-400" title="Failed 'jac check' compilation">
										Jac Check: -{item.penalties.jac_check.toFixed(1)}
									</span>
								)}
								{item.penalties.syntax > 0 && (
									<span className="text-orange-400" title="Basic syntax errors detected">
										Syntax: -{item.penalties.syntax.toFixed(1)}
									</span>
								)}
								{item.penalties.required > 0 && (
									<span className="text-yellow-400" title="Missing required elements">
										Missing: -{item.penalties.required.toFixed(1)}
									</span>
								)}
								{item.penalties.forbidden > 0 && (
									<span className="text-red-400" title="Used forbidden elements">
										Forbidden: -{item.penalties.forbidden.toFixed(1)}
									</span>
								)}
								{Object.values(item.penalties).every((v: any) => v <= 0) && (
									<span className="text-green-500">None</span>
								)}
							</div>
						)}

						<div className="flex justify-end text-xs text-gray-500 mt-1">{item.count} tests</div>
					</div>
				))}
			</div>
		</div>
	);
}
