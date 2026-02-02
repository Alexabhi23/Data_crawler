# 🏭 Industrial Data Crawler Pro

**Single-file, enterprise-grade web data extraction system**

## ✨ Highlights

- **Self-Contained** - Everything in one `crawler_app.py` file (700+ lines)
- **Modern UI** - Two-panel layout with live stats
- **Enhanced Extraction** - Tables, metadata, links, structured data
- **Multi-Format Export** - JSON, CSV, Excel, SQLite

## 🚀 Quick Start

```bash
# Install dependencies
py -m pip install -r requirements.txt

# Run the crawler
py crawler_app.py
```

## � GitHub Deployment

Want to push this project to GitHub? See [`GITHUB_PUSH_INSTRUCTIONS.md`](GITHUB_PUSH_INSTRUCTIONS.md) for detailed steps including:
- Repository creation guide
- Ready-to-use descriptions
- Push commands and setup
- Recommended GitHub topics

## �📦 What's Included

**Single File:** `crawler_app.py`
- Data extraction engine
- Multi-format exporter
- Web crawler core
- Modern GUI

**Dependencies:**
- `requests`, `beautifulsoup4` - Web crawling
- `pandas`, `openpyxl` - Data processing & Excel
- `lxml` - Fast HTML parsing

## 💡 Features

### Data Extraction
- 📋 **Tables** - Automatic detection with pandas
- 🏷️ **Metadata** - SEO tags, Open Graph
- 📊 **Structured Data** - JSON-LD extraction
- 📝 **Text** - Clean paragraphs + word counts
- 🔗 **Links** - Internal/external categorization
- 📑 **Lists** - Ordered and unordered
- 📄 **Forms** - Input field analysis

### Export Formats
| Format | Features |
|--------|----------|
| **Excel** | Multi-sheet workbooks (Overview + Tables) |
| **JSON** | Structured hierarchical data |
| **CSV** | Flat table for analysis |
| **SQLite** | Relational database with indexes |

### UI Layout

```
Left Panel (Controls)    Right Panel (Results)
├── URL Input           ├── Live Stats (4 cards)
├── Settings            ├── Progress Log
├── Export Format       └── Real-time Updates
└── Action Buttons
```

## 📖 Usage

1. **Extract**: Enter URL → Configure settings → Click START
2. **Monitor**: Watch live stats and progress log
3. **Export**: Select format → Click EXPORT → Files in `exports/`

## 🎯 Use Cases

- Market research & competitor analysis
- SEO metadata collection
- Content aggregation
- Data science dataset creation
- Business intelligence

## 📊 Sample Output

### JSON Structure
```json
{
  "url": "...",
  "metadata": {"title": "...", "description": "..."},
  "tables": [{"rows": 10, "cols": 3, "data": [...]}],
  "text": {"paragraphs": [...], "word_count": 1234},
  "links": {"internal": [...], "external": [...]}
}
```

### Excel Sheets
- **Overview**: URLs, titles, word counts, table/link counts
- **Tables**: Extracted table data with source URLs

## 🏗️ Architecture

**Self-Contained Design:**
```
crawler_app.py (700+ lines)
├── DataExtractor        → HTML parsing & extraction
├── DataExporter         → Multi-format export engine
├── IndustrialCrawler   → Core crawling logic
└── IndustrialCrawlerGUI → Modern UI (Tkinter)
```

**No External Files Needed!**

## ⚡ What's New

### v2.0 - Consolidated Edition
✅ Merged all modules into single file  
✅ Redesigned UI with two-panel layout  
✅ Enhanced data extraction (forms, lists, headings)  
✅ Live statistics dashboard  
✅ Improved error handling  
✅ Better logging system  

### Legacy Files (Archived)
The `Layout_extracter &Security_cheecker for web/` folder contains the original modular files:
- 📦 `polite_crawler_enhanced.py` - Original polite crawler (merged)
- 📦 `security_crawler_enhanced.py` - Original security crawler (merged)

These files are **no longer required** to run the application. All functionality has been consolidated into `crawler_app.py`.


## 📁 Project Structure

```
wflow/
├── crawler_app.py                            # Main application (all-in-one) ⭐
├── requirements.txt                          # Dependencies
├── exports/                                  # Exported data files
├── industrial_crawler.log                    # Application logs
├── README.md                                 # This file
├── GITHUB_PUSH_INSTRUCTIONS.md               # GitHub deployment guide
├── .github-repo-description.txt              # Repository descriptions
└── Layout_extracter &Security_cheecker for web/  # Legacy files (archived)
    ├── polite_crawler_enhanced.py            #   Original polite crawler
    └── security_crawler_enhanced.py          #   Original security crawler
```

> **Note:** The files in `Layout_extracter &Security_cheecker for web/` are the original modules that have been **merged into `crawler_app.py`**. They are kept for reference but are no longer needed to run the application.

## 🔧 Configuration

Adjust settings in the UI:
- **Max Pages**: 1-500 pages per crawl
- **Delay**: 0.1-10 seconds between requests
- **Export Format**: Choose from 4 formats

## 📝 Logging

All activity logged to: `industrial_crawler.log`

Format: `timestamp - level - message`

## 🚧 Roadmap

- [ ] Session resume capability
- [ ] Proxy rotation support
- [ ] JavaScript rendering (Selenium)
- [ ] Custom CSS selector builder
- [ ] Automatic pagination detection

## 📞 Support

- Check `walkthrough.md` for detailed documentation
- See `GITHUB_PUSH_INSTRUCTIONS.md` for GitHub deployment help

---

**Built with Python • Tkinter • Pandas • BeautifulSoup**

**Version 2.0** - Consolidated Single-File Edition
