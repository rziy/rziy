import datetime
import json
import os
import re
import sys
import urllib.request

API = "https://graphql.anilist.co"
README = "README.md"
START = "<!--ANILIST:START-->"
END = "<!--ANILIST:END-->"

USER = os.environ.get("ANILIST_USER", "").strip()
LIMIT = int(os.environ.get("LIMIT", "6"))

USER_QUERY = "query($name:String){ User(name:$name){ id } }"
ACTIVITY_QUERY = """
query($id:Int,$n:Int){
  Page(perPage:$n){
    activities(userId:$id, type:MEDIA_LIST, sort:ID_DESC){
      ... on ListActivity {
        status progress createdAt
        media { type siteUrl title { romaji english } }
      }
    }
  }
}
"""


def gql(query, variables):
    req = urllib.request.Request(
        API,
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "profile-readme-updater",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as res:
        return json.load(res)


def clean(text):
    return (text or "").replace("[", "(").replace("]", ")").strip()


def line(act):
    media = act.get("media") or {}
    title = clean((media.get("title") or {}).get("english") or (media.get("title") or {}).get("romaji") or "?")
    url = media.get("siteUrl") or "https://anilist.co"
    status = (act.get("status") or "").strip()
    status = status[:1].upper() + status[1:]
    progress = act.get("progress")
    date = datetime.datetime.fromtimestamp(act.get("createdAt") or 0, datetime.timezone.utc).strftime("%Y-%m-%d")
    middle = f" {progress} of" if progress else ""
    return f"- {date} · {status}{middle} [{title}]({url})"


def build(user):
    uid = gql(USER_QUERY, {"name": user})["data"]["User"]["id"]
    data = gql(ACTIVITY_QUERY, {"id": uid, "n": LIMIT * 3})
    acts = data["data"]["Page"]["activities"]
    acts = [a for a in acts if a and (a.get("media") or {}).get("type") == "ANIME"][:LIMIT]
    if not acts:
        return ""
    body = "\n".join(line(a) for a in acts)
    return f"## Aktivitas anime terbaru\n\n{body}\n\n---\n"


def main():
    if not USER or USER.startswith("ISI_"):
        print("ANILIST_USER belum diisi, dilewati.")
        return 0

    with open(README, encoding="utf-8") as f:
        text = f.read()
    if START not in text or END not in text:
        print("Penanda ANILIST tidak ditemukan di README.md")
        return 1

    block = build(USER)
    new = re.sub(
        re.escape(START) + r".*?" + re.escape(END),
        lambda _m: f"{START}\n{block}{END}",
        text,
        flags=re.DOTALL,
    )
    if new != text:
        with open(README, "w", encoding="utf-8") as f:
            f.write(new)
        print("README.md diperbarui.")
    else:
        print("Tidak ada perubahan.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
