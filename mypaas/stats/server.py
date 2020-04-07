"""
The logic to serve the stats dashboard.

MyPaas sitemap:

    /           -> dashboard home, showing server stats, and links
    /dashboard  -> the Traefik dashboard (hosted by Traefik)
    /stats      -> stat pages, select categories via query params
    /daemon     -> very basic daemon info page (hosted by daemond)

"""

import os
import json
import time
import asyncio
import platform

import psutil
import pscript
import asgineer

from .client_style import CSS


START_TIME = time.time()
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(THIS_DIR, "client_code.py"), "rb") as f:
    JS = pscript.py2js(f.read().decode())


static_assets = {"style.css": CSS, "client.js": JS}
asset_handler = asgineer.utils.make_asset_handler(static_assets)


async def stats_handler(request, collector):
    """ The main http handler to serve stats data.
    """

    if request.method != "GET":
        return 405, {}, "invalid method"

    if request.path == "/":
        categories = collector.get_categories()
        links = [
            f"<a href='/stats?categories={cat}'>{cat} stats</a>" for cat in categories
        ]
        html = MAIN_HTML_TEMPLATE
        html = html.replace("{LINKS}", "<br>".join(links))
        html = html.replace("{INFO}", get_system_info())
        html = html.replace("{INFO-STREAM}", get_system_info_stream())
        return 200, {}, html

    if request.path == "/stats":
        categories = request.querydict.get("categories", "")
        categories = [cat.strip() for cat in categories.split(",") if cat.strip()]
        ndays = request.querydict.get("ndays", "")
        daysago = request.querydict.get("daysago", "")
        if categories:
            return get_webpage(
                collector, ndays, daysago, categories, title="MyPaas Monitor"
            )
        else:
            return 302, {"Location": "/"}, b""

    elif request.path == "/statsget":

        quickstats = {"uptime": _uptime()}

        cpu = collector.get_latest_value("system", "sys cpu|num|%")
        if cpu:
            quickstats["cpu"] = f"{cpu:0.1f} %"
        mem = collector.get_latest_value("system", "sys mem|num|iB")
        if mem:
            quickstats["mem"] = f"{mem/2**30:0.3f} GiB"
        disk = collector.get_latest_value("system", "sys disl|num|iB")
        if disk:
            quickstats["disk"] = f"{disk/2**30:0.3f} GiB"
        open = collector.get_latest_value("system", "open connections|num")
        if open:
            quickstats["open"] = f"{open}"

        return 200, {}, quickstats

    # elif request.path == "/statstream":
    #     # print("starting stat stream")
    #     raise NotImplementedError("Asigneer does not properly close streams.")
    #     # return 200, {"content-type": "text/plain"}, stat_streamer()

    else:
        fname = request.path.split("/")[-1]
        return await asset_handler(request, fname)


async def stat_streamer():
    # eek, asgineer does not seem to stop this when the connection is closed by the client
    while True:
        await asyncio.sleep(1.0)
        t = asyncio.Task.current_task()
        print("sending at ", time.time(), id(t))
        yield f"hi {time.time()}"


def get_webpage(collector, ndays, daysago, categories, title=None, extra_info=None):
    """ Generate a webpage with aggegation data from ndays1 ago to
    ndays2 ago (the order does not matter). Returns an complete html
    document as a string.

    Note that this call performs sync queries to a database, so you
    might want to asyncify the calling of this method.
    """
    # Query data, dump to json, and sanitize
    ndays, daysago = _normalize_ndays_and_daysago(ndays, daysago)
    # todo: we could asyncify this call. But only admins watch this page so ...
    data = json.dumps(collector.get_data(categories, ndays, daysago))
    data = data.replace("<", "&lt;").replace(">", "&gt;")
    info = {}  # adding info here will make it display as the first panel
    # Build page
    html = STATSVIEW_HTML_TEMPLATE.replace("{TITLE}", title or "Monitor")
    html = html.replace("{NDAYS}", str(ndays)).replace("{DAYSAGO}", str(daysago))
    html = html.replace("{INFO}", json.dumps(info))
    html = html.replace("{DATA_PER_DB}", data)
    return html


def get_system_info():
    info = {
        "server name": str(platform.node()),
        "server platform": str(platform.platform()),
        "server cpu-count": str(psutil.cpu_count()),
        "server mem": f"{psutil.virtual_memory().total / 2**30:0.1f} GiB",
        "server disk": f"{psutil.disk_usage('/').total / 2**30:0.1f} GiB",
    }
    html = "<table>"
    for key, value in info.items():
        html += f"<tr><td>{key}</td><td>{value}</td></tr>"
    html += "</table>"
    return html


def get_system_info_stream():
    info = {
        "": "&nbsp;" * 30,
        "system uptime": "<span id='info-uptime' />",
        "CPU usage": "<span id='info-cpu' />",
        "mem usage": "<span id='info-mem' />",
        "disk usage": "<span id='info-disk' />",
        "open connections": "<span id='info-open' />",
    }
    html = "<table>"
    for key, value in info.items():
        html += f"<tr><td>{key}</td><td>{value}</td></tr>"
    html += "</table>"
    return html


def _uptime():
    nsecs = time.time() - START_TIME
    if nsecs >= 3 * 86400:
        return f"{nsecs / 86400:0.1f} days"
    elif nsecs >= 3 * 3600:
        return f"{nsecs / 3600:0.1f} hours"
    elif nsecs >= 3 * 60:
        return f"{nsecs / 60:0.1f} minutes"
    else:
        return f"{nsecs:0.0f} seconds"


def _normalize_ndays_and_daysago(ndays, daysago):
    ndays = int(float(ndays)) if ndays else 3
    daysago = int(float(daysago)) if daysago else 0
    return max(1, ndays), max(0, daysago)


MAIN_HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>MyPaas dashboard</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="stylesheet" href="style.css">
</head>
<body>

<script>
var statgetter = function () {
    fetch('/statsget')
        .then(function(response) {
            return response.json();
        }).then(function(data) {
            for (key in data) {
                var el = document.getElementById("info-" + key);
                if (el) {
                    el.innerHTML = data[key];
                }
            }
        });
    setTimeout(statgetter, 1000);
};
setTimeout(statgetter, 10);
</script>

<h1>MyPaas dashboard</h1>

<h2>System info</h2>
<div class="panelcontainer">
    <div class="panel"> <div class="content">
    {INFO}
    </div></div>
    <div class="panel"> <div class="content">
    {INFO-STREAM}
    </div></div>
</div>

<h2>Stats</h2>

<p style='font-size: 120%; line-height: 160%'>
<a href='/dashboard'>Traefik dashboard (router status)</a>
<br />
{LINKS}
</p>

</body>
</html>
""".lstrip()


STATSVIEW_HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>{TITLE}</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="stylesheet" href="style.css">
</head>
<body>

<script>
var text_color = "#BBB";
var info = {INFO};
var data_per_db = {DATA_PER_DB};
var ndays = {NDAYS};
var daysago = {DAYSAGO};
</script>
<script src='client.js'></script>

<div id='topbar' class='topbar'>
<a href='/'><b>{TITLE}</b></a>&nbsp;&nbsp;
<div style='display:inline-block;'>
Showing
<a href="javascript:update_range('zoomin');"> ◀ </a>
{NDAYS}
<a href="javascript:update_range('zoomout');"> ▶ </a>
days
</div> <div style='display:inline-block;'>
until
<a href="javascript:update_range('newer');"> ◀ </a>
{DAYSAGO}
<a href="javascript:update_range('older');"> ▶ </a>
days ago.
</div>

&nbsp; &nbsp;
<a href="javascript:toggle_columns();">compact/wide panels</a>
<a href="javascript:toggle_utc();">utc/local time</a>
</div>

</body>
</html>
""".lstrip()
