import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pymongo import MongoClient

# ==========================================================
# 1. CONFIGURATION SQL (Pour les données structurées / ACID)
# ==========================================================
# À remplacer par vos identifiants réels en production
SQL_DATABASE_URL = "sqlite:///./cinepoly_relationnel.db" 
# Note : L'utilisation de SQLite en local facilite les tests sans installation lourde.

engine = create_engine(SQL_DATABASE_URL, connect_args={"check_sharing_thread": False} if "sqlite" in SQL_DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Dépendance pour obtenir la session SQL dans les routes API
def get_sql_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==========================================================
# 2. CONFIGURATION NOSQL (MongoDB - Pour la flexibilité des données)
# ==========================================================
# À remplacer par votre chaîne de connexion MongoDB Atlas si hébergé sur le Cloud
MONGO_URL = "mongodb://localhost:27017" 
mongo_client = MongoClient(MONGO_URL)
nosql_db = mongo_client["cinepoly_documentaire_db"]

# Dépendance pour obtenir la base NoSQL dans les routes API
def get_nosql_db():
    return nosql_db
