import flet as ft
import os

def main(page: ft.Page):
    page.title = "SAFKATY"
    page.vertical_alignment = "center"
    page.horizontal_alignment = "center"
    
    # Textfeld für Ausgabe
    ausgabe = ft.TextField(
        multiline=True,
        min_lines=10,
        max_lines=20,
        width=500,
        read_only=True,
        border_color="blue"
    )
    
    # Button-Funktion
    def starte_safkaty(e):
        ausgabe.value = "🔍 Prüfe Dateien...\n"
        page.update()
        
        # 1. Dateien auflisten
        dateien = os.listdir(".")
        ausgabe.value += f"📁 {len(dateien)} Dateien gefunden:\n"
        for datei in dateien:
            ausgabe.value += f"  • {datei}\n"
        
        page.update()
        
        # 2. safkaty.py suchen
        ausgabe.value += "\n🔎 Suche safkaty.py...\n"
        if "safkaty.py" in dateien:
            ausgabe.value += "✅ safkaty.py GEFUNDEN!\n"
            
            # Test: Einfache Ausgabe
            ausgabe.value += "\n📋 TEST-AUSGABE:\n"
            ausgabe.value += "=" * 40 + "\n"
            ausgabe.value += "SAFKATY Marchés Publics\n"
            ausgabe.value += "Version 1.0\n"
            ausgabe.value += "Funktioniert!\n"
            ausgabe.value += "=" * 40 + "\n"
            
        else:
            ausgabe.value += "❌ safkaty.py NICHT GEFUNDEN!\n"
            ausgabe.value += "Bitte sicherstellen dass die Datei existiert.\n"
        
        page.update()
    
    # Button
    button = ft.ElevatedButton(
        "🚀 SAFKATY STARTEN",
        on_click=starte_safkaty,
        width=250,
        height=50,
        style=ft.ButtonStyle(
            bgcolor="blue",
            color="white"
        )
    )
    
    # Alles zusammenbauen
    page.add(
        ft.Column([
            ft.Text("✅ SAFKATY IST BEREIT", size=20, color="green"),
            ft.Text("SAFKATY", size=36, weight="bold"),
            ft.Text("Marchés publics manager", size=18),
            ft.Divider(),
            button,
            ft.Divider(),
            ausgabe,
            ft.Text("Klicke den blauen Button oben", size=12, color="gray")
        ],
        spacing=20,
        horizontal_alignment="center")
    )

ft.app(target=main)
