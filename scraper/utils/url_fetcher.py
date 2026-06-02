"""
URL Fetcher Module
Handles HTTP requests with retries, rate limiting, and error handling.
"""

import time
import logging
import requests
from typing import Optional, Dict, Any
from urllib.parse import urljoin, urlparse


class URLFetcher:
    """Fetches URLs with configurable retries, delays, and headers."""
    
    def __init__(
        self,
        user_agent: str = "MistralDocsScraper/1.0",
        delay: float = 1.0,
        timeout: int = 10,
        retries: int = 3,
        max_pages: int = 1000
    ):
        """
        Initialize the URL fetcher.
        
        Args:
            user_agent: User-Agent header value
            delay: Delay between requests in seconds
            timeout: Request timeout in seconds
            retries: Number of retries for failed requests
            max_pages: Maximum number of pages to fetch
        """
        self.user_agent = user_agent
        self.delay = delay
        self.timeout = timeout
        self.retries = retries
        self.max_pages = max_pages
        self.pages_fetched = 0
        self.last_request_time = 0
        
        # Configure logging
        self.logger = logging.getLogger(__name__)
        
        # Session for connection pooling
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        })
    
    def _should_fetch(self, url: str) -> bool:
        """Check if we should fetch this URL (rate limiting, max pages)."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.delay:
            time.sleep(self.delay - time_since_last)
        
        if self.pages_fetched >= self.max_pages:
            self.logger.warning(f"Max pages limit ({self.max_pages}) reached")
            return False
        
        return True
    
    def _is_valid_url(self, url: str, base_url: str, allowed_paths: list, disallowed_paths: list) -> bool:
        """Check if URL is valid and should be scraped."""
        parsed = urlparse(url)
        
        # Must be HTTP/HTTPS
        if parsed.scheme not in ("http", "https"):
            return False
        
        # Must be same domain
        base_parsed = urlparse(base_url)
        if parsed.netloc != base_parsed.netloc:
            return False
        
        # Check path against allowed/disallowed
        path = parsed.path
        
        # Disallowed paths take precedence
        for disallowed in disallowed_paths:
            if path.startswith(disallowed):
                return False
        
        # Must match at least one allowed path
        if allowed_paths:
            for allowed in allowed_paths:
                if path.startswith(allowed):
                    return True
            return False
        
        return True
    
    def fetch(self, url: str, base_url: str, allowed_paths: list, disallowed_paths: list) -> Optional[str]:
        """
        Fetch a URL and return its HTML content.
        
        Args:
            url: URL to fetch
            base_url: Base URL for domain validation
            allowed_paths: List of allowed path prefixes
            disallowed_paths: List of disallowed path prefixes
            
        Returns:
            HTML content as string, or None if failed
        """
        # Validate URL
        if not self._is_valid_url(url, base_url, allowed_paths, disallowed_paths):
            self.logger.debug(f"Skipping invalid URL: {url}")
            return None
        
        # Rate limiting
        if not self._should_fetch(url):
            return None
        
        # Prepare full URL
        if not urlparse(url).netloc:
            url = urljoin(base_url, url)
        
        # Try with retries
        for attempt in range(self.retries):
            try:
                self.logger.info(f"Fetching: {url} (attempt {attempt + 1})")
                response = self.session.get(url, timeout=self.timeout)
                
                # Update counters
                self.pages_fetched += 1
                self.last_request_time = time.time()
                
                # Check status
                if response.status_code == 200:
                    return response.text
                elif response.status_code == 404:
                    self.logger.warning(f"404 Not Found: {url}")
                    return None
                elif response.status_code == 403:
                    self.logger.error(f"403 Forbidden: {url} (check robots.txt)")
                    return None
                elif response.status_code == 429:
                    # Rate limited, wait longer
                    wait_time = 2 ** attempt  # Exponential backoff
                    self.logger.warning(f"429 Rate Limited: {url}, waiting {wait_time}s")
                    time.sleep(wait_time)
                else:
                    self.logger.warning(f"HTTP {response.status_code}: {url}")
                    
            except requests.exceptions.Timeout:
                self.logger.warning(f"Timeout: {url}")
            except requests.exceptions.RequestException as e:
                self.logger.error(f"Request error for {url}: {e}")
            
            # Wait before retry
            if attempt < self.retries - 1:
                time.sleep(1)
        
        self.logger.error(f"Failed to fetch after {self.retries} attempts: {url}")
        return None
    
    def close(self):
        """Close the session."""
        self.session.close()
