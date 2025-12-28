# main.py - ULTIMATIVE SAFKATY APP (Android + PC)
import flet as ft
import sys
import os
import re
import json
from datetime import datetime

def main(page: ft.Page):
    # App-Einstellungen
    page.title = "SAFKATY PRO"
    page.theme_mode = "light"
    page.padding = 20
    page.scroll = "adaptive"
    
    IS_ANDROID = hasattr(sys, 'getandroidapilevel')
    APP_VERSION = "2.0"
    
    # ===== DATEN-MODEL (für Android) =====
    class MarchePublic:
        def __init__(self, reference, titre, montant, date_limite, region):
            self.reference = reference
            self.titre = titre
            self.montant = montant
            self.date_limite = date_limite
            self.region = region
        
        def to_dict(self):
            return {
                "reference": self.reference,
                "titre": self.titre,
                "montant": self.montant,
                "date_limite": self.date_limite,
                "region": self.region
            }
    
    # ===== KERN-FUNKTIONEN =====
    
    def analyze_safkaty_code():
        """Analysiere dein safkaty.py Skript"""
        try:
            with open("safkaty.py", 'r', encoding='utf-8') as f:
                content = f.read()
            
            analysis = {
                "lines": len(content.split('\n')),
                "chars": len(content),
                "functions": len(re.findall(r'def (\w+)\(', content)),
                "imports": list(set(re.findall(r'import (\w+)|from (\w+) import', content))),
                "has_gui": "webbrowser" in content or "threading" in content,
                "has_scraper": "requests" in content or "beautifulsoup" in content,
                "has_db": "sqlite3" in content,
                "last_modified": datetime.fromtimestamp(os.path.getmtime("safkaty.py")).strftime("%d.%m.%Y %H:%M")
            }
            
            return analysis
            
        except Exception as e:
            return {"error": str(e)}
    
    def generate_sample_data():
        """Generiere Beispiel-Daten basierend auf deinem Code"""
        # Basierend auf deinem safkaty.py Inhalt
        sample_marches = []
        
        # Extrahiere Schlüsselwörter aus deinem Code
        with open("safkaty.py", 'r', encoding='utf-8') as f:
            content = f.read().lower()
        
        # Bestimme Typen basierend auf Code-Inhalten
        if "bau" in content or "construction" in content:
            sample_marches.append(MarchePublic(
                "MP-2024-BAU-001",
                "Bauarbeiten Grundschule",
                "250.000 DH",
                "15.03.2024",
                "Casablanca"
            ))
        
        if "it" in content or "informatique" in content:
            sample_marches.append(MarchePublic(
                "MP-2024-IT-045",
                "IT-Infrastruktur Ministerium",
                "180.000 DH",
                "20.03.2024",
                "Rabat"
            ))
        
        if "möbel" in content or "mobilier" in content:
            sample_marches.append(MarchePublic(
                "MP-2024-MOB-012",
                "Möbellieferung Krankenhaus",
                "95.000 DH",
                "10.03.2024",
                "Marrakech"
            ))
        
        if "nettoyage" in content or "cleaning" in content:
            sample_marches.append(MarchePublic(
                "MP-2024-NET-087",
                "Reinigungsdienst Universität",
                "65.000 DH",
                "25.03.2024",
                "Fès"
            ))
        
        # Fallback falls nichts gefunden
        if not sample_marches:
            sample_marches = [
                MarchePublic("MP-2024-001", "Allgemeine Ausschreibung", "100.000 DH", "30.03.2024", "Marokko"),
                MarchePublic("MP-2024-002", "Dienstleistungsauftrag", "75.000 DH", "25.03.2024", "Marokko"),
                MarchePublic("MP-2024-003", "Lieferauftrag Material", "150.000 DH", "20.03.2024", "Marokko"),
            ]
        
        return sample_marches
    
    def export_to_json(marches):
        """Exportiere Daten als JSON"""
        try:
            data = {
                "export_date": datetime.now().isoformat(),
                "count": len(marches),
                "total_amount": sum(int(re.sub(r'\D', '', m.montant)) for m in marches),
                "marches": [m.to_dict() for m in marches]
            }
            
            filename = f"safkaty_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            if IS_ANDROID:
                # Auf Android: In Downloads speichern
                export_path = f"/sdcard/Download/{filename}"
            else:
                export_path = filename
            
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            return f"✅ Exportiert: {export_path}\n📊 {len(marches)} Einträge"
            
        except Exception as e:
            return f"❌ Export-Fehler: {str(e)}"
    
    def simulate_web_scraping():
        """Simuliere Web-Scraping (Android-sicher)"""
        try:
            # Prüfe Internet (nur Info, keine echte Prüfung auf Android)
            result = [
                "🌐 WEB-SCRAPER SIMULATION",
                "=" * 40,
                f"📱 Plattform: {'Android' if IS_ANDROID else 'PC'}",
                f"🕒 Zeit: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
                "",
                "📊 SIMULIERTE ROHDATEN:",
                "-" * 30
            ]
            
            # Basierend auf deinem Code: Simuliere Web-Inhalte
            web_content = """
            <div class="marche">
                <span class="ref">MP-2024-GEN-001</span>
                <h3>Fourniture de matériel informatique</h3>
                <span class="montant">120.000 DH</span>
                <span class="date">15/03/2024</span>
                <span class="region">Casablanca-Settat</span>
            </div>
            <div class="marche">
                <span class="ref">MP-2024-TRA-042</span>
                <h3>Travaux de réhabilitation</h3>
                <span class="montant">350.000 DH</span>
                <span class="date">22/03/2024</span>
                <span class="region">Rabat-Salé-Kénitra</span>
            </div>
            """
            
            # "Parse" die simulierten HTML-Daten
            refs = re.findall(r'MP-\d{4}-[A-Z]{3}-\d{3}', web_content)
            titres = re.findall(r'<h3>(.*?)</h3>', web_content)
            montants = re.findall(r'(\d{1,3}(?:\.\d{3})*\.?\d*)\s*DH', web_content)
            regions = re.findall(r'region">(.*?)</span>', web_content)
            
            for i in range(min(3, len(refs))):  # Zeige max 3
                result.append(f"\n📋 {refs[i] if i < len(refs) else 'MP-2024-XXX'}")
                result.append(f"🏷️  {titres[i] if i < len(titres) else 'Titre non disponible'}")
                result.append(f"💰 {montants[i] if i < len(montants) else '0'} DH")
                result.append(f"📍 {regions[i] if i < len(regions) else 'Non spécifié'}")
                result.append("-" * 30)
            
            result.append(f"\n🔍 {len(refs)} Einträge im HTML gefunden")
            result.append("📈 Scraping-Simulation abgeschlossen")
            result.append("\n💡 HINWEIS: Auf PC könnte dies echte Web-Daten sein")
            
            return "\n".join(result)
            
        except Exception as e:
            return f"❌ Scraping-Simulation fehlgeschlagen:\n{str(e)}"
    
    # ===== UI-FUNKTIONEN =====
    
    def show_dashboard():
        """Zeige Haupt-Dashboard"""
        output.value = ""
        
        # 1. Code-Analyse
        analysis = analyze_safkaty_code()
        
        dashboard = [
            "📊 SAFKATY PRO DASHBOARD",
            "=" * 50,
            f"🆔 Version: {APP_VERSION} | Android: {'✓' if IS_ANDROID else '✗'}",
            f"📅 Letzte Analyse: {analysis.get('last_modified', 'Unbekannt')}",
            "",
            "📦 CODE-ANALYSE:",
            f"• Zeilen: {analysis.get('lines', 0):,}",
            f"• Funktionen: {analysis.get('functions', 0)}",
            f"• Mit GUI: {'✓' if analysis.get('has_gui') else '✗'}",
            f"• Mit Scraper: {'✓' if analysis.get('has_scraper') else '✗'}",
            f"• Mit Datenbank: {'✓' if analysis.get('has_db') else '✗'}",
            "",
            "🚀 VERFÜGBARE FUNKTIONEN:",
            "1. Echtzeit-Analyse deines Codes",
            "2. Dynamische Daten-Generierung",
            "3. JSON-Export",
            "4. Web-Scraping Simulation",
            "5. Marchés Publics Management",
            "",
            "💡 TIPP: Nutze 'Echte Analyse' für aktuelle Daten"
        ]
        
        output.value = "\n".join(dashboard)
        status.value = "✅ Dashboard geladen"
        status.color = "green"
        page.update()
    
    def run_real_analysis(e):
        """Führe echte Analyse durch"""
        status.value = "🔍 Analysiere..."
        status.color = "orange"
        output.value = "📦 Lade und analysiere SAFKATY Code...\n"
        page.update()
        
        try:
            # 1. Code analysieren
            analysis = analyze_safkaty_code()
            
            result = [
                "🔬 DETAILLIERTE CODE-ANALYSE",
                "=" * 50,
                f"📄 Datei: safkaty.py",
                f"📏 Größe: {analysis.get('lines', 0):,} Zeilen, {analysis.get('chars', 0):,} Zeichen",
                f"⚙️  Funktionen: {analysis.get('functions', 0)}",
                f"📦 Letzte Änderung: {analysis.get('last_modified', 'Unbekannt')}",
                ""
            ]
            
            # 2. Generiere Daten basierend auf Code
            output.value += "🚀 Generiere Daten...\n"
            page.update()
            
            marches = generate_sample_data()
            
            result.append("📊 GENERIERTE MARCHÉS PUBLICS:")
            result.append("-" * 40)
            
            total = 0
            for m in marches:
                montant_num = int(re.sub(r'\D', '', m.montant))
                total += montant_num
                result.append(f"\n📋 {m.reference}")
                result.append(f"🏷️  {m.titre}")
                result.append(f"💰 {m.montant}")
                result.append(f"📅 {m.date_limite}")
                result.append(f"📍 {m.region}")
                result.append("-" * 30)
            
            result.append(f"\n📈 STATISTIKEN:")
            result.append(f"• Anzahl: {len(marches)} Marchés")
            result.append(f"• Gesamtvolumen: {total:,} DH")
            result.append(f"• Durchschnitt: {total//len(marches):,} DH")
            result.append(f"• Höchstregion: {max(set(m.region for m in marches), key=list(m.region for m in marches).count)}")
            
            result.append("\n✅ Analyse erfolgreich abgeschlossen!")
            
            # Speichere für Export
            page.data["current_marches"] = marches
            
            output.value = "\n".join(result)
            status.value = f"✅ {len(marches)} Marchés analysiert"
            status.color = "green"
            
        except Exception as ex:
            output.value = f"❌ Analyse fehlgeschlagen:\n{str(ex)}"
            status.value = "❌ Fehler"
            status.color = "red"
        
        page.update()
    
    def run_web_scraping(e):
        """Starte Web-Scraping"""
        status.value = "🌐 Scrape Web-Daten..."
        status.color = "blue"
        output.value = ""
        page.update()
        
        result = simulate_web_scraping()
        output.value = result
        
        if "❌" in result:
            status.value = "❌ Scraping fehlgeschlagen"
            status.color = "red"
        else:
            status.value = "✅ Web-Simulation abgeschlossen"
            status.color = "green"
        
        page.update()
    
    def export_data(e):
        """Exportiere Daten"""
        if "current_marches" not in page.data:
            output.value = "⚠️  Keine Daten zum Exportieren\n\nFühre zuerst eine Analyse durch!"
            status.value = "⚠️  Keine Daten"
            status.color = "orange"
            page.update()
            return
        
        status.value = "📤 Exportiere..."
        status.color = "purple"
        output.value = ""
        page.update()
        
        result = export_to_json(page.data["current_marches"])
        output.value = result
        
        if "✅" in result:
            status.value = "✅ Export fertig"
            status.color = "green"
        else:
            status.value = "❌ Export fehlgeschlagen"
            status.color = "red"
        
        page.update()
    
    # ===== UI-ELEMENTE =====
    
    # Header
    header = ft.Row([
        ft.Icon(name="analytics", color="blue", size=45),
        ft.Column([
            ft.Text("SAFKATY PRO", size=34, weight="bold", color="blue700"),
            ft.Text(f"v{APP_VERSION} • {'📱 Android' if IS_ANDROID else '💻 PC'} Mode", 
                   size=14, color="bluegrey600"),
        ])
    ])
    
    # Status
    status = ft.Text("👋 Willkommen bei SAFKATY PRO", 
                    size=18, weight="bold", color="green700")
    
    # Output
    output = ft.TextField(
        multiline=True,
        min_lines=20,
        max_lines=35,
        expand=True,
        read_only=True,
        border_color="bluegrey300",
        filled=True,
        fill_color="bluegrey50",
        text_size=14
    )
    
    # Buttons
    buttons = ft.ResponsiveRow([
        ft.ElevatedButton(
            "📊 Dashboard",
            icon="dashboard",
            on_click=lambda e: show_dashboard(),
            style=ft.ButtonStyle(padding=15, bgcolor="bluegrey700", color="white"),
            col={"sm": 12, "md": 3}
        ),
        ft.ElevatedButton(
            "🔍 Echte Analyse",
            icon="search",
            on_click=run_real_analysis,
            style=ft.ButtonStyle(padding=15, bgcolor="blue", color="white"),
            col={"sm": 12, "md": 3}
        ),
        ft.ElevatedButton(
            "🌐 Web-Scraping",
            icon="public",
            on_click=run_web_scraping,
            style=ft.ButtonStyle(padding=15, bgcolor="green", color="white"),
            col={"sm": 12, "md": 3}
        ),
        ft.ElevatedButton(
            "📤 JSON Export",
            icon="download",
            on_click=export_data,
            style=ft.ButtonStyle(padding=15, bgcolor="purple", color="white"),
            col={"sm": 12, "md": 3}
        )
    ], spacing=10)
    
    # Footer
    footer = ft.Container(
        ft.Column([
            ft.Text("ℹ️  SAFKATY PRO - Professionelle Marchés Publics Lösung", 
                   size=12, text_align="center"),
            ft.Text(f"Dein Code: {analyze_safkaty_code().get('functions', 0)} Funktionen • {analyze_safkaty_code().get('lines', 0):,} Zeilen",
                   size=11, color="grey", text_align="center")
        ]),
        padding=10,
        bgcolor="bluegrey100",
        border_radius=8
    )
    
    # ===== UI ZUSAMMENBAUEN =====
    page.add(
        ft.Column([
            header,
            ft.Divider(height=25),
            
            ft.Container(
                ft.Column([
                    ft.Text("Status:", size=22, weight="bold"),
                    status
                ]),
                padding=15,
                bgcolor="bluegrey50",
                border_radius=10,
                margin=ft.margin.only(bottom=15)
            ),
            
            buttons,
            ft.Divider(height=20),
            
            ft.Text("Ergebnisse:", size=22, weight="bold"),
            output,
            ft.Divider(height=15),
            
            footer
        ], spacing=10)
    )
    
    # Starte mit Dashboard
    show_dashboard()

# App starten
if __name__ == "__main__":
    ft.app(target=main)
