def parse_ua(s, always_include_os=False):
    """ Parse the given user-agent string and return a string of the
    form "client - os". Use x.partition(' - ') if needed. The
    client is "Browser" if unknown. The os is "Other" if unknown and
    may contain a string "Mobile", "Tablet" or "Desktop. When the ua
    does not represent a browser (but e.g. a bot or wget) the os is
    omitted.

    This function is less precise than https://github.com/ua-parser/uap-python,
    in that it marks rare browsers as either "Browser" or as the browser
    that it's based upon (e.g. IceWeasel becomes Firefox). It also marks
    all bots as simply "Bot" and does not care about TV's that have a
    browser. Other than that, this function is quite accurate and passes
    ua-parser's test suite.

    If you can live with the above restrictions (you probably can if
    you're using this to e.g. monitor your website's traffic) then use
    this function: it's over 100 times faster that ua_parser! Also, it
    wont ever raise an exception.
    """
    s = str(s)
    ls = s.lower()
    is_browser = s.startswith("Mozilla/5")
    client = opsys = device_type = ""

    if not is_browser:
        # This is a bot or something like wget (or a weird/old browser)
        client = "Other"
        if "bot" in ls or "crawl" in ls or "spider" in ls or "scrap" in ls:
            client = "Bot"
        elif "indexer" in ls or "pinger" in ls or "monitor" in s:
            client = "Bot"
        elif "facebook" in ls or "google" in ls or "Argus" in s:
            client = "Bot"

    elif "bot" in ls or "crawl" in ls or "scraper" in ls or "spider" in ls:
        # This is a bot pretending to be a browser
        is_browser = False
        client = "Bot"

    else:
        # This is a browser, try to detect which one!
        client = "Browser"

        if "Firefox" in s:
            # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/User-Agent/Firefox
            client = "Firefox"
            if "Gecko/20100101" in s:
                # On Desktop, geckotrail is the fixed string "20100101"
                device_type = "Desktop"
            else:
                # Mobile!
                device_type = "Mobile"
                if "Mobi" in s:
                    device_type = "Mobile"  # but now we're sure :)
                elif "Tablet" in s:
                    device_type = "Tablet"
            # Some clients include Firefox for compat
            # Some are based on Firefox. Perhaps we should just call them FF
            if "Trident" in s:
                client = "IE"
            # elif "PaleMoon" in s:
            #     client = "Pale Moon"
            # elif "SailfishBrowser" in s:
            #     client = "Sailfish Browser"
            # elif "IceWeasel" in s:
            #     client = "IceWeasel"
            # elif "Waterfox" in s:
            #     client = "Waterfox"
            # elif "Basilisk" in s:
            #     client = "Basilisk"
        elif "Edge" in s:
            client = "Edge"
        elif "Chrom" in s:
            # https://developer.chrome.com/multidevice/user-agent
            # Note that "Safari" is also present, so check for Chrome first
            client = "Chrome"
            if "HeadlessChrome" in s:
                client = "HeadlessChrome"  # Can be Chrome or Chromium based
            elif "Chromium" in s:
                client = "Chromium"
            elif "Brave" in s:
                client = "Brave"
            elif "OPR" in s:
                client = "Opera"  # put here because it includes Chrome for compat
            elif "Silk" in s:
                client = "Silk"
        elif "Safari" in s:
            client = "Safari"
            if "FxiOS" in s:
                client = "Firefox"
            elif "CriOS" in s:
                client = "Chrome"
            elif "Coast" in s or "OPiOS" in s:
                client = "Opera"
            elif "Silk" in s:
                client = "Silk"
        elif "IE" in s or "Trident" in s:
            client = "IE"

        if not device_type and "mobi" in ls:
            device_type = "Mobile"

    # Try to detect the OS if this is a browser
    if is_browser or always_include_os:
        opsys = "Other"
        if "Windows" in s:
            opsys = "Windows"
            if "X11" in s:
                opsys = "Chrome OS"  # WTF
            if not device_type:
                if "Zune" in s or "Phone" in s:
                    device_type = "Mobile"
        elif "Android" in s:
            opsys = "Android"
            if "iOS" in s:
                opsys = "iOS"
        elif "Silk-Accelerated" in s:
            opsys = "Android"
        elif "BSD" in s:
            opsys = "BSD"  # includes FreeBSD, NetBSD and OpenBSD
        elif "Kindle" in s:  # check before Linux
            opsys = "Kindle"
        elif "Linux" in s:
            opsys = "Linux"
            if "Sailfish" in s:
                opsys = "Sailfish"  # Adroidish os
            elif "Mobile" in s or "UCW" in s:
                opsys = "Android"
            elif "Philips" in s or "Sony" in s or "LG" in s:
                opsys = "Other"
            elif "TV" in s or "wOSBrowser" in s or "WeTab" in s or "CrKey" in s:
                opsys = "Other"
            elif "Maemo" in s:
                opsys = "Other"
        elif "SunOS" in s:
            opsys = "Solaris"
        elif "iOS" in s:
            opsys = "iOS"
        elif "iP" in s and ("iPad" in s or "iPod" in s or "iPhone" in s):
            opsys = "iOS"
        elif "Mac" in s:
            opsys = "Mac OS X"
            if "Mac_PowerPC" in s:
                opsys = "Mac OS"
            elif "Apple TV" in s:
                opsys = "Other"
        elif "Darwin" in s:
            if "86" in s:  # x86 or i86
                opsys = "Mac OS X"
            else:
                opsys = "iOS"
        elif "Nokia" in s:
            opsys = "Nokia"
        elif "BB10" in s or "BlackBerry" in s:
            opsys = "BlackBerry OS"
        elif "PlayBook" in s:
            opsys = "BlackBerry Tablet OS"

    # Return as str
    if device_type:
        opsys = opsys + " " + device_type
    if opsys:
        client = client + " - " + opsys
    return client
