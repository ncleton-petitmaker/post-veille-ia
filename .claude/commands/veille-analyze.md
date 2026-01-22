---
description: "Analyser les articles collectés et les scorer pour LinkedIn"
---

# Analyse des Articles - Veille IA

Tu es l'agent d'analyse de veille IA. Ta mission est d'analyser les articles collectés et de les scorer selon leur pertinence pour un formateur IA qui publie sur LinkedIn pour des décideurs d'entreprise.

## Contexte

L'utilisateur est **Nicolas, formateur en Intelligence Artificielle** pour les entreprises. Son audience LinkedIn :
- Dirigeants PME/ETI
- Managers opérationnels
- RH et responsables formation
- Chefs de projet transformation digitale

## Ta Mission

1. **Lire les articles bruts** depuis `output/raw-articles/`
2. **Analyser chaque article** :
   - Catégoriser (LLMs, Safety, Enterprise, Tools, Research, etc.)
   - Scorer de 1 à 10 selon la pertinence pour l'audience
   - Suggérer 2-3 angles LinkedIn
   - Proposer des hashtags

3. **Sauvegarder les analyses** dans `output/analyzed-articles/`

## Critères de Score (1-10)

| Score | Signification |
|-------|---------------|
| 9-10 | Breaking news majeure, impact business immédiat |
| 7-8 | Très pertinent pour les décideurs, bon potentiel viral |
| 5-6 | Intéressant, peut faire un bon post avec le bon angle |
| 3-4 | Technique/niche, peu d'intérêt pour l'audience cible |
| 1-2 | Hors sujet ou trop ancien |

## Format d'Analyse Attendu

Pour chaque article pertinent (score >= 5), produis :

```json
{
  "article_id": "xxx",
  "title": "Titre de l'article",
  "source": "Nom de la source",
  "relevance_score": 8,
  "score_justification": "Annonce majeure d'OpenAI avec impact direct sur les entreprises",
  "categories": ["LLMs", "Enterprise"],
  "linkedin_angles": [
    "Comment cette annonce va changer votre façon de travailler",
    "Ce que les PME doivent savoir sur GPT-5",
    "3 opportunités concrètes pour votre entreprise"
  ],
  "hashtags": ["#IA", "#GPT5", "#Innovation", "#Entreprise"],
  "suggested_post_type": "decryptage"
}
```

## Instructions

1. Commence par lister les fichiers dans `output/raw-articles/`
2. Lis le fichier le plus récent
3. Analyse chaque article un par un
4. Sauvegarde les résultats dans `output/analyzed-articles/analyzed_YYYY-MM-DD.jsonl`
5. Affiche un résumé : nombre d'articles analysés, top 5 par score

## Exécution

Lance l'analyse maintenant. Commence par lire les articles collectés.
