"""
Configuration pour le Dashboard Emergency Management
"""

# ========== SERVEUR MCP ==========
MCP_BASE_URL = "http://localhost:8000"
REQUEST_TIMEOUT = 5  # secondes

# ========== SIMULATION ==========
DEFAULT_SIMULATION_SPEED = 1.0  # secondes par minute simulée
AUTO_REFRESH_INTERVAL = 5  # secondes (quand simulation désactivée)
MAX_EVENTS_LOG = 30  # nombre d'événements à afficher
MAX_METRICS_HISTORY = 100  # nombre de points dans l'historique

# ========== VISUALISATION ==========
GRAVITE_COLORS = {
    "ROUGE": "#ff6b6b",
    "JAUNE": "#ffd93d",
    "VERT": "#51cf66",
    "GRIS": "#adb5bd"
}

GRAVITE_EMOJIS = {
    "ROUGE": "🔴",
    "JAUNE": "🟡",
    "VERT": "🟢",
    "GRIS": "⚪"
}

STATUS_COLORS = {
    "disponible": "green",
    "occupe": "red",
    "transport": "orange"
}

# Seuils de saturation
SATURATION_NORMAL = 60  # %
SATURATION_WARNING = 80  # %

# ========== DONNÉES DE TEST ==========

PRENOMS_TEST = [
    "Sophie", "Lucas", "Emma", "Thomas", "Léa", "Hugo", 
    "Chloé", "Nathan", "Camille", "Alexandre", "Marie", 
    "Pierre", "Julie", "Antoine", "Manon", "Nicolas"
]

NOMS_TEST = [
    "Martin", "Bernard", "Dubois", "Thomas", "Robert", 
    "Petit", "Richard", "Durand", "Leroy", "Moreau",
    "Simon", "Laurent", "Lefebvre", "Michel", "Garcia"
]

SYMPTOMES_PAR_GRAVITE = {
    "ROUGE": [
        "Douleur thoracique intense avec irradiation",
        "AVC suspecté - troubles de la parole et motricité",
        "Détresse respiratoire sévère - saturation < 90%",
        "Traumatisme crânien grave avec perte de conscience",
        "Hémorragie importante non contrôlée",
        "Arrêt cardiaque récupéré",
        "Sepsis sévère avec choc septique",
        "Polytraumatisé - accident de la route"
    ],
    "JAUNE": [
        "Fracture du bras avec déformation visible",
        "Forte fièvre (40°C) avec confusion",
        "Plaie profonde au mollet nécessitant sutures",
        "Entorse sévère de la cheville avec œdème",
        "Douleurs abdominales intenses depuis 6h",
        "Crise d'asthme modérée",
        "Vertiges et vomissements répétés",
        "Luxation de l'épaule"
    ],
    "VERT": [
        "Migraine persistante depuis 2 jours",
        "Petite plaie à la main à désinfecter",
        "Légère foulure du poignet",
        "Rhume avec toux grasse",
        "Mal de dos modéré lombaire",
        "Réaction allergique cutanée légère",
        "Entorse bénigne de la cheville",
        "Brûlure superficielle du 1er degré"
    ],
    "GRIS": [
        "Renouvellement ordonnance - pas urgent",
        "Question administrative sur un certificat médical",
        "Mal de gorge léger depuis hier",
        "Certificat d'aptitude au sport"
    ]
}

ANTECEDENTS_POSSIBLES = [
    "Diabète type 2",
    "Hypertension artérielle",
    "Asthme",
    "Allergie pénicilline",
    "Insuffisance cardiaque",
    "BPCO",
    "Épilepsie",
    "Aucun antécédent"
]

# ========== SCÉNARIOS PRÉDÉFINIS ==========

SCENARIO_AFFLUX = {
    "nom": "Afflux massif",
    "description": "Simulation d'un afflux important (15 patients)",
    "patients": [
        {"count": 3, "gravite": "ROUGE"},
        {"count": 5, "gravite": "JAUNE"},
        {"count": 7, "gravite": "VERT"}
    ]
}

SCENARIO_ROUGE_URGENCE = {
    "nom": "Urgences vitales multiples",
    "description": "5 patients ROUGE en même temps",
    "patients": [
        {"count": 5, "gravite": "ROUGE"}
    ]
}

SCENARIO_FILE_ATTENTE = {
    "nom": "Longue file d'attente",
    "description": "Beaucoup de patients VERT et JAUNE",
    "patients": [
        {"count": 2, "gravite": "JAUNE"},
        {"count": 10, "gravite": "VERT"}
    ]
}

# ========== RÈGLES MÉDICALES ==========

REGLES_PRIORITE = {
    "ROUGE": {
        "priorite": 0,
        "description": "Vital + urgent - Traitement immédiat",
        "delai_max": 0  # minutes
    },
    "JAUNE": {
        "priorite": 2,
        "description": "Non vital mais urgent",
        "delai_max": 60  # minutes
    },
    "VERT": {
        "priorite": 3,
        "description": "Non vital, non urgent",
        "delai_max": 360  # minutes
    },
    "VERT_EXCEPTION": {
        "priorite": 1,
        "description": "VERT > 360 min passe avant JAUNE",
        "delai_min": 360  # minutes
    },
    "GRIS": {
        "priorite": 4,
        "description": "Ne nécessite pas les urgences",
        "delai_max": None
    }
}

# ========== CONTRAINTES PERSONNEL ==========

CONTRAINTES_PERSONNEL = {
    "medecin": {
        "fixe": True,
        "localisation": "consultation",
        "peut_bouger": False
    },
    "infirmiere_fixe": {
        "fixe": True,
        "localisation": "triage",
        "peut_bouger": False
    },
    "infirmiere_mobile": {
        "fixe": False,
        "role": "surveillance",
        "temps_min_poste": 15  # minutes
    },
    "aide_soignant": {
        "fixe": False,
        "role": "transport",
        "temps_max_absence": 60  # minutes
    }
}

# ========== CAPACITÉS ==========

CAPACITES_SALLES = {
    "salle_attente_1": 5,
    "salle_attente_2": 10,
    "salle_attente_3": 5
}

CAPACITES_UNITES = {
    "Soins Critiques": 5,
    "Cardiologie": 10,
    "Pneumologie": 5,
    "Neurologie": 8,
    "Orthopédie": 7
}

# ========== ALERTES ==========

SEUILS_ALERTES = {
    "surveillance_max_minutes": 15,  # salle sans surveillance
    "attente_longue_rouge": 15,  # minutes
    "attente_longue_jaune": 60,  # minutes
    "attente_longue_vert": 360,  # minutes
    "saturation_critique": 90,  # %
}

# ========== GRAPHIQUES ==========

GRAPH_CONFIG = {
    "height": 350,
    "template": "plotly_white",
    "line_width": 3,
    "marker_size": 8,
    "colors": {
        "saturation": "#ff6b6b",
        "attente": "#4dabf7",
        "total": "#51cf66"
    }
}

# ========== MESSAGES ==========

MESSAGES = {
    "serveur_offline": "⚠️ Le serveur MCP semble hors ligne. Vérifiez que server.py est lancé.",
    "simulation_start": "🎬 Simulation démarrée",
    "simulation_pause": "⏸️ Simulation en pause",
    "simulation_reset": "🔄 Système réinitialisé",
    "patient_added": "✅ Patient ajouté avec succès",
    "error_generic": "❌ Une erreur s'est produite",
    "no_alerts": "✅ Aucune alerte active",
    "no_patients": "ℹ️ Aucun patient dans le système",
    "no_queue": "✅ Aucun patient en attente de consultation"
}

# ========== API ENDPOINTS ==========

API_ENDPOINTS = {
    "health": "/",
    "etat_systeme": "/tools/get_etat_systeme",
    "alertes": "/tools/get_alertes",
    "ajouter_patient": "/tools/ajouter_patient",
    "assigner_salle": "/tools/assigner_salle_attente",
    "assigner_surveillance": "/tools/assigner_surveillance",
    "transport_consultation": "/tools/demarrer_transport_consultation",
    "terminer_consultation": "/tools/terminer_consultation",
    "transport_unite": "/tools/demarrer_transport_unite",
    "prochain_patient": "/tools/get_prochain_patient_consultation",
    "prochain_transport": "/tools/get_prochain_patient_transport",
    "reset": "/admin/reset"
}