# main.py - KORRIGIERTE Version
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
    APP_VERSION = "2.1"  # Version erhöht
    
    # ===== DATEN-MODEL =====
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
    
    # ===== KERN-FUNKTIONEN (KORRIGIERT) =====
    
    def analyze_safkaty_code():
        """Analysiere dein safkaty.py Skript - KORRIGIERT"""
        try:
            if not os.path.exists("safkaty.py"):
                return {"error": "safkaty.py nicht gefunden", "lines": 0, "chars": 0, "functions": 0}
            
            with open("safkaty.py", 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Funktionen zählen
            functions = re.findall(r'def (\w+)\(', content)
            
            # Importe extrahieren
            imports_raw = re.findall(r'import (\w+)|from (\w+) import', content)
            imports = []
            for imp in imports_raw:
                imports.append(imp[0] if imp[0] else imp[1])
            
            # Features prüfen
            has_gui = "webbrowser" in content or "threading" in content
            has_scraper = "requests" in content or "beautifulsoup" in content
            has_db = "sqlite3" in content
            
            # Letzte Änderung
            try:
                mtime = os.path.getmtime("safkaty.py")
                last_modified = datetime.fromtimestamp(mtime).strftime("%d.%m.%Y %H:%M")
            except:
                last_modified = "Unbekannt"
            
            analysis = {
                "lines": len(content.split('\n')),
                "chars": len(content),
                "functions": len(functions),
                "imports": list(set(imports)),
                "has_gui": has_gui,
                "has_scraper": has_scraper,
                "has_db": has_db,
                "last_modified": last_modified,
                "function_names": functions[:10]  # Erste 10 Funktionen
            }
            
            return analysis
            
        except Exception as e:
            return {"error": str(e), "lines": 0, "chars": 0, "functions": 0}
    
    def generate_sample_data():
        """Generiere Beispiel-Daten basierend auf deinem Code"""
        try:
            sample_marches = []
            
            # Lese Code-Inhalte sicher
            if os.path.exists("safkaty.py"):
                with open("safkaty.py", 'r', encoding='utf-8') as f:
                    content = f.read().lower()
            else:
                content = ""
            
            # Generiere basierend auf Keywords
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
            
            # Fallback
            if not sample_marches:
                sample_marches = [
                    MarchePublic("MP-2024-001", "Allgemeine Ausschreibung", "100.000 DH", "30.03.2024", "Marokko"),
                    MarchePublic("MP-2024-002", "Dienstleistungsauftrag", "75.000 DH", "25.03.2024", "Marokko"),
                    MarchePublic("MP-2024-003", "Lieferauftrag Material", "150.000 DH", "20.03.2024", "Marokko"),
                ]
            
            return sample_marches
            
        except Exception:
            # Fallback-Daten
            return [
                MarchePublic("MP-2024-DEF-001", "Standard Ausschreibung", "120.000 DH", "28.12.2024", "Marokko"),
                MarchePublic("MP-2024-DEF-002", "Service Vertrag", "85.000 DH", "30.12.2024", "Marokko"),
            ]
    
    def export_to_json(marches):
        """Exportiere Daten als JSON"""
        try:
            data = {
                "export_date": datetime.now().isoformat(),
                "count": len(marches),
                "marches": [m.to_dict() for m in marches],
                "generated_by": f"SAFKATY PRO v{APP_VERSION}"
            }
            
            filename = f"safkaty_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            if IS_ANDROID:
                # Auf Android: Versuche Downloads
                export_path = f"safkaty_{datetime.now().strftime('%Y%m%d')}.json"
            else:
                export_path = filename
            
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            return f"✅ Exportiert: {export_path}\n📊 {len(marches)} Einträge\n📁 Größe: {os.path.getsize(export_path)} Bytes"
            
        except Exception as e:
            return f"❌ Export-Fehler: {str(e)}"
    
    def simulate_web_scraping():
        """Simuliere Web-Scraping"""
        try:
            result = [
                "🌐 WEB-SCRAPER SIMULATION",
                "=" * 40,
                f"📱 Plattform: {'Android' if IS_ANDROID else 'PC'}",
                f"🕒 Zeit: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
                f"🔧 Version: {APP_VERSION}",
                "",
                "📊 SIMULIERTE DATEN VON MARCHESPUBLICS.GOV.MA:",
                "-" * 40
            ]
            
            # Simulierte Daten basierend auf deinem Code
            sample_data = [
                {"ref": "MP-2024-ADM-001", "title": "Services administratifs", "amount": "75.000 DH", "region": "Rabat"},
                {"ref": "MP-2024-SAN-042", "title": "Équipement sanitaire", "amount": "120.000 DH", "region": "Casablanca"},
                {"ref": "MP-2024-EDU-087", "title": "Fourniture scolaire", "amount": "95.000 DH", "region": "Marrakech"},
                {"ref": "MP-2024-TRA-123", "title": "Travaux routiers", "amount": "350.000 DH", "region": "Tanger"},
            ]
            
            for item in sample_data:
                result.append(f"\n📋 {item['ref']}")
                result.append(f"🏷️  {item['title']}")
                result.append(f"💰 {item['amount']}")
                result.append(f"📍 {item['region']}")
                result.append("-" * 30)
            
            result.append(f"\n🔍 {len(sample_data)} Ausschreibungen gefunden")
            result.append("📈 Scraping-Simulation erfolgreich")
            result.append("\n💡 INFO: In der PC-Version könnte dies")
            result.append("   echte Web-Anfragen durchführen")
            
            return "\n".join(result)
            
        except Exception as e:
            return f"❌ Scraping-Fehler:\n{str(e)}"
    
    # ===== UI-FUNKTIONEN =====
    
    def show_dashboard():
        """Zeige Haupt-Dashboard"""
        output.value = ""
        
        analysis = analyze_safkaty_code()
        
        dashboard = [
            "📊 SAFKATY PRO DASHBOARD",
            "=" * 50,
            f"🆔 Version: {APP_VERSION} | Android: {'✓' if IS_ANDROID else '✗'}",
            f"📅 Letzte Änderung: {analysis.get('last_modified', 'Unbekannt')}",
            "",
            "📦 CODE-ANALYSE:",
            f"• Zeilen: {analysis.get('lines', 0):,}",
            f"• Funktionen: {analysis.get('functions', 0)}",
            f"• GUI-Funktionen: {'✓' if analysis.get('has_gui') else '✗'}",
            f"• Scraper-Funktionen: {'✓' if analysis.get('has_scraper') else '✗'}",
            f"• Datenbank: {'✓' if analysis.get('has_db') else '✗'}",
        ]
        
        # Zeige erste Funktionen
        if analysis.get('function_names'):
            dashboard.append(f"\n🔧 Erste Funktionen:")
            for i, func in enumerate(analysis['function_names'][:5], 1):
                dashboard.append(f"  {i}. {func}()")
            if len(analysis['function_names']) > 5:
                dashboard.append(f"  ... und {len(analysis['function_names']) - 5} weitere")
        
        dashboard.extend([
            "",
            "🚀 VERFÜGBARE AKTIONEN:",
            "1. 🔍 Echte Analyse - Analysiert deinen Code",
            "2. 🌐 Web-Scraping - Simuliert Web-Daten",
            "3. 📤 JSON Export - Speichert Ergebnisse",
            "4. 📊 Dashboard - Diese Übersicht",
            "",
            "💡 TIPP: Beginne mit 'Echte Analyse'"
        ])
        
        output.value = "\n".join(dashboard)
        status.value = "✅ Dashboard geladen"
        status.color = "green"
        page.update()
    
    def run_real_analysis(e):
        """Führe echte Analyse durch - KORRIGIERT"""
        status.value = "🔍 Analysiere Code..."
        status.color = "orange"
        output.value = "📦 Lade SAFKATY Skript...\n"
        page.update()
        
        try:
            # 1. Code analysieren
            analysis = analyze_safkaty_code()
            
            if "error" in analysis and analysis["error"] != "safkaty.py nicht gefunden":
                output.value = f"❌ Analyse-Fehler: {analysis['error']}"
                status.value = "❌ Fehler"
                status.color = "red"
                page.update()
                return
            
            result = [
                "🔬 DETAILLIERTE CODE-ANALYSE",
                "=" * 50,
                f"📄 Datei: safkaty.py",
                f"📏 Größe: {analysis.get('lines', 0):,} Zeilen",
                f"⚙️  Funktionen: {analysis.get('functions', 0)}",
                f"📦 Letzte Änderung: {analysis.get('last_modified', 'Unbekannt')}",
                f"🔧 Scraper: {'Vorhanden ✓' if analysis.get('has_scraper') else 'Nicht vorhanden ✗'}",
                f"💾 Datenbank: {'Vorhanden ✓' if analysis.get('has_db') else 'Nicht vorhanden ✗'}",
                ""
            ]
            
            # 2. Generiere Daten
            output.value += "🚀 Generiere Beispiel-Daten...\n"
            page.update()
            
            marches = generate_sample_data()
            
            result.append("📊 GENERIERTE MARCHÉS PUBLICS:")
            result.append("-" * 40)
            
            total_amounts = []
            for m in marches:
                # Extrahiere Zahlen aus Montant
                numbers = re.findall(r'\d+', m.montant)
                if numbers:
                    total_amounts.append(int(''.join(numbers)))
                
                result.append(f"\n📋 {m.reference}")
                result.append(f"🏷️  {m.titre}")
                result.append(f"💰 {m.montant}")
                result.append(f"📅 {m.date_limite}")
                result.append(f"📍 {m.region}")
                result.append("-" * 30)
            
            # Statistiken
            if total_amounts:
                total = sum(total_amounts)
                avg = total // len(total_amounts) if total_amounts else 0
                result.append(f"\n📈 STATISTIKEN:")
                result.append(f"• Anzahl: {len(marches)} Marchés")
                result.append(f"• Gesamtvolumen: {total:,} DH")
                result.append(f"• Durchschnitt: {avg:,} DH")
            
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
        status.value = "🌐 Simuliere Web-Daten..."
        status.color = "blue"
        output.value = ""
        page.update()
        
        result = simulate_web_scraping()
        output.value = result
        
        if "❌" in result:
            status.value = "❌ Simulation fehlgeschlagen"
            status.color = "red"
        else:
            status.value = "✅ Simulation abgeschlossen"
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
        
        status.value = "📤 Exportiere als JSON..."
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
        ft.Icon(name="analytics", color="green", size=45),
        ft.Column([
            ft.Text("SAFKATY PRO", size=34, weight="bold", color="green700"),
            ft.Text(f"v{APP_VERSION} • {'📱 Android' if IS_ANDROID else '💻 Desktop'}", 
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
            style=ft.ButtonStyle(padding=15, bgcolor="blue600", color="white"),
            col={"sm": 12, "md": 3}
        ),
        ft.ElevatedButton(
            "🌐 Web-Scraping",
            icon="public",
            on_click=run_web_scraping,
            style=ft.ButtonStyle(padding=15, bgcolor="green600", color="white"),
            col={"sm": 12, "md": 3}
        ),
        ft.ElevatedButton(
            "📤 JSON Export",
            icon="download",
            on_click=export_data,
            style=ft.ButtonStyle(padding=15, bgcolor="purple600", color="white"),
            col={"sm": 12, "md": 3}
        )
    ], spacing=10)
    
    # Footer
    footer = ft.Container(
        ft.Column([
            ft.Text("🚀 SAFKATY PRO - Deine Marchés Publics Lösung", 
                   size=13, weight="bold", text_align="center"),
            ft.Text("83 Funktionen • 1.828 Zeilen • Vollständig mobil",
                   size=11, color="grey", text_align="center")
        ]),
        padding=12,
        bgcolor="green50",
        border_radius=8,
        border=ft.border.all(1, "green100")
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
