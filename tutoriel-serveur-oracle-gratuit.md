# Comment avoir un serveur gratuit à vie sur Oracle Cloud (même quand ça dit "plus de place")

## C'est quoi le problème qu'on résout ?

Oracle Cloud offre un petit serveur **gratuit à vie** (2 CPU, 12 Go de RAM), mais tellement de monde en veut un que quand tu essaies d'en créer un, ça répond presque toujours "pas de capacité disponible". La seule solution qui marche, c'est de laisser un robot réessayer à ta place, encore et encore, jusqu'à ce qu'une place se libère (souvent la nuit ou tôt le matin).

Ce tuto t'explique comment mettre en place ce robot, gratuitement, sans avoir besoin de garder ton ordinateur allumé.

**Temps nécessaire :** environ 30-45 minutes la première fois. Ensuite c'est automatique.

**Ce dont t'as besoin :** un compte email, c'est tout. On va créer tous les autres comptes ensemble.

---

## ⚠️ Une règle d'or à respecter tout du long

Tu vas manipuler des "clés" et des "tokens" (des sortes de mots de passe très longs et random). **Ne les partage JAMAIS avec personne, ne les mets JAMAIS dans un chat, un email, ou une capture d'écran que tu montres à quelqu'un** (même à un pote qui t'aide) — elles se collent uniquement dans les champs prévus pour, jamais ailleurs. Si jamais t'en montres une par erreur à quelqu'un, considère-la grillée et régénères-en une nouvelle immédiatement.

---

## Partie 1 — Créer ton compte Oracle Cloud

1. Va sur [oracle.com/cloud/free](https://www.oracle.com/cloud/free/) et clique sur "Start for free"
2. Remplis le formulaire (email, mot de passe, pays)
3. Choisis la région **France Central (Paris)** si tu veux un serveur en France (attention : ce choix est **définitif**, tu ne pourras plus en changer après)
4. Tu devras renseigner une carte bancaire pour vérification — **tu ne seras pas débité** tant que tu restes dans les limites "Always Free" (le serveur qu'on va créer est dedans)
5. Valide, attends que le compte soit activé (quelques minutes, parfois plus)

---

## Partie 2 — Récupérer tes informations OCI (les "identifiants")

Connecte-toi sur [cloud.oracle.com](https://cloud.oracle.com) avec ton nouveau compte. On va noter plusieurs informations au fur et à mesure — ouvre un fichier texte sur ton ordi (Bloc-notes / TextEdit) pour toutes les coller au propre.

### 2.1 — Le "Tenancy OCID" (= identifiant de ton compte)

1. En haut à droite, clique sur l'icône de ton profil
2. Clique sur **"Tenancy: [ton nom]"**
3. Tu vois un champ **OCID** avec un bouton **Copy** — clique dessus
4. Colle-le dans ton fichier texte, étiquette-le `TENANCY_OCID`

*(Ce même identifiant va aussi te servir de `COMPARTMENT_ID` — c'est normal, ne t'inquiète pas.)*

### 2.2 — Ton "User OCID"

1. Toujours dans le menu profil (icône en haut à droite), clique sur **"User Settings"**
2. En haut de la page, copie le champ **OCID**
3. Colle-le dans ton fichier, étiquette-le `USER_OCID`

### 2.3 — L'Availability Domain (l'"AD")

1. Menu ☰ (en haut à gauche) > **Compute** > **Instances**
2. Clique sur **Create Instance** (on ne va pas aller au bout, juste voir une info)
3. Dans la section "Placement", tu vois un nom du genre `xxxx:EU-PARIS-1-AD-1` — copie-le
4. Étiquette-le `AD`
5. Tu peux annuler la création (clique ailleurs ou ferme), on n'en a pas besoin maintenant

### 2.4 — Le Subnet (le "réseau")

1. Menu ☰ > **Networking** > **Virtual Cloud Networks**
2. Si tu vois déjà un réseau dans la liste, clique dessus, puis clique sur le nom du subnet à l'intérieur (ex: `subnet-xxxxx`)
3. Si tu ne vois **aucun** réseau : clique sur **Start VCN Wizard** > choisis "Create VCN with Internet Connectivity" > laisse les valeurs par défaut > **Create**. Une fois créé, retourne dans le VCN, clique sur le subnet à l'intérieur.
4. Sur la page du subnet, copie le champ **OCID**
5. Étiquette-le `SUBNET_ID`

### 2.5 — L'Image (le système d'exploitation)

1. Menu ☰ > **Compute** > **Instances** > **Create Instance**
2. Section "Image and shape" > clique **Edit**
3. Clique **Change Shape**
4. Choisis l'onglet **Ampere**, sélectionne **VM.Standard.A1.Flex**
5. Reviens dans la partie "Image", assure-toi que c'est **Ubuntu 22.04** qui est sélectionné
6. En dessous du nom de l'image, copie l'**OCID** affiché
7. Étiquette-le `IMAGE_ID`
8. Annule la création (on voulait juste cette info)

> ⚠️ Ce point est piégeur : si tu récupères l'OCID de l'image **sans** avoir d'abord choisi le shape Ampere, tu auras la mauvaise version (incompatible), et Oracle refusera de créer l'instance plus tard. Suis bien l'ordre ci-dessus.

### 2.6 — La clé API (attention, partie sensible)

1. Menu profil (icône en haut à droite) > **User Settings**
2. Dans le menu de gauche, clique **API Keys**
3. Clique **Add API Key**
4. Choisis **"Generate API Key Pair"**
5. Clique **Download Private Key** — un fichier `.pem` se télécharge sur ton ordi. **Ne le partage avec personne, jamais.**
6. Clique **Add**
7. Une fenêtre apparaît avec un bloc de texte contenant un `fingerprint` — copie cette valeur (juste la ligne `fingerprint=...`)
8. Étiquette-la `FINGERPRINT`

Le fichier `.pem` téléchargé, garde-le précieusement sur ton ordi (pas besoin de le partager, on va juste s'en servir dans quelques étapes).

---

## Partie 3 — Créer une clé SSH (pour te connecter à ton futur serveur)

Cette clé te servira plus tard à te connecter à ton serveur une fois créé.

**Sur Windows :**
1. Ouvre le "Terminal" (cherche-le dans le menu Démarrer)
2. Tape : `ssh-keygen -t ed25519 -C "mon-serveur-oracle"`
3. Appuie sur Entrée à chaque question (valeurs par défaut)

**Sur Mac/Linux :**
1. Ouvre le "Terminal"
2. Même commande : `ssh-keygen -t ed25519 -C "mon-serveur-oracle"`
3. Entrée à chaque question

Ça crée deux fichiers dans un dossier caché `.ssh` de ton dossier utilisateur :
- `id_ed25519` → la clé privée, **jamais à partager**
- `id_ed25519.pub` → la clé publique, celle-là tu vas t'en servir dans la partie suivante

Ouvre le fichier `id_ed25519.pub` avec un éditeur de texte (Bloc-notes), copie tout son contenu (une seule ligne commençant par `ssh-ed25519`), colle-le dans ton fichier texte récapitulatif, étiquette-le `SSH_PUBLIC_KEY`.

---

## Partie 4 — Créer ton compte GitHub et préparer le robot

GitHub va héberger et faire tourner gratuitement le "robot" qui réessaie de créer ton serveur.

### 4.1 — Créer le compte et le repo

1. Va sur [github.com](https://github.com), crée un compte si t'en as pas
2. Une fois connecté, clique sur le **+** en haut à droite > **New repository**
3. Donne-lui un nom (ex: `mon-serveur-oracle`)
4. Choisis **Public** (important : ça te donne un temps d'exécution illimité et gratuit, contrairement à "Private")
5. Clique **Create repository**

### 4.2 — Ajouter les deux fichiers du robot

Télécharge les deux fichiers `oci_retry.py` et `oci-retry.yml` fournis avec ce tutoriel.

**Pour `oci_retry.py` :**
1. Sur la page de ton repo, clique **Add file** > **Upload files**
2. Glisse le fichier `oci_retry.py`
3. Clique **Commit changes**

**Pour `oci-retry.yml` (attention, chemin spécial) :**
1. Clique **Add file** > **Create new file**
2. Dans le champ du nom en haut, tape exactement : `.github/workflows/oci-retry.yml`
3. Ouvre le fichier `oci-retry.yml` avec un éditeur de texte, copie tout son contenu, colle-le dans la zone de texte GitHub
4. Clique **Commit changes**

### 4.3 — Ajouter tes informations en secret

1. Sur la page du repo, clique **Settings** (onglet en haut)
2. Menu de gauche : **Secrets and variables** > **Actions**
3. Clique **New repository secret** pour chacune des lignes ci-dessous (nom exact à gauche, valeur à droite) :

| Nom du secret | Valeur à coller |
|---|---|
| `OCI_USER_OCID` | ton `USER_OCID` |
| `OCI_FINGERPRINT` | ton `FINGERPRINT` |
| `OCI_TENANCY_OCID` | ton `TENANCY_OCID` |
| `OCI_REGION` | `eu-paris-1` |
| `OCI_COMPARTMENT_ID` | même valeur que `TENANCY_OCID` |
| `OCI_AD` | ton `AD` |
| `OCI_SUBNET_ID` | ton `SUBNET_ID` |
| `OCI_IMAGE_ID` | ton `IMAGE_ID` |
| `SSH_PUBLIC_KEY` | ton `SSH_PUBLIC_KEY` |

**Pour le dernier secret `OCI_CLI_KEY_CONTENT`, une étape spéciale est nécessaire** (pour éviter un bug très fréquent) :

**Sur Windows (PowerShell) :**
```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes("C:\chemin\vers\ta_cle.pem"))
```

**Sur Mac/Linux (Terminal) :**
```bash
base64 -w 0 chemin/vers/ta_cle.pem
```

Ça affiche une longue chaîne de texte sur une seule ligne. Copie-la en entier, et mets-la comme valeur du secret `OCI_CLI_KEY_CONTENT`.

---

## Partie 5 — Tester une première fois

1. Sur ton repo GitHub, clique l'onglet **Actions**
2. Clique sur **"OCI Free Tier Retry"** dans la liste à gauche
3. Clique le bouton **Run workflow** > confirme
4. Attends 10-30 secondes, clique sur le run qui apparaît pour voir son statut
5. Regarde le résumé en haut de la page du run :
   - **✅ Instance créée avec succès** → 🎉 direction la Partie 7 pour te connecter à ton serveur
   - **⏳ Pas encore de capacité disponible** → c'est normal, c'est justement pour ça qu'on met en place le reste (Partie 6)
   - **Une erreur en rouge** → un des secrets est probablement mal rempli, relis les valeurs une par une

---

## Partie 6 — Faire réessayer le robot automatiquement

GitHub tout seul ne relance pas le robot assez souvent, donc on utilise un deuxième service gratuit qui va cliquer sur "Run workflow" à ta place toutes les X minutes.

### 6.1 — Créer un token GitHub (une clé d'accès limitée)

1. Sur GitHub, clique ton avatar (en haut à droite) > **Settings**
2. Menu de gauche, tout en bas : **Developer settings**
3. **Personal access tokens** > **Fine-grained tokens**
4. **Generate new token**
5. Donne-lui un nom (ex: "cron retry")
6. Section **Repository access** : choisis **"Only select repositories"**, sélectionne ton repo
7. Plus bas, section **Repository permissions** : trouve la ligne **"Actions"**, mets-la sur **"Read and write"**
8. Scroll tout en bas, clique **Generate token**
9. **Copie le token affiché immédiatement** (il ne sera plus jamais visible après). Ne le montre à personne.

### 6.2 — Créer le compte cron-job.org et configurer le déclenchement

1. Va sur [cron-job.org](https://cron-job.org), crée un compte gratuit
2. Une fois connecté, **Cronjobs** > **Create cronjob**
3. **URL**, remplace `TON_PSEUDO` et `TON_REPO` par les tiens :
   ```
   https://api.github.com/repos/TON_PSEUDO/TON_REPO/actions/workflows/oci-retry.yml/dispatches
   ```
4. **Méthode de requête** : POST
5. Section **En-têtes (Headers)**, ajoute ces 3 lignes :

   | Clé | Valeur |
   |---|---|
   | `Content-Type` | `application/json` |
   | `Authorization` | `Bearer TON_TOKEN` *(remplace TON_TOKEN par le token copié à l'étape 6.1, garde le mot "Bearer" suivi d'un espace)* |
   | `Accept` | `application/vnd.github+json` |

6. **Corps de la demande** :
   ```json
   {"ref":"main"}
   ```
7. Configure la fréquence à toutes les **15 minutes**
8. **Enregistre**

### 6.3 — Vérifier que ça tourne

Attends 15-20 minutes, puis retourne sur GitHub > ton repo > **Actions**. Tu dois voir un nouveau run apparaître tout seul, sans que t'aies rien cliqué. S'il continue d'apparaître régulièrement, c'est bon, tu peux fermer ton ordinateur — ça tourne sur les serveurs de GitHub et cron-job.org, pas chez toi.

---

## Partie 7 — Une fois que ça a réussi

1. **Désactive immédiatement le cronjob** sur cron-job.org (bouton pause/désactiver) — sinon le robot va continuer à essayer de créer un 2e serveur et ça va bloquer sur les limites
2. Va sur la console OCI > **Compute** > **Instances**, clique sur ton instance
3. Note son **adresse IP publique**
4. Connecte-toi en SSH depuis ton Terminal :
   ```bash
   ssh -i chemin/vers/id_ed25519 ubuntu@TON_IP_PUBLIQUE
   ```
   (remplace `ubuntu` par le nom d'utilisateur par défaut de l'image utilisée, et `TON_IP_PUBLIQUE` par l'IP notée)

Félicitations, t'as ton serveur gratuit à vie 🎉

---

## En cas de souci

Si une erreur apparaît dans les logs GitHub Actions que tu comprends pas, copie le message d'erreur complet (texte, pas juste une capture partielle) et montre-le à quelqu'un qui peut t'aider — mais **jamais tes secrets/clés/tokens**, uniquement les messages d'erreur.
