#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UI/UX Pro Max Core - BM25 search engine for UI/UX style guides
"""

import csv
import re
from pathlib import Path
from math import log
from collections import defaultdict

# ============ CONFIGURATION ============
DATA_DIR = Path(__file__).parent.parent.parent / "data"
MAX_RESULTS = 3

# ============ CHINESE TO ENGLISH TRANSLATION MAP ============
ZH_EN_TRANSLATION_MAP = {
    "科技": "tech technology",
    "公司": "company business",
    "科技公司": "tech startup SaaS",
    "创业": "startup",
    "创业公司": "startup company",
    "互联网": "internet web",
    "软件": "software app",
    "应用": "app application",
    "平台": "platform",
    "奢侈": "luxury premium",
    "奢侈品": "luxury premium high-end",
    "奢侈品牌": "luxury brand premium",
    "高端": "high-end premium luxury",
    "医疗": "medical healthcare",
    "健康": "health wellness",
    "医疗健康": "healthcare medical health",
    "医院": "hospital clinic medical",
    "诊所": "clinic medical",
    "金融": "finance financial fintech",
    "金融科技": "fintech blockchain crypto",
    "银行": "banking finance",
    "支付": "payment fintech",
    "投资": "investment finance",
    "保险": "insurance",
    "教育": "education learning",
    "培训": "training course",
    "教育培训": "education e-learning course",
    "学校": "school education",
    "在线教育": "online course e-learning",
    "电商": "e-commerce ecommerce retail",
    "电子商务": "e-commerce ecommerce",
    "零售": "retail shop store",
    "购物": "shopping e-commerce",
    "商城": "marketplace e-commerce store",
    "创意": "creative artistic",
    "设计": "design creative",
    "创意设计": "creative agency design studio",
    "广告": "advertising marketing agency",
    "营销": "marketing advertising",
    "品牌": "brand branding",
    "企业": "enterprise business corporate",
    "企业服务": "B2B service enterprise",
    "政府": "government public service",
    "公共服务": "public service government",
    "游戏": "gaming game entertainment",
    "娱乐": "entertainment media",
    "音乐": "music streaming audio",
    "视频": "video streaming OTT",
    "社交": "social media network",
    "社交媒体": "social media app",
    "旅游": "travel tourism",
    "酒店": "hotel hospitality",
    "餐饮": "restaurant food cafe",
    "美食": "food culinary restaurant",
    "咖啡": "coffee cafe",
    "美容": "beauty spa wellness",
    "健身": "fitness gym workout",
    "房地产": "real estate property",
    "汽车": "automotive car dealership",
    "物流": "logistics delivery",
    "快递": "delivery logistics",
    "农业": "agriculture farm tech",
    "建筑": "construction architecture",
    "法律": "legal law attorney",
    "律师": "attorney legal law",
    "宠物": "pet tech animal",
    "儿童": "children kids childcare",
    "婚礼": "wedding event planning",
    "摄影": "photography studio",
    "新闻": "news media journalism",
    "博客": "blog magazine editorial",
    "简约": "minimalism minimal clean",
    "简洁": "clean minimal simple",
    "现代": "modern contemporary",
    "专业": "professional corporate",
    "优雅": "elegant sophisticated",
    "活泼": "vibrant playful energetic",
    "暗黑": "dark mode OLED",
    "深色": "dark mode dark theme",
    "科幻": "sci-fi futuristic cyberpunk",
    "复古": "retro vintage nostalgic",
    "极简": "minimalist minimal swiss",
    "玻璃": "glassmorphism glass",
    "毛玻璃": "glassmorphism frosted glass",
    "立体": "3D depth dimensional",
    "扁平": "flat design 2D",
    "渐变": "gradient aurora mesh",
    "仪表盘": "dashboard analytics",
    "数据分析": "analytics data dashboard",
    "后台": "admin dashboard panel",
    "管理系统": "admin dashboard management",
    "人工智能": "AI artificial intelligence",
    "智能": "AI smart intelligent",
    "聊天机器人": "chatbot AI assistant",
    "区块链": "blockchain crypto web3",
    "加密货币": "crypto cryptocurrency NFT",
    "元宇宙": "metaverse VR AR spatial",
    "虚拟现实": "VR virtual reality spatial",
    "可持续": "sustainable ESG green",
    "环保": "eco sustainable green",
    "数字产品": "digital products downloads",
    "订阅": "subscription SaaS membership",
    "会员": "membership community subscription",
    "自由职业": "freelancer platform",
    "远程办公": "remote work collaboration",
    "协作": "collaboration teamwork",
    "演示": "presentation pitch deck",
    "演讲": "presentation speech pitch",
    "路演": "pitch deck startup",
    "融资": "funding investment pitch",
    "商业计划": "business plan pitch startup",
}


def translate_chinese_to_english(query: str) -> str:
    """
    Translate Chinese keywords to English for better search results.
    Falls back to original query if no translation found.
    """
    if not any('\u4e00' <= char <= '\u9fff' for char in query):
        return query

    translated_parts = []
    remaining = query

    sorted_keys = sorted(ZH_EN_TRANSLATION_MAP.keys(), key=len, reverse=True)

    for zh_term in sorted_keys:
        if zh_term in remaining:
            en_term = ZH_EN_TRANSLATION_MAP[zh_term]
            translated_parts.append(en_term)
            remaining = remaining.replace(zh_term, " ", 1)

    non_chinese = re.sub(r'[\u4e00-\u9fff]', ' ', remaining)
    non_chinese = ' '.join(non_chinese.split())

    if non_chinese:
        translated_parts.append(non_chinese)

    if translated_parts:
        result = ' '.join(translated_parts)
        return ' '.join(result.split())

    return query

CSV_CONFIG = {
    "style": {
        "file": "styles.csv",
        "search_cols": ["Style Category", "Keywords", "Best For", "Type", "AI Prompt Keywords"],
        "output_cols": ["Style Category", "Type", "Keywords", "Primary Colors", "Effects & Animation", "Best For", "Performance", "Accessibility", "Framework Compatibility", "Complexity", "AI Prompt Keywords", "CSS/Technical Keywords", "Implementation Checklist", "Design System Variables"]
    },
    "color": {
        "file": "colors.csv",
        "search_cols": ["Product Type", "Notes"],
        "output_cols": ["Product Type", "Primary (Hex)", "Secondary (Hex)", "CTA (Hex)", "Background (Hex)", "Text (Hex)", "Notes"]
    },
    "chart": {
        "file": "charts.csv",
        "search_cols": ["Data Type", "Keywords", "Best Chart Type", "Accessibility Notes"],
        "output_cols": ["Data Type", "Keywords", "Best Chart Type", "Secondary Options", "Color Guidance", "Accessibility Notes", "Library Recommendation", "Interactive Level"]
    },
    "landing": {
        "file": "landing.csv",
        "search_cols": ["Pattern Name", "Keywords", "Conversion Optimization", "Section Order"],
        "output_cols": ["Pattern Name", "Keywords", "Section Order", "Primary CTA Placement", "Color Strategy", "Conversion Optimization"]
    },
    "product": {
        "file": "products.csv",
        "search_cols": ["Product Type", "Keywords", "Primary Style Recommendation", "Key Considerations"],
        "output_cols": ["Product Type", "Keywords", "Primary Style Recommendation", "Secondary Styles", "Landing Page Pattern", "Dashboard Style (if applicable)", "Color Palette Focus"]
    },
    "ux": {
        "file": "ux-guidelines.csv",
        "search_cols": ["Category", "Issue", "Description", "Platform"],
        "output_cols": ["Category", "Issue", "Platform", "Description", "Do", "Don't", "Code Example Good", "Code Example Bad", "Severity"]
    },
    "typography": {
        "file": "typography.csv",
        "search_cols": ["Font Pairing Name", "Category", "Mood/Style Keywords", "Best For", "Heading Font", "Body Font"],
        "output_cols": ["Font Pairing Name", "Category", "Heading Font", "Body Font", "Mood/Style Keywords", "Best For", "Google Fonts URL", "CSS Import", "Tailwind Config", "Notes"]
    },
    "icons": {
        "file": "icons.csv",
        "search_cols": ["Category", "Icon Name", "Keywords", "Best For"],
        "output_cols": ["Category", "Icon Name", "Keywords", "Library", "Import Code", "Usage", "Best For", "Style"]
    },
    "react": {
        "file": "react-performance.csv",
        "search_cols": ["Category", "Issue", "Keywords", "Description"],
        "output_cols": ["Category", "Issue", "Platform", "Description", "Do", "Don't", "Code Example Good", "Code Example Bad", "Severity"]
    },
    "web": {
        "file": "web-interface.csv",
        "search_cols": ["Category", "Issue", "Keywords", "Description"],
        "output_cols": ["Category", "Issue", "Platform", "Description", "Do", "Don't", "Code Example Good", "Code Example Bad", "Severity"]
    }
}

STACK_CONFIG = {
    "html-tailwind": {"file": "stacks/html-tailwind.csv"},
    "react": {"file": "stacks/react.csv"},
    "nextjs": {"file": "stacks/nextjs.csv"},
    "astro": {"file": "stacks/astro.csv"},
    "vue": {"file": "stacks/vue.csv"},
    "nuxtjs": {"file": "stacks/nuxtjs.csv"},
    "nuxt-ui": {"file": "stacks/nuxt-ui.csv"},
    "svelte": {"file": "stacks/svelte.csv"},
    "swiftui": {"file": "stacks/swiftui.csv"},
    "react-native": {"file": "stacks/react-native.csv"},
    "flutter": {"file": "stacks/flutter.csv"},
    "shadcn": {"file": "stacks/shadcn.csv"},
    "jetpack-compose": {"file": "stacks/jetpack-compose.csv"}
}

# Common columns for all stacks
_STACK_COLS = {
    "search_cols": ["Category", "Guideline", "Description", "Do", "Don't"],
    "output_cols": ["Category", "Guideline", "Description", "Do", "Don't", "Code Good", "Code Bad", "Severity", "Docs URL"]
}

AVAILABLE_STACKS = list(STACK_CONFIG.keys())


# ============ BM25 IMPLEMENTATION ============
class BM25:
    """BM25 ranking algorithm for text search"""

    def __init__(self, k1=1.5, b=0.75):
        self.k1 = k1
        self.b = b
        self.corpus = []
        self.doc_lengths = []
        self.avgdl = 0
        self.idf = {}
        self.doc_freqs = defaultdict(int)
        self.N = 0

    def tokenize(self, text):
        """Lowercase, split, remove punctuation, filter short words"""
        text = re.sub(r'[^\w\s]', ' ', str(text).lower())
        return [w for w in text.split() if len(w) > 2]

    def fit(self, documents):
        """Build BM25 index from documents"""
        self.corpus = [self.tokenize(doc) for doc in documents]
        self.N = len(self.corpus)
        if self.N == 0:
            return
        self.doc_lengths = [len(doc) for doc in self.corpus]
        self.avgdl = sum(self.doc_lengths) / self.N

        for doc in self.corpus:
            seen = set()
            for word in doc:
                if word not in seen:
                    self.doc_freqs[word] += 1
                    seen.add(word)

        for word, freq in self.doc_freqs.items():
            self.idf[word] = log((self.N - freq + 0.5) / (freq + 0.5) + 1)

    def score(self, query):
        """Score all documents against query"""
        query_tokens = self.tokenize(query)
        scores = []

        for idx, doc in enumerate(self.corpus):
            score = 0
            doc_len = self.doc_lengths[idx]
            term_freqs = defaultdict(int)
            for word in doc:
                term_freqs[word] += 1

            for token in query_tokens:
                if token in self.idf:
                    tf = term_freqs[token]
                    idf = self.idf[token]
                    numerator = tf * (self.k1 + 1)
                    denominator = tf + self.k1 * (1 - self.b + self.b * doc_len / self.avgdl)
                    score += idf * numerator / denominator

            scores.append((idx, score))

        return sorted(scores, key=lambda x: x[1], reverse=True)


# ============ SEARCH FUNCTIONS ============
def _load_csv(filepath):
    """Load CSV and return list of dicts"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def _search_csv(filepath, search_cols, output_cols, query, max_results):
    """Core search function using BM25"""
    if not filepath.exists():
        return []

    data = _load_csv(filepath)

    # Build documents from search columns
    documents = [" ".join(str(row.get(col, "")) for col in search_cols) for row in data]

    # BM25 search
    bm25 = BM25()
    bm25.fit(documents)
    ranked = bm25.score(query)

    # Get top results with score > 0
    results = []
    for idx, score in ranked[:max_results]:
        if score > 0:
            row = data[idx]
            results.append({col: row.get(col, "") for col in output_cols if col in row})

    return results


def detect_domain(query):
    """Auto-detect the most relevant domain from query"""
    query_lower = query.lower()

    domain_keywords = {
        "color": ["color", "palette", "hex", "#", "rgb"],
        "chart": ["chart", "graph", "visualization", "trend", "bar", "pie", "scatter", "heatmap", "funnel"],
        "landing": ["landing", "page", "cta", "conversion", "hero", "testimonial", "pricing", "section"],
        "product": ["saas", "ecommerce", "e-commerce", "fintech", "healthcare", "gaming", "portfolio", "crypto", "dashboard", "luxury", "premium", "brand", "startup", "app", "platform", "service", "agency", "restaurant", "hotel", "travel", "education", "fitness", "real estate", "automotive", "medical", "legal", "insurance", "banking", "streaming", "social", "marketplace", "logistics", "news", "blog", "wedding", "photography", "construction", "agriculture"],
        "style": ["style", "design", "ui", "minimalism", "glassmorphism", "neumorphism", "brutalism", "dark mode", "flat", "aurora", "prompt", "css", "implementation", "variable", "checklist", "tailwind", "modern", "clean", "elegant", "playful", "vibrant", "retro", "sci-fi", "cyberpunk"],
        "ux": ["ux", "usability", "accessibility", "wcag", "touch", "scroll", "animation", "keyboard", "navigation", "mobile"],
        "typography": ["font", "typography", "heading", "serif", "sans"],
        "icons": ["icon", "icons", "lucide", "heroicons", "symbol", "glyph", "pictogram", "svg icon"],
        "react": ["react", "next.js", "nextjs", "suspense", "memo", "usecallback", "useeffect", "rerender", "bundle", "waterfall", "barrel", "dynamic import", "rsc", "server component"],
        "web": ["aria", "focus", "outline", "semantic", "virtualize", "autocomplete", "form", "input type", "preconnect"]
    }

    scores = {domain: sum(1 for kw in keywords if kw in query_lower) for domain, keywords in domain_keywords.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "product"


def search(query, domain=None, max_results=MAX_RESULTS):
    """Main search function with auto-domain detection and Chinese translation fallback"""
    translated_query = translate_chinese_to_english(query)

    if domain is None:
        domain = detect_domain(translated_query)

    config = CSV_CONFIG.get(domain, CSV_CONFIG["style"])
    filepath = DATA_DIR / config["file"]

    if not filepath.exists():
        return {"error": f"File not found: {filepath}", "domain": domain}

    results = _search_csv(filepath, config["search_cols"], config["output_cols"], translated_query, max_results)

    return {
        "domain": domain,
        "query": query,
        "translated_query": translated_query if translated_query != query else None,
        "file": config["file"],
        "count": len(results),
        "results": results
    }


def search_stack(query, stack, max_results=MAX_RESULTS):
    """Search stack-specific guidelines with Chinese translation fallback"""
    if stack not in STACK_CONFIG:
        return {"error": f"Unknown stack: {stack}. Available: {', '.join(AVAILABLE_STACKS)}"}

    translated_query = translate_chinese_to_english(query)
    filepath = DATA_DIR / STACK_CONFIG[stack]["file"]

    if not filepath.exists():
        return {"error": f"Stack file not found: {filepath}", "stack": stack}

    results = _search_csv(filepath, _STACK_COLS["search_cols"], _STACK_COLS["output_cols"], translated_query, max_results)

    return {
        "domain": "stack",
        "stack": stack,
        "query": query,
        "translated_query": translated_query if translated_query != query else None,
        "file": STACK_CONFIG[stack]["file"],
        "count": len(results),
        "results": results
    }
