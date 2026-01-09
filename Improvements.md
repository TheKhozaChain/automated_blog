# Daily AI Timeline - Improvements

Track planned improvements for the blog. ~~Strikethrough~~ items are completed.

---

## 📰 Content & Sources

1. ~~**More sources** - Add Google News API, Reddit (r/MachineLearning, r/artificial), Twitter/X lists, newsletters (The Batch, Import AI)~~ ✅ Added Reddit r/MachineLearning and r/artificial

2. ~~**Historical archive** - Keep past articles in a browsable archive instead of overwriting `today.md`~~ ✅ Articles saved to `out/archive/` with dates, archive.html page added

3. ~~**Weekly digest mode** - Generate a longer weekly roundup in addition to daily posts~~ ✅ Added `--mode weekly` (7-day lookback)

---

## 🎨 Frontend & UX

4. **RSS feed output** - Generate an RSS feed so readers can subscribe

5. **Mobile PWA** - Make it installable as a progressive web app

6. **Search** - Full-text search across archived posts

7. **Table of contents** - For longer articles, add anchor links to each story

8. **Social share buttons** - One-click share to Twitter/LinkedIn

---

## 🚀 Distribution & Publishing

9. **Auto-post to social media** - Publish directly to X/LinkedIn via APIs

10. **Email newsletter** - Integrate with Mailchimp/Buttondown to send daily emails

11. **Deploy to hosting** - Auto-deploy to Vercel/Netlify/GitHub Pages

12. **Custom domain** - Add instructions for pointing a domain to the blog

---

## ⚡ Automation

13. **Cron/scheduler** - Set up a cron job or GitHub Action to run daily automatically

14. **One-command daily** - Combine `run` + `serve` into a single `python -m daily_ai_timeline daily` command

15. **Watch mode** - Auto-regenerate when sources.json changes

---

## 📊 Analytics & Feedback

16. **Click tracking** - Track which linked articles readers actually click

17. **Readership analytics** - Simple analytics (page views, time on page)

18. **Thumbs up/down** - Let readers rate articles to improve future selection

---

## 🧠 Quality & Intelligence

19. **Sentiment analysis** - Tag stories as positive/negative/neutral

20. **Clustering** - Group related stories together (e.g., all CES stories)

21. **Importance scoring** - Use LLM to rate "how significant is this for the AI field?"

22. **Fact-checking prompts** - Add a step that flags potentially dubious claims

23. **Source diversity** - Ensure the 10 selected items come from diverse sources, not all from one outlet

---

## 🔧 Developer Experience

24. **Config file** - Move settings from `.env` to a `config.yaml` for easier editing

25. **Preview mode** - Generate without the expensive DALL-E call for testing

26. **Dry run** - Show what would be generated without actually calling LLMs

27. **Better error handling** - Graceful fallbacks when arXiv or other sources are down
