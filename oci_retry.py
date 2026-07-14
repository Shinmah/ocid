"""
Script de retry pour créer une instance OCI Always Free (A1.Flex ou E2.1.Micro)
quand Oracle renvoie "Out of capacity".

Deux modes de config :
  - LOCAL : utilise ton fichier ~/.oci/config classique (généré par `oci setup config`)
  - CI (GitHub Actions) : utilise des variables d'environnement (secrets)

Installation locale :
    pip install oci

Usage local :
    python oci_retry.py
"""

import os
import sys
import time
import base64
import datetime

import oci


# ---------------------------------------------------------------------------
# CONFIGURATION - à adapter (ou à passer via variables d'environnement)
# ---------------------------------------------------------------------------
CONFIG = {
    "compartment_id": os.environ.get("OCI_COMPARTMENT_ID", "ocid1.compartment.oc1..REMPLACE_MOI"),
    "availability_domain": os.environ.get("OCI_AD", "xxxx:EU-PARIS-1-AD-1"),
    "shape": os.environ.get("OCI_SHAPE", "VM.Standard.A1.Flex"),
    "ocpus": float(os.environ.get("OCI_OCPUS", "4")),
    "memory_in_gbs": float(os.environ.get("OCI_MEMORY", "24")),
    "subnet_id": os.environ.get("OCI_SUBNET_ID", "ocid1.subnet.oc1..REMPLACE_MOI"),
    "image_id": os.environ.get("OCI_IMAGE_ID", "ocid1.image.oc1..REMPLACE_MOI"),
    "ssh_public_key_path": os.environ.get("OCI_SSH_KEY_PATH", os.path.expanduser("~/.ssh/id_rsa.pub")),
    "display_name": os.environ.get("OCI_DISPLAY_NAME", "free-tier-instance"),
    "boot_volume_size_gb": int(os.environ.get("OCI_BOOT_VOLUME_GB", "50")),
}

RETRY_INTERVAL_SECONDS = int(os.environ.get("RETRY_INTERVAL", "60"))
MAX_ATTEMPTS = int(os.environ.get("MAX_ATTEMPTS", "0"))  # 0 = illimité


def load_oci_config():
    """Charge la config OCI soit depuis ~/.oci/config (local), soit depuis
    des variables d'environnement (CI / GitHub Actions).

    La clé privée peut être fournie de deux façons via OCI_CLI_KEY_CONTENT :
      - en clair (contenu brut du .pem, avec les lignes BEGIN/END)
      - en base64 (recommandé : évite les soucis de retours à la ligne
        corrompus lors du copier-coller dans un secret GitHub)
    """
    raw_key = os.environ.get("OCI_CLI_KEY_CONTENT")
    if raw_key:
        key_content = raw_key.strip()
        if "BEGIN" not in key_content:
            # Pas de header PEM visible -> on suppose que c'est du base64
            try:
                key_content = base64.b64decode(key_content).decode("utf-8")
            except Exception as e:
                print(f"Impossible de décoder OCI_CLI_KEY_CONTENT en base64 : {e}")
                sys.exit(1)

        # Gère le cas où le \n a été collé comme texte littéral au lieu
        # d'un vrai retour à la ligne (fréquent avec certains copier-coller)
        if "\\n" in key_content and "\n" not in key_content.strip("\\n"):
            key_content = key_content.replace("\\n", "\n")

        # Diagnostic SANS exposer la clé : juste sa "forme"
        num_lines = key_content.count("\n") + 1
        starts_ok = key_content.strip().startswith("-----BEGIN")
        ends_ok = key_content.strip().endswith("-----END PRIVATE KEY-----") or key_content.strip().endswith("-----END RSA PRIVATE KEY-----")
        print(f"[diag] longueur={len(key_content)} lignes={num_lines} header_ok={starts_ok} footer_ok={ends_ok}")
        if num_lines < 3:
            print("[diag] ATTENTION : le PEM tient sur une seule ligne (pas de vrais retours à la ligne).")
            print("[diag] C'est très probablement la cause de l'erreur. Il faut réencoder proprement en base64.")

        config = {
            "user": os.environ["OCI_USER_OCID"],
            "key_content": key_content,
            "fingerprint": os.environ["OCI_FINGERPRINT"],
            "tenancy": os.environ["OCI_TENANCY_OCID"],
            "region": os.environ["OCI_REGION"],
        }
        oci.config.validate_config(config)
        return config
    return oci.config.from_file()  # utilise ~/.oci/config par défaut


def launch_attempt(compute_client):
    with open(CONFIG["ssh_public_key_path"]) as f:
        ssh_key = f.read()

    details = oci.core.models.LaunchInstanceDetails(
        compartment_id=CONFIG["compartment_id"],
        availability_domain=CONFIG["availability_domain"],
        shape=CONFIG["shape"],
        display_name=CONFIG["display_name"],
        shape_config=oci.core.models.LaunchInstanceShapeConfigDetails(
            ocpus=CONFIG["ocpus"],
            memory_in_gbs=CONFIG["memory_in_gbs"],
        ),
        create_vnic_details=oci.core.models.CreateVnicDetails(
            subnet_id=CONFIG["subnet_id"],
            assign_public_ip=True,
        ),
        source_details=oci.core.models.InstanceSourceViaImageDetails(
            image_id=CONFIG["image_id"],
            boot_volume_size_in_gbs=CONFIG["boot_volume_size_gb"],
        ),
        metadata={"ssh_authorized_keys": ssh_key},
    )
    return compute_client.launch_instance(details)


def main():
    config = load_oci_config()
    compute_client = oci.core.ComputeClient(config)

    attempt = 0
    while MAX_ATTEMPTS == 0 or attempt < MAX_ATTEMPTS:
        attempt += 1
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            print(f"[{now}] Tentative #{attempt}... (shape={CONFIG['shape']}, ocpus={CONFIG['ocpus']}, memory_gb={CONFIG['memory_in_gbs']})")
            response = launch_attempt(compute_client)
            print(f"[{now}] Instance créée avec succès ! OCID : {response.data.id}")
            print("Va sur la console OCI (Compute > Instances) pour récupérer l'IP publique.")
            sys.exit(0)
        except oci.exceptions.ServiceError as e:
            msg = str(e.message or "")
            if "OutOfCapacity" in str(e.code) or "Out of capacity" in msg or "capacity" in msg.lower():
                print(f"[{now}] Out of capacity, nouvelle tentative dans {RETRY_INTERVAL_SECONDS}s.")
            else:
                print(f"[{now}] Erreur inattendue : {e.code} - {e.message}")
                if e.status in (400, 404):
                    print("Ça ressemble à une erreur de configuration (mauvais OCID, etc.). Arrêt du script.")
                    sys.exit(1)
        time.sleep(RETRY_INTERVAL_SECONDS)

    print("Nombre maximum de tentatives atteint sans succès. Relance plus tard.")


if __name__ == "__main__":
    main()
