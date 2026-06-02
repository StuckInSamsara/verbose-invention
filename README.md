# Mistral AI Documentation Scraper

A Python-based web scraper for extracting and structuring all documentation from [Mistral AI](https://mistral.ai) in both English and French.

## Features

- **Comprehensive Scraping**: Scrapes all documentation from `docs.mistral.ai` (English) and `mistral.ai/fr` (French)
- **Structured Output**: Saves content in JSON and Markdown formats
- **Recursive Navigation**: Follows links to scrape entire sections
- **Rate Limiting**: Respectful crawling with configurable delays
- **HTML Cleaning**: Removes scripts, styles, and artifacts
- **Duplicate Removal**: Eliminates duplicate content and headings
- **Link Preservation**: Maintains internal links in Markdown format

## Project Structure

```
verbose-invention/
├── scrape_mistral_docs.py      # Main entry point
├── scraper/
│   ├── __init__.py
│   ├── config.yaml             # Configuration (URLs, selectors, rate limiting)
│   ├── mistral_docs_scraper.py # Main scraper class
│   └── utils/
│       ├── __init__.py
│       ├── url_fetcher.py      # HTTP requests with retries and rate limiting
│       └── html_cleaner.py     # HTML parsing and cleaning
├── data/
│   ├── raw/                    # Raw HTML files
│   │   └── docs_mistral_ai/
│   ├── processed/              # Cleaned and structured data
│   │   ├── en/
│   │   └── fr/
│   └── output/                 # Final output files
│       ├── documentation_en.jsonl
│       └── documentation_fr.jsonl
├── requirements.txt            # Python dependencies
└── README.md
```

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the Scraper

#### Scrape a single page (test):
```bash
python scraper/mistral_docs_scraper.py
```

#### Scrape all documentation:
```bash
python scrape_mistral_docs.py
```

### 3. Output Files

- **Raw HTML**: `data/raw/docs_mistral_ai/*.html`
- **Processed JSON**: `data/processed/en/*.json` (one file per page)
- **JSONL Output**: `data/output/documentation_en.jsonl` (one line per page)
- **Summary**: `data/output/scraping_summary.json`

## Configuration

Edit `scraper/config.yaml` to customize:

```yaml
domains:
  - name: "Mistral Docs (EN)"
    base_url: "https://docs.mistral.ai"
    language: "en"
    allowed_paths:
      - "/models"
      - "/api"
      - "/getting-started"
      - "/resources"
      - "/developers"
      - "/admin"
    selectors:
      title: "h1"
      content: "article.prose"
      links: "article.prose a[href^='/']"

scraping:
  delay: 1.0          # Seconds between requests
  max_depth: 4        # Maximum recursion depth
  timeout: 10         # Request timeout
  retries: 3          # Number of retries
  max_pages: 1000     # Maximum pages to scrape

output:
  format: "jsonl"     # or "markdown"
  raw_dir: "data/raw/docs_mistral_ai"
  processed_dir: "data/processed/en"
  final_dir: "data/output"
```

## Data Structure

Each scraped page is stored as a JSON object with the following structure:

```json
{
  "url": "https://docs.mistral.ai/models/overview",
  "title": "Models Overview",
  "content": "Cleaned Markdown content...",
  "language": "en",
  "domain": "Mistral Docs (EN)",
  "scraped_at": "2025-06-02T16:00:00.000000",
  "headings": [
    {"level": 1, "text": "Models Overview", "id": ""},
    {"level": 2, "text": "Featured Models", "id": ""}
  ],
  "links": [
    {"href": "/models/model-cards/mistral-medium-3-5-26-04", "text": "Mistral Medium 3.5"}
  ],
  "metadata": {}
}
```

## Supported Sections

The scraper currently targets:

- **docs.mistral.ai** (English):
  - `/models` - Model documentation
  - `/api` - API reference
  - `/getting-started` - Getting started guides
  - `/resources` - Cookbooks and resources
  - `/developers` - Developer documentation
  - `/admin` - Admin documentation
  - `/products` - Product documentation

- **mistral.ai/fr** (French):
  - `/fr/products` - Produits
  - `/fr/solutions` - Solutions
  - `/fr/models` - Modèles
  - `/fr/news` - Actualités
  - `/fr/customers` - Clients
  - `/fr/industry` - Secteurs

## Technical Details

### HTML Cleaning

The scraper:
1. Extracts content from `<article class="prose">` (main content container)
2. Removes HTML comments (used by Next.js)
3. Cleans up control characters and artifacts
4. Converts links to Markdown format: `[text](url)`
5. Converts images to Markdown format: `![alt](src)`
6. Converts tables to Markdown format
7. Removes duplicate consecutive lines
8. Preserves code blocks with syntax highlighting

### Rate Limiting

- Default delay: 1 second between requests
- Configurable retries: 3 attempts per page
- Respects `robots.txt` (excludes disallowed paths)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests (if any)
5. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
