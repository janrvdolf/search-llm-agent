import requests
import json
import os
import re
from typing import Dict, List, Optional
from urllib.parse import urlencode, urlparse


class SearXNGClient:
    def __init__(self, base_url: str = "http://localhost:8080"):
        """
        Initialize SearXNG client

        Args:
            base_url: Base URL of your SearXNG instance
        """
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        # Add headers to avoid bot detection
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.9",
                "Content-Type": "application/x-www-form-urlencoded",
            }
        )

    def search(
        self,
        query: str,
        categories: Optional[List[str]] = None,
        engines: Optional[List[str]] = None,
        language: str = "auto",
        format: str = "json",
        safesearch: int = 0,
        timeout: int = 10,
    ) -> Dict:
        """
        Perform a search query and retrieve results in JSON format

        Args:
            query: Search query string
            categories: List of categories to search in (e.g., ['general', 'news', 'images'])
            engines: List of specific engines to use (e.g., ['google', 'bing', 'duckduckgo'])
            language: Language code (e.g., 'en', 'de', 'auto')
            format: Response format (defaults to 'json')
            safesearch: Safe search level (0=off, 1=moderate, 2=strict)
            timeout: Request timeout in seconds

        Returns:
            Dictionary containing JSON search results with metadata
        """
        # Prepare POST data for SearXNG
        data = {
            "q": query,
            "format": format,
            "language": language,
            "safesearch": safesearch,
        }

        # Add categories
        if categories:
            for category in categories:
                data[f"category_{category}"] = "1"
        else:
            # Default to general category
            data["category_general"] = "1"

        # Add specific engines if requested
        if engines:
            data["engines"] = ",".join(engines)

        try:
            response = self.session.post(
                f"{self.base_url}/search", data=data, timeout=timeout
            )
            response.raise_for_status()

            # Parse JSON response
            json_data = response.json()

            # Add query metadata for convenience
            json_data["query_info"] = {
                "original_query": query,
                "language": language,
                "categories": categories or ["general"],
                "engines": engines,
                "safesearch": safesearch,
                "total_results": len(json_data.get("results", [])),
            }

            return json_data

        except requests.exceptions.RequestException as e:
            return {
                "error": str(e),
                "status_code": getattr(e.response, "status_code", None),
            }
        except json.JSONDecodeError as e:
            return {"error": f"Invalid JSON response: {str(e)}"}

    def get_engines(self) -> Dict:
        """Get available search engines in JSON format"""
        try:
            # Try different possible endpoints for engines
            endpoints = ["/engines.json", "/stats", "/preferences"]

            for endpoint in endpoints:
                try:
                    response = self.session.get(f"{self.base_url}{endpoint}")
                    if response.status_code == 200:
                        if endpoint == "/engines.json":
                            return response.json()
                        elif endpoint == "/stats":
                            # Parse stats page for engine information
                            return {
                                "info": "Engine stats available",
                                "endpoint": endpoint,
                            }
                        elif endpoint == "/preferences":
                            # Parse preferences page for engine information
                            return {
                                "info": "Engine preferences available",
                                "endpoint": endpoint,
                            }
                except:
                    continue

            return {"error": "No engines endpoint available"}

        except requests.exceptions.RequestException as e:
            return {"error": str(e)}

    def get_categories(self) -> List[str]:
        """Get available search categories"""
        # Return common SearXNG categories since engines endpoint might not be available
        return [
            "general",
            "images",
            "videos",
            "news",
            "map",
            "music",
            "it",
            "science",
            "files",
            "social media",
        ]

    def search_with_pagination(self, query: str, page: int = 1, **kwargs) -> Dict:
        """
        Search with pagination support

        Args:
            query: Search query string
            page: Page number (starting from 1)
            **kwargs: Additional search parameters

        Returns:
            Dictionary containing JSON search results with pagination info
        """
        # Add page number to the search data
        data = {
            "q": query,
            "format": "json",
            "pageno": page,
            "language": kwargs.get("language", "auto"),
            "safesearch": kwargs.get("safesearch", 0),
        }

        # Add categories
        categories = kwargs.get("categories")
        if categories:
            for category in categories:
                data[f"category_{category}"] = "1"
        else:
            data["category_general"] = "1"

        # Add engines
        engines = kwargs.get("engines")
        if engines:
            data["engines"] = ",".join(engines)

        try:
            response = self.session.post(
                f"{self.base_url}/search", data=data, timeout=kwargs.get("timeout", 10)
            )
            response.raise_for_status()

            json_data = response.json()

            # Add pagination metadata
            json_data["pagination_info"] = {
                "current_page": page,
                "query": query,
                "results_on_page": len(json_data.get("results", [])),
                "language": kwargs.get("language", "auto"),
                "categories": categories or ["general"],
            }

            return json_data

        except requests.exceptions.RequestException as e:
            return {
                "error": str(e),
                "status_code": getattr(e.response, "status_code", None),
            }
        except json.JSONDecodeError as e:
            return {"error": f"Invalid JSON response: {str(e)}"}


def print_image_urls(
    results: Dict, max_results: int = 10, max_urls_to_return: int = 5
) -> List[str]:
    """
    Print direct image URLs from search results and return them as a list

    Args:
        results: JSON response from image search
        max_results: Maximum number of image URLs to display
        max_urls_to_return: Maximum number of URLs to return in the list (default: 5)

    Returns:
        List of direct image URLs (limited to max_urls_to_return)
    """
    if "error" in results:
        print(f"❌ Image search failed: {results['error']}")
        return []

    query_info = results.get("query_info", {})
    search_results = results.get("results", [])

    # Common image file extensions
    image_extensions = {
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".webp",
        ".bmp",
        ".svg",
        ".tiff",
        ".tif",
        ".ico",
    }

    # Filter results to only include direct image URLs with proper mime type validation
    direct_image_results = []

    def extract_direct_image_url(url):
        """Try to extract direct image URL from a page URL"""
        try:
            import requests

            # For Wikimedia Commons, convert to direct image URL
            if "commons.wikimedia.org/wiki/File:" in url:
                # Extract filename from URL
                filename = url.split("File:")[-1]
                # Convert to direct image URL using Special:FilePath
                direct_url = (
                    f"https://commons.wikimedia.org/wiki/Special:FilePath/{filename}"
                )
                return direct_url

            return url  # Return original URL if no conversion needed

        except Exception:
            return url

    def is_direct_image_url(url):
        """Check if URL is a direct image URL by validating mime type"""
        try:
            import requests

            # First try to extract direct image URL if this is a page URL
            test_url = extract_direct_image_url(url)

            # Make HEAD request to check mime type
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }

            response = requests.head(
                test_url, headers=headers, timeout=10, allow_redirects=True
            )
            content_type = response.headers.get("content-type", "").lower()

            # Only accept if content type is actually an image
            if content_type.startswith("image/"):
                return True

            return False

        except Exception:
            # If we can't check, be very strict - only accept URLs with clear image extensions
            url_lower = url.lower()
            # Must end with image extension (no query parameters)
            if any(url_lower.endswith(ext) for ext in image_extensions):
                return True
            return False

    # Process results and convert page URLs to direct image URLs where possible
    for result in search_results:
        original_url = result.get("url", "")
        if original_url:
            # Try to convert to direct image URL
            direct_url = extract_direct_image_url(original_url)

            # Test if the URL (original or converted) is a direct image
            if is_direct_image_url(original_url):
                # Update the result with the direct URL if it was converted
                if direct_url != original_url:
                    result = result.copy()
                    result["url"] = direct_url
                direct_image_results.append(result)

    print(f"🖼️ Image Search: '{query_info.get('original_query', 'N/A')}'")
    print(
        f"📊 Found {len(search_results)} total results, {len(direct_image_results)} direct image URLs"
    )
    print(f"🔧 Engines: {', '.join(query_info.get('engines', ['all']))}")
    print("=" * 80)

    if not direct_image_results:
        print(
            "⚠️ No direct image URLs found. Try using different search engines or queries."
        )
        print("💡 Tip: Some engines return page URLs instead of direct image URLs.")
        return []

    # Collect URLs to return
    image_urls = []

    for i, result in enumerate(direct_image_results[:max_results], 1):
        title = result.get("title", "No Title")
        image_url = result.get("url", "No URL")
        content = result.get("content", "No description")

        # Add URL to return list
        image_urls.append(image_url)

        # Extract file extension for display
        url_lower = image_url.lower()
        file_ext = "unknown"
        for ext in image_extensions:
            if ext in url_lower:
                file_ext = ext.upper().replace(".", "")
                break

        print(f"\n{i}. {title}")
        print(f"   🔗 Direct Image URL: {image_url}")
        print(f"   📁 Format: {file_ext}")

        if content and content != "No description":
            if len(content) > 80:
                content = content[:80] + "..."
            print(f"   📝 Description: {content}")

        # Show which engines found this image
        engines = result.get("engines", [])
        if engines:
            print(f"   🔍 Found by: {', '.join(engines)}")

    print("=" * 80)

    if len(direct_image_results) > max_results:
        print(
            f"💡 Showing {max_results} of {len(direct_image_results)} direct image URLs"
        )
        print(f"   Increase max_results parameter to see more")

    # Limit the returned URLs to max_urls_to_return
    urls_to_return = image_urls[:max_urls_to_return]

    if len(image_urls) > max_urls_to_return:
        print(
            f"🔗 Returning {max_urls_to_return} of {len(image_urls)} URLs for download"
        )
        print(f"   Increase max_urls_to_return parameter to get more URLs")

    return urls_to_return


def extract_direct_image_url(url: str, session: requests.Session) -> Optional[str]:
    """
    Extract direct image URL from Wikimedia Commons page URLs

    Args:
        url: URL that might be a Wikimedia Commons page
        session: Requests session to use

    Returns:
        Direct image URL if found, otherwise None
    """
    # If it's already a direct image URL, return it
    if any(
        ext in url.lower()
        for ext in [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg"]
    ):
        if "upload.wikimedia.org" in url:
            return url

    # If it's a Wikimedia Commons page, extract the actual image URL
    if "commons.wikimedia.org/wiki/File:" in url or "wikipedia.org/wiki/File:" in url:
        try:
            response = session.get(url, timeout=10)
            response.raise_for_status()
            content = response.text

            # Look for the original file URL in the HTML
            # Pattern for full-size image: upload.wikimedia.org/wikipedia/commons/[hash]/filename.ext
            pattern = r'https://upload\.wikimedia\.org/wikipedia/commons/[^"]*\.(?:jpg|jpeg|png|gif|webp|bmp|svg)'
            matches = re.findall(pattern, content, re.IGNORECASE)

            if matches:
                # Prefer the original (non-thumb) version
                for match in matches:
                    if "/thumb/" not in match:
                        return match
                # If no original found, use the largest thumbnail
                return max(matches, key=len)

        except Exception as e:
            print(f"   ⚠️ Could not extract image URL from page: {str(e)}")

    return None


def download_images(
    image_urls: List[str], download_dir: str = "zebras", timeout: int = 30
) -> List[str]:
    """
    Download images from URLs to a local directory, handling Wikimedia Commons pages

    Args:
        image_urls: List of image URLs to download (can include page URLs)
        download_dir: Directory to save images (relative to current working directory)
        timeout: Request timeout in seconds

    Returns:
        List of successfully downloaded file paths
    """
    if not image_urls:
        print("⚠️ No image URLs provided for download")
        return []

    # Create download directory if it doesn't exist
    os.makedirs(download_dir, exist_ok=True)
    print(f"📁 Created/using download directory: {download_dir}")

    downloaded_files = []
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
    )

    print(f"⬇️ Starting download of {len(image_urls)} images...")
    print("=" * 60)

    for i, url in enumerate(image_urls, 1):
        try:
            print(
                f"📥 Processing {i}/{len(image_urls)}: {url[:60]}{'...' if len(url) > 60 else ''}"
            )

            # Extract direct image URL if needed
            direct_url = extract_direct_image_url(url, session)
            if not direct_url:
                direct_url = url  # Use original URL as fallback

            if direct_url != url:
                print(
                    f"   🔗 Found direct image URL: {direct_url[:60]}{'...' if len(direct_url) > 60 else ''}"
                )

            # Get the image
            response = session.get(direct_url, timeout=timeout, stream=True)
            response.raise_for_status()

            # Check if we actually got an image
            content_type = response.headers.get("content-type", "").lower()
            if "text/html" in content_type:
                print(f"   ⚠️ Got HTML instead of image, skipping...")
                continue

            # Determine file extension from URL or content type
            parsed_url = urlparse(direct_url)
            path = parsed_url.path.lower()

            # Try to get extension from URL
            file_ext = None
            image_extensions = [
                ".jpg",
                ".jpeg",
                ".png",
                ".gif",
                ".webp",
                ".bmp",
                ".svg",
                ".tiff",
                ".tif",
                ".ico",
            ]
            for ext in image_extensions:
                if ext in path:
                    file_ext = ext
                    break

            # If no extension found in URL, try to determine from content type
            if not file_ext:
                if "jpeg" in content_type or "jpg" in content_type:
                    file_ext = ".jpg"
                elif "png" in content_type:
                    file_ext = ".png"
                elif "gif" in content_type:
                    file_ext = ".gif"
                elif "webp" in content_type:
                    file_ext = ".webp"
                elif "svg" in content_type:
                    file_ext = ".svg"
                else:
                    file_ext = ".jpg"  # Default fallback

            # Generate filename
            filename = f"zebra_{i:02d}{file_ext}"
            filepath = os.path.join(download_dir, filename)

            # Save the image
            with open(filepath, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            file_size = os.path.getsize(filepath)
            print(f"   ✅ Saved as {filename} ({file_size:,} bytes)")
            downloaded_files.append(filepath)

        except requests.exceptions.RequestException as e:
            print(f"   ❌ Failed to download: {str(e)}")
        except Exception as e:
            print(f"   ❌ Error saving file: {str(e)}")

    print("=" * 60)
    print(
        f"🎉 Download complete! {len(downloaded_files)}/{len(image_urls)} images saved successfully"
    )

    if downloaded_files:
        print(f"📂 Images saved in: {os.path.abspath(download_dir)}")
        print(f"📋 Downloaded files:")
        for filepath in downloaded_files:
            print(f"   • {filepath}")

    return downloaded_files


def print_search_results(results: Dict, max_results: int = 5):
    """
    Pretty print search results from JSON response

    Args:
        results: JSON response from search
        max_results: Maximum number of results to display
    """
    if "error" in results:
        print(f"❌ Search failed: {results['error']}")
        return

    # Check for pagination info first
    if "pagination_info" in results:
        pagination = results["pagination_info"]
        print(f"🔍 Query: '{pagination.get('query', 'N/A')}'")
        print(f"📄 Page: {pagination.get('current_page', 'N/A')}")
        print(f"📊 Found {pagination.get('results_on_page', 0)} results on this page")
        print(f"🌐 Language: {pagination.get('language', 'N/A')}")
        print(f"📁 Categories: {', '.join(pagination.get('categories', []))}")
    else:
        query_info = results.get("query_info", {})
        search_results = results.get("results", [])

        print(f"🔍 Query: '{query_info.get('original_query', 'N/A')}'")
        print(f"📊 Found {len(search_results)} results")
        print(f"🌐 Language: {query_info.get('language', 'N/A')}")
        print(f"📁 Categories: {', '.join(query_info.get('categories', []))}")

        if query_info.get("engines"):
            print(f"🔧 Engines: {', '.join(query_info.get('engines', []))}")

    print("=" * 80)

    search_results = results.get("results", [])
    for i, result in enumerate(search_results[:max_results], 1):
        print(f"\n{i}. {result.get('title', 'No Title')}")
        print(f"   🔗 {result.get('url', 'No URL')}")

        content = result.get("content", "No description available")
        if len(content) > 100:
            content = content[:100] + "..."
        print(f"   📝 {content}")

        # Show engines that found this result
        engines = result.get("engines", [])
        if engines:
            print(f"   🔍 Found by: {', '.join(engines)}")

        # Show score if available
        score = result.get("score")
        if score:
            print(f"   ⭐ Score: {score:.2f}")

    print("=" * 80)


# Example usage
if __name__ == "__main__":
    # Initialize client
    client = SearXNGClient("http://localhost:8080")

    print("🚀 SearXNG JSON Client Demo")
    print("=" * 50)

    # Basic search
    print("\n1. Basic Search:")
    results = client.search("Python programming")
    print_search_results(results)

    # Search with specific categories
    print("\n2. News Search:")
    news_results = client.search("AI developments", categories=["news"])
    print_search_results(news_results, max_results=3)

    # Search with specific engines
    print("\n3. Search with Specific Engines:")
    engine_results = client.search("machine learning", engines=["google", "duckduckgo"])
    print_search_results(engine_results, max_results=3)

    # Pagination example
    print("\n4. Pagination Example (Page 2):")
    page2_results = client.search_with_pagination("Python tutorials", page=2)
    print_search_results(page2_results, max_results=3)

    # Get available engines
    print("\n5. Available Engines:")
    engines = client.get_engines()
    if "error" not in engines:
        if isinstance(engines, list):
            print(f"📋 Total engines available: {len(engines)}")
            active_engines = [
                e["name"]
                for e in engines
                if isinstance(e, dict) and not e.get("disabled", False)
            ]
            print(f"✅ Active engines: {len(active_engines)}")
            print(f"🔧 Sample engines: {', '.join(active_engines[:10])}")
        else:
            print(f"📋 Engine info: {engines.get('info', 'Available')}")
            print(f"🔧 Endpoint: {engines.get('endpoint', 'Unknown')}")
    else:
        print(f"❌ Error getting engines: {engines['error']}")

    # Get available categories
    print("\n6. Available Categories:")
    categories = client.get_categories()
    if categories:
        print(f"📂 Available categories: {', '.join(categories)}")
    else:
        print("❌ No categories available")

    # Zebra image search with Google
    print("\n7. Zebra Image Search (Google):")
    zebra_images = client.search("zebra", categories=["images"], engines=["google"])
    zebra_urls = print_image_urls(zebra_images, max_results=8, max_urls_to_return=5)

    # Download zebra images to local directory
    print("\n8. Downloading Zebra Images:")
    if zebra_urls:
        downloaded_files = download_images(zebra_urls, download_dir="zebras")
        print(f"\n✨ Successfully downloaded {len(downloaded_files)} zebra images!")
    else:
        print("⚠️ No zebra image URLs found to download")

    print("\n🎉 Demo completed!")
