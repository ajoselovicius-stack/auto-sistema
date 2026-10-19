#!/usr/bin/env python3
"""Download Autoplius make/model IDs into a versioned JSON snapshot."""
import json
import os
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

BASES = ["https://autoplius.lt", "https://en.autoplius.lt"]
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0 Safari/537.36",
    "Accept": "application/xml,text/xml,*/*",
    "Accept-Language": "lt-LT,lt;q=0.9,en;q=0.8",
    "Referer": "https://autoplius.lt/",
}
OUT = Path(__file__).resolve().parents[1] / "autoplius_catalog.json"


def get_xml(path):
    last_error = None
    for base in BASES:
        request = urllib.request.Request(base + path, headers=HEADERS)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return ET.fromstring(response.read())
        except (urllib.error.URLError, ET.ParseError, TimeoutError, OSError) as error:
            last_error = error
    raise RuntimeError(f"Autoplius katalogo užklausa nepavyko: {path}: {last_error}")


def read_items(parent, tag):
    section = parent.find(tag)
    if section is None:
        return []
    items = []
    for node in section.findall("item"):
        ident = node.findtext("id")
        title = node.findtext("title")
        if ident and title:
            try:
                items.append({"name": title.strip(), "id": int(ident)})
            except ValueError:
                continue
    return sorted(items, key=lambda item: item["name"].casefold())


def main():
    root = get_xml("/importhandler?datacollector=1&category_id=2")
    makes = read_items(root, "./response/make_id")
    if not makes:
        raise RuntimeError("Autoplius negrąžino markių sąrašo; senas katalogas paliekamas.")

    catalog = {"source": "Autoplius", "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "makes": []}
    for index, make in enumerate(makes, 1):
        path = f"/importhandler?datacollector=1&category_id=2&make_id={make['id']}"
        try:
            model_root = get_xml(path)
            models = read_items(model_root, "./response/models")
        except RuntimeError as error:
            raise RuntimeError(f"Modelių katalogas markei {make['name']} nepasiekiamas; senas katalogas paliekamas.") from error
        catalog["makes"].append({**make, "models": models})
        print(f"[{index}/{len(makes)}] {make['name']}: {len(models)} modelių")
        time.sleep(0.2)

    temporary = OUT.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(OUT)
    print(f"Išsaugota {len(catalog['makes'])} markių į {OUT}")


if __name__ == "__main__":
    main()
