import re
import string
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter
from .llm import LLM

try:
    import spacy
    NLP_AVAILABLE = True
except ImportError:
    NLP_AVAILABLE = False


class AcronymMapper:
    """Maps frequent terms to single-letter or short aliases for compression."""

    JAC_ALIASES = {
        'walker': 'W',
        'node': 'N',
        'edge': 'E',
        'graph': 'G',
        'ability': 'A',
        'spawn': 'S',
        'visit': 'V',
        'report': 'R',
        'entry': 'EN',
        'exit': 'EX',
        'here': 'H',
        'self': 'SL',
        'root': 'RT',
        'async': 'AS',
        'await': 'AW',
        'import': 'I',
        'object': 'O',
        'function': 'F',
        'parameter': 'P',
        'return': 'RE',
        'string': 'str',
        'integer': 'int',
        'boolean': 'bool',
        'dictionary': 'dict',
        'list': 'lst',
        'tuple': 'tpl',
        'None': 'nil',
        'True': 'T',
        'False': 'F',
        'example': 'ex',
        'definition': 'def',
        'declaration': 'decl',
        'expression': 'expr',
        'statement': 'stmt',
        'variable': 'var',
        'constant': 'const',
        'attribute': 'attr',
        'method': 'mth',
        'class': 'cls',
        'instance': 'inst',
        'reference': 'ref',
        'pointer': 'ptr',
        'traversal': 'trav',
        'connection': 'conn',
        'relationship': 'rel',
    }

    def __init__(self):
        self.custom_aliases = {}
        self.term_freq = Counter()

    def build_from_corpus(self, texts, min_freq=5, max_aliases=50):
        """Build custom aliases from corpus frequency analysis."""
        words = []
        for text in texts:
            words.extend(re.findall(r'\b[a-zA-Z]{6,}\b', text.lower()))

        self.term_freq = Counter(words)

        existing = set(self.JAC_ALIASES.keys())
        candidates = [
            (word, count) for word, count in self.term_freq.most_common(200)
            if word not in existing and count >= min_freq
        ]

        alias_chars = list(string.ascii_lowercase)
        used = set(v.lower() for v in self.JAC_ALIASES.values())

        for word, _ in candidates[:max_aliases]:
            for i in range(1, min(4, len(word))):
                alias = word[:i]
                if alias not in used:
                    self.custom_aliases[word] = alias
                    used.add(alias)
                    break

    def get_alias_map(self):
        """Get combined alias map with legend."""
        combined = {**self.JAC_ALIASES, **self.custom_aliases}
        return combined

    def get_legend(self):
        """Generate compact legend for output header."""
        combined = self.get_alias_map()
        items = [f"{v}={k}" for k, v in sorted(combined.items(), key=lambda x: x[1])]
        return "ALIASES:" + ",".join(items)


class SemanticSkeletonizer:
    """Strips grammatical glue, preserves semantic core."""

    STOP_WORDS = {
        'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
        'should', 'may', 'might', 'must', 'shall', 'can', 'this', 'that',
        'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they',
        'what', 'which', 'who', 'whom', 'when', 'where', 'why', 'how',
        'all', 'each', 'every', 'both', 'few', 'more', 'most', 'other',
        'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so',
        'than', 'too', 'very', 'just', 'also', 'now', 'here', 'there',
        'then', 'once', 'if', 'or', 'and', 'but', 'because', 'as', 'until',
        'while', 'of', 'at', 'by', 'for', 'with', 'about', 'against',
        'between', 'into', 'through', 'during', 'before', 'after', 'above',
        'below', 'to', 'from', 'up', 'down', 'in', 'out', 'on', 'off',
        'over', 'under', 'again', 'further', 'let', 'lets', "let's",
        'see', 'look', 'consider', 'note', 'notice', 'following', 'below',
        'above', 'example', 'shows', 'demonstrates', 'illustrates',
    }

    FILLER_PATTERNS = [
        r"let'?s\s+(see|look|consider|explore)",
        r"here\s+(we|is|are)",
        r"now\s+(we|let's)",
        r"in\s+this\s+(section|example|case)",
        r"as\s+(you\s+can\s+see|shown|mentioned)",
        r"note\s+that",
        r"it\s+is\s+(important|worth|useful)\s+to",
        r"for\s+example",
        r"such\s+as",
        r"in\s+order\s+to",
        r"make\s+sure\s+to",
        r"keep\s+in\s+mind",
        r"the\s+following",
    ]

    def __init__(self):
        self.nlp = None
        if NLP_AVAILABLE:
            try:
                self.nlp = spacy.load("en_core_web_sm")
            except OSError:
                pass

    def strip_fillers(self, text):
        """Remove filler phrases."""
        result = text
        for pattern in self.FILLER_PATTERNS:
            result = re.sub(pattern, '', result, flags=re.IGNORECASE)
        return result

    def extract_semantic_tokens(self, text):
        """Extract high-value nouns and verbs using NLP."""
        if self.nlp is None:
            return self._fallback_extraction(text)

        doc = self.nlp(text[:100000])
        tokens = []

        for token in doc:
            if token.pos_ in ('NOUN', 'PROPN', 'VERB') and not token.is_stop:
                tokens.append(token.lemma_.lower())
            elif token.pos_ == 'NUM':
                tokens.append(token.text)

        return tokens

    def _fallback_extraction(self, text):
        """Fallback when spaCy unavailable: keep non-stopwords."""
        words = re.findall(r'\b[a-zA-Z0-9_]+\b', text.lower())
        return [w for w in words if w not in self.STOP_WORDS and len(w) > 2]

    def skeletonize(self, text):
        """Convert prose to skeleton form."""
        lines = text.split('\n')
        result = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            if stripped.startswith('```') or stripped.startswith('#'):
                result.append(stripped)
                continue

            if re.match(r'^[\s`\-\*]', line) and '`' in line:
                result.append(stripped)
                continue

            cleaned = self.strip_fillers(stripped)
            tokens = self._fallback_extraction(cleaned)

            if tokens:
                result.append(' '.join(tokens[:20]))

        return '\n'.join(result)


class FunctionalNotationConverter:
    """Converts verbose descriptions to functional notation."""

    PATTERNS = [
        (r'(\w+)\s+takes?\s+(?:a\s+)?(\w+)\s+and\s+returns?\s+(?:a\s+)?(\w+)',
         r'\1(\2)->\3'),
        (r'(\w+)\s+accepts?\s+(\w+(?:\s*,\s*\w+)*)\s+as\s+(?:parameters?|arguments?)',
         r'\1(\2)'),
        (r'call(?:ing)?\s+(\w+)\s+with\s+(\w+)',
         r'\1(\2)'),
        (r'(\w+)\s+(?:is\s+)?connect(?:ed|s)?\s+to\s+(\w+)\s+(?:via|using|with)\s+(\w+)',
         r'\1--\3-->\2'),
        (r'(\w+)\s+(?:has|contains?)\s+(?:a\s+)?(\w+)\s+(?:property|attribute|field)',
         r'\1.has(\2)'),
        (r'spawn(?:ing|s)?\s+(?:a\s+)?(\w+)\s+(?:walker\s+)?(?:at|on|from)\s+(\w+)',
         r'S(\1)@\2'),
        (r'visit(?:ing|s)?\s+(?:all\s+)?(\w+)\s+nodes?',
         r'V(\1)'),
        (r'report(?:ing|s)?\s+(\w+)',
         r'R(\1)'),
        (r'the\s+(\w+)\s+(?:method|function|ability)\s+(?:of\s+)?(\w+)',
         r'\2.\1()'),
        (r'POST\s+(?:to\s+)?(/[\w/{}]+)',
         r'POST\1'),
        (r'GET\s+(?:from\s+)?(/[\w/{}]+)',
         r'GET\1'),
        (r'returns?\s+(?:a\s+)?(\w+)\s+(?:object|value|result)',
         r'->\1'),
    ]

    def convert(self, text):
        """Apply functional notation conversions."""
        result = text
        for pattern, replacement in self.PATTERNS:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        return result


class ByteOptimizer:
    """Optional byte-level compression tricks."""

    @staticmethod
    def strip_vowels(text, preserve_first=True):
        """Strip vowels from words (preserve code blocks)."""
        def process_word(word):
            if len(word) <= 3:
                return word
            if preserve_first:
                return word[0] + re.sub(r'[aeiouAEIOU]', '', word[1:])
            return re.sub(r'[aeiouAEIOU]', '', word)

        parts = re.split(r'(```[\s\S]*?```|`[^`]+`)', text)
        result = []
        for i, part in enumerate(parts):
            if i % 2 == 1:
                result.append(part)
            else:
                words = re.split(r'(\s+)', part)
                result.append(''.join(
                    process_word(w) if re.match(r'^[a-zA-Z]+$', w) else w
                    for w in words
                ))
        return ''.join(result)

    @staticmethod
    def camel_case_compress(text):
        """Compress multi-word phrases to CamelCase."""
        def to_camel(match):
            words = match.group(0).split()
            return ''.join(w.capitalize() for w in words)

        result = re.sub(r'\b([a-z]+\s+){2,}[a-z]+\b', to_camel, text)
        return result

    @staticmethod
    def collapse_whitespace(text):
        """Collapse multiple spaces/newlines."""
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()


class Reducer:
    """Semantic density encoder for 50x documentation compression."""

    def __init__(self, llm: LLM, config: dict, on_progress=None):
        self.llm = llm
        self.on_progress = on_progress or (lambda *a: None)
        self.in_dir = Path(config.get('merge', {}).get('output_dir', 'output/2_merged'))
        self.out_dir = Path(config.get('hierarchical_merge', {}).get('output_dir', 'output/3_hierarchical'))
        self.out_dir.mkdir(parents=True, exist_ok=True)

        hier_cfg = config.get('hierarchical_merge', {})
        self.target_ratio = hier_cfg.get('target_ratio', 50)
        self.enable_vowel_strip = hier_cfg.get('vowel_strip', False)
        self.enable_camel_case = hier_cfg.get('camel_case', False)
        self.max_workers = hier_cfg.get('max_workers', 8)

        self.acronym_mapper = AcronymMapper()
        self.skeletonizer = SemanticSkeletonizer()
        self.fn_converter = FunctionalNotationConverter()
        self.byte_optimizer = ByteOptimizer()

        root = Path(__file__).parents[2]
        prompt_path = root / "config/stage3_reduce_prompt.txt"
        with open(prompt_path) as f:
            self.teacher_prompt = f.read()

    def run(self, ratio=None):
        """Execute semantic density encoding pipeline."""
        self.out_dir.mkdir(parents=True, exist_ok=True)
        files = sorted(self.in_dir.glob("*.txt"))
        if not files:
            return None

        contents = [f.read_text() for f in files]
        total_input = sum(len(c) for c in contents)

        total_steps = 6
        step = 0

        self.on_progress(step, total_steps, "Building acronym map...")
        self.acronym_mapper.build_from_corpus(contents)
        step += 1

        self.on_progress(step, total_steps, "Semantic skeletonization...")
        skeletonized = []
        for content in contents:
            skel = self.skeletonizer.skeletonize(content)
            skeletonized.append(skel)
        step += 1

        self.on_progress(step, total_steps, "Converting to functional notation...")
        functional = []
        for content in skeletonized:
            fn = self.fn_converter.convert(content)
            functional.append(fn)
        step += 1

        self.on_progress(step, total_steps, "Teacher LLM distillation...")
        distilled = self._parallel_distill(functional)
        step += 1

        self.on_progress(step, total_steps, "Applying acronym compression...")
        compressed = self._apply_acronyms('\n\n'.join(distilled))
        step += 1

        self.on_progress(step, total_steps, "Byte-level optimization...")
        if self.enable_vowel_strip:
            compressed = self.byte_optimizer.strip_vowels(compressed)
        if self.enable_camel_case:
            compressed = self.byte_optimizer.camel_case_compress(compressed)
        compressed = self.byte_optimizer.collapse_whitespace(compressed)

        legend = self.acronym_mapper.get_legend()
        final_output = f"{legend}\n---\n{compressed}"

        out_path = self.out_dir / "unified_doc.txt"
        out_path.write_text(final_output)

        total_output = len(final_output)
        achieved_ratio = total_input / max(total_output, 1)

        self.on_progress(total_steps, total_steps,
                        f"Complete: {achieved_ratio:.1f}x reduction")

        intermediate_dir = self.out_dir / "intermediate"
        intermediate_dir.mkdir(exist_ok=True)
        (intermediate_dir / "1_skeletonized.txt").write_text('\n\n---\n\n'.join(skeletonized))
        (intermediate_dir / "2_functional.txt").write_text('\n\n---\n\n'.join(functional))
        (intermediate_dir / "3_distilled.txt").write_text('\n\n---\n\n'.join(distilled))

        return {
            'success': True,
            'output_path': str(out_path),
            'input_size': total_input,
            'output_size': total_output,
            'compression_ratio': achieved_ratio
        }

    def _parallel_distill(self, contents):
        """Use Teacher LLM to distill content into semantic maps."""
        results = [None] * len(contents)

        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            futures = {
                pool.submit(self._distill_single, content, i): i
                for i, content in enumerate(contents)
            }

            for future in as_completed(futures):
                idx = futures[future]
                try:
                    results[idx] = future.result()
                except Exception as e:
                    results[idx] = contents[idx][:1000]

        return [r for r in results if r]

    def _distill_single(self, content, idx):
        """Distill single content chunk via Teacher LLM."""
        if len(content) < 100:
            return content

        try:
            result = self.llm.query(content, self.teacher_prompt)
            return result if result else content[:500]
        except Exception:
            return content[:500]

    def _apply_acronyms(self, text):
        """Apply acronym substitutions."""
        alias_map = self.acronym_mapper.get_alias_map()

        parts = re.split(r'(```[\s\S]*?```)', text)
        result = []

        for i, part in enumerate(parts):
            if i % 2 == 1:
                result.append(part)
            else:
                processed = part
                for term, alias in sorted(alias_map.items(), key=lambda x: -len(x[0])):
                    pattern = rf'\b{re.escape(term)}\b'
                    processed = re.sub(pattern, alias, processed, flags=re.IGNORECASE)
                result.append(processed)

        return ''.join(result)
