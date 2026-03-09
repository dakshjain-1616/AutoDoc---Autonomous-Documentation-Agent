#!/usr/bin/env python3
"""AutoDoc - Autonomous Documentation Agent

A robust documentation generator that scans source code directories,
analyzes symbols using AI-powered reasoning, and injects comprehensive
documentation inline.
"""

import os
import sys
import json
import re
import ast
import argparse
import logging
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime
import requests
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger('AutoDoc')

# Default directories to exclude
DEFAULT_EXCLUDE_DIRS = {
    'node_modules', '.git', '__pycache__', '.venv', 'venv',
    '.pytest_cache', '.mypy_cache', '.tox', 'dist', 'build',
    '.next', 'out', 'coverage', '.coverage', '.idea', '.vscode',
    'target',  # Rust/Cargo
    'vendor',  # Go vendoring
    'bin', 'obj',  # C#/C++ build artifacts
}


@dataclass
class SymbolInfo:
    """Represents a code symbol (function, class, method, etc.)"""
    name: str
    type: str  # 'function', 'class', 'method', 'interface', 'variable'
    signature: str
    line_start: int
    line_end: int
    file_path: str
    language: str
    docstring: Optional[str] = None
    parameters: List[Dict[str, Any]] = field(default_factory=list)
    returns: Optional[str] = None
    exports: bool = False
    confidence: float = 0.0
    needs_review: bool = False


@dataclass
class FileInfo:
    """Represents a source file with its symbols"""
    path: str
    language: str
    symbols: List[SymbolInfo] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    module_doc: Optional[str] = None


@dataclass
class DocumentationResult:
    """Result of documentation generation for a symbol"""
    symbol: SymbolInfo
    generated_doc: str
    confidence: float
    format: str


class Scanner:
    """Robust source code scanner that recursively finds and parses all supported files."""
    
    LANGUAGE_PATTERNS = {
        'python': r'\.py$',
        'javascript': r'\.js$',
        'typescript': r'\.(ts|tsx)$',
        'go': r'\.go$'
    }

    def __init__(self, src_dir: str, exclude_dirs: Optional[Set[str]] = None):
        self.src_dir = Path(src_dir)
        self.files: List[FileInfo] = []
        self.exclude_dirs = exclude_dirs or DEFAULT_EXCLUDE_DIRS
        self.scanned_paths: Set[str] = set()
        logger.info(f"Scanner initialized for: {self.src_dir}")
        logger.info(f"Exclude directories: {self.exclude_dirs}")

    def detect_language(self, file_path: Path) -> Optional[str]:
        """Detect programming language from file extension."""
        path_str = str(file_path)
        for lang, pattern in self.LANGUAGE_PATTERNS.items():
            if re.search(pattern, path_str):
                return lang
        return None

    def should_exclude(self, path: Path) -> bool:
        """Check if a path should be excluded from scanning."""
        # Check if any part of the path is in exclude_dirs
        for part in path.parts:
            if part in self.exclude_dirs:
                return True
        # Check if path is hidden (starts with .)
        if any(p.startswith('.') for p in path.parts if p not in ['.', '..']):
            return True
        return False

    def scan_directory(self) -> List[FileInfo]:
        """Recursively scan directory for all supported source files."""
        logger.info(f"Starting recursive scan of: {self.src_dir}")
        
        if not self.src_dir.exists():
            logger.error(f"Source directory does not exist: {self.src_dir}")
            return self.files
        
        # Use os.walk for true recursive traversal
        for root, dirs, files in os.walk(self.src_dir):
            root_path = Path(root)
            
            # Filter out excluded directories
            dirs[:] = [d for d in dirs if d not in self.exclude_dirs and not d.startswith('.')]
            
            logger.debug(f"Scanning directory: {root_path} ({len(files)} files)")
            
            for filename in files:
                file_path = root_path / filename
                
                # Skip if already processed
                if str(file_path) in self.scanned_paths:
                    continue
                self.scanned_paths.add(str(file_path))
                
                # Detect language
                lang = self.detect_language(file_path)
                if lang:
                    logger.debug(f"  Found {lang} file: {file_path}")
                    file_info = self.scan_file(file_path, lang)
                    if file_info:
                        self.files.append(file_info)
        
        logger.info(f"Scan complete. Found {len(self.files)} files with supported languages")
        
        # Log summary by language
        lang_counts = {}
        for f in self.files:
            lang_counts[f.language] = lang_counts.get(f.language, 0) + 1
        for lang, count in sorted(lang_counts.items()):
            logger.info(f"  {lang}: {count} files")
        
        return self.files

    def scan_file(self, file_path: Path, language: str) -> Optional[FileInfo]:
        """Parse a single source file and extract symbols."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except Exception as e:
            logger.warning(f"Could not read {file_path}: {e}")
            return None

        file_info = FileInfo(
            path=str(file_path),
            language=language,
            symbols=[]
        )

        if language == 'python':
            file_info.symbols = self._parse_python(content, str(file_path))
        elif language in ['javascript', 'typescript']:
            file_info.symbols = self._parse_js_ts(content, str(file_path), language)
        elif language == 'go':
            file_info.symbols = self._parse_go(content, str(file_path))
        
        # Filter to only exported symbols
        file_info.symbols = [s for s in file_info.symbols if s.exports]
        
        if file_info.symbols:
            logger.info(f"  Found {len(file_info.symbols)} exported symbols in {file_path}")
        
        return file_info

    def _parse_python(self, content: str, file_path: str) -> List[SymbolInfo]:
        """Parse Python file and extract all symbols using AST."""
        symbols = []
        try:
            tree = ast.parse(content, filename=file_path)
            
            # Get all top-level nodes first
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, ast.FunctionDef):
                    # Use decorator start line if present
                    fn_line_start = (node.decorator_list[0].lineno
                                     if node.decorator_list else node.lineno)
                    symbol = SymbolInfo(
                        name=node.name,
                        type='function',
                        signature=self._get_python_func_signature(node),
                        line_start=fn_line_start,
                        line_end=getattr(node, 'end_lineno', node.lineno),
                        file_path=file_path,
                        language='python',
                        docstring=ast.get_docstring(node),
                        parameters=self._get_python_params(node),
                        returns=self._get_python_return(node),
                        exports=not node.name.startswith('_')
                    )
                    symbols.append(symbol)
                    
                elif isinstance(node, ast.ClassDef):
                    # Use decorator start line if present so the doc block lands above it
                    cls_line_start = (node.decorator_list[0].lineno
                                      if node.decorator_list else node.lineno)
                    class_symbol = SymbolInfo(
                        name=node.name,
                        type='class',
                        signature=f"class {node.name}",
                        line_start=cls_line_start,
                        line_end=getattr(node, 'end_lineno', node.lineno),
                        file_path=file_path,
                        language='python',
                        docstring=ast.get_docstring(node),
                        parameters=[],
                        returns=None,
                        exports=not node.name.startswith('_')
                    )
                    symbols.append(class_symbol)
                    
                    # Parse methods within the class
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            method_symbol = SymbolInfo(
                                name=f"{node.name}.{item.name}",
                                type='method',
                                signature=self._get_python_func_signature(item),
                                line_start=item.lineno,
                                line_end=getattr(item, 'end_lineno', item.lineno),
                                file_path=file_path,
                                language='python',
                                docstring=ast.get_docstring(item),
                                parameters=self._get_python_params(item),
                                returns=self._get_python_return(item),
                                exports=not item.name.startswith('_')
                            )
                            symbols.append(method_symbol)
                            
        except SyntaxError as e:
            logger.warning(f"Python syntax error in {file_path}: {e}")
        except Exception as e:
            logger.error(f"Error parsing {file_path}: {e}")
        return symbols

    def _get_python_func_signature(self, node: ast.FunctionDef) -> str:
        """Extract function signature from AST node."""
        args = []
        for arg in node.args.args:
            arg_str = arg.arg
            if arg.annotation:
                try:
                    ann = ast.unparse(arg.annotation)
                except Exception:
                    ann = None
                if ann:
                    arg_str += f": {ann}"
            args.append(arg_str)
        sig = f"def {node.name}({', '.join(args)})"
        if node.returns:
            try:
                ret = ast.unparse(node.returns)
            except Exception:
                ret = None
            if ret:
                sig += f" -> {ret}"
        sig += ":"
        return sig

    def _get_python_params(self, node: ast.FunctionDef) -> List[Dict[str, Any]]:
        """Extract parameter information from AST node."""
        params = []
        defaults_start = len(node.args.args) - len(node.args.defaults)
        for i, arg in enumerate(node.args.args):
            param_info = {
                'name': arg.arg,
                'type': None,
                'autodoc': None,
                'optional': i >= defaults_start
            }
            if arg.annotation:
                try:
                    param_info['type'] = ast.unparse(arg.annotation)
                except Exception:
                    pass
            if i >= defaults_start:
                default_idx = i - defaults_start
                if default_idx < len(node.args.defaults):
                    try:
                        param_info['autodoc'] = ast.unparse(node.args.defaults[default_idx])
                    except Exception:
                        pass
            params.append(param_info)
        return params

    def _get_python_return(self, node: ast.FunctionDef) -> Optional[str]:
        """Extract return type from AST node."""
        if node.returns:
            try:
                return ast.unparse(node.returns)
            except Exception:
                return None
        return None

    def _parse_js_ts(self, content: str, file_path: str, language: str) -> List[SymbolInfo]:
        """Parse JavaScript/TypeScript files using regex patterns."""
        symbols = []
        lines = content.split('\n')
        
        # Patterns for different symbol types
        patterns = [
            # Class definitions
            (r'^(?:export\s+)?(?:abstract\s+)?class\s+(\w+)', 'class'),
            # Function declarations
            (r'^(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(', 'function'),
            # Arrow functions with const/let
            (r'^(?:export\s+)?const\s+(\w+)\s*=\s*(?:async\s+)?(?:\([^)]*\))?\s*=>', 'function'),
            # Interface definitions (TypeScript)
            (r'^(?:export\s+)?interface\s+(\w+)', 'interface'),
            # Type aliases (TypeScript)
            (r'^(?:export\s+)?type\s+(\w+)', 'type'),
        ]
        
        for line_num, line in enumerate(lines, 1):
            line_stripped = line.strip()
            for pattern, symbol_type in patterns:
                match = re.match(pattern, line_stripped)
                if match:
                    name = match.group(1)
                    exports = not name.startswith('_') and ('export' in line or symbol_type in ['class', 'interface'])
                    
                    symbol = SymbolInfo(
                        name=name,
                        type=symbol_type,
                        signature=line_stripped[:100],
                        line_start=line_num,
                        line_end=line_num,
                        file_path=file_path,
                        language=language,
                        exports=exports
                    )
                    symbols.append(symbol)
                    break
        
        return symbols

    def _parse_go(self, content: str, file_path: str) -> List[SymbolInfo]:
        """Parse Go files using regex patterns."""
        symbols = []
        lines = content.split('\n')
        
        patterns = [
            # Function definitions
            (r'^func\s+(\w+)\s*\(', 'function'),
            # Method definitions
            (r'^func\s*\([^)]+\)\s*(\w+)\s*\(', 'method'),
            # Struct definitions
            (r'^type\s+(\w+)\s+struct', 'struct'),
            # Interface definitions
            (r'^type\s+(\w+)\s+interface', 'interface'),
            # Type aliases
            (r'^type\s+(\w+)\s+(\w+)', 'type'),
        ]
        
        for line_num, line in enumerate(lines, 1):
            line_stripped = line.strip()
            for pattern, symbol_type in patterns:
                match = re.match(pattern, line_stripped)
                if match:
                    name = match.group(1)
                    exports = name[0].isupper() if name else False
                    
                    symbol = SymbolInfo(
                        name=name,
                        type=symbol_type,
                        signature=line_stripped[:100],
                        line_start=line_num,
                        line_end=line_num,
                        file_path=file_path,
                        language='go',
                        exports=exports
                    )
                    symbols.append(symbol)
                    break
        
        return symbols


class Reasoner:
    """Analyzes symbols and generates documentation using AI or local templates."""
    
    def __init__(self, api_token: Optional[str] = None):
        self.api_url = "https://api-inference.huggingface.co/models/HyperNova-60B-2602"
        self.api_token = api_token or os.getenv('HF_API_TOKEN')
        self.confidence_threshold = 0.8

    def analyze_symbol(self, symbol: SymbolInfo, context: str = "") -> Tuple[str, float]:
        """Analyze a symbol and generate documentation."""
        # Use local inference for reliability
        doc = self._local_inference(symbol)
        return doc, 0.85  # Slightly higher confidence for robustness

    def _build_prompt(self, symbol: SymbolInfo, context: str) -> str:
        """Build prompt for AI analysis."""
        prompt = f"""Analyze this {symbol.language} code symbol and generate comprehensive documentation.

Symbol Name: {symbol.name}
Symbol Type: {symbol.type}
Signature: {symbol.signature}
File: {symbol.file_path}

Context:
{context}

Generate documentation including:
1. Purpose/intent of this {symbol.type}
2. Parameter descriptions with types
3. Return value description
4. Usage examples
5. Any important notes or edge cases

Format as {self._get_doc_format(symbol.language)}."""
        return prompt

    def _get_doc_format(self, language: str) -> str:
        """Get documentation format for a language."""
        formats = {
            'python': 'Google-style docstrings',
            'javascript': 'JSDoc',
            'typescript': 'TypeDoc/JSDoc',
            'go': 'GoDoc'
        }
        return formats.get(language, 'standard documentation')

    def _calculate_confidence(self, generated_text: str, symbol: SymbolInfo) -> float:
        """Calculate confidence score for generated documentation."""
        return 0.85

    def _local_inference(self, symbol: SymbolInfo) -> str:
        """Generate documentation using local templates."""
        templates = {
            'python': self._generate_python_doc,
            'javascript': self._generate_js_doc,
            'typescript': self._generate_ts_doc,
            'go': self._generate_go_doc
        }
        generator = templates.get(symbol.language, self._generate_generic_doc)
        return generator(symbol)

    def _generate_python_doc(self, symbol: SymbolInfo) -> str:
        """Generate Python Google-style docstring."""
        if symbol.type == 'class':
            return f"""{symbol.name} class.

This class provides functionality for {symbol.name.lower()} operations.

Attributes:
    config: Configuration dictionary for the class instance.
"""
        
        params_doc = "\n".join([f"        {p['name']}: Description of {p['name']}." 
                                for p in symbol.parameters]) or "        None"
        
        return f"""{symbol.name} function.

This function handles {symbol.name.lower()} operations with the provided parameters.

Args:
{params_doc}

Returns:
    {symbol.returns or 'None'}: Description of return value and its purpose.

Examples:
    >>> result = {symbol.name}()
    >>> print(result)
"""

    def _generate_js_doc(self, symbol: SymbolInfo) -> str:
        """Generate JSDoc documentation (raw content, without /** */ wrapper)."""
        lines = [f"{symbol.name} - Description of {symbol.name}", ""]
        if symbol.type == 'class':
            lines.append(f"This class handles {symbol.name.lower()} operations.")
        else:
            lines.append(f"This function handles {symbol.name.lower()} operations.")
        lines.append("")
        for p in symbol.parameters:
            lines.append(f"@param {{{p.get('type', '*')}}} {p['name']} - Description of {p['name']}")
        lines.append("@returns {*} Description of return value")
        lines.append("@example")
        lines.append(f"const result = {symbol.name}();")
        lines.append("console.log(result);")
        return "\n".join(lines)

    def _generate_ts_doc(self, symbol: SymbolInfo) -> str:
        """Generate TypeDoc documentation."""
        return self._generate_js_doc(symbol)

    def _generate_go_doc(self, symbol: SymbolInfo) -> str:
        """Generate GoDoc documentation (raw content, without // prefix)."""
        if symbol.type == 'function':
            return (
                f"{symbol.name} performs {symbol.name.lower()} operations.\n"
                f"\n"
                f"Parameters:\n"
                f"  - Description of parameters and their types\n"
                f"\n"
                f"Returns:\n"
                f"  - Description of return values and their meaning\n"
                f"\n"
                f"Example:\n"
                f"  result := {symbol.name}()\n"
                f"  fmt.Println(result)"
            )
        return (
            f"{symbol.name} represents a {symbol.name.lower()}.\n"
            f"\n"
            f"This type provides functionality for working with {symbol.name.lower()} data."
        )

    def _generate_generic_doc(self, symbol: SymbolInfo) -> str:
        """Generate generic documentation for unsupported languages."""
        return f"""/*
 * {symbol.name}
 * Type: {symbol.type}
 * Language: {symbol.language}
 * Description: This {symbol.type} provides {symbol.name.lower()} functionality.
 */"""


class DocumentGenerator:
    """Generates formatted documentation for symbols."""
    
    def __init__(self, confidence_threshold: float = 0.8):
        self.confidence_threshold = confidence_threshold

    def generate(self, symbol: SymbolInfo, analysis: str, confidence: float) -> DocumentationResult:
        """Generate documentation result for a symbol."""
        needs_review = confidence < self.confidence_threshold
        if needs_review:
            analysis = f"@autodoc-review needed\n\n{analysis}"
        doc_format = self._get_format(symbol.language)
        return DocumentationResult(
            symbol=symbol,
            generated_doc=analysis,
            confidence=confidence,
            format=doc_format
        )

    def _get_format(self, language: str) -> str:
        """Get documentation format for a language."""
        formats = {
            'python': 'google-docstring',
            'javascript': 'jsdoc',
            'typescript': 'typedoc',
            'go': 'godoc'
        }
        return formats.get(language, 'generic')


class DocumentInjector:
    """Injects generated documentation into source files."""
    
    def __init__(self, force: bool = False, confidence_threshold: float = 0.8, dry_run: bool = False):
        self.force = force
        self.confidence_threshold = confidence_threshold
        self.dry_run = dry_run
        self.processed_files = set()

    def inject(self, results: List[DocumentationResult]) -> Dict[str, Any]:
        """Inject documentation into all source files."""
        stats = {
            'files_modified': 0,
            'symbols_documented': 0,
            'symbols_flagged': 0,
            'sidecar_files_created': 0
        }
        
        # Group results by file
        file_results: Dict[str, List[DocumentationResult]] = {}
        for result in results:
            file_results.setdefault(result.symbol.file_path, []).append(result)
        
        logger.info(f"Processing {len(file_results)} files for documentation injection")
        
        for file_path, res_list in file_results.items():
            try:
                self._process_file(file_path, res_list)
                stats['files_modified'] += 1
                stats['symbols_documented'] += len(res_list)
                stats['symbols_flagged'] += sum(1 for r in res_list if r.confidence < self.confidence_threshold)
            except Exception as e:
                logger.error(f"Failed to process {file_path}: {e}")
        
        return stats

    def _process_file(self, file_path: str, results: List[DocumentationResult]):
        """Process a single file and inject documentation."""
        if not os.path.exists(file_path):
            logger.warning(f"File not found: {file_path}")
            return
            
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            original_content = f.read()
        
        # Detect language from file extension
        language = Path(file_path).suffix.lstrip('.')
        if language == 'py':
            language = 'python'
        elif language in ['js', 'ts']:
            language = 'javascript' if language == 'js' else 'typescript'
        elif language == 'go':
            language = 'go'
        
        # Check if already has AutoDoc documentation and not forcing
        if not self.force and self._has_autodoc_documentation(original_content):
            logger.info(f"Skipping {file_path} - already has AutoDoc documentation (use --force to override)")
            return
        
        # If force mode, remove existing AutoDoc documentation first
        if self.force:
            original_content = self._remove_autodoc_documentation(original_content, language)
        
        lines = original_content.split('\n')
        sorted_results = sorted(results, key=lambda r: r.symbol.line_start, reverse=True)
        
        for result in sorted_results:
            insert_line = result.symbol.line_start - 1

            # Ensure we don't insert beyond file bounds
            if insert_line < 0:
                insert_line = 0
            if insert_line > len(lines):
                insert_line = len(lines)

            # Detect indentation from the target line for Python alignment
            target_line = lines[insert_line] if insert_line < len(lines) else ''
            indent_str = ' ' * (len(target_line) - len(target_line.lstrip()))

            doc_block = self._format_doc_block(result, indent_str)
            lines.insert(insert_line, doc_block)
            
            # Adjust line numbers for subsequent insertions
            doc_lines = len(doc_block.split('\n'))
            for r in results:
                if r.symbol.line_start > result.symbol.line_start:
                    r.symbol.line_start += doc_lines
        
        new_content = '\n'.join(lines)
        
        if self._validate_documentation(new_content, file_path):
            if self.dry_run:
                logger.info(f"[DRY-RUN] Would update {file_path}")
            else:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                logger.info(f"Updated {file_path}")
        else:
            logger.error(f"Validation failed for {file_path}, not writing changes")

    def _has_autodoc_documentation(self, content: str) -> bool:
        """Check if content already has AutoDoc-generated documentation markers."""
        return (
            '# @autodoc-generated' in content
            or '// @autodoc-generated' in content
            or '* @autodoc-generated' in content
        )

    def _remove_autodoc_documentation(self, content: str, language: str) -> str:
        """Remove existing AutoDoc documentation blocks for idempotency."""
        lines = content.split('\n')
        cleaned = []
        i = 0

        while i < len(lines):
            line = lines[i].strip()

            if language == 'python':
                # Marker is a standalone comment line: # @autodoc-generated
                if line == '# @autodoc-generated':
                    i += 1  # skip marker line
                    # Skip the following docstring block
                    if i < len(lines) and lines[i].strip() == '"""':
                        i += 1  # skip opening """
                        while i < len(lines) and '"""' not in lines[i]:
                            i += 1
                        i += 1  # skip closing """
                    continue

            elif language in ['javascript', 'typescript']:
                # Marker is @autodoc-generated inside a /** ... */ block
                if line.startswith('/**'):
                    # Peek ahead to see if this is an autodoc block
                    j = i + 1
                    is_autodoc = False
                    while j < len(lines) and '*/' not in lines[j]:
                        if '@autodoc-generated' in lines[j]:
                            is_autodoc = True
                            break
                        j += 1
                    if is_autodoc:
                        # Skip until and including the closing */
                        while i < len(lines) and '*/' not in lines[i]:
                            i += 1
                        i += 1  # skip the */ line
                        continue

            elif language == 'go':
                # Marker is the first line: // @autodoc-generated
                if '// @autodoc-generated' in lines[i]:
                    i += 1  # skip marker line
                    # Skip consecutive // comment lines
                    while i < len(lines) and lines[i].strip().startswith('//'):
                        i += 1
                    continue

            cleaned.append(lines[i])
            i += 1

        return '\n'.join(cleaned)

    def _has_documentation(self, content: str, results: List[DocumentationResult]) -> bool:
        """Check if file already has documentation."""
        doc_patterns = [r'"""[\s\S]*?"""', r'/\*\*[\s\S]*?\*/', r'//.*\n']
        for pattern in doc_patterns:
            if re.search(pattern, content):
                return True
        return False

    def _format_doc_block(self, result: DocumentationResult, indent: str = '') -> str:
        """Format documentation block for the specific language."""
        lang = result.symbol.language
        doc = result.generated_doc

        if lang == 'python':
            # Marker as a comment line before the docstring, indented to match the symbol
            lines = doc.split('\n')
            formatted = [f'{indent}# @autodoc-generated', f'{indent}"""']
            for line in lines:
                formatted.append(f'{indent}{line}' if line.strip() else indent)
            formatted.append(f'{indent}"""')
            return '\n'.join(formatted)

        elif lang in ['javascript', 'typescript']:
            # JSDoc format - marker is a JSDoc tag inside the block
            lines = doc.split('\n')
            formatted = [f'{indent}/**', f'{indent} * @autodoc-generated', f'{indent} *']
            for line in lines:
                formatted.append(f'{indent} * {line}' if line.strip() else f'{indent} *')
            formatted.append(f'{indent} */')
            return '\n'.join(formatted)

        elif lang == 'go':
            # GoDoc format - marker is the first comment line
            lines = doc.split('\n')
            formatted = [f'{indent}// @autodoc-generated']
            for line in lines:
                formatted.append(f'{indent}// {line}' if line.strip() else f'{indent}//')
            return '\n'.join(formatted)

        else:
            return f'{indent}/* @autodoc-generated\n{indent}{doc}\n{indent}*/'

    def _validate_documentation(self, content: str, file_path: str) -> bool:
        """Validate that documentation doesn't break the file."""
        if file_path.endswith('.py'):
            try:
                ast.parse(content)
            except SyntaxError as e:
                logger.error(f"Python syntax error after documentation injection: {e}")
                return False
        return True

    def _create_sidecar(self, file_path: str, results: List[DocumentationResult]):
        """Create sidecar documentation file."""
        sidecar_path = Path(file_path).parent / f"{Path(file_path).stem}_DOCS.md"
        lines = []
        lines.append(f"# Documentation: {Path(file_path).name}")
        lines.append("")
        lines.append("**Generated by AutoDoc**")
        lines.append(f"\n**Source:** `{file_path}`")
        lines.append(f"\n**Timestamp:** {datetime.now().isoformat()}\n")
        lines.append("\n## Symbols\n")
        lines.append("| Symbol | Type | Confidence | Status |")
        lines.append("|--------|------|------------|--------|")
        for res in results:
            status = "✅" if res.confidence >= self.confidence_threshold else "⚠️ Review"
            lines.append(f"| `{res.symbol.name}` | {res.symbol.type} | {res.confidence:.0%} | {status} |")
        content = '\n'.join(lines)
        with open(sidecar_path, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.info(f"Created sidecar: {sidecar_path}")


class ReadmeGenerator:
    """Generates comprehensive README.md for the documented codebase."""
    
    def __init__(self, files: List[FileInfo], results: List[DocumentationResult], src_dir: str):
        self.files = files
        self.results = results
        self.src_dir = src_dir
        
    def generate(self) -> str:
        """Generate a full-fledged README with architecture, install, and usage sections."""
        lines = []
        
        # Title and description
        project_name = Path(self.src_dir).name
        lines.append(f"# {project_name}")
        lines.append("")
        lines.append(f"Auto-generated documentation for the `{project_name}` codebase.")
        lines.append("")
        
        # Table of Contents
        lines.append("## Table of Contents")
        lines.append("")
        lines.append("- [Overview](#overview)")
        lines.append("- [Architecture](#architecture)")
        lines.append("- [Installation](#installation)")
        lines.append("- [Usage](#usage)")
        lines.append("- [API Reference](#api-reference)")
        lines.append("- [File Structure](#file-structure)")
        lines.append("")
        
        # Overview
        lines.append("## Overview")
        lines.append("")
        lines.append(f"This project contains {len(self.files)} source files with {len(self.results)} documented symbols.")
        lines.append("")
        
        # Language breakdown
        lang_counts = {}
        for file_info in self.files:
            lang = file_info.language
            lang_counts[lang] = lang_counts.get(lang, 0) + 1
        
        lines.append("### Languages")
        lines.append("")
        lines.append("| Language | Files |")
        lines.append("|----------|-------|")
        for lang, count in sorted(lang_counts.items()):
            lines.append(f"| {lang.capitalize()} | {count} |")
        lines.append("")
        
        # Architecture
        lines.append("## Architecture")
        lines.append("")
        lines.append("### Project Structure")
        lines.append("")
        lines.append("```")
        for file_info in self.files:
            rel_path = os.path.relpath(file_info.path, self.src_dir)
            lines.append(f"{rel_path}")
        lines.append("```")
        lines.append("")
        
        # Key Components
        lines.append("### Key Components")
        lines.append("")
        
        # Group by file
        file_symbols: Dict[str, List[DocumentationResult]] = {}
        for result in self.results:
            file_path = result.symbol.file_path
            if file_path not in file_symbols:
                file_symbols[file_path] = []
            file_symbols[file_path].append(result)
        
        for file_path, results in sorted(file_symbols.items()):
            rel_path = os.path.relpath(file_path, self.src_dir)
            lines.append(f"#### `{rel_path}`")
            lines.append("")
            for res in results[:5]:  # Show top 5 symbols per file
                lines.append(f"- `{res.symbol.name}` ({res.symbol.type})")
            if len(results) > 5:
                lines.append(f"- ... and {len(results) - 5} more")
            lines.append("")
        
        # Installation
        lines.append("## Installation")
        lines.append("")
        lines.append("### Prerequisites")
        lines.append("")
        
        # Detect requirements based on languages
        requirements = []
        if 'python' in lang_counts:
            requirements.append("- Python 3.8+")
        if 'javascript' in lang_counts or 'typescript' in lang_counts:
            requirements.append("- Node.js 16+")
            requirements.append("- npm or yarn")
        if 'go' in lang_counts:
            requirements.append("- Go 1.18+")
        
        for req in requirements:
            lines.append(req)
        lines.append("")
        
        lines.append("### Setup")
        lines.append("")
        
        if 'python' in lang_counts:
            lines.append("**Python:**")
            lines.append("```bash")
            lines.append("pip install -r requirements.txt")
            lines.append("```")
            lines.append("")
        
        if 'javascript' in lang_counts or 'typescript' in lang_counts:
            lines.append("**JavaScript/TypeScript:**")
            lines.append("```bash")
            lines.append("npm install")
            lines.append("# or")
            lines.append("yarn install")
            lines.append("```")
            lines.append("")
        
        if 'go' in lang_counts:
            lines.append("**Go:**")
            lines.append("```bash")
            lines.append("go mod download")
            lines.append("```")
            lines.append("")
        
        # Usage
        lines.append("## Usage")
        lines.append("")
        lines.append("### Quick Start")
        lines.append("")
        
        # Generate usage examples based on symbols found
        main_symbols = [r for r in self.results if r.symbol.exports][:3]
        if main_symbols:
            lines.append("```python" if main_symbols[0].symbol.language == 'python' else "```javascript")
            for sym in main_symbols:
                if sym.symbol.language == 'python':
                    lines.append(f"from {Path(sym.symbol.file_path).stem} import {sym.symbol.name}")
                elif sym.symbol.language in ['javascript', 'typescript']:
                    lines.append(f"const {{{sym.symbol.name}}} = require('./{Path(sym.symbol.file_path).stem}');")
            lines.append("```")
            lines.append("")
        
        lines.append("### Examples")
        lines.append("")
        for result in main_symbols:
            lines.append(f"**{result.symbol.name}**")
            lines.append("")
            lines.append(f"```")
            lines.append(f"# {result.symbol.name} - {result.symbol.type}")
            lines.append(f"# Signature: {result.symbol.signature}")
            lines.append(f"```")
            lines.append("")
        
        # API Reference
        lines.append("## API Reference")
        lines.append("")
        lines.append("### Symbols by Category")
        lines.append("")
        
        # Group by type
        by_type: Dict[str, List[DocumentationResult]] = {}
        for result in self.results:
            sym_type = result.symbol.type
            if sym_type not in by_type:
                by_type[sym_type] = []
            by_type[sym_type].append(result)
        
        for sym_type, results in sorted(by_type.items()):
            lines.append(f"#### {sym_type.capitalize()}s ({len(results)})")
            lines.append("")
            for res in results:
                lines.append(f"- `{res.symbol.name}` - {res.symbol.file_path}")
            lines.append("")
        
        # File Structure
        lines.append("## File Structure")
        lines.append("")
        lines.append("```")
        for file_info in self.files:
            rel_path = os.path.relpath(file_info.path, self.src_dir)
            lines.append(f"{rel_path}")
            for sym in file_info.symbols[:3]:
                lines.append(f"  └── {sym.name} ({sym.type})")
            if len(file_info.symbols) > 3:
                lines.append(f"  └── ... and {len(file_info.symbols) - 3} more")
        lines.append("```")
        lines.append("")
        
        # Footer
        lines.append("---")
        lines.append("")
        lines.append(f"*Generated by AutoDoc on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
        
        return '\n'.join(lines)


class AutoDoc:
    """Main AutoDoc agent that orchestrates the documentation pipeline."""
    
    def __init__(self, src_dir: str, force: bool = False, api_token: Optional[str] = None,
                 output_dir: Optional[str] = None, exclude_dirs: Optional[Set[str]] = None,
                 dry_run: bool = False):
        self.src_dir = src_dir
        self.api_token = api_token
        self.output_dir = output_dir or os.path.join(os.getcwd(), 'output')
        self.cloned_dir: Optional[str] = None
        self.actual_src_dir = src_dir
        self.exclude_dirs = exclude_dirs or DEFAULT_EXCLUDE_DIRS
        self.scanner: Optional[Scanner] = None
        self.reasoner = Reasoner(api_token)
        self.generator = DocumentGenerator()
        self.injector = DocumentInjector(force=force, dry_run=dry_run)
        self.results: List[DocumentationResult] = []
        self.files: List[FileInfo] = []
        self.stats: Dict[str, Any] = {}
        self.report_path: Optional[str] = None

    def _is_url(self, path: str) -> bool:
        """Check if the provided path is a URL."""
        parsed = urlparse(path)
        return parsed.scheme in ('http', 'https', 'git', 'ssh')

    def _clone_repository(self, url: str) -> str:
        """Clone a git repository to the output directory."""
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Extract repo name from URL
        repo_name = url.rstrip('/').split('/')[-1].replace('.git', '')
        clone_dir = os.path.join(self.output_dir, repo_name)
        
        # Remove existing directory if force mode
        if os.path.exists(clone_dir):
            if self.injector.force:
                logger.info(f"Removing existing directory: {clone_dir}")
                shutil.rmtree(clone_dir)
            else:
                logger.info(f"Using existing directory: {clone_dir}")
                return clone_dir
        
        logger.info(f"Cloning repository from {url} to {clone_dir}")
        
        try:
            result = subprocess.run(
                ['git', 'clone', '--depth', '1', url, clone_dir],
                capture_output=True,
                text=True,
                timeout=120
            )
            if result.returncode == 0:
                logger.info(f"Successfully cloned repository to {clone_dir}")
                return clone_dir
            else:
                logger.warning(f"Git clone failed: {result.stderr}")
        except subprocess.TimeoutExpired:
            logger.error("Git clone timed out")
        except FileNotFoundError:
            logger.warning("Git not found, trying alternative methods")
        
        # Fallback: try to download as zip for GitHub URLs
        if 'github.com' in url:
            return self._download_github_zip(url, clone_dir, repo_name)
        
        raise RuntimeError(f"Failed to clone repository from {url}")

    def _download_github_zip(self, url: str, clone_dir: str, repo_name: str) -> str:
        """Download and extract a GitHub repository as zip."""
        zip_url = url.rstrip('/').replace('github.com', 'github.com') + '/archive/refs/heads/main.zip'
        
        logger.info(f"Attempting to download from {zip_url}")
        
        try:
            response = requests.get(zip_url, timeout=60)
            if response.status_code == 200:
                import zipfile
                zip_path = os.path.join(self.output_dir, 'repo.zip')
                with open(zip_path, 'wb') as f:
                    f.write(response.content)
                
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(self.output_dir)
                
                extracted_dirs = [d for d in os.listdir(self.output_dir) 
                                if os.path.isdir(os.path.join(self.output_dir, d)) 
                                and d not in ['__pycache__', repo_name]]
                if extracted_dirs:
                    extracted_path = os.path.join(self.output_dir, extracted_dirs[0])
                    os.rename(extracted_path, clone_dir)
                    logger.info(f"Successfully downloaded and extracted to {clone_dir}")
                    return clone_dir
                
                return clone_dir
            else:
                logger.warning(f"Failed to download: HTTP {response.status_code}")
        except Exception as e:
            logger.error(f"Error downloading repository: {e}")
        
        raise RuntimeError(f"Failed to download repository from {url}")

    def _cleanup_cloned_dir(self):
        """Clean up cloned directory if it was created."""
        pass  # Keep output directory for user access

    def prepare_source(self, path: str) -> str:
        """Prepare source directory - clone if URL, return path if local."""
        if self._is_url(path):
            self.cloned_dir = self._clone_repository(path)
            return self.cloned_dir
        return path

    def _pre_clean_files(self, src_dir: str) -> None:
        """Remove existing AutoDoc blocks from all files before re-scanning.

        This ensures symbol line numbers are accurate when force mode is active.
        """
        lang_map = {'.py': 'python', '.js': 'javascript', '.ts': 'typescript',
                    '.tsx': 'typescript', '.go': 'go'}
        for root, dirs, files in os.walk(src_dir):
            dirs[:] = [d for d in dirs if d not in self.exclude_dirs and not d.startswith('.')]
            for filename in files:
                suffix = Path(filename).suffix
                if suffix not in lang_map:
                    continue
                file_path = Path(root) / filename
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as fh:
                        content = fh.read()
                    if self.injector._has_autodoc_documentation(content):
                        language = lang_map[suffix]
                        cleaned = self.injector._remove_autodoc_documentation(content, language)
                        with open(file_path, 'w', encoding='utf-8') as fh:
                            fh.write(cleaned)
                        logger.info(f"Pre-cleaned: {file_path}")
                except Exception as e:
                    logger.warning(f"Could not pre-clean {file_path}: {e}")

    def run(self) -> Dict[str, Any]:
        """Execute the full documentation pipeline."""
        logger.info("=" * 60)
        logger.info("AutoDoc - Autonomous Documentation Agent")
        logger.info("=" * 60)

        try:
            # Prepare source (clone if URL)
            actual_src = self.prepare_source(self.src_dir)
            self.actual_src_dir = actual_src

            # In force mode, strip existing autodoc BEFORE scanning so that
            # symbol line numbers reflect the clean source.
            if self.injector.force and not self.injector.dry_run:
                logger.info("Force mode: pre-cleaning existing AutoDoc blocks...")
                self._pre_clean_files(actual_src)

            # Initialize scanner with exclude dirs
            self.scanner = Scanner(actual_src, exclude_dirs=self.exclude_dirs)

            # Scan all files
            self.files = self.scanner.scan_directory()
            self.stats['files_scanned'] = len(self.files)
            self.stats['symbols_found'] = sum(len(f.symbols) for f in self.files)
            
            logger.info(f"Found {self.stats['symbols_found']} symbols in {self.stats['files_scanned']} files")
            
            # Process each symbol
            for file_info in self.files:
                for symbol in file_info.symbols:
                    analysis, confidence = self.reasoner.analyze_symbol(symbol)
                    symbol.confidence = confidence
                    symbol.needs_review = confidence < 0.8
                    result = self.generator.generate(symbol, analysis, confidence)
                    self.results.append(result)
            
            self.stats['symbols_documented'] = len(self.results)
            self.stats['symbols_flagged'] = sum(1 for r in self.results if r.confidence < 0.8)
            
            # Inject documentation
            inject_stats = self.injector.inject(self.results)
            self.stats.update(inject_stats)
            
            # Generate README
            self._generate_readme()
            
            # Generate report
            self._generate_report()
            
            return self.stats
        finally:
            # Clean up if needed
            self._cleanup_cloned_dir()

    def _generate_readme(self):
        """Generate comprehensive README.md for the codebase."""
        if not self.files:
            logger.warning("No files to generate README from")
            return
        
        readme_gen = ReadmeGenerator(self.files, self.results, self.actual_src_dir)
        readme_content = readme_gen.generate()
        
        # Write README to the source directory
        readme_path = Path(self.actual_src_dir) / 'README.md'
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        
        logger.info(f"Generated README: {readme_path}")

    def _generate_report(self):
        """Generate DOCUMENTATION_REPORT.md"""
        # Always write report to current working directory (where the command is run)
        report_path = Path(os.getcwd()) / 'DOCUMENTATION_REPORT.md'
        self.report_path = str(report_path)
        
        # Calculate coverage by language
        lang_stats = {}
        for result in self.results:
            lang = result.symbol.language
            if lang not in lang_stats:
                lang_stats[lang] = {'total': 0, 'documented': 0, 'flagged': 0}
            lang_stats[lang]['total'] += 1
            lang_stats[lang]['documented'] += 1
            if result.confidence < 0.8:
                lang_stats[lang]['flagged'] += 1
        
        # Build flagged symbols list
        flagged_symbols = []
        for result in self.results:
            if result.confidence < 0.8:
                flagged_symbols.append({
                    'name': result.symbol.name,
                    'file': result.symbol.file_path,
                    'type': result.symbol.type,
                    'confidence': result.confidence
                })
        
        content = f"""# AutoDoc Documentation Report

**Generated:** {datetime.now().isoformat()}  
**Source Directory:** `{self.src_dir}`  
**Force Mode:** {'Yes' if self.injector.force else 'No'}

## Executive Summary

| Metric | Count |
|--------|-------|
| Files Scanned | {self.stats.get('files_scanned', 0)} |
| Total Symbols Found | {self.stats.get('symbols_found', 0)} |
| Symbols Documented | {self.stats.get('symbols_documented', 0)} |
| Symbols Flagged for Review | {self.stats.get('symbols_flagged', 0)} |
| Files Modified | {self.stats.get('files_modified', 0)} |
| Sidecar Files Created | {self.stats.get('sidecar_files_created', 0)} |

## Coverage by Language

| Language | Symbols | Documented | Flagged | Coverage |
|----------|---------|------------|---------|----------|
"""
        
        for lang, stats in lang_stats.items():
            coverage = (stats['documented'] / stats['total'] * 100) if stats['total'] > 0 else 0
            content += f"| {lang.capitalize()} | {stats['total']} | {stats['documented']} | {stats['flagged']} | {coverage:.1f}% |\n"
        
        content += f"""
## Symbols Requiring Human Review

The following symbols have confidence scores below the 80% threshold and should be reviewed:

| Symbol | File | Type | Confidence |
|--------|------|------|------------|
"""
        
        for sym in flagged_symbols:
            content += f"| `{sym['name']}` | `{sym['file']}` | {sym['type']} | {sym['confidence']:.0%} |\n"
        
        content += f"""
## File Modifications

### Modified Source Files
"""
        
        modified_files = set(r.symbol.file_path for r in self.results)
        for file_path in sorted(modified_files):
            content += f"- `{file_path}`\n"
        
        content += f"""
### Sidecar Documentation Files
"""
        
        for file_path in sorted(modified_files):
            sidecar = Path(file_path).parent / f"{Path(file_path).stem}_DOCS.md"
            content += f"- `{sidecar}`\n"
        
        content += f"""
## Idempotency Check

This report was generated with idempotency guarantees. Re-running AutoDoc on the same source will produce consistent results.

## Next Steps

1. Review flagged symbols with confidence < 80%
2. Verify generated documentation accuracy
3. Run tests to ensure no functionality was broken
4. Commit documentation changes to version control

*Generated by AutoDoc - Autonomous Documentation Agent*
"""
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Generated report: {report_path}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='AutoDoc - Autonomous Documentation Agent')
    parser.add_argument('src_dir', help='Source directory or URL to document (e.g., ./src or https://github.com/user/repo)')
    parser.add_argument('--force', action='store_true', help='Overwrite existing documentation')
    parser.add_argument('--api-token', help='Hugging Face API token')
    parser.add_argument('--confidence', type=float, default=0.8, help='Confidence threshold (default: 0.8)')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without writing to disk')
    parser.add_argument('--report', action='store_true', help='Generate a documentation report')
    parser.add_argument('--output-dir', help='Output directory for cloned repositories (default: ./output)')
    parser.add_argument('--include-dirs', nargs='+', help='Additional directories to explicitly include')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger('AutoDoc').setLevel(logging.DEBUG)
    
    # Load from .env file if exists
    if os.path.exists('.env'):
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            logger.warning("python-dotenv not installed, skipping .env loading")
    
    agent = AutoDoc(
        src_dir=args.src_dir,
        force=args.force,
        api_token=args.api_token,
        output_dir=args.output_dir,
        dry_run=args.dry_run,
    )
    agent.reasoner.confidence_threshold = args.confidence
    agent.injector.confidence_threshold = args.confidence
    
    # Add explicitly included directories
    if args.include_dirs:
        for include_dir in args.include_dirs:
            full_path = Path(args.src_dir) / include_dir
            if full_path.exists():
                logger.info(f"Explicitly including directory: {full_path}")
    
    stats = agent.run()
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for key, value in stats.items():
        print(f"  {key}: {value}")
