from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List
from datetime import datetime
from sqlalchemy.orm import Session

# Importation des modules locaux
from .database import get_sql_db, get_nosql_db
from .auth import TokenData, obtenir_utilisateur_actuel, verifier_role_administrateur

app = FastAPI(
    title="CinéPoly API",
    description="API Backend avec Architecture Polyglotte (PostgreSQL & MongoDB) et Sécurisation par JWT",
    version="1.0.0"
)

# ==========================================
# 1. MODÈLES DE DONNÉES (Pydantic)
# ==========================================
class CritiqueCreate(BaseModel):
    film_id: int
    note: float
    titre_critique: str
    texte_critique: str
    tags: List[str]

# ==========================================
# 2. ENDPOINTS / ROUTES API
# ==========================================

@app.get("/")
def route_racine():
    """Route d'accueil pour vérifier le statut de l'API."""
    return {"statut": "API CinéPoly opérationnelle", "version": "1.0.0"}


@app.post("/films/critiques", status_code=status.HTTP_201_CREATED)
async def publier_critique(
    critique: CritiqueCreate, 
    sql_db: Session = Depends(get_sql_db),
    nosql_db = Depends(get_nosql_db),
    utilisateur_actuel: TokenData = Depends(obtenir_utilisateur_actuel)
):
    """
    Cas d'usage : Publier une critique sur un film (Architecture Hybride).
    - Sécurité : Exige un token JWT valide (Utilisateur connecté).
    - Validation SQL : Vérifie si le film existe dans la base relationnelle.
    - Stockage NoSQL : Insère la critique enrichie dans MongoDB.
    """
    
    # ÉTAPE A : Vérifier l'existence du film dans la base SQL (Intégrité Référentielle)
    requete_film = "SELECT id FROM Film WHERE id = :film_id"
    film_existe = sql_db.execute(requete_film, {"film_id": critique.film_id}).fetchone()
    
    if not film_existe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Action impossible : Le film avec l'ID {critique.film_id} n'existe pas dans la base SQL principale."
        )

    # ÉTAPE B : Structurer le document pour MongoDB (Modèle Documentaire flexible)
    nouvelle_critique = {
        "film_id": critique.film_id,
        "utilisateur_id": utilisateur_actuel.username,  # Extrait du Token JWT
        "pseudo_auteur": utilisateur_actuel.username,
        "note": critique.note,
        "titre_critique": critique.titre_critique,
        "texte_critique": critique.texte_critique,
        "tags": critique.tags,  # Tableau dynamique géré nativement par le NoSQL
        "date_publication": datetime.utcnow(),
        "commentaires": []  # Tableau imbriqué pour les futures réponses
    }
    
    # ÉTAPE C : Insertion dans la collection MongoDB
    resultat = nosql_db.critiques.insert_one(nouvelle_critique)
    
    return {
        "message": "Critique publiée avec succès dans la base NoSQL MongoDB !",
        "critique_id": str(resultat.inserted_id),
        "auteur": utilisateur_actuel.username
    }


@app.delete("/admin/critiques/{critique_id}", status_code=status.HTTP_200_OK)
async def moderer_critique(
    critique_id: str,
    nosql_db = Depends(get_nosql_db),
    admin_actuel: TokenData = Depends(verifier_role_administrateur)
):
    """
    Cas d'usage : Modération / Suppression d'une critique abusive.
    - Sécurité Strict : Seul l'acteur 'Administrateur' peut appeler cette route.
    - Action : Suppression directe dans MongoDB via l'identifiant unique.
    """
    from bson import ObjectId
    try:
        id_object = ObjectId(critique_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Format de l'identifiant critique_id non valide (doit être un ObjectId MongoDB)."
        )
        
    critique_supprimee = nosql_db.critiques.find_one_and_delete({"_id": id_object})
    
    if not critique_supprimee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La critique spécifiée n'existe pas dans la base de données."
        )
        
    return {
        "message": "Contenu modéré. La critique a été supprimée définitivement de MongoDB.",
        "modérateur": admin_actuel.username
    }
