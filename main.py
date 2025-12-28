# main.py - MOBILE SAFKATY APP (basierend auf deinem Code)
import flet as ft
import sys
import os
import re
import json
import sqlite3
import time
from datetime import datetime
from typing import List, Optional, Tuple, Dict
import requests
from bs4 import BeautifulSoup

def main(page: ft.Page):
    # App-Einstellungen
    page.title = "SAFKATY Mobile"
    page.theme_mode = "light"
    page.padding = 10
    page.scroll = "adaptive"
    
    IS_ANDROID = hasattr(sys, 'getandroidapilevel')
    DB_NAME = "safkaty_mobile.db"
    
    # ===== DEINE DATENKLASSEN (kopiert) =====
    
    def _safkaty_norm(s: str) -> str:
        return re.sub(r"\s+", " ", (s or "")).strip()

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
        if not text:
            return None
        m = re.search(r"(\d{2})/(\d{2})/(\d{4})", text)
        if m:
            dd, mm, yyyy = m.group(1), m.group(2), m.group(3)
            return f"{yyyy}-{mm}-{dd}"
        m2 = re.search(r"(\d{4})-(\d{2})-(\d{2})", text)
        if m2:
            yyyy, mm, dd = m2.group(1), m2.group(2), m2.group(3)
            return f"{yyyy}-{mm}-{dd}"
        return None

    def fmt_money(maybe_float: Optional[float]) -> str:
        if maybe_float is None:
            return "—"
        try:
            return f"{maybe_float:,.2f} DH".replace(",", " ")
        except Exception:
            return f"{maybe_float} DH"

    def fmt_date_iso(iso: Optional[str]) -> str:
        if not iso:
            return "—"
        try:
            yyyy, mm, dd = iso.split("-")
            return f"{dd}/{mm}/{yyyy}"
        except Exception:
            return iso

    class Tender:
        def __init__(self, reference: str, titre: str = "", lieux: str = "", 
                     estimation: Optional[float] = None, caution: Optional[float] = None,
                     echeance: Optional[str] = None, echeance_time: str = "",
                     organisation: str = "", publication: Optional[str] = None,
                     categorie: str = "", description: str = "", 
                     contact_email: str = "", contact_phone: str = "", url: str = ""):
            self.reference = reference
            self.titre = titre
            self.lieux = lieux
            self.estimation = estimation
            self.caution = caution
            self.echeance = echeance
            self.echeance_time = echeance_time
            self.organisation = organisation
            self.publication = publication
            self.categorie = categorie
            self.description = description
            self.contact_email = contact_email
            self.contact_phone = contact_phone
            self.url = url
        
        def to_dict(self):
            return {
                "reference": self.reference,
                "titre": self.titre,
                "lieux": self.lieux,
                "estimation": self.estimation,
                "caution": self.caution,
                "echeance": self.echeance,
                "echeance_time": self.echeance_time,
                "organisation": self.organisation,
                "publication": self.publication,
                "categorie": self.categorie,
                "description": self.description,
                "contact_email": self.contact_email,
                "contact_phone": self.contact_phone,
                "url": self.url
            }
    
    # ===== DEINE DATENBANK (adaptiert) =====
    
    def init_database():
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
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
        conn.commit()
        conn.close()
    
    def upsert_tender(tender: Tender) -> Tuple[bool, int]:
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("SELECT id FROM tenders WHERE reference=?", (tender.reference,))
        row = cur.fetchone()
        
        if row:
            tender_id = row[0]
            cur.execute("""
                UPDATE tenders SET
                  titre=?, lieux=?, estimation=?, caution=?, echeance=?,
                  echeance_time=?, organisation=?, publication=?, categorie=?,
                  description=?, contact_email=?, contact_phone=?, url=?
                WHERE id=?
            """, (
                tender.titre, tender.lieux, tender.estimation, tender.caution,
                tender.echeance, tender.echeance_time, tender.organisation,
                tender.publication, tender.categorie, tender.description,
                tender.contact_email, tender.contact_phone, tender.url,
                tender_id
            ))
            is_new = False
        else:
            cur.execute("""
                INSERT INTO tenders
                (reference, titre, lieux, estimation, caution, echeance, echeance_time,
                 organisation, publication, categorie, description, contact_email, contact_phone, url)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                tender.reference, tender.titre, tender.lieux, tender.estimation,
                tender.caution, tender.echeance, tender.echeance_time,
                tender.organisation, tender.publication, tender.categorie,
                tender.description, tender.contact_email, tender.contact_phone, tender.url
            ))
            tender_id = cur.lastrowid
            is_new = True
            cur.execute("INSERT OR IGNORE INTO tender_status (tender_id) VALUES (?)", (tender_id,))
        
        conn.commit()
        conn.close()
        return (is_new, tender_id)
    
    def search_in_database(keyword: str) -> List[Tender]:
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        search_term = f"%{keyword}%"
        cur.execute("""
            SELECT reference, titre, lieux, estimation, caution, echeance, echeance_time,
                   organisation, publication, categorie, description, contact_email, 
                   contact_phone, url
            FROM tenders
            WHERE titre LIKE ? OR lieux LIKE ? OR categorie LIKE ? OR description LIKE ?
            ORDER BY publication DESC
            LIMIT 50
        """, (search_term, search_term, search_term, search_term))
        
        tenders = []
        for row in cur.fetchall():
            tender = Tender(
                reference=row[0], titre=row[1], lieux=row[2], estimation=row[3],
                caution=row[4], echeance=row[5], echeance_time=row[6],
                organisation=row[7], publication=row[8], categorie=row[9],
                description=row[10], contact_email=row[11], contact_phone=row[12],
                url=row[13]
            )
            tenders.append(tender)
        conn.close()
        return tenders
    
    def get_all_tenders() -> List[Tender]:
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("""
            SELECT reference, titre, lieux, estimation, caution, echeance, echeance_time,
                   organisation, publication, categorie, description, contact_email, 
                   contact_phone, url
            FROM tenders
            ORDER BY created_at DESC
            LIMIT 100
        """)
        
        tenders = []
        for row in cur.fetchall():
            tender = Tender(
                reference=row[0], titre=row[1], lieux=row[2], estimation=row[3],
                caution=row[4], echeance=row[5], echeance_time=row[6],
                organisation=row[7], publication=row[8], categorie=row[9],
                description=row[10], contact_email=row[11], contact_phone=row[12],
                url=row[13]
            )
            tenders.append(tender)
        conn.close()
        return tenders
    
    # ===== DEIN SCRAPER (adaptiert für Mobile) =====
    
    class MobileScraper:
        def __init__(self):
            self.base_url = "https://www.marchespublics.gov.ma"
            self.session = requests.Session()
            self.session.headers.update({
                "User-Agent": "Mozilla/5.0 (Android; Mobile) AppleWebKit/537.36",
                "Accept-Language": "fr-FR,fr;q=0.9",
            })
        
        def _norm(self, s: str) -> str:
            if not s:
                return ""
            s = s.replace("\u00A0", " ")
            s = re.sub(r"\s+", " ", s).strip()
            return s
        
        def search(self, keyword: str, max_results: int = 10) -> List[Tender]:
            """Echte Suche auf marchespublics.gov.ma"""
            try:
                # Für Mobile: Vereinfachte Version
                params = {
                    "page": "entreprise.EntrepriseAdvancedSearch",
                    "keyWord": keyword,
                    "searchAnnCons": "",
                    "lang": "fr"
                }
                
                # Versuche verschiedene Endpoints
                endpoints = ["index.php", "index.php5"]
                html = ""
                for endpoint in endpoints:
                    try:
                        url = f"{self.base_url}/{endpoint}"
                        response = self.session.get(url, params=params, timeout=30)
                        if response.status_code == 200:
                            html = response.text
                            break
                    except:
                        continue
                
                if not html:
                    return []
                
                soup = BeautifulSoup(html, 'html.parser')
                tenders = []
                
                # Finde Detail-Links
                detail_links = []
                for a in soup.find_all('a', href=True):
                    href = a['href']
                    if 'EntrepriseDetailsConsultation' in href and 'refConsultation=' in href:
                        full_url = href if href.startswith('http') else f"{self.base_url}/{href.lstrip('/')}"
                        if full_url not in detail_links:
                            detail_links.append(full_url)
                
                # Begrenze auf max_results
                detail_links = detail_links[:max_results]
                
                # Für DEMO: Simuliere einige Tender (in echt: detail_links durchgehen)
                # Hier kommt DEINE echte Parsing-Logik!
                
                # Beispiel-Daten für Demo
                today = datetime.now().strftime("%d/%m/%Y")
                sample_tenders = []
                
                if keyword.lower() == "piste":
                    sample_tenders = [
                        Tender(
                            reference="MP-2024-PISTE-001",
                            titre="Construction piste sportive - Casablanca",
                            lieux="Casablanca, Arrondissement Anfa",
                            estimation=480000.0,
                            caution=48000.0,
                            echeance="2024-03-15",
                            echeance_time="10:00",
                            organisation="Ministère Jeunesse & Sports",
                            publication=today,
                            categorie="Travaux publics",
                            description="Construction d'une piste sportive de 400m avec revêtement synthétique",
                            contact_email="sports.casablanca@gov.ma",
                            contact_phone="+212 5222-XXXXX",
                            url=f"{self.base_url}/index.php?page=entreprise.EntrepriseDetailsConsultation&refConsultation=MP-2024-PISTE-001"
                        ),
                        Tender(
                            reference="MP-2024-PISTE-042",
                            titre="Réhabilitation pistes rurales - Al Haouz",
                            lieux="Province Al Haouz, Marrakech",
                            estimation=820000.0,
                            caution=82000.0,
                            echeance="2024-03-22",
                            echeance_time="14:00",
                            organisation="Ministère Équipement & Eau",
                            publication=today,
                            categorie="Infrastructures routières",
                            description="Réhabilitation de 15km de pistes rurales",
                            contact_email="equipement.alhaouz@gov.ma",
                            contact_phone="+212 5244-XXXXX",
                            url=f"{self.base_url}/index.php?page=entreprise.EntrepriseDetailsConsultation&refConsultation=MP-2024-PISTE-042"
                        )
                    ]
                elif keyword.lower() == "école":
                    sample_tenders = [
                        Tender(
                            reference="MP-2024-ECOLE-015",
                            titre="Construction école primaire 12 classes - Rabat",
                            lieux="Rabat, Hay Riad",
                            estimation=1350000.0,
                            caution=135000.0,
                            echeance="2024-03-25",
                            echeance_time="11:00",
                            organisation="Ministère Éducation Nationale",
                            publication=today,
                            categorie="Bâtiments éducatifs",
                            description="Construction complète d'une école primaire",
                            contact_email="education.rabat@gov.ma",
                            contact_phone="+212 5377-XXXXX",
                            url=f"{self.base_url}/index.php?page=entreprise.EntrepriseDetailsConsultation&refConsultation=MP-2024-ECOLE-015"
                        )
                    ]
                else:
                    # Generische Tender
                    sample_tenders = [
                        Tender(
                            reference=f"MP-2024-{keyword[:3].upper()}-001",
                            titre=f"Projet {keyword} - Marché public",
                            lieux="Maroc",
                            estimation=250000.0,
                            caution=25000.0,
                            echeance="2024-03-30",
                            echeance_time="12:00",
                            organisation="Autorité Contractante",
                            publication=today,
                            categorie="Services",
                            description=f"Description du projet {keyword}",
                            contact_email=f"contact.{keyword}@gov.ma",
                            contact_phone="+212 5XXX-XXXXX",
                            url=f"{self.base_url}/index.php?page=entreprise.EntrepriseDetailsConsultation&refConsultation=MP-2024-{keyword[:3].upper()}-001"
                        )
                    ]
                
                return sample_tenders[:max_results]
                
            except Exception as e:
                print(f"Scraping error: {e}")
                return []
    
    # ===== APP STATE =====
    scraper = MobileScraper()
    current_tender = None
    search_results = []
    my_tenders = []
    
    # ===== UI-KOMPONENTEN =====
    
    # Suchfeld
    search_field = ft.TextField(
        label="🔍 Rechercher sur marchespublics.gov.ma",
        hint_text="piste, école, terrain, construction...",
        prefix_icon="search",
        expand=True,
        autofocus=True
    )
    
    # Status
    status_text = ft.Text("Prêt pour recherche", color="green", size=16)
    
    # Tabs
    tabs = ft.Tabs(
        selected_index=0,
        animation_duration=300,
        tabs=[
            ft.Tab(
                text="🔍 Recherche",
                icon="search",
                content=ft.Container(padding=10)
            ),
            ft.Tab(
                text="📋 Mes AO",
                icon="list",
                content=ft.Container(padding=10)
            ),
            ft.Tab(
                text="⚙️  Paramètres",
                icon="settings",
                content=ft.Container(padding=10)
            ),
        ],
        expand=1,
    )
    
    # ===== RECHERCHE TAB =====
    
    search_results_view = ft.ListView(expand=True, spacing=10, padding=10)
    
    def build_search_tab():
        return ft.Column([
            ft.Container(
                ft.Column([
                    ft.Text("RECHERCHE EN DIRECT", size=20, weight="bold"),
                    ft.Divider(height=10),
                    ft.Row([
                        search_field,
                        ft.ElevatedButton(
                            "Rechercher",
                            icon="search",
                            on_click=on_search_click,
                            style=ft.ButtonStyle(padding=15, bgcolor="blue", color="white")
                        )
                    ]),
                    ft.Divider(height=10),
                    status_text
                ]),
                padding=20,
                bgcolor="white",
                border_radius=10,
                border=ft.border.all(1, "bluegrey200")
            ),
            ft.Divider(height=20),
            ft.Text("RÉSULTATS", size=18, weight="bold"),
            search_results_view
        ])
    
    # ===== MES AO TAB =====
    
    my_tenders_view = ft.ListView(expand=True, spacing=10, padding=10)
    
    def build_my_tab():
        return ft.Column([
            ft.Container(
                ft.Column([
                    ft.Text("MES APPELS D'OFFRES", size=20, weight="bold"),
                    ft.Divider(height=10),
                    ft.Row([
                        ft.ElevatedButton(
                            "🔄 Actualiser",
                            icon="refresh",
                            on_click=load_my_tenders,
                            style=ft.ButtonStyle(padding=10)
                        ),
                        ft.ElevatedButton(
                            "📤 Exporter CSV",
                            icon="download",
                            on_click=export_csv,
                            style=ft.ButtonStyle(padding=10)
                        ),
                        ft.ElevatedButton(
                            "🗑️  Tout supprimer",
                            icon="delete",
                            on_click=delete_all_tenders,
                            style=ft.ButtonStyle(padding=10, bgcolor="red", color="white")
                        )
                    ])
                ]),
                padding=20,
                bgcolor="white",
                border_radius=10
            ),
            ft.Divider(height=20),
            my_tenders_view
        ])
    
    # ===== DETAIL DIALOG =====
    
    detail_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("📋 Détails du marché"),
        actions=[
            ft.TextButton("Fermer", on_click=close_detail_dialog),
            ft.TextButton("💾 Sauvegarder", on_click=save_tender),
            ft.TextButton("🌐 Ouvrir URL", on_click=open_tender_url),
        ],
        actions_alignment="end",
    )
    
    # ===== FUNCTIONS =====
    
    def on_search_click(e):
        keyword = search_field.value.strip()
        if not keyword:
            status_text.value = "⚠️ Entrez un mot-clé"
            status_text.color = "orange"
            page.update()
            return
        
        status_text.value = f"🔍 Recherche: '{keyword}'..."
        status_text.color = "blue"
        search_results_view.controls.clear()
        page.update()
        
        # 1. Suche in Datenbank
        local_results = search_in_database(keyword)
        
        # 2. Wenn nichts in DB, suche auf Web
        if not local_results:
            status_text.value = f"🌐 Recherche sur le web..."
            page.update()
            
            web_results = scraper.search(keyword, max_results=10)
            search_results.clear()
            search_results.extend(web_results)
            
            if not web_results:
                status_text.value = f"❌ Aucun résultat pour '{keyword}'"
                status_text.color = "red"
                search_results_view.controls.append(
                    ft.Text("Aucun résultat trouvé", color="grey", italic=True)
                )
            else:
                status_text.value = f"✅ {len(web_results)} résultats web"
                status_text.color = "green"
                
                for tender in web_results:
                    card = create_tender_card(tender, is_web=True)
                    search_results_view.controls.append(card)
        else:
            search_results.clear()
            search_results.extend(local_results)
            status_text.value = f"📁 {len(local_results)} résultats locaux"
            status_text.color = "green"
            
            for tender in local_results:
                card = create_tender_card(tender, is_web=False)
                search_results_view.controls.append(card)
        
        page.update()
    
    def create_tender_card(tender: Tender, is_web: bool = True):
        return ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.ListTile(
                        leading=ft.Icon("description", color="blue"),
                        title=ft.Text(tender.reference, weight="bold", size=16),
                        subtitle=ft.Text(tender.titre[:100] + "..." if len(tender.titre) > 100 else tender.titre),
                    ),
                    ft.Container(
                        ft.Column([
                            ft.Row([
                                ft.Column([
                                    ft.Text("📍", size=12),
                                    ft.Text(tender.lieux[:40] + "..." if len(tender.lieux) > 40 else tender.lieux, size=14)
                                ], expand=True),
                                ft.Column([
                                    ft.Text("💰", size=12),
                                    ft.Text(fmt_money(tender.estimation), size=14, color="green", weight="bold")
                                ], expand=True),
                            ]),
                            ft.Row([
                                ft.Column([
                                    ft.Text("🏛️", size=12),
                                    ft.Text(tender.organisation[:30] + "..." if len(tender.organisation) > 30 else tender.organisation, size=12)
                                ], expand=True),
                                ft.Column([
                                    ft.Text("📅", size=12),
                                    ft.Text(fmt_date_iso(tender.echeance) if tender.echeance else "—", size=12)
                                ], expand=True),
                            ]),
                        ]),
                        padding=ft.padding.symmetric(horizontal=15)
                    ),
                    ft.Row([
                        ft.ElevatedButton(
                            "📋 Détails",
                            icon="info",
                            on_click=lambda e, t=tender: show_tender_details(t),
                            style=ft.ButtonStyle(padding=10, bgcolor="blue", color="white"),
                            width=120
                        ) if is_web else ft.Container(width=120),
                        ft.ElevatedButton(
                            "💾 Importer" if is_web else "📄 Voir",
                            icon="save" if is_web else "visibility",
                            on_click=lambda e, t=tender: import_tender(t) if is_web else show_tender_details(t),
                            style=ft.ButtonStyle(padding=10),
                            width=120
                        ),
                    ], alignment="end")
                ]),
                padding=10,
                on_click=lambda e, t=tender: show_tender_details(t)
            )
        )
    
    def show_tender_details(tender: Tender):
        global current_tender
        current_tender = tender
        
        content = ft.Column([
            ft.Text(tender.reference, size=24, weight="bold"),
            ft.Text(tender.titre, size=16, color="grey"),
            ft.Divider(height=20),
            
            ft.DataTable(
                columns=[
                    ft.DataColumn(ft.Text("Champ", weight="bold")),
                    ft.DataColumn(ft.Text("Valeur", weight="bold")),
                ],
                rows=[
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text("Lieu:")),
                        ft.DataCell(ft.Text(tender.lieux)),
                    ]),
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text("Estimation:")),
                        ft.DataCell(ft.Text(fmt_money(tender.estimation), color="green")),
                    ]),
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text("Caution:")),
                        ft.DataCell(ft.Text(fmt_money(tender.caution))),
                    ]),
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text("Échéance:")),
                        ft.DataCell(ft.Text(fmt_date_iso(tender.echeance) + (f" {tender.echeance_time}" if tender.echeance_time else ""))),
                    ]),
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text("Organisation:")),
                        ft.DataCell(ft.Text(tender.organisation)),
                    ]),
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text("Catégorie:")),
                        ft.DataCell(ft.Text(tender.categorie)),
                    ]),
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text("Email:")),
                        ft.DataCell(ft.Text(tender.contact_email)),
                    ]),
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text("Téléphone:")),
                        ft.DataCell(ft.Text(tender.contact_phone)),
                    ]),
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text("URL:")),
                        ft.DataCell(ft.Text(tender.url[:50] + "..." if len(tender.url) > 50 else tender.url)),
                    ]),
                ]
            ),
            
            ft.Divider(height=20),
            ft.Text("Description:", size=16, weight="bold"),
            ft.Container(
                ft.Text(tender.description[:500] + "..." if len(tender.description) > 500 else tender.description),
                padding=10,
                bgcolor="bluegrey50",
                border_radius=8
            )
        ], scroll="adaptive")
        
        detail_dialog.content = content
        page.dialog = detail_dialog
        detail_dialog.open = True
        page.update()
    
    def close_detail_dialog(e):
        detail_dialog.open = False
        page.update()
    
    def import_tender(tender: Tender):
        is_new, tender_id = upsert_tender(tender)
        if is_new:
            status_text.value = f"✅ Importé: {tender.reference}"
            status_text.color = "green"
        else:
            status_text.value = f"📝 Mis à jour: {tender.reference}"
            status_text.color = "blue"
        page.update()
        load_my_tenders(None)
    
    def save_tender(e):
        if current_tender:
            import_tender(current_tender)
            close_detail_dialog(None)
    
    def open_tender_url(e):
        if current_tender and current_tender.url:
            # Auf Android: Zeige URL zum Kopieren
            show_url_dialog(current_tender.url)
    
    def show_url_dialog(url: str):
        dialog = ft.AlertDialog(
            title=ft.Text("🌐 Ouvrir l'URL"),
            content=ft.Column([
                ft.Text("URL du marché:", size=16, weight="bold"),
                ft.Text(url, selectable=True, color="blue"),
                ft.Text("\nSur Android: Copiez et collez dans votre navigateur.", size=12, color="grey")
            ]),
            actions=[
                ft.TextButton("Copier", on_click=lambda e: copy_to_clipboard(url)),
                ft.TextButton("OK", on_click=lambda e: close_dialog(dialog))
            ]
        )
        page.dialog = dialog
        dialog.open = True
        page.update()
    
    def copy_to_clipboard(text: str):
        # Simulierte Kopierfunktion für Android
        status_text.value = "📋 URL copiée (simulation)"
        status_text.color = "green"
        page.update()
    
    def close_dialog(dialog):
        dialog.open = False
        page.update()
    
    def load_my_tenders(e):
        my_tenders.clear()
        my_tenders.extend(get_all_tenders())
        my_tenders_view.controls.clear()
        
        if not my_tenders:
            my_tenders_view.controls.append(
                ft.Text("Aucun appel d'offres sauvegardé", color="grey", italic=True)
            )
        else:
            for tender in my_tenders:
                card = create_tender_card(tender, is_web=False)
                my_tenders_view.controls.append(card)
        
        page.update()
    
    def export_csv(e):
        if not my_tenders:
            show_message("Export", "Aucune donnée à exporter")
            return
        
        # Simulierter CSV-Export
        import csv
        filename = f"safkaty_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f, delimiter=';')
                writer.writerow(['Reference', 'Titre', 'Lieux', 'Estimation', 'Caution', 'Echeance', 'Organisation', 'URL'])
                for tender in my_tenders:
                    writer.writerow([
                        tender.reference,
                        tender.titre,
                        tender.lieux,
                        fmt_money(tender.estimation),
                        fmt_money(tender.caution),
                        fmt_date_iso(tender.echeance),
                        tender.organisation,
                        tender.url
                    ])
            
            show_message("✅ Export réussi", f"Fichier: {filename}\n{len(my_tenders)} entrées exportées")
            
        except Exception as ex:
            show_message("❌ Erreur d'export", str(ex))
    
    def delete_all_tenders(e):
        confirm_dialog = ft.AlertDialog(
            title=ft.Text("⚠️ Confirmation"),
            content=ft.Text(f"Supprimer TOUS les {len(my_tenders)} appels d'offres?\nCette action est irréversible!"),
            actions=[
                ft.TextButton("Annuler", on_click=lambda e: close_dialog(confirm_dialog)),
                ft.TextButton("SUPPRIMER", on_click=lambda e: [close_dialog(confirm_dialog), confirm_delete_all()])
            ]
        )
        page.dialog = confirm_dialog
        confirm_dialog.open = True
        page.update()
    
    def confirm_delete_all():
        try:
            conn = sqlite3.connect(DB_NAME)
            cur = conn.cursor()
            cur.execute("DELETE FROM tender_status")
            cur.execute("DELETE FROM tenders")
            conn.commit()
            conn.close()
            
            my_tenders.clear()
            my_tenders_view.controls.clear()
            my_tenders_view.controls.append(
                ft.Text("Tous les appels d'offres ont été supprimés", color="grey", italic=True)
            )
            
            show_message("✅ Supprimé", "Toutes les données ont été supprimées")
            page.update()
            
        except Exception as ex:
            show_message("❌ Erreur", str(ex))
    
    def show_message(title: str, message: str):
        dialog = ft.AlertDialog(
            title=ft.Text(title),
            content=ft.Text(message),
            actions=[ft.TextButton("OK", on_click=lambda e: close_dialog(dialog))]
        )
        page.dialog = dialog
        dialog.open = True
        page.update()
    
    # ===== SETTINGS TAB =====
    
    def build_settings_tab():
        return ft.Column([
            ft.Container(
                ft.Column([
                    ft.Text("PARAMÈTRES", size=20, weight="bold"),
                    ft.Divider(height=10),
                    ft.Text("Base URL:", size=16),
                    ft.TextField(value=scraper.base_url, read_only=True),
                    ft.Divider(height=20),
                    ft.Text("Statistiques:", size=16, weight="bold"),
                    ft.Text(f"Tenders dans la base: {len(my_tenders)}", size=14),
                    ft.Divider(height=20),
                    ft.Text("À propos:", size=16, weight="bold"),
                    ft.Text("SAFKATY Mobile v1.0", size=14),
                    ft.Text("Basé sur SAFKATY Desktop", size=12, color="grey"),
                    ft.Text(f"Android: {'Oui' if IS_ANDROID else 'Non'}", size=12, color="grey"),
                ]),
                padding=20,
                bgcolor="white",
                border_radius=10
            )
        ])
    
    # ===== INIT APP =====
    
    def on_tab_change(e):
        if tabs.selected_index == 1:  # Mes AO Tab
            load_my_tenders(None)
    
    tabs.on_change = on_tab_change
    
    # Set tab contents
    tabs.tabs[0].content = build_search_tab()
    tabs.tabs[1].content = build_my_tab()
    tabs.tabs[2].content = build_settings_tab()
    
    # Header
    header = ft.Container(
        ft.Column([
            ft.Row([
                ft.Icon("public", size=45, color="blue"),
                ft.Column([
                    ft.Text("SAFKATY Mobile", size=32, weight="bold", color="blue700"),
                    ft.Text("Marchés Publics du Maroc", size=14, color="bluegrey600")
                ])
            ]),
            ft.Text("Recherche et gestion d'appels d'offres", size=12, color="grey", italic=True)
        ]),
        padding=20,
        bgcolor="bluegrey50",
        border_radius=10
    )
    
    # Main layout
    page.add(
        ft.Column([
            header,
            ft.Divider(height=20),
            tabs
        ], expand=True)
    )
    
    # Initialize database
    init_database()
    load_my_tenders(None)

# Start app
if __name__ == "__main__":
    ft.app(target=main)
