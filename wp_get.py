#!/usr/bin/env python
"""
GET Wikipedia article content from title, URL or filename

This is basically an alternative path to article content outside of
the MediaWiki API, which is often quite slow. The problem is that you
don't get ``wikitext``. But you can get raw HTML or Markdown text
(versus Wiki syntax) which can give good lead/summary output.

INPUT
    Wikipedia title, URL or filename
    input file expected to be Wikipedia HTML

OUTPUT
    full article (sans boilerplate) or summary (lead_section) only
    as HTML or Markdown text

See also
    wp_query
    wp_summary

References
    https://pypi.python.org/pypi/html2text
    https://en.wikipedia.org/wiki/Wikipedia:Manual_of_Style/Lead_section
"""

from __future__ import print_function

import argparse
import html5lib
import html2text
import lxml
import os
import re
import requests
import sys
import time

__author__ = "siznax"
__version__ = "24 Sep 2015"

XPATH = '//*[@id="mw-content-text"]'
TIMEOUT = 30

def _user_agent():
    return ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_5) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/45.0.2454.85 Safari/537.36")


def _tostring(elem, strip_tags=False):
    if strip_tags:
        return lxml.etree.tostring(elem, method="text", encoding="utf-8")
    return lxml.etree.tostring(elem)


def _epedia(content):
    content = re.sub(r"\[\d+\]", '', content)
    content = re.sub(r"\n{2,}", " \xc2\xb6 ", content)  # pilcrow '\xc2\xb6'
    last_char = content.strip()[-2:]
    if last_char == '\xc2\xb6':
        content = content.strip()[:-2]
    return content


def _process(html, xpath, lead=False, strip_tags=False, epedia=False):
    if epedia:
        lead = True
        strip_tags = True
    content = []
    etree = html5lib.parse(html,
                           treebuilder='lxml',
                           namespaceHTMLElements=False)
    root = etree.xpath(xpath)
    for item in root[0]:
        if lead:
            if item.tag.startswith("h"):
                break
            if item.tag == "p":
                content.append(_tostring(item, strip_tags))
        else:
            content.append(_tostring(item, strip_tags))
    content = "\n".join(content)
    if epedia:
        content = _epedia(content)
    return content


def article(title, epedia, lead, markdown, strip):
    """returns article as string. raises ValueError."""
    output = ""
    if os.path.exists(title):
        with open(title) as fh:
            output = _process(fh, XPATH, lead, strip, epedia)
    else:
        if not title.startswith('http'):
            base = "https://en.wikipedia.org/wiki"
            title = "%s/%s" % (base, title.replace(" ", "_"))
        print("GET %s " % title, end="", file=sys.stderr)
        r = requests.get(title, headers={'user-agent': _user_agent()},
                         timeout=TIMEOUT)
        print(r.status_code, file=sys.stderr)
        if r.status_code != 200:
            raise ValueError("HTTP status code = %d" % r.status_code)
        output = _process(r.content, XPATH, lead, strip, epedia)
    if markdown:
        output = html2text.html2text(output).encode('utf-8')
    return output


def _main(title, epedia, lead, markdown, strip):
    """prints Wikipedia article requested"""
    print(article(title, epedia, lead, markdown, strip))


if __name__ == "__main__":
    desc = "GET Wikipedia article from title, URL or filename via HTTP"
    argp = argparse.ArgumentParser(description=desc)
    argp.add_argument("title", help="article title, URL or filename")
    argp.add_argument("-e", "-pedia", action='store_true',
                      help="Epedia format")
    argp.add_argument("-l", "-lead", action='store_true',
                      help="lead paragraphs (summary) only")
    argp.add_argument("-m", "-markdown", action='store_true',
                      help="convert content to markdown text")
    argp.add_argument("-s", "-strip", action='store_true',
                      help="strip tags")
    args = argp.parse_args()

    start = time.time()
    _main(args.title, args.e, args.l, args.m, args.s)
    print("%5.3f seconds" % (time.time() - start), file=sys.stderr)
