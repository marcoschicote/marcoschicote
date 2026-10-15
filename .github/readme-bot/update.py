#!/usr/bin/env python3
"""Propose updates to the "open source" part of the profile README.

Finds what's new since the last run (merged PRs to other people's repos,
commits that credit me as co-author, new public repos of mine), asks a free
OpenRouter model to fold it into the README section between the markers, and
leaves the result in the working tree for the workflow to turn into a PR.

    update.py            detect, rewrite README.md and state.json if needed
    update.py --dry-run  detect and print what's new, change nothing
    update.py --seed     mark everything found today as seen, change nothing else

Set FORGET=<substring> to treat matching seen items as new, e.g. to try a run.
"""

import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
README = os.path.join(ROOT, "README.md")
CONFIG = os.path.join(HERE, "config.json")
STATE = os.path.join(HERE, "state.json")
PR_BODY = os.path.join(HERE, "pr-body.md")  # not committed, read by the workflow

START, END = "<!-- GITHUB:START -->", "<!-- GITHUB:END -->"
HEADING = "**Open source**"
MINE = "(my project)"

SYSTEM_PROMPT = f"""You edit one section of a GitHub profile README.

The section is the heading {HEADING} followed by one bullet per repo, in this form:
- [repo name](repo url): what the project is. What I did in it.
Contributions to other people's projects come first. Repos I created come last,
marked with "{MINE}" right after the link, and only say what the project is.

You get the current section and a list of new items. Return the updated section.

Rules:
- An item for a repo that already has a bullet goes into that bullet. Only add
  a bullet for a repo that doesn't have one yet, in the right place of the order.
- Leave bullets alone, word for word, when the new items add nothing to them,
  including when a bullet already describes an item. Don't restate or pad.
- Describe what the project is and what the work does for its users, not commit
  titles. Plain and specific, first person ("I added ..."), no hype, no emoji.
- Use only the URLs you are given.
- Skip trivial items (license year bumps, typo fixes, CI tweaks) when they don't
  add anything worth telling a visitor. Leaving the section unchanged is fine.
- Never invent facts that aren't in the input.
- Output only the section markdown: the heading and its bullets.
  No markers, no code fences, no commentary."""


def load_json(path):
    with open(path) as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def github_token():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        token = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True).stdout.strip()
    return token


def gh(path, **params):
    url = "https://api.github.com" + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={
        "Authorization": "Bearer " + github_token(),
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


_repo_cache = {}


def repo_info(full_name):
    if full_name not in _repo_cache:
        r = gh(f"/repos/{full_name}")
        _repo_cache[full_name] = {"description": r.get("description") or "", "stars": r["stargazers_count"]}
    return _repo_cache[full_name]


def collect(config):
    """Every item that could belong in the section, keyed by a stable id."""
    user, items = config["user"], {}

    for r in gh(f"/users/{user}/repos", type="owner", per_page=100):
        if r["fork"] or r["private"] or r["archived"]:
            continue
        items["repo:" + r["full_name"]] = {
            "kind": "my repo",
            "repo": r["full_name"],
            "url": r["html_url"],
            "title": r["name"],
            "description": r.get("description") or "",
            "stars": r["stargazers_count"],
        }

    prs = gh("/search/issues", q=f"author:{user} is:pr is:merged -user:{user}", per_page=100)
    for pr in prs["items"]:
        repo = pr["repository_url"].split("/repos/", 1)[1]
        items[pr["html_url"]] = {
            "kind": "merged PR",
            "repo": repo,
            "url": pr["html_url"],
            "title": pr["title"],
            "body": (pr.get("body") or "")[:400],
            "date": pr["closed_at"][:10],
        }

    # Maintainers sometimes fold a contribution into their own commit and credit
    # it with a Co-authored-by trailer instead of merging the PR.
    commits = gh("/search/commits", q=f'"Co-authored-by: {config["name"]}" -user:{user}', per_page=100)
    for c in commits["items"]:
        message = c["commit"]["message"]
        if f"{user}@users.noreply.github.com" not in message:
            continue
        repo = c["repository"]["full_name"]
        pulls = gh(f"/repos/{repo}/commits/{c['sha']}/pulls")
        if any(p["user"]["login"] == user for p in pulls):
            continue  # squash-merge of one of my PRs, already counted above
        items[c["html_url"]] = {
            "kind": "commit crediting me as co-author",
            "repo": repo,
            "url": c["html_url"],
            "title": message.split("\n", 1)[0],
            "date": c["commit"]["committer"]["date"][:10],
        }

    ignored_repos, ignored_items = set(config["ignore_repos"]), set(config["ignore_items"])
    return {k: v for k, v in items.items() if v["repo"] not in ignored_repos and k not in ignored_items}


def split_readme(text):
    head, rest = text.split(START, 1)
    section, tail = rest.split(END, 1)
    return head, section.strip(), tail


def describe(items):
    lines = []
    for item in items:
        repo = item["repo"]
        if item["kind"] != "my repo":
            info = repo_info(repo)
            item.setdefault("description", info["description"])
            item.setdefault("stars", info["stars"])
        lines.append(f"- {item['kind']} in {repo} (https://github.com/{repo}, "
                     f"{item['stars']} stars): {item['description']}")
        if item["kind"] != "my repo":
            lines.append(f"  {item['title']} ({item['url']}, {item['date']})")
            if item.get("body"):
                lines.append("  " + " ".join(item["body"].split()))
    return "\n".join(lines)


def links(markdown):
    return set(re.findall(r"\]\((https?://[^)\s]+)\)", markdown))


def call_model(config, section, new_items):
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        return None, "OPENROUTER_API_KEY is not set"
    prompt = f"Current section:\n\n{section}\n\nNew items:\n\n{describe(new_items)}"
    errors = []
    for model in config["models"]:
        body = json.dumps({
            "model": model,
            "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}],
            "temperature": 0.3,
        }).encode()
        req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=body, headers={
            "Authorization": "Bearer " + key,
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/" + config["user"],
            "X-Title": "profile README updater",
        })
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                answer = json.load(resp)
            text = answer["choices"][0]["message"]["content"] or ""
        except (urllib.error.URLError, KeyError, IndexError, ValueError) as e:
            detail = e.read().decode()[:300] if isinstance(e, urllib.error.HTTPError) else str(e)
            errors.append(f"{model}: {detail}")
            continue
        text = re.sub(r"^```(?:markdown|md)?\s*|\s*```$", "", text.strip())
        problem = check(text, section, new_items)
        if problem:
            errors.append(f"{model}: rejected output, {problem}")
            continue
        return text, model
    return None, "; ".join(errors)


def check(text, section, new_items):
    """Why the model's section can't be used, or None if it can."""
    if not text.startswith(HEADING):
        return "it doesn't start with the heading"
    bullets = [line for line in text.splitlines() if line.startswith("- ")]
    if not bullets or not all(line.startswith("- [") for line in bullets):
        return "a bullet doesn't start with the repo link"
    mine = [MINE in line for line in bullets]
    if mine != sorted(mine):
        return "my own projects aren't last"
    if START in text or END in text:
        return "it contains the markers"
    if len(text) > 2 * len(section) + 800:
        return "it's much longer than the current section"
    allowed = links(section) | {i["url"] for i in new_items} | {"https://github.com/" + i["repo"] for i in new_items}
    unknown = links(text) - allowed
    if unknown:
        return "it links to URLs it wasn't given: " + ", ".join(sorted(unknown))
    return None


def fallback(section, new_items):
    """No model available: add plain bullets for review to finish by hand."""
    lines = section.splitlines()
    first_mine = next((n for n, line in enumerate(lines) if MINE in line), len(lines))
    theirs, mine = {}, []
    for i in new_items:
        if i["kind"] == "my repo":
            mine.append(f"- [{i['title']}]({i['url']}) {MINE}: {i['description']}")
        else:
            theirs.setdefault(i["repo"], []).append(i["title"])
    theirs = [f"- [{repo.split('/')[1]}](https://github.com/{repo}): {'; '.join(titles)}"
              for repo, titles in theirs.items()]
    return "\n".join(lines[:first_mine] + theirs + lines[first_mine:] + mine)


def pr_body(new_items, model, error, changed):
    lines = ["Found since the last update:", ""]
    for i in new_items:
        lines.append(f"- {i['kind']}: [{i['title']}]({i['url']})" + ("" if i["kind"] == "my repo" else f" in `{i['repo']}`"))
    lines.append("")
    if model:
        lines.append(f"Section rewritten by `{model}` on OpenRouter. Edit the wording in this PR before merging if needed.")
    else:
        lines.append(f"No model output was usable ({error}), so these are plain bullets to rewrite by hand.")
    if not changed:
        lines.append("\nThe README is unchanged: nothing above was worth mentioning. Merge to mark these items as seen.")
    lines += ["", "Merging also records these items in `.github/readme-bot/state.json` so they aren't proposed again. "
              "To reject one for good, close this PR and add its id to `ignore_items` (or its repo to `ignore_repos`) "
              "in `.github/readme-bot/config.json`."]
    return "\n".join(lines) + "\n"


def set_output(name, value):
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a") as f:
            f.write(f"{name}={value}\n")


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    config, state = load_json(CONFIG), load_json(STATE)
    items = collect(config)

    if mode == "--seed":
        state["seen"] = sorted(set(state["seen"]) | set(items))
        save_json(STATE, state)
        print(f"Marked {len(items)} items as seen.")
        return

    seen = set(state["seen"])
    forget = os.environ.get("FORGET", "").strip()  # for test runs: treat matching ids as new again
    if forget:
        seen = {k for k in seen if forget not in k}
    new_items = [items[k] for k in sorted(items) if k not in seen]
    if not new_items:
        print("Nothing new.")
        set_output("changed", "false")
        return
    print("New:\n" + "\n".join(f"  {i['kind']}: {i['title']} ({i['url']})" for i in new_items))
    if mode == "--dry-run":
        return

    with open(README) as f:
        head, section, tail = split_readme(f.read())
    text, model = call_model(config, section, new_items)
    error = None
    if text is None:
        error, model = model, None
        print("Model step failed, using plain bullets: " + error)
        text = fallback(section, new_items)
    else:
        print("Section written by " + model)

    with open(README, "w") as f:
        f.write(f"{head}{START}\n{text.strip()}\n{END}{tail}")
    state["seen"] = sorted(seen | {k for k in items if k not in seen})
    save_json(STATE, state)
    with open(PR_BODY, "w") as f:
        f.write(pr_body(new_items, model, error, text.strip() != section))
    set_output("changed", "true")


if __name__ == "__main__":
    main()
