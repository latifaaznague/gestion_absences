from .rpc_client import marquer_presence, get_presences, valider_seance

def marquer_presence_etudiant(etudiant_id, seance_id, statut):
    return marquer_presence(etudiant_id, seance_id, statut)

def liste_presences_etudiant(etudiant_id):
    return get_presences(etudiant_id)

def valider_seance_par_prof(seance_id, validation):
    return valider_seance(seance_id, validation)
