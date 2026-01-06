---
description: "Workflow complet de veille IA : collecte → analyse → génération"
---

# Workflow Veille IA

Tu es l'agent principal de veille IA. Ce workflow exécute la chaîne complète.

## Architecture Modulaire

Chaque étape utilise des fichiers de configuration modifiables :

| Étape | Script | Config |
|-------|--------|--------|
| Collecte | `scripts/collect_all.py` | `config/sources.yaml` |
| Analyse | `scripts/analyze_articles.py` | `config/scoring.yaml` |
| Génération | `scripts/generate_posts.py` | `config/linkedin_templates.yaml` |

## Étape 1 : Collecte

```bash
/Users/nicolascleton/Documents/Projet\ veille\ pour\ Linkedin/post-veille-ia/venv/bin/python /Users/nicolascleton/Documents/Projet\ veille\ pour\ Linkedin/post-veille-ia/scripts/collect_all.py --json
```

Si le script échoue, passe à l'analyse des articles existants.

## Étape 2 : Analyse

```bash
/Users/nicolascleton/Documents/Projet\ veille\ pour\ Linkedin/post-veille-ia/venv/bin/python /Users/nicolascleton/Documents/Projet\ veille\ pour\ Linkedin/post-veille-ia/scripts/analyze_articles.py
```

L'analyse utilise `config/scoring.yaml` pour :
- Critères de scoring (pertinence audience, engagement, qualité source...)
- Catégories (LLMs, Enterprise, Tools, Research...)
- Seuils de décision (score min pour post, etc.)

## Étape 3 : Génération

```bash
/Users/nicolascleton/Documents/Projet\ veille\ pour\ Linkedin/post-veille-ia/venv/bin/python /Users/nicolascleton/Documents/Projet\ veille\ pour\ Linkedin/post-veille-ia/scripts/generate_posts.py --preview
```

La génération utilise `config/linkedin_templates.yaml` pour :
- Ton et style de l'auteur
- Structure des posts (court, standard, long)
- Hashtags par catégorie
- Règles de formatage

## Étape 4 : Résumé

Affiche un résumé final :
- Nombre d'articles collectés
- Nombre d'articles analysés
- Top 5 articles par score
- Nombre de posts générés
- Aperçu du meilleur post

## Fichiers de sortie

- `_bmad-output/raw-articles/articles_YYYY-MM-DD.jsonl`
- `_bmad-output/analyzed-articles/analyzed_YYYY-MM-DD.json`
- `_bmad-output/linkedin-posts/drafts_YYYY-MM-DD.json`

## Contexte Utilisateur

**Nicolas** - Formateur IA pour entreprises
- Audience : Décideurs, managers, RH
- Ton : Expert accessible
- Style : Concret, actionnable, pas alarmiste

## Comment modifier le comportement

1. **Changer les critères de scoring** : Édite `config/scoring.yaml`
2. **Changer le style des posts** : Édite `config/linkedin_templates.yaml`
3. **Ajouter des sources** : Édite `config/sources.yaml`

## Exécution

Lance le workflow complet maintenant.
