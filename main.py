# main.py - KOMPLETTE SAFKATY APP mit SQLite und Suchfunktion
import flet as ft
import sys
import os
import re
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple

def main(page: ft.Page):
    # App-Einstellungen
    page.title = "SAFKATY - Recherche Marchés Publics"
    page.theme_mode = "light"
    page.padding = 15
    page.scroll = "adaptive"
    
    IS_ANDROID = hasattr(sys, 'getandroidapilevel')
    DB_NAME = "safkaty.db"
    
    # ===== DATENKLASSEN (basierend auf deinem Code) =====
    class Tender:
        def __init__(self, reference: str, titre: str, lieux: str, estimation: str, 
                     caution: str, echeance: str, echeance_time: str, organisation: str,
                     publication: str, categorie: str, description: str, 
                     contact_email: str, contact_phone: str, url: str):
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
    
    # ===== DATENBANK (SQLite) =====
    
    def init_database():
        """Initialisiere die SQLite-Datenbank"""
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        
        # Tabelle tenders (wie in deinem Code)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS tenders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reference TEXT UNIQUE NOT NULL,
            titre TEXT,
            lieux TEXT,
            estimation TEXT,
            caution TEXT,
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
        
        # Tabelle tender_status (wie in deinem Code)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS tender_status (
            tender_id INTEGER UNIQUE,
            status TEXT DEFAULT 'nouveau',
            priority INTEGER DEFAULT 3,
            notes TEXT DEFAULT '',
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(tender_id) REFERENCES tenders(id)
        )
        """)
        
        # Tabelle für Suchverlauf
        cur.execute("""
        CREATE TABLE IF NOT EXISTS search_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT NOT NULL,
            result_count INTEGER,
            search_date TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        conn.commit()
        conn.close()
    
    def upsert_tender(tender: Tender) -> Tuple[bool, int]:
        """Speichere oder aktualisiere einen Tender"""
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        
        # Prüfe ob Tender existiert
        cur.execute("SELECT id FROM tenders WHERE reference=?", (tender.reference,))
        row = cur.fetchone()
        
        if row:
            # Update vorhandener Tender
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
            # Neuer Tender
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
            # Status-Eintrag erstellen
            cur.execute("INSERT OR IGNORE INTO tender_status (tender_id) VALUES (?)", (tender_id,))
        
        conn.commit()
        conn.close()
        return (is_new, tender_id)
    
    def save_search_history(keyword: str, count: int):
        """Speichere Suchverlauf"""
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO search_history (keyword, result_count) VALUES (?, ?)
        """, (keyword, count))
        conn.commit()
        conn.close()
    
    def get_search_history(limit: int = 10) -> List[Tuple[str, int, str]]:
        """Hole Suchverlauf"""
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("""
            SELECT keyword, result_count, search_date 
            FROM search_history 
            ORDER BY search_date DESC 
            LIMIT ?
        """, (limit,))
        results = cur.fetchall()
        conn.close()
        return results
    
    def search_tenders(keyword: str) -> List[Tender]:
        """Suche Tender in der Datenbank"""
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        
        # Suche in verschiedenen Feldern
        query = """
            SELECT reference, titre, lieux, estimation, caution, echeance, echeance_time,
                   organisation, publication, categorie, description, contact_email, 
                   contact_phone, url
            FROM tenders
            WHERE titre LIKE ? OR lieux LIKE ? OR categorie LIKE ? OR description LIKE ?
            ORDER BY publication DESC
        """
        
        search_term = f"%{keyword}%"
        cur.execute(query, (search_term, search_term, search_term, search_term))
        rows = cur.fetchall()
        conn.close()
        
        tenders = []
        for row in rows:
            tender = Tender(
                reference=row[0], titre=row[1], lieux=row[2], estimation=row[3],
                caution=row[4], echeance=row[5], echeance_time=row[6],
                organisation=row[7], publication=row[8], categorie=row[9],
                description=row[10], contact_email=row[11], contact_phone=row[12],
                url=row[13]
            )
            tenders.append(tender)
        
        return tenders
    
    # ===== SIMULIERTE DATEN (für Demo) =====
    
    def generate_sample_tenders(keyword: str) -> List[Tender]:
        """Generiere Beispiel-Tender basierend auf Keyword"""
        today = datetime.now()
        sample_date = today.strftime("%d/%m/%Y")
        tomorrow = (today + timedelta(days=1)).strftime("%d/%m/%Y")
        
        if keyword.lower() == "piste":
            return [
                Tender(
                    reference="MP-2024-PIS-001",
                    titre="Construction d'une piste sportive multifonctionnelle",
                    lieux="Casablanca, District Anfa",
                    estimation="450.000 DH",
                    caution="45.000 DH",
                    echeance="15/03/2024",
                    echeance_time="10:00",
                    organisation="Ministère de la Jeunesse et des Sports",
                    publication=sample_date,
                    categorie="Travaux publics",
                    description="Construction d'une piste sportive de 400m avec revêtement synthétique, éclairage LED et tribunes pour 200 spectateurs.",
                    contact_email="sports.casablanca@gov.ma",
                    contact_phone="+212 5222-XXXXX",
                    url="http://marchespublics.gov.ma/MP-2024-PIS-001"
                ),
                Tender(
                    reference="MP-2024-PIS-042",
                    titre="Réhabilitation de pistes rurales dans la région d'Al Haouz",
                    lieux="Al Haouz, Province de Marrakech",
                    estimation="780.000 DH",
                    caution="78.000 DH",
                    echeance="22/03/2024",
                    echeance_time="14:00",
                    organisation="Ministère de l'Équipement et de l'Eau",
                    publication=sample_date,
                    categorie="Routes et infrastructures",
                    description="Réhabilitation de 15km de pistes rurales, incluant drainage, signalisation et travaux de terrassement.",
                    contact_email="equipement.alhaouz@gov.ma",
                    contact_phone="+212 5244-XXXXX",
                    url="http://marchespublics.gov.ma/MP-2024-PIS-042"
                )
            ]
        
        elif keyword.lower() == "école":
            return [
                Tender(
                    reference="MP-2024-ECO-015",
                    titre="Construction d'une école primaire de 12 salles de classe",
                    lieux="Rabat, Quartier Hay Riad",
                    estimation="1.200.000 DH",
                    caution="120.000 DH",
                    echeance="25/03/2024",
                    echeance_time="11:00",
                    organisation="Ministère de l'Éducation Nationale",
                    publication=sample_date,
                    categorie="Bâtiments éducatifs",
                    description="Construction complète d'une école primaire avec 12 salles de classe, cantine, bibliothèque et terrain de sport.",
                    contact_email="education.rabat@gov.ma",
                    contact_phone="+212 5377-XXXXX",
                    url="http://marchespublics.gov.ma/MP-2024-ECO-015"
                ),
                Tender(
                    reference="MP-2024-ECO-087",
                    titre="Équipement informatique pour écoles rurales",
                    lieux="Meknès-Tafilalet",
                    estimation="350.000 DH",
                    caution="35.000 DH",
                    echeance="18/03/2024",
                    echeance_time="09:00",
                    organisation="Direction Provinciale de l'Éducation - Meknès",
                    publication=sample_date,
                    categorie="Fournitures informatiques",
                    description="Fourniture et installation d'équipements informatiques (ordinateurs, projecteurs, réseau) pour 10 écoles rurales.",
                    contact_email="education.meknes@gov.ma",
                    contact_phone="+212 5355-XXXXX",
                    url="http://marchespublics.gov.ma/MP-2024-ECO-087"
                )
            ]
        
        elif keyword.lower() == "terrain":
            return [
                Tender(
                    reference="MP-2024-TER-123",
                    titre="Aménagement d'un terrain de football synthétique",
                    lieux="Marrakech, Quartier Guéliz",
                    estimation="320.000 DH",
                    caution="32.000 DH",
                    echeance=tomorrow,
                    echeance_time="16:00",
                    organisation="Municipalité de Marrakech",
                    publication=sample_date,
                    categorie="Équipements sportifs",
                    description="Aménagement complet d'un terrain de football synthétique avec éclairage, vestiaires et gradins.",
                    contact_email="sports.marrakech@gov.ma",
                    contact_phone="+212 5244-XXXXX",
                    url="http://marchespublics.gov.ma/MP-2024-TER-123"
                )
            ]
        
        else:
            # Generische Tender für andere Keywords
            return [
                Tender(
                    reference=f"MP-2024-{keyword[:3].upper()}-{i:03d}",
                    titre=f"Projet {keyword.capitalize()} {i} - Services techniques",
                    lieux=f"Région {['Casablanca', 'Rabat', 'Marrakech', 'Fès'][i % 4]}",
                    estimation=f"{100 + i * 50}.000 DH",
                    caution=f"{10 + i * 5}.000 DH",
                    echeance=(today + timedelta(days=10 + i)).strftime("%d/%m/%Y"),
                    echeance_time=f"{9 + i}:00",
                    organisation="Autorité Contractante Nationale",
                    publication=sample_date,
                    categorie="Services techniques",
                    description=f"Description détaillée du projet {keyword} numéro {i}. Ce projet inclut tous les aspects techniques et administratifs nécessaires.",
                    contact_email=f"contact.{keyword}@gov.ma",
                    contact_phone=f"+212 5XXX-XXXX{i}",
                    url=f"http://marchespublics.gov.ma/MP-2024-{keyword[:3].upper()}-{i:03d}"
                ) for i in range(1, 4)
            ]
    
    def save_tenders_to_db(tenders: List[Tender]):
        """Speichere Tender in der Datenbank"""
        for tender in tenders:
            upsert_tender(tender)
    
    # ===== UI-VARIABLEN =====
    tenders_trouves = []
    tender_selectionne = None
    historique_recherches = []
    
    # ===== UI-KOMPONENTEN =====
    
    # Suchfeld
    champ_recherche = ft.TextField(
        label="🔍 Mot-clé de recherche",
        hint_text="Ex: piste, école, terrain, construction, hospital...",
        prefix_icon="search",
        expand=True,
        autofocus=True,
        on_submit=lambda e: lancer_recherche(e)
    )
    
    # Recherche-Button
    btn_recherche = ft.ElevatedButton(
        "Rechercher",
        icon="search",
        on_click=lancer_recherche,
        style=ft.ButtonStyle(padding=15, bgcolor="blue", color="white")
    )
    
    # Historique-Button
    btn_historique = ft.OutlinedButton(
        "📜 Historique",
        icon="history",
        on_click=afficher_historique,
        width=120
    )
    
    # Status-Anzeige
    status_text = ft.Text("Prêt pour la recherche", size=16, weight="bold", color="green700")

    
    # Ergebnis-Liste
    liste_resultats = ft.ListView(
        expand=True,
        spacing=10,
        padding=10
    )
    
    # Detail-Anzeige
    detail_container = ft.Container(
        visible=False,
        padding=0
    )
    
    # ===== UI-FUNKTIONEN =====
    
    def lancer_recherche(e):
        """Starte die Suche"""
        mot_cle = champ_recherche.value.strip()
        
        if not mot_cle:
            status_text.value = "⚠️  Veuillez entrer un mot-clé"
            status_text.color = "orange"
            page.update()
            return
        
        # Suche starten
        status_text.value = f"🔍 Recherche: '{mot_cle}'..."
        status_text.color = "blue"
        liste_resultats.controls.clear()
        detail_container.visible = False
        page.update()
        
        # 1. Suche in der Datenbank
        tenders_db = search_tenders(mot_cle)
        
        if tenders_db:
            # Gefunden in DB
            tenders_trouves.clear()
            tenders_trouves.extend(tenders_db)
            count = len(tenders_db)
            status_text.value = f"✅ {count} résultats trouvés dans la base de données"
            status_text.color = "green"
            
        else:
            # Keine Ergebnisse in DB -> Generiere Beispieldaten
            status_text.value = f"🔍 Simulation de résultats pour '{mot_cle}'..."
            page.update()
            
            tenders_simules = generate_sample_tenders(mot_cle)
            save_tenders_to_db(tenders_simules)  # Speichere in DB
            
            tenders_trouves.clear()
            tenders_trouves.extend(tenders_simules)
            count = len(tenders_simules)
            status_text.value = f"📋 {count} résultats simulés pour '{mot_cle}'"
            status_text.color = "green"
        
        # Suchverlauf speichern
        save_search_history(mot_cle, count)
        
        if not tenders_trouves:
            status_text.value = f"❌ Aucun résultat pour '{mot_cle}'"
            status_text.color = "red"
            liste_resultats.controls.append(
                ft.Text("Aucun marché public trouvé.", size=16, color="grey", italic=True)

            )
        else:
            # Ergebnisse anzeigen
            for i, tender in enumerate(tenders_trouves):
                card = creer_carte_tender(tender, i)
                liste_resultats.controls.append(card)
        
        page.update()
    
    def creer_carte_tender(tender: Tender, index: int):
        """Erstelle eine Tender-Karte für die Liste"""
        return ft.Card(
            elevation=3,
            content=ft.Container(
                content=ft.Column([
                    # Header mit Reference und Titel
                    ft.ListTile(
                        leading=ft.Icon("description", color="blue"),
                        title=ft.Text(
                            tender.reference, 
                            weight="bold",
                            size=16,
                            color="blue700"
                        ),
                        subtitle=ft.Text(
                            tender.titre[:100] + "..." if len(tender.titre) > 100 else tender.titre,
                            size=14
                        ),
                    ),
                    
                    # Wichtige Informationen
                    ft.Container(
                        ft.ResponsiveRow([
                            ft.Column([
                                ft.Text("📍 Lieu:", size=12, color="grey"),
                                ft.Text(tender.lieux, size=14, weight="bold")
                            ], col={"sm": 12, "md": 4}),
                            ft.Column([
                                ft.Text("💰 Estimation:", size=12, color="grey"),
                                ft.Text(tender.estimation, size=14, weight="bold", color="green")
                            ], col={"sm": 12, "md": 4}),
                            ft.Column([
                                ft.Text("📅 Échéance:", size=12, color="grey"),
                                ft.Text(f"{tender.echeance} à {tender.echeance_time}", size=14, weight="bold", color="red" if "2024" in tender.echeance else "black") 

                            ], col={"sm": 12, "md": 4}),
                        ]),
                        padding=ft.padding.symmetric(horizontal=15)
                    ),
                    
                    # Zusätzliche Infos
                    ft.Container(
                        ft.ResponsiveRow([
                            ft.Column([
                                ft.Text("🏛️ Organisation:", size=12, color="grey"),
                                ft.Text(tender.organisation[:30] + "..." if len(tender.organisation) > 30 else tender.organisation, size=13) 

                            ], col={"sm": 12, "md": 6}),
                            ft.Column([
                                ft.Text("📂 Catégorie:", size=12, color="grey"),
                                ft.Text(tender.categorie, size=13)
                            ], col={"sm": 12, "md": 6}),
                        ]),
                        padding=ft.padding.symmetric(horizontal=15)
                    ),
                    
                    # Buttons
                    ft.Container(
                        ft.Row([
                            ft.ElevatedButton(
                                "📋 Détails",
                                icon="info",
                                on_click=lambda e, idx=index: afficher_details(idx),
                                style=ft.ButtonStyle(
                                    padding=10,
                                    bgcolor="blue600",
                                    color="white"
                                ),
                                width=120
                            ),
                            ft.OutlinedButton(
                                "💾 Exporter",
                                icon="save",
                                on_click=lambda e, idx=index: exporter_tender(idx),
                                width=120
                            ),
                            ft.IconButton(
                                icon="share",
                                on_click=lambda e, idx=index: partager_tender(idx),
                                tooltip="Partager"
                            )
                        ], alignment=ft.MainAxisAlignment.END),
                        padding=ft.padding.symmetric(horizontal=15, vertical=10)
                    )
                ], spacing=10),
                padding=10,
                on_click=lambda e, idx=index: afficher_details(idx)
            )
        )
    
    def afficher_details(index: int):
        """Zeige Detail-Informationen für einen Tender"""
        global tender_selectionne
        
        if index < 0 or index >= len(tenders_trouves):
            return
        
        tender = tenders_trouves[index]
        tender_selectionne = tender
        
        # Baue Detail-Ansicht
        contenu_details = ft.Column([
            # Header
            ft.Container(
                ft.Column([
                    ft.Row([
                        ft.Icon("description", size=40, color="blue"),
                        ft.Column([
                            ft.Text("DÉTAILS DU MARCHÉ", size=24, weight="bold"),
                            ft.Text(tender.reference, size=18, color="bluegrey600")
                        ])
                    ]),
                    ft.Text(tender.titre, size=16, color="grey700")
                ]),
                padding=20,
                bgcolor="bluegrey50",
                border_radius=10
            ),
            
            ft.Divider(height=20),
            
            # Grundinformationen in Kacheln
            ft.ResponsiveRow([
                # Linke Spalte
                ft.Column([
                    # Référence et Catégorie
                    ft.Container(
                        ft.Column([
                            ft.Text("📋 INFORMATIONS GÉNÉRALES", size=18, weight="bold"),
                            ft.Divider(height=10),
                            ft.DataTable(
                                columns=[
                                    ft.DataColumn(ft.Text("Champ", weight="bold")),
                                    ft.DataColumn(ft.Text("Valeur", weight="bold")),
                                ],
                                rows=[
                                    ft.DataRow(cells=[
                                        ft.DataCell(ft.Text("Référence:")),
                                        ft.DataCell(ft.Text(tender.reference, weight="bold")),
                                    ]),
                                    ft.DataRow(cells=[
                                        ft.DataCell(ft.Text("Catégorie:")),
                                        ft.DataCell(ft.Text(tender.categorie)),
                                    ]),
                                    ft.DataRow(cells=[
                                        ft.DataCell(ft.Text("Organisation:")),
                                        ft.DataCell(ft.Text(tender.organisation)),
                                    ]),
                                    ft.DataRow(cells=[
                                        ft.DataCell(ft.Text("Date publication:")),
                                        ft.DataCell(ft.Text(tender.publication)),
                                    ]),
                                ]
                            )
                        ]),
                        padding=20,
                        bgcolor="white",
                        border_radius=10,
                        border=ft.border.all(1, "bluegrey200"),
                        col={"sm": 12, "md": 6}
                    ),
                    
                    ft.Divider(height=20),
                    
                    # Contact Information
                    ft.Container(
                        ft.Column([
                            ft.Text("📞 COORDONNÉES", size=18, weight="bold"),
                            ft.Divider(height=10),
                            ft.ListTile(
                                leading=ft.Icon("email", color="blue"),
                                title=ft.Text("Email", size=14, color="grey"),
                                subtitle=ft.Text(tender.contact_email, size=16)
                            ),
                            ft.ListTile(
                                leading=ft.Icon("phone", color="green"),
                                title=ft.Text("Téléphone", size=14, color="grey"),
                                subtitle=ft.Text(tender.contact_phone, size=16)
                            ),
                            ft.ListTile(
                                leading=ft.Icon("link", color="purple"),
                                title=ft.Text("URL", size=14, color="grey"),
                                subtitle=ft.Text(tender.url, size=14, color="blue", selectable=True)
                            )
                        ]),
                        padding=20,
                        bgcolor="white",
                        border_radius=10,
                        border=ft.border.all(1, "bluegrey200"),
                        col={"sm": 12, "md": 6}
                    )
                ], col={"sm": 12, "md": 6}),
                
                # Rechte Spalte
                ft.Column([
                    # Financial Information
                    ft.Container(
                        ft.Column([
                            ft.Text("💰 INFORMATIONS FINANCIÈRES", size=18, weight="bold"),
                            ft.Divider(height=10),
                            ft.ResponsiveRow([
                                ft.Column([
                                    ft.Container(
                                        ft.Column([
                                            ft.Text("Estimation", size=14, color="grey"),
                                            ft.Text(tender.estimation, size=24, weight="bold", color="green")
                                        ], horizontal_alignment="center"),
                                        padding=20,
                                        bgcolor="green50",
                                        border_radius=10,
                                        col={"sm": 12, "md": 6}
                                    )
                                ], col={"sm": 12, "md": 6}),
                                ft.Column([
                                    ft.Container(
                                        ft.Column([
                                            ft.Text("Caution", size=14, color="grey"),
                                            ft.Text(tender.caution, size=24, weight="bold", color="orange")
                                        ], horizontal_alignment="center"),
                                        padding=20,
                                        bgcolor="orange50",
                                        border_radius=10,
                                        col={"sm": 12, "md": 6}
                                    )
                                ], col={"sm": 12, "md": 6}),
                            ]),
                            ft.Divider(height=20),
                            ft.Text("📅 DÉLAIS", size=16, weight="bold"),
                            ft.ResponsiveRow([
                                ft.Column([
                                    ft.Text("Date échéance:", size=14, color="grey"),
                                    ft.Text(tender.echeance, size=18, weight="bold", color="red")
                                ], col={"sm": 12, "md": 6}),
                                ft.Column([
                                    ft.Text("Heure limite:", size=14, color="grey"),
                                    ft.Text(tender.echeance_time, size=18, weight="bold")
                                ], col={"sm": 12, "md": 6}),
                            ])
                        ]),
                        padding=20,
                        bgcolor="white",
                        border_radius=10,
                        border=ft.border.all(1, "bluegrey200"),
                        col={"sm": 12, "md": 6}
                    ),
                    
                    ft.Divider(height=20),
                    
                    # Location
                    ft.Container(
                        ft.Column([
                            ft.Text("📍 LIEU D'EXÉCUTION", size=18, weight="bold"),
                            ft.Divider(height=10),
                            ft.Row([
                                ft.Icon("place", color="red", size=30),
                                ft.Text(tender.lieux, size=20, weight="bold")
                            ])
                        ]),
                        padding=20,
                        bgcolor="white",
                        border_radius=10,
                        border=ft.border.all(1, "bluegrey200"),
                        col={"sm": 12, "md": 6}
                    )
                ], col={"sm": 12, "md": 6}),
            ]),
            
            ft.Divider(height=20),
            
            # Description complète
            ft.Container(
                ft.Column([
                    ft.Text("📄 DESCRIPTION DÉTAILLÉE", size=20, weight="bold"),
                    ft.Divider(height=10),
                    ft.Container(
                        ft.Text(tender.description, size=16, selectable=True),
                        padding=20,
                        bgcolor="bluegrey50",
                        border_radius=10
                    )
                ]),
                padding=20,
                bgcolor="white",
                border_radius=10,
                border=ft.border.all(1, "bluegrey200")
            ),
            
            ft.Divider(height=20),
            
            # Actions
            ft.Container(
                ft.ResponsiveRow([
                    ft.Column([
                        ft.ElevatedButton(
                            "⬅️ Retour à la liste",
                            icon="arrow_back",
                            on_click=retour_liste,
                            style=ft.ButtonStyle(padding=15, bgcolor="bluegrey", color="white"),
                            width=200
                        )
                    ], col={"sm": 12, "md": 4}),
                    ft.Column([
                        ft.ElevatedButton(
                            "💾 Exporter JSON",
                            icon="save",
                            on_click=lambda e: exporter_tender_details(),
                            style=ft.ButtonStyle(padding=15, bgcolor="green", color="white"),
                            width=200
                        )
                    ], col={"sm": 12, "md": 4}),
                    ft.Column([
                        ft.ElevatedButton(
                            "📋 Copier référence",
                            icon="content_copy",
                            on_click=lambda e: copier_reference(tender.reference),
                            style=ft.ButtonStyle(padding=15, bgcolor="purple", color="white"),
                            width=200
                        )
                    ], col={"sm": 12, "md": 4}),
                ]),
                padding=20
            )
        ], scroll="adaptive")
        
        # Zeige Details
        detail_container.content = contenu_details
        detail_container.visible = True
        
        status_text.value = f"✅ Détails chargés: {tender.reference}"
        status_text.color = "green"
        page.update()
    
    def retour_liste(e):
        """Zurück zur Ergebnisliste"""
        detail_container.visible = False
        if tenders_trouves:
            status_text.value = f"📋 {len(tenders_trouves)} résultats"
        else:
            status_text.value = "Prêt pour la recherche"
        status_text.color = "green"
        page.update()
    
    def exporter_tender(index: int):
        """Exportiere einen Tender als JSON"""
        if index < 0 or index >= len(tenders_trouves):
            return
        
        tender = tenders_trouves[index]
        exporter_tender_single(tender)
    
    def exporter_tender_single(tender: Tender):
        """Exportiere einen einzelnen Tender"""
        try:
            data = {
                "marche_public": tender.to_dict(),
                "export_info": {
                    "date": datetime.now().isoformat(),
                    "application": "SAFKATY Mobile",
                    "format": "JSON"
                }
            }
            
            filename = f"SAFKATY_{tender.reference}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            if IS_ANDROID:
                filepath = f"/sdcard/Download/{filename}"
            else:
                filepath = filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            status_text.value = f"✅ Exporté: {filename}"
            status_text.color = "green"
            
            # Zeige Erfolgsmeldung
            page.dialog = ft.AlertDialog(
                title=ft.Text("✅ Export réussi"),
                content=ft.Text(f"Le marché {tender.reference} a été exporté.\n\nFichier: {filename}"),
                actions=[ft.TextButton("OK", on_click=lambda e: fermer_dialog())]
            )
            page.dialog.open = True
            
        except Exception as ex:
            status_text.value = f"❌ Erreur d'export: {str(ex)}"
            status_text.color = "red"
        
        page.update()
    
    def exporter_tender_details():
        """Exportiere den aktuellen Tender"""
        if tender_selectionne:
            exporter_tender_single(tender_selectionne)
    
    def copier_reference(ref: str):
        """Kopiere Referenz (simuliert)"""
        status_text.value = f"📋 Référence copiée: {ref}"
        status_text.color = "blue"
        page.update()
    
    def partager_tender(index: int):
        """Teile Tender-Informationen"""
        if index < 0 or index >= len(tenders_trouves):
            return
        
        tender = tenders_trouves[index]
        share_text = f"""
        📋 Marché Public: {tender.reference}
        🏷️  {tender.titre}
        📍 {tender.lieux}
        💰 {tender.estimation}
        📅 Échéance: {tender.echeance} à {tender.echeance_time}
        🔗 {tender.url}
        
        Via SAFKATY App
        """
        
        page.dialog = ft.AlertDialog(
            title=ft.Text("📤 Partager le marché"),
            content=ft.TextField(
                value=share_text,
                multiline=True,
                min_lines=8,
                max_lines=12,
                read_only=True
            ),
            actions=[
                ft.TextButton("Copier", on_click=lambda e: copier_texte(share_text)),
                ft.TextButton("Fermer", on_click=lambda e: fermer_dialog())
            ]
        )
        page.dialog.open = True
        page.update()
    
    def copier_texte(texte: str):
        """Kopiere Text (simuliert)"""
        status_text.value = "📋 Texte copié dans le presse-papier"
        status_text.color = "green"
        page.dialog.open = False
        page.update()
    
    def afficher_historique(e):
        """Zeige Suchverlauf"""
        historique = get_search_history(10)
        
        if not historique:
            content = ft.Text("Aucun historique de recherche.")
        else:
            rows = []
            for keyword, count, date_str in historique:
                date_obj = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                date_formatted = date_obj.strftime("%d/%m/%Y %H:%M")
                rows.append(
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text(keyword, weight="bold")),
                        ft.DataCell(ft.Text(str(count), color="green" if count > 0 else "red")),
                        ft.DataCell(ft.Text(date_formatted, size=12, color="grey")),
                        ft.DataCell(
                            ft.IconButton(
                                icon="search",
                                on_click=lambda e, kw=keyword: rechercher_historique(kw),
                                tooltip="Rechercher à nouveau"
                            )
                        )
                    ])
                )
            
            content = ft.DataTable(
                columns=[
                    ft.DataColumn(ft.Text("Mot-clé", weight="bold")),
                    ft.DataColumn(ft.Text("Résultats", weight="bold")),
                    ft.DataColumn(ft.Text("Date", weight="bold")),
                    ft.DataColumn(ft.Text("Action", weight="bold")),
                ],
                rows=rows
            )
        
        page.dialog = ft.AlertDialog(
            title=ft.Text("📜 Historique des recherches"),
            content=content,
            actions=[ft.TextButton("Fermer", on_click=lambda e: fermer_dialog())]
        )
        page.dialog.open = True
        page.update()
    
    def rechercher_historique(keyword: str):
        """Suche mit historischem Keyword"""
        champ_recherche.value = keyword
        page.dialog.open = False
        lancer_recherche(None)
        page.update()
    
    def fermer_dialog():
        """Schließe Dialog"""
        if hasattr(page, 'dialog'):
            page.dialog.open = False
        page.update()
    
    # ===== UI-AUFBAU =====
    
    # Header
    header = ft.Container(
        ft.Column([
            ft.Row([
                ft.Icon("public", size=50, color="blue"),
                ft.Column([
                    ft.Text("SAFKATY", size=38, weight="bold", color="blue700"),
                    ft.Text("Marchés Publics du Maroc", size=16, color="bluegrey600")
                ])
            ]),
            ft.Text("Recherchez, analysez et gérez les appels d'offres", size=14, color="grey", italic=True)

        ]),
        padding=25,
        bgcolor="bluegrey50",
        border_radius=10
    )
    
    # Recherche-Bereich
    recherche_section = ft.Container(
        ft.Column([
            ft.Text("🔍 RECHERCHE PAR MOT-CLÉ", size=20, weight="bold"),
            ft.Divider(height=10),
            ft.Row([champ_recherche, btn_recherche, btn_historique], spacing=10, vertical_alignment="center"),

            ft.Divider(height=15),
            status_text
        ]),
        padding=20,
        bgcolor="white",
        border_radius=10,
        border=ft.border.all(1, "bluegrey200")
    )
    
    # Info-Box
    info_box = ft.Container(
        ft.Column([
            ft.Row([
                ft.Icon("info", color="blue", size=20),
                ft.Text("💡 Conseils de recherche:", size=16, weight="bold")
            ]),
            ft.Text("• Utilisez des mots-clés spécifiques: 'piste', 'école', 'terrain'", size=14),
            ft.Text("• Combinez plusieurs mots: 'construction école primaire'", size=14),
            ft.Text("• Consultez l'historique pour vos recherches précédentes", size=14),
        ]),
        padding=15,
        bgcolor="blue50",
        border_radius=8,
        border=ft.border.all(1, "blue100")
    )
    
    # Haupt-Layout
    page.add(
        ft.Column([
            header,
            ft.Divider(height=20),
            recherche_section,
            ft.Divider(height=15),
            info_box,
            ft.Divider(height=20),
            
            # Ergebnisse oder Details
            ft.Container(
                ft.Column([
                    ft.Row([
                        ft.Text("📋 RÉSULTATS DE RECHERCHE", size=20, weight="bold"),

                        ft.Container(
                            ft.Text("0 résultats", size=14, color="grey", weight="bold"),

                            padding=ft.padding.symmetric(horizontal=10, vertical=5),
                            bgcolor="bluegrey100",
                            border_radius=20
                        )
                    ]),
                    liste_resultats
                ]),
                expand=True,
                visible=True
            ),
            
            detail_container
        ], spacing=10, expand=True)
    )
    
    # Datenbank initialisieren
    init_database()
    
    # Historique laden
    historique_recherches = get_search_history(5)

# App starten
if __name__ == "__main__":
    ft.app(target=main)
