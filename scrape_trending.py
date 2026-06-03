#!/usr/bin/env python3
"""
Scrape GitHub Trending (weekly + monthly) using Scrapling, filter AI repos, generate index.html.
"""
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

from scrapling.fetchers import Fetcher
from jinja2 import Template

HERE = Path(__file__).parent
OUTPUT_FILE = HERE / "index.html"
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

CSS = r"""* { margin: 0; padding: 0; box-sizing: border-box; }

:root {
  --bg: #fff;
  --fg: #111;
  --border: #e0e0e0;
  --muted: #888;
  --card-bg: #fafafa;
  --accent: #000;
  --tag-bg: #f0f0f0;
  --green: #2a2;
  --transition: 0.25s ease;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
  background: var(--bg);
  color: var(--fg);
  line-height: 1.6;
  padding: 16px;
  max-width: 600px;
  margin: 0 auto;
  -webkit-font-smoothing: antialiased;
}

header { text-align: center; padding: 24px 0 4px; border-bottom: 1px solid var(--border); margin-bottom: 20px; }
h1 { font-size: 20px; font-weight: 700; letter-spacing: 0.5px; }
.subtitle { font-size: 12px; color: var(--muted); margin-top: 4px; }
.update-badge { display: none; }

.toggle-bar {
  display: flex; gap: 0; margin: 0 auto 20px;
  border: 1px solid var(--accent); border-radius: 8px; overflow: hidden;
  max-width: 320px;
}
.toggle-btn {
  flex: 1; padding: 10px 0; text-align: center; font-size: 14px; font-weight: 600;
  border: none; background: var(--bg); color: var(--muted);
  cursor: pointer; transition: background var(--transition), color var(--transition);
  letter-spacing: 0.5px;
}
.toggle-btn.active { background: var(--accent); color: #fff; }
.update-time { font-size: 11px; color: var(--muted); text-align: center; margin-bottom: 16px; }

.project-list {
  display: grid; grid-template-columns: 1fr; gap: 12px;
  transition: opacity 0.2s ease;
}

.project-card {
  display: block; text-decoration: none; color: var(--fg);
  background: var(--card-bg); border: 1px solid var(--border);
  border-radius: 10px; padding: 16px; position: relative;
  transition: border-color var(--transition), box-shadow var(--transition);
}
.project-card:hover, .project-card:active {
  border-color: var(--accent); box-shadow: 0 2px 12px rgba(0,0,0,0.06);
}

.rank-badge {
  display: inline-block; font-size: 11px; font-weight: 700; color: var(--muted);
  min-width: 24px;
}

.card-header {
  display: flex; align-items: center; gap: 10px; margin-bottom: 6px;
}
.avatar { display: none; }
.repo-info { flex: 1; min-width: 0; }
.owner { display: none; }
.repo-name {
  font-size: 16px; font-weight: 700;
  display: flex; align-items: center; gap: 8px;
}
.repo-name .name {
  color: var(--accent); word-break: break-all;
}

.description {
  font-size: 13px; color: #555; margin-bottom: 10px; line-height: 1.5;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}

.stats {
  display: flex; align-items: center; gap: 12px; flex-wrap: wrap; margin-bottom: 0;
}
.stat { display: flex; align-items: center; gap: 4px; font-size: 13px; color: var(--fg); }
.stat .star-icon { color: var(--fg); }
.stat .num { font-weight: 600; }
.stat-fork { display: none; }
.hot-badge {
  font-size: 12px; color: var(--green); font-weight: 600;
}

.meta { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; margin-top: 8px; }
.lang-dot { display: none; }
.lang { font-size: 11px; padding: 2px 8px; border-radius: 12px; background: var(--tag-bg); color: var(--muted); font-weight: 500; }
.tags { display: none; }
.license { display: none; }

footer { text-align: center; padding: 24px 0; font-size: 11px; color: var(--muted); border-top: 1px solid var(--border); margin-top: 24px; }

@media (min-width: 640px) {
  body { max-width: 900px; padding: 24px 32px; }
  .project-list { grid-template-columns: 1fr 1fr; gap: 14px; }
  header { padding: 32px 0 8px; margin-bottom: 24px; }
  h1 { font-size: 24px; }
  .subtitle { font-size: 13px; }
}

@media (min-width: 1024px) {
  body {
    max-width: 100%;
    padding: 0;
    background: linear-gradient(135deg, #0d1117 0%, #161b22 100%);
    color: #e6edf3;
    min-height: 100vh;
  }
  .container { max-width: 1280px; margin: 0 auto; padding: 40px 24px; position: relative; }

  body::before {
    content: '';
    position: fixed;
    inset: 0;
    background-image: radial-gradient(circle, rgba(0,212,255,0.18) 1.5px, transparent 1.5px);
    background-size: 32px 32px;
    pointer-events: none;
    z-index: -1;
  }

  body::after {
    content: '';
    position: fixed;
    top: 0; left: 0;
    width: 100%; height: 3px;
    background: linear-gradient(90deg,
      transparent 0%,
      rgba(0,212,255,0) 3%,
      #00d4ff 15%,
      #a855f7 40%,
      #ff6b35 60%,
      #a855f7 78%,
      #00d4ff 90%,
      transparent 100%
    );
    box-shadow: 0 0 18px rgba(0,212,255,0.5), 0 0 60px rgba(168,85,247,0.25);
    pointer-events: none;
    z-index: 100;
    opacity: 1;
  }

  header {
    text-align: center; padding: 0 0 0 0 !important; margin-bottom: 48px !important;
    border-bottom: none;
    display: block;
  }
  header h1 {
    font-size: 2.8rem !important; font-weight: 800;
    background: linear-gradient(135deg, #58a6ff, #bc8cff);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text; margin-bottom: 8px;
  }
  header .subtitle {
    font-size: 1.1rem !important; color: #8b949e; margin-top: 0 !important;
    display: flex; align-items: center; justify-content: center; gap: 8px;
  }
  header .subtitle svg { width: 20px; height: 20px; fill: #8b949e; flex-shrink: 0; }
  .update-badge {
    display: inline-block; margin-top: 12px;
    background: rgba(88,166,255,0.15); color: #58a6ff;
    padding: 6px 16px; border-radius: 20px; font-size: 0.85rem;
    border: 1px solid rgba(88,166,255,0.3);
  }
  .update-time { display: none; }

  .toggle-bar {
    max-width: 320px; margin: 20px auto 0;
    border: 1px solid rgba(255,255,255,0.12); border-radius: 8px;
    background: rgba(255,255,255,0.04);
  }
  .toggle-btn {
    padding: 8px 24px; font-size: 14px;
    background: transparent; color: #8b949e;
  }
  .toggle-btn.active {
    background: rgba(255,255,255,0.10); color: #fff;
    backdrop-filter: blur(4px);
  }

  .project-list {
    grid-template-columns: repeat(auto-fill, minmax(380px, 1fr)) !important;
    gap: 20px !important;
  }

  .project-card {
    display: block; text-decoration: none;
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 12px;
    padding: 24px;
    transition: transform 0.2s, border-color 0.2s, box-shadow 0.2s;
    position: relative;
    overflow: hidden;
    color: #e6edf3;
  }
  .project-card:hover {
    transform: translateY(-4px);
    border-color: #58a6ff;
    box-shadow: 0 12px 32px rgba(88,166,255,0.1);
  }

  .rank-badge {
    position: absolute; top: 12px; right: 12px;
    width: 32px; height: 32px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-weight: 700; font-size: 0.85rem;
    min-width: auto;
  }
  .rank-1 { background: linear-gradient(135deg, #ffd700, #ffaa00); color: #0d1117; }
  .rank-2 { background: linear-gradient(135deg, #e0e0e0, #c0c0c0); color: #0d1117; }
  .rank-3 { background: linear-gradient(135deg, #cd7f32, #a0522d); color: #fff; }
  .rank-other { background: rgba(139,148,158,0.2); color: #8b949e; }

  .card-header { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
  .avatar {
    display: flex !important;
    width: 44px; height: 44px; border-radius: 50%;
    background: #21262d; flex-shrink: 0;
    align-items: center; justify-content: center;
    font-size: 1.3rem; font-weight: 700; color: #58a6ff;
  }
  .repo-info { flex: 1; min-width: 0; }
  .owner { display: block; font-size: 0.8rem; color: #8b949e; }
  .repo-name { display: block; gap: 0; }
  .repo-name .name {
    font-size: 1.1rem; font-weight: 600;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    display: block;
  }
  .repo-name .name a { color: #58a6ff; text-decoration: none; }
  .repo-name .name a:hover { text-decoration: underline; }

  .description {
    font-size: 0.9rem; color: #8b949e; line-height: 1.5;
    margin-bottom: 16px;
    -webkit-line-clamp: 3; color: #8b949e;
  }

  .stats {
    display: flex; flex-wrap: wrap; gap: 16px; margin-bottom: 14px;
    font-size: 0.85rem;
  }
  .stat { display: flex; align-items: center; gap: 4px; color: #8b949e; }
  .stat .star-icon { color: #8b949e; }
  .stat .num { font-weight: 600; color: #e6edf3; }
  .stat-fork { display: flex !important; }
  .hot-badge {
    background: rgba(255,102,0,0.15); color: #ff6600;
    padding: 2px 10px; border-radius: 10px; font-weight: 600;
    font-size: 0.8rem; border: 1px solid rgba(255,102,0,0.3);
    margin-left: auto;
  }

  .meta { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
  .lang { font-size: 0.85rem; color: #8b949e; display: flex; align-items: center; gap: 6px; background: none; padding: 0; border-radius: 0; }
  .lang-dot { display: inline-block !important; width: 12px; height: 12px; border-radius: 50%; flex-shrink: 0; }
  .tags { display: flex; gap: 6px; flex-wrap: wrap; flex: 1; }
  .tag {
    font-size: 0.75rem; background: rgba(88,166,255,0.1);
    color: #58a6ff; padding: 2px 8px; border-radius: 8px;
    max-width: 120px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }
  .license { display: block; font-size: 0.78rem; color: #484f58; margin-top: 10px; }

  footer {
    text-align: center; margin-top: 48px; padding: 20px 0;
    border-top: 1px solid #21262d; color: #484f58; font-size: 0.85rem;
  }
  footer a { color: #58a6ff; text-decoration: none; }

  .container { position: relative; }

  .corner {
    position: absolute;
    width: 36px; height: 36px;
    pointer-events: none;
    z-index: 10;
    opacity: 0.9;
    animation: cornerPulse 2.5s ease-in-out infinite;
  }
  .corner-tl {
    top: -1px; left: -1px;
    border-top: 3px solid #00d4ff;
    border-left: 3px solid #00d4ff;
    border-radius: 8px 0 0 0;
    box-shadow: -2px -2px 12px rgba(0,212,255,0.5), 0 0 20px rgba(0,212,255,0.15);
  }
  .corner-tr {
    top: -1px; right: -1px;
    border-top: 3px solid #a855f7;
    border-right: 3px solid #a855f7;
    border-radius: 0 8px 0 0;
    box-shadow: 2px -2px 12px rgba(168,85,247,0.5), 0 0 20px rgba(168,85,247,0.15);
  }
  .corner-bl {
    bottom: -1px; left: -1px;
    border-bottom: 3px solid #a855f7;
    border-left: 3px solid #a855f7;
    border-radius: 0 0 0 8px;
    box-shadow: -2px 2px 12px rgba(168,85,247,0.5), 0 0 20px rgba(168,85,247,0.15);
  }
  .corner-br {
    bottom: -1px; right: -1px;
    border-bottom: 3px solid #00d4ff;
    border-right: 3px solid #00d4ff;
    border-radius: 0 0 8px 0;
    box-shadow: 2px 2px 12px rgba(0,212,255,0.5), 0 0 20px rgba(0,212,255,0.15);
  }

  .container::before,
  .container::after {
    content: '';
    position: absolute;
    top: 8%;
    width: 2px;
    height: 84%;
    pointer-events: none;
    z-index: 0;
  }
  .container::before {
    left: 0;
    background: linear-gradient(to bottom,
      transparent 0%,
      rgba(0,212,255,0.35) 25%,
      rgba(168,85,247,0.5) 50%,
      rgba(0,212,255,0.35) 75%,
      transparent 100%
    );
    box-shadow: -1px 0 6px rgba(0,212,255,0.15);
  }
  .container::after {
    right: 0;
    background: linear-gradient(to bottom,
      transparent 0%,
      rgba(0,212,255,0.35) 25%,
      rgba(168,85,247,0.5) 50%,
      rgba(0,212,255,0.35) 75%,
      transparent 100%
    );
    box-shadow: 1px 0 6px rgba(0,212,255,0.15);
  }

  .container .bottom-line {
    position: absolute;
    bottom: -1px; left: 10%;
    width: 80%; height: 2px;
    background: linear-gradient(90deg,
      transparent 0%,
      rgba(0,212,255,0.3) 15%,
      #00d4ff 30%,
      #a855f7 50%,
      #00d4ff 70%,
      rgba(0,212,255,0.3) 85%,
      transparent 100%
    );
    box-shadow: 0 0 10px rgba(0,212,255,0.3);
    pointer-events: none;
  }
}

@media not all and (min-width: 1024px) {
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #0d1117;
    --fg: #c9d1d9;
    --border: #30363d;
    --muted: #8b949e;
    --card-bg: #161b22;
    --accent: #58a6ff;
    --tag-bg: #21262d;
  }
  .project-card:hover, .project-card:active {
    box-shadow: 0 2px 12px rgba(88,166,255,0.08);
  }
  .description { color: #8b949e; }
}
}

@keyframes cornerPulse {
  0%, 100% { opacity: 0.65; filter: drop-shadow(0 0 4px rgba(0,212,255,0.3)); }
  50% { opacity: 1; filter: drop-shadow(0 0 12px rgba(0,212,255,0.6)); }
}"""


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


def gen_html(weekly: list[dict], monthly: list[dict]) -> str:
    now = datetime.now()
    update_date = f"{now.year}-{now.month:02d}-{now.day:02d}"
    month_label = f"{now.year}年{now.month}月"

    def card_html(r: dict, rank: int) -> str:
        rc = "rank-1" if rank == 1 else "rank-2" if rank == 2 else "rank-3" if rank == 3 else "rank-other"
        lh = f'<span class="lang-dot" style="background:{r["lang_color"]};"></span> {r["language"]}' if r["language"] else ""
        th = "".join(f'<span class="tag">{t}</span>' for t in r["tags"][:5])
        tags_section = f'<div class="tags">{th}</div>' if th else ""
        lic = f'<div class="license">{r["license"]}</div>' if r["license"] else ""
        hot = f'🔥 +{r["stars_period"]:,}' if r["stars_period"] else "🔥 趋势项目"
        return f"""    <div class="project-card">
      <div class="rank-badge {rc}">{rank}</div>
      <div class="card-header">
        <div class="avatar" style="background:{r["avatar_bg"]};color:{r["avatar_fg"]};">{r["avatar_char"]}</div>
        <div class="repo-info">
          <span class="owner">{r["owner"]}</span>
          <div class="repo-name"><span class="name"><a href="{r["url"]}">{r["name"]}</a></span></div>
        </div>
      </div>
      <div class="description">{r["description"]}</div>
      <div class="stats">
        <span class="stat"><span class="star-icon">⭐</span> <span class="num">{r["stars_abbr"]}</span></span>
        <span class="stat stat-fork">⑂ <span class="num">{r["forks_abbr"]}</span></span>
        <span class="hot-badge">{hot}</span>
      </div>
      <div class="meta">
        <span class="lang">{lh}</span>
        {tags_section}
      </div>
      {lic}
    </div>"""

    wcards = "\n".join(card_html(r, i+1) for i, r in enumerate(weekly))
    mcards = "\n".join(card_html(r, i+1) for i, r in enumerate(monthly))

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="description" content="GitHub 中文区 AI 热门项目排行榜 — 每周/每月更新 Trending AI 项目聚合">
  <meta name="keywords" content="GitHub,AI,Trending,中文,热门项目,开源">
  <meta property="og:title" content="GitHub 中文区 AI 热门项目">
  <meta property="og:description" content="AI 开源项目排行榜 · 每周/每月更新">
  <meta property="og:type" content="website">
  <meta property="og:locale" content="zh_CN">
  <meta name="twitter:card" content="summary">
  <title>🤖 GitHub 中文区 AI 热门项目</title>
  <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🤖</text></svg>">
<style>
{CSS}
</style>
</head>
<body>

<div class="container">
  <span class="corner corner-tl"></span>
  <span class="corner corner-tr"></span>
  <span class="corner corner-bl"></span>
  <span class="corner corner-br"></span>
  <span class="bottom-line"></span>
  <header>
    <h1>🤖 GitHub 中文区 AI 热门</h1>
    <p class="subtitle">
      <svg viewBox="0 0 16 16" width="20" height="20"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/></svg>
      数据来自 GitHub Trending · 中文区 AI 热门
    </p>
    <span class="update-badge">📅 {month_label} · 按新增 Star 排序</span>
  </header>

  <div class="toggle-bar">
    <button class="toggle-btn active" data-tab="weekly">本周</button>
    <button class="toggle-btn" data-tab="monthly">本月</button>
  </div>

  <p class="update-time">更新时间：{update_date}</p>

  <div class="project-list" id="weekly-list">
{wcards}
  </div>

  <div class="project-list" id="monthly-list" style="display:none">
{mcards}
  </div>

  <footer>
    <p>数据来源：<a href="https://github.com/trending" target="_blank">GitHub Trending</a> · 由 <a href="https://github.com/D4Vinci/Scrapling" target="_blank">Scrapling</a> 自动抓取 · 更新时间 {update_date}</p>
    <p style="margin-top:4px">用 ⭐ 支持你喜欢的项目！</p>
  </footer>
</div>

<script>
function switchTab(tab) {{
  const currentActive = document.querySelector('.toggle-btn.active');
  const btn = document.querySelector('.toggle-btn[data-tab="'+tab+'"]');
  if (currentActive === btn) return;
  currentActive.classList.remove('active');
  btn.classList.add('active');
  document.getElementById('weekly-list').style.display = tab === 'weekly' ? '' : 'none';
  document.getElementById('monthly-list').style.display = tab === 'monthly' ? '' : 'none';
}}
document.querySelectorAll('.toggle-btn').forEach(function(btn) {{
  btn.addEventListener('click', function(e) {{
    switchTab(this.getAttribute('data-tab'));
  }});
}});
</script>
</body>
</html>"""


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

    html = gen_html(wa[:15], ma[:15])
    OUTPUT_FILE.write_text(html, encoding="utf-8")
    print(f"\n✅ Generated {OUTPUT_FILE}")
    print(f"   Weekly: {len(wa[:15])} AI repos · Monthly: {len(ma[:15])} AI repos")


if __name__ == "__main__":
    main()
