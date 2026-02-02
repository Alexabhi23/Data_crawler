import os
import time
import json
import logging
import ssl
import socket
import requests
import jsbeautifier
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser
from collections import deque
from datetime import datetime
from typing import Dict, List, Callable, Optional
import re

# Inherit from enhanced crawler
import sys
sys.path.append(os.path.dirname(__file__))
try:
    from polite_crawler_enhanced import CrawlerStats, PoliteCrawler
except:
    pass  # Will define standalone if import fails

# Configuration
MAX_PAGES_TO_CRAWL = 10
DELAY_BETWEEN_PAGES = 1.5

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('security_crawler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Sensitive files to check
SENSITIVE_FILES = [
    '.git/config', '.git/HEAD', '.env', '.env.local', '.env.production',
    'config.php', 'wp-config.php', 'database.yml', 'secrets.json',
    '.htaccess', 'web.config', 'phpinfo.php', 'admin/', 'backup.sql',
    '.DS_Store', 'composer.json', 'package.json', '.npmrc',
    'id_rsa', 'id_rsa.pub', 'authorized_keys', 'credentials.json',
    'Dockerfile', 'docker-compose.yml', '.dockerignore'
]

# Vulnerable library patterns
VULNERABLE_PATTERNS = {
    'jquery-1.': 'jQuery version < 3.0 has known XSS vulnerabilities',
    'jquery-2.': 'jQuery 2.x may have security issues',
    'angular.js/1.0': 'AngularJS 1.0.x has critical vulnerabilities',
    'angular.js/1.1': 'AngularJS 1.1.x has critical vulnerabilities',
    'bootstrap/3.': 'Bootstrap 3.x has XSS vulnerabilities',
    'moment.js': 'Moment.js is deprecated, use dayjs or date-fns'
}

# SQL Injection patterns in URLs
SQL_INJECTION_PATTERNS = [
    r"id=\d+", r"page=\d+", r"user=", r"search=", r"q=",
    r"query=", r"keyword=", r"login=", r"admin="
]

# Common CMS detection patterns
CMS_PATTERNS = {
    'WordPress': ['/wp-content/', '/wp-includes/', '/wp-admin/'],
    'Drupal': ['/sites/default/', '/modules/', '/themes/'],
    'Joomla': ['/administrator/', '/components/', '/templates/'],
    'Magento': ['/skin/', '/js/mage/', '/media/catalog/']
}

class SecurityCrawler(PoliteCrawler):
    """Enhanced security-focused web crawler"""
    
    def __init__(self, start_url: str, max_pages: int = 10, delay: float = 1.5,
                 progress_callback: Optional[Callable] = None):
        super().__init__(start_url, max_pages, delay, progress_callback)
        
        self.security_issues = {
            'critical': [],
            'high': [],
            'medium': [],
            'low': [],
            'info': []
        }
        
        self.cms_detected = None
        self.subdomains_found = set()
        
    def setup_folders(self):
        """Create folder structure including security reports"""
        super().setup_folders()
        self.folders["reports"] = f"{self.domain}/security_reports"
        os.makedirs(self.folders["reports"], exist_ok=True)
        
    def check_ssl_certificate(self):
        """Check SSL/TLS certificate validity"""
        try:
            context = ssl.create_default_context()
            with socket.create_connection((self.domain, 443), timeout=5) as sock:
                with context.wrap_socket(sock, server_hostname=self.domain) as ssock:
                    cert = ssock.getpeercert()
                    
                    # Check certificate expiry
                    not_after = datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z')
                    days_left = (not_after - datetime.now()).days
                    
                    if days_left < 30:
                        self.security_issues['high'].append({
                            'type': 'SSL Certificate Expiring',
                            'details': f'Certificate expires in {days_left} days',
                            'location': self.domain,
                            'severity_score': 7.5,
                            'recommendation': 'Renew SSL certificate immediately'
                        })
                    elif days_left < 90:
                        self.security_issues['medium'].append({
                            'type': 'SSL Certificate Expiring Soon',
                            'details': f'Certificate expires in {days_left} days',
                            'location': self.domain,
                            'severity_score': 5.0,
                            'recommendation': 'Plan SSL certificate renewal'
                        })
                    else:
                        self.security_issues['info'].append({
                            'type': 'SSL Certificate Valid',
                            'details': f'Certificate expires in {days_left} days',
                            'location': self.domain
                        })
                    
                    # Check for TLS version
                    tls_version = ssock.version()
                    if tls_version in ['TLSv1', 'TLSv1.1']:
                        self.security_issues['high'].append({
                            'type': 'Outdated TLS Version',
                            'details': f'Using {tls_version} which is deprecated',
                            'location': self.domain,
                            'severity_score': 7.0,
                            'recommendation': 'Upgrade to TLS 1.2 or 1.3'
                        })
                        
                    return True
                    
        except ssl.SSLError as e:
            self.security_issues['critical'].append({
                'type': 'SSL/TLS Error',
                'details': str(e),
                'location': self.domain,
                'severity_score': 9.0,
                'recommendation': 'Fix SSL configuration immediately'
            })
            return False
        except Exception as e:
            self.security_issues['info'].append({
                'type': 'SSL Check Failed',
                'details': str(e),
                'location': self.domain
            })
            return False
            
    def check_security_headers(self, response, url):
        """Check for important security headers"""
        headers = response.headers
        
        # HSTS
        if 'Strict-Transport-Security' not in headers:
            self.security_issues['high'].append({
                'type': 'Missing HSTS Header',
                'details': 'HSTS header not set - vulnerable to SSL stripping attacks',
                'location': url,
                'severity_score': 7.0,
                'owasp': 'A05:2021 – Security Misconfiguration',
                'recommendation': 'Add header: Strict-Transport-Security: max-age=31536000; includeSubDomains'
            })
        
        # Clickjacking protection
        if 'X-Frame-Options' not in headers and 'Content-Security-Policy' not in headers:
            self.security_issues['medium'].append({
                'type': 'Missing Clickjacking Protection',
                'details': 'Neither X-Frame-Options nor CSP frame-ancestors set',
                'location': url,
                'severity_score': 6.0,
                'owasp': 'A05:2021 – Security Misconfiguration',
                'recommendation': 'Add header: X-Frame-Options: SAMEORIGIN or use CSP'
            })
        
        # MIME sniffing
        if 'X-Content-Type-Options' not in headers:
            self.security_issues['medium'].append({
                'type': 'Missing X-Content-Type-Options',
                'details': 'MIME-sniffing attacks possible',
                'location': url,
                'severity_score': 5.0,
                'recommendation': 'Add header: X-Content-Type-Options: nosniff'
            })
        
        # CSP
        if 'Content-Security-Policy' not in headers:
            self.security_issues['medium'].append({
                'type': 'Missing Content Security Policy',
                'details': 'No CSP header - vulnerable to XSS attacks',
                'location': url,
                'severity_score': 6.5,
                'owasp': 'A03:2021 – Injection',
                'recommendation': 'Implement a strict Content-Security-Policy'
            })
        
        # X-XSS-Protection (legacy but good to have)
        if 'X-XSS-Protection' not in headers:
            self.security_issues['low'].append({
                'type': 'Missing X-XSS-Protection',
                'details': 'Legacy XSS protection header not set',
                'location': url,
                'severity_score': 3.0,
                'recommendation': 'Add header: X-XSS-Protection: 1; mode=block'
            })
        
        # Referrer Policy
        if 'Referrer-Policy' not in headers:
            self.security_issues['low'].append({
                'type': 'Missing Referrer-Policy',
                'details': 'No referrer policy set - may leak sensitive URLs',
                'location': url,
                'severity_score': 3.5,
                'recommendation': 'Add header: Referrer-Policy: strict-origin-when-cross-origin'
            })
        
        # Permissions Policy (formerly Feature-Policy)
        if 'Permissions-Policy' not in headers and 'Feature-Policy' not in headers:
            self.security_issues['info'].append({
                'type': 'Missing Permissions-Policy',
                'details': 'No permissions policy defined',
                'location': url,
                'recommendation': 'Consider adding Permissions-Policy header'
            })
            
    def check_sensitive_files(self):
        """Check for exposed sensitive files"""
        logger.info("Checking for exposed sensitive files...")
        
        for file in SENSITIVE_FILES:
            url = urljoin(self.base_url, file)
            try:
                response = self.session.get(url, timeout=3, allow_redirects=False)
                if response.status_code == 200:
                    self.security_issues['critical'].append({
                        'type': 'Sensitive File Exposed',
                        'details': f'Accessible file: {file}',
                        'location': url,
                        'severity_score': 9.5,
                        'owasp': 'A01:2021 – Broken Access Control',
                        'recommendation': f'Block public access to {file}'
                    })
                    logger.warning(f"EXPOSED: {file}")
                time.sleep(0.3)  # Be polite
            except:
                pass
                
    def check_form_security(self, soup, url):
        """Check form security"""
        forms = soup.find_all('form')
        
        for form in forms:
            action = form.get('action', '')
            method = form.get('method', 'GET').upper()
            
            # Mixed content
            if action.startswith('http://') and url.startswith('https://'):
                self.security_issues['high'].append({
                    'type': 'Mixed Content Form',
                    'details': 'Form on HTTPS page submits to HTTP endpoint',
                    'location': url,
                    'form_action': action,
                    'severity_score': 7.5,
                    'owasp': 'A02:2021 – Cryptographic Failures',
                    'recommendation': 'Use HTTPS for form action'
                })
            
            # Password autocomplete
            password_fields = form.find_all('input', {'type': 'password'})
            if password_fields:
                for field in password_fields:
                    if field.get('autocomplete', '').lower() != 'off':
                        self.security_issues['low'].append({
                            'type': 'Password Autocomplete Enabled',
                            'details': 'Password field allows autocomplete',
                            'location': url,
                            'severity_score': 3.5,
                            'recommendation': 'Add autocomplete="off" to password fields'
                        })
                        break
            
            # CSRF token check
            if method == 'POST':
                csrf_field = form.find('input', {'name': re.compile(r'csrf|token|_token', re.I)})
                if not csrf_field:
                    self.security_issues['medium'].append({
                        'type': 'Potential Missing CSRF Protection',
                        'details': 'POST form without visible CSRF token',
                        'location': url,
                        'severity_score': 6.0,
                        'owasp': 'A01:2021 – Broken Access Control',
                        'recommendation': 'Implement CSRF tokens for all forms'
                    })
                    
    def check_vulnerable_libraries(self, soup, url):
        """Check for known vulnerable JavaScript libraries"""
        scripts = soup.find_all('script', src=True)
        
        for script in scripts:
            src = script.get('src', '')
            for pattern, issue in VULNERABLE_PATTERNS.items():
                if pattern in src.lower():
                    self.security_issues['high'].append({
                        'type': 'Vulnerable JavaScript Library',
                        'details': issue,
                        'location': url,
                        'script_src': src,
                        'severity_score': 7.0,
                        'owasp': 'A06:2021 – Vulnerable and Outdated Components',
                        'recommendation': 'Update to latest secure version'
                    })
                    
    def check_cookies(self, response, url):
        """Check cookie security settings"""
        cookies = response.cookies
        
        for cookie in cookies:
            issues = []
            
            if not cookie.secure and url.startswith('https://'):
                issues.append('Missing Secure flag on HTTPS site')
            
            if not cookie.has_nonstandard_attr('HttpOnly'):
                issues.append('Missing HttpOnly flag - vulnerable to XSS cookie theft')
            
            if not cookie.has_nonstandard_attr('SameSite'):
                issues.append('Missing SameSite attribute - vulnerable to CSRF')
            
            if issues:
                self.security_issues['medium'].append({
                    'type': f'Insecure Cookie: {cookie.name}',
                    'details': ', '.join(issues),
                    'location': url,
                    'severity_score': 5.5,
                    'owasp': 'A05:2021 – Security Misconfiguration',
                    'recommendation': 'Set Secure, HttpOnly, and SameSite attributes'
                })
                
    def detect_cms(self, soup, url):
        """Detect CMS and version"""
        html_content = str(soup)
        
        for cms_name, patterns in CMS_PATTERNS.items():
            for pattern in patterns:
                if pattern in html_content:
                    self.cms_detected = cms_name
                    self.security_issues['info'].append({
                        'type': 'CMS Detected',
                        'details': f'{cms_name} detected',
                        'location': url,
                        'recommendation': 'Ensure CMS is up-to-date'
                    })
                    logger.info(f"CMS Detected: {cms_name}")
                    return
                    
    def check_sql_injection_vectors(self, url):
        """Check for potential SQL injection vectors in URLs"""
        for pattern in SQL_INJECTION_PATTERNS:
            if re.search(pattern, url, re.I):
                self.security_issues['medium'].append({
                    'type': 'Potential SQL Injection Vector',
                    'details': f'URL parameter matches SQL injection pattern: {pattern}',
                    'location': url,
                    'severity_score': 6.5,
                    'owasp': 'A03:2021 – Injection',
                    'recommendation': 'Use parameterized queries and input validation'
                })
                break
                
    def process_page(self, url: str) -> List[str]:
        """Process page with security checks"""
        logger.info(f"Processing page: {url}")
        
        if not self.can_fetch(url):
            logger.warning(f"robots.txt disallows fetching: {url}")
            return []
        
        try:
            response = self.download_with_retry(url)
            if not response:
                return []
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Security checks
            self.check_security_headers(response, url)
            self.check_form_security(soup, url)
            self.check_vulnerable_libraries(soup, url)
            self.check_cookies(response, url)
            self.check_sql_injection_vectors(url)
            
            if not self.cms_detected:
                self.detect_cms(soup, url)
            
        except Exception as e:
            logger.error(f"Error processing page {url}: {e}")
            self.stats.errors.append({'url': url, 'error': str(e)})
            return []
        
        # Continue with normal crawling
        return super().process_page(url)
        
    def generate_security_report(self):
        """Generate comprehensive security report"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_path = os.path.join(self.folders["reports"], f"security_report_{timestamp}.txt")
        json_path = os.path.join(self.folders["reports"], f"security_report_{timestamp}.json")
        
        total_issues = sum(len(issues) for issues in self.security_issues.values())
        
        # Text report
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("="*80 + "\n")
            f.write(f"SECURITY SCAN REPORT - {self.domain}\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("="*80 + "\n\n")
            
            if self.cms_detected:
                f.write(f"CMS Detected: {self.cms_detected}\n\n")
            
            f.write(f"SUMMARY:\n")
            f.write(f"  🔴 Critical Issues: {len(self.security_issues['critical'])}\n")
            f.write(f"  🟠 High Severity:   {len(self.security_issues['high'])}\n")
            f.write(f"  🟡 Medium Severity: {len(self.security_issues['medium'])}\n")
            f.write(f"  🟢 Low Severity:    {len(self.security_issues['low'])}\n")
            f.write(f"  ℹ️  Informational:   {len(self.security_issues['info'])}\n")
            f.write(f"  TOTAL ISSUES:       {total_issues}\n\n")
            
            for severity in ['critical', 'high', 'medium', 'low', 'info']:
                issues = self.security_issues[severity]
                if issues:
                    f.write("="*80 + "\n")
                    f.write(f"{severity.upper()} SEVERITY ISSUES ({len(issues)})\n")
                    f.write("="*80 + "\n\n")
                    
                    for idx, issue in enumerate(issues, 1):
                        f.write(f"[{idx}] {issue['type']}\n")
                        f.write(f"    Details: {issue['details']}\n")
                        f.write(f"    Location: {issue['location']}\n")
                        
                        if 'severity_score' in issue:
                            f.write(f"    Severity Score: {issue['severity_score']}/10\n")
                        if 'owasp' in issue:
                            f.write(f"    OWASP: {issue['owasp']}\n")
                        if 'recommendation' in issue:
                            f.write(f"    💡 Recommendation: {issue['recommendation']}\n")
                        if 'form_action' in issue:
                            f.write(f"    Form Action: {issue['form_action']}\n")
                        if 'script_src' in issue:
                            f.write(f"    Script Source: {issue['script_src']}\n")
                        f.write("\n")
        
        # JSON report
        security_report = {
            'metadata': {
                'domain': self.domain,
                'scan_date': datetime.now().isoformat(),
                'cms_detected': self.cms_detected,
                'pages_scanned': self.stats.pages_crawled
            },
            'summary': {
                'critical': len(self.security_issues['critical']),
                'high': len(self.security_issues['high']),
                'medium': len(self.security_issues['medium']),
                'low': len(self.security_issues['low']),
                'info': len(self.security_issues['info']),
                'total': total_issues
            },
            'issues': self.security_issues
        }
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(security_report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Security reports saved:\n  - {report_path}\n  - {json_path}")
        
        # Print summary
        print("\n" + "="*80)
        print("🔒 SECURITY SCAN COMPLETE")
        print("="*80)
        if self.cms_detected:
            print(f"CMS Detected: {self.cms_detected}")
        print(f"\nIssues Found:")
        print(f"  🔴 Critical: {len(self.security_issues['critical'])}")
        print(f"  🟠 High:     {len(self.security_issues['high'])}")
        print(f"  🟡 Medium:   {len(self.security_issues['medium'])}")
        print(f"  🟢 Low:      {len(self.security_issues['low'])}")
        print(f"  ℹ️  Info:     {len(self.security_issues['info'])}")
        print(f"\nReports saved to: {self.folders['reports']}/")
        print("="*80 + "\n")
        
    def crawl(self):
        """Main crawl with security checks"""
        logger.info(f"Starting security scan of {self.start_url}")
        self.stats.start_time = datetime.now()
        
        self.setup_folders()
        self.check_robots_txt()
        
        # Initial security checks
        if self.start_url.startswith('https://'):
            self.check_ssl_certificate()
        self.check_sensitive_files()
        
        # Start crawling
        super().crawl()
        
        # Generate security report
        self.generate_security_report()

def main():
    """CLI entry point"""
    print("="*80)
    print("🔒 SECURITY WEB CRAWLER - Enhanced Edition")
    print("="*80 + "\n")
    
    target = input("Enter Website URL to Scan: ").strip()
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
    
    crawler = SecurityCrawler(target, max_pages=limit, delay=delay, progress_callback=progress_callback)
    crawler.crawl()

if __name__ == "__main__":
    main()
