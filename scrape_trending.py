#!/usr/bin/env python3
"""
Scrape GitHub Trending (weekly + monthly) using Scrapling, filter AI repos, generate data.json.
"""
import json
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

from scrapling.fetchers import Fetcher

HERE = Path(__file__).parent
OUTPUT_FILE = HERE / "data.json"
CACHE_WEEKLY = HERE / "_cached_weekly.html"
CACHE_MONTHLY = HERE / "_cached_monthly.html"

TRENDING_WEEKLY = "https://github.com/trending?since=weekly"
TRENDING_MONTHLY = "https://github.com/trending?since=monthly"

AI_KEYWORDS = [
    "ai", "artificial intelligence", "machine learning", "deep learning",
    "llm", "gpt", "chatgpt", "claude", "openai", "anthropic",
    "transformer", "neural", "diffusion", "stable diffusion",
    "agent", "multi-agent", "autonomous", "copilot",
    "embedding", "rag", "retrieval augmented",
    "tensorflow", "pytorch", "huggingface", "langchain",
    "genai", "generative", "text-to-image", "text-to-video",
    "deepseek", "qwen", "mistral", "llama",
    "intelligence", "cognition", "vision", "nlp",
    "fine-tun", "finetun", "prompt", "token",
    "code completion", "code generation", "code review",
    "aider", "continue.dev", "codex",
    "prompt engineering", "instruct",
    "chatbot", "conversation",
    "knowledge graph", "codegraph",
]

LANG_COLORS = {
    "Python": "#3572A5", "TypeScript": "#3178C6", "JavaScript": "#f1e05a",
    "Rust": "#dea584", "Go": "#00ADD8", "Java": "#b07219",
    "C": "#555555", "C++": "#f34b7d", "C#": "#178600",
    "Shell": "#89e051", "Ruby": "#701516", "PHP": "#4F5D95",
    "Swift": "#F05138", "Kotlin": "#A97BFF", "Dart": "#00B4AB",
    "Scala": "#c22d40", "Lua": "#000080", "R": "#198CE7",
    "HTML": "#e34c26", "CSS": "#563d7c", "Vue": "#41b883",
    "Svelte": "#ff3e00", "Zig": "#ec915c", "Solidity": "#AA6746",
    "Jupyter Notebook": "#DA5B0B", "TeX": "#3D6117",
    "Dockerfile": "#384d54", "PowerShell": "#012456",
    "Clojure": "#db5855", "Elixir": "#6e4a7e",
    "Haskell": "#5e5086", "Erlang": "#B83998", "Perl": "#0298c3",
}


def elem_text(el) -> str:
    nodes = el.css("::text")
    if not nodes:
        return ""
    for n in reversed(nodes):
        t = n.text.strip() if hasattr(n, "text") else str(n).strip()
        if t:
            return t
    return nodes[-1].text.strip() if hasattr(nodes[-1], "text") else str(nodes[-1]).strip()


def parse_stars(text: str) -> int:
    text = text.strip()
    for s in ["stars this month", "stars today", "stars this week", "stars"]:
        text = text.replace(s, "")
    return int(text.replace(",", "").strip())


def parse_number(text: str) -> int:
    return int(text.strip().replace(",", ""))


def abbreviate_number(n: int) -> str:
    if n >= 1000:
        val = n / 1000
        if val >= 100:
            return f"{val:.0f}k"
        return f"{val:.1f}k"
    return str(n)


def is_ai_related(description: str, tags: list[str], repo_name: str) -> bool:
    text = f"{description} {' '.join(tags)} {repo_name}".lower()
    return any(kw in text for kw in AI_KEYWORDS)


def get_avatar_params(owner: str) -> dict:
    h = sum(ord(c) for c in owner)
    bg = ["#e3f2fd","#fce4ec","#fff3e0","#e8f5e9","#f3e5f5","#e0f7fa","#fff8e1","#fbe9e7"]
    fg = ["#1565c0","#c62828","#e65100","#2e7d32","#7b1fa2","#00838f","#f9a825","#bf360c"]
    return {"avatar_bg": bg[h % len(bg)], "avatar_fg": fg[h % len(fg)], "avatar_char": owner[0].upper() if owner else "?"}


def get_repo_details(owner: str, repo_name: str) -> tuple[str | None, list[str]]:
    url = f"https://api.github.com/repos/{owner}/{repo_name}"
    try:
        req = urllib.request.Request(url)
        req.add_header("Accept", "application/vnd.github.mercy-preview+json")
        req.add_header("User-Agent", "Scrapling-Trending/1.0")
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read().decode("utf-8"))
        lic = None
        if data.get("license") and data["license"].get("spdx_id"):
            s = data["license"]["spdx_id"]
            if s != "NOASSERTION":
                lic = f"{s} License" if "License" not in s else s
        return lic, data.get("topics", [])[:8]
    except Exception as e:
        print(f"  [!] API error: {e}", file=sys.stderr)
        return None, []


def fetch_page(url: str, cache_path: Path) -> bytes:
    try:
        print(f"Fetching {url} ...")
        p = Fetcher.get(url, verify=False, timeout=15)
        body = p.body if isinstance(p.body, bytes) else p.body.encode("utf-8")
        print(f"  Fetched {len(body)} bytes")
        cache_path.write_bytes(body)
        return body
    except Exception as e:
        print(f"  Fetch failed: {e}", file=sys.stderr)
        if cache_path.exists():
            print("  Using cached copy")
            return cache_path.read_bytes()
        raise


def parse_trending(html: bytes) -> list[dict]:
    from scrapling import Selector
    page = Selector(html.decode("utf-8"))
    articles = page.css("article")
    print(f"  Found {len(articles)} articles")

    repos = []
    for i, art in enumerate(articles):
        try:
            h2_link = art.css("h2 a")
            if not h2_link: continue
            href = h2_link[0].attrib.get("href", "")
            parts = href.strip("/").split("/")
            if len(parts) < 2: continue
            owner, name = parts[0], parts[1]

            desc = elem_text(art.css("p.col-9")[0]) if art.css("p.col-9") else ""
            sd = art.css("div.f6")
            if not sd: continue
            s = sd[0]

            st = parse_number(elem_text(s.css('a[href*="/stargazers"]')[0])) if s.css('a[href*="/stargazers"]') else 0
            fk = parse_number(elem_text(s.css('a[href*="/forks"]')[0])) if s.css('a[href*="/forks"]') else 0
            sp = 0
            if s.css("span.float-sm-right"):
                mt = elem_text(s.css("span.float-sm-right")[0])
                if mt: sp = parse_stars(mt)
            lang = elem_text(s.css('span[itemprop="programmingLanguage"]')[0]) if s.css('span[itemprop="programmingLanguage"]') else None
            lc = LANG_COLORS.get(lang, "#8b949e")
            av = get_avatar_params(owner)
            url = f"https://github.com/{owner}/{name}"
            lic, tags = get_repo_details(owner, name)

            repos.append({"owner": owner, "name": name, "url": url, "description": desc,
                "stars_total": st, "stars_abbr": abbreviate_number(st),
                "forks": fk, "forks_abbr": abbreviate_number(fk),
                "stars_period": sp, "language": lang, "lang_color": lc,
                "license": lic, "tags": tags, "is_ai": is_ai_related(desc, tags, name), **av})
        except Exception as e:
            print(f"  [!] Error #{i+1}: {e}", file=sys.stderr)

    return repos


def gen_data(weekly: list[dict], monthly: list[dict]) -> dict:
    """Bundle scraped repo data into a clean JSON structure."""
    now = datetime.now()
    return {
        "updated_at": f"{now.year}-{now.month:02d}-{now.day:02d}",
        "month_label": f"{now.year}年{now.month}月",
        "weekly": weekly,
        "monthly": monthly,
    }


def main():
    print("=" * 50)
    print("GitHub AI Trending Scraper")
    print("=" * 50)

    print("\n📆 Weekly:")
    wh = fetch_page(TRENDING_WEEKLY, CACHE_WEEKLY)
    wr = parse_trending(wh)
    wa = [r for r in wr if r["is_ai"]]
    print(f"  AI repos: {len(wa)}/{len(wr)}")

    print("\n📅 Monthly:")
    mh = fetch_page(TRENDING_MONTHLY, CACHE_MONTHLY)
    mr = parse_trending(mh)
    ma = [r for r in mr if r["is_ai"]]
    print(f"  AI repos: {len(ma)}/{len(mr)}")

    if not wa and not ma:
        print("ERROR: No AI repos found!", file=sys.stderr)
        wa, ma = wr[:15], mr[:15]

    data = gen_data(wa[:15], ma[:15])
    OUTPUT_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✅ Generated {OUTPUT_FILE}")
    print(f"   Weekly: {len(wa[:15])} AI repos · Monthly: {len(ma[:15])} AI repos")


if __name__ == "__main__":
    main()
