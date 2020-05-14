# Yeah ... it is ugly embedding CSS like this, but this way I don't have to
# fiddle with package data when distributing. It's not that many lines!

CSS = """
body {
    font-family: Ubuntu,"Helvetica Neue",Arial,sans-serif;
    background: #333;
    color: #fff;
    padding: 0;
    margin: 0;
}
p {
    padding: 1em;
}
h1 {
    padding: 0.5em;
    text-align: center;
    color: #5af;
}
h2 {
    padding: 0.5em;
}
a, a:link, a:active, a:hover, a:visited {
    color: #bdf;
    text-decoration: none;
}
a:hover {
    color: #5af;
}
ul.links {
    font-size: 100%;
    line-height: 160%;
    padding: 0 1em;
    list-style: none;
}
ul.links > li > ul, ul.links > ul {
    list-style: none;
    padding-left: 1em;
}
.topbar {
    background: #333;
    color: #fff;
    font-size: 110%;
    margin: 0;
    margin-bottom: 6px;
}
.topbar * {
    color: #fff; /* overload link colors */
    text-decoration: none;
}
.topbar a, .topbar a:link, .topbar a:active, .topbar a:hover, .topbar a:visited {
    display: inline-block;
    padding: 0.3em;
    outline: none;
    color: #fff;
}
.topbar a:hover {
    background: rgba(128, 128, 128, 0.3);
}

.panelcontainertitle {
    text-align: center;
    background: #444;
    margin: 0;
    margin-top: 1em;
    padding: 0.3em;
}
.panelcontainer {
    min-height: 20px;
    background: #444;
    display: grid;
    grid-template-columns: auto;
    justify-items: stretch;
    align-items: stretch;
    justify-content: stretch;
    align-content: start;
    grid-auto-rows: 250px;
    padding: 4px 0px;
}

.panel {
    box-sizing: border-box;
    position: relative;
    vertical-align: top;
    background: #000;
    color: #BBB;
    box-shadow: 0 -3px 6px rgba(0, 0, 0, 0.3);
    margin: 4px;
    padding: 0;
    overflow: hidden;
}
.panel .title {
    -moz-user-select: none;
    user-select: none;
    text-align: center;
    background: #444;
    margin-bottom: 5px;
    padding: 3px;
    font-weight: bold;
}
.panel canvas {
    outline: none;
    -moz-user-select: none;
    user-select: none;
    position: absolute;
    top: 30px;
    left: 5px;
}
.panel .content {
    position: absolute;
    top: 30px;
    left: 5px;
    right: 5px;
    bottom: 5px;
    overflow: hidden;
    overflow-y: auto;
}
.panel .scrollhider {
    background: #000;
    position: absolute;
    top: 30px;
    width: 50px;
    right: 0px;
    bottom: 0px;

}
.panel .content table {
    width: 100%;
    text-align: left;
    border-collapse: collapse;
    font-size: 85%;
}
table.info {
    text-align: left;
    border-collapse: collapse;
}
.panel .content table td, table.info td {
    padding-left: 0.7em;
}
.panel .content table tr, table.info tr {
    background-color: rgba(100, 100, 100, 0.2);
}
.panel .content table tr:nth-child(even), table.info tr:nth-child(even) {
    background-color: rgba(160, 160, 160, 0.2);
}

@media screen and (min-height: 600px) {
    .panelcontainer {
       grid-auto-rows: 300px;
    }
}
@media screen and (min-width: 600px) {
    .panelcontainer {
       grid-template-columns: auto auto;
       padding: 4px 4px;
    }
}
@media screen and (min-width: 1200px) {
    .panelcontainer {
       grid-template-columns: auto auto auto;
    }
}
@media screen and (min-width: 1600px) {
    .panelcontainer {
       grid-template-columns: auto auto auto auto;
    }
}
"""
