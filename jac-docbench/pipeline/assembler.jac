"""Single-pass LLM assembler for Jac documentation using by llm()."""

include:jac pipeline.extractor;
include:jac pipeline.validator;
include:jac config;

import:py from pathlib import Path;

glob llm = Anthropic(model_name="claude-opus-4-5");

obj AssemblyInput {
    """Input structure for LLM assembly."""
    has signatures: str;
    has examples: str;
    has keywords: str;
}

"""You are assembling a concise Jac language reference document.

Given the extracted signatures and examples, create a well-organized reference that:
1. Preserves ALL critical syntax patterns (++>, -->, by llm(), spawn, etc.)
2. Groups related constructs together (nodes/edges, walkers, abilities)
3. Uses minimal prose - let code examples speak for themselves
4. Keeps examples focused and under 20 lines each

The output should be markdown with code blocks marked as ```jac.

CRITICAL: Every pattern in the input MUST appear in the output.
Do not summarize or omit any syntax patterns."""
can assemble_reference(content: str) -> str
by llm(model=llm, temperature=0.0);

obj Assembler {
    has validator: Validator = Validator();
    has prompt_template: str = "";

    can :init: {
        prompt_path = Path("config/assembly_prompt.txt");
        if prompt_path.exists() {
            with open(prompt_path) as f {
                self.prompt_template = f.read();
            }
        }
    }

    can :async: assemble(
        extracted: ExtractedContent,
        extractor: DeterministicExtractor,
        progress_callback: object | None = None
    ) -> str {
        """Assemble final document from extracted content."""
        if progress_callback is not None {
            await progress_callback(0, 3, "Formatting extracted content...");
        }

        formatted_content = extractor.format_for_assembly(extracted);

        if progress_callback is not None {
            await progress_callback(1, 3, "Assembling with LLM (single pass)...");
        }

        result = assemble_reference(formatted_content);

        if not result {
            raise RuntimeError("LLM assembly failed - no output");
        }

        if progress_callback is not None {
            await progress_callback(2, 3, "Validating output...");
        }

        validation = self.validator.validate_final(result);
        if not validation["is_valid"] {
            print(f"Warning: Validation issues: {validation['issues']}");
            if validation["missing_patterns"] {
                print(f"Missing patterns: {validation['missing_patterns'][:5]}");
            }
        }

        if progress_callback is not None {
            await progress_callback(3, 3, "Assembly complete");
        }

        output_dir = Path("output/2_assembled");
        output_dir.mkdir(parents=True, exist_ok=True);
        output_path = output_dir / "reference.txt";
        output_path.write_text(result);

        release_dir = Path("release");
        release_dir.mkdir(exist_ok=True);
        (release_dir / "candidate.txt").write_text(result);

        return result;
    }
}
