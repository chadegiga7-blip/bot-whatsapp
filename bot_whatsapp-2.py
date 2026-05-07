"""
Bot de Modération WhatsApp — Version Render.com
"""

import json
import re
import os
import sys
from datetime import datetime, timedelta

TON_NUMERO = os.environ.get("WA_NUMERO", "METS_TON_NUMERO")
NOM_GROUPE = os.environ.get("WA_GROUPE", "METS_LE_GROUPE")

MOTS_INTERDITS = [
    "idiot", "imbécile", "crétin", "connard", "salaud",
    "abruti", "débile", "stupide", "con", "nul",
    "bâtard", "enculé", "fils de pute",
]

MAX_AVERTISSEMENTS = 3
MAX_MUTES          = 3
DUREE_MUTE_MIN     = 30

FICHIER_DATA = "casier.json"

def charger():
    try:
        with open(FICHIER_DATA, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def sauver(data):
    with open(FICHIER_DATA, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def profil(data, uid, nom="?"):
    if uid not in data:
        data[uid] = {"nom": nom, "avertissements": 0, "mutes": 0, "mute_fin": None, "banni": False}
    data[uid]["nom"] = nom
    return data[uid]

def a_insulte(texte):
    t = texte.lower()
    for mot in MOTS_INTERDITS:
        if re.search(r'\b' + re.escape(mot) + r'\b', t):
            return True
    return False

def est_mute(p):
    if not p["mute_fin"]:
        return False
    return datetime.now() < datetime.fromisoformat(p["mute_fin"])

def min_restantes(p):
    if not p["mute_fin"]:
        return 0
    return max(0, int((datetime.fromisoformat(p["mute_fin"]) - datetime.now()).total_seconds() / 60))

def avertir(data, uid, nom):
    p = profil(data, uid, nom)
    p["avertissements"] += 1
    n = p["avertissements"]
    sauver(data)
    if n >= MAX_AVERTISSEMENTS:
        return muter(data, uid, nom)
    return (f"⚠️ *Avertissement {n}/{MAX_AVERTISSEMENTS}* — @{nom}\n"
            f"━━━━━━━━━━━━━━━━━━━━\nReste respectueux 🙏\n"
            f"Encore *{MAX_AVERTISSEMENTS - n} avertissement(s)* avant la sourdine.")

def muter(data, uid, nom):
    p = profil(data, uid, nom)
    p["mutes"] += 1
    p["avertissements"] = 0
    p["mute_fin"] = (datetime.now() + timedelta(minutes=DUREE_MUTE_MIN)).isoformat()
    n = p["mutes"]
    sauver(data)
    if n >= MAX_MUTES:
        return bannir(data, uid, nom)
    return (f"🔇 *@{nom} est en sourdine* pour {DUREE_MUTE_MIN} min\n"
            f"━━━━━━━━━━━━━━━━━━━━\nMute {n}/{MAX_MUTES} — encore {MAX_MUTES - n} mute(s) avant le ban.")

def bannir(data, uid, nom):
    profil(data, uid, nom)["banni"] = True
    sauver(data)
    return f"🚫 *@{nom} a été banni du groupe*\n━━━━━━━━━━━━━━━━━━━━\nTrop d'infractions. Au revoir ! 👋"

def gracier(data, uid, nom, admin):
    p = profil(data, uid, nom)
    p.update({"avertissements": 0, "mutes": 0, "mute_fin": None, "banni": False})
    sauver(data)
    return f"✅ *@{nom} gracié* par @{admin}. Nouvelle chance ! 🕊️"

def stats(data, uid, nom):
    p = profil(data, uid, nom)
    return (f"📊 *Casier de @{nom}*\n━━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ Avertissements : {p['avertissements']}/{MAX_AVERTISSEMENTS}\n"
            f"🔇 Mutes : {p['mutes']}/{MAX_MUTES}\n"
            f"⏱️ Mute actif : {'Oui (' + str(min_restantes(p)) + ' min)' if est_mute(p) else 'Non'}\n"
            f"🚫 Banni : {'Oui' if p['banni'] else 'Non'}")

def traiter(uid, nom, texte, est_admin=False):
    data = charger()
    p    = profil(data, uid, nom)
    if p["banni"]: return None
    if est_mute(p): return f"🔇 @{nom}, sourdine encore {min_restantes(p)} min."
    texte = texte.strip()
    if texte.startswith("/"):
        if not est_admin: return "❌ Commandes réservées aux admins."
        parties = texte.split()
        cmd     = parties[0].lower()
        cible   = parties[1].lstrip("@") if len(parties) > 1 else None
        if not cible: return "❌ Précise un pseudo. Ex : /warn @pseudo"
        cible_uid = next((k for k, v in data.items() if v.get("nom", "").lower() == cible.lower()), cible)
        if cmd == "/warn":   return avertir(data, cible_uid, cible)
        if cmd == "/mute":   return muter(data, cible_uid, cible)
        if cmd == "/ban":    return bannir(data, cible_uid, cible)
        if cmd == "/pardon": return gracier(data, cible_uid, cible, nom)
        if cmd == "/stats":  return stats(data, cible_uid, cible)
        return "❓ Commandes : /warn /mute /ban /pardon /stats"
    if a_insulte(texte): return avertir(data, uid, nom)
    return None

# ─────────────────────────────────────────────
#  CONNEXION WHATSAPP AVEC whatsapp-web.py
# ─────────────────────────────────────────────

def demarrer():
    print("=" * 50)
    print("  BOT MODÉRATION — Démarrage sur Render")
    print("=" * 50)
    print(f"Groupe cible : {NOM_GROUPE}")

    try:
        from whatsapp_web_py import WhatsApp
        print("✅ Bibliothèque chargée")
    except ImportError:
        try:
            # Fallback : essaie le nom alternatif
            from whatsapp import WhatsApp
            print("✅ Bibliothèque chargée (fallback)")
        except ImportError as e:
            print(f"❌ Impossible de charger la bibliothèque WhatsApp : {e}")
            print("Bibliothèques installées :")
            import subprocess
            r = subprocess.run(["pip", "list"], capture_output=True, text=True)
            print(r.stdout)
            sys.exit(1)

    wa = WhatsApp(session_data_path="./wa_session")

    @wa.on_message()
    def on_msg(msg):
        try:
            if not getattr(msg, "is_group", False):
                return
            groupe = getattr(msg, "group", None) or getattr(msg, "chat", None)
            if not groupe:
                return
            nom_groupe = getattr(groupe, "name", "") or getattr(groupe, "title", "")
            if nom_groupe != NOM_GROUPE:
                return

            uid      = getattr(msg.sender, "phone", str(msg.sender))
            nom      = getattr(msg.sender, "name", uid) or uid
            texte    = getattr(msg, "text", "") or getattr(msg, "body", "") or ""
            is_admin = getattr(msg.sender, "is_admin", False)

            if not texte:
                return

            print(f"[{nom}]: {texte[:80]}")
            reponse = traiter(uid, nom, texte, is_admin)
            if reponse:
                msg.reply(reponse)
                print(f"[BOT] ➜ {reponse[:60]}")

        except Exception as e:
            print(f"⚠️ Erreur: {e}")
            import traceback
            traceback.print_exc()

    print("🤖 Bot en écoute...")
    wa.run()

if __name__ == "__main__":
    demarrer()
