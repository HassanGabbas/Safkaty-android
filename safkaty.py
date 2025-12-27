#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SAFKATY - Marchés Publics Manager + Scraper (marchespublics.gov.ma)

Run:
  pip install requests beautifulsoup4
  python safkaty.py
"""

import os
import re
import csv
import time
import queue
import sqlite3
import threading
import webbrowser
import urllib.parse
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Tuple



# === SAFKATY_PATCH_V21_1 ===
# Multi-Lot: Jeder Lot = eigene Zeile ("REF | Lot X")
# Diese Funktionen werden von der bestehenden App genutzt, ohne GUI zu ändern.

import json

def _safkaty_norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()

def _safkaty_money(s: str) -> str:
    if not s:
        return ""
    # akzeptiert: 400 200,00 / 400.200,00 / 400200.00
    m = re.search(r"([0-9][0-9\s\.,\u00A0\u202F]*)\s*(DH|DHS|MAD)?", s, flags=re.I)
    if not m:
        return ""
    num = _safkaty_norm(m.group(1))
    cur = (m.group(2) or "").strip()
    if cur:
        return f"{num} {cur}".replace("  ", " ")
    # wenn Währung fehlt: bei marchespublics fast immer DH
    return f"{num} DH"

def safkaty_parse_lots_popup(popup_html: str):
    """
    Robust: erkennt Lot-Header:
      Lot 1:, Lot 1 -, Lot 1 – , Lot 1 — , Lot 1 (ohne Trenner)
    und liest Estimation/Caution nur innerhalb des aktuellen Lot-Blocks.
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(popup_html or "", "html.parser")
    txt = soup.get_text("\n", strip=True)
    lines = [_safkaty_norm(x) for x in (txt.split("\n") if txt else []) if _safkaty_norm(x)]

    lots = []
    cur = None
    buf = []

    def flush():
        nonlocal cur, buf, lots
        if cur is None:
            return
        est = ""
        cau = ""
        # Zeilenweise: Wert kann nach ":" kommen oder in der nächsten Zeile
        for i, ln in enumerate(buf):
            if re.match(r"^Estimation\b", ln, flags=re.I):
                if ":" in ln:
                    est = _safkaty_money(ln.split(":", 1)[1])
                else:
                    est = _safkaty_money(buf[i+1] if i+1 < len(buf) else "")
            if re.match(r"^Caution\s+provisoire\b", ln, flags=re.I):
                if ":" in ln:
                    cau = _safkaty_money(ln.split(":", 1)[1])
                else:
                    cau = _safkaty_money(buf[i+1] if i+1 < len(buf) else "")

        lots.append({"lot": int(cur), "estimation": _safkaty_norm(est), "caution": _safkaty_norm(cau)})
        cur = None
        buf = []

    for ln in lines:
        m = re.match(r"^Lot\s*(?:n[°o]\s*)?(\d+)\b(?:\s*[:\-–—]\s*.*)?$", ln, flags=re.I)
        if m:
            flush()
            cur = m.group(1)
            buf = []
        else:
            if cur is not None:
                buf.append(ln)

    flush()
    return lots

def safkaty_expand_rows_with_lots(rows):
    """
    rows: Liste von dict oder tuples aus deiner App.
    Wenn ein Datensatz 'lots_json' oder 'lots' enthält, wird er zu mehreren Zeilen expandiert.
    Erwartet folgende Keys (falls vorhanden):
      - reference
      - estimation
      - caution
      - lots_json (JSON string) ODER lots (list)
    """
    expanded = []

    for r in rows:
        # dict-fall
        if isinstance(r, dict):
            lots = None
            if r.get("lots") and isinstance(r["lots"], list):
                lots = r["lots"]
            elif r.get("lots_json"):
                try:
                    lots = json.loads(r["lots_json"])
                except Exception:
                    lots = None

            if lots and isinstance(lots, list) and len(lots) > 0:
                base_ref = r.get("reference", "")
                for lot in lots:
                    rr = dict(r)
                    lot_no = lot.get("lot")
                    rr["reference"] = f"{base_ref} | Lot {lot_no}"
                    rr["estimation"] = lot.get("estimation", "") or rr.get("estimation", "")
                    rr["caution"] = lot.get("caution", "") or rr.get("caution", "")
                    expanded.append(rr)
            else:
                expanded.append(r)
        else:
            # tuple/list-fall: lassen wir unverändert (deine App kann später umstellen)
            expanded.append(r)

    return expanded



import requests
from bs4 import BeautifulSoup

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkinter.scrolledtext import ScrolledText


def safe_float_amount(text: str) -> Optional[float]:
    if not text:
        return None
    t = text.strip().replace("\u00A0", " ")
    t = re.sub(r"(MAD|DH|DHS|Dirhams?)", "", t, flags=re.IGNORECASE).strip()
    t = t.replace(" ", "")
    if "," in t and t.count(",") == 1:
        t = t.replace(".", "").replace(",", ".")
    m = re.search(r"(\d+(?:\.\d+)?)", t)
    if not m:
        return None
    try:
        return float(m.group(1))
    except Exception:
        return None


def parse_date_ddmmyyyy(text: str) -> Optional[str]:
    """Parst dd/mm/yyyy (ggf. mit Uhrzeit) ODER yyyy-mm-dd."""
    if not text:
        return None
    # dd/mm/yyyy
    m = re.search(r"(\d{2})/(\d{2})/(\d{4})", text)
    if m:
        dd, mm, yyyy = m.group(1), m.group(2), m.group(3)
        return f"{yyyy}-{mm}-{dd}"
    # yyyy-mm-dd
    m2 = re.search(r"(\d{4})-(\d{2})-(\d{2})", text)
    if m2:
        yyyy, mm, dd = m2.group(1), m2.group(2), m2.group(3)
        return f"{yyyy}-{mm}-{dd}"
    return None


def fmt_money(maybe_float: Optional[float]) -> str:
    if maybe_float is None:
        return "—"
    try:
        return f"{maybe_float:,.2f} MAD".replace(",", " ")
    except Exception:
        return f"{maybe_float} MAD"


def fmt_date_iso(iso: Optional[str]) -> str:
    if not iso:
        return "—"
    try:
        yyyy, mm, dd = iso.split("-")
        return f"{dd}/{mm}/{yyyy}"
    except Exception:
        return iso


@dataclass
class Tender:
    reference: str
    titre: str = ""
    lieux: str = ""
    estimation: Optional[float] = None
    caution: Optional[float] = None
    echeance: Optional[str] = None          # yyyy-mm-dd
    echeance_time: str = ""
    organisation: str = ""
    publication: Optional[str] = None       # yyyy-mm-dd
    categorie: str = ""
    description: str = ""
    contact_email: str = ""
    contact_phone: str = ""
    url: str = ""


class Database:
    def __init__(self):
        self.db_file = self._get_database_path()
        self.conn = sqlite3.connect(self.db_file, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self._create_tables()

    def _get_database_path(self) -> str:
        docs = Path.home() / ("Dokumente" if os.name == "nt" else "Documents")
        if not docs.exists():
            docs = Path.home() / "Documents"
        folder = docs / "Safkaty"
        folder.mkdir(parents=True, exist_ok=True)
        return str(folder / "safkaty.db")

    def _create_tables(self):
        cur = self.conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS tenders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reference TEXT UNIQUE NOT NULL,
            titre TEXT,
            lieux TEXT,
            estimation REAL,
            caution REAL,
            echeance TEXT,
            echeance_time TEXT,
            organisation TEXT,
            publication TEXT,
            categorie TEXT,
            description TEXT,
            contact_email TEXT,
            contact_phone TEXT,
            url TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS tender_status (
            tender_id INTEGER UNIQUE,
            status TEXT DEFAULT 'neu',
            priority INTEGER DEFAULT 3,
            notes TEXT DEFAULT '',
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(tender_id) REFERENCES tenders(id)
        )
        """)
        self.conn.commit()

    def upsert_tender(self, t: Tender) -> Tuple[bool, int]:
        cur = self.conn.cursor()
        cur.execute("SELECT id FROM tenders WHERE reference=?", (t.reference,))
        row = cur.fetchone()
        if row:
            tender_id = row[0]
            cur.execute("""
                UPDATE tenders SET
                  titre=?,
                  lieux=?,
                  estimation=?,
                  caution=?,
                  echeance=?,
                  echeance_time=?,
                  organisation=?,
                  publication=?,
                  categorie=?,
                  description=?,
                  contact_email=?,
                  contact_phone=?,
                  url=?
                WHERE id=?
            """, (
                t.titre, t.lieux, t.estimation, t.caution,
                t.echeance, t.echeance_time,
                t.organisation, t.publication, t.categorie,
                t.description, t.contact_email, t.contact_phone, t.url,
                tender_id
            ))
            self.conn.commit()
            return (False, tender_id)

        cur.execute("""
            INSERT INTO tenders
              (reference, titre, lieux, estimation, caution, echeance, echeance_time,
               organisation, publication, categorie, description, contact_email, contact_phone, url)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            t.reference, t.titre, t.lieux, t.estimation, t.caution,
            t.echeance, t.echeance_time,
            t.organisation, t.publication, t.categorie,
            t.description, t.contact_email, t.contact_phone, t.url
        ))
        tender_id = cur.lastrowid
        cur.execute("INSERT OR IGNORE INTO tender_status (tender_id) VALUES (?)", (tender_id,))
        self.conn.commit()
        return (True, tender_id)

    def list_tenders(self, search: str = "", status: str = "Alle", priority: str = "Alle") -> List[Tuple]:
        cur = self.conn.cursor()
        conditions = []
        params: List = []

        if search.strip():
            conditions.append("(LOWER(reference) LIKE ? OR LOWER(titre) LIKE ? OR LOWER(lieux) LIKE ? OR LOWER(organisation) LIKE ?)")
            s = f"%{search.lower().strip()}%"
            params.extend([s, s, s, s])

        if status != "Alle":
            conditions.append("COALESCE(ts.status,'neu') = ?")
            params.append(status)

        if priority != "Alle":
            conditions.append("COALESCE(ts.priority,3) = ?")
            params.append(int(priority))

        where = " AND ".join(conditions) if conditions else "1=1"

        cur.execute(f"""
        SELECT
            t.id, t.reference, t.titre, t.organisation, t.lieux,
            t.estimation, t.caution, t.echeance,
            COALESCE(ts.status,'neu') as status,
            COALESCE(ts.priority,3) as priority
        FROM tenders t
        LEFT JOIN tender_status ts ON ts.tender_id=t.id
        WHERE {where}
        ORDER BY
          COALESCE(ts.priority,3) ASC,
          CASE WHEN t.echeance IS NULL OR t.echeance='' THEN 1 ELSE 0 END,
          t.echeance ASC
        """, params)
        return cur.fetchall()

    def get_tender(self, tender_id: int) -> Optional[Dict]:
        cur = self.conn.cursor()
        cur.execute("""
        SELECT
          t.*, COALESCE(ts.status,'neu') as status, COALESCE(ts.priority,3) as priority, COALESCE(ts.notes,'') as notes
        FROM tenders t
        LEFT JOIN tender_status ts ON ts.tender_id=t.id
        WHERE t.id=?
        """, (tender_id,))
        row = cur.fetchone()
        if not row:
            return None
        cols = [d[0] for d in cur.description]
        return dict(zip(cols, row))

    def update_status(self, tender_id: int, status: str):
        cur = self.conn.cursor()
        cur.execute("""
          INSERT INTO tender_status (tender_id, status, updated_at)
          VALUES (?,?,?)
          ON CONFLICT(tender_id) DO UPDATE SET status=excluded.status, updated_at=excluded.updated_at
        """, (tender_id, status, datetime.now().isoformat(timespec="seconds")))
        self.conn.commit()

    def update_priority(self, tender_id: int, priority: int):
        cur = self.conn.cursor()
        cur.execute("""
          INSERT INTO tender_status (tender_id, priority, updated_at)
          VALUES (?,?,?)
          ON CONFLICT(tender_id) DO UPDATE SET priority=excluded.priority, updated_at=excluded.updated_at
        """, (tender_id, priority, datetime.now().isoformat(timespec="seconds")))
        self.conn.commit()

    def update_notes(self, tender_id: int, notes: str):
        cur = self.conn.cursor()
        cur.execute("""
          INSERT INTO tender_status (tender_id, notes, updated_at)
          VALUES (?,?,?)
          ON CONFLICT(tender_id) DO UPDATE SET notes=excluded.notes, updated_at=excluded.updated_at
        """, (tender_id, notes, datetime.now().isoformat(timespec="seconds")))
        self.conn.commit()

    def stats(self) -> Dict[str, int]:
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM tenders")
        total = cur.fetchone()[0]
        cur.execute("""SELECT COALESCE(status,'neu'), COUNT(*) FROM tender_status GROUP BY COALESCE(status,'neu')""")
        by_status = {k: v for k, v in cur.fetchall()}
        by_status["TOTAL"] = total
        return by_status

    def close(self):
        try:
            self.conn.close()
        except Exception:
            pass


class MarchesPublicsScraper:
    def __init__(self, base_url: str = "https://www.marchespublics.gov.ma"):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.6",
        })

    def _abs_url(self, href: str) -> str:
        if not href:
            return ""
        if href.startswith("http"):
            return href
        if href.startswith("/"):
            return self.base_url + href
        return f"{self.base_url}/{href}"

    def _norm(self, s: str) -> str:
        if not s:
            return ""
        s = s.replace("\u00A0", " ")
        s = re.sub(r"\s+", " ", s).strip()
        return s

    def _get(self, url: str, params: Optional[dict] = None, timeout: int = 40, headers: Optional[dict] = None) -> str:
        last_err = None
        for attempt in range(3):
            try:
                r = self.session.get(url, params=params, timeout=timeout, headers=headers)
                self.last_response_url = str(r.url)
                txt = r.text or ""
                if "captcha" in txt.lower() or "access denied" in txt.lower():
                    raise RuntimeError("CAPTCHA/Block erkannt. Bitte 'Max' kleiner machen (z.B. 10) oder später erneut.")
                return txt
            except Exception as e:
                last_err = e
                time.sleep(1.3 + attempt * 1.2)
        raise RuntimeError(str(last_err))

    # NEW: robust fetch (index.php5 vs index.php)
    def _count_detail_links(self, soup: BeautifulSoup) -> int:
        return sum(
            1 for a in soup.find_all("a", href=True)
            if "EntrepriseDetailsConsultation" in a["href"] and "refConsultation=" in a["href"]
        )

    def _fetch_search_soup(self, keyword: str) -> BeautifulSoup:
        params = {"page": "entreprise.EntrepriseAdvancedSearch", "keyWord": keyword, "searchAnnCons": "", "lang": "fr"}
        best_html = ""
        best_links = -1

        for endpoint in ("index.php5", "index.php"):
            url = f"{self.base_url}/{endpoint}"
            try:
                html = self._get(url, params=params)
                soup = BeautifulSoup(html, "html.parser")
                cnt = self._count_detail_links(soup)
                if cnt > best_links:
                    best_links = cnt
                    best_html = html
            except Exception:
                continue

        if not best_html:
            best_html = self._get(f"{self.base_url}/index.php", params=params)

        return BeautifulSoup(best_html, "html.parser")

    def _extract_detail_links_fallback(self, soup: BeautifulSoup) -> List[str]:
        links: List[str] = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "EntrepriseDetailsConsultation" in href and "refConsultation=" in href:
                links.append(self._abs_url(href))
        seen = set()
        out: List[str] = []
        for u in links:
            if u not in seen:
                seen.add(u)
                out.append(u)
        return out

    def _find_value_by_labels(self, soup: BeautifulSoup, labels: List[str]) -> str:
        labels_norm = [self._norm(l).lower() for l in labels]
        for tr in soup.find_all("tr"):
            cells = tr.find_all(["th", "td"])
            if len(cells) < 2:
                continue
            left = self._norm(cells[0].get_text(" ", strip=True)).lower().strip(":")
            for lab in labels_norm:
                if lab and lab in left:
                    return self._norm(cells[1].get_text(" ", strip=True))
        for el in soup.find_all(["div", "span", "label", "p"]):
            t = self._norm(el.get_text(" ", strip=True)).lower()
            if not t:
                continue
            for lab in labels_norm:
                if lab and lab in t:
                    sib = el.find_next_sibling()
                    if sib:
                        v = self._norm(sib.get_text(" ", strip=True))
                        if v:
                            return v
                    td = el.find_next("td")
                    if td:
                        v = self._norm(td.get_text(" ", strip=True))
                        if v:
                            return v
        return ""

    def fetch_details_by_url(self, detail_url: str) -> Dict[str, str]:
        """
        Detailseite:
        - Daten stehen im HTML (auch wenn eingeklappt).
        - Estimation/Caution sind oft pro LOT in einem Popup:
          index.php?page=commun.PopUpDetailLots&orgAcronyme=...&refConsultation=...
        """
        import urllib.parse

        referer = f"{self.base_url}/index.php?page=entreprise.EntrepriseAdvancedSearch&lang=fr"
        html = self._get(detail_url, headers={"Referer": referer})
        soup = BeautifulSoup(html, "html.parser")
        full_text = soup.get_text("\n", strip=True)

        def extract_after_label(label: str) -> str:
            # robust: accepts "Label : value" and also cases where ':' is on the next line or even missing
            # Example: "Estimation (en Dhs TTC) : 400 200,00"
            lab = re.escape(label)
            m = re.search(
                rf"{lab}\s*(?:\([^)]*\))?\s*(?:(?::)|(?:\n\s*:))?\s*(.*?)(?:\n(?=[A-Za-zÀ-ÿ0-9][^:\n]{1,80}\s*:)|\Z)",
                full_text,
                flags=re.IGNORECASE | re.DOTALL
            )
            if not m:
                return ""
            val = re.sub(r"\s+", " ", m.group(1)).strip()
            return val

        def first_email(txt: str) -> str:
            em = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", txt or "")
            return em.group(0) if em else ""

        def pick_time(txt: str) -> str:
            m = re.search(r"\b(\d{1,2}:\d{2})\b", txt or "")
            return m.group(1) if m else ""

        data: Dict[str, str] = {}

        data["reference"] = self._norm(extract_after_label("Référence") or extract_after_label("Reference"))
        data["objet"] = self._norm(extract_after_label("Objet"))
        data["organisation"] = self._norm(extract_after_label("Acheteur public"))

        lieux_raw = extract_after_label("Lieu d'exécution") or extract_after_label("Lieu d’exécution")
        lieux_raw = re.split(r"\bEstimation\b", lieux_raw, flags=re.IGNORECASE)[0].strip()
        data["lieux"] = self._norm(lieux_raw)

        echeance_txt = extract_after_label("Date et heure limite de remise des plis") or extract_after_label("Date limite de remise des plis")
        data["echeance"] = parse_date_ddmmyyyy(echeance_txt) or ""
        data["echeance_time"] = pick_time(echeance_txt)

        data["estimation"] = self._norm(
            extract_after_label("Estimation") or
            extract_after_label("Montant estimatif") or
            extract_after_label("Montant estimé")
        )
        if not data["estimation"]:
            m = re.search(r"Estimation\s*(?:\([^)]*\))?\s*:\s*([0-9][0-9\s\.,\u00A0\u202F]*)", full_text, flags=re.IGNORECASE)
            if m:
                data["estimation"] = self._norm(m.group(1))
            if not data["estimation"]:
                m2 = re.search(r"Estimation\s*(?:\([^)]*\))?\s*(?:(?::)|(?:\n\s*:))?\s*([0-9][0-9\s\.,\u00A0\u202F]*)", full_text, flags=re.IGNORECASE)
                if m2:
                    data["estimation"] = self._norm(m2.group(1))

        data["caution"] = self._norm(
            extract_after_label("Caution provisoire") or
            extract_after_label("Garantie provisoire") or
            extract_after_label("Caution")
        )

        # Contact (prefer "Contact Administratif" block to avoid footer text)
        def _contact_block(txt: str) -> str:
            if not txt:
                return ""
            m = re.search(r"(Contact\s+Administratif|Contact\s+administratif)", txt, flags=re.IGNORECASE)
            if not m:
                return txt  # fallback: whole text
            tail = txt[m.start():]
            stop = re.search(r"\n(?:Contact\s+technique|Objet\s*:|Acheteur\s+public|Lieu\s+d['’]exécution|Date\s+et\s+heure\s+limite|Lots?)\b", tail, flags=re.IGNORECASE)
            return tail[:stop.start()] if stop else tail

        def _first_email(txt: str) -> str:
            m = re.search(r"([A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,})", txt or "", flags=re.IGNORECASE)
            return m.group(1) if m else ""

        def _phone(txt: str) -> str:
            if not txt:
                return ""
            m = re.search(r"(?:Téléphone|Telephone|Tel|Tél)\s*[:\-]?\s*([+]?\d[\d\s\-/]{6,})", txt, flags=re.IGNORECASE)
            if m:
                return m.group(1).strip()
            m = re.search(r"(\+212[\d\s\-/]{7,}|0[\d\s\-/]{8,})", txt)
            return m.group(1).strip() if m else ""

        cb = _contact_block(full_text)
        data["contact_email"] = self._norm(extract_after_label("Adresse électronique") or _first_email(cb))
        data["contact_phone"] = self._norm(_phone(cb))
        # LOT popup parsing (Estimation/Caution per lot)
        try:
            import urllib.parse
            import json as _json

            def is_empty(v: str) -> bool:
                return (v or "").strip() in ("", "-", "—", "–")

            def parse_money_from_text(t: str) -> str:
                """
                Extract a money-like amount from text.
                We avoid accidentally grabbing phone numbers / huge concatenations.
                Prefer amounts with decimals (',' or '.') or an explicit currency.
                """
                if not t:
                    return ""
                t = self._norm(t)

                # Find candidates like: "12 000,00 DH" / "12000.00 MAD" / "400 200,00"
                candidates = re.findall(
                    r"([0-9][0-9\s\.,\u00A0\u202F]*)(?:\s*(DH|DHS|MAD))?",
                    t,
                    flags=re.IGNORECASE
                )
                for num_raw, cur in candidates:
                    num = self._norm(num_raw)
                    cur = (cur or "").strip().upper()

                    # Require either decimal separators OR explicit currency (to avoid phones/IDs)
                    if ("," not in num_raw and "." not in num_raw) and not cur:
                        continue

                    # remove separators to gauge digit length (ignore decimals)
                    digits = re.sub(r"[^0-9]", "", num_raw)
                    if len(digits) > 15:
                        continue

                    out = num
                    if cur:
                        out = f"{out} {cur}"
                    return out.strip()

                return ""

            def extract_value_from_lines(lines, key_regex):
                # Find line containing label; value may be on same line after ':' or on next line(s).
                # IMPORTANT: stop scanning if another label or next Lot starts (prevents stealing Estimation for Caution etc.)
                LABEL_STOP = re.compile(
                    r"^(Estimation|Caution\s+provisoire|Cat[ée]gorie|Objet|Acheteur\s+public|Lieu|Date\s+et\s+heure|Date\s+limite|Proc[ée]dure|Type\s+d'annonce|Allotissement)\b",
                    flags=re.IGNORECASE
                )
                LOT_STOP = re.compile(r"^Lot\s*(?:n[°o]\s*)?\d+\b", flags=re.IGNORECASE)

                for i, line in enumerate(lines):
                    if re.search(key_regex, line, flags=re.IGNORECASE):
                        # same line: Label : value
                        if ":" in line:
                            after = line.split(":", 1)[1].strip()
                            v = parse_money_from_text(after)
                            if v:
                                return v

                        # next lines: value might be after ':' on own line or on following line
                        for j in range(i + 1, min(i + 10, len(lines))):
                            nxt = lines[j].strip()
                            if not nxt or nxt in ("-", "—", "–"):
                                continue
                            if nxt == ":":
                                continue

                            # stop if we hit another label (and it's not just the same one repeated) or next Lot
                            if LOT_STOP.match(nxt):
                                break
                            if (":" in nxt and re.match(r"^[A-Za-zÀ-ÿ]", nxt)) or LABEL_STOP.match(nxt):
                                break

                            v = parse_money_from_text(nxt)
                            if v:
                                return v
                        return ""
                return ""

            def extract_lot_title(lines):
                # Usually: first meaningful line after "Lot X:" before "Catégorie"
                for ln in lines:
                    if re.match(r"^Cat[ée]gorie\b", ln, flags=re.IGNORECASE):
                        break
                    if re.match(r"^(Services|Travaux|Fournitures)\b", ln, flags=re.IGNORECASE):
                        # category line; not a title
                        continue
                    if ln and ln not in ("-", "—", "–"):
                        return ln
                return ""

            def parse_popup(html_text: str):
                soup = BeautifulSoup(html_text, "html.parser")
                text = soup.get_text("\n", strip=True)
                lines = [self._norm(x) for x in text.split("\n") if self._norm(x)]

                lots = []
                current_no = None
                current_lines = []

                def flush():
                    nonlocal current_no, current_lines
                    if current_no is None:
                        return
                    title = extract_lot_title(current_lines)
                    est = extract_value_from_lines(current_lines, r"^Estimation\b")
                    cau = extract_value_from_lines(current_lines, r"^Caution\s+provisoire\b")

                    # Portal often shows estimation without currency; normalize to DH if none
                    if est and not re.search(r"\b(DH|DHS|MAD)\b", est, flags=re.IGNORECASE):
                        est = est + " DH"
                    if cau and not re.search(r"\b(DH|DHS|MAD)\b", cau, flags=re.IGNORECASE):
                        cau = cau + " DH"

                    if est or cau or title:
                        lots.append((current_no, self._norm(title), self._norm(est), self._norm(cau)))
                    current_no = None
                    current_lines = []

                for ln in lines:
                    mlot = re.match(r"^Lot\s*(?:n[°o]\s*)?(\d+)\b(?:\s*(?:[:\-–—].*)?)?$", ln, flags=re.IGNORECASE)
                    if mlot:
                        flush()
                        current_no = int(mlot.group(1))
                        current_lines = []
                        continue
                    if current_no is not None:
                        current_lines.append(ln)

                flush()

                if not lots:
                    # Lot unique fallback: treat whole text
                    title = ""
                    est = extract_value_from_lines(lines, r"^Estimation\b")
                    cau = extract_value_from_lines(lines, r"^Caution\s+provisoire\b")
                    if est and not re.search(r"\b(DH|DHS|MAD)\b", est, flags=re.IGNORECASE):
                        est = est + " DH"
                    if cau and not re.search(r"\b(DH|DHS|MAD)\b", cau, flags=re.IGNORECASE):
                        cau = cau + " DH"
                    if est or cau:
                        lots = [(1, title, self._norm(est), self._norm(cau))]
                return lots

            parsed = urllib.parse.urlparse(detail_url)
            q = dict(urllib.parse.parse_qsl(parsed.query, keep_blank_values=True))
            refc = q.get("refConsultation") or q.get("refconsultation")
            orga = q.get("orgAcronyme") or q.get("orgacronyme") or q.get("orgAccronyme")
            code = q.get("code", "")
            retraits = q.get("retraits", "")
            lang = (q.get("lang") or "fr").strip() or "fr"

            
            # Prefer to discover the *real* popup URL from the HTML (robust against parameter naming changes)
            def find_popup_url_from_html(soup_obj, html_text: str) -> str:
                # 1) direct link in href
                for a in soup_obj.find_all("a", href=True):
                    href = a.get("href", "")
                    if "PopUpDetailLots" in href:
                        return href
                # 2) sometimes it is embedded in onclick JS
                for a in soup_obj.find_all("a"):
                    onclick = a.get("onclick") or ""
                    m = re.search(r"(index\.php\?page=commun\.PopUpDetailLots[^'\"]+)", onclick)
                    if m:
                        return m.group(1)
                # 3) last resort: regex scan in HTML
                m = re.search(r"(index\.php\?page=commun\.PopUpDetailLots[^'\"\s>]+)", html_text or "")
                if m:
                    return m.group(1)
                return ""

            popup_href = find_popup_url_from_html(soup, html)
            popup_url = self._abs_url(popup_href) if popup_href else ""

            lots = []
            if popup_url:
                try:
                    pop_html = self._get(popup_url, headers={"Referer": detail_url})
                    lots = parse_popup(pop_html)
                except Exception:
                    lots = []

            # Fallback: construct popup URL from query parameters
            if (not lots) and refc and orga:
                popup_variants = [
                    {"orgAcronyme": orga, "orgAccronyme": orga},
                    {"orgAccronyme": orga},
                    {"orgAcronyme": orga},
                ]
                for org_params in popup_variants:
                    popup_q = {
                        "page": "commun.PopUpDetailLots",
                        "refConsultation": refc,
                        "code": code,
                        "retraits": retraits,
                        "lang": lang,
                        **org_params,
                    }
                    try:
                        tmp_url = f"{self.base_url}/index.php?{urllib.parse.urlencode(popup_q, doseq=True)}"
                        pop_html = self._get(tmp_url, headers={"Referer": detail_url})
                        lots = parse_popup(pop_html)
                        if lots:
                            break
                    except Exception:
                        continue
                    if lots:
                        break

                if lots:
                    lots.sort(key=lambda x: x[0])

                    # store lots for caller (search() can expand into multiple rows)
                    data["lots_json"] = _json.dumps(
                        [{"lot": n, "lot_title": t, "estimation": e, "caution": c} for n, t, e, c in lots],
                        ensure_ascii=False
                    )

                    # For single-lot consultations, also fill the normal fields
                    if len(lots) == 1:
                        if is_empty(data.get("estimation", "")) and lots[0][2]:
                            data["estimation"] = lots[0][2]
                        if is_empty(data.get("caution", "")) and lots[0][3]:
                            data["caution"] = lots[0][3]
        except Exception:
            pass

        for k, v in list(data.items()):
            data[k] = self._norm(v)

        return data

    def _parse_result_table(self, soup: BeautifulSoup) -> List[Tuple[Dict[str, str], str]]:
        """
        SUPER robust (ohne Spaltenindex-Mapping):
        - Wir lesen pro Zeile per Regex/Heuristik aus dem Zeilentext.
        - Wichtig: In jeder Ergebniszeile gibt es mehrere Links (InfoSite, Tester, Ajouter, ...).
          Wir akzeptieren NUR den Link EntrepriseDetailsConsultation&refConsultation=...
        """
        import unicodedata

        results: List[Tuple[Dict[str, str], str]] = []

        BAD_KEYS = [
            "infosite",
            "conditions d'utilisation", "conditions dutilisation", "conditions d’utilisation",
            "pre requis", "prerequis", "pre-requis",
            "acceder a la consultation", "accéder à la consultation",
            "tester la configuration", "ajouter au panier",
            "reponse electronique", "réponse électronique",
            "signature electronique", "signature électronique",
            "pas de reponse electronique", "pas de réponse électronique",
            "nouvelle recherche", "actions"
        ]

        def key(s: str) -> str:
            # lower + remove accents + normalize spaces
            s = s.lower()
            s = unicodedata.normalize("NFKD", s)
            s = "".join(ch for ch in s if not unicodedata.combining(ch))
            s = re.sub(r"\s+", " ", s).strip()
            return s

        def clean_lines(tr) -> List[str]:
            txt = tr.get_text("\n", strip=True)
            lines = [self._norm(x) for x in txt.split("\n")]
            lines = [x for x in lines if x and x != "-"]
            return lines

        def is_bad_line(ln: str) -> bool:
            k = key(ln)
            return any(b in k for b in [key(x) for x in BAD_KEYS])

        def pick_location(lines: List[str]) -> str:
            # 1) Nach Acheteur public suchen -> nächste gute kurze Zeile ist meist der Ort
            for i, ln in enumerate(lines):
                if "acheteur public" in key(ln):
                    for j in range(i+1, min(i+6, len(lines))):
                        cand = lines[j]
                        if is_bad_line(cand):
                            continue
                        if ":" in cand:
                            continue
                        if 2 <= len(cand) <= 80:
                            return cand

            # 2) Caps-Heuristik
            cands = []
            for ln in lines:
                if is_bad_line(ln):
                    continue
                if ":" in ln:
                    continue
                if len(ln) > 80:
                    continue
                score = 0
                if ln.upper() == ln and any(ch.isalpha() for ch in ln):
                    score += 3
                if re.fullmatch(r"[A-ZÀ-Ü\s'\-]{3,}", ln):
                    score += 2
                if 1 <= len(ln.split()) <= 5:
                    score += 1
                if score >= 3:
                    cands.append((score, ln))
            if cands:
                cands.sort(key=lambda x: (-x[0], len(x[1])))
                return cands[0][1]

            # 3) fallback: letzte gute kurze Zeile
            for ln in reversed(lines):
                if is_bad_line(ln):
                    continue
                if ":" in ln:
                    continue
                if 2 <= len(ln) <= 80:
                    return ln
            return ""

        def pick_published_and_deadline(lines: List[str]) -> Tuple[Optional[str], Optional[str]]:
            dates_ddmmyyyy = []
            for ln in lines:
                for m in re.finditer(r"\b(\d{2})/(\d{2})/(\d{4})\b", ln):
                    dd, mm, yy = m.group(1), m.group(2), m.group(3)
                    dates_ddmmyyyy.append((yy, mm, dd, f"{dd}/{mm}/{yy}"))
            if not dates_ddmmyyyy:
                return (None, None)
            dates_ddmmyyyy.sort()
            publication = dates_ddmmyyyy[0][3]
            deadline = dates_ddmmyyyy[-1][3]
            return (publication, deadline)

        def pick_time(lines: List[str]) -> str:
            for ln in lines:
                m = re.search(r"\b(\d{1,2}:\d{2})\b", ln)
                if m:
                    return m.group(1)
            return ""

        def extract_reference(full_text: str) -> str:
            # Return ONLY the reference code (never "Objet : ..." etc.)
            text = full_text or ""
            # cut anything after 'Objet :' if present on same line
            text = re.split(r"\bObjet\b\s*:", text, flags=re.IGNORECASE)[0]

            patterns = [
                r"\b\d{1,6}/[A-Z]{1,10}/\d{4}\b",                 # 34/BP/2025
                r"\b[A-Z0-9]{1,20}/\d{4}/[A-Z0-9_-]+\b",           # TC4129613/2025/ONEEBELEC
                r"\b\d{1,6}/\d{4}/[A-Z0-9_-]+\b",                 # 336/2025/SRMCS
                r"\b\d{1,6}/[A-Z0-9_-]{2,20}/\d{4}\b",            # 21/DAAF/FNAC/2025
                r"\b\d{1,6}/\d{4}\b",                             # 08/2026
            ]
            for pat in patterns:
                mm = re.search(pat, text)
                if mm:
                    return mm.group(0)

            first_line = (text.splitlines()[0] if text.splitlines() else text).strip()
            first_token = re.split(r"\s+", first_line)[0]
            first_token = re.sub(r"[^A-Za-z0-9/_-]", "", first_token)
            return first_token or ""



        for tr in soup.find_all("tr"):
            detail_a = None
            for a in tr.find_all("a", href=True):
                href = a["href"]
                if "EntrepriseDetailsConsultation" in href and "refConsultation=" in href:
                    detail_a = a
                    break
            if not detail_a:
                continue

            detail_url = self._abs_url(detail_a["href"])
            lines = clean_lines(tr)
            lines_clean = [ln for ln in lines if not is_bad_line(ln)]
            full = "\n".join(lines_clean)

            ref = extract_reference(full)

            objet = ""
            m = re.search(r"Objet\s*:\s*(.+)", full, flags=re.IGNORECASE)
            if m:
                objet = self._norm(m.group(1))
            else:
                objet = self._norm(detail_a.get_text(" ", strip=True))

            org = ""
            m = re.search(r"Acheteur\s+public\s*:\s*(.+)", full, flags=re.IGNORECASE)
            if m:
                org = self._norm(m.group(1))
                # falls der Match doch Action-Text enthält -> leeren
                if is_bad_line(org):
                    org = ""

            lieux = pick_location(lines_clean)

            publication_dd, deadline_dd = pick_published_and_deadline(lines_clean)
            time_dead = pick_time(lines_clean)

            row_data = {
                "reference": ref,
                "objet": objet,
                "lieux": lieux if not is_bad_line(lieux) else "",
                "organisation_raw": org if not is_bad_line(org) else "",
                "date_publication_raw": publication_dd or "",
                "date_limite_raw": (deadline_dd or "") + (f" {time_dead}" if time_dead else ""),
            }

            results.append((row_data, detail_url))

        try:
            results = safkaty_expand_rows_with_lots(results)
        except Exception:
            pass

        return results

    def search(self, keyword: str, max_results: int = 20, polite_delay: float = 0.8, enrich_details: bool = True) -> List[Tender]:
        keyword = keyword.strip()
        soup = self._fetch_search_soup(keyword)

        rows = self._parse_result_table(soup)

        # Fallback: wenn Parser keine Tabelle findet, trotzdem echte Detail-Links nutzen
        if not rows:
            detail_links = self._extract_detail_links_fallback(soup)
            if not detail_links:
                return []
            rows = [({}, u) for u in detail_links[:max_results]]

        tenders: List[Tender] = []
        for row_data, detail_url in rows[:max_results]:
            ref = (row_data.get("reference") if row_data else "") or ""
            objet = (row_data.get("objet") if row_data else "") or ""
            lieux = (row_data.get("lieux") if row_data else "") or ""

            dead_raw = (row_data.get("date_limite_raw") if row_data else "") or ""
            echeance = parse_date_ddmmyyyy(dead_raw)
            tm = re.search(r"\b(\d{1,2}:\d{2})\b", dead_raw)
            echeance_time = tm.group(1) if tm else ""

            publication_raw = (row_data.get("date_publication_raw") if row_data else "") or ""
            publication = parse_date_ddmmyyyy(publication_raw)

            extra: Dict[str, str] = {}
            if enrich_details:
                try:
                    extra = self.fetch_details_by_url(detail_url)
                except Exception:
                    extra = {}

            if not ref:
                ref = extra.get("reference", "") or ""
            if not objet:
                objet = extra.get("objet", "") or objet

            final_lieux = extra.get("lieux") or lieux
            final_org = extra.get("organisation") or ""
            final_cat = extra.get("categorie") or ""
            final_email = extra.get("contact_email") or ""
            final_phone = extra.get("contact_phone") or ""

            est = safe_float_amount(extra.get("estimation", ""))
            cau = safe_float_amount(extra.get("caution", ""))

            if extra.get("echeance"):
                echeance = extra.get("echeance") or echeance
            if extra.get("echeance_time"):
                echeance_time = extra.get("echeance_time") or echeance_time

            
            # If consultation has multiple LOTS, list each LOT as its own row (same reference + lot suffix)
            lots = []
            if extra.get("lots_json"):
                try:
                    import json as _json
                    lots = _json.loads(extra.get("lots_json") or "[]") or []
                except Exception:
                    lots = []

            if isinstance(lots, list) and len(lots) >= 1 and any(isinstance(x, dict) and x.get('lot') for x in lots):
                for lot in lots:
                    lot_no = lot.get("lot") if isinstance(lot, dict) else None
                    lot_title = lot.get("lot_title", "") if isinstance(lot, dict) else ""
                    lot_est = safe_float_amount((lot.get("estimation", "") if isinstance(lot, dict) else "") or "")
                    lot_cau = safe_float_amount((lot.get("caution", "") if isinstance(lot, dict) else "") or "")
                    lot_ref = ref or "(unknown)"
                    if lot_no:
                        lot_ref = f"{lot_ref} [Lot {lot_no}]"
                    lot_obj = lot_title.strip() or objet

                    tenders.append(Tender(
                        reference=lot_ref,
                        titre=lot_obj,
                        lieux=final_lieux,
                        estimation=lot_est,
                        caution=lot_cau,
                        echeance=echeance,
                        echeance_time=echeance_time,
                        organisation=final_org,
                        publication=publication,
                        categorie=final_cat,
                        description=objet,
                        contact_email=final_email,
                        contact_phone=final_phone,
                        url=detail_url
                    ))
                time.sleep(polite_delay)
                continue

            tenders.append(Tender(
                reference=ref or "(unknown)",
                titre=objet,
                lieux=final_lieux,
                estimation=est,
                caution=cau,
                echeance=echeance,
                echeance_time=echeance_time,
                organisation=final_org,
                publication=publication,
                categorie=final_cat,
                description=objet,
                contact_email=final_email,
                contact_phone=final_phone,
                url=detail_url
            ))
            time.sleep(polite_delay)

        return tenders


class SafkatyApp:
    def __init__(self):
        self.db = Database()
        self.scraper = MarchesPublicsScraper()
        self.q = queue.Queue()

        self.root = tk.Tk()
        self.root.title("SAFKATY • Marchés Publics Manager")
        self.root.geometry("1400x900")
        self.root.minsize(1180, 780)

        self._style()
        self._build_ui()

        self.root.after(100, self._process_queue)
        self._refresh_dashboard()
        self._load_my_tenders()

    def _style(self):
        self.root.configure(bg="#0b1220")
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure("TFrame", background="#0b1220")
        style.configure("TLabel", background="#0b1220", foreground="#e8eefc", font=("Segoe UI", 10))
        style.configure("Header.TLabel", background="#0b1220", foreground="#e8eefc", font=("Segoe UI", 18, "bold"))
        style.configure("SubHeader.TLabel", background="#0b1220", foreground="#a8b3cf", font=("Segoe UI", 10))

        style.configure("Card.TFrame", background="#121b2e", relief="flat")
        style.configure("CardTitle.TLabel", background="#121b2e", foreground="#a8b3cf", font=("Segoe UI", 10))
        style.configure("CardValue.TLabel", background="#121b2e", foreground="#e8eefc", font=("Segoe UI", 22, "bold"))

        style.configure("TNotebook", background="#0b1220", borderwidth=0)
        style.configure("TNotebook.Tab", padding=(14, 8), font=("Segoe UI", 10, "bold"))
        style.map("TNotebook.Tab",
                  background=[("selected", "#121b2e")],
                  foreground=[("selected", "#e8eefc"), ("!selected", "#a8b3cf")])

        style.configure("Treeview",
                        background="#121b2e",
                        fieldbackground="#121b2e",
                        foreground="#e8eefc",
                        rowheight=28,
                        bordercolor="#1f2a44",
                        borderwidth=0)
        style.configure("Treeview.Heading",
                        background="#0f1729",
                        foreground="#a8b3cf",
                        font=("Segoe UI", 10, "bold"))
        style.map("Treeview", background=[("selected", "#1f2a44")])

        style.configure("TButton", font=("Segoe UI", 10, "bold"), padding=(10, 8))
        style.configure("Primary.TButton", background="#2b63ff", foreground="white")
        style.map("Primary.TButton", background=[("active", "#1f4fe0")])

        style.configure("Danger.TButton", background="#d93b3b", foreground="white")
        style.map("Danger.TButton", background=[("active", "#b83232")])

        style.configure("TEntry", fieldbackground="#121b2e", foreground="#e8eefc")
        style.configure("TCombobox", fieldbackground="#121b2e", foreground="#e8eefc")

    def _build_ui(self):
        top = ttk.Frame(self.root)
        top.pack(fill="x", padx=16, pady=(14, 10))

        ttk.Label(top, text="SAFKATY", style="Header.TLabel").pack(side="left")
        ttk.Label(top, text="• Ausschreibungen von marchespublics.gov.ma verwalten",
                  style="SubHeader.TLabel").pack(side="left", padx=(10, 0))

        self.status_var = tk.StringVar(value="Bereit.")
        ttk.Label(top, textvariable=self.status_var, style="SubHeader.TLabel").pack(side="right")

        self.nb = ttk.Notebook(self.root)
        self.nb.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        self.tab_dashboard = ttk.Frame(self.nb)
        self.tab_search = ttk.Frame(self.nb)
        self.tab_my = ttk.Frame(self.nb)
        self.tab_details = ttk.Frame(self.nb)
        self.tab_settings = ttk.Frame(self.nb)

        self.nb.add(self.tab_dashboard, text="🏠 Dashboard")
        self.nb.add(self.tab_search, text="🔎 Web-Suche")
        self.nb.add(self.tab_my, text="📌 Meine AO")
        self.nb.add(self.tab_details, text="📄 Details")
        self.nb.add(self.tab_settings, text="⚙️ Settings")

        self._build_dashboard()
        self._build_search()
        self._build_my()
        self._build_details()
        self._build_settings()

        bottom = ttk.Frame(self.root)
        bottom.pack(fill="x", padx=16, pady=(0, 14))
        self.progress = ttk.Progressbar(bottom, mode="indeterminate")
        self.progress.pack(side="right", fill="x", expand=False)

    def _make_card(self, parent, title: str, value: str):
        f = ttk.Frame(parent, style="Card.TFrame")
        ttk.Label(f, text=title, style="CardTitle.TLabel").pack(anchor="w", padx=12, pady=(10, 0))
        val = ttk.Label(f, text=value, style="CardValue.TLabel")
        val.pack(anchor="w", padx=12, pady=(0, 12))
        f.value_label = val  # type: ignore
        return f

    def _build_dashboard(self):
        container = ttk.Frame(self.tab_dashboard)
        container.pack(fill="both", expand=True, padx=6, pady=6)

        cards = ttk.Frame(container)
        cards.pack(fill="x", pady=(0, 12))

        self.card_total = self._make_card(cards, "TOTAL", "0")
        self.card_neu = self._make_card(cards, "NEU", "0")
        self.card_bearb = self._make_card(cards, "IN BEARBEITUNG", "0")
        self.card_done = self._make_card(cards, "ERLEDIGT", "0")

        self.card_total.pack(side="left", expand=True, fill="x", padx=6)
        self.card_neu.pack(side="left", expand=True, fill="x", padx=6)
        self.card_bearb.pack(side="left", expand=True, fill="x", padx=6)
        self.card_done.pack(side="left", expand=True, fill="x", padx=6)

        actions = ttk.Frame(container)
        actions.pack(fill="x", pady=(0, 10))

        ttk.Button(actions, text="🔎 Zur Web-Suche", style="Primary.TButton",
                   command=lambda: self.nb.select(self.tab_search)).pack(side="left", padx=4)
        ttk.Button(actions, text="📌 Meine AO", command=lambda: self.nb.select(self.tab_my)).pack(side="left", padx=4)
        ttk.Button(actions, text="🔄 Refresh", command=self._refresh_dashboard).pack(side="left", padx=4)

        box = ttk.Frame(container, style="Card.TFrame")
        box.pack(fill="both", expand=True, padx=6, pady=6)

        ttk.Label(box, text="⏳ Übersicht (Priorität & Frist)", style="CardTitle.TLabel").pack(anchor="w", padx=12, pady=(10, 6))

        cols = ("Ref", "Titre", "Organisation", "Lieux", "Estimation", "Caution", "Échéance", "Status", "Prio")
        self.dashboard_tree = ttk.Treeview(box, columns=cols, show="headings", height=12)
        for c in cols:
            self.dashboard_tree.heading(c, text=c)
        self.dashboard_tree.column("Ref", width=150)
        self.dashboard_tree.column("Titre", width=420)
        self.dashboard_tree.column("Organisation", width=240)
        self.dashboard_tree.column("Lieux", width=240)
        self.dashboard_tree.column("Estimation", width=120, anchor="e")
        self.dashboard_tree.column("Caution", width=120, anchor="e")
        self.dashboard_tree.column("Échéance", width=140, anchor="center")
        self.dashboard_tree.column("Status", width=140, anchor="center")
        self.dashboard_tree.column("Prio", width=60, anchor="center")

        sb = ttk.Scrollbar(box, orient="vertical", command=self.dashboard_tree.yview)
        self.dashboard_tree.configure(yscrollcommand=sb.set)
        self.dashboard_tree.pack(side="left", fill="both", expand=True, padx=(12, 0), pady=(0, 12))
        sb.pack(side="right", fill="y", padx=(0, 12), pady=(0, 12))

    def _build_search(self):
        container = ttk.Frame(self.tab_search)
        container.pack(fill="both", expand=True, padx=6, pady=6)

        panel = ttk.Frame(container, style="Card.TFrame")
        panel.pack(fill="x", padx=6, pady=6)

        row = ttk.Frame(panel, style="Card.TFrame")
        row.pack(fill="x", padx=12, pady=12)

        ttk.Label(row, text="Keyword:", style="CardTitle.TLabel").pack(side="left")
        self.keyword_var = tk.StringVar(value="piste")
        self.keyword_entry = ttk.Entry(row, textvariable=self.keyword_var, width=50)
        self.keyword_entry.pack(side="left", padx=8)
        self.keyword_entry.bind("<Return>", lambda e: self._start_search())

        ttk.Label(row, text="Max:", style="CardTitle.TLabel").pack(side="left", padx=(10, 0))
        self.max_var = tk.IntVar(value=10)
        self.max_spin = ttk.Spinbox(row, from_=5, to=60, textvariable=self.max_var, width=6)
        self.max_spin.pack(side="left", padx=8)

        ttk.Button(row, text="🚀 Suchen", style="Primary.TButton", command=self._start_search).pack(side="left", padx=8)
        ttk.Button(row, text="🧹 Clear", command=self._clear_search_results).pack(side="left", padx=4)

        box = ttk.Frame(container, style="Card.TFrame")
        box.pack(fill="both", expand=True, padx=6, pady=6)

        ttk.Label(box, text="Ergebnisse (Web)", style="CardTitle.TLabel").pack(anchor="w", padx=12, pady=(10, 6))

        cols = ("Reference", "Titre", "Lieux", "Estimation", "Caution", "Échéance", "Organisation", "URL")
        self.search_tree = ttk.Treeview(box, columns=cols, show="headings", height=16)
        for c in cols:
            self.search_tree.heading(c, text=c)

        self.search_tree.column("Reference", width=180)
        self.search_tree.column("Titre", width=520)
        self.search_tree.column("Lieux", width=280)
        self.search_tree.column("Estimation", width=120, anchor="e")
        self.search_tree.column("Caution", width=120, anchor="e")
        self.search_tree.column("Échéance", width=140, anchor="center")
        self.search_tree.column("Organisation", width=260)
        self.search_tree.column("URL", width=320)

        sb = ttk.Scrollbar(box, orient="vertical", command=self.search_tree.yview)
        self.search_tree.configure(yscrollcommand=sb.set)
        self.search_tree.pack(side="left", fill="both", expand=True, padx=(12, 0), pady=(0, 12))
        sb.pack(side="right", fill="y", padx=(0, 12), pady=(0, 12))

        btns = ttk.Frame(container)
        btns.pack(fill="x", padx=6, pady=(6, 0))

        ttk.Button(btns, text="✅ Auswahl importieren", style="Primary.TButton",
                   command=self._import_selected).pack(side="left", padx=4)
        ttk.Button(btns, text="📥 Alles importieren", command=self._import_all).pack(side="left", padx=4)
        ttk.Button(btns, text="🌐 URL öffnen", command=self._open_search_url).pack(side="left", padx=4)

        logbox = ttk.Frame(container, style="Card.TFrame")
        logbox.pack(fill="x", padx=6, pady=6)
        ttk.Label(logbox, text="Log", style="CardTitle.TLabel").pack(anchor="w", padx=12, pady=(10, 6))
        self.log = ScrolledText(logbox, height=6, bg="#0f1729", fg="#e8eefc", insertbackground="#e8eefc",
                                font=("Consolas", 9), relief="flat", borderwidth=0)
        self.log.pack(fill="x", padx=12, pady=(0, 12))

    def _build_my(self):
        container = ttk.Frame(self.tab_my)
        container.pack(fill="both", expand=True, padx=6, pady=6)

        panel = ttk.Frame(container, style="Card.TFrame")
        panel.pack(fill="x", padx=6, pady=6)

        row = ttk.Frame(panel, style="Card.TFrame")
        row.pack(fill="x", padx=12, pady=12)

        ttk.Label(row, text="Suche:", style="CardTitle.TLabel").pack(side="left")
        self.my_search_var = tk.StringVar(value="")
        e = ttk.Entry(row, textvariable=self.my_search_var, width=40)
        e.pack(side="left", padx=8)
        e.bind("<Return>", lambda ev: self._load_my_tenders())

        ttk.Label(row, text="Status:", style="CardTitle.TLabel").pack(side="left", padx=(10, 0))
        self.status_filter_var = tk.StringVar(value="Alle")
        self.status_filter = ttk.Combobox(row, textvariable=self.status_filter_var, state="readonly",
                                          values=["Alle", "neu", "in_bearbeitung", "angebot_abgegeben", "gewonnen", "verloren", "abgebrochen"],
                                          width=18)
        self.status_filter.pack(side="left", padx=8)
        self.status_filter.bind("<<ComboboxSelected>>", lambda ev: self._load_my_tenders())

        ttk.Label(row, text="Prio:", style="CardTitle.TLabel").pack(side="left", padx=(10, 0))
        self.prio_filter_var = tk.StringVar(value="Alle")
        self.prio_filter = ttk.Combobox(row, textvariable=self.prio_filter_var, state="readonly",
                                        values=["Alle", "1", "2", "3"], width=6)
        self.prio_filter.pack(side="left", padx=8)
        self.prio_filter.bind("<<ComboboxSelected>>", lambda ev: self._load_my_tenders())

        ttk.Button(row, text="🔄 Refresh", command=self._load_my_tenders).pack(side="left", padx=8)
        ttk.Button(row, text="📤 Export CSV", command=self._export_csv).pack(side="left", padx=4)

        box = ttk.Frame(container, style="Card.TFrame")
        box.pack(fill="both", expand=True, padx=6, pady=6)

        ttk.Label(box, text="Meine Ausschreibungen", style="CardTitle.TLabel").pack(anchor="w", padx=12, pady=(10, 6))

        cols = ("ID", "Ref", "Titre", "Organisation", "Lieux", "Est", "Caution", "Échéance", "Status", "Prio")
        self.my_tree = ttk.Treeview(box, columns=cols, show="headings", height=18)
        for c in cols:
            self.my_tree.heading(c, text=c)

        self.my_tree.column("ID", width=60, anchor="center")
        self.my_tree.column("Ref", width=180)
        self.my_tree.column("Titre", width=460)
        self.my_tree.column("Organisation", width=260)
        self.my_tree.column("Lieux", width=280)
        self.my_tree.column("Est", width=120, anchor="e")
        self.my_tree.column("Caution", width=120, anchor="e")
        self.my_tree.column("Échéance", width=140, anchor="center")
        self.my_tree.column("Status", width=140, anchor="center")
        self.my_tree.column("Prio", width=60, anchor="center")

        sb = ttk.Scrollbar(box, orient="vertical", command=self.my_tree.yview)
        self.my_tree.configure(yscrollcommand=sb.set)
        self.my_tree.pack(side="left", fill="both", expand=True, padx=(12, 0), pady=(0, 12))
        sb.pack(side="right", fill="y", padx=(0, 12), pady=(0, 12))

        self.my_tree.bind("<Double-1>", lambda e: self._open_selected_details())

        btns = ttk.Frame(container)
        btns.pack(fill="x", padx=6, pady=(6, 0))

        ttk.Button(btns, text="📄 Details öffnen", style="Primary.TButton", command=self._open_selected_details).pack(side="left", padx=4)
        ttk.Button(btns, text="🌐 URL öffnen", command=self._open_selected_url).pack(side="left", padx=4)
        ttk.Button(btns, text="🗑️ Löschen", style="Danger.TButton", command=self._delete_selected).pack(side="left", padx=4)

    def _build_details(self):
        container = ttk.Frame(self.tab_details)
        container.pack(fill="both", expand=True, padx=6, pady=6)

        left = ttk.Frame(container, style="Card.TFrame")
        right = ttk.Frame(container, style="Card.TFrame")
        left.pack(side="left", fill="both", expand=True, padx=(6, 3), pady=6)
        right.pack(side="right", fill="both", expand=True, padx=(3, 6), pady=6)

        ttk.Label(left, text="Tender Details", style="CardTitle.TLabel").pack(anchor="w", padx=12, pady=(10, 6))

        self.detail_labels: Dict[str, tk.StringVar] = {}
        fields = [
            ("reference", "Reference"),
            ("titre", "Objet"),
            ("organisation", "Acheteur public"),
            ("lieux", "Lieu d'exécution"),
            ("estimation", "Estimation"),
            ("caution", "Caution"),
            ("echeance", "Date limite"),
            ("categorie", "Catégorie"),
            ("contact_phone", "Téléphone"),
            ("contact_email", "Email"),
            ("url", "URL"),
        ]
        grid = ttk.Frame(left, style="Card.TFrame")
        grid.pack(fill="both", expand=False, padx=12, pady=(0, 12))

        r = 0
        for key, label in fields:
            ttk.Label(grid, text=f"{label}:", style="CardTitle.TLabel").grid(row=r, column=0, sticky="w", pady=4, padx=(0, 10))
            var = tk.StringVar(value="—")
            self.detail_labels[key] = var
            ttk.Label(grid, textvariable=var).grid(row=r, column=1, sticky="w", pady=4)
            r += 1

        ttk.Label(left, text="Beschreibung", style="CardTitle.TLabel").pack(anchor="w", padx=12, pady=(0, 6))
        self.detail_desc = ScrolledText(left, height=8, bg="#0f1729", fg="#e8eefc", insertbackground="#e8eefc",
                                        font=("Segoe UI", 10), relief="flat", borderwidth=0)
        self.detail_desc.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        ttk.Label(right, text="Workflow", style="CardTitle.TLabel").pack(anchor="w", padx=12, pady=(10, 6))
        wf = ttk.Frame(right, style="Card.TFrame")
        wf.pack(fill="x", padx=12, pady=(0, 12))

        ttk.Label(wf, text="Status:", style="CardTitle.TLabel").grid(row=0, column=0, sticky="w", pady=6)
        self.detail_status_var = tk.StringVar(value="neu")
        self.detail_status_cb = ttk.Combobox(
            wf, textvariable=self.detail_status_var, state="readonly",
            values=["neu", "in_bearbeitung", "angebot_abgegeben", "gewonnen", "verloren", "abgebrochen"],
            width=24
        )
        self.detail_status_cb.grid(row=0, column=1, sticky="w", pady=6, padx=8)

        ttk.Label(wf, text="Priorität:", style="CardTitle.TLabel").grid(row=1, column=0, sticky="w", pady=6)
        self.detail_prio_var = tk.IntVar(value=3)
        self.detail_prio_cb = ttk.Combobox(wf, textvariable=self.detail_prio_var, state="readonly", values=[1, 2, 3], width=6)
        self.detail_prio_cb.grid(row=1, column=1, sticky="w", pady=6, padx=8)

        btnrow = ttk.Frame(right, style="Card.TFrame")
        btnrow.pack(fill="x", padx=12, pady=(0, 8))
        ttk.Button(btnrow, text="💾 Status speichern", style="Primary.TButton", command=self._save_workflow).pack(side="left", padx=4)
        ttk.Button(btnrow, text="🌐 URL öffnen", command=self._open_detail_url).pack(side="left", padx=4)

        ttk.Label(right, text="Notizen", style="CardTitle.TLabel").pack(anchor="w", padx=12, pady=(6, 6))
        self.detail_notes = ScrolledText(right, height=14, bg="#0f1729", fg="#e8eefc", insertbackground="#e8eefc",
                                         font=("Segoe UI", 10), relief="flat", borderwidth=0)
        self.detail_notes.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        ttk.Button(right, text="💾 Notizen speichern", command=self._save_notes).pack(anchor="w", padx=12, pady=(0, 12))

        self.current_tender_id: Optional[int] = None

    def _build_settings(self):
        container = ttk.Frame(self.tab_settings)
        container.pack(fill="both", expand=True, padx=6, pady=6)

        box = ttk.Frame(container, style="Card.TFrame")
        box.pack(fill="x", padx=6, pady=6)

        ttk.Label(box, text="Scraper Settings", style="CardTitle.TLabel").pack(anchor="w", padx=12, pady=(10, 6))

        row = ttk.Frame(box, style="Card.TFrame")
        row.pack(fill="x", padx=12, pady=(0, 12))

        ttk.Label(row, text="Base URL:", style="CardTitle.TLabel").pack(side="left")
        self.base_url_var = tk.StringVar(value=self.scraper.base_url)
        ttk.Entry(row, textvariable=self.base_url_var, width=50).pack(side="left", padx=8)
        ttk.Button(row, text="✅ Übernehmen", style="Primary.TButton", command=self._apply_settings).pack(side="left", padx=8)

        info = ("Tipp: Stell 'Max' zuerst auf 10, um Block/CAPTCHA zu vermeiden.")
        ttk.Label(container, text=info, foreground="#a8b3cf", background="#0b1220", justify="left").pack(anchor="w", padx=14, pady=10)

    def _apply_settings(self):
        url = self.base_url_var.get().strip().rstrip("/")
        if not url.startswith("http"):
            messagebox.showerror("Fehler", "Bitte eine gültige URL eingeben, z.B. https://www.marchespublics.gov.ma")
            return
        self.scraper = MarchesPublicsScraper(url)
        self._log(f"Base URL gesetzt auf: {url}")
        self.status_var.set("Settings gespeichert.")

    def _log(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        try:
            self.log.insert("end", f"[{ts}] {msg}\n")
            self.log.see("end")
        except Exception:
            pass

    def _set_busy(self, busy: bool, text: str = ""):
        if busy:
            self.status_var.set(text or "Lade…")
            self.progress.start(10)
        else:
            self.progress.stop()
            self.status_var.set(text or "Bereit.")

    def _start_search(self):
        kw = self.keyword_var.get().strip()
        if not kw:
            messagebox.showwarning("Hinweis", "Bitte Keyword eingeben.")
            return
        maxr = int(self.max_var.get())
        self._set_busy(True, f"Suche '{kw}' …")
        self._log(f"Starte Suche: '{kw}' (max {maxr})")
        threading.Thread(target=self._worker_search, args=(kw, maxr), daemon=True).start()

    def _worker_search(self, kw: str, maxr: int):
        try:
            tenders = self.scraper.search(kw, max_results=maxr)
            self.q.put(("SEARCH_OK", tenders))
        except Exception as e:
            self.q.put(("SEARCH_ERR", str(e)))

    def _show_search_results(self, tenders: List[Tender]):
        for it in self.search_tree.get_children():
            self.search_tree.delete(it)
        for t in tenders:
            self.search_tree.insert("", "end", values=(
                t.reference,
                (t.titre or "")[:220],
                (t.lieux or "")[:220],
                fmt_money(t.estimation),
                fmt_money(t.caution),
                (fmt_date_iso(t.echeance) + (f" {t.echeance_time}" if t.echeance_time else "")).strip(),
                (t.organisation or "")[:120],
                (t.url or "")[:200],
            ))
        self._set_busy(False, f"{len(tenders)} Ergebnisse.")
        self._log(f"Fertig: {len(tenders)} Ergebnisse geladen.")

    def _clear_search_results(self):
        for it in self.search_tree.get_children():
            self.search_tree.delete(it)
        self._log("Suchergebnisse gelöscht.")
        self.status_var.set("Bereit.")

    def _open_search_url(self):
        sel = self.search_tree.selection()
        if not sel:
            messagebox.showwarning("Hinweis", "Bitte Ergebnis auswählen.")
            return
        url = self.search_tree.item(sel[0], "values")[7]
        if url:
            webbrowser.open(url)

    def _import_selected(self):
        sel = self.search_tree.selection()
        if not sel:
            messagebox.showwarning("Hinweis", "Bitte mindestens 1 Ergebnis auswählen.")
            return
        imported = 0
        for item in sel:
            vals = self.search_tree.item(item, "values")
            ref = vals[0]
            url = vals[7]
            try:
                extra = self.scraper.fetch_details_by_url(url)
            except Exception:
                extra = {}
            t = Tender(
                reference=ref,
                titre=vals[1],
                lieux=vals[2] if vals[2] != "—" else "",
                estimation=safe_float_amount(vals[3]),
                caution=safe_float_amount(vals[4]),
                echeance=parse_date_ddmmyyyy(vals[5]) or (extra.get("echeance") or None),
                echeance_time=extra.get("echeance_time",""),
                organisation=vals[6] if vals[6] != "—" else "",
                contact_email=extra.get("contact_email",""),
                contact_phone=extra.get("contact_phone",""),
                categorie=extra.get("categorie",""),
                url=url
            )
            new, _ = self.db.upsert_tender(t)
            if new:
                imported += 1
        messagebox.showinfo("Import", f"Import abgeschlossen. Neu: {imported}")
        self._load_my_tenders()
        self._refresh_dashboard()

    def _import_all(self):
        items = self.search_tree.get_children()
        if not items:
            messagebox.showwarning("Hinweis", "Keine Ergebnisse vorhanden.")
            return
        if not messagebox.askyesno("Import", f"Wirklich ALLE ({len(items)}) importieren?"):
            return
        self.search_tree.selection_set(items)
        self._import_selected()

    def _load_my_tenders(self):
        rows = self.db.list_tenders(
            search=self.my_search_var.get(),
            status=self.status_filter_var.get() if self.status_filter_var.get() != "Alle" else "Alle",
            priority=self.prio_filter_var.get() if self.prio_filter_var.get() != "Alle" else "Alle",
        )
        for it in self.my_tree.get_children():
            self.my_tree.delete(it)
        for r in rows:
            tid, ref, titre, org, lieux, est, cau, ech, st, pr = r
            self.my_tree.insert("", "end", values=(
                tid, ref, (titre or "")[:180], (org or "")[:120], (lieux or "")[:140],
                fmt_money(est), fmt_money(cau), fmt_date_iso(ech), st, pr
            ))

    def _refresh_dashboard(self):
        st = self.db.stats()
        total = st.get("TOTAL", 0)
        neu = st.get("neu", 0)
        bearb = st.get("in_bearbeitung", 0)
        done = st.get("gewonnen", 0) + st.get("verloren", 0) + st.get("abgebrochen", 0)
        self.card_total.value_label.config(text=str(total))  # type: ignore
        self.card_neu.value_label.config(text=str(neu))      # type: ignore
        self.card_bearb.value_label.config(text=str(bearb))  # type: ignore
        self.card_done.value_label.config(text=str(done))    # type: ignore

        rows = self.db.list_tenders(search="", status="Alle", priority="Alle")[:50]
        for it in self.dashboard_tree.get_children():
            self.dashboard_tree.delete(it)
        for r in rows:
            tid, ref, titre, org, lieux, est, cau, ech, stt, pr = r
            self.dashboard_tree.insert("", "end", values=(
                ref, (titre or "")[:140], (org or "")[:120], (lieux or "")[:120],
                fmt_money(est), fmt_money(cau), fmt_date_iso(ech), stt, pr
            ))

    def _open_selected_details(self):
        sel = self.my_tree.selection()
        if not sel:
            messagebox.showwarning("Hinweis", "Bitte in 'Meine AO' etwas auswählen.")
            return
        tid = int(self.my_tree.item(sel[0], "values")[0])
        self._load_details(tid)
        self.nb.select(self.tab_details)

    def _load_details(self, tender_id: int):
        data = self.db.get_tender(tender_id)
        if not data:
            return
        self.current_tender_id = tender_id
        self.detail_labels["reference"].set(data.get("reference") or "—")
        self.detail_labels["titre"].set(data.get("titre") or "—")
        self.detail_labels["organisation"].set(data.get("organisation") or "—")
        self.detail_labels["lieux"].set(data.get("lieux") or "—")
        self.detail_labels["estimation"].set(fmt_money(data.get("estimation")))
        self.detail_labels["caution"].set(fmt_money(data.get("caution")))
        dt = fmt_date_iso(data.get("echeance"))
        if data.get("echeance_time"):
            dt = f"{dt} {data.get('echeance_time')}"
        self.detail_labels["echeance"].set(dt)
        self.detail_labels["categorie"].set(data.get("categorie") or "—")
        self.detail_labels["contact_phone"].set(data.get("contact_phone") or "—")
        self.detail_labels["contact_email"].set(data.get("contact_email") or "—")
        self.detail_labels["url"].set(data.get("url") or "—")
        self.detail_desc.delete("1.0", "end")
        self.detail_desc.insert("1.0", data.get("description") or "")
        self.detail_status_var.set(data.get("status") or "neu")
        self.detail_prio_var.set(int(data.get("priority") or 3))
        self.detail_notes.delete("1.0", "end")
        self.detail_notes.insert("1.0", data.get("notes") or "")

    def _save_workflow(self):
        if not self.current_tender_id:
            return
        self.db.update_status(self.current_tender_id, self.detail_status_var.get())
        self.db.update_priority(self.current_tender_id, int(self.detail_prio_var.get()))
        self._load_my_tenders()
        self._refresh_dashboard()
        messagebox.showinfo("Gespeichert", "Status/Priorität gespeichert.")

    def _save_notes(self):
        if not self.current_tender_id:
            return
        notes = self.detail_notes.get("1.0", "end").strip()
        self.db.update_notes(self.current_tender_id, notes)
        messagebox.showinfo("Gespeichert", "Notizen gespeichert.")

    def _open_detail_url(self):
        url = self.detail_labels["url"].get()
        if url and url != "—":
            webbrowser.open(url)

    def _open_selected_url(self):
        sel = self.my_tree.selection()
        if not sel:
            messagebox.showwarning("Hinweis", "Bitte Ausschreibung auswählen.")
            return
        tid = int(self.my_tree.item(sel[0], "values")[0])
        data = self.db.get_tender(tid)
        if data and data.get("url"):
            webbrowser.open(data["url"])
        else:
            messagebox.showwarning("Hinweis", "Keine URL gespeichert.")

    def _delete_selected(self):
        sel = self.my_tree.selection()
        if not sel:
            messagebox.showwarning("Hinweis", "Bitte Ausschreibung auswählen.")
            return
        tid = int(self.my_tree.item(sel[0], "values")[0])
        if not messagebox.askyesno("Löschen", "Wirklich löschen?"):
            return
        cur = self.db.conn.cursor()
        cur.execute("DELETE FROM tender_status WHERE tender_id=?", (tid,))
        cur.execute("DELETE FROM tenders WHERE id=?", (tid,))
        self.db.conn.commit()
        self._load_my_tenders()
        self._refresh_dashboard()

    def _export_csv(self):
        rows = self.db.list_tenders(
            search=self.my_search_var.get(),
            status=self.status_filter_var.get() if self.status_filter_var.get() != "Alle" else "Alle",
            priority=self.prio_filter_var.get() if self.prio_filter_var.get() != "Alle" else "Alle",
        )
        if not rows:
            messagebox.showwarning("Export", "Keine Daten zum Export.")
            return
        fn = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")], initialfile="safkaty_export.csv")
        if not fn:
            return
        with open(fn, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(["ID", "Reference", "Objet", "Acheteur", "Lieu", "Estimation", "Caution", "Echeance", "Status", "Priority", "URL"])
            for r in rows:
                tid, ref, titre, org, lieux, est, cau, ech, st, pr = r
                data = self.db.get_tender(tid) or {}
                w.writerow([tid, ref, titre, org, lieux, est, cau, ech, st, pr, data.get("url","")])
        messagebox.showinfo("Export", f"Exportiert: {fn}")

    def _process_queue(self):
        try:
            while True:
                typ, payload = self.q.get_nowait()
                if typ == "SEARCH_OK":
                    self._show_search_results(payload)
                elif typ == "SEARCH_ERR":
                    self._set_busy(False, "Fehler.")
                    messagebox.showerror("Scraper Fehler", payload)
                    self._log(f"ERROR: {payload}")
                self.q.task_done()
        except queue.Empty:
            pass
        self.root.after(100, self._process_queue)

    def run(self):
        self.root.mainloop()
        self.db.close()


def main():
    app = SafkatyApp()
    app.run()


if __name__ == "__main__":
    main()
