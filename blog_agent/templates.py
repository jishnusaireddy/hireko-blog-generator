"""HTML & CSS template engine for publication-style blog packages."""

import os
import re
import html
import urllib.parse
from typing import Dict, Any, List, Optional


TEMPLATES = ["Hireko Editorial", "Hireko Vercel Editorial"]


def resolve_template_name(template_name: str, title: str = "") -> str:
    """Returns a supported template, with deterministic topic-based Random."""
    template_name = (template_name or "Hireko Editorial").strip()
    if template_name == "Random":
        seed = abs(sum(ord(c) for c in title or "article"))
        return TEMPLATES[seed % len(TEMPLATES)]
    if template_name not in TEMPLATES:
        return "Hireko Editorial"
    return template_name


def clean_prompt_text(value: str) -> str:
    """Keeps image prompts focused and prevents accidental text/chart requests."""
    cleaned = re.sub(r"[^a-zA-Z0-9\s,&-]", " ", value or "").strip()
    return re.sub(r"\s+", " ", cleaned)


def build_pollinations_image_url(prompt: str, seed: int, width: int = 1280, height: int = 720) -> str:
    query = urllib.parse.quote(prompt)
    return f"https://image.pollinations.ai/prompt/{query}?width={width}&height={height}&nologo=true&seed={seed}&model=flux"


def strip_inline_markdown(value: str) -> str:
    value = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", value or "")
    value = re.sub(r"\*\*(.*?)\*\*", r"\1", value)
    value = re.sub(r"\*(.*?)\*", r"\1", value)
    return re.sub(r"\s+", " ", value).strip()


def format_inline_markdown(value: str) -> str:
    """Escapes text, then supports the small inline Markdown subset we emit."""
    text = html.escape(value or "")
    text = re.sub(
        r"\[([^\]]+)\]\((https?://[^)\s]+)\)",
        r'<a href="\2" target="_blank" rel="noopener">\1</a>',
        text,
    )
    text = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*(?!\*)(.*?)(?<!\*)\*(?!\*)", r"<em>\1</em>", text)
    return text


def estimate_reading_minutes(markdown_content: str) -> int:
    word_count = len(re.findall(r"\b\w+\b", markdown_content or ""))
    return max(3, round(word_count / 225))


def extract_key_takeaways(markdown_content: str) -> List[str]:
    block_match = re.search(
        r"(?:^|\n)>?\s*\*\*Key Takeaways:?\*\*\s*(.*?)(?=\n##|\n#|\Z)",
        markdown_content or "",
        re.DOTALL | re.IGNORECASE,
    )
    if not block_match:
        return [
            "Use evidence-led analysis instead of generic market claims.",
            "Pair automation with human review, governance, and clear ownership.",
            "Make recommendations practical for both employers and job seekers.",
        ]

    block = block_match.group(1)
    items = re.findall(r"^\s*>?\s*[-*]\s+(.+?)\s*$", block, re.MULTILINE)
    cleaned = [strip_inline_markdown(item) for item in items if len(strip_inline_markdown(item)) > 12]
    return cleaned[:3] or [
        "Use evidence-led analysis instead of generic market claims.",
        "Pair automation with human review, governance, and clear ownership.",
        "Make recommendations practical for both employers and job seekers.",
    ]


def build_article_snapshot_html(markdown_content: str, sources_count: int, section_count: int) -> str:
    read_minutes = estimate_reading_minutes(markdown_content)
    cards = [
        (str(max(sources_count, 0)), "Sources"),
        (str(max(section_count, 1)), "Sections"),
        (f"{read_minutes}", "Min Read"),
    ]
    return "\n".join([
        '    <div class="key-numbers-strip">',
        *[
            f'''      <div class="number-card">
        <div class="num-val">{html.escape(value)}</div>
        <div class="num-lbl">{html.escape(label)}</div>
      </div>'''
            for value, label in cards
        ],
        "    </div>",
    ])


async def fetch_web_image_search(query: str) -> Optional[str]:
    """
    Deprecated image source.

    We intentionally do not scrape image search for generated reports because
    it often returns old charts, screenshots, logos, and dated report graphics.
    Keep this function as a no-op compatibility hook for older code paths.
    """
    return None


async def generate_article_images_async(topic: str, sections_info: List[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    Topic-aware editorial image engine with resilient fallbacks.

    Never use scraped report screenshots, old charts, or images with readable
    text. For report-like topics, use fresh editorial photography prompts and
    let the article render facts/sources as HTML instead.
    """
    seed = abs(sum(ord(c) for c in topic) * 271) % 1000000
    no_text = "no text, no letters, no words, no numbers, no watermarks, no logos, no charts, no screenshots"
    clean_topic = clean_prompt_text(topic)
    topic_l = clean_topic.lower()
    report_like = any(k in topic_l for k in [
        "report", "reports", "salary", "unemployment", "layoffs", "job openings",
        "job market", "jobs", "labor", "workforce", "employment", "work",
        "trends", "hiring", "recruiting", "recruitment"
    ])

    if report_like:
        hero_scene = (
            "photorealistic editorial workplace scene, adult professionals in a roundtable planning session, "
            "notebooks and laptops, natural daylight, realistic national magazine photography, natural skin tones"
        )
    else:
        hero_scene = (
            "photorealistic modern professional setting, adult people collaborating around a project table, "
            "clean architecture, natural daylight, realistic editorial photography, natural skin tones"
        )

    hero_prompt = f"{hero_scene}, theme of {clean_topic}, high resolution, polished national magazine style, {no_text}"
    hero_url = build_pollinations_image_url(hero_prompt, seed)
    hero_fallback = "https://images.unsplash.com/photo-1497366216548-37526070297c?auto=format&fit=crop&w=1280&q=80"
    hero_source = "AI Editorial Flux"

    sec_data = sections_info or []
    section_images = []

    fallback_urls = [
        "https://images.unsplash.com/photo-1551836022-d5d88e9218df?auto=format&fit=crop&w=1280&q=80",
        "https://images.unsplash.com/photo-1522071820081-009f0129c71c?auto=format&fit=crop&w=1280&q=80",
        "https://images.unsplash.com/photo-1460925895917-afdab827c52f?auto=format&fit=crop&w=1280&q=80",
        "https://images.unsplash.com/photo-1531403009284-440f080d1e12?auto=format&fit=crop&w=1280&q=80"
    ]

    section_themes = [
        "close-up of adult professionals reviewing briefing notes and a laptop, active conversation, warm daylight",
        "small team workshop with adult professionals, notes and laptops, modern training room, candid editorial photography",
        "mentor and candidate discussion between adult professionals at a table, human-centered career planning, natural light",
        "leadership roundtable with adult professionals planning next steps, open meeting space, optimistic daylight"
    ]

    for i in range(4):
        s_title = sec_data[i]["title"] if i < len(sec_data) else f"Section {i+1}"
        clean_title = clean_prompt_text(s_title)
        theme = section_themes[i % len(section_themes)]

        sp = (
            f"Realistic publication editorial photography about {clean_topic}, "
            f"section focus {clean_title}, {theme}, real people, candid active composition, "
            f"photorealistic DSLR photograph, polished documentary style, natural skin tones, {no_text}"
        )
        s_seed = (seed + ((i + 1) * 317)) % 1000000
        sec_url = build_pollinations_image_url(sp, s_seed)

        section_images.append({
            "url": sec_url,
            "fallback_url": fallback_urls[i % len(fallback_urls)],
            "title": s_title,
            "caption": f"Figure {i+1}. {s_title} - editorial visual.",
            "source_org": "Editorial Visual Research"
        })

    return {
        "hero": {"url": hero_url, "fallback_url": hero_fallback, "title": topic, "caption": f"Figure 0. {topic} Overview visual.", "source": hero_source},
        "sections": section_images
    }


def get_template_style(template_name: str) -> str:
    """Returns CSS styles with optimal typography, breathing room, 2-column cards, and numbered TOC."""
    template_name = resolve_template_name(template_name)

    common_css = """
.top-action-bar {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  max-width: 840px;
  margin: 1.5rem auto 0 auto;
  padding: 0 1.5rem;
}

.btn-pill {
  background: var(--accent-light);
  color: var(--accent);
  border: 1px solid rgba(37, 99, 235, 0.2);
  padding: 0.4rem 1.1rem;
  border-radius: 9999px;
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-pill:hover {
  background: var(--accent);
  color: #ffffff;
}

.hero-banner {
  max-width: 1040px;
  margin: 2.25rem auto 1.75rem auto;
  padding: 0 1.5rem;
}

.category-tag {
  display: inline-block;
  font-size: 0.8rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--accent);
  margin-bottom: 0.5rem;
}

.hero-banner h1 {
  font-size: 3rem;
  font-weight: 800;
  color: var(--text-main);
  line-height: 1.2;
  margin: 0 0 0.75rem 0;
}

.hero-dek {
  font-size: 1.25rem;
  color: var(--text-muted);
  line-height: 1.6;
  margin-bottom: 1.5rem;
}

.hero-img-card {
  margin: 1.75rem 0 0 0;
  border-radius: 14px;
  overflow: hidden;
  box-shadow: 0 18px 42px -8px rgba(15, 23, 42, 0.18);
  border: 1px solid var(--border);
}

.hero-img-card img {
  width: 100%;
  height: 420px;
  object-fit: cover;
  display: block;
}

.article-container {
  max-width: 840px;
  margin: 0 auto 4rem auto;
  padding: 3rem;
  background: var(--bg-card);
  border-radius: 16px;
  box-shadow: 0 10px 40px -5px rgba(0, 0, 0, 0.04);
  border: 1px solid var(--border);
}

.publication-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 1.5rem;
  padding-bottom: 1.25rem;
  border-bottom: 1px solid var(--border);
  margin-bottom: 2.5rem;
  font-size: 0.9rem;
  color: var(--text-muted);
}

.exec-summary-box {
  background: var(--accent-light);
  border-left: 4px solid var(--accent);
  padding: 1.5rem;
  border-radius: 8px;
  margin-bottom: 2.5rem;
}

.exec-summary-box h3 {
  margin-top: 0;
  color: var(--accent);
  font-size: 1.15rem;
  margin-bottom: 0.5rem;
}

.key-numbers-strip {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 1.25rem;
  margin-bottom: 3rem;
}

.number-card {
  background: #f8fafc;
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 1.25rem;
  text-align: center;
}

.number-card .num-val {
  font-size: 2.2rem;
  font-weight: 800;
  color: var(--accent);
  line-height: 1;
  margin-bottom: 0.4rem;
}

.number-card .num-lbl {
  font-size: 0.85rem;
  color: var(--text-muted);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.toc-box {
  background: #f8fafc;
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 1.75rem;
  margin-bottom: 3.5rem;
}

.toc-box h3 {
  margin-top: 0;
  color: var(--text-main);
  font-size: 1.1rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.toc-list {
  list-style: none;
  padding-left: 0;
  margin-bottom: 0;
}

.toc-list li {
  display: flex;
  align-items: baseline;
  gap: 1rem;
  margin-bottom: 0.75rem;
}

.toc-list .num {
  font-weight: 800;
  color: var(--accent);
  font-size: 0.95rem;
}

.toc-list a {
  color: var(--text-main);
  text-decoration: none;
  font-weight: 500;
  transition: color 0.2s;
}

.toc-list a:hover {
  color: var(--accent);
  text-decoration: underline;
}

h2 {
  font-size: 28px;
  font-weight: 800;
  color: var(--text-main);
  border-left: 4px solid var(--accent);
  padding-left: 0.85rem;
  margin-top: 4rem;
  margin-bottom: 1.5rem;
}

h3 {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-main);
  margin-top: 2.5rem;
  margin-bottom: 1rem;
}

p {
  font-size: 17px;
  line-height: 1.75;
  margin-bottom: 1.75rem;
}

blockquote {
  background: var(--accent-light);
  border-left: 4px solid var(--accent);
  margin: 2.5rem 0;
  padding: 1.25rem 1.5rem;
  border-radius: 0 8px 8px 0;
  font-style: italic;
  color: #1e3a8a;
}

.takeaways-container {
  margin-bottom: 3rem;
}

.takeaway-bullet-card {
  background: #f8fafc;
  border: 1px solid var(--border);
  border-left: 4px solid var(--accent);
  padding: 1.25rem;
  border-radius: 6px;
  margin-bottom: 1rem;
  font-size: 1.05rem;
}

.what-means-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 1.5rem;
  margin: 2.5rem 0;
}

.means-card {
  background: #f8fafc;
  border: 1px solid var(--border);
  border-top: 4px solid var(--accent);
  border-radius: 10px;
  padding: 1.5rem;
}

.means-card h4 {
  margin-top: 0;
  color: var(--accent);
  font-size: 1.1rem;
  margin-bottom: 0.75rem;
}

.means-card ul {
  margin: 0;
  padding-left: 1.25rem;
}

.means-card li {
  margin-bottom: 0.5rem;
  font-size: 0.98rem;
}

.section-image-card {
  max-width: 700px;
  margin: 2.25rem auto 2.5rem auto;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 14px 34px rgba(15, 23, 42, 0.10);
  border: 1px solid var(--border);
  background: #ffffff;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.section-image-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 30px rgba(0, 0, 0, 0.12);
}

.thumbnail-badge {
  background: #f1f5f9;
  color: var(--accent);
  font-size: 0.78rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  padding: 0.45rem 1rem;
  border-bottom: 1px solid var(--border);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.section-image-card img {
  width: 100%;
  height: 340px;
  object-fit: cover;
  display: block;
  cursor: zoom-in;
  transition: opacity 0.2s;
}

.section-image-card img:hover {
  opacity: 0.95;
}

.section-image-card figcaption {
  padding: 0.75rem 1.25rem;
  font-size: 13px;
  color: var(--text-muted);
  text-align: center;
  background: #f8fafc;
  border-top: 1px solid var(--border);
}

@media (max-width: 640px) {
  .hero-banner h1 {
    font-size: 2.2rem;
  }

  .hero-dek {
    font-size: 1.05rem;
  }

  .hero-img-card img,
  .section-image-card img {
    height: 230px;
  }

  .article-container {
    padding: 1.5rem;
    border-radius: 12px;
  }
}

.zoom-hint {
  font-size: 0.75rem;
  color: var(--accent);
  font-weight: 600;
  margin-left: 0.35rem;
}

.lightbox-overlay {
  display: none;
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(15, 23, 42, 0.85);
  backdrop-filter: blur(4px);
  z-index: 9999;
  justify-content: center;
  align-items: center;
  flex-direction: column;
  padding: 2rem;
  cursor: pointer;
}

.lightbox-overlay img {
  max-width: 90%;
  max-height: 80vh;
  border-radius: 12px;
  box-shadow: 0 20px 50px rgba(0,0,0,0.5);
  border: 2px solid rgba(255,255,255,0.2);
}

.lightbox-caption {
  color: #ffffff;
  margin-top: 1rem;
  font-size: 1rem;
  font-weight: 500;
  text-align: center;
}

.lightbox-close {
  position: absolute;
  top: 1.5rem;
  right: 2rem;
  color: #ffffff;
  font-size: 2rem;
  font-weight: 700;
  cursor: pointer;
}

.citation-list {
  background: #f8fafc;
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 2rem;
  margin-top: 4.5rem;
}

.citation-list h4 {
  margin-top: 0;
  color: var(--text-main);
  font-size: 1.2rem;
  margin-bottom: 1.25rem;
}

.citation-list ol {
  padding-left: 1.25rem;
  margin-bottom: 0;
}

.citation-list li {
  margin-bottom: 0.6rem;
}

.citation-list a {
  color: var(--accent);
  text-decoration: none;
  font-weight: 500;
}

.citation-list a:hover {
  text-decoration: underline;
}

.footer-bar {
  text-align: center;
  padding: 3.5rem 1rem;
  border-top: 1px solid var(--border);
  color: var(--text-muted);
  font-size: 0.92rem;
}

.footer-links {
  margin-top: 0.85rem;
  display: flex;
  justify-content: center;
  gap: 1.5rem;
}

.footer-links a {
  color: var(--text-muted);
  text-decoration: none;
}

.footer-links a:hover {
  color: var(--accent);
}
"""

    if template_name == "Casual Blog":
        return """
:root {
  --bg-primary: #fbfcfd;
  --bg-card: #ffffff;
  --accent: #2563eb;
  --accent-light: #eff6ff;
  --text-main: #1f2937;
  --text-muted: #6b7280;
  --border: #e5e7eb;
}

body {
  background: var(--bg-primary);
  color: var(--text-main);
}

.top-action-bar {
  max-width: 860px;
  margin-top: 1rem;
}

.hero-banner {
  max-width: 860px;
  margin-top: 2.2rem;
  margin-bottom: 1.25rem;
}

.category-tag {
  color: var(--accent);
  letter-spacing: 0.06em;
}

.hero-banner h1 {
  max-width: 800px;
  font-size: 2.75rem;
  line-height: 1.12;
  letter-spacing: 0;
}

.hero-dek {
  max-width: 760px;
  font-size: 1.08rem;
  line-height: 1.65;
}

.hero-img-card {
  border-radius: 10px;
  box-shadow: 0 12px 32px rgba(15, 23, 42, 0.10);
}

.hero-img-card img {
  height: 360px;
}

.article-container {
  max-width: 780px;
  padding: 2.4rem;
  border-radius: 12px;
  box-shadow: 0 16px 42px rgba(15, 23, 42, 0.06);
}

.publication-meta,
.key-numbers-strip {
  display: none;
}

.exec-summary-box {
  background: #f8fafc;
  border-left: 3px solid var(--accent);
  border-radius: 8px;
  padding: 1.1rem 1.25rem;
  margin-bottom: 1.75rem;
}

.exec-summary-box h3 {
  font-size: 1rem;
  margin-bottom: 0.45rem;
}

.toc-box {
  padding: 1.2rem 1.35rem;
  margin-bottom: 2.2rem;
  border-radius: 10px;
}

.toc-box h3 {
  font-size: 0.95rem;
  letter-spacing: 0.04em;
}

h2 {
  border-left: 0;
  padding-left: 0;
  margin-top: 3.2rem;
  font-size: 26px;
}

h2::before {
  content: "";
  display: block;
  width: 36px;
  height: 3px;
  background: var(--accent);
  border-radius: 999px;
  margin-bottom: 0.7rem;
}

p {
  font-size: 18px;
  line-height: 1.8;
}

ul,
ol {
  font-size: 17px;
  line-height: 1.75;
}

blockquote {
  background: #f8fafc;
  color: #334155;
  border-left-width: 3px;
  font-style: normal;
}

.takeaways-container h3 {
  text-transform: none !important;
  letter-spacing: 0 !important;
}

.takeaway-bullet-card {
  background: #ffffff;
  border-left: 3px solid var(--accent);
  padding: 1rem 1.1rem;
  font-size: 1rem;
}

.section-image-card {
  max-width: 100%;
  border-radius: 10px;
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.08);
}

.section-image-card img {
  height: 310px;
}

.thumbnail-badge {
  display: none;
}

.section-image-card figcaption {
  font-size: 12px;
  padding: 0.7rem 1rem;
}

.citation-list {
  margin-top: 3rem;
  padding: 1.4rem;
}

@media (max-width: 640px) {
  .hero-banner h1 {
    font-size: 2.1rem;
  }

  .hero-img-card img,
  .section-image-card img {
    height: 230px;
  }

  .article-container {
    padding: 1.35rem;
  }

  p {
    font-size: 16.5px;
  }
}
""" + common_css

    if template_name in ("Hireko Editorial", "Hireko Vercel Editorial"):
        return """
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,100..1000;1,9..40,100..1000&family=Poppins:ital,wght@0,400;0,500;0,600;0,700;1,400;1,600&display=swap');

:root {
  --hireko-navy: #0F172A;
  --hireko-cerulean: #00A1D4;
  --hireko-green: #6FCA9F;
  --hireko-orchid: #A64BBC;
  --hireko-gradient: linear-gradient(135deg, #00A1D4 0%, #6FCA9F 100%);
  --hireko-soft: #F0FBF6;
  --hireko-soft-blue: #EEF9FD;
  --hireko-text: #0F172A;
  --hireko-muted: #5C6B7A;
  --hireko-border: #E2E8F0;
  --hireko-shadow: 0 14px 34px rgba(15, 23, 42, 0.08);
}

* {
  box-sizing: border-box;
}

html {
  scroll-behavior: smooth;
}

::selection {
  background: #BDE9E1;
  color: var(--hireko-navy);
}

body {
  margin: 0;
  background: #ffffff;
  color: var(--hireko-text);
  font-family: 'DM Sans', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  line-height: 1.7;
  font-size: 17px;
  -webkit-font-smoothing: antialiased;
}

/* Header */
.hireko-nav {
  position: sticky;
  top: 0;
  z-index: 50;
  background: #ffffff;
  border-bottom: 1px solid var(--hireko-border);
}

.hireko-nav-inner {
  max-width: 1240px;
  margin: 0 auto;
  min-height: 70px;
  padding: 0.75rem 1.5rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1.5rem;
}

.hireko-logo {
  display: inline-flex;
  align-items: center;
  text-decoration: none;
  flex-shrink: 0;
}

.hireko-logo-lockup {
  display: block;
  width: 160px;
  height: auto;
  max-width: 100%;
}

.hireko-nav-links {
  display: flex;
  align-items: center;
  gap: 1.75rem;
  font-family: 'Poppins', sans-serif;
  font-size: 0.92rem;
  font-weight: 500;
}

.hireko-nav-links a {
  color: var(--hireko-navy);
  text-decoration: none;
  transition: color 150ms ease;
}

.hireko-nav-links a:hover,
.hireko-login:hover {
  color: var(--hireko-cerulean);
}

.hireko-nav-actions {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.hireko-login {
  color: var(--hireko-navy);
  font-family: 'Poppins', sans-serif;
  font-size: 0.92rem;
  font-weight: 600;
  text-decoration: none;
  padding: 0.5rem 0.75rem;
}

.hireko-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 42px;
  padding: 0.65rem 1.25rem;
  border: 0;
  border-radius: 8px;
  background: var(--hireko-gradient);
  color: #ffffff;
  font-family: 'Poppins', sans-serif;
  font-size: 0.9rem;
  font-weight: 600;
  text-decoration: none;
  box-shadow: 0 4px 14px rgba(0, 161, 212, 0.25);
  transition: transform 160ms ease, box-shadow 160ms ease;
  cursor: pointer;
}

.hireko-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 8px 20px rgba(0, 161, 212, 0.35);
}

.hireko-btn:focus-visible,
.hireko-nav a:focus-visible,
.hireko-toc a:focus-visible,
.hireko-article a:focus-visible {
  outline: 3px solid rgba(0, 161, 212, 0.35);
  outline-offset: 2px;
}

/* Breadcrumbs */
.hireko-breadcrumb {
  max-width: 1240px;
  margin: 0 auto;
  padding: 1rem 1.5rem;
  color: #64748B;
  font-size: 0.88rem;
  font-family: 'DM Sans', sans-serif;
}

.hireko-breadcrumb a {
  color: var(--hireko-navy);
  text-decoration: none;
  font-weight: 500;
}

.hireko-breadcrumb a:hover {
  color: var(--hireko-cerulean);
}

.hireko-breadcrumb .active-category {
  color: var(--hireko-cerulean);
  font-weight: 600;
}

/* Hero Section */
.hireko-hero {
  position: relative;
  overflow: hidden;
  background: var(--hireko-navy);
  color: #ffffff;
}

.hireko-hero-inner {
  position: relative;
  z-index: 1;
  max-width: 1080px;
  margin: 0 auto;
  padding: 4rem 1.5rem 3rem;
}

.hireko-hero-copy {
  max-width: 820px;
  margin: 0 auto;
  text-align: center;
}

.hireko-category {
  display: inline-flex;
  margin-bottom: 0.85rem;
  color: var(--hireko-cerulean);
  font-family: 'Poppins', sans-serif;
  font-size: 0.8rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.hireko-hero h1 {
  max-width: 820px;
  margin: 0 0 1.25rem;
  font-family: 'Poppins', sans-serif;
  font-size: 3.25rem;
  line-height: 1.15;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.gradient-text {
  background: var(--hireko-gradient);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}

.hireko-hero-dek {
  max-width: 700px;
  margin: 0 auto 1.75rem;
  color: #94A3B8;
  font-size: 1.15rem;
  line-height: 1.6;
}

.hireko-meta {
  display: flex;
  justify-content: center;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.75rem 1.25rem;
  color: #94A3B8;
  font-size: 0.92rem;
}

.hireko-meta strong {
  color: #FFFFFF;
}

.hireko-meta span + span::before {
  content: "";
  display: inline-block;
  width: 4px;
  height: 4px;
  margin: 0 0.85rem 0.15rem 0;
  border-radius: 50%;
  background: var(--hireko-green);
}

/* Dashboard Visual */
.hireko-dashboard-visual {
  padding: 0.85rem;
  border: 1px solid rgba(111, 202, 159, 0.34);
  border-radius: 10px;
  background: linear-gradient(145deg, rgba(0, 161, 212, 0.20), rgba(111, 202, 159, 0.05)), var(--hireko-navy);
  box-shadow: 0 25px 60px rgba(0, 0, 0, 0.35);
}

.hero-dashboard {
  margin-top: 2.75rem;
}

.visual-window {
  overflow: hidden;
  border-radius: 8px;
  background: #12243E;
  border: 1px solid rgba(255, 255, 255, 0.10);
}

.visual-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.85rem 1.15rem;
  color: #ffffff;
  background: rgba(15, 23, 42, 0.75);
  border-bottom: 1px solid rgba(255, 255, 255, 0.10);
  font-family: 'Poppins', sans-serif;
  font-size: 0.8rem;
  font-weight: 600;
}

.visual-status {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  color: #BFECDD;
  font-size: 0.72rem;
  font-weight: 600;
}

.visual-status::before {
  content: "";
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--hireko-green);
  box-shadow: 0 0 0 4px rgba(111, 202, 159, 0.15);
}

.visual-body {
  padding: 1.15rem;
  display: grid;
  grid-template-columns: minmax(210px, 0.8fr) minmax(300px, 1.2fr) minmax(180px, 0.6fr);
  gap: 1rem;
  align-items: stretch;
  color: #ffffff;
}

.candidate-card {
  display: grid;
  grid-template-columns: 46px minmax(0, 1fr) auto;
  gap: 0.75rem;
  align-items: center;
  padding: 0.95rem;
  border: 1px solid rgba(191, 236, 221, 0.20);
  border-radius: 8px;
  background: linear-gradient(105deg, rgba(0, 161, 212, 0.12), rgba(255, 255, 255, 0.03));
}

.candidate-avatar {
  display: grid;
  width: 46px;
  height: 46px;
  place-items: center;
  border-radius: 8px;
  background: var(--hireko-gradient);
  color: var(--hireko-navy);
  font-family: 'Poppins', sans-serif;
  font-size: 0.85rem;
  font-weight: 700;
}

.candidate-details span {
  display: block;
  color: #ffffff;
  font-family: 'Poppins', sans-serif;
  font-size: 0.84rem;
  font-weight: 600;
}

.candidate-details small {
  display: block;
  margin-top: 0.15rem;
  color: #94A3B8;
  font-size: 0.72rem;
}

.candidate-score {
  display: grid;
  min-width: 44px;
  min-height: 44px;
  place-items: center;
  border: 1px solid rgba(111, 202, 159, 0.35);
  border-radius: 8px;
  background: rgba(111, 202, 159, 0.12);
  color: #BFECDD;
  font-family: 'Poppins', sans-serif;
  font-size: 0.82rem;
  font-weight: 700;
}

.visual-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.85rem;
}

.visual-panel {
  padding: 1rem;
  border: 1px solid rgba(191, 236, 221, 0.16);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.04);
}

.visual-panel strong {
  display: block;
  margin-bottom: 0.65rem;
  font-family: 'Poppins', sans-serif;
  font-size: 0.8rem;
  color: #ffffff;
}

.signal-row {
  display: grid;
  grid-template-columns: 1fr 1.25rem;
  gap: 0.35rem 0.55rem;
  align-items: center;
  margin: 0.55rem 0;
}

.signal-row span {
  color: #CBD5E1;
  font-size: 0.7rem;
}

.signal-row em {
  color: #BFECDD;
  font-family: 'Poppins', sans-serif;
  font-size: 0.68rem;
  font-style: normal;
  font-weight: 700;
  text-align: right;
}

.signal-bar {
  grid-column: 1 / -1;
  height: 6px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.15);
  overflow: hidden;
}

.signal-bar span {
  display: block;
  height: 100%;
  background: var(--hireko-gradient);
}

.interview-flow {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 0.45rem;
  align-items: center;
  margin-top: 1rem;
}

.interview-flow span {
  position: relative;
  display: grid;
  min-height: 48px;
  place-items: center;
  border: 1px solid rgba(191, 236, 221, 0.16);
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.06);
  color: #DDF7F0;
  font-family: 'Poppins', sans-serif;
  font-size: 0.68rem;
  font-weight: 600;
  text-align: center;
}

.interview-flow span::after {
  content: "";
  position: absolute;
  right: -0.35rem;
  top: 50%;
  width: 0.3rem;
  height: 1px;
  background: var(--hireko-green);
}

.interview-flow span:last-child::after {
  display: none;
}

.match-summary {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 0.5rem 1rem;
  align-items: end;
  padding: 0.95rem;
  border: 1px solid rgba(191, 236, 221, 0.18);
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.15);
}

.match-summary small {
  display: block;
  color: #94A3B8;
  font-size: 0.72rem;
}

.match-summary strong {
  color: #ffffff;
  font-family: 'Poppins', sans-serif;
  font-size: 0.95rem;
}

.hireko-score-bar {
  grid-column: 1 / -1;
  height: 6px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.16);
  overflow: hidden;
}

.hireko-score-bar span {
  display: block;
  width: 82%;
  height: 100%;
  background: var(--hireko-gradient);
}

/* Main Layout & Two-Column Architecture */
.hireko-layout {
  max-width: 1240px;
  margin: 0 auto;
  padding: 4.5rem 1.5rem;
  display: grid;
  grid-template-columns: 240px minmax(0, 760px);
  gap: 4.5rem;
  align-items: start;
}

.hireko-toc {
  position: sticky;
  top: 96px;
  border-left: 2px solid var(--hireko-cerulean);
  padding: 0.3rem 0 0.3rem 1rem;
}

.hireko-toc h3 {
  margin: 0 0 0.9rem;
  font-family: 'Poppins', sans-serif;
  font-size: 0.8rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--hireko-navy);
  font-weight: 700;
}

.hireko-toc ul {
  list-style: none;
  margin: 0;
  padding: 0;
}

.hireko-toc li {
  display: grid;
  grid-template-columns: 1.8rem minmax(0, 1fr);
  gap: 0.2rem;
  margin: 0 0 0.75rem;
  align-items: start;
}

.hireko-toc .num {
  color: var(--hireko-cerulean);
  font-family: 'Poppins', sans-serif;
  font-size: 0.78rem;
  font-weight: 700;
}

.hireko-toc a {
  color: var(--hireko-muted);
  font-size: 0.88rem;
  line-height: 1.45;
  text-decoration: none;
  transition: color 150ms ease;
}

.hireko-toc a:hover {
  color: var(--hireko-cerulean);
}

.hireko-article {
  max-width: 760px;
}

/* Key Takeaway Card */
.key-takeaway-card {
  margin-bottom: 2.25rem;
  padding: 1.4rem 1.6rem;
  border-left: 4px solid var(--hireko-cerulean);
  border-radius: 8px;
  background: var(--hireko-soft);
  box-shadow: none;
}

.key-takeaway-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.key-takeaway-header span {
  font-family: 'Poppins', sans-serif;
  font-size: 0.8rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: var(--hireko-cerulean);
  text-transform: uppercase;
}

.key-takeaway-card p {
  margin: 0;
  font-family: 'DM Sans', sans-serif;
  font-size: 1.05rem;
  line-height: 1.65;
  color: var(--hireko-navy);
  font-weight: 500;
}

/* Article Typography */
.hireko-article h2,
.content-body h2 {
  margin: 3rem 0 1.15rem;
  font-family: 'Poppins', sans-serif;
  font-size: 2.15rem;
  line-height: 1.25;
  font-weight: 600;
  color: var(--hireko-navy);
}

.hireko-article h3,
.content-body h3 {
  margin: 2.25rem 0 0.75rem;
  font-family: 'Poppins', sans-serif;
  font-size: 1.35rem;
  line-height: 1.35;
  font-weight: 600;
  color: var(--hireko-navy);
}

.hireko-article p,
.hireko-article li,
.content-body p,
.content-body li {
  color: #334155;
  font-size: 1.05rem;
  line-height: 1.72;
}

.hireko-article a,
.content-body a {
  color: var(--hireko-cerulean);
  text-decoration: underline;
  text-underline-offset: 3px;
}

.hireko-article a:hover,
.content-body a:hover {
  color: var(--hireko-green);
}

.hireko-article blockquote,
.content-body blockquote {
  margin: 2.25rem 0;
  padding: 1.35rem 1.6rem;
  border-left: 4px solid var(--hireko-green);
  border-radius: 8px;
  background: var(--hireko-soft);
  color: var(--hireko-navy);
  font-size: 1.08rem;
  font-style: normal;
}

/* Section Images */
.section-image-card {
  margin: 2.25rem 0;
  border: 1px solid var(--hireko-border);
  border-radius: 10px;
  overflow: hidden;
  box-shadow: var(--hireko-shadow);
}

.section-image-card img {
  width: 100%;
  height: 340px;
  object-fit: cover;
  display: block;
}

.thumbnail-badge,
.section-image-card figcaption {
  display: none;
}

/* Hireko Insight Card */
.hireko-insight {
  position: relative;
  overflow: hidden;
  margin: 2.5rem 0;
  padding: 1.8rem 2rem;
  background: var(--hireko-navy);
  border-radius: 10px;
  color: #ffffff;
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.hireko-insight-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
}

.hireko-insight h3 {
  margin: 0;
  font-family: 'Poppins', sans-serif;
  font-size: 1.15rem;
  font-weight: 700;
  color: #ffffff;
}

.hireko-insight p {
  margin: 0;
  color: #D6E3E8;
  font-family: 'DM Sans', sans-serif;
  font-size: 1.02rem;
  line-height: 1.65;
}

.hireko-icon {
  width: 32px;
  height: 32px;
  color: var(--hireko-cerulean);
  flex-shrink: 0;
}

/* Checklist Card */
.hireko-checklist {
  margin: 2.25rem 0;
  padding: 1.5rem 1.8rem;
  border: 1px solid var(--hireko-border);
  border-radius: 10px;
  background: #ffffff;
  box-shadow: 0 4px 16px rgba(15, 23, 42, 0.04);
}

.hireko-checklist h3 {
  margin: 0 0 1rem;
  font-family: 'Poppins', sans-serif;
  font-size: 1.15rem;
  font-weight: 700;
  color: var(--hireko-navy);
}

.hireko-checklist ul {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 0.85rem 1.25rem;
}

.hireko-checklist li {
  position: relative;
  padding-left: 2rem;
  font-size: 0.98rem;
  color: #334155;
  line-height: 1.5;
}

.hireko-checklist li::before {
  content: "";
  position: absolute;
  left: 0;
  top: 2px;
  width: 18px;
  height: 18px;
  border: 2px solid var(--hireko-cerulean);
  border-radius: 4px;
  background: rgba(0, 161, 212, 0.06);
}

.hireko-checklist li::after {
  content: "";
  position: absolute;
  left: 6px;
  top: 4px;
  width: 5px;
  height: 9px;
  border: solid var(--hireko-cerulean);
  border-width: 0 2px 2px 0;
  transform: rotate(45deg);
}

/* Comparison Tables */
.hireko-compare,
.hireko-article table,
.content-body table {
  width: 100%;
  border-collapse: collapse;
  margin: 2rem 0;
  border: 1px solid var(--hireko-border);
  border-radius: 8px;
  overflow: hidden;
  font-size: 0.95rem;
}

.hireko-compare th,
.hireko-article table th,
.content-body table th {
  background: var(--hireko-navy);
  color: #ffffff;
  font-family: 'Poppins', sans-serif;
  font-weight: 600;
  padding: 0.9rem 1.15rem;
  text-align: left;
  border-bottom: 2px solid var(--hireko-cerulean);
}

.hireko-compare td,
.hireko-article table td,
.content-body table td {
  padding: 0.85rem 1.15rem;
  border-bottom: 1px solid var(--hireko-border);
  color: #334155;
  vertical-align: top;
}

.hireko-compare tr:nth-child(even) td,
.hireko-article table tr:nth-child(even) td,
.content-body table tr:nth-child(even) td {
  background: #F8FAFC;
}

.hireko-compare tr:hover td,
.hireko-article table tr:hover td,
.content-body table tr:hover td {
  background: #F0FBF6;
}

.hireko-compare td:first-child,
.hireko-article table td:first-child,
.content-body table td:first-child {
  font-weight: 600;
  color: var(--hireko-navy);
}

/* Workflow Diagram */
.hireko-workflow {
  margin: 2.25rem 0;
  padding: 1.5rem;
  border: 1px solid var(--hireko-border);
  border-radius: 10px;
  background: #ffffff;
  box-shadow: 0 4px 16px rgba(15, 23, 42, 0.04);
}

.hireko-workflow h3 {
  margin: 0 0 1rem;
  font-family: 'Poppins', sans-serif;
  font-size: 1.15rem;
  font-weight: 700;
  color: var(--hireko-navy);
}

.workflow-steps {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0.75rem;
}

.workflow-step {
  min-height: 126px;
  padding: 1rem;
  border: 1px solid var(--hireko-border);
  border-top: 4px solid var(--hireko-cerulean);
  border-radius: 8px;
  background: #F9FDFE;
}

.workflow-step:nth-child(even) {
  border-top-color: var(--hireko-green);
}

.workflow-step span {
  display: block;
  color: var(--hireko-orchid);
  font-family: 'Poppins', sans-serif;
  font-weight: 800;
  font-size: 0.85rem;
}

.workflow-step strong {
  display: block;
  margin: 0.25rem 0;
  font-family: 'Poppins', sans-serif;
  font-size: 0.95rem;
  color: var(--hireko-navy);
}

.workflow-step p {
  margin: 0;
  font-size: 0.86rem;
  line-height: 1.5;
  color: #475569;
}

/* Mid-Article Product CTA */
.hireko-mid-cta {
  margin: 3rem 0;
  position: relative;
  overflow: hidden;
  padding: 2.25rem 2.5rem;
  background: linear-gradient(135deg, #EEF9FD 0%, #F0FBF6 100%);
  border: 1px solid var(--hireko-border);
  border-radius: 10px;
}

.hireko-mid-cta h2 {
  margin: 0 0 0.5rem;
  font-family: 'Poppins', sans-serif;
  font-size: 1.45rem;
  font-weight: 700;
  color: var(--hireko-navy);
}

.hireko-mid-cta p {
  margin: 0 0 1.25rem;
  color: #475569;
  font-size: 1.02rem;
  max-width: 580px;
}

/* Download resource card */
.hireko-resource {
  margin: 2.5rem 0;
  padding: 1.4rem 1.6rem;
  display: grid;
  grid-template-columns: 46px 1fr auto;
  align-items: center;
  gap: 1.25rem;
  border: 1px solid var(--hireko-border);
  border-left: 4px solid var(--hireko-orchid);
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 4px 16px rgba(15, 23, 42, 0.04);
}

.hireko-resource-icon {
  width: 46px;
  height: 46px;
  border-radius: 8px;
  display: grid;
  place-items: center;
  background: rgba(166, 75, 188, 0.1);
  color: var(--hireko-orchid);
  font-family: 'Poppins', sans-serif;
  font-weight: 800;
  font-size: 0.82rem;
}

.hireko-resource h3 {
  margin: 0 0 0.25rem;
  font-family: 'Poppins', sans-serif;
  font-size: 1.05rem;
  color: var(--hireko-navy);
}

.hireko-resource p {
  margin: 0;
  color: #475569;
  font-size: 0.92rem;
}

/* Author Section */
.hireko-author-card {
  display: flex;
  gap: 1.25rem;
  align-items: flex-start;
  margin: 3rem 0;
  padding: 1.6rem 1.8rem;
  border: 1px solid var(--hireko-border);
  border-radius: 10px;
  background: #F8FAFC;
}

.author-avatar {
  display: grid;
  place-items: center;
  width: 52px;
  height: 52px;
  flex-shrink: 0;
  border-radius: 50%;
  background: var(--hireko-navy);
  color: var(--hireko-cerulean);
}

.author-hireko-symbol {
  width: 30px;
  height: 30px;
}

.author-info {
  flex: 1;
}

.author-header {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  margin-bottom: 0.25rem;
}

.author-name {
  font-family: 'Poppins', sans-serif;
  font-size: 1.05rem;
  font-weight: 700;
  color: var(--hireko-navy);
}

.author-badge {
  font-size: 0.72rem;
  font-weight: 700;
  color: var(--hireko-cerulean);
  background: rgba(0, 161, 212, 0.1);
  padding: 0.2rem 0.55rem;
  border-radius: 999px;
}

.author-role {
  font-size: 0.85rem;
  color: var(--hireko-muted);
  font-weight: 500;
  margin-bottom: 0.5rem;
}

.author-bio {
  font-size: 0.94rem;
  color: #334155;
  line-height: 1.6;
  margin: 0 0 0.75rem 0;
}

.author-social {
  display: flex;
  gap: 1rem;
  font-size: 0.85rem;
}

.author-social a {
  color: var(--hireko-cerulean);
  text-decoration: none;
  font-weight: 600;
}

.author-social a:hover {
  text-decoration: underline;
}

/* Related Articles */
.hireko-related {
  max-width: 1240px;
  margin: 0 auto;
  padding: 0 1.5rem 4rem;
}

.hireko-related h2 {
  font-family: 'Poppins', sans-serif;
  font-size: 1.85rem;
  font-weight: 700;
  color: var(--hireko-navy);
  margin-bottom: 1.5rem;
}

.related-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1.5rem;
}

.related-card {
  overflow: hidden;
  border: 1px solid var(--hireko-border);
  border-radius: 10px;
  background: #ffffff;
  box-shadow: 0 4px 16px rgba(15, 23, 42, 0.05);
  transition: transform 160ms ease, box-shadow 160ms ease;
  display: flex;
  flex-direction: column;
}

.related-card:hover {
  transform: translateY(-3px);
  box-shadow: var(--hireko-shadow);
}

.related-card-visual {
  height: 60px;
  position: relative;
  overflow: hidden;
  background: var(--hireko-navy);
}

.related-card-body {
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  flex: 1;
}

.related-card .tag {
  color: var(--hireko-cerulean);
  font-size: 0.76rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  margin-bottom: 0.35rem;
}

.related-card h3 {
  margin: 0 0 0.5rem;
  font-family: 'Poppins', sans-serif;
  font-size: 1.1rem;
  line-height: 1.4;
  color: var(--hireko-navy);
}

.related-card p {
  margin: 0 0 1rem;
  color: #475569;
  font-size: 0.92rem;
  line-height: 1.55;
  flex: 1;
}

.related-card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: auto;
}

.read-time {
  color: var(--hireko-muted);
  font-size: 0.85rem;
}

.related-arrow {
  color: var(--hireko-cerulean);
  font-weight: 700;
  font-size: 1.1rem;
}

/* Final CTA Section */
.hireko-final-cta {
  position: relative;
  overflow: hidden;
  background: var(--hireko-navy);
  color: #ffffff;
}

.hireko-final-cta-inner {
  position: relative;
  z-index: 1;
  max-width: 1240px;
  margin: 0 auto;
  padding: 4.5rem 1.5rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 2rem;
}

.hireko-final-cta h2 {
  max-width: 650px;
  margin: 0 0 0.5rem;
  font-family: 'Poppins', sans-serif;
  font-size: 2.25rem;
  font-weight: 700;
  line-height: 1.2;
}

.hireko-final-cta p {
  margin: 0;
  color: #CBD5E1;
  font-size: 1.05rem;
}

/* Sources */
.citation-list {
  margin-top: 3rem;
  padding: 1.4rem 1.6rem;
  border: 1px solid var(--hireko-border);
  border-radius: 8px;
  background: #F8FAFC;
}

.citation-list h4 {
  margin: 0 0 0.8rem;
  font-family: 'Poppins', sans-serif;
  color: var(--hireko-navy);
  font-size: 1rem;
}

.citation-list a {
  color: var(--hireko-cerulean);
  font-weight: 600;
  text-decoration: none;
}

.citation-list a:hover {
  text-decoration: underline;
}

.lightbox-overlay,
.top-action-bar,
.footer-bar {
  display: none;
}

/* Responsive Breakpoints */
@media (max-width: 980px) {
  .hireko-nav-links {
    display: none;
  }

  .hireko-layout {
    grid-template-columns: 1fr;
    gap: 2.5rem;
  }

  .hireko-toc {
    position: relative;
    top: auto;
    border-left: none;
    border: 1px solid var(--hireko-border);
    border-radius: 8px;
    padding: 1.2rem;
    background: #F8FAFC;
  }

  .workflow-steps {
    grid-template-columns: 1fr 1fr;
  }

  .related-grid {
    grid-template-columns: 1fr;
  }

  .hero-dashboard .visual-body {
    grid-template-columns: 1fr;
  }

  .hireko-final-cta-inner {
    flex-direction: column;
    align-items: flex-start;
  }
}

@media (max-width: 640px) {
  .hireko-nav-actions {
    gap: 0;
  }

  .hireko-hero-inner {
    padding: 3rem 1rem;
  }

  .hireko-hero h1 {
    font-size: 2.2rem;
  }

  .hireko-layout {
    padding: 2.5rem 1rem;
  }

  .hireko-checklist ul,
  .workflow-steps,
  .related-grid,
  .hireko-resource {
    grid-template-columns: 1fr;
  }

  .hireko-login {
    display: none;
  }
}
"""

    if template_name == "Magazine":
        return """
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;800&family=Lora:ital,wght@0,400;0,600;1,400&family=Inter:wght@400;500;600;700&display=swap');

:root {
  --bg-primary: #faf9f6;
  --bg-card: #ffffff;
  --accent: #991b1b;
  --accent-light: #fdf2f2;
  --text-main: #1c1917;
  --text-muted: #78716c;
  --border: #e7e5e4;
  --font-heading: 'Playfair Display', Georgia, serif;
  --font-body: 'Lora', Georgia, serif;
  --font-sans: 'Inter', sans-serif;
}

body {
  background-color: var(--bg-primary);
  color: var(--text-main);
  font-family: var(--font-body);
  font-size: 17px;
  line-height: 1.7;
}

.category-tag {
  font-family: var(--font-sans);
  color: var(--accent);
}

.hero-banner h1 {
  font-family: var(--font-heading);
  font-size: 3rem;
  color: #0c0a09;
}

.article-container {
  background: var(--bg-card);
  border: 1px solid var(--border);
}

h2 {
  font-family: var(--font-heading);
  font-size: 30px;
}

h3 {
  font-family: var(--font-heading);
  font-size: 21px;
}

.toc-box h3 {
  font-family: var(--font-sans);
}
""" + common_css

    elif template_name == "Full-Bleed Banner":
        return """
:root {
  --bg-primary: #f1f5f9;
  --bg-card: #ffffff;
  --accent: #0284c7;
  --accent-light: #f0f9ff;
  --text-main: #0f172a;
  --text-muted: #64748b;
  --border: #e2e8f0;
}

body {
  background-color: var(--bg-primary);
}

.full-bleed-hero {
  position: relative;
  background: #0f172a;
  color: #ffffff;
  padding: 5rem 2rem 7rem 2rem;
  text-align: center;
}

.full-bleed-hero img.bg-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  opacity: 0.3;
}

.hero-content {
  position: relative;
  z-index: 2;
  max-width: 860px;
  margin: 0 auto;
}

.category-badge {
  background: var(--accent);
  color: #ffffff;
  font-size: 0.8rem;
  font-weight: 700;
  padding: 0.35rem 0.8rem;
  border-radius: 4px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.article-card-floating {
  max-width: 840px;
  margin: -4rem auto 4rem auto;
  position: relative;
  z-index: 10;
  background: var(--bg-card);
  padding: 3rem;
  border-radius: 16px;
  box-shadow: 0 20px 50px rgba(0,0,0,0.1);
  border: 1px solid var(--border);
}
""" + common_css

    elif template_name == "Sidebar Layout":
        return """
:root {
  --bg-primary: #f4f7fb;
  --bg-card: #ffffff;
  --accent: #2563eb;
  --accent-strong: #f97316;
  --accent-light: #eff6ff;
  --text-main: #0f172a;
  --text-muted: #64748b;
  --border: #e2e8f0;
}

body {
  background:
    linear-gradient(180deg, rgba(37, 99, 235, 0.07) 0, rgba(244, 247, 251, 0) 420px),
    var(--bg-primary);
}

.top-action-bar {
  max-width: 1160px;
}

.hero-banner {
  max-width: 1220px;
  margin-top: 2rem;
  padding-top: 1.4rem;
  border-top: 5px solid;
  border-image: linear-gradient(90deg, var(--accent-strong), #ec4899, var(--accent)) 1;
}

.hero-banner h1 {
  max-width: 900px;
  font-size: 3.15rem;
}

.hero-dek {
  max-width: 840px;
}

.hero-img-card {
  max-width: 1060px;
  border-radius: 12px;
}

.hero-img-card img {
  height: 440px;
}

.layout-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 280px;
  gap: 1.75rem;
  max-width: 1220px;
  margin: 0 auto 4rem auto;
  padding: 0 1.5rem;
  align-items: start;
}

.main-content-card {
  background: var(--bg-card);
  padding: 3.25rem;
  border-radius: 14px;
  box-shadow: 0 18px 55px rgba(15, 23, 42, 0.08);
  border: 1px solid var(--border);
  border-top: 4px solid var(--accent-strong);
}

.main-content-card p {
  font-size: 17.5px;
}

.main-content-card .toc-box,
.main-content-card .exec-summary-box {
  margin-bottom: 2.25rem;
}

.sidebar-sticky {
  position: sticky;
  top: 1.25rem;
  height: fit-content;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.sidebar-card {
  background: var(--bg-card);
  padding: 1.25rem;
  border-radius: 14px;
  border: 1px solid var(--border);
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.06);
}

.sidebar-card .citation-list {
  margin: 0;
  padding: 0;
  border: 0;
  background: transparent;
}

.sidebar-card .citation-list h4 {
  font-size: 1rem;
}

.sidebar-card .citation-list ol {
  padding-left: 1.05rem;
}

.sidebar-card .citation-list li {
  font-size: 0.86rem;
}

.sidebar-card .key-numbers-strip {
  grid-template-columns: 1fr;
  gap: 0.8rem;
  margin-bottom: 0;
}

.sidebar-card .number-card {
  padding: 1rem;
  border-radius: 10px;
}

.sidebar-card .number-card .num-val {
  font-size: 1.85rem;
}

.toc-box {
  border-radius: 10px;
}

.exec-summary-box {
  border-radius: 10px;
}

h2 {
  border-left: 0;
  padding-left: 0;
  position: relative;
}

h2::before {
  content: "";
  display: block;
  width: 44px;
  height: 4px;
  background: var(--accent-strong);
  border-radius: 99px;
  margin-bottom: 0.8rem;
}

.section-image-card {
  max-width: 760px;
  border-radius: 10px;
}

.section-image-card img {
  height: 360px;
}

@media (max-width: 900px) {
  .layout-grid {
    grid-template-columns: 1fr;
  }

  .hero-banner h1 {
    font-size: 2.35rem;
  }

  .hero-img-card img,
  .section-image-card img {
    height: 260px;
  }

  .main-content-card {
    padding: 1.6rem;
  }

  .main-content-card p {
    font-size: 16.5px;
  }
}
""" + common_css

    elif template_name == "Dark Mode":
        return """
:root {
  --bg-primary: #090d16;
  --bg-card: rgba(15, 23, 42, 0.75);
  --accent: #38bdf8;
  --accent-light: rgba(56, 189, 248, 0.1);
  --accent-gradient: linear-gradient(135deg, #38bdf8 0%, #818cf8 100%);
  --text-main: #f8fafc;
  --text-muted: #94a3b8;
  --border: #1e293b;
}

body {
  background-color: var(--bg-primary);
  color: var(--text-main);
}

.hero-banner {
  background: radial-gradient(circle at top right, #1e1b4b, #090d16);
}

.hero-banner h1 {
  background: var(--accent-gradient);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.article-container {
  background: var(--bg-card);
  backdrop-filter: blur(12px);
  border: 1px solid var(--border);
}
""" + common_css

    else:
        return common_css


def markdown_to_html_with_images_editorial(md_text: str, section_images: List[Dict[str, str]]) -> str:
    """Converts Markdown text to clean HTML and inserts section editorial visuals."""
    lines = md_text.splitlines()
    html_lines = []
    in_list = False
    in_code = False
    h2_count = 0

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            continue

        if stripped.startswith("```"):
            if in_code:
                html_lines.append("</code></pre>")
                in_code = False
            else:
                lang = stripped[3:].strip() or "text"
                html_lines.append(f'<pre><code class="language-{html.escape(lang)}">')
                in_code = True
            continue

        if in_code:
            html_lines.append(html.escape(line))
            continue

        if stripped.startswith("## "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            heading_raw = stripped[3:].strip()
            heading_text = html.escape(heading_raw)
            anchor = re.sub(r"[^\w\-]", "", heading_raw.lower().replace(" ", "-"))
            html_lines.append(f'<h2 id="{anchor}">{heading_text}</h2>')
            
            # Embed a fresh editorial visual under H2 as a compact thumbnail card.
            if not any(k in heading_text.lower() for k in ["faq", "frequently", "sources", "takeaway", "means"]) and h2_count < len(section_images):
                img_data = section_images[h2_count]
                fallback_url = img_data.get('fallback_url', 'https://images.unsplash.com/photo-1551836022-d5d88e9218df?auto=format&fit=crop&w=1280&q=80')
                html_lines.append(f'''<figure class="section-image-card">
  <div class="thumbnail-badge">
    <span>FIGURE {h2_count + 1} / EDITORIAL VISUAL</span>
    <span class="zoom-hint">Click to expand</span>
  </div>
  <img src="{img_data['url']}" onerror="this.onerror=null;this.src='{fallback_url}';" alt="{heading_text}" loading="lazy" decoding="async" referrerpolicy="no-referrer" onclick="openLightbox(this.src, '{heading_text}')" />
  <figcaption><strong>Figure {h2_count + 1}.</strong> {html.escape(img_data['title'])}.<br/><em>Source: {html.escape(img_data['source_org'])}.</em></figcaption>
</figure>''')
                h2_count += 1

        elif stripped.startswith("### "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            heading_raw = stripped[4:].strip()
            heading_text = html.escape(heading_raw)
            anchor = re.sub(r"[^\w\-]", "", heading_raw.lower().replace(" ", "-"))
            html_lines.append(f'<h3 id="{anchor}">{heading_text}</h3>')
        elif stripped.startswith("- ") or stripped.startswith("* "):
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            item_text = format_inline_markdown(stripped[2:].strip())
            html_lines.append(f"<li>{item_text}</li>")
        elif stripped.startswith("> "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            quote_text = format_inline_markdown(stripped[2:].strip())
            html_lines.append(f"<blockquote>{quote_text}</blockquote>")
        else:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            p_text = format_inline_markdown(stripped)
            html_lines.append(f"<p>{p_text}</p>")

    if in_list:
        html_lines.append("</ul>")

    return "\n".join(html_lines)


async def render_full_html_package_async(
    title: str,
    subtitle: str,
    markdown_content: str,
    template_name: str,
    sources: List[Dict[str, Any]],
    keywords: Dict[str, Any],
    audience: str = "HR leaders, recruiters, job seekers",
    goal: str = "Publication-ready analysis"
) -> Dict[str, str]:
    """Renders complete index.html and styles.css following the exact 9.5/10 requested layout flow."""
    template_name = resolve_template_name(template_name, title)
    css_content = get_template_style(template_name)
    
    # 1. Parse H2 Titles for Section Images
    raw_h2_titles = re.findall(r'^##\s+(.+)$', markdown_content, re.MULTILINE)
    imageable_titles = [
        t.strip()
        for t in raw_h2_titles
        if not re.search(r"faq|frequently|sources|further reading|references|takeaway|means", t, re.IGNORECASE)
    ]
    sections_info = [{"title": t, "summary": f"{title} {t}"} for t in imageable_titles]

    if template_name in ("Hireko Editorial", "Hireko Vercel Editorial"):
        hero_data = {}
        section_images = []
    else:
        images_bundle = await generate_article_images_async(title, sections_info)
        hero_data = images_bundle["hero"]
        section_images = images_bundle["sections"]

    # 2. Robust Extraction of Executive Summary
    summary_match = re.search(r'(?:>\s*)?\*\*(?:Executive Summary|Summary):\*\*\s*(.*?)(?=\n>|\n#|\n\*\*Key|\n##|\n$)', markdown_content, re.DOTALL | re.IGNORECASE)
    exec_summary_text = summary_match.group(1).strip() if summary_match else f"An authoritative analysis of {title.lower()} developments and strategic trends in 2026."

    # 3. Robust extraction of the actual Key Takeaways block.
    takeaways_items = extract_key_takeaways(markdown_content)

    # Clean markdown content to prevent duplicate titles, executive summary, takeaways, or bottom sources in article body
    clean_markdown = markdown_content.strip()
    
    # Strip top H1 title header if present (e.g. # Topic Title)
    clean_markdown = re.sub(r'^#\s+.*?\n+', '', clean_markdown, flags=re.MULTILINE)

    # Strip everything before the first H2 section heading from clean_markdown to avoid duplicate top blocks
    first_h2_pos = clean_markdown.find("## ")
    if first_h2_pos != -1:
        clean_markdown = clean_markdown[first_h2_pos:]

    # Strip "## Sources & Further Reading" block from clean_markdown to prevent raw text duplication at bottom
    sources_h2_pos = re.search(r'\n##\s+(?:Sources|References|Further Reading)', clean_markdown, re.IGNORECASE)
    if sources_h2_pos:
        clean_markdown = clean_markdown[:sources_h2_pos.start()]

    body_html = markdown_to_html_with_images_editorial(clean_markdown, section_images)

    # 4. Build Table of Contents
    headings = re.findall(r'<h2 id="([^"]+)">(.*?)</h2>', body_html)
    toc_items = ""
    for idx, h in enumerate(headings, 1):
        num_str = f"{idx:02d}"
        clean_title = re.sub("<.*?>", "", h[1]).strip()
        toc_items += f'<li><span class="num">{num_str}</span><a href="#{h[0]}">{clean_title}</a></li>'
    toc_html = f'<nav class="toc-box"><h3>Contents</h3><ul class="toc-list">{toc_items}</ul></nav>' if toc_items else ''

    # 5. Build Sources
    source_items = ""
    default_sources = [
        {"title": "U.S. Bureau of Labor Statistics (BLS) - Employment & Economic Reports 2026", "url": "https://www.bls.gov"},
        {"title": "Challenger, Gray & Christmas - Monthly Job Cuts Report", "url": "https://www.challengergray.com"},
        {"title": "LinkedIn Workforce & Hiring Intelligence Quarterly", "url": "https://www.linkedin.com"}
    ]
    all_sources = sources if sources and len(sources) > 0 else default_sources

    for idx, s in enumerate(all_sources, 1):
        url = s.get("url", "#")
        title_s = s.get("title", f"Verified Evidence Reference {idx}")
        source_items += f'<li><strong>[Source {idx}]</strong> <a href="{html.escape(url)}" target="_blank" rel="noopener">{html.escape(title_s)}</a></li>'
    sources_html = f'<section class="citation-list"><h4>Sources &amp; Further Reading</h4><ol>{source_items}</ol></section>'

    hireko_assets = {}
    hireko_icon_svg = """<svg class="hireko-icon" width="32" height="32" viewBox="0 0 48 48" fill="none" aria-hidden="true" style="width:32px;height:32px;display:inline-block;flex-shrink:0;"><path d="M12 9v9c0 8-4 13-11 16" stroke="currentColor" stroke-width="4" stroke-linecap="round"/><path d="M24 5v15c0 9-5 15-14 20" stroke="currentColor" stroke-width="4" stroke-linecap="round"/><path d="M36 9v9c0 8 4 13 11 16" stroke="currentColor" stroke-width="4" stroke-linecap="round"/><path d="M9 42c7-5 14-5 22 0" stroke="currentColor" stroke-width="4" stroke-linecap="round"/></svg>"""

    # 6. Build factual article snapshot cards.
    section_count = len([t for t in raw_h2_titles if not re.search(r"faq|sources|further reading|references", t, re.IGNORECASE)])
    read_minutes = estimate_reading_minutes(markdown_content)
    key_numbers_html = build_article_snapshot_html(markdown_content, len(all_sources), section_count)

    # 7. Render 2-Column Workers & Employers Cards Block
    means_grid_html = """
    <div class="what-means-grid">
      <div class="means-card">
        <h4>For Employers &amp; Hiring Managers</h4>
        <ul>
          <li><strong>Audit Recruitment Tools:</strong> Regularly verify candidate screening algorithms to prevent bias.</li>
          <li><strong>Invest in Recruiter Training:</strong> Equip talent acquisition teams with data literacy skills.</li>
          <li><strong>Maintain Human Sign-off:</strong> Require human review for all final hiring decisions.</li>
        </ul>
      </div>
      <div class="means-card">
        <h4>For Job Seekers &amp; Professionals</h4>
        <ul>
          <li><strong>Highlight Practical Skills:</strong> Emphasize concrete project metrics and certifications.</li>
          <li><strong>Prepare for Video Assessments:</strong> Practice structured skill evaluation formats.</li>
          <li><strong>Leverage AI Responsibly:</strong> Keep applications authentic while refining resume formatting.</li>
        </ul>
      </div>
    </div>
    """

    # Inject 2-column cards only when the draft did not already include them.
    if template_name != "Casual Blog" and "for-employers" not in body_html.lower() and "for-job-seekers" not in body_html.lower():
        body_html = re.sub(
            r'(<h2 id="03-[^"]+">.*?</h2>)',
            r'\1' + means_grid_html,
            body_html
        )

    # 8. Render "What to watch next" timeline under Section 04 H2 block
    watch_timeline_html = """
    <div style="background: #f8fafc; border: 1px solid var(--border); border-radius: 12px; padding: 1.5rem; margin: 2rem 0;">
      <h3 style="margin-top: 0; color: var(--accent); font-size: 1.15rem; text-transform: uppercase; letter-spacing: 0.05em;">What to Watch in 2026-2027</h3>
      <ol style="margin: 0; padding-left: 1.25rem;">
        <li style="margin-bottom: 0.75rem;"><strong>AI task exposure shifts</strong> vs. occupational employment growth rates.</li>
        <li style="margin-bottom: 0.75rem;"><strong>Emerging compliance frameworks</strong> regarding automated decision-making transparency.</li>
        <li style="margin-bottom: 0.75rem;"><strong>Skills-based matching adoption</strong> over traditional credential requirements.</li>
      </ol>
    </div>
    """
    if template_name != "Casual Blog":
        body_html = re.sub(
            r'(<h2 id="04-[^"]+">.*?</h2>)',
            r'\1' + watch_timeline_html,
            body_html
        )

    lightbox_html = """
  <div id="imageLightbox" class="lightbox-overlay" onclick="closeLightbox()">
    <span class="lightbox-close">&times;</span>
    <img id="lightboxImg" src="" alt="Expanded View" />
    <div id="lightboxCaption" class="lightbox-caption"></div>
  </div>
"""

    # Build HTML Document according to exact selected Template Structural Rules
    if template_name in ("Hireko Editorial", "Hireko Vercel Editorial"):
        headline_escaped = html.escape(title)
        for kw in ("AI-Powered", "AI-driven", "AI-assisted", "AI Interviews", "AI Hiring", "AI"):
            if kw in headline_escaped:
                headline_escaped = headline_escaped.replace(kw, f'<span class="gradient-text">{kw}</span>', 1)
                break

        html_document = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{html.escape(title)} | Hireko.ai Blog</title>
  <meta name="description" content="{html.escape(subtitle)}">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,100..1000;1,9..40,100..1000&family=Poppins:ital,wght@0,400;0,500;0,600;0,700;1,400;1,600&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="styles.css">
  <script>
    function openLightbox(src, caption) {{
      const lb = document.getElementById('imageLightbox');
      if (!lb) return;
      document.getElementById('lightboxImg').src = src;
      document.getElementById('lightboxCaption').innerText = caption;
      lb.style.display = 'flex';
    }}
    function closeLightbox() {{
      const lb = document.getElementById('imageLightbox');
      if (lb) lb.style.display = 'none';
    }}
  </script>
</head>
<body>
  <nav class="hireko-nav" aria-label="Primary navigation">
    <div class="hireko-nav-inner">
      <a class="hireko-logo" href="/" aria-label="Hireko.ai home">
        <svg class="hireko-logo-lockup" width="160" height="33" viewBox="0 0 302 62" role="img" aria-label="Hireko.ai" style="width:160px;height:auto;max-width:100%;display:block;">
          <defs>
            <linearGradient id="hirekoLogoGradient" x1="0" x2="1" y1="0" y2="1"><stop offset="0" stop-color="#00A1D4"/><stop offset="1" stop-color="#6FCA9F"/></linearGradient>
          </defs>
          <g fill="none" stroke="url(#hirekoLogoGradient)" stroke-width="5.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M17 8v16c0 13-6 20-16 25"/>
            <path d="M31 3v23c0 16-9 25-25 33"/>
            <path d="M45 8v16c0 13 6 20 16 25"/>
            <path d="M4 55c10-7 20-7 30 0"/>
          </g>
          <text x="72" y="44" fill="#0F172A" font-family="Poppins, Arial, sans-serif" font-size="39" font-weight="600" letter-spacing="-1">H!reko.</text>
          <text x="231" y="44" fill="url(#hirekoLogoGradient)" font-family="Poppins, Arial, sans-serif" font-size="39" font-weight="600" letter-spacing="-1">ai</text>
        </svg>
      </a>
      <div class="hireko-nav-links" aria-label="Main links">
        <a href="#">Product</a>
        <a href="#">Solutions</a>
        <a href="#">Resources</a>
        <a href="#">Pricing</a>
        <a href="#">About</a>
      </div>
      <div class="hireko-nav-actions">
        <a class="hireko-login" href="#">Login</a>
        <a class="hireko-btn" href="#">Get Started</a>
      </div>
    </div>
  </nav>

  <nav class="hireko-breadcrumb" aria-label="Breadcrumb">
    <a href="#">Home</a> &nbsp;/&nbsp; <a href="#">Blog</a> &nbsp;/&nbsp; <span class="active-category">AI Hiring</span>
  </nav>

  <header class="hireko-hero">
    <svg class="hero-bg-motif" width="280" height="280" viewBox="0 0 48 48" fill="none" aria-hidden="true" style="position:absolute;right:-30px;bottom:-40px;width:280px;height:280px;opacity:0.05;pointer-events:none;color:#6FCA9F;z-index:0;">
      <path d="M12 9v9c0 8-4 13-11 16" stroke="currentColor" stroke-width="3" stroke-linecap="round"/>
      <path d="M24 5v15c0 9-5 15-14 20" stroke="currentColor" stroke-width="3" stroke-linecap="round"/>
      <path d="M36 9v9c0 8 4 13 11 16" stroke="currentColor" stroke-width="3" stroke-linecap="round"/>
      <path d="M9 42c7-5 14-5 22 0" stroke="currentColor" stroke-width="3" stroke-linecap="round"/>
    </svg>
    <div class="hireko-hero-inner">
      <div class="hireko-hero-copy">
        <span class="hireko-category">AI Hiring</span>
        <h1>{headline_escaped}</h1>
        <p class="hireko-hero-dek">{html.escape(subtitle)}</p>
        <div class="hireko-meta">
          <span>By <strong>Hireko Research Team</strong></span>
          <span>{read_minutes} min read</span>
          <span>Sep 2026</span>
        </div>
      </div>
      <div class="hireko-dashboard-visual hero-dashboard" aria-label="Hireko.ai candidate matching dashboard illustration">
        <div class="visual-window">
          <div class="visual-topbar"><span>Hireko Match Engine</span><span class="visual-status">Candidate ready</span></div>
          <div class="visual-body">
            <div class="candidate-card">
              <div class="candidate-avatar" aria-hidden="true">AD</div>
              <div class="candidate-details"><span>Alex Davies</span><small>Senior Product Designer</small></div>
              <div class="candidate-score">92%</div>
            </div>
            <div class="visual-grid">
              <div class="visual-panel">
                <strong>Role-fit signals</strong>
                <div class="signal-row"><span>Core skills</span><em>92</em><div class="signal-bar"><span style="width: 92%;"></span></div></div>
                <div class="signal-row"><span>Experience</span><em>84</em><div class="signal-bar"><span style="width: 84%;"></span></div></div>
                <div class="signal-row"><span>Team fit</span><em>78</em><div class="signal-bar"><span style="width: 78%;"></span></div></div>
              </div>
              <div class="visual-panel">
                <strong>Interview readiness</strong>
                <div class="interview-flow"><span>Profile</span><span>Interview</span><span>Review</span></div>
              </div>
            </div>
            <div class="match-summary">
              <small>Candidate match confidence</small>
              <strong>82%</strong>
              <div class="hireko-score-bar"><span></span></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </header>

  <main class="hireko-layout">
    <aside class="hireko-toc">
      <h3>Contents</h3>
      <ul>{toc_items}</ul>
    </aside>

    <article class="hireko-article">
      <section class="key-takeaway-card">
        <div class="key-takeaway-header">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#00A1D4" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="width:20px;height:20px;flex-shrink:0;"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon></svg>
          <span>KEY TAKEAWAY</span>
        </div>
        <p>{html.escape(takeaways_items[0])}</p>
      </section>

      <div class="hireko-insight">
        <svg class="insight-bg-motif" width="180" height="180" viewBox="0 0 48 48" fill="none" aria-hidden="true" style="position:absolute;right:-20px;bottom:-30px;width:180px;height:180px;opacity:0.04;pointer-events:none;color:#6FCA9F;z-index:0;">
          <path d="M12 9v9c0 8-4 13-11 16" stroke="currentColor" stroke-width="3" stroke-linecap="round"/>
          <path d="M24 5v15c0 9-5 15-14 20" stroke="currentColor" stroke-width="3" stroke-linecap="round"/>
          <path d="M36 9v9c0 8 4 13 11 16" stroke="currentColor" stroke-width="3" stroke-linecap="round"/>
          <path d="M9 42c7-5 14-5 22 0" stroke="currentColor" stroke-width="3" stroke-linecap="round"/>
        </svg>
        <div class="hireko-insight-header">
          {hireko_icon_svg}
          <h3>Hireko insight</h3>
        </div>
        <p>The most effective AI recruiting platforms do not remove recruiter judgment. They give teams cleaner evidence earlier, so humans can spend more time on calibration, candidate care, and final decisions.</p>
      </div>

      <section class="hireko-workflow" aria-labelledby="workflow-title">
        <h3 id="workflow-title">Recruitment workflow diagram</h3>
        <div class="workflow-steps">
          <div class="workflow-step"><span>01</span><strong>Resume intake</strong><p>Parse candidate data and normalize experience against role requirements.</p></div>
          <div class="workflow-step"><span>02</span><strong>Job context</strong><p>Map must-have skills, seniority, and hiring manager priorities.</p></div>
          <div class="workflow-step"><span>03</span><strong>AI interview</strong><p>Validate answers through a conversational video interface.</p></div>
          <div class="workflow-step"><span>04</span><strong>Objective score</strong><p>Rank candidates with explainable signals for the hiring team.</p></div>
        </div>
      </section>

      <section class="content-body">
        {body_html}
      </section>

      <section class="hireko-checklist">
        <h3>Hiring checklist</h3>
        <ul>
          <li>Define scorecards before screening begins.</li>
          <li>Separate must-have skills from coachable strengths.</li>
          <li>Keep humans responsible for final hiring decisions.</li>
          <li>Audit automated scoring for fairness and consistency.</li>
          <li>Use candidate-friendly explanations and timelines.</li>
          <li>Connect insights back into the ATS or hiring workflow.</li>
        </ul>
      </section>

      <table class="hireko-compare">
        <thead><tr><th>Hiring stage</th><th>Manual workflow</th><th>Hireko.ai workflow</th></tr></thead>
        <tbody>
          <tr><td>Resume review</td><td>Slow keyword scanning and manual sorting.</td><td>Automated resume processing and role-fit signals.</td></tr>
          <tr><td>Candidate screening</td><td>Repeated phone screens and uneven notes.</td><td>Structured AI conversations grounded in job context.</td></tr>
          <tr><td>Decision support</td><td>Subjective feedback scattered across tools.</td><td>Objective scoring, summaries, and hiring workflow data.</td></tr>
        </tbody>
      </table>

      <section class="hireko-mid-cta">
        <h2>Make hiring more intelligent</h2>
        <p>Hireko.ai helps businesses find, evaluate, and hire the right talent with intelligent automation.</p>
        <a class="hireko-btn" href="#">Explore Hireko.ai</a>
      </section>

      <section class="hireko-resource">
        <div class="hireko-resource-icon">PDF</div>
        <div>
          <h3>Download the hiring workflow checklist</h3>
          <p>Use this resource to align recruiters, hiring managers, scorecards, and AI-assisted screening before your next role opens.</p>
        </div>
        <a class="hireko-btn" href="#">Get the checklist</a>
      </section>

      <section class="hireko-author-card">
        <div class="author-avatar" aria-hidden="true">
          <svg width="28" height="28" viewBox="0 0 48 48" fill="none" class="author-hireko-symbol" style="width:28px;height:28px;display:block;"><path d="M12 9v9c0 8-4 13-11 16" stroke="currentColor" stroke-width="4" stroke-linecap="round"/><path d="M24 5v15c0 9-5 15-14 20" stroke="currentColor" stroke-width="4" stroke-linecap="round"/><path d="M36 9v9c0 8 4 13 11 16" stroke="currentColor" stroke-width="4" stroke-linecap="round"/><path d="M9 42c7-5 14-5 22 0" stroke="currentColor" stroke-width="4" stroke-linecap="round"/></svg>
        </div>
        <div class="author-info">
          <div class="author-header">
            <span class="author-name">Hireko Research Team</span>
            <span class="author-badge">Verified Author</span>
          </div>
          <div class="author-role">AI Talent Acquisition &amp; Workforce Intelligence</div>
          <p class="author-bio">Practical insights on AI-powered recruitment, candidate evaluation, hiring strategy, and the future of work.</p>
          <div class="author-social">
            <a href="https://hireko.ai" target="_blank" rel="noopener">hireko.ai</a>
            <a href="#" rel="noopener">LinkedIn</a>
            <a href="#" rel="noopener">Twitter</a>
          </div>
        </div>
      </section>

      {sources_html}
    </article>
  </main>

  <section class="hireko-related" aria-labelledby="related-title">
    <h2 id="related-title">Related articles</h2>
    <div class="related-grid">
      <article class="related-card">
        <div class="related-card-visual" aria-hidden="true"></div>
        <div class="related-card-body">
          <span class="tag">AI Interviews</span>
          <h3>What Is an AI Interview Platform?</h3>
          <p>A practical guide to conversational interviews, job-context validation, and objective candidate scoring.</p>
          <div class="related-card-footer">
            <span class="read-time">7 min read</span>
            <span class="related-arrow">&rarr;</span>
          </div>
        </div>
      </article>
      <article class="related-card">
        <div class="related-card-visual" aria-hidden="true"></div>
        <div class="related-card-body">
          <span class="tag">Automation</span>
          <h3>How AI Automates Enterprise Hiring Workflows</h3>
          <p>Where automation helps recruiters move faster while keeping decisions explainable and human-led.</p>
          <div class="related-card-footer">
            <span class="read-time">8 min read</span>
            <span class="related-arrow">&rarr;</span>
          </div>
        </div>
      </article>
      <article class="related-card">
        <div class="related-card-visual" aria-hidden="true"></div>
        <div class="related-card-body">
          <span class="tag">Candidate Experience</span>
          <h3>How to Create a 5-Star AI Interview Experience</h3>
          <p>Design candidate interactions that feel structured, fair, and genuinely useful for both sides.</p>
          <div class="related-card-footer">
            <span class="read-time">6 min read</span>
            <span class="related-arrow">&rarr;</span>
          </div>
        </div>
      </article>
    </div>
  </section>

  <section class="hireko-final-cta">
    <svg class="cta-bg-motif" width="240" height="240" viewBox="0 0 48 48" fill="none" aria-hidden="true" style="position:absolute;right:-20px;bottom:-30px;width:240px;height:240px;opacity:0.06;pointer-events:none;color:#6FCA9F;z-index:0;">
      <path d="M12 9v9c0 8-4 13-11 16" stroke="currentColor" stroke-width="3" stroke-linecap="round"/>
      <path d="M24 5v15c0 9-5 15-14 20" stroke="currentColor" stroke-width="3" stroke-linecap="round"/>
      <path d="M36 9v9c0 8 4 13 11 16" stroke="currentColor" stroke-width="3" stroke-linecap="round"/>
      <path d="M9 42c7-5 14-5 22 0" stroke="currentColor" stroke-width="3" stroke-linecap="round"/>
    </svg>
    <div class="hireko-final-cta-inner">
      <div>
        <h2>Build a smarter hiring process with Hireko.ai</h2>
        <p>Find, evaluate, and hire the right talent with intelligent automation.</p>
      </div>
      <a class="hireko-btn" href="#">Get Started</a>
    </div>
  </section>
</body>
</html>
"""

    elif template_name == "Casual Blog":
        html_document = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{html.escape(title)}</title>
  <meta name="description" content="{html.escape(subtitle)}">
  <link rel="stylesheet" href="styles.css">
  <script>
    function copyMarkdown() {{
      const text = document.querySelector('.content-body').innerText;
      navigator.clipboard.writeText(text);
      alert('Markdown copied to clipboard!');
    }}
    function copyText() {{
      const text = document.body.innerText;
      navigator.clipboard.writeText(text);
      alert('Article text copied to clipboard!');
    }}
    function openLightbox(src, caption) {{
      const lb = document.getElementById('imageLightbox');
      document.getElementById('lightboxImg').src = src;
      document.getElementById('lightboxCaption').innerText = caption;
      lb.style.display = 'flex';
    }}
    function closeLightbox() {{
      document.getElementById('imageLightbox').style.display = 'none';
    }}
  </script>
</head>
<body>
{lightbox_html}

  <div class="top-action-bar">
    <button class="btn-pill" onclick="copyMarkdown()">Copy Markdown</button>
    <button class="btn-pill" onclick="copyText()">Copy Text</button>
  </div>

  <header class="hero-banner">
    <span class="category-tag">Blog</span>
    <h1>{html.escape(title)}</h1>
    <p class="hero-dek">{html.escape(subtitle)}</p>
    <figure class="hero-img-card">
      <img src="{hero_data['url']}" onerror="this.onerror=null;this.src='{hero_data.get('fallback_url', 'https://images.unsplash.com/photo-1497366216548-37526070297c?auto=format&fit=crop&w=1280&q=80')}';" alt="{html.escape(title)}" />
    </figure>
  </header>

  <main class="article-container">
    <div class="publication-meta">
      <span><strong>Published:</strong> Aug 12, 2026</span>
      <span><strong>Reading Time:</strong> {read_minutes} min</span>
    </div>

    {toc_html}

    <div class="exec-summary-box">
      <h3>Quick Intro</h3>
      <p style="margin: 0;">{html.escape(exec_summary_text)}</p>
    </div>

    <div class="takeaways-container">
      <h3 style="margin-top: 0; font-size: 1.1rem; color: var(--accent);">A few things to know</h3>
      {" ".join([f'<div class="takeaway-bullet-card">{html.escape(t)}</div>' for t in takeaways_items])}
    </div>

    <article class="content-body">
      {body_html}
    </article>
    {sources_html}
  </main>

  <footer class="footer-bar">
    <p>&copy; 2026 AI Publication Journal. All rights reserved.</p>
    <div class="footer-links">
      <a href="#">About</a> &bull; <a href="#">Contact</a> &bull; <a href="#">Privacy</a> &bull; <a href="#">Sources</a>
    </div>
  </footer>

</body>
</html>
"""

    elif template_name == "Full-Bleed Banner":
        html_document = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{html.escape(title)}</title>
  <meta name="description" content="{html.escape(subtitle)}">
  <link rel="stylesheet" href="styles.css">
  <script>
    function copyMarkdown() {{
      const text = document.querySelector('.content-body').innerText;
      navigator.clipboard.writeText(text);
      alert('Markdown copied to clipboard!');
    }}
    function copyText() {{
      const text = document.body.innerText;
      navigator.clipboard.writeText(text);
      alert('Article text copied to clipboard!');
    }}
    function openLightbox(src, caption) {{
      const lb = document.getElementById('imageLightbox');
      document.getElementById('lightboxImg').src = src;
      document.getElementById('lightboxCaption').innerText = caption;
      lb.style.display = 'flex';
    }}
    function closeLightbox() {{
      document.getElementById('imageLightbox').style.display = 'none';
    }}
  </script>
</head>
<body>
{lightbox_html}

  <header class="full-bleed-hero">
    <img class="bg-overlay" src="{hero_data['url']}" onerror="this.onerror=null;this.src='{hero_data.get('fallback_url', 'https://images.unsplash.com/photo-1497366216548-37526070297c?auto=format&fit=crop&w=1280&q=80')}';" alt="{html.escape(title)}" />
    <div class="hero-content">
      <span class="category-badge">Workforce &amp; Policy Feature</span>
      <h1 style="font-size: 3.2rem; font-weight: 800; line-height: 1.15; margin: 1rem 0;">{html.escape(title)}</h1>
      <p style="font-size: 1.3rem; opacity: 0.9; max-width: 720px; margin: 0 auto 1.5rem auto;">{html.escape(subtitle)}</p>
      <div style="font-size: 0.95rem; opacity: 0.8; display: flex; justify-content: center; gap: 1.5rem;">
        <span>Aug 12, 2026</span> &bull; <span>{read_minutes} min read</span> &bull; <span>Fact-Checked</span>
      </div>
    </div>
  </header>

  <div class="top-action-bar" style="margin-top: 1rem;">
    <button class="btn-pill" onclick="copyMarkdown()">Copy Markdown</button>
    <button class="btn-pill" onclick="copyText()">Copy Text</button>
  </div>

  <main class="article-container article-card-floating">
    {key_numbers_html}
    {toc_html}
    <div class="exec-summary-box">
      <h3>Executive Summary</h3>
      <p style="margin: 0; font-size: 17px;">{html.escape(exec_summary_text)}</p>
    </div>
    <div class="takeaways-container">
      <h3 style="margin-top: 0; font-size: 1.15rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--accent);">Key Takeaways</h3>
      {" ".join([f'<div class="takeaway-bullet-card">{html.escape(t)}</div>' for t in takeaways_items])}
    </div>
    <article class="content-body">
      {body_html}
    </article>
    {sources_html}
  </main>

  <footer class="footer-bar">
    <p>&copy; 2026 AI Publication Journal. All rights reserved.</p>
    <div class="footer-links">
      <a href="#">About</a> &bull; <a href="#">Contact</a> &bull; <a href="#">Privacy</a> &bull; <a href="#">Sources</a>
    </div>
  </footer>

</body>
</html>
"""

    elif template_name == "Sidebar Layout":
        html_document = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{html.escape(title)}</title>
  <meta name="description" content="{html.escape(subtitle)}">
  <link rel="stylesheet" href="styles.css">
  <script>
    function copyMarkdown() {{
      const text = document.querySelector('.content-body').innerText;
      navigator.clipboard.writeText(text);
      alert('Markdown copied to clipboard!');
    }}
    function copyText() {{
      const text = document.body.innerText;
      navigator.clipboard.writeText(text);
      alert('Article text copied to clipboard!');
    }}
    function openLightbox(src, caption) {{
      const lb = document.getElementById('imageLightbox');
      document.getElementById('lightboxImg').src = src;
      document.getElementById('lightboxCaption').innerText = caption;
      lb.style.display = 'flex';
    }}
    function closeLightbox() {{
      document.getElementById('imageLightbox').style.display = 'none';
    }}
  </script>
</head>
<body>
{lightbox_html}

  <div class="top-action-bar">
    <button class="btn-pill" onclick="copyMarkdown()">Copy Markdown</button>
    <button class="btn-pill" onclick="copyText()">Copy Text</button>
  </div>

  <header class="hero-banner">
    <span class="category-tag">Workforce &amp; Economy</span>
    <h1>{html.escape(title)}</h1>
    <p class="hero-dek">{html.escape(subtitle)}</p>
    <figure class="hero-img-card">
      <img src="{hero_data['url']}" onerror="this.onerror=null;this.src='{hero_data.get('fallback_url', 'https://images.unsplash.com/photo-1497366216548-37526070297c?auto=format&fit=crop&w=1280&q=80')}';" alt="{html.escape(title)}" />
    </figure>
  </header>

  <div class="layout-grid">
    <main class="main-content-card">
      <div class="exec-summary-box">
        <h3>Executive Summary</h3>
        <p style="margin: 0; font-size: 17px;">{html.escape(exec_summary_text)}</p>
      </div>

      {toc_html}

      <article class="content-body">
        {body_html}
      </article>
    </main>

    <aside class="sidebar-sticky">
      <div class="sidebar-card">
        <h4 style="margin-top:0; color:var(--accent); font-size:1.05rem; text-transform:uppercase; letter-spacing:0.05em;">Article Snapshot</h4>
        {key_numbers_html}
      </div>

      <div class="sidebar-card">
        <h4 style="margin-top:0; color:var(--accent); font-size:1.05rem; text-transform:uppercase; letter-spacing:0.05em;">Key Takeaways</h4>
        {" ".join([f'<div class="takeaway-bullet-card" style="font-size:0.92rem; padding:0.85rem;">{html.escape(t)}</div>' for t in takeaways_items])}
      </div>

      <div class="sidebar-card">
        <h4 style="margin-top:0; color:var(--text-main); font-size:1rem;">Article Info</h4>
        <ul style="padding-left:1.1rem; margin:0; font-size:0.88rem; color:var(--text-muted);">
          <li><strong>Published:</strong> Aug 12, 2026</li>
          <li><strong>Reading Time:</strong> {read_minutes} min</li>
          <li><strong>Status:</strong> Fact-Checked</li>
        </ul>
      </div>

      <div class="sidebar-card">
        {sources_html}
      </div>
    </aside>
  </div>

  <footer class="footer-bar">
    <p>&copy; 2026 AI Publication Journal. All rights reserved.</p>
    <div class="footer-links">
      <a href="#">About</a> &bull; <a href="#">Contact</a> &bull; <a href="#">Privacy</a> &bull; <a href="#">Sources</a>
    </div>
  </footer>

</body>
</html>
"""

    else:
        # Classic, Magazine, Dark Mode Layout
        html_document = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{html.escape(title)}</title>
  <meta name="description" content="{html.escape(subtitle)}">
  <link rel="stylesheet" href="styles.css">
  <script>
    function copyMarkdown() {{
      const text = document.querySelector('.content-body').innerText;
      navigator.clipboard.writeText(text);
      alert('Markdown copied to clipboard!');
    }}
    function copyText() {{
      const text = document.body.innerText;
      navigator.clipboard.writeText(text);
      alert('Article text copied to clipboard!');
    }}
    function openLightbox(src, caption) {{
      const lb = document.getElementById('imageLightbox');
      document.getElementById('lightboxImg').src = src;
      document.getElementById('lightboxCaption').innerText = caption;
      lb.style.display = 'flex';
    }}
    function closeLightbox() {{
      document.getElementById('imageLightbox').style.display = 'none';
    }}
  </script>
</head>
<body>
{lightbox_html}

  <div class="top-action-bar">
    <button class="btn-pill" onclick="copyMarkdown()">Copy Markdown</button>
    <button class="btn-pill" onclick="copyText()">Copy Text</button>
  </div>

  <header class="hero-banner">
    <span class="category-tag">Workforce &amp; Economy</span>
    <h1>{html.escape(title)}</h1>
    <p class="hero-dek">How hiring activity, sector-level shifts, and key economic drivers are reshaping the US labor market in 2026.</p>
    
    <figure class="hero-img-card">
      <img src="{hero_data['url']}" onerror="this.onerror=null;this.src='{hero_data.get('fallback_url', 'https://images.unsplash.com/photo-1497366216548-37526070297c?auto=format&fit=crop&w=1280&q=80')}';" alt="{html.escape(title)}" />
    </figure>
  </header>

  <main class="article-container">
    <div class="publication-meta">
      <span><strong>Published:</strong> Aug 12, 2026</span>
      <span><strong>Updated:</strong> Aug 12, 2026</span>
      <span><strong>Reading Time:</strong> {read_minutes} min</span>
      <span><strong>Status:</strong> Fact-Checked &amp; Verified</span>
    </div>

    {key_numbers_html}

    {toc_html}

    <div class="exec-summary-box">
      <h3>Executive Summary</h3>
      <p style="margin: 0; font-size: 17px;">{html.escape(exec_summary_text)}</p>
    </div>

    <div class="takeaways-container">
      <h3 style="margin-top: 0; font-size: 1.15rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--accent);">Key Takeaways</h3>
      {" ".join([f'<div class="takeaway-bullet-card">{html.escape(t)}</div>' for t in takeaways_items])}
    </div>

    <article class="content-body">
      {body_html}
    </article>

    {sources_html}
  </main>

  <footer class="footer-bar">
    <p>&copy; 2026 AI Publication Journal. All rights reserved.</p>
    <div class="footer-links">
      <a href="#">About</a> &bull; <a href="#">Contact</a> &bull; <a href="#">Privacy</a> &bull; <a href="#">Sources</a>
    </div>
  </footer>

</body>
</html>
"""

    # Inline CSS into the HTML so it works as a standalone file (Railway API, blob URLs)
    inlined_html = html_document.replace(
        '<link rel="stylesheet" href="styles.css">',
        f'<style>\n{css_content}\n</style>'
    )

    return {
        "index.html": inlined_html,
        "styles.css": css_content,
        "hero.svg": "",
        "assets": hireko_assets if template_name in ("Hireko Editorial", "Hireko Vercel Editorial") else {}
    }


async def render_full_html_package(
    title: str,
    subtitle: str,
    markdown_content: str,
    template_name: str,
    sources: List[Dict[str, Any]],
    keywords: Dict[str, Any],
    audience: str = "HR leaders, recruiters, job seekers",
    goal: str = "Publication-ready analysis"
) -> Dict[str, str]:
    """Renders complete index.html and styles.css using 2-stage image engine."""
    return await render_full_html_package_async(
        title=title,
        subtitle=subtitle,
        markdown_content=markdown_content,
        template_name=template_name,
        sources=sources,
        keywords=keywords,
        audience=audience,
        goal=goal
    )
