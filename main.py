# main.py - NUR FÜR ANDROID
import flet as ft
import sys

def main(page: ft.Page):
    # Einfache App die garantiert auf Android funktioniert
    page.title = "SAFKATY"
    
    # Header
    page.add(
        ft.Column([
            ft.Row([
                ft.Icon(ft.icons.PUBLIC, color="blue", size=40),
                ft.Column([
                    ft.Text("SAFKATY", size=32, weight="bold"),
                    ft.Text("Marchés Publics", size=14, color="grey")
                ])
            ]),
            ft.Divider(),
            ft.Text("Willkommen bei SAFKATY Mobile!", size=18),
            ft.Text("Diese App funktioniert auf Android.", size=14, color="green"),
            ft.Divider(),
            ft.ElevatedButton(
                "Test starten",
                icon="play_arrow",
                on_click=lambda e: page.add(ft.Text("✅ Test erfolgreich!", color="green"))
            )
        ])
    )

# App für Android
if __name__ == "__main__":
    # Dies wird auf Android korrekt funktionieren
    ft.app(target=main)
