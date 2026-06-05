from flask import Flask, jsonify, request
import mysql.connector
from mysql.connector import Error
import urllib.request
import urllib.error
import json as json_lib

GROQ_API_KEY = "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"
GROQ_MODEL   = "openrouter/free"
GROQ_URL     = "https://openrouter.ai/api/v1/chat/completions" 

app = Flask(__name__)

@app.after_request
def add_headers(response):
    # Ne pas forcer JSON sur la route principale qui sert le HTML
    if request.path != '/':
        response.headers['Content-Type'] = 'application/json; charset=utf-8'
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response

import os

@app.route('/')
def index():
    html_path = os.path.join(os.path.expanduser('~'), 'Desktop', 'RTVC_Plateforme_MySQL.html')
    with open(html_path, 'r', encoding='utf-8') as f:
        return f.read()


# ── CONFIGURATION ────────────────────────────────────────────────────
DB_CONFIG = {
    'host':     '127.0.0.1',
    'user':     'root',
    'password': 'JumaiChou0906',
    'database': 'rtvc',
    'charset':  'utf8mb4',
    'use_unicode': True,
    'collation': 'utf8mb4_unicode_ci'
}


def word_pattern(word):
    """Construit un pattern regex pour trouver un mot exact."""
    return '(^|[ .,;:!?()\"\'-])' + word.lower() + '([ .,;:!?()\"\'-]|$)'

# Mots vides a ignorer dans les recherches
STOP_WORDS = {
    'la','le','les','de','du','des','un','une','en','et','ou','à','au','aux',
    'ce','se','sa','si','y','il','ils','elle','elles','je','tu','nous','vous',
    'que','qui','quoi','dont','the','a','an','in','of','to','is','are','was',
    'for','on','with','at','by','from','this','that','be','as','it','its'
}

def build_query(q):
    q = q.strip()
    words = q.lower().split()
    if len(words) == 1:
        # Mot simple: cherche le mot exact avec frontieres
        return [word_pattern(words[0])], 'single'
    else:
        # Phrase: cherche la sequence exacte de mots
        return [q.lower()], 'phrase'





def remove_accents(text):
    """Supprime les accents d un texte."""
    import unicodedata
    return ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'
    )

SYNONYMES = {
    'foi': ['foi', 'croire', 'croyance', 'croyant', 'confiance', 'faith', 'believe', 'belief'],
    'grandir': ['grandir', 'croître', 'maturité', 'croissance', 'mûrir', 'progresser', 'avancer',
                'sanctification', 'disciple', 'formation', 'grow', 'growth', 'mature', 'maturity'],
    'prier': ['prier', 'prière', 'intercession', 'prayer', 'pray', 'supplication', 'oraison',
              'communier', 'adorer', 'chercher', 'implorer', 'intercéder'],
    'priere': ['prière', 'prier', 'intercession', 'prayer', 'pray', 'supplication', 'priere'],
    'jeune': ['jeûne', 'jeune', 'jeuner', 'fasting', 'fast', 'abstinence'],
    'dieu': ['dieu', 'seigneur', 'éternel', 'eternel', 'père', 'pere', 'god', 'lord', 'father', 'créateur'],
    'jesus': ['jésus', 'jesus', 'christ', 'sauveur', 'fils', 'messie', 'savior'],
    'bible': ['bible', 'parole', 'écriture', 'ecriture', 'scripture', 'verset', 'verse', 'évangile', 'evangile'],
    'amour': ['amour', 'aimer', 'aimé', 'aime', 'charité', 'charite', 'tendresse', 'love', 'charity'],
    'guerison': ['guérison', 'guerison', 'guérir', 'guerir', 'guéri', 'santé', 'healing', 'heal', 'miracle'],
    'fidelite': ['fidélité', 'fidelite', 'fidèle', 'fidele', 'fidèles', 'fideles', 'loyal', 'loyauté', 'faithfulness', 'faithful'],
    'grace': ['grâce', 'grace', 'miséricorde', 'misericorde', 'bonté', 'bonte', 'bénédiction', 'benediction', 'mercy', 'blessing'],
    'paix': ['paix', 'tranquillité', 'repos', 'peace', 'rest', 'shalom'],
    'peche': ['péché', 'peche', 'pécheur', 'pecheur', 'faute', 'transgression', 'sin', 'sinner'],
    'salut': ['salut', 'sauvé', 'sauve', 'sauver', 'salvation', 'saved', 'délivrance'],
    'esprit': ['esprit', 'saint', 'paraclet', 'spirit', 'holy'],
    'mission': ['mission', 'évangélisation', 'evangelisation', 'témoignage', 'temoignage', 'evangelism', 'witness'],
    'eglise': ['église', 'eglise', 'assemblée', 'assemblee', 'communauté', 'communaute', 'congregation', 'church'],
    'louange': ['louange', 'adoration', 'adorer', 'worship', 'praise', 'glorifier'],
    'enseignement': ['enseignement', 'enseigner', 'prédication', 'predication', 'prêcher', 'precher', 'teaching', 'sermon'],
    'homme': ['homme', 'hommes', 'frère', 'frere', 'frères', 'freres', 'man', 'men', 'brother'],
    'femme': ['femme', 'femmes', 'sœur', 'soeur', 'sœurs', 'soeurs', 'woman', 'women', 'sister'],
    'enfant': ['enfant', 'enfants', 'jeunesse', 'child', 'children', 'youth'],
    'famille': ['famille', 'foyer', 'mariage', 'family', 'home', 'marriage'],
    'argent': ['argent', 'richesse', 'offrande', 'dîme', 'dime', 'money', 'wealth', 'tithe'],
    'souffrance': ['souffrance', 'souffrir', 'épreuve', 'epreuve', 'trial', 'suffering', 'pain'],
}

DATE_PATTERNS_CHRONO = [
    r'\b(\d{1,2})\s+(janvier|f[eé]vrier|mars|avril|mai|juin|juillet|ao[uû]t|septembre|octobre|novembre|d[eé]cembre)\s+(201[0-9]|202[0-6])\b',
    r'\b(201[0-9]|202[0-6])\s+(janvier|f[eé]vrier|mars|avril|mai|juin|juillet|ao[uû]t|septembre|octobre|novembre|d[eé]cembre)\b',
    r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{{1,2}}[,\s]+(201[0-9]|202[0-6])\b',
    r'\b(201[0-9]|202[0-6])[/-](0[1-9]|1[0-2])[/-](0[1-9]|[12]\d|3[01])\b',
    r'\b(nous sommes en|c\'est en|en|year|en l\'an)\s+(201[0-9]|202[0-6])\b',
]

def extract_year_from_text(text):
    """Extrait l annee mentionnee dans le texte."""
    if not text:
        return None
    import re as re2
    from collections import Counter
    text_lower = text.lower()
    years = []
    for pattern in DATE_PATTERNS_CHRONO:
        for m in re2.finditer(pattern, text_lower, re2.IGNORECASE):
            for g in m.groups():
                if g and re2.match(r'^20[0-9]{2}$', str(g)):
                    years.append(int(g))
    # Garder seulement les années entre 2010 et 2026
    years = [y for y in years if 2010 <= y <= 2026]
    if years:
        return Counter(years).most_common(1)[0][0]
    return None


def expand_query(q):
    """Expande la requete avec des synonymes et mots lies."""
    words = [w.strip().lower() for w in q.split() if len(w.strip()) > 2]
    expanded = set()
    for word in words:
        word_na = remove_accents(word)
        # Ajouter le mot original (avec accents) ET sans accents
        expanded.add(word)
        expanded.add(word_na)
        for key, synonyms in SYNONYMES.items():
            if word_na == key or word_na in [remove_accents(s) for s in synonyms] or word in synonyms:
                # Ajouter tous les synonymes avec ET sans accents
                for s in synonyms:
                    expanded.add(s)
                    expanded.add(remove_accents(s))
                break
        if word_na.endswith('s') and len(word_na) > 4:
            expanded.add(word_na[:-1])
    return list(expanded) if expanded else [word.lower() for word in words]


def get_conn():
    conn = mysql.connector.connect(**DB_CONFIG)
    conn.set_charset_collation('utf8mb4', 'utf8mb4_unicode_ci')
    return conn

# ── ROUTES ───────────────────────────────────────────────────────────

# Stats generales
@app.route('/api/stats')
def stats():
    try:
        conn   = get_conn()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT COUNT(*) as total FROM medias")
        total = cursor.fetchone()['total']

        cursor.execute("SELECT COUNT(*) as total FROM medias WHERE has_text = 1")
        with_text = cursor.fetchone()['total']

        cursor.execute("SELECT COUNT(*) as total FROM segments")
        total_segs = cursor.fetchone()['total']

        cursor.execute("SELECT source, COUNT(*) as n FROM medias GROUP BY source ORDER BY n DESC")
        sources = cursor.fetchall()

        cursor.close()
        conn.close()

        return jsonify({
            'total':        total,
            'with_text':    with_text,
            'total_segments': total_segs,
            'sources':      sources
        })
    except Error as e:
        return jsonify({'error': str(e)}), 500


# Recherche dans les titres
@app.route('/api/search/titles')
def search_titles():
    q      = request.args.get('q', '').strip()
    source = request.args.get('source', '')
    limit  = int(request.args.get('limit', 50))

    if not q:
        return jsonify([])

    try:
        conn   = get_conn()
        cursor = conn.cursor(dictionary=True)

        sql    = "SELECT id, title, source, runtime, has_text, summary FROM medias WHERE LOWER(title) LIKE %s"
        params = ['%' + q.lower() + '%']

        if source and source != 'all':
            sql    += " AND source = %s"
            params.append(source)

        sql += " LIMIT %s"
        params.append(limit)

        cursor.execute(sql, params)
        results = cursor.fetchall()

        cursor.close()
        conn.close()
        return jsonify(results)
    except Error as e:
        return jsonify({'error': str(e)}), 500


# Recherche dans les segments (timestamps)
@app.route('/api/search/segments')
def search_segments():
    q      = request.args.get('q', '').strip()
    source = request.args.get('source', '')
    limit  = int(request.args.get('limit', 200))

    if not q:
        return jsonify([])

    try:
        conn   = get_conn()
        cursor = conn.cursor(dictionary=True)

        # Recherche simple et precise
        q_lower = q.lower().strip()
        q_no_accent = remove_accents(q_lower)
        boundary = '(^|[^a-zA-ZÀ-ÿ])'

        if len(q_lower.split()) == 1:
            # Mot unique: frontières de mots avec et sans accent
            pattern1 = boundary + q_lower + '([^a-zA-ZÀ-ÿ]|$)'
            pattern2 = boundary + q_no_accent + '([^a-zA-ZÀ-ÿ]|$)'
            if q_lower != q_no_accent:
                where  = "(LOWER(s.text) REGEXP %s OR LOWER(s.text) REGEXP %s)"
                params = [pattern1, pattern2]
            else:
                where  = "LOWER(s.text) REGEXP %s"
                params = [pattern1]
        else:
            # Phrase exacte
            if q_lower != q_no_accent:
                where  = "(LOWER(s.text) LIKE %s OR LOWER(s.text) LIKE %s)"
                params = ['%' + q_lower + '%', '%' + q_no_accent + '%']
            else:
                where  = "LOWER(s.text) LIKE %s"
                params = ['%' + q_lower + '%']

        sql = """
            SELECT s.id, s.media_id, s.start_time, s.end_time, s.text,
                   m.title, m.source, m.soundcloud_link, m.video_path,
                   m.drive_link, m.runtime, m.summary
            FROM segments s
            JOIN medias m ON s.media_id = m.id
            WHERE """ + where + """
        """

        if source and source != 'all':
            sql    += " AND m.source = %s"
            params.append(source)

        sql += " ORDER BY m.id LIMIT %s"
        params.append(limit)

        cursor.execute(sql, params)
        rows = cursor.fetchall()

        # Grouper par media
        import re as re_module
        grouped = {}
        for row in rows:
            mid = row['media_id']
            if mid not in grouped:
                grouped[mid] = {
                    'media_id':      mid,
                    'title':         row['title'],
                    'source':        row['source'],
                    'soundcloud':    row['soundcloud_link'],
                    'video':         row['video_path'],
                    'drive':         row['drive_link'],
                    'runtime':       row['runtime'],
                    'summary':       row.get('summary', ''),
                    'segments':      []
                }
            grouped[mid]['segments'].append({
                's': float(row['start_time'] or 0),
                'e': float(row['end_time']   or 0),
                't': row['text']
            })

        # Segments déjà filtrés par SQL

        results = sorted(grouped.values(), key=lambda x: -len(x['segments']))
        cursor.close()
        conn.close()
        return jsonify(results)
    except Error as e:
        return jsonify({'error': str(e)}), 500


# Recherche par theme
@app.route('/api/search/theme')
def search_theme():
    keywords = request.args.getlist('kw')
    limit    = int(request.args.get('limit', 200))

    if not keywords:
        return jsonify([])

    try:
        conn   = get_conn()
        cursor = conn.cursor(dictionary=True)

        # Recherche mot exact: entouré d'espaces ou de ponctuation
        conditions = " OR ".join(["LOWER(s.text) REGEXP %s"] * len(keywords))
        params     = [word_pattern(kw) for kw in keywords]

        sql = f"""
            SELECT s.media_id, s.start_time, s.end_time, s.text,
                   m.title, m.source, m.soundcloud_link, m.video_path,
                   m.drive_link, m.runtime
            FROM segments s
            JOIN medias m ON s.media_id = m.id
            WHERE {conditions}
            ORDER BY m.id
            LIMIT %s
        """
        params.append(limit)

        cursor.execute(sql, params)
        rows = cursor.fetchall()

        grouped = {}
        for row in rows:
            mid = row['media_id']
            if mid not in grouped:
                grouped[mid] = {
                    'media_id':   mid,
                    'title':      row['title'],
                    'source':     row['source'],
                    'soundcloud': row['soundcloud_link'],
                    'video':      row['video_path'],
                    'drive':      row['drive_link'],
                    'runtime':    row['runtime'],
                    'segments':   []
                }
            grouped[mid]['segments'].append({
                's': float(row['start_time'] or 0),
                'e': float(row['end_time']   or 0),
                't': row['text']
            })

        results = sorted(grouped.values(), key=lambda x: -len(x['segments']))
        cursor.close()
        conn.close()
        return jsonify(results)
    except Error as e:
        return jsonify({'error': str(e)}), 500


# Chronologie
@app.route('/api/chrono')
def chrono():
    year = request.args.get('year', '')
    try:
        conn   = get_conn()
        cursor = conn.cursor(dictionary=True)

        # Recuperer tous les medias avec leur transcription pour extraire la date
        if year and year != 'all':
            # Filtrer par annee: chercher dans le titre GMT ou annee explicite
            sql = """
                SELECT m.id, m.title, m.source, m.runtime,
                       m.soundcloud_link, m.video_path, m.drive_link,
                       LEFT(t.text, 2000) as trans_text
                FROM medias m
                LEFT JOIN transcriptions t ON t.media_id = m.id
                WHERE m.title REGEXP '[0-9]{4}'
                   OR m.title LIKE 'GMT%'
                ORDER BY m.id
            """
            cursor.execute(sql)
        else:
            sql = """
                SELECT m.id, m.title, m.source, m.runtime,
                       m.soundcloud_link, m.video_path, m.drive_link,
                       LEFT(t.text, 2000) as trans_text
                FROM medias m
                LEFT JOIN transcriptions t ON t.media_id = m.id
                WHERE m.title REGEXP '[0-9]{4}'
                   OR m.title LIKE 'GMT%'
                ORDER BY m.id
            """
            cursor.execute(sql)

        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        import re
        result = []
        for row in rows:
            title = row['title'] or ''
            extracted_year = None

            # Extraction annee: GMT en priorite, sinon titre nettoye
            gmt_m = re.search(r'GMT(20[0-9]{2})[0-9]{4}', title)
            if gmt_m:
                extracted_year = int(gmt_m.group(1))
            else:
                # Nettoyer les sequences de 5+ chiffres pour eviter faux positifs
                clean = re.sub(r'[0-9]{5,}', '', title)
                matches = re.findall(r'(?<![0-9])(201[0-9]|202[0-6])(?![0-9])', clean)
                extracted_year = int(matches[0]) if matches else None

            if not extracted_year:
                continue

            # Filtrer par annee si demande
            if year and year != 'all' and str(extracted_year) != str(year):
                continue

            result.append({
                'id':         row['id'],
                'title':      title,
                'source':     row['source'],
                'runtime':    row['runtime'],
                'year':       extracted_year,
                'soundcloud': row.get('soundcloud_link'),
                'video':      row.get('video_path'),
                'drive':      row.get('drive_link'),
            })

        # Trier par annee decroissante
        result.sort(key=lambda x: x['year'], reverse=True)
        return jsonify(result)

    except Error as e:
        return jsonify({'error': str(e)}), 500



# ── CHATBOT ──────────────────────────────────────────────────────────
@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.get_json()
    question = (data.get('question') or '').strip()
    history  = data.get('history') or []
    if not question:
        return jsonify({'error': 'Question vide'}), 400

    try:
        conn   = get_conn()
        cursor = conn.cursor(dictionary=True)

        # Chercher les segments pertinents dans MySQL
        words = [w for w in question.lower().split() if len(w) > 2 and w not in STOP_WORDS]
        if not words:
            words = question.lower().split()

        all_segments = []
        seen_ids = set()

        # Filtrer les mots vides et garder seulement les mots significatifs
        STOP_WORDS_FR = {'comment', 'quoi', 'quelle', 'quels', 'quelles', 'quel',
                         'est', 'sont', 'les', 'des', 'une', 'pour', 'dans', 'avec',
                         'que', 'qui', 'quand', 'vous', 'nous', 'peut', 'plus',
                         'bien', 'aussi', 'tout', 'cette', 'faire', 'avoir',
                         'efficacement', 'vraiment', 'correctement', 'simplement',
                         'facilement', 'rapidement', 'seulement', 'maintenant',
                         'toujours', 'jamais', 'souvent', 'parfois', 'encore',
                         'what', 'how', 'why', 'when', 'where', 'which', 'the',
                         'effectively', 'really', 'truly', 'simply', 'just'}
        # Mots clés de la question (sans mots vides)
        key_words = [w for w in words if len(w) > 3 and remove_accents(w.lower()) not in STOP_WORDS_FR][:5]
        if not key_words:
            key_words = [w for w in words if len(w) > 3][:3]
        if not key_words:
            key_words = words[:3]
        # Expansion avec synonymes pour les mots clés
        search_words = []
        for kw in key_words:
            kw_na = remove_accents(kw.lower())
            search_words.append(kw)
            for key, synonyms in SYNONYMES.items():
                if kw_na == key or kw_na in [remove_accents(s) for s in synonyms]:
                    search_words.extend(synonyms[:4])
                    break
        search_words = list(dict.fromkeys(search_words))[:8]  # dédupliquer
        # 1. Chercher dans les transcriptions completes avec les mots exacts
        for word in search_words[:4]:
            cursor.execute("""
                SELECT SUBSTRING(t.text,
                       GREATEST(1, LOCATE(%s, LOWER(t.text)) - 200),
                       2500) as text,
                       LOCATE(%s, LOWER(t.text)) as text_position,
                       LENGTH(t.text) as text_length,
                       m.title, m.soundcloud_link,
                       m.video_path, m.drive_link, m.id as media_id,
                       m.runtime
                FROM transcriptions t
                JOIN medias m ON t.media_id = m.id
                WHERE t.text LIKE %s OR t.text LIKE %s
                ORDER BY 
                    CASE WHEN t.text REGEXP '[\u00e0-\u00ff]' THEN 0 ELSE 1 END,
                    LENGTH(t.text) DESC
                LIMIT 5
            """, [word, word, '%' + word + '%', '%' + remove_accents(word) + '%'])
            rows = cursor.fetchall()
            for row in rows:
                key = ('trans', row['media_id'])
                if key not in seen_ids:
                    seen_ids.add(key)
                    # Chercher le timestamp dans les segments horodates du meme enregistrement
                    estimated_ts = 0
                    media_id_val = row.get('media_id')
                    text_val = str(row.get('text') or '')
                    if media_id_val and text_val:
                        # Prendre les 5 premiers mots de l'extrait pour chercher dans segments
                        first_words = ' '.join(text_val.strip().split()[:5]).lower()
                        if first_words:
                            cursor.execute("""
                                SELECT start_time FROM segments
                                WHERE media_id = %s AND LOWER(text) LIKE %s
                                ORDER BY start_time ASC LIMIT 1
                            """, [media_id_val, '%' + first_words[:30] + '%'])
                            seg_row = cursor.fetchone()
                            if seg_row and seg_row['start_time']:
                                estimated_ts = float(seg_row['start_time'])
                            else:
                                # Fallback: chercher le mot cle dans les segments
                                cursor.execute("""
                                    SELECT start_time FROM segments
                                    WHERE media_id = %s AND LOWER(text) LIKE %s
                                    ORDER BY start_time ASC LIMIT 1
                                """, [media_id_val, '%' + word + '%'])
                                seg_row2 = cursor.fetchone()
                                if seg_row2 and seg_row2['start_time']:
                                    estimated_ts = float(seg_row2['start_time'])
                    row['start_time'] = estimated_ts
                    all_segments.append(row)

        # 2. Chercher aussi dans les segments horodates (pour les references avec timestamps)
        for word in search_words[:3]:
            cursor.execute("""
                SELECT s.text, s.start_time, m.title, m.soundcloud_link,
                       m.video_path, m.drive_link, m.id as media_id
                FROM segments s
                JOIN medias m ON s.media_id = m.id
                WHERE LOWER(s.text) REGEXP %s
                ORDER BY s.start_time ASC
                LIMIT 5
            """, ['(^|[^a-zA-ZÀ-ÿ])' + word + '([^a-zA-ZÀ-ÿ]|$)'])
            rows = cursor.fetchall()
            for row in rows:
                key = (row['media_id'], row['start_time'])
                if key not in seen_ids:
                    seen_ids.add(key)
                    all_segments.append(row)

        cursor.close()
        conn.close()

        if not all_segments:
            return jsonify({
                'answer': "Je n'ai pas trouve de passages dans les transcriptions RTVC qui correspondent a votre question. Essayez avec d'autres mots-cles.",
                'references': []
            })

        # Construire le contexte pour Groq
        context_parts = []
        references = []
        for i, seg in enumerate(all_segments[:15]):
            ts_val = float(seg.get('start_time') or 0)
            has_real_ts = ts_val > 0
            context_parts.append("[Extrait " + str(i+1) + "] Titre: " + str(seg["title"]) + " | Texte: " + str(seg["text"]))
            ref = {
                'title': seg['title'],
                'timestamp': round(ts_val),
                'text': seg['text'],
                'soundcloud': seg.get('soundcloud_link'),
                'video': seg.get('video_path'),
                'drive': seg.get('drive_link'),
                'no_timestamp': not has_real_ts
            }
            references.append(ref)

        # Donner le texte complet du premier extrait, résumer les autres
        context_parts_final = []
        for ci, cp in enumerate(context_parts):
            if ci == 0:
                context_parts_final.append(cp)  # Premier extrait complet
            else:
                # Limiter les autres à 300 caractères
                parts = cp.split(' | Texte: ', 1)
                if len(parts) == 2 and len(parts[1]) > 300:
                    context_parts_final.append(parts[0] + ' | Texte: ' + parts[1][:300] + '...')
                else:
                    context_parts_final.append(cp)
        context = "\n\n".join(context_parts_final)

        # Detecter si message conversationnel
        conv_words = ['merci', 'thank', 'bonjour', 'bonsoir', 'salut', 'ok', 'super',
                      'parfait', 'bravo', 'cool', 'good', 'great', 'hello',
                      'au revoir', 'goodbye', 'bye', 'yes', 'no']
        is_conv = len(question.split()) <= 5 and any(w in question.lower() for w in conv_words)

        # Construire l'historique pour le contexte
        hist_text = ""
        if history:
            hist_text = "HISTORIQUE DE LA CONVERSATION:\n"
            for h in history[-6:]:  # garder les 6 derniers échanges
                role = "Utilisateur" if h['role'] == 'user' else "Assistant"
                hist_text += role + ": " + h['content'][:300] + "\n"
            hist_text += "\n"

        if is_conv:
            prompt = (
                "Tu es un assistant chaleureux de Radio Television Voix de la Croix (RTVC).\n"
                "Reponds dans la langue du message de facon naturelle et breve comme un ami.\n"
                + hist_text +
                "Message actuel: '" + question + "'\n"
                "Si le message fait reference a une reponse precedente (ex: 'reponds autrement', 'explique mieux'), "
                "tiens compte de l historique. Maximum 2-3 phrases."
            )
            references = []  # pas de références pour les messages conversationnels
        else:
            prompt = (
                "Tu es un assistant biblique de Radio Television Voix de la Croix (RTVC).\n"
                "LANGUE: Reponds UNIQUEMENT dans la langue de la question.\n"
                + hist_text +
                "INSTRUCTIONS:\n"
                "1. Tiens compte de l historique si la question fait reference a un echange precedent.\n"
                "2. Base-toi UNIQUEMENT sur les extraits fournis. N invente rien.\n"
                "3. Reponds de facon naturelle, detaillee et bien developpee en te basant sur les extraits.\n"
                "4. Developpe chaque point avec des explications claires et approfondies (minimum 5-7 phrases).\n"
                "5. Cite 2-3 passages exacts entre guillemets pour appuyer ta reponse.\n"
                "6. Explique le sens de chaque citation dans son contexte.\n"
                "7. A la fin, ajoute 'En resume:' suivi de 2-3 phrases claires et pratiques.\n"
                "8. Commence par [Extrait N] pour indiquer la source principale.\n"
                "9. Si les extraits ne repondent pas directement: reponds de facon bienveillante sans inventer.\n\n"
                "EXTRAITS RTVC:\n" + context + "\n\n"
                "QUESTION: " + question + "\n\n"
                "REPONSE (detaillee et bien developpee):"
            )
        # Construction de la requete API
        data = json_lib.dumps({
            "model": GROQ_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 2500,
            "temperature": 0
        }).encode('utf-8')

        req = urllib.request.Request(
            GROQ_URL,
            data=data,
            headers={
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + GROQ_API_KEY,
                'HTTP-Referer': 'http://localhost:5000',
                'X-Title': 'RTVC Plateforme'
            },
            method='POST'
        )

        # Retry automatique en cas de rate limit (429)
        import time as time_mod
        for attempt in range(3):
            try:
                resp = urllib.request.urlopen(req, timeout=60)
                result = json_lib.loads(resp.read())
                answer = result['choices'][0]['message']['content'].strip()
                break
            except urllib.error.HTTPError as he:
                if he.code == 429 and attempt < 2:
                    time_mod.sleep(30)
                    continue
                raise he

        # Filtrer les références : garder seulement celles citées par l'IA
        import re as re_sort
        cited_nums = [int(m)-1 for m in re_sort.findall(r'\[Extrait (\d+)\]', answer)]
        not_found = any(p in answer.lower() for p in [
            "pas trouve", "n ai pas trouve", "aucune information", "not found",
            "pas trouvé", "n'ai pas trouvé", "je n'ai pas", "je n ai pas",
            "ne contiennent pas", "extraits ne contiennent", "pas de conseils",
            "not found in", "no information"
        ])

        if is_conv or not_found:
            references = []
        elif cited_nums:
            cited_refs = []
            for idx in cited_nums:
                if 0 <= idx < len(references) and references[idx] not in cited_refs:
                    cited_refs.append(references[idx])
            references = cited_refs[:2]
        else:
            references = references[:1]

        # Nettoyer les tags [Extrait N] de la réponse
        answer = re_sort.sub(r'\[Extrait \d+\]\s*', '', answer).strip()

        return jsonify({'answer': answer, 'references': references})

    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')
        return jsonify({'error': f'Erreur Groq: {e.code} - {body}'}), 500
    except Exception as e:
        return jsonify({'error': f'Erreur serveur Chatbot: {str(e)}'}), 500


if __name__ == '__main__':
    print("Serveur RTVC demarre sur http://localhost:5000")
    print("Appuyez sur Ctrl+C pour arreter")
    app.run(debug=False, host='0.0.0.0', port=5000)
