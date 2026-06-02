#!/usr/bin/env python3
"""
Mistral AI Documentation Scraper
Scrapes documentation from docs.mistral.ai and saves it in structured formats.
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
from urllib.parse import urlparse
import yaml

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Local imports
from scraper.utils.url_fetcher import URLFetcher
from scraper.utils.html_cleaner import HTMLCleaner


class MistralDocsScraper:
    """Main scraper class for Mistral AI documentation."""
    
    def __init__(self, config_path: str = "scraper/config.yaml"):
        """
        Initialize the scraper with configuration.
        
        Args:
            config_path: Path to YAML configuration file
        """
        self.config = self._load_config(config_path)
        self._setup_logging()
        self._setup_directories()
        
        # Initialize components
        scraping_config = self.config.get("scraping", {})
        self.fetcher = URLFetcher(
            user_agent=scraping_config.get("user_agent", "MistralDocsScraper/1.0"),
            delay=scraping_config.get("delay", 1.0),
            timeout=scraping_config.get("timeout", 10),
            retries=scraping_config.get("retries", 3),
            max_pages=scraping_config.get("max_pages", 1000)
        )
        self.cleaner = HTMLCleaner()
        
        # Track scraped pages
        self.scraped_pages = set()
        self.failed_pages = set()
        
        self.logger.info("MistralDocsScraper initialized")
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            self.logger.warning(f"Config file not found: {config_path}, using defaults")
            return {}
        except yaml.YAMLError as e:
            self.logger.error(f"Error parsing config: {e}")
            return {}
    
    def _setup_logging(self):
        """Configure logging."""
        log_config = self.config.get("logging", {})
        level = getattr(logging, log_config.get("level", "INFO"))
        log_file = log_config.get("file", "scraper.log")
        
        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def _setup_directories(self):
        """Create necessary directories."""
        output_config = self.config.get("output", {})
        
        directories = [
            output_config.get("raw_dir", "data/raw/docs_mistral_ai"),
            output_config.get("processed_dir", "data/processed/en"),
            output_config.get("final_dir", "data/output")
        ]
        
        for directory in directories:
            if directory:
                Path(directory).mkdir(parents=True, exist_ok=True)
                self.logger.debug(f"Created directory: {directory}")
    
    def _get_domain_config(self, domain_name: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific domain."""
        domains = self.config.get("domains", [])
        for domain in domains:
            if domain.get("name") == domain_name:
                return domain
        return None
    
    def _save_raw_html(self, url: str, html: str) -> str:
        """Save raw HTML to file."""
        output_config = self.config.get("output", {})
        raw_dir = output_config.get("raw_dir", "data/raw/docs_mistral_ai")
        
        # Create safe filename
        parsed_url = urlparse(url)
        path = parsed_url.path.strip("/").replace("/", "_")
        if not path:
            path = "index"
        filename = f"{path}.html"
        filepath = Path(raw_dir) / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)
        
        self.logger.debug(f"Saved raw HTML: {filepath}")
        return str(filepath)
    
    def _save_processed(self, data: Dict[str, Any], format: str = "jsonl") -> str:
        """Save processed data to file."""
        output_config = self.config.get("output", {})
        processed_dir = Path(output_config.get("processed_dir", "data/processed/en"))
        final_dir = Path(output_config.get("final_dir", "data/output"))
        
        # Create filename
        url = data.get("url", "unknown")
        parsed_url = urlparse(url)
        path = parsed_url.path.strip("/").replace("/", "_")
        if not path:
            path = "index"
        
        if format == "jsonl":
            # Save to processed directory
            processed_file = processed_dir / f"{path}.json"
            with open(processed_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=output_config.get("indent", 2), ensure_ascii=False)
            
            # Also append to final JSONL file
            final_file = final_dir / "documentation_en.jsonl"
            with open(final_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(data, ensure_ascii=False) + "\n")
            
            self.logger.debug(f"Saved processed data: {processed_file}")
            return str(processed_file)
        
        elif format == "markdown":
            md_content = self.cleaner.to_markdown()
            md_file = processed_dir / f"{path}.md"
            with open(md_file, 'w', encoding='utf-8') as f:
                f.write(md_content)
            
            self.logger.debug(f"Saved markdown: {md_file}")
            return str(md_file)
        
        return ""
    
    def scrape_page(
        self,
        url: str,
        domain_name: str = "Mistral Docs (EN)",
        save_raw: bool = True,
        save_processed: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Scrape a single page.
        
        Args:
            url: URL to scrape
            domain_name: Name of the domain configuration to use
            save_raw: Whether to save raw HTML
            save_processed: Whether to save processed data
            
        Returns:
            Dictionary with scraped data or None if failed
        """
        # Get domain configuration
        domain_config = self._get_domain_config(domain_name)
        if not domain_config:
            self.logger.error(f"Domain configuration not found: {domain_name}")
            return None
        
        base_url = domain_config.get("base_url", "")
        allowed_paths = domain_config.get("allowed_paths", [])
        disallowed_paths = domain_config.get("disallowed_paths", [])
        selectors = domain_config.get("selectors", {})
        
        # Normalize URL (remove trailing slash, etc.)
        from urllib.parse import urlparse, urlunparse
        parsed = urlparse(url)
        normalized_url = urlunparse(parsed._replace(path=parsed.path.rstrip('/') or '/'))
        
        # Check if already scraped
        if normalized_url in self.scraped_pages:
            self.logger.debug(f"Already scraped: {url}")
            return None
        
        # Fetch the page
        self.logger.info(f"Scraping: {url}")
        html = self.fetcher.fetch(url, base_url, allowed_paths, disallowed_paths)
        
        if not html:
            self.failed_pages.add(url)
            self.logger.warning(f"Failed to fetch: {url}")
            return None
        
        # Save raw HTML if requested
        if save_raw:
            self._save_raw_html(url, html)
        
        # Parse and clean HTML
        self.cleaner.parse(html)
        
        # Extract structured data
        title_selector = selectors.get("title", "h1")
        content_selector = selectors.get("content", "article, main, .markdown")
        link_selector = selectors.get("links", "a[href^='/']")
        
        data = self.cleaner.to_structured_data(
            url=url,
            title_selector=title_selector,
            content_selector=content_selector,
            link_selector=link_selector
        )
        
        # Add additional metadata
        data["scraped_at"] = datetime.utcnow().isoformat()
        data["domain"] = domain_name
        data["language"] = domain_config.get("language", "en")
        
        # Save processed data if requested
        if save_processed:
            output_config = self.config.get("output", {})
            format = output_config.get("format", "jsonl")
            self._save_processed(data, format)
        
        # Mark as scraped (using normalized URL)
        self.scraped_pages.add(normalized_url)
        
        self.logger.info(f"Successfully scraped: {url}")
        return data
    
    def scrape_section(
        self,
        section_path: str,
        domain_name: str = "Mistral Docs (EN)",
        max_depth: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Scrape a section recursively.
        
        Args:
            section_path: Path to the section (e.g., "/models")
            domain_name: Name of the domain configuration to use
            max_depth: Maximum recursion depth
            
        Returns:
            List of scraped pages data
        """
        domain_config = self._get_domain_config(domain_name)
        if not domain_config:
            self.logger.error(f"Domain configuration not found: {domain_name}")
            return []
        
        base_url = domain_config.get("base_url", "")
        full_url = f"{base_url.rstrip('/')}{section_path}"
        
        # Use BFS for scraping
        from collections import deque
        
        queue = deque()
        queue.append((full_url, 0))
        
        results = []
        
        while queue:
            url, depth = queue.popleft()
            
            # Check depth
            if depth > max_depth:
                continue
            
            # Scrape the page
            data = self.scrape_page(url, domain_name)
            if data:
                results.append(data)
                
                # Add links to queue if not at max depth
                if depth < max_depth:
                    for link in data.get("links", []):
                        href = link.get("href", "")
                        if href and href not in self.scraped_pages and href not in self.failed_pages:
                            # Construct full URL
                            if not href.startswith("http"):
                                full_href = f"{base_url.rstrip('/')}{href}"
                            else:
                                full_href = href
                            
                            # Check if it's within allowed paths
                            domain_config = self._get_domain_config(domain_name)
                            allowed_paths = domain_config.get("allowed_paths", [])
                            disallowed_paths = domain_config.get("disallowed_paths", [])
                            
                            from urllib.parse import urlparse
                            path = urlparse(full_href).path
                            
                            # Skip if not allowed
                            if allowed_paths:
                                allowed = any(path.startswith(ap) for ap in allowed_paths)
                                if not allowed:
                                    continue
                            
                            # Skip if disallowed
                            disallowed = any(path.startswith(dp) for dp in disallowed_paths)
                            if disallowed:
                                continue
                            
                            queue.append((full_href, depth + 1))
        
        return results
    
    def scrape_all(self) -> Dict[str, Any]:
        """
        Scrape all configured domains and sections.
        
        Returns:
            Dictionary with scraping results
        """
        results = {
            "scraped_pages": [],
            "failed_pages": list(self.failed_pages),
            "start_time": datetime.utcnow().isoformat()
        }
        
        domains = self.config.get("domains", [])
        scraping_config = self.config.get("scraping", {})
        max_depth = scraping_config.get("max_depth", 4)
        
        for domain in domains:
            domain_name = domain.get("name", "")
            base_url = domain.get("base_url", "")
            allowed_paths = domain.get("allowed_paths", [])
            
            self.logger.info(f"Starting scrape for domain: {domain_name}")
            
            # Scrape each allowed path
            for path in allowed_paths:
                self.logger.info(f"Scraping section: {path}")
                section_results = self.scrape_section(
                    section_path=path,
                    domain_name=domain_name,
                    max_depth=max_depth
                )
                results["scraped_pages"].extend(section_results)
        
        results["end_time"] = datetime.utcnow().isoformat()
        results["total_pages"] = len(results["scraped_pages"])
        
        # Save summary
        output_config = self.config.get("output", {})
        final_dir = Path(output_config.get("final_dir", "data/output"))
        summary_file = final_dir / "scraping_summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Scraping complete. Total pages: {results['total_pages']}")
        return results
    
    def close(self):
        """Clean up resources."""
        self.fetcher.close()
        self.logger.info("Scraper closed")


if __name__ == "__main__":
    # Example usage
    from urllib.parse import urlparse
    
    # Initialize scraper
    scraper = MistralDocsScraper()
    
    try:
        # Test with a single page
        test_url = "https://docs.mistral.ai/models/overview"
        print(f"Testing with URL: {test_url}")
        
        result = scraper.scrape_page(test_url)
        
        if result:
            print(f"\n✅ Successfully scraped: {result['url']}")
            print(f"Title: {result['title']}")
            print(f"Language: {result['language']}")
            print(f"Content length: {len(result.get('content', ''))} characters")
            print(f"Number of links: {len(result.get('links', []))}")
            print(f"Number of headings: {len(result.get('headings', []))}")
            
            # Show first 200 characters of content
            content = result.get('content', '')
            if content:
                print(f"\nContent preview:\n{content[:200]}...")
        else:
            print("❌ Failed to scrape the test page")
        
        # Close scraper
        scraper.close()
        
    except Exception as e:
        scraper.logger.error(f"Error during scraping: {e}")
        scraper.close()
        raise
