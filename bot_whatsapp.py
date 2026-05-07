"""
╔══════════════════════════════════════════════╗
║     BOT MODÉRATION WHATSAPP — RENDER.COM     ║
╚══════════════════════════════════════════════╝

MODIFIE UNIQUEMENT CES DEUX LIGNES AVANT DE DÉPLOYER :
    TON_NUMERO = "33612345678"
    NOM_GROUPE = "Nom exact de ton groupe"
"""

import json
import re
import os
import sys
from datetime import datetime, timedelta

# ─────────────────────────────────────────────────────────
#  CONFIGURATION — MODIFIE CES DEUX LIGNES
# ─────────────────────────────────────────────────────────

TON_NUMERO = os.environ.get("WA_NUMERO", "METS_TON_NUMERO_ICI")
NOM_GROUPE = os.environ.get("WA_GROUPE", "METS_LE_NOM_DU_GROUPE")

MOTS_INTERDITS = [
    "idiot", "imbécile", "crétin", "connard", "salaud",
    "abruti", "débile", "stupide", "con", "nul",
    "bâtard", "enculé", "fils de pute",
    # Ajoute tes mots ici
]

MAX_AVERTISSEMENTS = 3
MAX_MUTES          = 3
DUREE_MUTE_MIN     = 30

# ─────────────────────────────────────────────────────────
#  BASE DE DONNÉES LOCALE
# ─────────────────────────────────────────────────────────

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
        data[uid] = {
            "nom": nom,
            "avertissements": 0,
            "mutes": 0,
            "mute_fin": None,
            "banni": False
        }
    data[uid]["nom"] = nom
    return data[uid]

# ─────────────────────────────────────────────────────────
#  DÉTECTION
# ─────────────────────────────────────────────────────────

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
    delta = datetime.fromisoformat(p["mute_fin"]) - datetime.now()
    return max(0, int(delta.total_seconds() / 60))

# ─────────────────────────────────────────────────────────
#  ACTIONS
# ─────────────────────────────────────────────────────────

def avertir(data, uid, nom):
    p = profil(data, uid, nom)
    p["avertissements"] += 1
    n = p["avertissements"]
    sauver(data)
    if n >= MAX_AVERTISSEMENTS:
        return muter(data, uid, nom)
    restants = MAX_AVERTISSEMENTS - n
    return (
        f"⚠️ *Avertissement {n}/{MAX_AVERTISSEMENTS}* — @{nom}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Reste respectueux 🙏\n"
        f"Encore *{restants} avertissement(s)* avant la sourdine."
    )

def muter(data, uid, nom):
    p = profil(data, uid, nom)
    p["mutes"] += 1
    p["avertissements"] = 0
    fin = datetime.now() + timedelta(minutes=DUREE_MUTE_MIN)
    p["mute_fin"] = fin.isoformat()
    n = p["mutes"]
    sauver(data)
    if n >= MAX_MUTES:
        return bannir(data, uid, nom)
    restants = MAX_MUTES - n
    return (
        f"🔇 *@{nom} est en sourdine* pour {DUREE_MUTE_MIN} min\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Mute {n}/{MAX_MUTES} — encore {restants} mute(s) avant le ban."
    )

def bannir(data, uid, nom):
    p = profil(data, uid, nom)
    p["banni"] = True
    sauver(data)
    return (
        f"🚫 *@{nom} a été banni du groupe*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Trop d'infractions. Au revoir ! 👋"
    )

def gracier(data, uid, nom, admin):
    p = profil(data, uid, nom)
    p["avertissements"] = 0
    p["mutes"]          = 0
    p["mute_fin"]       = None
    p["banni"]          = False
    sauver(data)
    return f"✅ *@{nom} gracié* par @{admin}. Nouvelle chance ! 🕊️"

def stats(data, uid, nom):
    p = profil(data, uid, nom)
    mute_info = f"Oui ({min_restantes(p)} min)" if est_mute(p) else "Non"
    return (
        f"📊 *Casier de @{nom}*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"⚠️ Avertissements : {p['avertissements']}/{MAX_AVERTISSEMENTS}\n"
        f"🔇 Mutes : {p['mutes']}/{MAX_MUTES}\n"
        f"⏱️ Mute actif : {mute_info}\n"
        f"🚫 Banni : {'Oui' if p['banni'] else 'Non'}"
    )

# ─────────────────────────────────────────────────────────
#  TRAITEMENT MESSAGE
# ─────────────────────────────────────────────────────────

def traiter(uid, nom, texte, est_admin=False):
    data = charger()
    p    = profil(data, uid, nom)

    if p["banni"]:
        return None

    if est_mute(p):
        return f"🔇 @{nom}, sourdine encore {min_restantes(p)} min."

    texte = texte.strip()

    if texte.startswith("/"):
        if not est_admin:
            return "❌ Commandes réservées aux admins."
        parties  = texte.split()
        cmd      = parties[0].lower()
        cible    = parties[1].lstrip("@") if len(parties) > 1 else None
        if not cible:
            return "❌ Précise un pseudo. Ex : /warn @pseudo"

        cible_uid = cible
        for k, v in data.items():
            if v.get("nom", "").lower() == cible.lower():
                cible_uid = k
                break

        if cmd == "/warn":   return avertir(data, cible_uid, cible)
        if cmd == "/mute":   return muter(data, cible_uid, cible)
        if cmd == "/ban":    return bannir(data, cible_uid, cible)
        if cmd == "/pardon": return gracier(data, cible_uid, cible, nom)
        if cmd == "/stats":  return stats(data, cible_uid, cible)
        return "❓ Commandes : /warn /mute /ban /pardon /stats"

    if a_insulte(texte):
        return avertir(data, uid, nom)

    return None

# ─────────────────────────────────────────────────────────
#  CONNEXION WHATSAPP AVEC whatsapp-web.py
# ─────────────────────────────────────────────────────────

def demarrer():
    print("="*50)
    print("  BOT MODÉRATION — Démarrage sur Render")
    print("="*50)

    try:
        from whatsapp_web_py import WhatsApp
    except ImportError:
        print("❌ whatsapp-web-py non trouvé. Vérifie requirements.txt")
        sys.exit(1)

    print("\n📱 Scan du QR code nécessaire au premier lancement")
    print("   Consulte les logs Render pour voir le QR\n")

    wa = WhatsApp(session_data_path="./session")

    @wa.on_message()
    def handler(message):
        try:
            if not message.is_group:
                return
            if message.group.name != NOM_GROUPE:
                return

            uid       = message.sender.phone
            nom       = message.sender.name or uid
            texte     = message.text or ""
            est_admin = message.sender.is_admin

            if not texte:
                return

            print(f"[{nom}]: {texte[:80]}")
            reponse = traiter(uid, nom, texte, est_admin)
            if reponse:
                wa.send_message(message.group.id, reponse)
                print(f"[BOT] ➜ {reponse[:80]}")

        except Exception as e:
            print(f"⚠️ Erreur: {e}")

    wa.run()

# ─────────────────────────────────────────────────────────
#  LANCEMENT
# ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    if "METS_TON_NUMERO" in TON_NUMERO:
        print("⚠️  Configure WA_NUMERO dans les variables d'environnement Render !")
        sys.exit(1)
    demarrer()
