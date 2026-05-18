## Plan: Add CLI wrappers (bash + PowerShell)

TL;DR - Create a small bash wrapper: `scrape`. It queres the `https://www.pkulaw.com/lawrule` endpoint to find the canonical relative page `url`, prefers the result whose `name` contains “现行有效”, build a full URL by prefixing `https://www.pkulaw.com`, and invoke the existing spider CLI `python spiders/law_spider.py --url <FULL_URL> [--headless]` to fetch and save the result.

**Steps**
1. Create `scrape` (bash):
   - Use `curl -sG 'https://www.pkulaw.com/lawrule' --data-urlencode 'lib=$LIB' --data-urlencode 'keywords=$TITLE' -H 'Accept: application/json' -A 'Mozilla/5.0'` to fetch JSON.
   - Parse the JSON with `jq` to select the `url` field from the first item whose `name` contains `现行有效`; fallback to `.[0].url` if none match. (If `jq` is not installed, fallback to a short `python -c` parser.)
   - Compose `FULL_URL` by prefixing `https://www.pkulaw.com` to the returned relative `url`.
   - Run the spider CLI: `$PYTHON spiders/law_spider.py --url "$FULL_URL" --headless` and surface errors if the lawrule response is empty.
   - Make the script executable (`chmod +x scrape`).

2. Update `README.md` with usage examples and prerequisites: `python3`, `Firefox` + `geckodriver` and `jq` (for bash).
