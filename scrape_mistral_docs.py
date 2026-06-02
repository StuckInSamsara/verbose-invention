#!/usr/bin/env python3
"""
Main script to scrape Mistral AI documentation.
Run this script to scrape all documentation from docs.mistral.ai.
"""

import sys
import logging
from scraper.mistral_docs_scraper import MistralDocsScraper


def main():
    """Main entry point for scraping Mistral AI documentation."""
    
    # Initialize scraper
    scraper = MistralDocsScraper()
    
    try:
        print("=" * 60)
        print("Mistral AI Documentation Scraper")
        print("=" * 60)
        print()
        
        # Scrape all configured domains
        print("Starting full scrape...")
        results = scraper.scrape_all()
        
        print()
        print("=" * 60)
        print("Scraping Summary")
        print("=" * 60)
        print(f"Total pages scraped: {results['total_pages']}")
        print(f"Failed pages: {len(results['failed_pages'])}")
        if results['failed_pages']:
            print("Failed URLs:")
            for url in results['failed_pages'][:10]:
                print(f"  - {url}")
            if len(results['failed_pages']) > 10:
                print(f"  ... and {len(results['failed_pages']) - 10} more")
        print(f"Start time: {results['start_time']}")
        print(f"End time: {results['end_time']}")
        print()
        print("✅ Scraping complete!")
        
    except KeyboardInterrupt:
        print("\n⚠️  Scraping interrupted by user")
    except Exception as e:
        scraper.logger.error(f"Error during scraping: {e}")
        print(f"❌ Error: {e}")
        return 1
    finally:
        scraper.close()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
