import os
import time
import json
import logging
import requests
import jsbeautifier
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urlunparse
from urllib.robotparser import RobotFileParser
from collections import deque
from datetime import datetime
from typing import Dict, List, Callable, Optional

# --- Configuration ---
MAX_PAGES_TO_CRAWL = 10
DELAY_BETWEEN_PAGES = 1.5
MAX_RETRIES = 3
TIMEOUT = 10
BEAUTIFY_OPTS = jsbeautifier.default_options()
BEAUTIFY_OPTS.indent_size = 2

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('crawler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class CrawlerStats:
    """Track crawler statistics"""
    def __init__(self):
        self.pages_crawled = 0
        self.assets_downloaded = 0
        self.total_bytes = 0
        self.start_time = None
        self.end_time = None
        self.errors = []
        self.urls_found = 0
        
    def to_dict(self):
        duration = 0
        if self.start_time and self.end_time:
            duration = (self.end_time - self.start_time).total_seconds()
        
        return {
            'pages_crawled': self.pages_crawled,
            'assets_downloaded': self.assets_downloaded,
            'total_bytes': self.total_bytes,
            'total_mb': round(self.total_bytes / (1024 * 1024), 2),
            'duration_seconds': round(duration, 2),
            'urls_found': self.urls_found,
            'errors_count': len(self.errors),
            'errors': self.errors[:10]  # Limit to first 10 errors
        }

class PoliteCrawler:
    """Enhanced web crawler with progress tracking and JSON export"""
    
    def __init__(self, start_url: str, max_pages: int = 10, delay: float = 1.5, 
                 progress_callback: Optional[Callable] = None):
        self.start_url = start_url
        self.max_pages = max_pages
        self.delay = delay
        self.progress_callback = progress_callback or (lambda x: None)
        
        parsed = urlparse(start_url)
        self.domain = parsed.netloc
        self.base_url = f"{parsed.scheme}://{parsed.netloc}"
        
        self.visited_urls = set()
        self.url_queue = deque()
        self.stats = CrawlerStats()
        self.results = {
            'metadata': {},
            'pages': [],
            'assets': {
                'images': [],
                'svgs': [],
                'data_files': []  # For any data files found
            }
        }
        
        self.folders = {}
        self.robots_parser = RobotFileParser()
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'Mozilla/5.0 (compatible; PoliteCrawler/1.0)'})
        
    def setup_folders(self):
        """Create folder structure for downloads"""
        self.folders = {
            'root': self.domain,
            'html': os.path.join(self.domain, 'pages'),
            'images': os.path.join(self.domain, 'assets', 'images'),
            'svgs': os.path.join(self.domain, 'assets', 'svgs'),
            'data': os.path.join(self.domain, 'data')  # For data files
        }
        for f in self.folders.values():
            os.makedirs(f, exist_ok=True)
        logger.info(f"Created folder structure at {self.domain}/")
        
    def check_robots_txt(self):
        """Check and parse robots.txt"""
        robots_url = urljoin(self.base_url, '/robots.txt')
        try:
            self.robots_parser.set_url(robots_url)
            self.robots_parser.read()
            logger.info(f"Successfully parsed robots.txt from {robots_url}")
        except Exception as e:
            logger.warning(f"Could not read robots.txt: {e}")
            
    def can_fetch(self, url: str) -> bool:
        """Check if we're allowed to fetch this URL according to robots.txt"""
        try:
            return self.robots_parser.can_fetch("PoliteCrawler", url)
        except:
            return True  # If check fails, assume we can fetch
            
    def download_with_retry(self, url: str, stream: bool = False) -> Optional[requests.Response]:
        """Download URL with retry logic"""
        for attempt in range(MAX_RETRIES):
            try:
                response = self.session.get(url, stream=stream, timeout=TIMEOUT)
                response.raise_for_status()
                return response
            except requests.RequestException as e:
                if attempt == MAX_RETRIES - 1:
                    logger.error(f"Failed to download {url} after {MAX_RETRIES} attempts: {e}")
                    self.stats.errors.append({'url': url, 'error': str(e)})
                    return None
                time.sleep(1)  # Wait before retry
                
    def download_asset(self, url: str, folder: str, asset_type: str) -> Optional[str]:
        """Download binary assets (images, fonts, etc.)"""
        try:
            filename = os.path.basename(urlparse(url).path)
            if not filename:
                return None
            filename = filename.split('?')[0]
            filepath = os.path.join(folder, filename)
            
            if os.path.exists(filepath):
                logger.debug(f"Asset already exists: {filename}")
                return filename
            
            response = self.download_with_retry(url, stream=True)
            if not response:
                return None
            
            file_size = 0
            with open(filepath, "wb") as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
                    file_size += len(chunk)
            
            self.stats.assets_downloaded += 1
            self.stats.total_bytes += file_size
            logger.info(f"Downloaded {asset_type}: {filename} ({file_size} bytes)")
            
            return filename
            
        except Exception as e:
            logger.error(f"Error downloading asset {url}: {e}")
            self.stats.errors.append({'url': url, 'error': str(e)})
            return None
            
    def save_text_asset(self, url: str, folder: str, file_type: str) -> Optional[str]:
        """Download and beautify text files (CSS, JS)"""
        try:
            filename = os.path.basename(urlparse(url).path)
            if not filename:
                filename = f"script.{file_type}"
            filename = filename.split('?')[0]
            filepath = os.path.join(folder, filename)
            
            if os.path.exists(filepath):
                logger.debug(f"Code file already exists: {filename}")
                return filename
            
            response = self.download_with_retry(url)
            if not response:
                return None
            
            content = response.text
            if file_type == 'js':
                content = jsbeautifier.beautify(content, BEAUTIFY_OPTS)
            elif file_type == 'css':
                content = jsbeautifier.beautify_css(content, BEAUTIFY_OPTS)
            
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            
            file_size = len(content.encode('utf-8'))
            self.stats.assets_downloaded += 1
            self.stats.total_bytes += file_size
            logger.info(f"Downloaded {file_type.upper()}: {filename} ({file_size} bytes)")
            
            return filename
            
        except Exception as e:
            logger.error(f"Error downloading {file_type} {url}: {e}")
            self.stats.errors.append({'url': url, 'error': str(e)})
            return None
            
    def process_page(self, url: str) -> List[str]:
        """Process a single page and extract all resources"""
        logger.info(f"Processing page: {url}")
        
        if not self.can_fetch(url):
            logger.warning(f"robots.txt disallows fetching: {url}")
            return []
        
        try:
            response = self.download_with_retry(url)
            if not response:
                return []
            
            soup = BeautifulSoup(response.text, "html.parser")
            
        except Exception as e:
            logger.error(f"Error processing page {url}: {e}")
            self.stats.errors.append({'url': url, 'error': str(e)})
            return []
        
        # Save HTML
        page_name = urlparse(url).path.strip("/")
        if not page_name:
            page_name = "index"
        page_name = page_name.replace("/", "_") + ".html"
        
        html_path = os.path.join(self.folders["html"], page_name)
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(soup.prettify())
        
        page_data = {
            'url': url,
            'filename': page_name,
            'title': soup.title.string if soup.title else '',
            'assets': {'images': [], 'css': [], 'js': [], 'svgs': []}
        }
        
        # Extract images
        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src")
            if src and not src.startswith("data:"):
                full_url = urljoin(url, src)
                filename = self.download_asset(full_url, self.folders["images"], "image")
                if filename:
                    page_data['assets']['images'].append(full_url)
                    self.results['assets']['images'].append(full_url)
        
        # Extract CSS
        for link in soup.find_all("link", attrs={"rel": "stylesheet"}):
            href = link.get("href")
            if href:
                full_url = urljoin(url, href)
                # Skip CSS and JS - Data collection only (commented out)
                # CSS and JavaScript files not downloaded for pure data collection
                # Only HTML pages, images, and SVGs are collected
                # filename = self.save_text_asset(full_url, self.folders["css"], 'css')
                # if filename:
                #     page_data['assets']['css'].append(full_url)
                #     self.results['assets']['css'].append(full_url)
        
        # Extract JavaScript
        for script in soup.find_all("script"):
            src = script.get("src")
            if src:
                full_url = urljoin(url, src)
                # filename = self.save_text_asset(full_url, self.folders["js"], 'js')
                # if filename:
                #     page_data['assets']['js'].append(full_url)
                #     self.results['assets']['js'].append(full_url)
        
        # Extract inline SVGs
        for i, svg in enumerate(soup.find_all("svg")):
            fname = f"{page_name.replace('.html', '')}_icon{i}.svg"
            svg_path = os.path.join(self.folders["svg"], fname)
            with open(svg_path, "w", encoding="utf-8") as f:
                f.write(svg.prettify())
            page_data['assets']['svgs'].append(fname)
            self.results['assets']['svgs'].append(fname)
        
        self.results['pages'].append(page_data)
        
        # Find internal links
        internal_links = []
        for a in soup.find_all("a", href=True):
            href = a['href']
            full_url = urljoin(url, href)
            parsed_link = urlparse(full_url)
            
            # Only stay on same domain
            if parsed_link.netloc == self.domain and "mailto:" not in href:
                clean_url = full_url.split('#')[0]
                if clean_url not in self.visited_urls:
                    internal_links.append(clean_url)
                    self.stats.urls_found += 1
        
        return internal_links
        
    def crawl(self):
        """Main crawl loop"""
        logger.info(f"Starting crawl of {self.start_url}")
        self.stats.start_time = datetime.now()
        
        self.setup_folders()
        self.check_robots_txt()
        
        self.url_queue.append(self.start_url)
        self.visited_urls.add(self.start_url)
        
        while self.url_queue and self.stats.pages_crawled < self.max_pages:
            # Rate limiting
            if self.stats.pages_crawled > 0:
                logger.debug(f"Sleeping for {self.delay} seconds...")
                time.sleep(self.delay)
            
            current_url = self.url_queue.popleft()
            found_links = self.process_page(current_url)
            self.stats.pages_crawled += 1
            
            # Progress callback
            progress = {
                'pages_crawled': self.stats.pages_crawled,
                'max_pages': self.max_pages,
                'current_url': current_url,
                'assets_downloaded': self.stats.assets_downloaded,
                'queue_size': len(self.url_queue)
            }
            self.progress_callback(progress)
            
            # Add new links to queue
            for link in found_links:
                if link not in self.visited_urls:
                    self.visited_urls.add(link)
                    self.url_queue.append(link)
        
        self.stats.end_time = datetime.now()
        self.save_results()
        self.print_summary()
        
    def save_results(self):
        """Save crawl results as JSON"""
        self.results['metadata'] = {
            'start_url': self.start_url,
            'domain': self.domain,
            'crawl_date': datetime.now().isoformat(),
            'stats': self.stats.to_dict()
        }
        
        json_path = os.path.join(self.folders["root"], 'crawl_results.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Results saved to {json_path}")
        
    def print_summary(self):
        """Print crawl summary"""
        stats_dict = self.stats.to_dict()
        print("\n" + "="*80)
        print("✅ CRAWL COMPLETE")
        print("="*80)
        print(f"Pages Crawled:      {stats_dict['pages_crawled']}")
        print(f"Assets Downloaded:  {stats_dict['assets_downloaded']}")
        print(f"Total Size:         {stats_dict['total_mb']} MB")
        print(f"Duration:           {stats_dict['duration_seconds']} seconds")
        print(f"URLs Found:         {stats_dict['urls_found']}")
        print(f"Errors:             {stats_dict['errors_count']}")
        print(f"\nOutput folder:      {self.folders['root']}/")
        print("="*80 + "\n")

def main():
    """CLI entry point"""
    print("="*80)
    print("🕷️  POLITE WEB CRAWLER - Enhanced Edition")
    print("="*80 + "\n")
    
    target = input("Enter Website URL to Crawl: ").strip()
    if not target.startswith("http"):
        target = "https://" + target
    
    try:
        limit = int(input("How many pages to scan? (Default 10): ").strip())
    except:
        limit = 10
    
    try:
        delay = float(input(f"Delay between pages in seconds? (Default {DELAY_BETWEEN_PAGES}): ").strip())
    except:
        delay = DELAY_BETWEEN_PAGES
    
    def progress_callback(progress):
        """Print progress updates"""
        print(f"  [{progress['pages_crawled']}/{progress['max_pages']}] "
              f"Assets: {progress['assets_downloaded']} | "
              f"Queue: {progress['queue_size']}")
    
    crawler = PoliteCrawler(target, max_pages=limit, delay=delay, progress_callback=progress_callback)
    crawler.crawl()

if __name__ == "__main__":
    main()
