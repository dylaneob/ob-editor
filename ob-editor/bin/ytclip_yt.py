#!/usr/bin/env python3
"""How many views a long-form got from Instagram (and Shorts) since a date: the "does the clip send people to the full video"
half of ytclip's Monday review. YouTube Analytics, read only, OB's own sign-in (~/ob-youtube).
  ~/ob-youtube/.venv-google/bin/python ytclip_yt.py VIDEO_ID SINCE(YYYY-MM-DD)   -> JSON on stdout"""
import datetime, json, os, sys

sys.path.insert(0, os.path.expanduser("~/ob-youtube"))
import yt_analytics as YA   # noqa: E402
from googleapiclient.discovery import build   # noqa: E402

vid, since = sys.argv[1], sys.argv[2]
ya = build("youtubeAnalytics", "v2", credentials=YA.load(), cache_discovery=False)
q = lambda **kw: ya.reports().query(ids="channel==MINE", startDate=since, endDate=str(datetime.date.today()), **kw).execute().get("rows") or []
by_type = q(metrics="views", dimensions="insightTrafficSourceType", filters=f"video=={vid}")
ext = q(metrics="views", dimensions="insightTrafficSourceDetail", filters=f"video=={vid};insightTrafficSourceType==EXT_URL", maxResults=25, sort="-views")
daily = q(metrics="views", dimensions="day", filters=f"video=={vid}")
ig = sum(v for d, v in ext if "instagram" in str(d).lower())
print(json.dumps(dict(video=vid, since=since, views=sum(v for d, v in daily), by_source={k: v for k, v in by_type},
                      external_top=ext[:10], instagram_views=ig, shorts_views=dict(by_type).get("SHORTS", 0), daily=daily)))
