"""
Application Streamlit pour l'enrichissement via Pappers.fr
Module complémentaire pour enrichir les données obtenues de l'API publique
"""

import streamlit as st
import pandas as pd
import os
from enrichment_pappers import (
    check_api_key, 
    enrich_with_pappers,
    PAPPERS_DELAY,
    PAPPERS_API_KEY,
    SCRAPING_ENABLED,
    SCRAPING_MIN_DELAY,
    SCRAPING_MAX_DELAY
)

st.set_page_config(
    page_title="Enrichissement Pappers.fr",
    page_icon="💰",
    layout="wide"
)

st.title("💰 Enrichissement Pappers.fr")
st.markdown("""
Cet outil enrichit vos données d'entreprises avec **l'historique financier complet** 
depuis Pappers.fr (historique jusqu'à 10 ans).

**🔄 Deux modes disponibles:**
- **Mode API** (recommandé) : Rapide et fiable avec clé API
- **Mode Scraping** (fallback) : Gratuit mais plus lent (délais aléatoires 2-5s)

**📊 Données ajoutées par Pappers:**
- Chiffre d'affaires (CA) historique
- Résultat net historique  
- Effectifs historique
- Résultat d'exploitation
- Dette financière
- Et bien plus...
""")

# Vérification de la clé API
st.sidebar.header("⚙️ Configuration")

has_api = check_api_key()
has_scraping = SCRAPING_ENABLED

if not has_api and not has_scraping:
    st.error("""
    ❌ **Aucune méthode d'enrichissement configurée**
    
    **Option 1 - API (recommandée):**
    1. Obtenez une clé sur [pappers.fr/api](https://www.pappers.fr/api)
    2. Créez un fichier `.env` : `PAPPERS_API_KEY=votre_clé`
    
    **Option 2 - Scraping (gratuit):**
    1. Créez un fichier `.env` : `SCRAPING_ENABLED=true`
    2. ⚠️ Plus lent (2-5s par entreprise) avec délais aléatoires
    
    **Template disponible:** `.env.example`
    """)
    st.stop()

# Affichage du mode actif
if has_api:
    st.sidebar.success("✅ Mode API activé")
    st.sidebar.info(f"⏱️ Délai API: {PAPPERS_DELAY}s")
    
    # Afficher l'abonnement détecté
    if PAPPERS_DELAY >= 2.0:
        st.sidebar.caption("Plan: Gratuit (2+ req/sec)")
    elif PAPPERS_DELAY >= 0.5:
        st.sidebar.caption("Plan: Starter (~2 req/sec)")
    else:
        st.sidebar.caption("Plan: Pro (~5 req/sec)")
    
    if has_scraping:
        st.sidebar.info("🔄 Scraping activé en fallback")
else:
    st.sidebar.warning("⚠️ Mode Scraping uniquement")
    st.sidebar.info(f"⏱️ Délais aléatoires: {SCRAPING_MIN_DELAY}-{SCRAPING_MAX_DELAY}s")
    st.sidebar.caption("Aucune clé API configurée")

# Instructions
st.markdown("---")
st.subheader("📤 Import du fichier")
st.markdown("""
**Fichier attendu:** Export Excel/CSV de l'API publique avec au minimum:
- Une colonne **SIREN** (9 chiffres)
- Optionnel: autres données déjà récupérées

**Workflow recommandé:**
1. Utilisez d'abord `app.py` pour obtenir les données de l'API publique (gratuit)
2. Exportez le fichier Excel
3. Importez-le ici pour l'enrichir avec Pappers (payant mais complet)
""")

uploaded_file = st.file_uploader(
    "Choisissez le fichier à enrichir",
    type=['xlsx', 'csv'],
    help="Fichier Excel ou CSV contenant une colonne SIREN"
)

if uploaded_file:
    try:
        # Lecture du fichier
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
        
        st.success(f"✅ Fichier chargé: {len(df)} entreprises")
        
        # Vérifier la présence du SIREN
        siren_columns = [col for col in df.columns if 'SIREN' in col.upper()]
        
        if not siren_columns:
            st.error("❌ Aucune colonne SIREN trouvée dans le fichier")
            st.info("Colonnes disponibles: " + ", ".join(df.columns))
            st.stop()
        
        siren_column = st.selectbox(
            "Sélectionnez la colonne SIREN",
            siren_columns,
            index=0
        )
        
        # Aperçu des données
        with st.expander("👁️ Aperçu des données", expanded=False):
            st.dataframe(df.head(10))
        
        # Statistiques
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Entreprises", len(df))
        with col2:
            valid_sirens = df[siren_column].dropna().astype(str).str.match(r'^\d{9}$').sum()
            st.metric("SIREN valides", valid_sirens)
        with col3:
            # Calcul du temps selon le mode
            if has_api:
                estimated_time = int(len(df) * PAPPERS_DELAY)
            else:
                # Moyenne des délais aléatoires
                avg_delay = (SCRAPING_MIN_DELAY + SCRAPING_MAX_DELAY) / 2
                estimated_time = int(len(df) * avg_delay)
            
            minutes = estimated_time // 60
            seconds = estimated_time % 60
            time_str = f"~{minutes}m{seconds}s" if minutes > 0 else f"~{seconds}s"
            st.metric("Temps estimé", time_str)
        
        # Bouton d'enrichissement
        st.markdown("---")
        
        if st.button("🚀 Lancer l'enrichissement Pappers", type="primary"):
            try:
                with st.spinner("🔄 Enrichissement en cours... Cela peut prendre plusieurs minutes."):
                    # Enrichissement
                    enriched_df = enrich_with_pappers(df, siren_column=siren_column)
                    
                    # Afficher les résultats
                    st.success("✅ Enrichissement terminé !")
                    
                    # Statistiques d'enrichissement
                    if 'Pappers_Annees_Disponibles' in enriched_df.columns:
                        has_data = enriched_df['Pappers_Annees_Disponibles'] > 0
                        success_count = has_data.sum()
                        success_rate = (success_count / len(enriched_df) * 100)
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Données trouvées", f"{success_count}/{len(enriched_df)}")
                        with col2:
                            st.metric("Taux de succès", f"{success_rate:.1f}%")
                        with col3:
                            avg_years = enriched_df[has_data]['Pappers_Annees_Disponibles'].mean()
                            st.metric("Années moyennes", f"{avg_years:.1f}")
                    
                    # Aperçu des résultats
                    st.subheader("📊 Résultats enrichis")
                    st.dataframe(enriched_df)
                    
                    # Export
                    st.markdown("---")
                    st.subheader("💾 Export des résultats")
                    
                    # Générer le nom du fichier
                    original_name = uploaded_file.name.rsplit('.', 1)[0]
                    output_filename = f"{original_name}_enrichi_pappers.xlsx"
                    
                    # Créer le fichier Excel en mémoire
                    from io import BytesIO
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        enriched_df.to_excel(writer, index=False, sheet_name='Données enrichies')
                    
                    st.download_button(
                        label="📥 Télécharger le fichier enrichi",
                        data=output.getvalue(),
                        file_name=output_filename,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                    
                    st.success(f"✅ Export prêt: {output_filename}")
                    
            except Exception as e:
                st.error(f"❌ Erreur lors de l'enrichissement: {str(e)}")
                import traceback
                with st.expander("🔍 Détails de l'erreur"):
                    st.code(traceback.format_exc())
    
    except Exception as e:
        st.error(f"❌ Erreur lors de la lecture du fichier: {str(e)}")

# Footer
st.markdown("---")
st.caption("""
💡 **Astuce:** Pour optimiser les coûts, utilisez d'abord l'API publique gratuite (`app.py`), 
puis enrichissez uniquement les entreprises qui vous intéressent avec Pappers.

📖 Documentation Pappers: [pappers.fr/api/documentation](https://www.pappers.fr/api/documentation)
""")
