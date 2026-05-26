import os
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

# Configuration de la sécurité (À adapter ou sécuriser via des variables d'environnement)
SECRET_KEY = "CINEPOLY_SUPER_SECRET_KEY_DONT_SHARE"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# Contexte pour le hachage des mots de passe (Sécurisation des données SQL)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Modèles Pydantic pour l'authentification
class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None

# 1. Fonctions de Hachage pour le contrôleur Utilisateur (SQL)
def hacher_mot_de_passe(mot_de_passe: str) -> str:
    """Transforme le mot de passe clair en empreinte Bcrypt."""
    return pwd_context.hash(mot_de_passe)

def verifier_mot_de_passe(mot_de_passe_clair: str, mot_de_passe_hache: str) -> bool:
    """Vérifie si le mot de passe correspond à l'empreinte stockée."""
    return pwd_context.verify(mot_de_passe_clair, mot_de_passe_hache)

# 2. Génération du Token JWT lors de la connexion (Login)
def creer_token_acces(donnees: dict, duree_expiration: Optional[timedelta] = None) -> str:
    """Génère un JWT contenant l'identité et le rôle de l'utilisateur."""
    a_encoder = donnees.copy()
    if duree_expiration:
        expire = datetime.utcnow() + duree_expiration
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    a_encoder.update({"exp": expire})
    encoded_jwt = jwt.encode(a_encoder, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# 3. Middleware de vérification du Token et des Rôles (Sécurité des endpoints)
async def obtenir_utilisateur_actuel(token: str = Depends(oauth2_scheme)) -> TokenData:
    """Décode le token, vérifie sa validité et extrait les informations de rôle."""
    exception_authentification = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Impossible de valider les identifiants de connexion.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        if username is None or role is None:
            raise exception_authentification
        return TokenData(username=username, role=role)
    except JWTError:
        raise exception_authentification

def verifier_role_administrateur(utilisateur_actuel: TokenData = Depends(obtenir_utilisateur_actuel)):
    """Garantit que seul un administrateur peut accéder à une route (ex: Modération, CRUD)."""
    if utilisateur_actuel.role != "Administrateur":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès refusé : Vous devez être Administrateur pour effectuer cette action."
        )
    return utilisateur_actuel
