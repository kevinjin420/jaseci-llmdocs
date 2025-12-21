export interface Model {
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
	top_provider?: {
		max_completion_tokens?: number;
	};
}

export interface Variant {
	name: string;
	url: string;
	size_bytes: number;
	size_kb: number;
}

export interface TestFile {
	name: string;
	path: string;
	size: number;
	modified: number;
	evaluation_status?: "pending" | "evaluating" | "completed" | "failed";
	metadata?: {
		model: string;
		model_full: string;
		variant: string;
		total_tests: string;
		batch_size?: number;
		num_batches?: number;
	};
}

export interface Stash {
	name: string;
	path: string;
	file_count: number;
	created: number;
	metadata?: {
		model: string;
		model_full: string;
		variant: string;
		total_tests: string;
		batch_size?: number;
	};
}

export interface BatchStatus {
	status: "pending" | "running" | "completed" | "failed";
	retry: number;
	max_retries: number;
}

export interface BenchmarkStatus {
	status: "idle" | "running" | "evaluating" | "completed" | "failed";
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
	batch_statuses?: Record<string, BatchStatus>;
	evaluating_count?: number;
	total_evaluations?: number;
	completed_evaluations?: number;
	evaluation_statuses?: Record<string, "pending" | "running" | "completed" | "failed">;
}

export const API_BASE = "http://localhost:5050/api";
export const WS_BASE = "http://localhost:5050";

export const MODEL_DISPLAY_NAMES: Record<string, string> = {
	"claude-sonnet": "Claude Sonnet 4.5",
	"claude-opus": "Claude Opus 4",
	"claude-haiku": "Claude Haiku 3.5",
	"gemini-flash": "Gemini 2.0 Flash",
	"gemini-pro": "Gemini 2.5 Pro",
	"gpt-4": "GPT-4o",
	"gpt-4-mini": "GPT-4o Mini",
	"o1": "O1",
	"o1-mini": "O1 Mini",
};
