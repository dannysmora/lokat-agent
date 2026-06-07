"""
LOKAT CI - AGENT CONVERSATIONNEL WHATSAPP v1.0
Meta WhatsApp Cloud API + Groq IA
"""

from flask import Flask, request, jsonify
from groq import Groq
import requests
import json
import logging

app = Flask(__name__)

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────
GROQ_API_KEY    = "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"
META_TOKEN      = "EAAas8vFs4q0BRh7FZCMOzSZBS8T2F4bVCblqbvmuE1N1ruCiz9g6nD4CRxWYKkDpViVd48y1nvraYWpMHWZAEmTe7T8NVuUjyAwuJyElHeHS0GdLhSGWZA7kwAaBm4ZAdC1hDCA9gmRMaFvnUoshYpkc6nbmWxZBw1BWCuNmFuKCYCM1H7dmhBbeUIHJCzNHWGifdsXjwBmJPcQ6nt0uZCCzkdfBZA62C7J9L9y8XUSstrzdJH3fSjYN5Pb307bqPca1AzhuliTwWZB0PRNDwnuUNcYMjbwZDZD"
PHONE_NUMBER_ID = "1070113989528553"
VERIFY_TOKEN    = "lokat_ci_webhook_2026"
LIEN_APP        = "https://dannysmora.github.io/lokat-ci-/"
FICHIER_CONV    = "lokat_conversations.json"

# ─────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("lokat_agent.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("LokatAgent")

# ─────────────────────────────────────────────
# MEMOIRE DES CONVERSATIONS
# ─────────────────────────────────────────────
def charger_conversations():
    try:
        with open(FICHIER_CONV, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def sauvegarder_conversation(telephone, historique):
    data = charger_conversations()
    data[telephone] = historique
    with open(FICHIER_CONV, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_historique(telephone):
    return charger_conversations().get(telephone, [])

# ─────────────────────────────────────────────
# ENVOI DE MESSAGE VIA META API
# ─────────────────────────────────────────────
def envoyer_message(telephone, texte):
    url = f"https://graph.facebook.com/v20.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {META_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": telephone,
        "type": "text",
        "text": {"body": texte}
    }
    try:
        r = requests.post(url, headers=headers, json=payload)
        if r.status_code == 200:
            log.info(f"Message envoye a {telephone}")
            return True
        else:
            log.error(f"Erreur Meta API {r.status_code} : {r.text}")
            return False
    except Exception as e:
        log.error(f"Erreur envoi : {e}")
        return False

# ─────────────────────────────────────────────
# IA - GENERATEUR DE REPONSE
# ─────────────────────────────────────────────
def generer_reponse(telephone, message_recu):
    client     = Groq(api_key=GROQ_API_KEY)
    historique = get_historique(telephone)

    # Compter combien de fois le lien a deja ete envoye
    lien_deja_envoye = any(LIEN_APP in m.get("content", "") for m in historique if m["role"] == "assistant")

    system_prompt = f"""Tu es Kouassi, agent commercial de Lokat CI en Côte d'Ivoire.
Lokat CI est une application GRATUITE de location immobilière qui permet aux propriétaires et agences de publier leurs annonces et aux locataires de trouver facilement un logement.
Lien de téléchargement : {LIEN_APP}

Ton objectif : convaincre le propriétaire ou l'agence de télécharger l'app et publier son bien.

Règles strictes :
- Commence TOUJOURS par répondre au message reçu avant tout.
- Pose une question pour poursuivre l'échange.
- Si la personne possède des biens à louer (maison, appartement, studio, magasin, villa, terrain), explique comment Lokat CI peut l'aider à avoir plus de visibilité.
- Si la personne semble intéressée, partage le lien {LIEN_APP}.
- N'envoie JAMAIS le lien dans chaque message. {'Ne le renvoie pas, il a deja ete envoye.' if lien_deja_envoye else 'Tu peux le partager si la personne est interessee.'}
- Sois poli, chaleureux et naturel. Pas trop formel.
- Utilise un vocabulaire simple adapté à la Côte d'Ivoire.
- Réponses courtes : maximum 4 lignes.
- Si la personne refuse, remercie-la poliment et termine la conversation.
- Si la personne pose une question sur l'app, réponds précisément.
- Ne sois jamais agressif ou trop insistant.
- L'objectif final : inscription ou dépôt d'annonce sur Lokat CI."""

    historique.append({"role": "user", "content": message_recu})
    messages = [{"role": "system", "content": system_prompt}] + historique

    try:
        response = client.chat.completions.create(
            messages=messages,
            model="llama-3.1-8b-instant",
            temperature=0.7,
            max_tokens=200
        )
        reponse_ia = response.choices[0].message.content.strip()
        historique.append({"role": "assistant", "content": reponse_ia})
        sauvegarder_conversation(telephone, historique)
        return reponse_ia
    except Exception as e:
        log.error(f"Erreur IA : {e}")
        return "Désolé, je reviens vers toi très bientôt ! 🙏"

# ─────────────────────────────────────────────
# WEBHOOK META - VERIFICATION
# ─────────────────────────────────────────────
@app.route("/webhook", methods=["GET"])
def verifier_webhook():
    mode      = request.args.get("hub.mode")
    token     = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        log.info("Webhook verifie avec succes !")
        return challenge, 200
    else:
        log.warning("Echec verification webhook")
        return "Forbidden", 403

# ─────────────────────────────────────────────
# WEBHOOK META - RECEPTION DES MESSAGES
# ─────────────────────────────────────────────
@app.route("/webhook", methods=["POST"])
def recevoir_message():
    data = request.get_json()

    try:
        entry   = data["entry"][0]
        changes = entry["changes"][0]
        value   = changes["value"]

        # Verifier que c'est bien un message entrant
        if "messages" not in value:
            return jsonify({"status": "ok"}), 200

        message   = value["messages"][0]
        telephone = message["from"]
        type_msg  = message.get("type", "")

        # Ignorer les messages non-texte (images, audio, etc.)
        if type_msg != "text":
            log.info(f"Message non-texte ignore ({type_msg}) de {telephone}")
            return jsonify({"status": "ok"}), 200

        texte = message["text"]["body"]
        log.info(f"Message recu de {telephone} : {texte}")

        # Generer et envoyer la reponse
        reponse = generer_reponse(telephone, texte)
        log.info(f"Reponse : {reponse}")
        envoyer_message(telephone, reponse)

    except Exception as e:
        log.error(f"Erreur traitement message : {e}")

    return jsonify({"status": "ok"}), 200

# ─────────────────────────────────────────────
# FONCTION POUR LE SCRAPER
# ─────────────────────────────────────────────
def envoyer_premier_message(telephone, message):
    """Appelee par le scraper pour envoyer le 1er message et initialiser la conversation."""
    succes = envoyer_message(telephone, message)
    if succes:
        historique = [{"role": "assistant", "content": message}]
        sauvegarder_conversation(telephone, historique)
    return succes

# ─────────────────────────────────────────────
# POINT D'ENTREE
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 55)
    print("  LOKAT CI - Agent Conversationnel WhatsApp")
    print("=" * 55)
    print("  Webhook : http://localhost:5000/webhook")
    print()
    print("  IMPORTANT : Lance ngrok dans un autre terminal :")
    print("  ngrok http 5000")
    print()
    print("  Copie l'URL ngrok dans Meta Developer Console :")
    print("  Configuration WhatsApp → Webhooks → URL de rappel")
    print(f"  Token de verification : {VERIFY_TOKEN}")
    print("=" * 55)
    app.run(host="0.0.0.0", port=5000, debug=False)
