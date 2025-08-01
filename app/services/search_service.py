# app/services/search_service.py

import asyncio
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List
from urllib.parse import urlencode

from app.schemas import SearchResult
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

# Note: crawl4ai uses Playwright under the hood. You might need to run `playwright install` once.

class SearchService:
    """Service for web search using a direct crawling approach with crawl4ai."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        # Using a ThreadPoolExecutor to run the async crawler in a sync context if needed,
        # but we will call the async methods directly from our async graph nodes.
        self.executor = ThreadPoolExecutor(max_workers=3) # Reduced workers as browser instances are heavy

    def _construct_search_url(self, query: str) -> str:
        """Constructs a DuckDuckGo search URL."""
        return f"https://duckduckgo.com/?{urlencode({'q': query})}&ia=web"

    # In app/services/search_service.py, replace ONLY this method:

    def _parse_crawler_markdown(self, markdown_content: str, query: str) -> List[SearchResult]:
        """
        Parses the raw markdown from the crawler to extract organic search results
        and convert them into SearchResult Pydantic models. This version uses a more
        robust regex to handle variations in the crawler's output.
        """
        pattern = re.compile(
            r"##\s+(?:\d+\.\s)?\[(.*?)\]\((.*?)\)\n(.*?)(?=\n##\s|\n\s*Searches related to|\Z)",
            re.DOTALL
        )
        matches = pattern.findall(markdown_content)
        
        if not matches:
            self.logger.warning(f"Regex found no matches for query: '{query}'. Check the raw markdown output.")
            return []

        results = []
        for match in matches:
            # We capture three groups: title, url, and the raw snippet block
            title, url, snippet_block = match

            # Skip ads and non-http links
            if "duckduckgo.com/y.js" in url or not url.startswith('http'):
                continue
            
            # Clean the snippet: remove junk lines and extra whitespace
            lines = snippet_block.strip().split('\n')
            cleaned_lines = [
                line for line in lines if not line.strip().startswith('![]') and url not in line
            ]
            cleaned_snippet = ' '.join(cleaned_lines).strip().replace('**', '')

            if not cleaned_snippet:
                continue

            relevance_score = self._calculate_relevance(title, cleaned_snippet, query)

            results.append(SearchResult(
                title=title.strip(),
                url=url.strip(),
                snippet=cleaned_snippet,
                relevance_score=relevance_score
            ))
            
        self.logger.info(f"Successfully parsed {len(results)} results for query: '{query}'.")
        return results
    
    async def _execute_single_search(self, query: str) -> List[SearchResult]:
        """
        Performs a single search using the web crawler and returns structured results.
        """
        self.logger.info(f"Crawling DuckDuckGo for: '{query}'")
        try:
            browser_config = BrowserConfig(browser_type="firefox", headless=True, verbose=False)
            run_config = CrawlerRunConfig(page_timeout=15000, scan_full_page=True) # 15-second timeout

            async with AsyncWebCrawler(config=browser_config) as crawler:
                search_url = self._construct_search_url(query)
                result = await crawler.arun(url=search_url, config=run_config)

                if not result or not result.markdown:
                    self.logger.error(f"Crawling failed for '{query}', no markdown returned.")
                    return []
                # The markdown now contains the page content, parse it
                return self._parse_crawler_markdown(result.markdown, query)

        except Exception as e:
            self.logger.error(f"An exception occurred during crawl for query '{query}': {str(e)}")
            return []

    async def search_multiple_queries(self, queries: List[str]) -> List[SearchResult]:
        """Execute multiple search queries concurrently using the crawler."""
        self.logger.info(f"Executing {len(queries)} search queries using crawl4ai.")

        # Limit concurrent searches as each one spins up a browser instance
        tasks = [self._execute_single_search(query) for query in queries[:5]] # Reduced to 5 concurrent for stability
        
        results_of_lists = await asyncio.gather(*tasks)

        # Flatten the list of lists
        all_results = [item for sublist in results_of_lists for item in sublist]

        unique_results = self._deduplicate_results(all_results)
        ranked_results = self._rank_results(unique_results)
        
        self.logger.info(f"Found {len(ranked_results)} unique and ranked sources.")
        return ranked_results[:15] # Return top 15 overall

    # --- Helper methods (deduplicate, rank, calculate_relevance) remain the same ---

    def _calculate_relevance(self, title: str, snippet: str, query: str) -> float:
        query_terms = set(query.lower().split())
        combined_text = (title + " " + snippet).lower()
        title_text = title.lower()
        
        if not query_terms:
            return 0.0

        matches = len(query_terms.intersection(set(combined_text.split())))
        title_matches = len(query_terms.intersection(set(title_text.split())))
        
        # Score based on term matches, with a heavy boost for title matches
        score = (matches / len(query_terms)) * 0.7 + (title_matches / len(query_terms)) * 0.3
        
        return min(score, 1.0)

    def _deduplicate_results(self, results: List[SearchResult]) -> List[SearchResult]:
        seen_urls = set()
        unique_results = []
        for result in results:
            normalized_url = result.url.split('#')[0].rstrip('/')
            if normalized_url not in seen_urls:
                seen_urls.add(normalized_url)
                unique_results.append(result)
        return unique_results

    def _rank_results(self, results: List[SearchResult]) -> List[SearchResult]:
        return sorted(results, key=lambda x: x.relevance_score, reverse=True)