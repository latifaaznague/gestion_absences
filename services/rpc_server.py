from jsonrpcserver import method, serve
from db import execute_query

@method
def marquer_presence(etudiant_id: int, seance_id: int, statut: str):
    query = """
        INSERT INTO presence (etudiant_id, seance_id, statut, date_saisie)
        VALUES (%s, %s, %s, NOW())
        RETURNING id;
    """
    row = execute_query(query, (etudiant_id, seance_id, statut), fetch_one=True)
    return {"presence_id": row[0]}

@method
def get_presences(etudiant_id: int):
    query = "SELECT id, etudiant_id, seance_id, statut, date_saisie FROM presence WHERE etudiant_id = %s"
    rows = execute_query(query, (etudiant_id,), fetch_all=True)
    result = []
    for r in rows or []:
        result.append({
            "id": r[0],
            "etudiant_id": r[1],
            "seance_id": r[2],
            "statut": r[3],
            "date_saisie": str(r[4])
        })
    return result


@method
def valider_seance(seance_id: int, validation: bool):
    """
    Met à jour le champ 'valide' dans la table seance.
    """
    query = "UPDATE seance SET valide = %s WHERE id = %s RETURNING id;"
    row = execute_query(query, (validation, seance_id), fetch_one=True)
    if row is None:
        return {"status": "not_found", "seance_id": seance_id}
    return {"status": "ok", "seance_id": row[0], "validation": validation}

if __name__ == "__main__":
    print("Starting RPC Server...")
    serve()