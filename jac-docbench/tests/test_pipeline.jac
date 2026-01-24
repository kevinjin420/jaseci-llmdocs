"""Tests for pipeline validation and stage logic."""

include:jac pipeline.validator;
include:jac models.stage;
include:jac models.pipeline;
include:jac utils.patterns;

test test_validator_creation {
    """Test Validator object creation with defaults."""
    validator = Validator();

    assert validator.min_size_ratio == 0.1;
    assert validator.required_pattern_ratio == 0.5;
}

test test_validator_validate_empty_output {
    """Test validation of empty output."""
    validator = Validator();

    result = validator.validate("Some input text", "");

    assert result["is_valid"] == False;
    assert "Output is empty" in result["issues"];
}

test test_validator_validate_too_small {
    """Test validation of output that's too small."""
    validator = Validator();

    input_text = "x" * 1000;
    output_text = "y" * 50;

    result = validator.validate(input_text, output_text);

    assert result["is_valid"] == False;
    assert result["size_ratio"] == 0.05;
}

test test_validator_validate_pattern_loss {
    """Test validation when patterns are lost."""
    validator = Validator();

    input_text = '''
node MyNode {
    has value: int;
}

walker MyWalker {
    can walk with entry {
        spawn SubWalker();
    }
}

can process() by llm();
''';

    output_text = '''
node MyNode {
    has value: int;
}
''';

    result = validator.validate(input_text, output_text);

    assert result["is_valid"] == False;
    assert len(result["missing_patterns"]) > 0;
}

test test_validator_validate_success {
    """Test successful validation."""
    validator = Validator();

    text = '''
node MyNode {
    has value: int;
}

walker MyWalker {
    can walk with entry {
        visit [-->];
        spawn SubWalker();
        here ++> target;
        report self.data;
    }
}

can summarize(text: str) -> str
by llm(model=anthropic);
''';

    result = validator.validate(text, text);

    assert result["is_valid"] == True;
    assert result["size_ratio"] == 1.0;
    assert len(result["issues"]) == 0;
}

test test_validator_validate_final {
    """Test final validation with required patterns."""
    validator = Validator();

    valid_text = '''
node Entity {
    has id: str;
}

walker Processor {
    can process with entry {
        spawn Handler();
        here ++> result;
    }
}

can generate() by llm();
''';

    result = validator.validate_final(valid_text);

    assert result["is_valid"] == True;
    assert len(result["missing_patterns"]) == 0;
}

test test_validator_validate_final_missing {
    """Test final validation with missing required patterns."""
    validator = Validator();

    incomplete_text = '''
node Entity {
    has id: str;
}
''';

    result = validator.validate_final(incomplete_text);

    assert result["is_valid"] == False;
    assert len(result["missing_patterns"]) > 0;
}

test test_stage_metrics_creation {
    """Test StageMetrics node creation."""
    stage = StageMetrics(name="fetch");

    assert stage.name == "fetch";
    assert stage.status == StageStatus.PENDING;
    assert stage.start_time is None;
    assert stage.end_time is None;
    assert stage.input_size == 0;
    assert stage.output_size == 0;
}

test test_stage_metrics_lifecycle {
    """Test StageMetrics start/complete lifecycle."""
    stage = StageMetrics(name="extract");

    stage.start();
    assert stage.status == StageStatus.RUNNING;
    assert stage.start_time is not None;
    assert stage.end_time is None;

    stage.complete();
    assert stage.status == StageStatus.COMPLETE;
    assert stage.end_time is not None;

    duration = stage.get_duration();
    assert duration is not None;
    assert duration >= 0;
}

test test_stage_metrics_failure {
    """Test StageMetrics failure handling."""
    stage = StageMetrics(name="assemble");

    stage.start();
    stage.fail("Connection error");

    assert stage.status == StageStatus.ERROR;
    assert stage.error_message == "Connection error";
    assert stage.end_time is not None;
}

test test_stage_metrics_progress {
    """Test StageMetrics progress tracking."""
    stage = StageMetrics(name="fetch");

    stage.start();
    stage.update_progress(5, 10, "Processing file 5 of 10");

    assert stage.progress == 5;
    assert stage.progress_total == 10;
    assert stage.progress_message == "Processing file 5 of 10";
}

test test_stage_metrics_compression_ratio {
    """Test StageMetrics compression ratio calculation."""
    stage = StageMetrics(name="assemble");

    stage.input_size = 100000;
    stage.output_size = 5000;

    ratio = stage.get_compression_ratio();
    assert ratio == 0.05;
}

test test_stage_metrics_to_dict {
    """Test StageMetrics serialization."""
    stage = StageMetrics(name="fetch");
    stage.input_size = 10000;
    stage.output_size = 5000;
    stage.file_count = 15;

    d = stage.to_dict();

    assert d["name"] == "fetch";
    assert d["input_size"] == 10000;
    assert d["output_size"] == 5000;
    assert d["file_count"] == 15;
    assert d["compression_ratio"] == 0.5;
}

test test_stage_metrics_reset {
    """Test StageMetrics reset functionality."""
    stage = StageMetrics(name="extract");

    stage.start();
    stage.input_size = 5000;
    stage.output_size = 2000;
    stage.complete();

    stage.reset();

    assert stage.status == StageStatus.PENDING;
    assert stage.start_time is None;
    assert stage.end_time is None;
    assert stage.input_size == 0;
    assert stage.output_size == 0;
}

test test_pipeline_state_creation {
    """Test PipelineState node creation."""
    pipeline = PipelineState();

    assert pipeline.is_running == False;
    assert pipeline.overall_start is None;
    assert pipeline.overall_end is None;
    assert pipeline.current_stage is None;
    assert pipeline.error is None;
}

test test_pipeline_state_lifecycle {
    """Test PipelineState start/complete lifecycle."""
    pipeline = PipelineState();

    pipeline.start();
    assert pipeline.is_running == True;
    assert pipeline.overall_start is not None;
    assert pipeline.error is None;

    validation = {"is_valid": True, "issues": []};
    pipeline.complete(validation);

    assert pipeline.is_running == False;
    assert pipeline.overall_end is not None;
    assert pipeline.final_validation == validation;

    duration = pipeline.get_duration();
    assert duration is not None;
    assert duration >= 0;
}

test test_pipeline_state_failure {
    """Test PipelineState failure handling."""
    pipeline = PipelineState();

    pipeline.start();
    pipeline.set_stage("fetch");
    pipeline.fail("Network error");

    assert pipeline.is_running == False;
    assert pipeline.error == "Network error";
    assert pipeline.current_stage is None;
}

test test_pipeline_state_to_dict {
    """Test PipelineState serialization."""
    pipeline = PipelineState();

    pipeline.start();
    pipeline.set_stage("extract");

    d = pipeline.to_dict();

    assert d["is_running"] == True;
    assert d["current_stage"] == "extract";
    assert d["overall_start"] is not None;
}
