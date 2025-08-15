import os, sys, requests, datetime as dt
from dateutil import tz

TOKEN = os.environ["GITHUB_TOKEN"]
LOGIN = os.environ.get("GH_LOGIN", "miranda-1")
README_PATH = os.environ.get("README_PATH", "README.md")

API = "https://api.github.com/graphql"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}

QUERY = """
query($login:String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
          }
        }
      }
      totalCommitContributions
    }
  }
}
"""

def fetch_calendar(login: str):
    r = requests.post(API, json={"query": QUERY, "variables":{"login": login}}, headers=HEADERS, timeout=30)
    r.raise_for_status()
    data = r.json()
    if "errors" in data:
      raise RuntimeError(data["errors"])
    c = data["data"]["user"]["contributionsCollection"]
    cal = c["contributionCalendar"]
    total_commits = c["totalCommitContributions"]
    days = []
    for w in cal["weeks"]:
      for d in w["contributionDays"]:
        days.append({"date": d["date"], "count": d["contributionCount"]})
    days.sort(key=lambda x: x["date"])
    return days, total_commits

def last_n_days(days, n=14):
    cutoff = (dt.date.today() - dt.timedelta(days=n-1)).isoformat()
    return [d for d in days if d["date"] >= cutoff]

def group_by_weekday(days):
    wd = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
    out = {k: [] for k in wd}
    for d in days:
      y,m,dd = map(int, d["date"].split("-"))
      w = dt.date(y,m,dd).weekday()  # 0=Mon
      out[wd[w]].append((d["date"], d["count"]))
    return out

def month_summary(days):
    today = dt.date.today()
    month_prefix = today.strftime("%Y-%m-")
    this_month = [d for d in days if d["date"].startswith(month_prefix)]
    total = sum(x["count"] for x in this_month)
    media = total / max(1, len(this_month))
    return total, media, today.strftime("%B/%Y")

def make_table_recent(days):
    rows = ["| Data | Commits |", "|:----:|:-------:|"]
    for d in reversed(days):
      rows.append(f"| {d['date']} | **{d['count']}** |")
    return "\n".join(rows)

def make_table_weekday(groups):
    header = "| Seg | Ter | Qua | Qui | Sex | Sáb | Dom |"
    sep = "|:---:|:---:|:---:|:---:|:---:|:---:|:---:|"
    sums = [sum(c for _,c in groups[k]) for k in ["Seg","Ter","Qua","Qui","Sex","Sáb","Dom"]]
    row = "| " + " | ".join(f"**{s}**" for s in sums) + " |"
    return "\n".join([header, sep, row])

def patch_readme(path, start_tag, end_tag, new_content):
    with open(path, "r", encoding="utf-8") as f:
      txt = f.read()
    start = txt.find(start_tag)
    end = txt.find(end_tag)
    if start == -1 or end == -1 or end < start:
      print("Marcadores não encontrados, criando seção...", file=sys.stderr)
      txt += f"\n\n{start_tag}\n{new_content}\n{end_tag}\n"
    else:
      txt = txt[:start+len(start_tag)] + "\n" + new_content + "\n" + txt[end:]
    with open(path, "w", encoding="utf-8") as f:
      f.write(txt)

def main():
    days, total_commits = fetch_calendar(LOGIN)
    last14 = last_n_days(days, 14)
    groups = group_by_weekday(last14)
    m_total, m_media, m_label = month_summary(days)

    t_recent = make_table_recent(last14)
    t_week = make_table_weekday(groups)

    resumo = (
      f"- **Commits no mês ({m_label})**: **{m_total}**\n"
      f"- **Média diária no mês**: **{m_media:.2f}** commits/dia\n"
      f"- **Total de commits (ano atual)**: **{total_commits}**\n"
    )

    blocao = (
      f"### 🔮 Últimos 14 dias\n\n{t_recent}\n\n"
      f"### 💜 Commits por dia da semana (últimos 14 dias)\n\n{t_week}\n"
    )

    patch_readme(README_PATH, "<!--COMMITS_TABLE_START-->", "<!--COMMITS_TABLE_END-->", blocao)
    patch_readme(README_PATH, "<!--COMMITS_SUMMARY_START-->", "<!--COMMITS_SUMMARY_END-->", resumo)

if __name__ == "__main__":
    main()
