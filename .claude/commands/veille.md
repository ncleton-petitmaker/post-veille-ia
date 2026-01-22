---
description: "Workflow complet de veille IA : collecte → sélection → génération"
---

# Workflow Veille IA

Tu es l'agent principal de veille IA.

## Étape 1 : Collecte

```bash
/Users/nicolascleton/Documents/Projet\ veille\ pour\ Linkedin/post-veille-ia/venv/bin/python /Users/nicolascleton/Documents/Projet\ veille\ pour\ Linkedin/post-veille-ia/scripts/collect_all.py --json
```

## Étape 2 : Sélection des articles

### 2.1 Lis la consigne de l'utilisateur

**AVANT TOUTE CHOSE**, lis `config/content_preferences.json` et récupère le champ `news_focus`.

**AFFICHE CE TEXTE** pour confirmer que tu l'as bien lu.

**C'EST LA CONSIGNE DE L'UTILISATEUR. Tu dois :**
1. Comprendre ce qu'il recherche
2. Comprendre ce qu'il veut ÉVITER
3. Utiliser cette consigne pour CHAQUE décision de sélection et de rédaction

### 2.2 Lis les paramètres

Lis `config/scoring.yaml` → `thresholds.max_posts_per_day` = nombre d'articles à retenir.

### 2.3 Lis les articles DÉJÀ traités (à exclure)

Lis les fichiers `output/linkedin-posts/drafts_*.json` des jours précédents.
Extrais toutes les URLs des articles déjà utilisés pour générer des posts.
**Ces articles doivent être EXCLUS de la sélection.**

### 2.4 Lis tous les articles du jour

Lis `output/raw-articles/articles_YYYY-MM-DD.jsonl` (date du jour).
**Ignore les articles dont l'URL est déjà dans la liste des exclusions.**

### 2.5 Score et sélectionne

Pour chaque article NON exclu, calcule un score :

**Score de pertinence (1-10)** : L'article correspond-il à la consigne `news_focus` ?

**Bonus de récence** :
- Article de moins de 24h : +3 points
- Article de 24-48h : +2 points
- Article de 48-72h : +1 point
- Article de plus de 72h : +0 point

**Score final = pertinence + bonus récence**

Garde les `max_posts_per_day` articles avec les meilleurs scores finaux.

**LISTE les articles sélectionnés avec leur score.**

## Étape 3 : Génération des posts

**IMPORTANT : Tu DOIS générer un post pour CHAQUE article sélectionné. Si tu as sélectionné 15 articles, tu génères 15 posts. PAS MOINS.**

Pour chaque article retenu :

1. **Lis le contenu** avec WebFetch sur l'URL de l'article
2. **Lis le style** dans `config/content_preferences.json` → `post_style`
3. **Oriente le contenu** selon le `news_focus` :
   - L'audience cible est définie dans le news_focus
   - Réponds aux questions que cette audience se pose
   - Évite les angles techniques si le news_focus le demande
4. **Génère 3 versions** en suivant EXACTEMENT le `post_style` :
   - court (100-150 mots)
   - standard (200-300 mots)
   - long (400-500 mots)
5. **Génère le visual_prompt** pour chaque post :
   - Lis le template dans `config/content_preferences.json` → `visual_prompt_template`
   - Crée un prompt UNIQUE et SPÉCIFIQUE au contenu du post
   - **TOUT TEXTE VISIBLE DOIT ÊTRE EN FRANÇAIS** (labels, mots-clés, chiffres avec unités françaises)
   - Ajoute toujours : "All text and labels must be in French"
   - 50-100 mots, décris une illustration abstraite capturant l'essence du post
   - Respecte le style et la palette du template

### Sauvegarde

**IMPORTANT** : Si le fichier `output/linkedin-posts/drafts_YYYY-MM-DD.json` existe déjà :
1. Lis les posts existants
2. **AJOUTE les nouveaux posts AU DÉBUT** de la liste (les plus récents en premier)
3. Ne supprime AUCUN post existant
4. Le total peut dépasser `max_posts_per_day` - c'est normal

Sauvegarde dans `output/linkedin-posts/drafts_YYYY-MM-DD.json` :

```json
{
  "date": "YYYY-MM-DD",
  "generated_at": "ISO timestamp",
  "total_generated": N,
  "posts": [
    // NOUVEAUX POSTS EN PREMIER
    {
      "title": "Résumé du hook en 5-7 mots max",
      "article_title": "Titre original de l'article",
      "article_url": "https://...",
      "article_source": "Source",
      "article_date": "YYYY-MM-DD",
      "score": 8.5,
      "visual_prompt": "Digital whiteboard illustration with sticky notes showing [CONCEPT EN FRANÇAIS]. All text and labels must be in French. Background #f9fafb, soft shadows. Square 1:1 for LinkedIn.",
      "versions": {
        "court": { "content": "..." },
        "standard": { "content": "..." },
        "long": { "content": "..." }
      }
    },
    // PUIS LES POSTS EXISTANTS
    ...
  ]
}
```

## Étape 4 : Vérification

**VÉRIFIE que tu as bien généré `max_posts_per_day` posts.**

Si tu en as généré moins, CONTINUE jusqu'à atteindre le nombre demandé.

## Étape 5 : Résumé

Affiche :
- Nombre d'articles collectés
- Nombre sélectionnés
- Nombre de posts générés (doit être = max_posts_per_day)
- Liste des posts avec titre et score

## Exécution

Lance maintenant. **Ne t'arrête pas avant d'avoir généré tous les posts.**
