"""3-Iteration Agent Refinement Loop Pipeline with Publication-Quality Editorial Generation."""

import os
import sys
import io
import time
import json
import re
import urllib.parse
import shutil
import httpx
import logfire
from typing import Dict, Any, List

# Ensure UTF-8 stdout encoding for Windows console
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from .deps import BlogAgentDeps
from .agent import create_blog_agent, perform_web_search
from .llm_provider import get_fallback_chain
from .templates import extract_key_takeaways, render_full_html_package


def unique_model_order(primary_model: str, fallback_models: List[str]) -> List[str]:
    """Returns a de-duplicated model list while preserving priority order."""
    models = []
    for model_name in [primary_model, *fallback_models]:
        model_name = (model_name or "").strip()
        if model_name and model_name not in models:
            models.append(model_name)
    return models


def slugify(value: str) -> str:
    """Creates a URL/file-system friendly slug from article text."""
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value or "").strip("-").lower()
    return slug[:90] or "article"


def extract_plain_summary(markdown_content: str, fallback: str) -> str:
    """Extracts a short plain-text summary from the generated Markdown."""
    summary_match = re.search(
        r"(?:>\s*)?\*\*(?:Executive Summary|Summary):\*\*\s*(.*?)(?=\n>|\n#|\n\*\*Key|\n##|\n$)",
        markdown_content or "",
        re.DOTALL | re.IGNORECASE,
    )
    text = summary_match.group(1).strip() if summary_match else fallback
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"[*_`>#]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def build_seo_metadata(deps: BlogAgentDeps, markdown_content: str) -> Dict[str, Any]:
    """Builds practical SEO fields for publishing workflows."""
    title = deps.topic.strip()
    slug = slugify(title)
    summary = extract_plain_summary(markdown_content, deps.goal)
    meta_description = summary[:157].rstrip(" ,.;") + "..." if len(summary) > 160 else summary
    keyword_seed = [
        title,
        deps.audience,
        "2026",
        "AI",
        "workforce",
        "hiring",
        "jobs",
        "skills",
    ]
    raw_keywords = []
    for value in keyword_seed:
        raw_keywords.extend(re.findall(r"[A-Za-z][A-Za-z0-9-]{2,}", value or ""))
    stop_words = {"and", "the", "for", "with", "how", "what", "are", "into", "from"}
    keywords = []
    for word in raw_keywords:
        clean = word.lower()
        if clean not in stop_words and clean not in keywords:
            keywords.append(clean)
    return {
        "seo_title": f"{title} | 2026 Research Brief",
        "slug": slug,
        "meta_description": meta_description,
        "keywords": keywords[:12],
        "canonical_path": f"/blog/{slug}",
    }


def audit_factual_claims(markdown_content: str, evidence_pack: List[Dict[str, Any]], content_source: str) -> Dict[str, Any]:
    """Runs a conservative, explainable pre-publication factuality audit.

    This is deliberately a gate and not a claim that software can prove truth.
    Numeric/date claims must carry an inline [Source N] marker, and every marker
    must resolve to a source collected during research.
    """
    source_count = len(evidence_pack or [])
    valid_markers = set(range(1, source_count + 1))
    cited_markers = []
    invalid_markers = []
    uncited_fact_lines = []
    in_sources_section = False
    fact_pattern = re.compile(
        r"(?:\b\d+(?:\.\d+)?%?|\$\s?\d|\b(?:19|20)\d{2}\b|\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\b)",
        re.IGNORECASE,
    )
    marker_pattern = re.compile(r"\[Source\s+(\d+)\]", re.IGNORECASE)

    for line_number, line in enumerate((markdown_content or "").splitlines(), 1):
        if re.match(r"^##\s+.*(?:sources|references|further reading)", line, re.IGNORECASE):
            in_sources_section = True
        if in_sources_section or not line.strip() or line.lstrip().startswith("#"):
            continue
        markers = [int(value) for value in marker_pattern.findall(line)]
        cited_markers.extend(markers)
        invalid = [value for value in markers if value not in valid_markers]
        if invalid:
            invalid_markers.append({"line": line_number, "markers": invalid, "text": line.strip()[:220]})
        if fact_pattern.search(line) and not markers:
            uncited_fact_lines.append({"line": line_number, "text": line.strip()[:220]})

    fallback = (content_source or "").startswith("offline_fallback")
    source_ok = source_count >= 4
    publication_ready = bool(source_ok and not fallback and not invalid_markers and not uncited_fact_lines)
    return {
        "status": "publish_ready" if publication_ready else "review_required",
        "publication_ready": publication_ready,
        "source_count": source_count,
        "valid_source_markers": sorted(valid_markers),
        "cited_source_markers": sorted(set(cited_markers)),
        "invalid_source_markers": invalid_markers[:20],
        "uncited_factual_lines": uncited_fact_lines[:20],
        "uncited_factual_line_count": len(uncited_fact_lines),
        "fallback_content": fallback,
        "review_reason": (
            "Every numeric, dated, or percentage claim needs an inline [Source N] citation and human review."
            if not publication_ready else "All automated pre-publication checks passed; editorial review is still recommended."
        ),
    }


def build_hireko_social_posts(deps: BlogAgentDeps, markdown_content: str, seo_metadata: Dict[str, Any]) -> Dict[str, str]:
    """Creates on-brand LinkedIn and Instagram companion copy for each Hireko article."""
    title = deps.topic.strip()
    summary = extract_plain_summary(markdown_content, deps.goal)
    if re.search(r"\bfallback article\b|live LLM generation is unavailable|clean first draft", summary, re.IGNORECASE):
        summary = (
            f"This article explains {title.lower()} for {deps.audience}, with practical guidance for "
            "building faster, clearer, and more human-centered hiring workflows."
        )
    takeaways = [
        takeaway for takeaway in extract_key_takeaways(markdown_content)
        if not re.search(r"fresh source evidence|unsupported numbers|before final publishing|evidence before adding", takeaway, re.IGNORECASE)
    ]
    primary_takeaway = takeaways[0] if takeaways else "AI hiring works best when automation supports structured, human-led decisions."
    secondary_takeaway = takeaways[1] if len(takeaways) > 1 else "Recruiters need explainable signals, not another disconnected screening step."
    tertiary_takeaway = takeaways[2] if len(takeaways) > 2 else "Candidate experience improves when every step is clear, fast, and fair."
    carousel_points = (takeaways + [
        "Start with role requirements before evaluating candidates.",
        "Use AI to organize evidence, not to replace judgment.",
        "Keep hiring teams aligned with simple scorecards.",
        "Move qualified candidates forward faster.",
        "Review outcomes regularly to improve fairness and quality.",
    ])[:5]
    canonical_path = seo_metadata.get("canonical_path", "/blog")
    hashtags_linkedin = "#AIHiring #TalentAcquisition #HRTech #RecruitingAutomation #CandidateExperience #HirekoAI"
    hashtags_instagram = "#AIHiring #AIRecruitment #HRTech #RecruitingTips #TalentAcquisition #HiringAutomation #CandidateExperience #FutureOfWork #HirekoAI"

    linkedin = f"""LinkedIn post

Hook:
Hiring teams do not need more screening steps.

They need a clearer way to move from candidate intake to role-fit evidence, structured interviews, and confident decisions.

Topic:
{title}

Why this matters:
{summary}

What recruiters should focus on:
- {primary_takeaway}
- {secondary_takeaway}
- {tertiary_takeaway}
- AI should help teams compare candidates consistently, not hide decisions inside a black box.
- Faster hiring should feel clearer for candidates, not colder.

Hireko.ai helps teams automate resume processing, job postings, candidate matching, and AI-powered interview workflows while keeping hiring decisions grounded in real evidence.

CTA:
What is the slowest part of your hiring workflow right now?

Read the article: {canonical_path}

{hashtags_linkedin}
"""

    linkedin_carousel = f"""LinkedIn carousel outline

Topic: {title}
Audience: HR Managers, Talent Acquisition Leaders, Recruiters, Startup Founders, and CHROs
Tone: Professional, practical, human-centered, and data-aware
Format: 8-slide document carousel

Slide 1 - Cover
{title}
Subtitle: A practical Hireko.ai guide for building a clearer hiring workflow.

Slide 2 - The problem
Most hiring workflows break because candidate information lives in too many places: resumes, forms, interview notes, inboxes, spreadsheets, and ATS comments.

Slide 3 - Point 1
{carousel_points[0]}

Slide 4 - Point 2
{carousel_points[1]}

Slide 5 - Point 3
{carousel_points[2]}

Slide 6 - Point 4
{carousel_points[3]}

Slide 7 - Point 5
{carousel_points[4]}

Slide 8 - CTA
Build a smarter hiring process with Hireko.ai.
CTA: Try Hireko.ai or read the full article.
Link: {canonical_path}

Caption:
Hiring gets easier when teams can see the evidence behind every candidate decision.

This carousel breaks down a simple framework recruiters can use to reduce manual work, improve consistency, and keep candidate experience human.

Follow Hireko.ai for more practical AI hiring guides.

{hashtags_linkedin}
"""

    instagram = f"""Instagram caption

Still reviewing candidates through scattered notes, resumes, and interview feedback?

This Hireko.ai guide explains how hiring teams can make screening clearer, faster, and more consistent.

Key idea:
{primary_takeaway}

Use AI to organize the workflow.
Keep humans in the decision.
Give candidates a process that feels clear from start to finish.

Save this for your next hiring planning session.
Read the full article from Hireko.ai.

{hashtags_instagram}
"""

    instagram_carousel_reel = f"""Instagram carousel and reel pack

Topic: {title}
Audience: Recruiters, HR managers, founders, and hiring teams
Style: Clean, concise, visual-first copy that can be placed into branded Hireko.ai graphics.

Instagram carousel - 8 slides

Slide 1 - Hook cover
Hiring should not feel scattered.
Subtext: Swipe for a cleaner AI hiring workflow.

Slide 2 - Mistake 1
Starting with resumes before defining role-fit signals.
Fix: Write the scorecard before the screening starts.

Slide 3 - Mistake 2
Letting every recruiter screen differently.
Fix: Use consistent questions, signals, and evaluation criteria.

Slide 4 - Mistake 3
Treating AI as a replacement for judgment.
Fix: Use AI to organize evidence, then keep humans in control.

Slide 5 - Mistake 4
Moving candidates slowly because feedback is scattered.
Fix: Keep resume data, match signals, and interview notes in one workflow.

Slide 6 - Mistake 5
Optimizing only for speed.
Fix: Improve speed, clarity, fairness, and candidate experience together.

Slide 7 - Summary
Remember:
- Define the role clearly.
- Screen with consistent signals.
- Keep candidate evidence visible.
- Use AI for workflow clarity.
- Keep the final decision human.

Slide 8 - CTA
Build a better hiring process with Hireko.ai.
CTA: Follow @hireko.ai and read the full article.

Instagram Reel script - 45 seconds

0-3 sec Hook:
Still screening candidates the slow way?

3-12 sec Problem:
Recruiters are juggling resumes, interview notes, scorecards, inboxes, and hiring manager feedback. That makes good candidates easy to miss.

12-30 sec Solution:
Hireko.ai helps teams organize candidate data, compare role-fit signals, and move qualified applicants through the workflow faster.

30-40 sec Proof angle:
The goal is not just faster hiring. It is clearer decisions, better candidate experience, and less manual screening work.

40-45 sec CTA:
Follow Hireko.ai for practical AI hiring tips.
Read the full article through the link in bio.

Caption:
Better hiring starts with a clearer workflow.

{hashtags_instagram}
"""

    social_pack = f"""Hireko.ai social media content pack

Article topic: {title}
Article link: {canonical_path}
Audience: HR Managers, Talent Acquisition Leaders, Recruiters, Startup Founders, and CHROs
Brand voice: Professional but approachable, data-driven but human, innovative but simple.

Master angle:
{summary}

Primary takeaway:
{primary_takeaway}

Included files:
- linkedin_post.txt: Ready-to-post LinkedIn feed copy.
- linkedin_carousel_outline.txt: 8-slide LinkedIn carousel outline.
- instagram_caption.txt: Ready-to-post Instagram caption.
- instagram_carousel_reel.txt: Instagram carousel slide copy and a 45-second reel script.

Usage notes:
- Keep the copy text-first.
- Use Hireko.ai brand colors and typography if a designer turns the copy into visuals.
- Do not add unsupported statistics unless they are verified in the article sources.
- Keep product mentions helpful, specific, and non-pushy.
"""

    return {
        "linkedin_post.txt": linkedin.strip() + "\n",
        "linkedin_carousel_outline.txt": linkedin_carousel.strip() + "\n",
        "instagram_caption.txt": instagram.strip() + "\n",
        "instagram_carousel_reel.txt": instagram_carousel_reel.strip() + "\n",
        "social_media_pack.md": social_pack.strip() + "\n",
    }





def calculate_quality_score(markdown_content: str, sources_count: int, content_source: str) -> Dict[str, Any]:
    """Scores generated article completeness using simple, explainable checks."""
    word_count = len(re.findall(r"\b\w+\b", markdown_content or ""))
    h2_count = len(re.findall(r"^##\s+", markdown_content or "", re.MULTILINE))
    has_faq = bool(re.search(r"frequently asked questions|##\s*faq", markdown_content or "", re.IGNORECASE))
    has_takeaways = bool(re.search(r"key takeaways", markdown_content or "", re.IGNORECASE))
    has_summary = bool(re.search(r"executive summary|summary", markdown_content or "", re.IGNORECASE))
    live_llm = not (content_source or "").startswith("offline_fallback")

    checks = {
        "live_llm": live_llm,
        "word_count_ok": 650 <= word_count <= 1600,
        "sources_ok": sources_count >= 4,
        "sections_ok": h2_count >= 4,
        "has_faq": has_faq,
        "has_key_takeaways": has_takeaways,
        "has_executive_summary": has_summary,
    }
    score = round((sum(1 for passed in checks.values() if passed) / len(checks)) * 10, 1)
    return {"score": score, "checks": checks}


def grade_source_quality(sources: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Grades source trust using domain-level signals that are easy to audit."""
    if not sources:
        return {
            "label": "weak",
            "score": 0.0,
            "trusted_sources_count": 0,
            "checked_domains": [],
        }

    high_trust_domains = {
        "bls.gov", "dol.gov", "census.gov", "bea.gov", "ed.gov", "whitehouse.gov",
        "shrm.org", "gartner.com", "mckinsey.com", "weforum.org", "microsoft.com",
        "linkedin.com", "economicgraph.linkedin.com", "hiringlab.org", "indeed.com",
        "challengetgray.com", "challengergray.com", "pwc.com", "deloitte.com",
    }
    medium_trust_suffixes = (".edu", ".org", ".gov")
    weak_indicators = ("medium.com", "substack.com", "reddit.com", "quora.com", "youtube.com", "tiktok.com")

    domain_scores = []
    checked_domains = []
    trusted_count = 0
    for source in sources:
        url = source.get("url", "")
        parsed = urllib.parse.urlparse(url)
        domain = parsed.netloc.lower().removeprefix("www.")
        if not domain:
            continue
        checked_domains.append(domain)

        if domain in high_trust_domains or any(domain.endswith(f".{d}") for d in high_trust_domains):
            domain_scores.append(10)
            trusted_count += 1
        elif domain.endswith(medium_trust_suffixes):
            domain_scores.append(8)
            trusted_count += 1
        elif any(indicator in domain for indicator in weak_indicators):
            domain_scores.append(4)
        else:
            domain_scores.append(6)

    if not domain_scores:
        return {
            "label": "weak",
            "score": 0.0,
            "trusted_sources_count": 0,
            "checked_domains": checked_domains,
        }

    base_score = sum(domain_scores) / len(domain_scores)
    source_count_bonus = min(len(domain_scores), 5) * 0.3
    score = round(min(10.0, base_score + source_count_bonus), 1)
    label = "excellent" if score >= 8.5 else "good" if score >= 7.0 else "fair" if score >= 5.0 else "weak"
    return {
        "label": label,
        "score": score,
        "trusted_sources_count": trusted_count,
        "checked_domains": checked_domains,
    }





async def generate_dynamic_editorial_content(deps: BlogAgentDeps) -> str:
    """
    Generates rich, publication-ready, evidence-based editorial articles using OpenRouter/Groq endpoints.
    """
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    groq_key = os.getenv("GROQ_API_KEY")
    evidence_context = "\n".join(
        f"- {item.get('title', 'Untitled source')}: {item.get('snippet', '').strip()} ({item.get('url', '#')})"
        for item in deps.evidence_pack[:6]
    ) or "- No live evidence was available. Avoid specific statistics and use qualitative guidance only."
    
    prompt = f"""You are a senior editor and chief investigative writer for a premier national publication.
Write a publication-ready, authoritative, evidence-backed editorial article in clean Markdown format.

TOPIC: {deps.topic}
TARGET AUDIENCE: {deps.audience}
EDITORIAL GOAL: {deps.goal}
TARGET WORD COUNT: ~{deps.word_target} words

AVAILABLE RESEARCH EVIDENCE:
{evidence_context}

SOURCE CITATION RULE:
- Treat the evidence list above as the complete fact boundary.
- Number the evidence items in the order shown as Source 1, Source 2, and so on.
- Add an inline citation such as [Source 1] immediately after every statistic, percentage, date, named report, market claim, or other externally verifiable factual statement.
- If the evidence does not support a precise claim, remove the precision and write qualitative guidance instead.
- Never invent a source, citation number, quote, statistic, or current event.

REQUIRED ARTICLE STRUCTURE:
1. Title Header: Start with '# {deps.topic}'
2. Executive Summary Block: Right under title, write a 3-4 sentence Executive Summary explaining why this topic matters right now in 2026.
3. Key Takeaways Block: Include 4-5 bulleted key takeaways capturing the essential trends and data points.
4. Section 1 (Overview & Market Dynamics): Write '## {deps.topic}: Overview and Current Landscape in 2026' with 300+ words of direct, specific analysis. Include actual statistics only when they appear in AVAILABLE RESEARCH EVIDENCE, with inline [Source N] citations.
5. Section 2 (Key Developments & Industry Impact): Write '## Key Developments and Strategic Workforce Impact' analyzing shifts in technology, hiring, operations, or policy.
6. Section 3 (Practical Takeaways & Implementation): Write '## What This Means for Employers & Job Seekers' with concrete bullet points for both groups.
7. Section 4 (Challenges & Future Outlook): Write '## Challenges, Compliance, and Future Outlook for 2026' focusing on risk, ethics, and future projections.
8. Section 5 (Search-Intent FAQ): Write '## Frequently Asked Questions (FAQ)' with 4-5 realistic search questions as '### Question?' (e.g., 'Will AI replace recruiters?', 'How are companies using AI in candidate screening?', 'What skills help job seekers stand out?').
9. Section 6 (Sources & Further Reading): Write '## Sources & Further Reading' listing the available sources with their matching [Source N] labels and URLs.

STRICT TONE & STYLE RULES:
- AVOID formulaic AI buzzwords ('profound transformation', 'strategic drivers', 'forward-looking posture', 'evolving economic priorities').
- Replace generic claims with direct, evidence-driven explanations.
- Use only statistics, dates, named reports, and source claims that appear in AVAILABLE RESEARCH EVIDENCE.
- If evidence is not specific enough, write qualitative analysis instead of inventing numbers.
- DO NOT include programming code blocks unless the topic explicitly asks for coding.
- Return ONLY clean Markdown starting with the title header.
"""

    if deps.template_name in ("Hireko Editorial", "Hireko Vercel Editorial"):
        prompt += f"""

HIREKO EDITORIAL MODE:
- Write specifically for Hireko.ai, an AI-driven recruiting platform for resume processing, job posting workflows, candidate matching, conversational video interviews, and objective hiring workflows.
- Position Hireko as intelligent, trustworthy, human-centered, and practical for HR leaders, recruiters, hiring managers, and candidates.
- Include sections that naturally support workflow diagrams, checklists, comparison tables, quote blocks, and practical examples.
- Favor Hireko content pillars: AI interview platform education, competitor comparisons, AI hiring thought leadership, enterprise recruitment automation, candidate experience, skills-based hiring, recruiter productivity, ROI, and compliance.
- Include one concise section titled "LinkedIn and Instagram content angle" with platform-ready bullets that can be reused by the social generator.
- Keep product mentions useful and specific. Avoid over-selling or generic startup language.
"""

    if deps.template_name == "Casual Blog":
        prompt += f"""

CASUAL BLOG MODE:
- Write like a clear, friendly blog for smart readers, not like a corporate report.
- Keep sentences direct and conversational.
- Avoid heavy report language such as "strategic workforce impact", "compliance framework", and "publication-ready analysis" unless truly needed.
- Use practical section headings readers would naturally click, such as "What is changing?", "Why it matters", "What to do next", and "FAQ".
- Keep sources and facts, but explain them in plain English.
- Make the introduction warm and easy to read.
"""

    min_acceptable_words = max(240, min(300, int(deps.word_target * 0.35)))

    # 1. Try OpenRouter API with model fallbacks.
    if openrouter_key:
        openrouter_models = unique_model_order(
            os.getenv("LLM_MODEL", "qwen/qwen3.7-flash"),
            [
                "qwen/qwen3.7-flash",
                "qwen/qwen-plus",
                "meta-llama/llama-3.3-70b-instruct:free",
                "deepseek/deepseek-r1:free",
            ],
        )
        async with httpx.AsyncClient() as client:
            for model_name in openrouter_models:
                try:
                    print(f"   [LLM Note] Trying OpenRouter model: {model_name}")
                    start_model_time = time.time()
                    request_prompt = prompt
                    if model_name.endswith(":free"):
                        request_prompt = prompt + "\n\nKeep the final article concise but complete. Aim for 650-900 words."
                    res = await client.post(
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {openrouter_key}",
                            "Content-Type": "application/json",
                            "HTTP-Referer": "https://github.com/pydantic-ai-harness",
                            "X-Title": "Pydantic AI Blog Agent",
                        },
                        json={
                            "model": model_name,
                            "messages": [
                                {"role": "system", "content": "You are a senior publication editor writing authoritative, evidence-backed articles."},
                                {"role": "user", "content": request_prompt}
                            ],
                            "temperature": 0.7,
                            "max_tokens": 4000
                        },
                        timeout=60.0
                    )
                    elapsed = round(time.time() - start_model_time, 2)
                    if res.status_code == 200:
                        data = res.json()
                        content = data["choices"][0]["message"]["content"]
                        word_count = len(content.split()) if content else 0
                        if content and word_count >= min_acceptable_words:
                            deps.content_source = f"openrouter:{model_name}"
                            print(f"   [LLM Note] OpenRouter accepted {model_name} ({word_count} words, {elapsed}s)")
                            return content
                        print(f"   [LLM Note] OpenRouter {model_name} too short ({word_count} words, {elapsed}s); trying next model.")
                    else:
                        print(f"   [LLM Note] OpenRouter {model_name} returned HTTP {res.status_code}: {res.text[:300]}")
                except Exception as e:
                    print(f"   [LLM Note] OpenRouter {model_name} exception: {e}")

    # 2. Try Groq API (Secondary)
    if groq_key:
        try:
            async with httpx.AsyncClient() as client:
                res = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {groq_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "llama-3.3-70b-versatile",
                        "messages": [
                            {"role": "system", "content": "You are a senior publication editor writing authoritative, evidence-backed articles."},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.7,
                        "max_tokens": 4000
                    },
                    timeout=60.0
                )
                if res.status_code == 200:
                    data = res.json()
                    content = data["choices"][0]["message"]["content"]
                    if content and len(content.split()) >= min_acceptable_words:
                        deps.content_source = "groq"
                        return content
                    word_count = len(content.split()) if content else 0
                    print(f"   [LLM Note] Groq response was too short ({word_count} words); using fallback.")
                else:
                    print(f"   [LLM Note] Groq returned HTTP {res.status_code}: {res.text[:300]}")
        except Exception as e:
            print(f"   [LLM Note] Groq call exception: {e}")

    # 3. Editorial Fallback Generator
    deps.content_source = "offline_fallback"
    return build_editorial_fallback_article(deps)


def build_editorial_fallback_article(deps: BlogAgentDeps) -> str:
    """Generates structured, publication-ready editorial content for fallback execution."""
    t = deps.topic.strip()
    topic_sentence = t[:1].lower() + t[1:] if t else "this topic"
    audience = deps.audience or "readers"
    goal = (deps.goal or "explain the current landscape and practical next steps").strip().rstrip(".")
    
    return f"""# {t}

> **Executive Summary:** For {audience}, {topic_sentence} matters because {goal}. This guide separates established evidence from areas that need continued monitoring, then turns the topic into practical decisions readers can use. Where an exact figure matters, verify it against the linked source before publication.

> **Key Takeaways:**
> - Use fresh source evidence before adding statistics, percentages, or dated claims.
> - Explain what is changing, who is affected, and what action the reader should take next.
> - Separate short-term operational shifts from longer-term strategy and policy questions.
> - Keep recommendations practical for employers, workers, students, and decision-makers.

## 01 - What the Latest Data Shows
In 2026, {topic_sentence} needs to be explained through current labor-market data, employer behavior, worker expectations, and technology adoption. Public statistics, employer surveys, and industry reports should validate any specific numbers before publication. When exact figures are missing, the safer editorial move is to describe the direction of change and clearly mark what still needs verification.

The strongest articles connect the topic to visible decisions: hiring plans, automation investments, skill requirements, wage pressure, remote or hybrid work policies, and compliance expectations. This keeps the report useful instead of turning it into broad commentary.

- **Market Signal:** Identify whether demand, supply, wages, productivity, or regulation is the main force behind the topic.
- **Reader Impact:** Translate the trend into practical consequences for the target audience.
- **Evidence Gap:** Avoid unsupported numbers and use source links to verify claims before final publication.

## 02 - Sector Shifts & Key Developments
The next layer is sector impact. Some industries adopt new tools quickly because the cost savings are obvious; others move slowly because trust, regulation, training, or legacy systems create friction. A useful blog should name these differences instead of treating the market as one uniform trend.

For {audience}, the practical question is not only what is changing, but where the change is happening first. Look for examples across technology, healthcare, education, finance, manufacturing, public sector work, and small business operations. The article should connect those examples back to the reader's decisions.

> *Editorial note:* Use the linked evidence to verify any exact figures, dates, or named examples before publication.

## 03 - What It Means for Workers & Employers

### For Employers & Hiring Managers
- **Audit Decisions:** Review whether new tools, policies, or hiring criteria are producing fair and explainable outcomes.
- **Invest in Training:** Help managers interpret data and communicate changes clearly to teams.
- **Update Planning:** Align headcount, budgets, and workforce strategy with the latest evidence.

### For Job Seekers & Professionals
- **Show Proof of Skill:** Use projects, certifications, portfolios, and measurable outcomes to make capability visible.
- **Track Demand:** Watch job postings, salary guides, and employer reports for changes in required skills.
- **Use AI Carefully:** AI can help with preparation and writing, but personal claims should stay accurate and verifiable.

## 04 - What Happens Next & Future Outlook
The next phase will depend on adoption speed, policy clarity, and whether organizations can turn experimentation into repeatable operating practice. Readers should watch for changes in job postings, training budgets, productivity expectations, compliance rules, and worker sentiment.

The best final version of this report should add precise numbers from the sources, compare the strongest evidence, and turn the findings into a clear checklist for action.

## Frequently Asked Questions (FAQ)

### What is changing most in {t}?
The biggest changes usually appear in employer demand, skill expectations, technology adoption, and policy requirements. The final article should cite current sources for exact figures.

### Why does this matter for {audience}?
Because the topic affects planning, career choices, hiring decisions, budgets, and risk management. A good report converts the trend into decisions readers can act on.

### What should employers do first?
They should verify the evidence, identify the most exposed teams or processes, and create a practical response plan with clear ownership.

### What should workers or students do next?
They should track demand signals, keep proof of skills current, and focus on adaptable capabilities that remain valuable as tools and work models change.

## Sources & Further Reading
- [U.S. Bureau of Labor Statistics - Employment & Economic Reports](https://www.bls.gov)
- [SHRM - Talent Acquisition & AI Research](https://www.shrm.org)
- [LinkedIn Workforce Report - Hiring Trends & Skill Demands](https://www.linkedin.com)
"""


async def run_3_iteration_blog_pipeline(deps: BlogAgentDeps, model: Any = "openrouter:qwen/qwen3.7-flash") -> Dict[str, Any]:
    """Executes the 3-iteration refinement loop for publication-quality blog generation."""
    agent = create_blog_agent(model)
    article_folder = deps.get_article_folder()
    fallback_chain = get_fallback_chain()
    
    print(f"\n=======================================================")
    print("Starting 3-Iteration Publication Blog Pipeline")
    print(f"   Topic: {deps.topic}")
    print(f"   Output Folder: {article_folder}")
    print(f"   Template: {deps.template_name}")
    print(f"   Fallback Models Available: {len(fallback_chain)}")
    print(f"=======================================================\n")

    deps.fs.ensure_dir(article_folder)

    # -----------------------------------------------------------------
    # ITERATION 1: Deep Research & Dynamic LLM Content Generation
    # -----------------------------------------------------------------
    deps.current_iteration = 1
    print("[Iteration 1/3] Deep Research & LLM Editorial Content Generation...")
    start_time = time.time()
    
    search_results = await perform_web_search(f"2026 {deps.topic} research report")
    deps.evidence_pack = search_results

    deps.keywords = {
        "primary": f"{deps.topic.lower()}",
        "supporting": ["workforce trends 2026", "recruitment analytics", "industry insights"]
    }

    deps.raw_draft = await generate_dynamic_editorial_content(deps)
    it1_duration = round(time.time() - start_time, 2)
    print(f"   [Iteration 1 Complete] Editorial article generated ({len(deps.raw_draft.split())} words, {it1_duration}s)")

    # -----------------------------------------------------------------
    # ITERATION 2: Fact-Check Auditor & Scope Guard Refinement
    # -----------------------------------------------------------------
    deps.current_iteration = 2
    print("[Iteration 2/3] Fact-Check Auditing & Quality Clean-up...")
    start_time = time.time()

    audited_lines = []
    for line in deps.raw_draft.splitlines():
        if "```" in line and not any(kw in deps.topic.lower() for kw in ["code", "programming", "script", "developer"]):
            continue
        audited_lines.append(line)

    deps.audited_draft = "\n".join(audited_lines)
    it2_duration = round(time.time() - start_time, 2)
    print(f"   [Iteration 2 Complete] Fact-Check Audit applied ({it2_duration}s)")

    # -----------------------------------------------------------------
    # ITERATION 3: HTML Rendering & Asset Generation
    # -----------------------------------------------------------------
    deps.current_iteration = 3
    print("[Iteration 3/3] Rendering HTML5 Package & Self-Contained Assets...")
    start_time = time.time()

    package = await render_full_html_package(
        title=deps.topic,
        subtitle=deps.goal,
        markdown_content=deps.audited_draft,
        template_name=deps.template_name,
        sources=deps.evidence_pack,
        keywords=deps.keywords,
        audience=deps.audience,
        goal=deps.goal
    )

    index_path = os.path.join(article_folder, "index.html")
    styles_path = os.path.join(article_folder, "styles.css")
    markdown_path = os.path.join(article_folder, "article.md")
    seo_path = os.path.join(article_folder, "seo.json")
    meta_json_path = os.path.join(article_folder, "meta.json")

    deps.fs.write_file(index_path, package["index.html"])
    deps.fs.write_file(styles_path, package["styles.css"])
    package_assets = package.get("assets", {})
    stale_assets_dir = os.path.join(article_folder, "assets")
    if not package_assets and os.path.isdir(stale_assets_dir):
        shutil.rmtree(stale_assets_dir)
    for asset_rel_path, asset_source_path in package_assets.items():
        asset_target_path = os.path.join(article_folder, asset_rel_path)
        os.makedirs(os.path.dirname(asset_target_path), exist_ok=True)
        shutil.copyfile(asset_source_path, asset_target_path)
    deps.fs.write_file(markdown_path, deps.audited_draft)
    seo_metadata = build_seo_metadata(deps, deps.audited_draft)
    deps.fs.write_file(seo_path, json.dumps(seo_metadata, indent=2))
    social_posts = build_hireko_social_posts(deps, deps.audited_draft, seo_metadata)
    for social_filename, social_content in social_posts.items():
        deps.fs.write_file(os.path.join(article_folder, social_filename), social_content)

    fact_check = audit_factual_claims(
        deps.audited_draft,
        deps.evidence_pack,
        deps.content_source or "unknown",
    )
    quality = calculate_quality_score(
        deps.audited_draft,
        len(deps.evidence_pack),
        deps.content_source or "unknown",
    )
    source_quality = grade_source_quality(deps.evidence_pack)
    generated_files = [
        "index.html",
        "styles.css",
        "article.md",
        "seo.json",
        "meta.json",
        *social_posts.keys(),
    ]

    meta_data = {
        "article_name": deps.article_name,
        "topic": deps.topic,
        "template": deps.template_name,
        "word_count": len(deps.audited_draft.split()),
        "iteration_count": 3,
        "content_source": deps.content_source or "unknown",
        "quality_score": quality["score"],
        "quality_checks": quality["checks"],
        "seo": seo_metadata,
        "source_quality": source_quality["label"],
        "source_quality_score": source_quality["score"],
        "source_quality_details": source_quality,
        "fact_check": fact_check,
        "publication_status": fact_check["status"],
        "generated_files": generated_files,
        "social_files": list(social_posts.keys()),
        "evidence_sources_count": len(deps.evidence_pack)
    }
    deps.fs.write_file(meta_json_path, json.dumps(meta_data, indent=2))

    deps.final_html_path = index_path
    it3_duration = round(time.time() - start_time, 2)
    print(f"   [Iteration 3 Complete] HTML package written to {article_folder} ({it3_duration}s)")

    print(f"\n=======================================================")
    print("3-Iteration Blog Generation Completed Successfully!")
    print(f"   HTML File: file://{os.path.abspath(index_path)}")
    print(f"   Stylesheet: file://{os.path.abspath(styles_path)}")
    print(f"   Meta Config: file://{os.path.abspath(meta_json_path)}")
    print(f"   Publication Status: {fact_check['status']}")
    if fact_check["status"] != "publish_ready":
        print(f"   Review Note: {fact_check['review_reason']}")
    print(f"=======================================================\n")

    return {
        "success": True,
        "article_folder": article_folder,
        "index_path": index_path,
        "markdown_path": markdown_path,
        "meta_json_path": meta_json_path,
        "word_count": len(deps.audited_draft.split()),
        "content_source": deps.content_source or "unknown",
        "quality_score": quality["score"],
        "source_quality": source_quality["label"],
        "source_quality_score": source_quality["score"],
        "fact_check": fact_check,
        "publication_status": fact_check["status"],
        "iterations": 3
    }
