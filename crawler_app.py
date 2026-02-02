"""
🏭 INDUSTRIAL DATA CRAWLER - All-in-One Edition
═══════════════════════════════════════════════
Enterprise-grade web data extraction system
Self-contained • Multi-threaded • Multi-format Export

Author: Industrial Crawler Pro
Version: 2.0
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import queue
import time
import os
import json
import csv
import sqlite3
import re
import logging
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser
from collections import deque
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor

# External dependencies (install via pip)
import requests
from bs4 import BeautifulSoup
import pandas as pd

# ═══════════════════════════════════════════════════════════════
# LOGGING CONFIGURATION
# ═══════════════════════════════════════════════════════════════
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('industrial_crawler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
# DATA EXTRACTION ENGINE
# ═══════════════════════════════════════════════════════════════

class DataExtractor:
    """Extract structured data from HTML pages"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.domain = urlparse(base_url).netloc
        
    def extract_all(self, html: str, url: str) -> Dict[str, Any]:
        """Extract ALL structured data from HTML page"""
        soup = BeautifulSoup(html, 'html.parser')
        
        return {
            'url': url,
            'metadata': self.extract_metadata(soup),
            'tables': self.extract_tables(soup),
            'lists': self.extract_lists(soup),
            'text': self.extract_text(soup),
            'links': self.extract_links(soup, url),
            'headings': self.extract_headings(soup),
            'forms': self.extract_forms(soup),
            'structured_data': self.extract_json_ld(soup)
        }
    
    def extract_metadata(self, soup: BeautifulSoup) -> Dict:
        """Extract SEO metadata"""
        meta = {'title': '', 'description': '', 'keywords': [], 'og': {}}
        
        if soup.title:
            meta['title'] = soup.title.string.strip()
        
        for tag in soup.find_all('meta'):
            name = tag.get('name', '').lower()
            prop = tag.get('property', '').lower()
            content = tag.get('content', '')
            
            if name == 'description':
                meta['description'] = content
            elif name == 'keywords':
                meta['keywords'] = [k.strip() for k in content.split(',')]
            elif prop.startswith('og:'):
                meta['og'][prop.replace('og:', '')] = content
        
        return meta
    
    def extract_tables(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract all tables with pandas"""
        tables = []
        for idx, table in enumerate(soup.find_all('table')):
            try:
                df = pd.read_html(str(table))[0]
                tables.append({
                    'index': idx,
                    'rows': df.shape[0],
                    'cols': df.shape[1],
                    'columns': df.columns.tolist(),
                    'data': df.to_dict('records'),
                    'caption': table.find('caption').get_text(strip=True) if table.find('caption') else ''
                })
            except:
                pass
        return tables
    
    def extract_lists(self, soup: BeautifulSoup) -> Dict:
        """Extract ul/ol lists"""
        return {
            'unordered': [[li.get_text(strip=True) for li in ul.find_all('li', recursive=False)] 
                         for ul in soup.find_all('ul')],
            'ordered': [[li.get_text(strip=True) for li in ol.find_all('li', recursive=False)] 
                       for ol in soup.find_all('ol')]
        }
    
    def extract_text(self, soup: BeautifulSoup) -> Dict:
        """Extract clean text content"""
        for elem in soup(['script', 'style', 'nav', 'footer', 'header']):
            elem.decompose()
        
        text = soup.get_text(separator='\n', strip=True)
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        return {
            'full': '\n'.join(lines),
            'paragraphs': [p.get_text(strip=True) for p in soup.find_all('p')],
            'word_count': len(' '.join(lines).split())
        }
    
    def extract_links(self, soup: BeautifulSoup, url: str) -> Dict:
        """Extract and categorize links"""
        links = {'internal': [], 'external': []}
        
        for a in soup.find_all('a', href=True):
            href = a['href']
            if href.startswith(('javascript:', 'mailto:', 'tel:', '#')):
                continue
            
            full_url = urljoin(url, href)
            link_data = {'url': full_url, 'text': a.get_text(strip=True)[:100]}
            
            if urlparse(full_url).netloc == self.domain:
                links['internal'].append(link_data)
            else:
                links['external'].append(link_data)
        
        return links
    
    def extract_headings(self, soup: BeautifulSoup) -> Dict:
        """Extract h1-h6 headings"""
        return {f'h{i}': [h.get_text(strip=True) for h in soup.find_all(f'h{i}')] 
                for i in range(1, 7)}
    
    def extract_forms(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract form structures"""
        forms = []
        for form in soup.find_all('form'):
            forms.append({
                'action': form.get('action', ''),
                'method': form.get('method', 'get').upper(),
                'fields': [{'name': inp.get('name', ''), 'type': inp.get('type', 'text')} 
                          for inp in form.find_all(['input', 'textarea', 'select'])]
            })
        return forms
    
    def extract_json_ld(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract JSON-LD structured data"""
        structured = []
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                structured.append(json.loads(script.string))
            except:
                pass
        return structured

# ═══════════════════════════════════════════════════════════════
# MULTI-FORMAT DATA EXPORTER
# ═══════════════════════════════════════════════════════════════

class DataExporter:
    """Export data to JSON, CSV, Excel, SQLite"""
    
    def __init__(self, output_dir: str = "exports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
    
    def export(self, data: List[Dict], format_type: str) -> str:
        """Export data in specified format"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if format_type == 'json':
            return self._export_json(data, f'crawl_{timestamp}.json')
        elif format_type == 'csv':
            return self._export_csv(data, f'crawl_{timestamp}.csv')
        elif format_type == 'excel':
            return self._export_excel(data, f'crawl_{timestamp}.xlsx')
        elif format_type == 'sqlite':
            return self._export_sqlite(data, f'crawl_{timestamp}.db')
    
    def _export_json(self, data: List[Dict], filename: str) -> str:
        filepath = self.output_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return str(filepath)
    
    def _export_csv(self, data: List[Dict], filename: str) -> str:
        filepath = self.output_dir / filename
        if not data:
            return str(filepath)
        
        flattened = []
        for record in data:
            flat = {
                'url': record['url'],
                'title': record.get('metadata', {}).get('title', ''),
                'description': record.get('metadata', {}).get('description', ''),
                'word_count': record.get('text', {}).get('word_count', 0),
                'tables_count': len(record.get('tables', [])),
                'links_count': len(record.get('links', {}).get('internal', [])),
            }
            flattened.append(flat)
        
        df = pd.DataFrame(flattened)
        df.to_csv(filepath, index=False)
        return str(filepath)
    
    def _export_excel(self, data: List[Dict], filename: str) -> str:
        filepath = self.output_dir / filename
        
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            # Main data sheet
            main_data = []
            for r in data:
                main_data.append({
                    'URL': r['url'],
                    'Title': r.get('metadata', {}).get('title', ''),
                    'Description': r.get('metadata', {}).get('description', '')[:200],
                    'Word Count': r.get('text', {}).get('word_count', 0),
                    'Tables': len(r.get('tables', [])),
                    'Links': len(r.get('links', {}).get('internal', []))
                })
            
            pd.DataFrame(main_data).to_excel(writer, sheet_name='Overview', index=False)
            
            # Tables sheet
            all_tables = []
            for r in data:
                for table in r.get('tables', []):
                    if table.get('data'):
                        df = pd.DataFrame(table['data'])
                        df['Source_URL'] = r['url']
                        all_tables.append(df)
            
            if all_tables:
                pd.concat(all_tables, ignore_index=True).to_excel(writer, sheet_name='Tables', index=False)
        
        return str(filepath)
    
    def _export_sqlite(self, data: List[Dict], filename: str) -> str:
        db_path = self.output_dir / filename
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        cursor.execute('''CREATE TABLE pages (
            id INTEGER PRIMARY KEY,
            url TEXT UNIQUE,
            title TEXT,
            description TEXT,
            word_count INTEGER
        )''')
        
        cursor.execute('''CREATE TABLE tables (
            id INTEGER PRIMARY KEY,
            page_id INTEGER,
            table_index INTEGER,
            row_count INTEGER,
            data_json TEXT
        )''')
        
        for record in data:
            cursor.execute('INSERT OR REPLACE INTO pages VALUES (NULL, ?, ?, ?, ?)',
                         (record['url'],
                          record.get('metadata', {}).get('title', ''),
                          record.get('metadata', {}).get('description', ''),
                          record.get('text', {}).get('word_count', 0)))
            
            page_id = cursor.lastrowid
            for table in record.get('tables', []):
                cursor.execute('INSERT INTO tables VALUES (NULL, ?, ?, ?, ?)',
                             (page_id, table['index'], table['rows'], 
                              json.dumps(table.get('data', []))))
        
        conn.commit()
        conn.close()
        return str(db_path)

# ═══════════════════════════════════════════════════════════════
# INDUSTRIAL WEB CRAWLER
# ═══════════════════════════════════════════════════════════════

class IndustrialCrawler:
    """Production-ready web crawler with data extraction"""
    
    def __init__(self, start_url: str, max_pages: int = 50, delay: float = 0.5, progress_callback=None):
        self.start_url = start_url
        self.max_pages = max_pages
        self.delay = delay
        self.progress_callback = progress_callback
        
        parsed = urlparse(start_url)
        self.domain = parsed.netloc
        
        self.visited_urls = set()
        self.url_queue = deque([start_url])
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        self.extractor = DataExtractor(start_url)
        self.extracted_data = []
        self.stats = {'pages': 0, 'errors': 0}
        
    def crawl(self) -> List[Dict]:
        """Main crawl loop with progress tracking"""
        logger.info(f"Starting crawl: {self.start_url}")
        
        while self.url_queue and self.stats['pages'] < self.max_pages:
            if self.stats['pages'] > 0:
                time.sleep(self.delay)
            
            url = self.url_queue.popleft()
            if url in self.visited_urls:
                continue
            
            self.visited_urls.add(url)
            
            try:
                response = self.session.get(url, timeout=10)
                response.raise_for_status()
                
                # Extract data
                data = self.extractor.extract_all(response.text, url)
                self.extracted_data.append(data)
                self.stats['pages'] += 1
                
                # Report progress
                progress_pct = (self.stats['pages'] / self.max_pages) * 100
                if self.progress_callback:
                    self.progress_callback({
                        'current': self.stats['pages'],
                        'total': self.max_pages,
                        'percentage': progress_pct,
                        'url': url
                    })
                
                # Find more links
                soup = BeautifulSoup(response.text, 'html.parser')
                for a in soup.find_all('a', href=True):
                    href = a['href']
                    if href.startswith(('#', 'javascript:', 'mailto:')):
                        continue
                    
                    full_url = urljoin(url, href)
                    if urlparse(full_url).netloc == self.domain and full_url not in self.visited_urls:
                        self.url_queue.append(full_url)
                
                logger.info(f"Crawled [{self.stats['pages']}/{self.max_pages}]: {url}")
                
            except Exception as e:
                self.stats['errors'] += 1
                logger.error(f"Error crawling {url}: {e}")
        
        return self.extracted_data

# ═══════════════════════════════════════════════════════════════
# GRAPHICAL USER INTERFACE
# ═══════════════════════════════════════════════════════════════

class IndustrialCrawlerGUI:
    """Modern GUI for industrial data crawler"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("🏭 Industrial Data Crawler Pro")
        self.root.geometry("1100x700")
        self.root.configure(bg='#0f172a')
        
        self.current_data = []
        self.is_crawling = False
        self.loop_active = False
        
        self.create_ui()
        
    def create_ui(self):
        # ═══ HEADER ═══
        header = tk.Frame(self.root, bg='#1e293b', height=90)
        header.pack(fill='x')
        header.pack_propagate(False)
        
        tk.Label(header, text="🏭 INDUSTRIAL DATA CRAWLER PRO", 
                font=('Arial', 20, 'bold'),
                bg='#1e293b', fg='#38bdf8').pack(pady=(10,2))
        tk.Label(header, text="Enterprise Data Extraction • Multi-Format Export • Real-Time Analytics", 
                font=('Arial', 9),
                bg='#1e293b', fg='#94a3b8').pack()
        tk.Label(header, text="Extract: Tables • Metadata • Links • Structured Data • Text Content", 
                font=('Arial', 8, 'italic'),
                bg='#1e293b', fg='#64748b').pack(pady=(2,0))
        
        # ═══ MAIN CONTENT ═══
        main = tk.Frame(self.root, bg='#0f172a')
        main.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Left panel - Controls (with scrollbar)
        left_container = tk.Frame(main, bg='#1e293b', width=400)
        left_container.pack(side='left', fill='y', padx=(0, 10))
        left_container.pack_propagate(False)
        
        # Create canvas and scrollbar for left panel
        canvas = tk.Canvas(left_container, bg='#1e293b', highlightthickness=0)
        scrollbar = tk.Scrollbar(left_container, orient='vertical', command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='#1e293b')
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Enable mouse wheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        self.build_controls(scrollable_frame)
        
        # Right panel - Results
        right_panel = tk.Frame(main, bg='#0f172a')
        right_panel.pack(side='right', fill='both', expand=True)
        
        self.build_results(right_panel)
        
        # ═══ STATUS BAR ═══
        status_bar = tk.Frame(self.root, bg='#1e293b', height=35)
        status_bar.pack(side='bottom', fill='x')
        status_bar.pack_propagate(False)
        
        self.status_label = tk.Label(status_bar, text="✅ Ready to Extract Data",
                                     font=('Arial', 9, 'bold'),
                                     bg='#1e293b', fg='#22c55e',
                                     anchor='w', padx=15)
        self.status_label.pack(side='left', fill='both', expand=True)
        
        tk.Button(status_bar, text="📁 Open Exports", command=self.open_exports,
                 bg='#0ea5e9', fg='white', font=('Arial', 9, 'bold'),
                 relief='flat', padx=15, cursor='hand2').pack(side='right', padx=10, pady=5)
    
    def build_controls(self, parent):
        # URL Input Section
        url_frame = tk.LabelFrame(parent, text=" 🌐 Target URLs ", 
                                 font=('Arial', 10, 'bold'),
                                 bg='#1e293b', fg='#38bdf8', 
                                 relief='ridge', bd=2, padx=10, pady=8)
        url_frame.pack(fill='x', padx=10, pady=(10,8))
        
        tk.Label(url_frame, text="Enter URLs (one per line):",
                bg='#1e293b', fg='#cbd5e1', font=('Arial', 9)).pack(anchor='w', pady=(0,3))
        
        self.urls_text = tk.Text(url_frame, height=4, width=40,
                                font=('Arial', 9), bg='#0f172a', fg='#e2e8f0',
                                insertbackground='#38bdf8', relief='solid', bd=2, wrap='word')
        self.urls_text.pack(fill='x')
        self.urls_text.insert('1.0', "https://example.com\nhttps://httpbin.org/html")
        
        # Settings
        settings_frame = tk.LabelFrame(parent, text=" ⚙️ Extraction Settings ", 
                                     font=('Arial', 10, 'bold'),
                                     bg='#1e293b', fg='#38bdf8',
                                     relief='ridge', bd=2, padx=10, pady=8)
        settings_frame.pack(fill='x', padx=10, pady=(0,8))
        
        # Max Pages
        row1 = tk.Frame(settings_frame, bg='#1e293b')
        row1.pack(fill='x', pady=3)
        tk.Label(row1, text="Max Pages/Site:", bg='#1e293b', fg='#cbd5e1', 
                font=('Arial', 9)).pack(side='left')
        self.max_pages_var = tk.IntVar(value=50)
        tk.Spinbox(row1, from_=1, to=500, textvariable=self.max_pages_var, 
                  width=12, font=('Arial', 9), 
                  bg='#0f172a', fg='#e2e8f0', buttonbackground='#1e293b').pack(side='right')
        
        # Delay
        row2 = tk.Frame(settings_frame, bg='#1e293b')
        row2.pack(fill='x', pady=3)
        tk.Label(row2, text="Delay (sec):", bg='#1e293b', fg='#cbd5e1',
                font=('Arial', 9)).pack(side='left')
        self.delay_var = tk.DoubleVar(value=0.5)
        tk.Spinbox(row2, from_=0.1, to=10, increment=0.1, 
                  textvariable=self.delay_var, width=12, font=('Arial', 9),
                  bg='#0f172a', fg='#e2e8f0', buttonbackground='#1e293b').pack(side='right')
        
        # Loop Mode
        loop_frame = tk.LabelFrame(parent, text=" 🔄 Loop Mode (Continuous) ", 
                                  font=('Arial', 10, 'bold'),
                                  bg='#1e293b', fg='#38bdf8',
                                  relief='ridge', bd=2, padx=10, pady=8)
        loop_frame.pack(fill='x', padx=10, pady=(0,8))
        
        self.loop_enabled_var = tk.BooleanVar(value=False)
        tk.Checkbutton(loop_frame, text="Enable Loop Mode (Run Continuously)", 
                      variable=self.loop_enabled_var,
                      font=('Arial', 9, 'bold'), bg='#1e293b', fg='#22c55e',
                      selectcolor='#0f172a', activebackground='#1e293b',
                      command=self.toggle_loop_mode).pack(anchor='w', pady=3)
        
        row3 = tk.Frame(loop_frame, bg='#1e293b')
        row3.pack(fill='x', pady=3)
        tk.Label(row3, text="Loop Interval (min):", bg='#1e293b', fg='#cbd5e1',
                font=('Arial', 9)).pack(side='left')
        self.loop_interval_var = tk.IntVar(value=60)
        self.loop_interval_spin = tk.Spinbox(row3, from_=1, to=1440, 
                                            textvariable=self.loop_interval_var, 
                                            width=12, font=('Arial', 9),
                                            bg='#0f172a', fg='#e2e8f0', 
                                            buttonbackground='#1e293b', state='disabled')
        self.loop_interval_spin.pack(side='right')
        
        self.auto_export_var = tk.BooleanVar(value=True)
        self.auto_export_check = tk.Checkbutton(loop_frame, text="Auto-export after each cycle", 
                                               variable=self.auto_export_var,
                                               font=('Arial', 8), bg='#1e293b', fg='#cbd5e1',
                                               selectcolor='#0f172a', activebackground='#1e293b',
                                               state='disabled')
        self.auto_export_check.pack(anchor='w', pady=2)
        
        # Export Format Selector
        export_frame = tk.LabelFrame(parent, text=" 📤 Export Formats (Multi-Select) ", 
                                   font=('Arial', 10, 'bold'),
                                   bg='#1e293b', fg='#38bdf8',
                                   relief='ridge', bd=2, padx=10, pady=8)
        export_frame.pack(fill='x', padx=10, pady=(0,8))
        
        tk.Label(export_frame, text="Hold Ctrl/Cmd to select multiple formats:",
                bg='#1e293b', fg='#94a3b8', font=('Arial', 8, 'italic')).pack(anchor='w', pady=(0,3))
        
        # Create Listbox with scrollbar
        listbox_frame = tk.Frame(export_frame, bg='#1e293b')
        listbox_frame.pack(fill='x')
        
        scrollbar = tk.Scrollbar(listbox_frame, bg='#0f172a')
        scrollbar.pack(side='right', fill='y')
        
        self.export_listbox = tk.Listbox(listbox_frame, 
                                        selectmode='multiple',
                                        height=4,
                                        font=('Arial', 9, 'bold'),
                                        bg='#0f172a', fg='#e2e8f0',
                                        selectbackground='#38bdf8',
                                        selectforeground='#0f172a',
                                        relief='solid', bd=2,
                                        yscrollcommand=scrollbar.set)
        self.export_listbox.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=self.export_listbox.yview)
        
        # Add format options
        formats = ["📊 Excel (.xlsx)", "📄 JSON (.json)", "📑 CSV (.csv)", "💾 SQLite (.db)"]
        for fmt in formats:
            self.export_listbox.insert('end', fmt)
        
        # Select Excel by default
        self.export_listbox.selection_set(0)
        
        # Quick select buttons
        btn_row = tk.Frame(export_frame, bg='#1e293b')
        btn_row.pack(fill='x', pady=(8,0))
        
        tk.Button(btn_row, text="✓ Select All", command=self.select_all_formats,
                 bg='#0ea5e9', fg='white', font=('Arial', 8, 'bold'),
                 relief='flat', padx=10, pady=3, cursor='hand2').pack(side='left', padx=(0,5))
        
        tk.Button(btn_row, text="✗ Clear All", command=self.select_no_formats,
                 bg='#64748b', fg='white', font=('Arial', 8, 'bold'),
                 relief='flat', padx=10, pady=3, cursor='hand2').pack(side='left')
        
        # Action Buttons - COMPACT BUT VISIBLE
        btn_frame = tk.Frame(parent, bg='#1e293b')
        btn_frame.pack(fill='x', padx=10, pady=15)
        
        # START BUTTON
        self.start_btn = tk.Button(btn_frame, text="▶️  START EXTRACTION", 
                                   command=self.start_crawl,
                                   font=('Arial', 12, 'bold'), 
                                   bg='#22c55e', fg='white',
                                   activebackground='#16a34a', 
                                   relief='raised', bd=3,
                                   padx=20, pady=12, cursor='hand2')
        self.start_btn.pack(fill='x', pady=(0,8))
        
        # STOP BUTTON
        self.stop_btn = tk.Button(btn_frame, text="⏹️  STOP LOOP", 
                                 command=self.stop_loop,
                                 font=('Arial', 10, 'bold'), 
                                 bg='#ef4444', fg='white',
                                 activebackground='#dc2626', 
                                 relief='raised', bd=2,
                                 padx=15, pady=8, cursor='hand2', 
                                 state='disabled')
        self.stop_btn.pack(fill='x', pady=(0,8))
        
        # EXPORT BUTTON
        tk.Button(btn_frame, text="💾  EXPORT DATA", 
                 command=self.export_data,
                 font=('Arial', 10, 'bold'), 
                 bg='#8b5cf6', fg='white',
                 activebackground='#7c3aed', 
                 relief='raised', bd=2,
                 padx=15, pady=8, cursor='hand2').pack(fill='x')
    
    def toggle_loop_mode(self):
        """Enable/disable loop mode controls"""
        if self.loop_enabled_var.get():
            self.loop_interval_spin.config(state='normal')
            self.auto_export_check.config(state='normal')
        else:
            self.loop_interval_spin.config(state='disabled')
            self.auto_export_check.config(state='disabled')
    
    def build_results(self, parent):
        # Stats Panel
        stats_frame = tk.LabelFrame(parent, text=" 📊 Live Statistics ", 
                                   font=('Arial', 12, 'bold'),
                                   bg='#1e293b', fg='#38bdf8',
                                   relief='ridge', bd=3, padx=15, pady=10)
        stats_frame.pack(fill='x', pady=(0,10))
        
        stats_grid = tk.Frame(stats_frame, bg='#1e293b')
        stats_grid.pack(fill='x')
        
        self.stat_labels = {}
        stats = [
            ("📄 Pages", "pages"),
            ("📋 Tables", "tables"),
            ("🔗 Links", "links"),
            ("📝 Words", "words")
        ]
        
        for idx, (label, key) in enumerate(stats):
            frame = tk.Frame(stats_grid, bg='#0f172a', relief='solid', bd=2)
            frame.grid(row=0, column=idx, padx=5, pady=5, sticky='ew')
            stats_grid.grid_columnconfigure(idx, weight=1)
            
            tk.Label(frame, text=label, bg='#0f172a', fg='#94a3b8',
                    font=('Arial', 10)).pack(pady=(8,2))
            self.stat_labels[key] = tk.Label(frame, text="0", bg='#0f172a', fg='#38bdf8',
                                            font=('Arial', 20, 'bold'))
            self.stat_labels[key].pack(pady=(0,8))
        
        # Export Summary Panel
        export_summary_frame = tk.LabelFrame(parent, text=" 💾 Exported Files ", 
                                            font=('Arial', 11, 'bold'),
                                            bg='#1e293b', fg='#a78bfa',
                                            relief='ridge', bd=2, padx=10, pady=10)
        export_summary_frame.pack(fill='x', pady=(0,10))
        
        self.export_badges_frame = tk.Frame(export_summary_frame, bg='#1e293b')
        self.export_badges_frame.pack(fill='x')
        
        # Initialize with "No exports yet" message
        self.no_exports_label = tk.Label(self.export_badges_frame, 
                                         text="📭 No files exported yet",
                                         font=('Arial', 10), bg='#1e293b', fg='#64748b')
        self.no_exports_label.pack(pady=5)
        
        self.exported_files_tracking = []  # Track exported files
        
        # Progress Log
        log_frame = tk.LabelFrame(parent, text=" 📈 Extraction Progress ", 
                                 font=('Arial', 12, 'bold'),
                                 bg='#1e293b', fg='#38bdf8',
                                 relief='ridge', bd=3, padx=10, pady=10)
        log_frame.pack(fill='both', expand=True)
        
        self.progress_text = scrolledtext.ScrolledText(log_frame, height=30,
                                                      font=('Consolas', 10),
                                                      bg='#0f172a', fg='#22c55e',
                                                      insertbackground='#38bdf8',
                                                      relief='flat', wrap='word')
        self.progress_text.pack(fill='both', expand=True)
    
    def log(self, message, color='#22c55e'):
        """Add message to progress log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.progress_text.insert('end', f"[{timestamp}] {message}\n")
        self.progress_text.see('end')
        self.root.update()
    
    def update_stats(self):
        """Update statistics display"""
        if not self.current_data:
            return
        
        total_tables = sum(len(d.get('tables', [])) for d in self.current_data)
        total_links = sum(len(d.get('links', {}).get('internal', [])) + 
                         len(d.get('links', {}).get('external', [])) 
                         for d in self.current_data)
        total_words = sum(d.get('text', {}).get('word_count', 0) for d in self.current_data)
        
        self.stat_labels['pages'].config(text=str(len(self.current_data)))
        self.stat_labels['tables'].config(text=str(total_tables))
        self.stat_labels['links'].config(text=str(total_links))
        self.stat_labels['words'].config(text=f"{total_words:,}")
    
    def start_crawl(self):
        """Start crawling in background thread"""
        if self.is_crawling:
            messagebox.showwarning("Already Running", "Extraction in progress!")
            return
        
        urls_text = self.urls_text.get('1.0', 'end').strip()
        if not urls_text:
            messagebox.showerror("Error", "Please enter at least one URL!")
            return
        
        urls = [u.strip() for u in urls_text.split('\n') if u.strip()]
        urls = [u if u.startswith(('http://', 'https://')) else 'https://' + u for u in urls]
        
        self.progress_text.delete('1.0', 'end')
        self.is_crawling = True
        self.loop_active = self.loop_enabled_var.get()
        
        # Update UI
        self.start_btn.config(state='disabled')
        if self.loop_active:
            self.stop_btn.config(state='normal')
        
        threading.Thread(target=self._crawl_thread, args=(urls,), daemon=True).start()
    
    def stop_loop(self):
        """Stop the loop mode"""
        self.loop_active = False
        self.stop_btn.config(state='disabled')
        self.log("⏹️  Loop stopped by user")
        self.status_label.config(text="⏹️  Loop stopped", fg='#f59e0b')
    
    def _crawl_thread(self, urls):
        """Background crawling thread with loop support"""
        cycle_count = 0
        
        while True:
            cycle_count += 1
            
            try:
                if self.loop_active:
                    self.log(f"\n{'═'*70}")
                    self.log(f"🔄 LOOP CYCLE #{cycle_count}")
                    self.log(f"{'═'*70}")
                else:
                    self.log("═" * 70)
                    self.log(f"🏭 BATCH EXTRACTION STARTED")
                    self.log("═" * 70)
                
                self.log(f"📝 URLs to process: {len(urls)}")
                self.log(f"⚙️  Max pages per site: {self.max_pages_var.get()}")
                self.status_label.config(text=f"🔄 Processing {len(urls)} sites...", fg='#f59e0b')
                
                batch_data = []
                batch_start = time.time()
                
                for idx, url in enumerate(urls, 1):
                    if not self.is_crawling:
                        break
                    
                    self.log(f"\n{'─'*70}")
                    self.log(f"[{idx}/{len(urls)}] 🌐 {url}")
                    
                    site_start = time.time()
                    
                    # Progress callback for this site
                    def progress_update(data):
                        pct = data['percentage']
                        current = data['current']
                        total = data['total']
                        
                        # Create visual progress bar
                        bar_length = 30
                        filled = int(bar_length * pct / 100)
                        bar = '█' * filled + '░' * (bar_length - filled)
                        
                        self.status_label.config(
                            text=f"🔄 [{idx}/{len(urls)}] {pct:.1f}% | {current}/{total} pages | {url[:50]}...",
                            fg='#f59e0b'
                        )
                        
                        # Update progress in log
                        progress_msg = f"📊 Progress: [{bar}] {pct:.1f}% ({current}/{total})"
                        # Clear previous line and write new one
                        self.progress_text.delete('end-2l', 'end-1l')
                        self.progress_text.insert('end', progress_msg + '\n')
                        self.progress_text.see('end')
                        self.root.update()
                    
                    try:
                        crawler = IndustrialCrawler(
                            url, 
                            self.max_pages_var.get(), 
                            self.delay_var.get(),
                            progress_callback=progress_update
                        )
                        site_data = crawler.crawl()
                        
                        batch_data.extend(site_data)
                        
                        duration = time.time() - site_start
                        self.log(f"✅ Complete | {len(site_data)} pages | {timedelta(seconds=int(duration))}")
                        
                    except Exception as e:
                        self.log(f"❌ Error: {str(e)}")
                        logger.exception(f"Error crawling {url}")
                
                # Store combined data
                self.current_data.extend(batch_data)
                
                batch_duration = time.time() - batch_start
                
                self.log(f"\n{'═'*70}")
                self.log(f"✅ BATCH COMPLETE!")
                self.log(f"📊 Total sites: {len(urls)} | Pages: {len(batch_data)}")
                self.log(f"📋 Tables: {sum(len(d.get('tables', [])) for d in batch_data)}")
                self.log(f"🔗 Links: {sum(len(d.get('links', {}).get('internal', [])) for d in batch_data)}")
                self.log(f"⏱️  Cycle time: {timedelta(seconds=int(batch_duration))}")
                
                # Auto-export if enabled
                if self.loop_active and self.auto_export_var.get():
                    self.log(f"\n💾 Auto-exporting data...")
                    try:
                        # Auto-export uses all selected formats
                        self.export_data(silent=True)
                        self.log(f"✅ Auto-export complete")
                    except Exception as e:
                        self.log(f"❌ Auto-export failed: {str(e)}")
                
                self.update_stats()
                
                # Check if loop should continue
                if not self.loop_active:
                    self.log("═" * 70)
                    self.status_label.config(text=f"✅ Complete! {len(self.current_data)} total records", 
                                           fg='#22c55e')
                    break
                
                # Wait for next cycle
                interval = self.loop_interval_var.get() * 60
                self.log(f"\n⏳ Next cycle in {self.loop_interval_var.get()} minutes...")
                self.status_label.config(text=f"⏳ Waiting {self.loop_interval_var.get()}min until next cycle", 
                                       fg='#f59e0b')
                
                # Sleep in chunks to allow stopping
                for _ in range(interval):
                    if not self.loop_active:
                        break
                    time.sleep(1)
                
                if not self.loop_active:
                    break
                
            except Exception as e:
                self.log(f"\n❌ CYCLE ERROR: {str(e)}")
                logger.exception("Cycle error")
                
                if not self.loop_active:
                    self.status_label.config(text=f"❌ Error: {str(e)}", fg='#ef4444')
                    break
        
        # Cleanup
        self.is_crawling = False
        self.loop_active = False
        self.start_btn.config(state='normal')
        self.stop_btn.config(state='disabled')
    
    def select_all_formats(self):
        """Select all export formats in listbox"""
        self.export_listbox.selection_set(0, 'end')
    
    def select_no_formats(self):
        """Deselect all export formats in listbox"""
        self.export_listbox.selection_clear(0, 'end')
    
    def update_export_badges(self, exported_files):
        """Update the export summary panel with format badges"""
        # Clear existing badges
        for widget in self.export_badges_frame.winfo_children():
            widget.destroy()
        
        # Hide "no exports" message if there are files
        if exported_files:
            # Track all exported files
            self.exported_files_tracking.extend(exported_files)
            
            # Count by format
            format_counts = {}
            for name, _ in self.exported_files_tracking:
                format_counts[name] = format_counts.get(name, 0) + 1
            
            # Create badges for each format
            format_colors = {
                'Excel': ('#10b981', '#065f46'),  # Green
                'JSON': ('#f59e0b', '#78350f'),   # Orange
                'CSV': ('#3b82f6', '#1e3a8a'),    # Blue
                'SQLite': ('#8b5cf6', '#4c1d95')  # Purple
            }
            
            format_icons = {
                'Excel': '📊',
                'JSON': '📄',
                'CSV': '📑',
                'SQLite': '💾'
            }
            
            for idx, (format_name, count) in enumerate(format_counts.items()):
                bg_color, text_color = format_colors.get(format_name, ('#64748b', '#1e293b'))
                icon = format_icons.get(format_name, '📁')
                
                badge_frame = tk.Frame(self.export_badges_frame, bg=bg_color, relief='raised', bd=2)
                badge_frame.pack(side='left', padx=5, pady=5)
                
                tk.Label(badge_frame, text=f"{icon} {format_name}",
                        font=('Arial', 10, 'bold'), bg=bg_color, fg='white',
                        padx=10, pady=3).pack()
                
                tk.Label(badge_frame, text=f"{count} file(s)",
                        font=('Arial', 8), bg=bg_color, fg='white',
                        padx=10, pady=2).pack()
        else:
            # Show "no exports" message
            self.no_exports_label = tk.Label(self.export_badges_frame, 
                                            text="📭 No files exported yet",
                                            font=('Arial', 10), bg='#1e293b', fg='#64748b')
            self.no_exports_label.pack(pady=5)
    
    def export_data(self, silent=False):
        """Export collected data to selected formats"""
        if not self.current_data:
            if not silent:
                messagebox.showwarning("No Data", "Please extract data first!")
            return
        
        # Get selected formats from listbox
        selected_indices = self.export_listbox.curselection()
        
        format_map = {
            0: ('Excel', 'excel'),
            1: ('JSON', 'json'),
            2: ('CSV', 'csv'),
            3: ('SQLite', 'sqlite')
        }
        
        selected_formats = [format_map[i] for i in selected_indices]
        
        if not selected_formats:
            if not silent:
                messagebox.showwarning("No Format Selected", 
                                     "Please select at least one export format from the list!\n\n" +
                                     "Tip: Hold Ctrl/Cmd and click to select multiple.")
            return
        
        try:
            exporter = DataExporter()
            exported_files = []
            
            if not silent:
                self.log(f"\n📤 Exporting {len(self.current_data)} records to {len(selected_formats)} format(s)...")
            
            for format_name, format_type in selected_formats:
                try:
                    if not silent:
                        self.log(f"   ⏳ Exporting {format_name}...")
                    
                    filepath = exporter.export(self.current_data, format_type)
                    exported_files.append((format_name, filepath))
                    
                    if not silent:
                        self.log(f"   ✅ {format_name}: {filepath}")
                    
                except Exception as e:
                    if not silent:
                        self.log(f"   ❌ {format_name} failed: {str(e)}")
                    logger.exception(f"{format_name} export error")
            
            # Update UI badges
            if exported_files:
                self.update_export_badges(exported_files)
            
            if not silent and exported_files:
                self.log(f"\n✅ Export complete! {len(exported_files)} file(s) created")
                
                # Show file list in message box
                files_text = '\n'.join([f"{name}: {path}" for name, path in exported_files])
                messagebox.showinfo("Export Complete", 
                                  f"Exported to {len(exported_files)} format(s):\n\n{files_text}")
            
        except Exception as e:
            if not silent:
                self.log(f"❌ Export failed: {str(e)}")
                messagebox.showerror("Export Error", str(e))
            logger.exception("Export error")
    
    def open_exports(self):
        """Open exports folder"""
        try:
            os.startfile("exports")
        except:
            messagebox.showinfo("Exports", "Exports saved in 'exports/' folder")

# ═══════════════════════════════════════════════════════════════
# MAIN APPLICATION
# ═══════════════════════════════════════════════════════════════

def main():
    """Launch the Industrial Data Crawler"""
    root = tk.Tk()
    app = IndustrialCrawlerGUI(root)
    root.mainloop()

if __name__ == "__main__":
    logger.info("═" * 70)
    logger.info("🏭 INDUSTRIAL DATA CRAWLER PRO - Starting")
    logger.info("═" * 70)
    main()
