"""
Python code that will be transpiled to JS to implement the client side.
"""

from pscript.stubs import window, document, undefined, Math, Date  # JS
from pscript.stubs import data_per_db, text_color  # are made available


panels = []


# %% Button callbacks


def toggle_utc():
    info = get_hash_info()
    if info.get("utc", False):
        info.pop("utc")
    else:
        info["utc"] = True
    return refresh(None, info)


def toggle_columns():
    info = get_hash_info()
    columns = info.get("columns", 0)
    if not columns:
        if window.document.body.clientWidth >= 1200:
            info["columns"] = 2
        else:
            info["columns"] = 1
    else:
        info.pop("columns")
    return refresh(None, info)


def update_range(action=""):

    ndays = window.ndays
    daysago = window.daysago
    if action == "zoomout":
        if ndays < 4:
            ndays += 1
        elif ndays < 10:
            ndays += 2
        elif ndays < 30:
            ndays += 5
        else:
            ndays += 10
    elif action == "zoomin":
        if ndays <= 4:
            ndays -= 1
        elif ndays <= 10:
            ndays -= 2
        elif ndays <= 30:
            ndays -= 5
        else:
            ndays -= 10
        ndays = max(1, ndays)
    elif action == "older":
        daysago += ndays
    elif action == "newer":
        daysago -= ndays

    info = get_query_info()
    info["ndays"] = ndays
    if daysago > 0:
        info["daysago"] = daysago
    else:
        info.pop("daysago", None)
    return refresh(info, None)


def refresh(self, query_info=None, hash_info=None):
    if query_info is None:
        query_info = get_query_info()
    if hash_info is None:
        hash_info = get_hash_info()

    url = window.location.origin + window.location.pathname
    encode_uri_component = window.encodeURIComponent
    if query_info:
        url += "?" + "&".join(
            [key + "=" + encode_uri_component(val) for key, val in query_info.items()]
        )
    if True:
        url += "#" + "&".join(
            [key + "=" + encode_uri_component(val) for key, val in hash_info.items()]
        )

    if url == window.location.href:
        window.location.reload()
    else:
        window.location.href = url
    return undefined


def panel_sort_func(x):
    t = x.split("|")[1]
    if t:
        t = {"num": "anum", "cat": "zcat"}.get(t, t)
    return (t + "|" + x).lower()


# %%


def on_init():

    for dbname, data in data_per_db.items():

        # Create panel container (and a title)
        title_el = document.createElement("div")
        container_el = document.createElement("div")
        title_el.innerText = dbname  # .replace("_", " ")
        title_el.classList.add("panelcontainertitle")
        container_el.classList.add("panelcontainer")
        document.body.appendChild(title_el)
        document.body.appendChild(container_el)

        if dbname == "system" and window.info:
            panels.append(InfoPanel(container_el, dbname, "info", "system info"))

        # Collect panel types
        panel_kinds = {}
        for i in range(len(data)):
            aggr = data[i]
            for key in aggr.keys():
                panel_kinds[key] = True

        # Sort the panel types - count, dcount, num, cat
        panel_kinds = panel_kinds.keys()
        panel_kinds.sort(key=panel_sort_func)

        # Create panels
        for i in range(len(panel_kinds)):
            key = panel_kinds[i]
            # Select panel class
            key_parts = key.split("|")
            if len(key_parts) == 2:
                name, type = key_parts
                unit = ""
            elif len(key_parts) == 3:
                name, type, unit = key_parts
            else:
                continue
            if type == "time":
                continue  # skip time info
            elif type == "count":
                title = "# " + name
                Cls = CountPanel  # noqa: N806
            elif type == "dcount":
                title = "# daily " + name
                Cls = DailyCountPanel  # noqa: N806
            elif type == "mcount":
                title = "# monthly " + name
                Cls = MonthlyCountPanel  # noqa: N806
            elif type == "cat":
                title = name + "'s"
                Cls = CategoricalPanel  # noqa: N806
            elif type == "num":
                title = name
                Cls = NumericalPanel  # noqa: N806
            else:
                window.console.warn(f"Don't know what to do with {key}")
                continue
            if unit:
                title = title + " " + unit
            # Create panel
            panel = Cls(container_el, dbname, key, title, unit)
            panels.append(panel)

    on_hash_change()  # calls on_resize()


def on_resize():
    window.setTimeout(_on_resize, 1)


def get_query_info():
    url = window.location.href
    q = ""
    if "?" in url:
        q = window.location.href.split("?", 1)[-1].split("#")[0]
    return get_dict_from_hash_or_query(q)


def get_hash_info():
    return get_dict_from_hash_or_query(window.location.hash.lstrip("#"))


def get_dict_from_hash_or_query(s):
    info = {}
    for s in s.split("&"):
        key, _, val = s.partition("=")
        if key and val:
            val = window.decodeURIComponent(val)
            if val.lower() == "true":
                val = True
            elif val.lower() == "false":
                val = False
            elif val in "0123456789":
                val = int(val)
            info[key] = val
        elif s:
            info[s] = True
    return info


def on_hash_change():
    info = get_hash_info()
    containers = document.getElementsByClassName("panelcontainer")

    columns = int(info.get("columns", "")) or 0
    if columns > 0:
        grid_template_columns = "auto ".repeat(columns)
    else:
        grid_template_columns = None

    height = int(info.get("height", "")) or 0
    if height > 0:
        grid_auto_rows = height + "px"
    else:
        grid_auto_rows = None

    for i in range(len(containers)):
        containers[i].style.gridAutoRows = grid_auto_rows
        containers[i].style.gridTemplateColumns = grid_template_columns

    on_resize()


def _on_resize():
    for panel in panels:
        if panel.canvas:
            # Get dimensions
            w = panel.node.clientWidth - 10
            h = panel.node.clientHeight - 35
            pixel_ratio = get_pixel_ratio(panel.canvas.getContext("2d"))
            # Set dimensions
            panel.canvas.style.width = w + "px"
            panel.canvas.style.height = h + "px"
            panel.canvas.width = w * pixel_ratio
            panel.canvas.height = h * pixel_ratio
            # Set some info on the object
            panel.pixel_ratio = pixel_ratio
            panel.width = w
            panel.height = h
        if panel.draw:
            panel.draw()


def get_pixel_ratio(ctx):
    """ Get the ratio of logical pixel to screen pixel.
    """
    PSCRIPT_OVERLOAD = False  # noqa

    dpr = window.devicePixelRatio or 1
    bsr = (
        ctx.webkitBackingStorePixelRatio
        or ctx.mozBackingStorePixelRatio
        or ctx.msBackingStorePixelRatio
        or ctx.oBackingStorePixelRatio
        or ctx.backingStorePixelRatio
        or 1
    )
    return dpr / bsr


def _create_tick_units():
    # Create tick units
    tick_units = []
    for e in range(-14, 14):
        for i in [10, 20, 25, 50]:
            tick_units.append(i * 10 ** e)
    return tick_units


_tick_units = _create_tick_units()


# def split_group(s, sep):
#     group, _, sub = s.partition(sep)
#     if len(sub) == 0:
#         return "", group
#     else:
#         return group, sub


class BasePanel:
    def __init__(self, container, dbname, key, title, unit):
        self.dbname = dbname
        self.key = key
        self.title = title
        self.unit = unit

        self.node = document.createElement("div")
        self.node.classList.add("panel")
        container.appendChild(self.node)

        self.titlenode = document.createElement("div")
        self.titlenode.classList.add("title")
        self.titlenode.innerText = title
        self.node.appendChild(self.titlenode)


class InfoPanel(BasePanel):
    def __init__(self, *args):
        super().__init__(*args)
        self.content = document.createElement("div")
        self.content.classList.add("content")
        self.node.appendChild(self.content)

        hider = document.createElement("div")
        hider.classList.add("scrollhider")
        self.node.appendChild(hider)

        self._create()

    def _create(self):
        PSCRIPT_OVERLOAD = False  # noqa
        if not window.info:
            return
        lines = []
        lines.append("<table>")
        for key, value in window.info.items():
            lines.append(f"<tr> <td>{key}</td> <td>{value}</td> </tr>")
        lines.append("</table>")
        self.content.innerHTML = "\n".join(lines)


class CategoricalPanel(InfoPanel):
    def _create(self):
        PSCRIPT_OVERLOAD = False  # noqa

        key = self.key

        # First aggregate
        data = data_per_db[self.dbname]
        totalcount = 0
        rows = {}
        for i in range(len(data)):
            aggr = data[i]
            meas = aggr.get(key, {})
            for k, v in meas.items():
                rows[k] = rows.get(k, 0) + v
                totalcount += v

        # Group so we can sort in a grouped fashion
        groups = {}
        group_counts = {}
        for key, count in rows.items():
            group, _, subkey = key.partition(" - ")
            groups.setdefault(group, []).append((subkey, count))
            group_counts[group] = group_counts.get(group, 0) + count
        group_counts = [(k, v) for k, v in group_counts.items()]

        # Sort groups and items inside the groupd
        group_counts.sort(key=lambda x: -x[1])
        for subs in groups.values():
            subs.sort(key=lambda x: -x[1])

        lines = []
        lines.append("<table>")
        for group, _ in group_counts:
            for sub, count in groups[group]:
                key = group + " - " + sub
                key = key.strip(" -")
                pct = 100 * count / totalcount
                lines.append(
                    f"<tr> <td>{pct:0.0f}%</td> <td>{count}</td> <td>{key}</td> </tr>"
                )
        lines.append("</table>")

        self.content.innerHTML = "\n".join(lines)


class PlotPanel(BasePanel):

    _values_are_integer = False

    def __init__(self, *args):
        super().__init__(*args)
        self.canvas = document.createElement("canvas")
        self.node.appendChild(self.canvas)

    def _draw_text(self, ctx, text, x, y, angle=0):
        PSCRIPT_OVERLOAD = False  # noqa
        ctx.save()
        ctx.translate(x, y)
        ctx.scale(1, -1)
        ctx.rotate(angle)
        ctx.fillText(text, 0, 0)
        ctx.restore()

    def _get_min_max(self):
        return 0, 1

    def _get_ticks(self, scale, mi, ma, min_tick_dist=40):
        PSCRIPT_OVERLOAD = False  # noqa
        # Inspired from flexx' PlotWidget, which took inspirartion from visvis

        # Get tick multipliers and unit modifier
        if self.unit == "iB":
            if ma >= 2 ** 30:
                mult, unit = 1 / 2 ** 30, "G"
            elif ma >= 2 ** 20:
                mult, unit = 1 / 2 ** 20, "M"
            elif ma >= 2 ** 10:
                mult, unit = 1 / 2 ** 10, "K"
            else:
                mult, unit = 1, ""
        else:
            if ma >= 10_000_000_000:
                mult, unit = 1 / 1_000_000_000, "G"
            elif ma >= 10_000_000:
                mult, unit = 1 / 1_000_000, "M"
            elif ma >= 10000:
                mult, unit = 1 / 1000, "K"
            elif ma < 0.0001:
                mult, unit = 1_000_000, "u"
            elif ma < 0.1:
                mult, unit = 1000, "m"
            else:
                mult, unit = 1, ""
        if self.unit in ("iB", "s"):
            title = self.title.replace(" " + self.unit, " " + unit + self.unit)
            self.titlenode.innerText = title
            unit = ""
        # Get tick unit
        is_int = self._values_are_integer
        for tick_unit in _tick_units:
            if is_int and str(tick_unit).indexOf(".") >= 0:
                continue
            if tick_unit * scale / mult >= min_tick_dist:
                break
        else:
            return []
        # Calculate tick values
        first_tick = Math.ceil(mi * mult / tick_unit) * tick_unit
        last_tick = Math.floor(ma * mult / tick_unit) * tick_unit
        ticks = {}
        t = first_tick  # t does not mean time here!
        while t <= last_tick:
            ticks[t / mult] = t
            t += tick_unit
        # Stringify
        for realt, t in ticks.items():
            if t == 0:
                s = "0"
            elif mult == 1 and is_int:
                s = str(int(t))
            else:
                s = t.toPrecision(4)  # t is already multiplied
                if "." in s:
                    while len(s) > 5 and s.endsWith("0"):
                        s = s[:-1]
            ticks[realt] = s + unit
        return ticks

    def draw(self):
        PSCRIPT_OVERLOAD = False  # noqa

        ctx = self.canvas.getContext("2d")

        # Prepare hidpi mode for canvas  (flush state just in case)
        for i in range(4):
            ctx.restore()
        ctx.save()
        ctx.scale(self.pixel_ratio, self.pixel_ratio)

        # Flip y-axis
        ctx.scale(1, -1)
        ctx.translate(0, -self.height)

        # Clear bg
        ctx.clearRect(0, 0, self.width, self.height)

        # Determine drawing area
        x0 = 45
        y0 = 35
        width = self.width - x0 - 15
        height = self.height - y0 - 5

        data = data_per_db[self.dbname]
        if len(data) == 0:
            return

        # Get bounding box
        t1 = data[0].time_start
        t2 = data[-1].time_stop
        mi, ma = self._get_min_max()
        if ma <= mi:
            return
        hscale = width / (t2 - t1)
        vscale = height / (ma - mi)

        unix_from_utc_tuple = Date.UTC  # avoid triggering new
        utc = get_hash_info().get("utc", False)
        xticks = {}

        # Prepare x ticks for hours (one hour is the smallest granularity)
        hourly_tick_units = (1, 3600), (2, 7200), (6, 21600)
        min_tick_dist = 60
        for nhours, tick_unit in hourly_tick_units:
            if tick_unit * hscale >= min_tick_dist:
                break
        else:
            tick_unit = 0
        #
        if tick_unit > 0:
            d = Date(t1 * 1000)
            if utc:
                tup = [
                    d.getUTCFullYear(),
                    d.getUTCMonth(),
                    d.getUTCDate(),
                    d.getUTCHours(),
                ]
                tup[-1] = nhours * int(tup[-1] / nhours)
                t = unix_from_utc_tuple(tup[0], tup[1], tup[2], tup[3]) / 1000
            else:
                tup = [d.getFullYear(), d.getMonth(), d.getDate(), d.getHours()]
                tup[-1] = nhours * int(tup[-1] / nhours)
                t = Date(tup[0], tup[1], tup[2], tup[3]).getTime() / 1000
            while t <= t2:
                if t >= t1:
                    d = Date(t * 1000)
                    if utc:
                        xticks[t] = f"{d.getUTCHours():02i}:{d.getUTCMinutes():02i}"
                    else:
                        xticks[t] = f"{d.getHours():02i}:{d.getMinutes():02i}"
                t += tick_unit

        # Prepare x ticks for days/months
        day_tick_units = (2, 1), (2, 2), (2, 5), (1, 1), (1, 2), (1, 3), (0, 365)
        min_tick_dist = 60
        for dindex, nsomething in day_tick_units:
            tick_unit = nsomething * [365 * 86400, 30 * 86400, 86400][dindex]
            if tick_unit * hscale >= min_tick_dist:
                break
        else:
            tick_unit = nsomething = 0
        #
        n_date_ticks = 0
        if nsomething > 0:
            d = Date(t1 * 1000)
            if utc:
                tup = [d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate()]
                tup[dindex] = nsomething * int(tup[dindex] / nsomething)
                t = unix_from_utc_tuple(tup[0], tup[1], tup[2]) / 1000
            else:
                tup = [d.getFullYear(), d.getMonth(), d.getDate()]
                tup[dindex] = nsomething * int(tup[dindex] / nsomething)
                t = Date(tup[0], tup[1], tup[2]).getTime() / 1000
            while t <= t2:
                if t >= t1:
                    n_date_ticks += 1
                    d = Date(t * 1000)
                    if utc:
                        dd = f"{d.getUTCDate():02i}"
                        mm = f"{d.getUTCMonth()+1:02i}"
                        yy = f"{d.getUTCFullYear()}"
                        xticks[t] = f"{dd}-{mm}-{yy}"
                    else:
                        dd = f"{d.getDate():02i}"
                        mm = f"{d.getMonth()+1:02i}"
                        yy = f"{d.getFullYear()}"
                        xticks[t] = f"{dd}-{mm}-{yy}"
                tup[dindex] += nsomething
                if utc:
                    t = unix_from_utc_tuple(tup[0], tup[1], tup[2]) / 1000
                else:
                    t = Date(tup[0], tup[1], tup[2]).getTime() / 1000
        #
        extra_x_tick = ""
        if n_date_ticks < 2:
            xtickskeys = xticks.keys()
            if len(xtickskeys) > 0 and hscale * (xtickskeys[0] - t1) < 30:
                xticks.pop(xtickskeys[0])
            d = Date(t1 * 1000)
            if utc:
                extra_x_tick = (
                    f"{d.getUTCFullYear()}-{d.getUTCMonth()+1:02i}-{d.getUTCDate():02i}"
                )
            else:
                extra_x_tick = (
                    f"{d.getFullYear()}-{d.getMonth()+1:02i}-{d.getDate():02i}"
                )

        # Prepare y ticks
        yticks = self._get_ticks(vscale, mi, ma, 25)  # text -> value

        # Prepare drawing
        ctx.lineWidth = 1

        # Draw grid lines
        ctx.strokeStyle = "rgba(128, 128, 128, 0.3)"
        ctx.beginPath()
        for v, text in yticks.items():
            y = y0 + (float(v) - mi) * vscale
            ctx.moveTo(x0, y)
            ctx.lineTo(x0 + width, y)
        ctx.stroke()

        # Draw x ticks
        ctx.strokeStyle = text_color
        ctx.fillStyle = text_color
        ctx.textAlign = "center"
        ctx.textBaseline = "top"  # middle
        ctx.beginPath()
        for t, text in xticks.items():
            x = x0 + (float(t) - t1) * hscale
            ctx.moveTo(x, y0)
            ctx.lineTo(x, y0 - 4)
        ctx.stroke()
        for t, text in xticks.items():
            x = x0 + (float(t) - t1) * hscale
            angle = 0  # -0.15 * Math.PI
            x = min(x, x0 + width - 15)
            self._draw_text(ctx, text, x, y0 - 10, angle)
        if extra_x_tick:
            ctx.textAlign = "left"
            ctx.textBaseline = "bottom"
            self._draw_text(ctx, extra_x_tick, 0, 0)

        # Draw y ticks
        ctx.textAlign = "right"
        ctx.textBaseline = "middle"
        ctx.beginPath()
        for v, text in yticks.items():
            y = y0 + (float(v) - mi) * vscale
            ctx.moveTo(x0 - 4, y)
            ctx.lineTo(x0, y)
        ctx.stroke()
        for v, text in yticks.items():
            y = y0 + (float(v) - mi) * vscale
            self._draw_text(ctx, text, x0 - 8, y)

        # Draw axis
        ctx.strokeStyle = text_color
        ctx.beginPath()
        ctx.moveTo(x0, y0)
        ctx.lineTo(x0 + width, y0)
        ctx.moveTo(x0, y0)
        ctx.lineTo(x0, y0 + height)
        ctx.stroke()

        # Draw content
        self._draw_content(ctx, mi, ma, t1, t2, x0, y0, hscale, vscale)

        # Draw local / UTC
        ctx.fillStyle = "rgba(128, 128, 128, 0.5)"
        ctx.textAlign = "right"
        ctx.textBaseline = "bottom"
        self._draw_text(ctx, "UTC" if utc else "Local time", self.width, 0)


class CountPanel(PlotPanel):

    _values_are_integer = True

    clr = 50, 250, 50

    def _get_min_max(self):
        PSCRIPT_OVERLOAD = False  # noqa
        key = self.key
        mi = 0
        ma = -9_999_999
        data = data_per_db[self.dbname]
        for i in range(len(data)):
            aggr = data[i]
            v = aggr[key]
            if v is undefined:
                continue
            ma = max(ma, v)
        return mi, ma

    def _draw_content(self, ctx, mi, ma, t1, t2, x0, y0, hscale, vscale):
        PSCRIPT_OVERLOAD = False  # noqa
        key = self.key
        clr = self.clr
        ctx.fillStyle = f"rgba({clr[0]}, {clr[1]}, {clr[2]}, 0.8)"
        data = data_per_db[self.dbname]
        for i in range(len(data)):
            aggr = data[i]
            v = aggr[key]
            if v is undefined:
                continue
            if aggr.time_start > t2:
                continue
            x = x0 + (aggr.time_start - t1) * hscale
            w = (aggr.time_stop - aggr.time_start) * hscale
            w = max(w - 1, 1)
            ctx.fillRect(x, y0, w, v * vscale)


class DailyCountPanel(CountPanel):

    clr = 220, 250, 0

    def _get_min_max(self):
        PSCRIPT_OVERLOAD = False  # noqa
        key = self.key
        mi = 0
        ma = -9_999_999
        self.daily = daily = []
        prev_day = ""
        data = data_per_db[self.dbname]
        for i in range(len(data)):
            aggr = data[i]
            v = aggr[key]
            if v is undefined:
                continue
            day = aggr.time_key[:10]
            if day != prev_day:
                if len(daily) > 0:
                    ma = max(ma, daily[-1][key])
                new_aggr = {"time_start": aggr.time_start, "time_stop": aggr.time_stop}
                new_aggr[key] = aggr[key]
                daily.append(new_aggr)
                prev_day = day
            else:
                daily[-1][key] += v
                daily[-1].time_stop = aggr.time_stop
        if len(daily) > 0:
            ma = max(ma, daily[-1][key])
        return mi, ma

    def _draw_content(self, ctx, mi, ma, t1, t2, x0, y0, hscale, vscale):
        PSCRIPT_OVERLOAD = False  # noqa
        # Draw daily
        key = self.key
        clr = self.clr
        ctx.fillStyle = f"rgba({clr[0]}, {clr[1]}, {clr[2]}, 0.4)"
        for i in range(len(self.daily)):
            aggr = self.daily[i]
            v = aggr[key]
            if aggr.time_start > t2:
                continue
            x = x0 + (aggr.time_start - t1) * hscale
            w = (aggr.time_stop - aggr.time_start) * hscale
            w = max(w - 1, 1)
            ctx.fillRect(x, y0, w, v * vscale)
        # Draw per unit
        super()._draw_content(ctx, mi, ma, t1, t2, x0, y0, hscale, vscale)


class MonthlyCountPanel(CountPanel):

    clr = 250, 200, 0

    def _get_min_max(self):
        PSCRIPT_OVERLOAD = False  # noqa
        key = self.key
        mi = 0
        ma = -9_999_999
        self.monthly = monthly = []
        prev_month = ""
        data = data_per_db[self.dbname]
        for i in range(len(data)):
            aggr = data[i]
            v = aggr[key]
            if v is undefined:
                continue
            month = aggr.time_key[:7]
            if month != prev_month:
                if len(monthly) > 0:
                    ma = max(ma, monthly[-1][key])
                new_aggr = {"time_start": aggr.time_start, "time_stop": aggr.time_stop}
                new_aggr[key] = aggr[key]
                monthly.append(new_aggr)
                prev_month = month
            else:
                monthly[-1][key] += v
                monthly[-1].time_stop = aggr.time_stop
        if len(monthly) > 0:
            ma = max(ma, monthly[-1][key])
        return mi, ma

    def _draw_content(self, ctx, mi, ma, t1, t2, x0, y0, hscale, vscale):
        PSCRIPT_OVERLOAD = False  # noqa
        # Draw monthly
        key = self.key
        clr = self.clr
        ctx.fillStyle = f"rgba({clr[0]}, {clr[1]}, {clr[2]}, 0.4)"
        for i in range(len(self.monthly)):
            aggr = self.monthly[i]
            v = aggr[key]
            if aggr.time_start > t2:
                continue
            x = x0 + (aggr.time_start - t1) * hscale
            w = (aggr.time_stop - aggr.time_start) * hscale
            w = max(w - 1, 1)
            ctx.fillRect(x, y0, w, v * vscale)
        # Draw per unit
        super()._draw_content(ctx, mi, ma, t1, t2, x0, y0, hscale, vscale)


class NumericalPanel(PlotPanel):

    clr = 0, 220, 250

    def __init__(self, *args):
        super().__init__(*args)

    def _get_min_max(self):
        PSCRIPT_OVERLOAD = False  # noqa
        key = self.key
        mi = +1e20
        ma = -1e20
        data = data_per_db[self.dbname]
        for i in range(len(data)):
            aggr = data[i]
            meas = aggr[key]
            if meas is undefined or meas.n == 0:
                continue
            mi = min(mi, meas.min)
            ma = max(ma, meas.max)
        if ma >= mi:
            mi = min(0.8 * ma, mi)  # Select a good min point
            mi = 0
        if self.unit == "%":
            mi = 0
            ma = max(ma, 100)  # percentages can be larger than 100
        return mi, ma

    def _draw_content(self, ctx, mi, ma, t1, t2, x0, y0, hscale, vscale):
        PSCRIPT_OVERLOAD = False  # noqa
        key = self.key
        clr = self.clr
        ctx.fillStyle = f"rgba({clr[0]}, {clr[1]}, {clr[2]}, 0.2)"
        ctx.strokeStyle = f"rgba({clr[0]}, {clr[1]}, {clr[2]}, 1.0)"
        data = data_per_db[self.dbname]
        mean_points = []
        for i in range(len(data)):
            aggr = data[i]
            meas = aggr[key]
            if meas is undefined or meas.n == 0:
                continue
            if aggr.time_start > t2:
                continue

            x = x0 + (aggr.time_start - t1) * hscale
            w = (aggr.time_stop - aggr.time_start) * hscale
            w = max(w, 1)

            # Draw rectangle for min max
            y = y0 + (meas.min - mi) * vscale
            h = (meas.max - meas.min) * vscale
            ctx.fillRect(x, y, w, h)

            # Draw rectangle for std
            mean = meas.mean
            std = (meas.magic / meas.n) ** 0.5  # Welford
            st1 = max(meas.min, mean - std)
            st2 = min(meas.max, mean + std)
            y = y0 + (st1 - mi) * vscale
            h = (st2 - st1) * vscale
            ctx.fillRect(x, y, w, h)

            y = y0 + (mean - mi) * vscale
            mean_points.append((x + 0.3333 * w, y))
            mean_points.append((x + 0.6666 * w, y))

        # Draw mean
        if len(mean_points) > 0:
            ctx.beginPath()
            ctx.moveTo(mean_points[0], mean_points[1])
            for x, y in mean_points:
                ctx.lineTo(x, y)
            ctx.stroke()


window.addEventListener("load", on_init)
window.addEventListener("resize", on_resize)
window.addEventListener("hashchange", on_hash_change)
