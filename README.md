# AutoDoc (NEO) - Autonomous Documentation Agent

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **Autonomously built by [NEO](https://heyneo.so/) — Your Autonomous AI Agent**

AutoDoc (codenamed **NEO**) is an autonomous documentation agent powered by the **HyperNova-60B-2602** model via the Hugging Face Inference API. It scans, reasons about, and documents source code across multiple languages with zero human intervention.

## 🚀 Features

- **Multi-Language Support**: Python, JavaScript, TypeScript, and Go
- **AI-Powered Analysis**: Uses HyperNova-60B-2602 for intelligent documentation generation
- **Multiple Output Formats**:
  - Python: Google-style docstrings
  - JavaScript: JSDoc
  - TypeScript: TypeDoc/JSDoc
  - Go: GoDoc
- **Smart Injection**: Preserves existing formatting and documentation
- **Sidecar Documentation**: Creates `NEO_DOCS.md` files for each module
- **Confidence Scoring**: Flags low-confidence documentation for human review
- **Idempotent**: Re-running produces consistent results

## 📋 Requirements

- Python 3.8 or higher
- Hugging Face API token (for HyperNova-60B-2602 access)
- Internet connection for API calls

## 🔧 Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd autoDock
   ```

2. **Create a virtual environment** (recommended):
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install requests
   ```

4. **Set up Hugging Face API token**:
   
   Copy the example environment file and add your token:
   ```bash
   cp .env.example .env
   # Edit .env and add your Hugging Face API token
   ```
   
   Or set the environment variable directly:
   ```bash
   export HUGGINGFACE_API_TOKEN="your_huggingface_api_token"
   ```
   
   Get your token from: https://huggingface.co/settings/tokens

## 🎯 Usage

### Quick Start with Trial Directory

AutoDoc includes a `trial` directory with sample code in Python, JavaScript, and Go for immediate testing:

```bash
# Document the trial directory
python3 autodoc.py ./trial

# Force overwrite existing documentation
python3 autodoc.py ./trial --force
```

The trial directory contains:
- `sample.py` - Python module with classes and functions
- `sample.js` - JavaScript module with ES6 classes
- `sample.go` - Go module with structs and interfaces

### Basic Usage

Document a local source directory:

```bash
python3 autodoc.py ./src
```

### Document Remote Repositories

AutoDoc can document code from remote GitHub repositories:

```bash
# Document a GitHub repository
python3 autodoc.py https://github.com/user/repo

# Document with force overwrite
python3 autodoc.py https://github.com/user/repo --force
```

The repository will be cloned to a temporary directory, documented, and then cleaned up automatically.

### Command-Line Options

```bash
python3 autodoc.py [OPTIONS] <source_directory>

Options:
  --force           Overwrite existing documentation
  --confidence N    Set confidence threshold (default: 0.8)
  --output-dir DIR  Specify output directory for reports
  --dry-run         Preview changes without writing to disk
  --verbose         Enable detailed logging

Examples:
  python3 autodoc.py ./src --force
  python3 autodoc.py ./src --confidence 0.9 --verbose
  python3 autodoc.py ./src --dry-run
```

### Python API

```python
from autodoc import Scanner, Reasoner, DocumentGenerator, DocumentInjector

# 1. Scan source directory
scanner = Scanner("./src")
files = scanner.scan_directory()

# 2. Analyze with AI
reasoner = Reasoner(api_token="your_token")
for file in files:
    for symbol in file.symbols:
        doc, confidence = reasoner.analyze_symbol(symbol)
        # ... process documentation

# 3. Generate and inject
generator = DocumentGenerator()
injector = DocumentInjector(force=False)
results = []
for file in files:
    for symbol in file.symbols:
        doc_result = generator.generate(symbol, "doc text", 0.85)
        results.append(doc_result)

stats = injector.inject(results)
```

## 📊 Output

### Inline Documentation

AutoDoc injects documentation directly into source files:

**Python Example:**
```python
def calculate_total(items, tax_rate=0.0):
    """
    Calculate the total price including tax.

    Args:
        items: List of items with price attribute.
        tax_rate: Tax rate as decimal (default: 0.0).

    Returns:
        float: Total price including tax.

    Examples:
        >>> calculate_total([item1, item2], 0.08)
        108.0
    """
    pass
```

### Sidecar Files

Each module gets a `NEO_DOCS.md` file with comprehensive documentation.

### Documentation Report

A `DOCUMENTATION_REPORT.md` is generated with:
- Processing statistics
- Coverage by language
- Symbols requiring review
- File modification summary

## 🔒 Confidence Threshold

AutoDoc uses an 80% confidence threshold by default. Symbols below this threshold are flagged with `@neo-review needed` for human verification.

Adjust the threshold:
```bash
python3 autodoc.py ./src --confidence 0.9  # Stricter
python3 autodoc.py ./src --confidence 0.7  # More lenient
```

## 🛡️ Safety Features

- **Non-destructive**: Preserves existing code and formatting
- **Backup recommended**: Always commit changes before running
- **Dry-run mode**: Preview changes without modifying files
- **Force flag**: Explicit opt-in for overwriting existing docs

## 🐛 Troubleshooting

### Common Issues

**API Token Not Set:**
```
Error: HF_API_TOKEN environment variable not set
```
**Solution:** Export your Hugging Face API token:
```bash
export HF_API_TOKEN="your_token_here"
```

**Rate Limiting:**
```
Error: 429 Too Many Requests
```
**Solution:** The tool implements retry logic. Wait a moment and retry.

**Model Not Available:**
```
Error: Model HyperNova-60B-2602 not found
```
**Solution:** Verify your Hugging Face account has access to the model.

## 📁 Project Structure

```
autoDock/
├── autodoc.py              # Main entry point
├── README.md               # This file
├── .gitignore             # Git ignore rules
├── DOCUMENTATION_REPORT.md # Generated report
├── src/                    # Example source code
│   ├── go/
│   ├── js/
│   ├── py/
│   └── ts/
├── data/                   # Data processing scripts
├── model/                  # Model artifacts
├── analysis/               # Reports and visualizations
└── utils/                  # Helper functions
```

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 🙏 Acknowledgments

- Hugging Face for providing the HyperNova-60B-2602 model
- The open-source community for inspiration and tools

---

**AutoDoc (NEO)** - Documenting code so you don't have to.

For support or questions, please open an issue on the project repository.

---

*This project was autonomously built by [NEO](https://heyneo.so/) — the Autonomous AI Agent.*
