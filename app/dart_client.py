from __future__ import annotations

import html
import io
import re
import zipfile
from datetime import date
from typing import Any

import requests


class DartClient:
    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ValueError("DART_API_KEY is required.")
        self.api_key = api_key

    def list_disclosures(
        self,
        begin_date: date,
        end_date: date | None = None,
        page_count: int = 100,
    ) -> list[dict[str, Any]]:
        end_date = end_date or begin_date
        response = requests.get(
            "https://opendart.fss.or.kr/api/list.json",
            params={
                "crtfc_key": self.api_key,
                "bgn_de": begin_date.strftime("%Y%m%d"),
                "end_de": end_date.strftime("%Y%m%d"),
                "page_count": page_count,
            },
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()

        if data.get("status") not in {"000", "013"}:
            raise RuntimeError(f"DART API error {data.get('status')}: {data.get('message')}")

        return data.get("list", [])

    def get_document_text(self, receipt_no: str) -> str:
        response = requests.get(
            "https://opendart.fss.or.kr/api/document.xml",
            params={"crtfc_key": self.api_key, "rcept_no": receipt_no},
            timeout=30,
        )
        response.raise_for_status()

        try:
            with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
                parts = []
                for name in archive.namelist():
                    if name.lower().endswith((".xml", ".html", ".htm")):
                        raw = archive.read(name)
                        parts.append(extract_text_from_html(decode_document(raw)))
                return "\n".join(part for part in parts if part).strip()
        except zipfile.BadZipFile as exc:
            text = response.text.strip()
            if text:
                raise RuntimeError(f"DART document API did not return a ZIP file: {text[:300]}") from exc
            raise RuntimeError("DART document API did not return a ZIP file.") from exc


def decode_document(raw: bytes) -> str:
    for encoding in ("utf-8", "cp949", "euc-kr"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def extract_text_from_html(source: str) -> str:
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", source, flags=re.I | re.S)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"</(p|div|tr|td|th|table|h\d)>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)
