# 🕷️ Module de Scraping Pappers.fr

## 📋 Vue d'ensemble

Le module de scraping permet d'enrichir vos données **gratuitement** sans clé API, en naviguant sur les pages publiques de Pappers.fr avec des délais aléatoires pour éviter la détection.

⚠️ **Important**: Le scraping est un **fallback gratuit** mais présente des limitations. L'API officielle est recommandée pour un usage professionnel.

---

## 🔄 Modes d'enrichissement

### 1. Mode API (Recommandé)
- ✅ Rapide (0.5s par entreprise)
- ✅ Fiable et stable
- ✅ Données structurées garanties
- ❌ Payant (20-100€/mois selon volume)

### 2. Mode Scraping (Gratuit)
- ✅ **Gratuit**
- ✅ Pas de limite d'utilisation
- ⚠️ Plus lent (2-5s par entreprise)
- ⚠️ Peut être bloqué
- ⚠️ Fragile (HTML peut changer)

### 3. Mode Hybride (Optimal)
- ✅ API en priorité
- ✅ Scraping en fallback si API échoue
- ✅ Meilleure résilience

---

## ⚙️ Configuration

### Fichier `.env`

```env
# ============================================
# MODE API (Recommandé)
# ============================================
PAPPERS_API_KEY=votre_cle_api_ici
PAPPERS_DELAY_SECONDS=0.5

# ============================================
# MODE SCRAPING (Fallback gratuit)
# ============================================
SCRAPING_ENABLED=true

# Délais aléatoires (IMPORTANT pour éviter le blocage)
SCRAPING_MIN_DELAY=2.0
SCRAPING_MAX_DELAY=5.0
```

### Scénarios de configuration

#### 1. API uniquement
```env
PAPPERS_API_KEY=ma_cle_secrete
SCRAPING_ENABLED=false
```

#### 2. Scraping uniquement (gratuit)
```env
SCRAPING_ENABLED=true
SCRAPING_MIN_DELAY=3.0
SCRAPING_MAX_DELAY=7.0
```

#### 3. Hybride (recommandé)
```env
PAPPERS_API_KEY=ma_cle_secrete
SCRAPING_ENABLED=true  # Fallback si API échoue
```

---

## 🚀 Utilisation

### Test rapide

```bash
python test_scraping.py
```

### Dans votre code

```python
from enrichment_pappers import get_company_data_unified

# Mode automatique (API → Scraping)
data = get_company_data_unified('449162163')

# Forcer le scraping
data = get_company_data_unified('449162163', prefer_api=False)
```

### Interface Streamlit

```bash
streamlit run app_pappers.py
```

L'interface détecte automatiquement le mode disponible :
- **Clé API configurée** → Mode API avec fallback scraping
- **Pas de clé API** → Mode scraping uniquement

---

## 🛡️ Mécanismes anti-détection

### 1. Délais aléatoires

```python
# Entre chaque requête: 2-5 secondes (aléatoire)
delay = random.uniform(2.0, 5.0)
time.sleep(delay)
```

**Pourquoi c'est important:**
- ✅ Simule un comportement humain
- ✅ Évite les patterns suspects
- ✅ Réduit le risque de blocage

### 2. Rotation des User-Agents

```python
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) Firefox/121.0',
    # ... 5 user agents différents
]

# Sélection aléatoire à chaque requête
headers = {'User-Agent': random.choice(USER_AGENTS)}
```

### 3. Headers HTTP réalistes

```python
headers = {
    'User-Agent': random_ua,
    'Accept': 'text/html,application/xhtml+xml,...',
    'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.7',
    'Accept-Encoding': 'gzip, deflate, br',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    # ... headers complets
}
```

### 4. Retry automatique avec backoff

```python
# 3 tentatives avec délais croissants
for attempt in range(3):
    try:
        response = requests.get(url)
        if response.status_code == 429:
            wait = random.uniform(2, 5) * (2 ** attempt)
            time.sleep(wait)
    except:
        time.sleep(random.uniform(2, 5))
```

---

## 📊 Performance

### Temps de traitement

| Mode | Temps/entreprise | 100 entreprises | 1000 entreprises |
|------|------------------|-----------------|------------------|
| **API** | 0.5s | ~50s | ~8min |
| **Scraping** | 2-5s (aléatoire) | ~6min | ~1h |
| **Hybride** | 0.5-5s (variable) | ~2-6min | ~10-60min |

### Taux de succès typique

- **API**: 95-98% (instabilité réseau)
- **Scraping**: 70-85% (blocages, timeouts)
- **Hybride**: 90-95% (combine les deux)

---

## ⚠️ Limitations du scraping

### 1. Instabilité
- La structure HTML de Pappers peut changer sans préavis
- Les sélecteurs CSS peuvent devenir obsolètes
- Nécessite maintenance régulière

### 2. Blocage possible
Pappers peut bloquer si :
- Trop de requêtes en peu de temps
- Pattern suspect détecté
- IP mise sur liste noire

**Solutions:**
```env
# Augmenter les délais
SCRAPING_MIN_DELAY=5.0
SCRAPING_MAX_DELAY=10.0
```

### 3. Données incomplètes
Le scraping peut manquer certaines données si :
- Structure HTML différente de prévue
- Données dynamiques chargées en JavaScript
- Format inattendu

### 4. Aspects légaux
⚠️ **Vérifiez les CGU de Pappers.fr** avant usage intensif
- Le scraping peut violer les conditions d'utilisation
- Usage commercial peut nécessiter autorisation
- Privilégiez l'API officielle pour éviter tout problème

---

## 🐛 Dépannage

### ❌ "Aucune donnée récupérée"

**Causes possibles:**
1. Structure HTML de Pappers a changé
2. Scraping bloqué par Pappers
3. Délais trop courts

**Solutions:**
```bash
# Tester manuellement
python test_scraping.py

# Augmenter délais
SCRAPING_MIN_DELAY=7.0
SCRAPING_MAX_DELAY=12.0

# Vérifier les logs
python enrichment_pappers.py
```

### ❌ "Timeout errors"

**Solution:**
```python
# Augmenter timeout dans enrichment_pappers.py
response = requests.get(url, timeout=60)  # Au lieu de 30
```

### ❌ "Rate limit 429"

**Solution:**
```env
# Délais beaucoup plus longs
SCRAPING_MIN_DELAY=10.0
SCRAPING_MAX_DELAY=20.0
```

### ❌ "Données financières mal extraites"

Le parsing HTML peut échouer si la structure change.

**Solution:**
1. Vérifier manuellement sur pappers.fr
2. Utiliser l'API officielle (plus fiable)
3. Signaler le problème pour mise à jour du code

---

## 💡 Bonnes pratiques

### 1. Commencer petit
```python
# Tester sur 5-10 entreprises d'abord
df_test = df.head(10)
enriched = enrich_with_pappers(df_test)
```

### 2. Sauvegardes fréquentes
```python
# Checkpoint tous les 50 SIREN
for i in range(0, len(df), 50):
    batch = enrich_with_pappers(df[i:i+50])
    batch.to_excel(f'backup_{i}.xlsx', index=False)
```

### 3. Heures creuses
- Scraper la nuit (moins de surveillance)
- Week-ends (trafic plus faible)
- Éviter 9h-18h en semaine

### 4. Rotation d'IP (avancé)
Pour usage intensif, utilisez des proxies :
```python
proxies = {
    'http': 'http://proxy1.com:8080',
    'https': 'https://proxy1.com:8080'
}
response = requests.get(url, proxies=proxies)
```

### 5. Monitoring
```python
# Logger les échecs
import logging
logging.basicConfig(filename='scraping.log', level=logging.INFO)
```

---

## 🎯 Quand utiliser chaque mode

### Utilisez l'API si:
- ✅ Budget disponible (20-100€/mois)
- ✅ Usage régulier/professionnel
- ✅ Besoin de fiabilité
- ✅ Gros volumes (>100 entreprises/jour)

### Utilisez le scraping si:
- ✅ Test/prototype
- ✅ Usage ponctuel
- ✅ Budget limité
- ✅ Petits volumes (<50 entreprises/jour)

### Utilisez le mode hybride si:
- ✅ Budget limité mais besoin de fiabilité
- ✅ Volumes moyens (50-200/jour)
- ✅ Tolérance aux temps variables

---

## 📈 Améliorer le taux de succès

### 1. Délais généreux
```env
SCRAPING_MIN_DELAY=5.0  # Plus lent mais plus sûr
SCRAPING_MAX_DELAY=10.0
```

### 2. Filtrer en amont
```python
# Scraper seulement les grandes entreprises
df_filtered = df[df['Effectif'] > 50]
```

### 3. Vérifier la disponibilité
```python
# Vérifier qu'une page existe avant scraping
response = requests.head(url)
if response.status_code == 200:
    data = scrape_company_data_pappers(siren)
```

---

## 🔒 Considérations légales

### ⚠️ IMPORTANT

Le scraping web soulève des questions légales :

1. **CGU de Pappers.fr**: Vérifiez qu'ils autorisent le scraping
2. **Usage commercial**: Peut nécessiter licence
3. **Données personnelles**: RGPD applicable
4. **Propriété intellectuelle**: Contenus potentiellement protégés

**Recommandations:**
- 📧 Contactez Pappers pour autorisation
- 📜 Lisez attentivement les CGU
- 💼 Pour usage professionnel → API officielle
- 🎓 Pour recherche/éducation → OK avec précautions

---

## 📞 Support

- **Documentation Pappers**: [pappers.fr/api/documentation](https://www.pappers.fr/api/documentation)
- **CGU Pappers**: [pappers.fr/cgu](https://www.pappers.fr/cgu)
- **Alternative légale**: API officielle Pappers

---

## ✅ Checklist avant utilisation

- [ ] Délais configurés (min 2s)
- [ ] Mode hybride activé (API + scraping)
- [ ] Test sur petit échantillon effectué
- [ ] Sauvegardes automatiques en place
- [ ] CGU Pappers.fr consultées
- [ ] Monitoring des erreurs actif
- [ ] Plan B (API) prévu si blocage

---

**🎯 Prêt à scraper ?** Lancez `python test_scraping.py` pour tester !
