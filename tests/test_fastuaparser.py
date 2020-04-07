import os
import json
import time

from testutils import run_tests

from mypaas.stats.fastuaparser import parse_ua

ua_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ua_data.json")


# Some uas queried with my machine
uas = {
    "Firefox": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:66.0) Gecko/20100101 Firefox/66.0",
    "Chrome": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.103 Safari/537.36",
    "Edge": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.140 Safari/537.36 Edge/17.17134",
    "IE": "Mozilla/5.0 (Windows NT 10.0; WOW64; Trident/7.0; rv:11.0) like Gecko",
}


# Clients based on Firefox that we chose to consider "Firefox"
firefox_like = "Pale Moon", "IceWeasel", "Waterfox", "Sailfish Browser", "Basilisk"

ie_like = "QQ Browser", "AOL"

# Clients that are ok if we call them "Browser"
browser_like = ("Pale Moon",)

clients_of_interest = (
    "Firefox",
    "Chrome",
    "Chromium",
    "Android browser",
    "Edge",
    "IE",
    "Safari",
    "Opera",
    "Brave",
    "Silk",
)

# Some ua's dont start with Mozilla/5, these are either ancient browsers
# or (old?) Opera browsers on certain devices.
silly_ua_starts = (
    "Mozilla/4",
    "Opera",
    "(Opera",
    "HTC",
    "LG",
    "Samsung",
    "SAMSUNG",
    "Safari",
)

# Some bots that we sometimes mark as Other, or Bot, or Firefox, or ...
crap_bots = (
    "Google-HTTP-Java-Client",
    "Daumoa",
    "Daumoa-feedfetcher",
    "Facebook",
    "Box Sync",
    "Google",
    "Web-sniffer",
    "WebPageTest.org bot",
)

# If any of these words are present in the ref client name, we consider it a bot
bot_hints = "bot", "crawl", "spider", "preview", "scraper"

# Names of bots that are not detected by the above. We just call all these "Bot"
bot_like = """
008, 50.nu, A6-Indexer, Aboundex, Accoona-AI-Agent, Accoona-Biz-Agent,
Altresium, Android, Ant-Nutch, AppEngine-Google, Argus, Ask Jeeves, Axtaris,
BaiduMobaider, BoardReader, BoardReader Blog Indexer, Checklinks, DNSGroup,
EDI, Flamingo_SearchEngine, GmailImageProxy, Goodzer, GoogleImageProxy, Grub,
HiddenMarket, HooWWWer, INGRID, IconSurf, IlTrovatore, Infohelfer, InfuzApp,
InternetArchive, Isara, Kraken, Kurzor, LEIA, LOOQ, LinkAider, Llaut,
Mediapartners-Google, NewsGator, Nutch, Nutch; http:, NutchCVS, NutchOSUOSL,
NutchOrg, ObjectsSearch, Orbiter, Other, PagesInventory, PathDefender,
PaxleFramework, Peew, PostPost, RedCarpet, Scrapy, ShopSalad, Simpy,
Slack-ImgProxy, Steeler, Tailsweep, Thumbshots.ru, VSE, Vagabondo, WIRE,
WebCrunch, WebIndexer, WebZIP, Wotbox, Y!J-BRI, Y!J-BRW, YahooSeeker, Yeti,
Yowedo, Zao, ZyBorg, aws-cli, boitho.com-dc, clumboot, envolk, gonzo1,
grub-client, heritrix, holmes, ichiro, ichiro/mobile, mozDex,
semanticdiscovery, sproose, voyager, wminer, www.almaden.ibm.com,
Charlotte
"""
bot_like = [x.strip() for x in bot_like.strip().replace("\n", " ").split(", ")]

linux_like = "Debian", "Ubuntu", "Mandriva", "Gentoo", "Red Hat"
bsd_like = "OpenBSD", "FreeBSD", "NetBSD"

nokia_like = (
    "MeeGo",
    "Nokia Series 40",
    "Other",
    "Symbian OS",
    "Symbian^3",
    "Symbian^3 Anna",
    "Symbian^3 Belle",
    "Nokia Series 30 Plus",
)


oses_not_of_interest = (
    "Bada",
    "Brew",
    "BREW",
    "Brew MP",
    "Symbian OS",
    "VRE",
    "webOS",
    "WebTV",
    "Samsung",
    "Philips",
    "LG",
    "Sony",
    "webOS",
    "WeTab",
    "Panasonic",
    "FireHbbTV",
    "Maemo",
    "GoogleTV",
    "ATV OS X",
    "tvOS",
    "Roku",
    "Web0S",
    "Tizen",
    "Chromecast",
    "Firefox OS",
)


def test_parse_ua_basics():

    # Does not raise
    assert parse_ua(None) == "Other"
    assert parse_ua("") == "Other"
    assert parse_ua(4) == "Other"

    # Check for common ua's
    for browser, ua in uas.items():
        assert parse_ua(ua) in (browser + " - Windows", browser + " - Windows Desktop")

    # Check that this first bit is important
    for browser, ua in uas.items():
        assert parse_ua(ua[1:]) == "Other"
        assert parse_ua("x" + ua) == "Other"

    # Unknown browsers are called "Browser
    assert parse_ua("Mozilla/5.0 (Linux) X") == "Browser - Linux"
    assert parse_ua("Mozilla/5.0 (Y) X") == "Browser - Other"

    # Unknown os's are called "Other"
    for browser, ua in uas.items():
        assert parse_ua(ua.replace("Win", "Loose")) in (
            browser + " - Other",
            browser + " - Other Desktop",
        )

    # We detect bots
    for browser, ua in uas.items():
        assert parse_ua(ua + "bot") == "Bot"

    # ... in several ways
    for ua in ("xxspider", "crawlee", "scrapy", "indexeroo"):
        assert parse_ua(ua) == "Bot"


def speedometer():
    # Read test data
    with open(ua_file, "rb") as f:
        cases = json.loads(f.read().decode())

    # Read as fast as we can
    t0 = time.perf_counter()
    for case in cases:
        parse_ua(case["ua"])
    t1 = time.perf_counter()
    print(len(cases), "ua strings in", t1 - t0, "s")


def test_parseua_client():

    # Read test data
    with open(ua_file, "rb") as f:
        cases = json.loads(f.read().decode())
    cases = [case for case in cases if case.get("client", None)]

    # Some more preparations
    clientmap = {}
    for case in cases:
        ref_client = case["client"]
        for x in clients_of_interest:
            if x in ref_client:
                clientmap[ref_client] = x
                break
    for x in firefox_like:
        clientmap[x] = "Firefox"
    for ign in (
        "Mail.ru Chromium Browser",
        "Firefox (Shiretoko)",
        "Mobile Safari UI/WKWebView",
        "HeadlessChrome",
        "Opera Neon",
    ):
        clientmap.pop(ign)

    # Test client
    for case in cases:
        s = case["ua"]
        ref_client = case["client"]
        ref_alias = clientmap.get(ref_client, None)
        client, _, os = parse_ua(s).partition(" - ")
        if client != ref_client:
            if ref_client in crap_bots:
                pass
            elif client == "Bot" and any(x in ref_client.lower() for x in bot_hints):
                pass  # The ref client really looks like a bot
            elif client == "Bot" and ref_client in bot_like:
                pass  # We've marked this ref client as a bot
            elif ref_alias is None and client in ("Other", "Browser"):
                pass  # A browser that we're not interested in
            elif client == ref_alias:
                pass  # alias, we use simpler names (are less specific)
            elif client == "Other" and s.startswith(silly_ua_starts):
                pass  # Some real old browser, meh
            elif client == "Browser" and ref_client in browser_like:
                pass
            elif ref_client == "Android" and client in ("Safari", "Chrome"):
                pass  # builtin android browser is based on either
            elif client == "Chrome" and ref_alias is None:
                pass  # A Chrome-based browser, these include Electron apps
            elif client == "Safari" and ref_alias is None:
                pass  # A Safari based browser
            elif client == "IE" and ref_client in ie_like:
                pass
            else:
                assert False, (client, ref_client)


def test_parse_ua_os():

    # Read test data
    with open(ua_file, "rb") as f:
        cases = json.loads(f.read().decode())
    cases = [case for case in cases if case.get("os", None)]

    # Test os
    for case in cases:
        s = case["ua"]
        ref_os = case["os"]
        client, _, os = parse_ua(s, True).partition(" - ")
        os = os.replace(" Mobile", "").replace(" Tablet", "").replace(" Desktop", "")
        ref_os = (
            ref_os.replace(" Mobile", "").replace(" Tablet", "").replace(" Phone", "")
        )
        if os != ref_os:
            if os == "Linux" and ref_os in linux_like:
                pass
            elif os == "BSD" and ref_os in bsd_like:
                pass
            elif os == "Nokia" and ref_os in nokia_like:
                pass
            elif os == "Other" and (s.startswith("Wget") or s.startswith("curl")):
                pass  # These use lowercase for Linux/BSD, meh
            elif os == "Other" and s.startswith("SalesforceMobileSDK"):
                pass  # Special case
            elif os == "Other" and ref_os in oses_not_of_interest:
                pass
            else:
                assert False, (os, ref_os)
        else:
            pass


if __name__ == "__main__":
    run_tests(globals())
    # speedometer()
