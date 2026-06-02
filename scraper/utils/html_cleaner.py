"""
HTML Cleaner Module
Cleans and extracts content from HTML using BeautifulSoup.
"""

import re
from typing import Optional, List, Dict, Any
from bs4 import BeautifulSoup, Tag, Comment


class HTMLCleaner:
    """Cleans HTML content and extracts structured data."""
    
    def __init__(self):
        """Initialize the HTML cleaner."""
        self.soup = None
    
    def parse(self, html: str) -> Optional[BeautifulSoup]:
        """
        Parse HTML content.
        
        Args:
            html: HTML string to parse
            
        Returns:
            BeautifulSoup object or None if parsing fails
        """
        try:
            self.soup = BeautifulSoup(html, 'lxml')
            return self.soup
        except Exception as e:
            print(f"Error parsing HTML: {e}")
            return None
    
    def extract_title(self, selector: str = "h1") -> Optional[str]:
        """
        Extract the page title.
        
        Args:
            selector: CSS selector for title element
            
        Returns:
            Title text or None
        """
        if not self.soup:
            return None
        
        title_element = self.soup.select_one(selector)
        if title_element:
            return title_element.get_text(strip=True)
        
        # Fallback to <title> tag
        title_tag = self.soup.find("title")
        if title_tag:
            return title_tag.get_text(strip=True)
        
        return None
    
    def extract_content(self, selector: str = "article, main, .markdown") -> Optional[str]:
        """
        Extract the main content from the page.
        
        Args:
            selector: CSS selector for content container
            
        Returns:
            Cleaned content text or None
        """
        if not self.soup:
            return None
        
        content_element = self.soup.select_one(selector)
        if not content_element:
            # Try to find any large text container
            content_element = self.soup.find("div", class_=re.compile(r"content|main|article|markdown"))
        
        if not content_element:
            return None
        
        # Clean the content
        raw_content = self._clean_element(content_element)
        
        # Post-processing: remove duplicates and clean up
        cleaned_content = self._post_process_content(raw_content)
        
        return cleaned_content
    
    def _post_process_content(self, content: str) -> str:
        """
        Post-process content to remove duplicates and clean up.
        
        Args:
            content: Raw cleaned content
            
        Returns:
            Post-processed content
        """
        if not content:
            return content
        
        # Remove control characters and artifacts (but preserve newlines and tabs)
        content = re.sub(r'[\x00-\x09\x0b-\x1f\x7f-\x9f]', '', content)
        content = re.sub(r'\$\?/\$|/\$|\$', '', content)
        
        # Remove duplicate consecutive non-empty lines while preserving all whitespace
        # Use a function to handle this properly
        def remove_consecutive_duplicates(match):
            # match.group(1) = leading whitespace/newlines before first occurrence
            # match.group(2) = the line content (can contain spaces)
            # match.group(3) = whitespace/newlines between occurrences
            # We want to keep: group(1) + group(2) + group(3)
            # But we're removing the duplicate, so just return group(1) + group(2) + group(3)
            return match.group(1) + match.group(2) + match.group(3)
        
        # Pattern: (whitespace/newlines before)(line content - any chars except newline)(whitespace/newlines after)(same line content)
        # We want to keep: group(1) + group(2) + group(3) and remove the duplicate
        content = re.sub(
            r'((?:\s*\n)+)([^\n]+?)((?:\s*\n)+)\2',
            remove_consecutive_duplicates,
            content
        )
        
        # Clean up excessive newlines at the start
        content = re.sub(r'^\n+', '', content)
        
        # Clean up excessive newlines at the end
        content = re.sub(r'\n+$', '', content)
        
        # Clean up excessive newlines in the middle (more than 2)
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        return content
    
    def _clean_element_list(self, elements) -> str:
        """
        Clean a list of elements.
        
        Args:
            elements: List of elements to clean
            
        Returns:
            Cleaned text
        """
        parts = []
        for element in elements:
            cleaned = self._clean_element(element)
            if cleaned and cleaned.strip():
                parts.append(cleaned)
        return " ".join(parts)
    
    def _clean_element(self, element) -> str:
        """
        Recursively clean an HTML element.
        
        Args:
            element: BeautifulSoup element to clean
            
        Returns:
            Cleaned text
        """
        # Handle comments - skip them entirely
        if isinstance(element, Comment):
            return ""
        
        if isinstance(element, str):
            # Clean string content
            cleaned = element.strip()
            # Remove control characters and artifacts
            cleaned = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', cleaned)
            cleaned = re.sub(r'\$\?/\$|/\$|\$', '', cleaned)
            return cleaned
        
        if not isinstance(element, Tag):
            return str(element)
        
        # Elements to remove entirely
        remove_tags = [
            "script", "style", "noscript", "iframe", "svg", 
            "nav", "footer", "header", "aside", "form",
            "button", "input", "select", "textarea"
        ]
        
        # If this element should be removed
        if element.name in remove_tags:
            return ""
        
        # Handle code blocks specially
        if element.name == "code":
            return f"```{element.get('class', [''])[0] if element.get('class') else ''}\n{element.get_text()}\n```"
        
        if element.name == "pre":
            code = element.find("code")
            if code:
                return self._clean_element(code)
            return f"```\n{element.get_text()}\n```"
        
        # Handle links
        if element.name == "a":
            href = element.get("href", "")
            if not href or href.startswith("#") or href.startswith("javascript:"):
                # Process children as normal content if not a valid link
                return self._clean_element_list(list(element.children))
            
            # Extract all text content and split into lines
            all_text = element.get_text(" ", strip=True)
            
            # Check if the link contains an image
            img = element.find("img")
            if img:
                # Remove the image from consideration
                img_text = img.get("alt", "")
                # Get text without the image
                img.extract()
                link_text = element.get_text(" ", strip=True)
                
                if link_text:
                    # Split text into parts (first part is likely the title)
                    parts = [p.strip() for p in link_text.split("  ") if p.strip()]
                    if parts:
                        # Use first part as link text, rest as description
                        link_title = parts[0]
                        description = " ".join(parts[1:]) if len(parts) > 1 else ""
                        
                        if description:
                            return f"[{link_title}]({href}) {description}"
                        else:
                            return f"[{link_title}]({href})"
                
                # If no text after removing image, use alt text
                if img_text:
                    return f"![{img_text}]({img.get('src', '')})"
                return ""
            
            # For regular text links
            if all_text:
                # Split text into parts
                parts = [p.strip() for p in all_text.split("  ") if p.strip()]
                if parts:
                    link_title = parts[0]
                    description = " ".join(parts[1:]) if len(parts) > 1 else ""
                    
                    if description:
                        return f"[{link_title}]({href}) {description}"
                    else:
                        return f"[{link_title}]({href})"
            
            return all_text
        
        # Handle images
        if element.name == "img":
            src = element.get("src", "")
            alt = element.get("alt", "")
            if src:
                return f"![{alt}]({src})"
            return ""
        
        # Handle lists
        if element.name in ["ul", "ol"]:
            items = []
            for li in element.find_all("li", recursive=False):
                items.append(f"- {self._clean_element(li)}")
            return "\n".join(items)
        
        # Handle tables
        if element.name == "table":
            return self._clean_table(element)
        
        # For other elements, process children
        parts = []
        for child in element.children:
            cleaned = self._clean_element(child)
            if cleaned and cleaned.strip():
                parts.append(cleaned)
        
        # Add newlines for block elements
        if element.name in ["div", "section", "p", "h1", "h2", "h3", "h4", "h5", "h6", "article", "main"]:
            return "\n\n".join(parts) + "\n\n"
        
        return " ".join(parts)
    
    def _clean_table(self, table: Tag) -> str:
        """
        Clean a table element and convert to Markdown.
        
        Args:
            table: BeautifulSoup table element
            
        Returns:
            Markdown table string
        """
        rows = table.find_all("tr")
        if not rows:
            return ""
        
        # Extract headers
        headers = []
        header_row = rows[0]
        for th in header_row.find_all(["th", "td"]):
            headers.append(self._clean_element(th).strip())
        
        # Extract data rows
        data_rows = []
        for row in rows[1:]:
            cells = []
            for td in row.find_all(["th", "td"]):
                cells.append(self._clean_element(td).strip())
            data_rows.append(cells)
        
        # Build Markdown table
        if not headers:
            return ""
        
        # Header row
        md_table = "| " + " | ".join(headers) + " |\n"
        # Separator row
        md_table += "| " + " | ".join(["---" for _ in headers]) + " |\n"
        # Data rows
        for row in data_rows:
            md_table += "| " + " | ".join(row) + " |\n"
        
        return md_table
    
    def extract_links(self, selector: str = "a[href^='/']") -> List[Dict[str, str]]:
        """
        Extract all internal links from the page.
        
        Args:
            selector: CSS selector for links
            
        Returns:
            List of dictionaries with href and text
        """
        if not self.soup:
            return []
        
        links = []
        for a in self.soup.select(selector):
            href = a.get("href", "")
            text = a.get_text(strip=True)
            
            # Skip empty or anchor links
            if not href or href.startswith("#") or href.startswith("javascript:"):
                continue
            
            links.append({
                "href": href,
                "text": text
            })
        
        return links
    
    def extract_metadata(self) -> Dict[str, Any]:
        """
        Extract metadata from the page (description, keywords, etc.).
        
        Returns:
            Dictionary with metadata
        """
        if not self.soup:
            return {}
        
        metadata = {}
        
        # Meta tags
        for meta in self.soup.find_all("meta"):
            name = meta.get("name") or meta.get("property")
            content = meta.get("content")
            if name and content:
                metadata[name] = content
        
        # Language
        html = self.soup.find("html")
        if html and html.get("lang"):
            metadata["language"] = html.get("lang")
        
        return metadata
    
    def extract_headings(self) -> List[Dict[str, Any]]:
        """
        Extract all headings (h1-h6) from the page.
        
        Returns:
            List of dictionaries with level, text, and id
        """
        if not self.soup:
            return []
        
        headings = []
        for level in range(1, 7):
            for heading in self.soup.find_all(f"h{level}"):
                headings.append({
                    "level": level,
                    "text": heading.get_text(strip=True),
                    "id": heading.get("id", "")
                })
        
        return headings
    
    def to_markdown(self, title_selector: str = "h1", content_selector: str = "article, main, .markdown") -> str:
        """
        Convert the page to Markdown format.
        
        Args:
            title_selector: CSS selector for title
            content_selector: CSS selector for content
            
        Returns:
            Markdown string
        """
        title = self.extract_title(title_selector)
        content = self.extract_content(content_selector)
        
        if not title and not content:
            return ""
        
        markdown = f"# {title}\n\n" if title else ""
        markdown += content if content else ""
        
        return markdown.strip()
    
    def to_structured_data(
        self,
        url: str,
        title_selector: str = "h1",
        content_selector: str = "article, main, .markdown",
        link_selector: str = "a[href^='/']"
    ) -> Dict[str, Any]:
        """
        Extract structured data from the page.
        
        Args:
            url: URL of the page
            title_selector: CSS selector for title
            content_selector: CSS selector for content
            link_selector: CSS selector for links
            
        Returns:
            Dictionary with structured data
        """
        title = self.extract_title(title_selector)
        content = self.extract_content(content_selector)
        links = self.extract_links(link_selector)
        metadata = self.extract_metadata()
        headings = self.extract_headings()
        
        return {
            "url": url,
            "title": title,
            "content": content,
            "language": metadata.get("language", "en"),
            "headings": headings,
            "links": links,
            "metadata": metadata
        }
