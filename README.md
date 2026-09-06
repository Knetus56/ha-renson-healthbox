<p align="center"><img src="icon.png" width="96" alt="Renson logo"></p>

# Renson Healthbox - Intégration Home Assistant

[![Validate](https://github.com/Knetus56/ha-renson-healthbox/actions/workflows/validate.yml/badge.svg)](https://github.com/Knetus56/ha-renson-healthbox/actions/workflows/validate.yml)

Une intégration [Home Assistant](https://www.home-assistant.io/) pour monitorer et piloter votre **Renson Healthbox 3** en local via son API HTTP, sans passer par le cloud Renson.

Réécriture complète de [rmassch/healthbox-hacs](https://github.com/rmassch/healthbox-hacs) (voir [Remerciements](#-remerciements)), corrigeant plusieurs bugs de l'original et modernisant le code selon les standards Home Assistant actuels.

## 🌟 Fonctionnalités

- 📊 **Monitoring temps réel** : qualité d'air, température, humidité, CO2, COV, débit de ventilation, pièce par pièce
- 🌀 **Contrôle du boost** : un `switch` par pièce pour démarrer/arrêter le boost, avec niveau et durée réglables
- 🎛️ **Changement de profil** : `select` par pièce (Eco / Health / Intense), modifiable directement depuis le tableau de bord
- 🏠 **Multi-pièces** : chaque pièce Healthbox devient un device HA à part entière, rattaché au hub
- 🔍 **Détection automatique des capteurs** : CO2, COV, etc. n'apparaissent que si le module est réellement installé dans la pièce - et sont ajoutés à la volée s'ils apparaissent plus tard
- 🔐 **Connexion locale** : aucune donnée ne transite par un cloud
- 🔑 **Clé API obligatoire** : nécessaire dès la configuration pour débloquer les capteurs par pièce (température, humidité, CO2, COV, qualité de l'air, boost, profil) - sans elle, l'intégration n'apporte quasiment rien d'utile
- ⚙️ **Modifiable après coup** : changez la clé API ou l'intervalle de scan sans recréer l'intégration
- 🩺 **Diagnostics intégrés** et **logs de debug** détaillés pour faciliter le signalement de bugs
- 🇫🇷 **Interface localisée** : français et anglais (l'écran de configuration s'affiche dans la langue de Home Assistant)

## 📋 Capteurs (Sensors)

### Capteurs du hub (Healthbox)

| Capteur | Description | Unité |
|---|---|---|
| `global_air_quality_index` | Qualité d'air globale | - |
| `error_count` | Nombre d'erreurs signalées par l'appareil | - |
| `fan_voltage` | Tension du ventilateur | V |
| `fan_pressure` | Pression du ventilateur | Pa |
| `fan_flow` | Débit du ventilateur | m³/h |
| `fan_power` | Puissance du ventilateur | W |
| `fan_rpm` | Vitesse du ventilateur | tr/min |
| `wifi_status` *(diagnostic)* | État de la connexion Wi-Fi | - |
| `wifi_internet_connection` *(diagnostic)* | Accès internet via le Wi-Fi | - |
| `wifi_ssid` *(diagnostic)* | Nom du réseau Wi-Fi | - |

### Capteurs par pièce (nécessitent la clé API)

| Capteur | Description | Unité |
|---|---|---|
| `temperature` | Température intérieure | °C |
| `humidity` | Humidité relative | % |
| `co2_concentration` | Concentration en CO2 *(si module installé)* | ppm |
| `volatile_organic_compounds` | Composés organiques volatils *(si module installé)* | ppm |
| `air_quality_index` | Qualité d'air de la pièce | - |
| `airflow_ventilation_rate` | Débit de ventilation | % |
| `boost_level` | Niveau du boost en cours | % |
| `boost_remaining` | Temps restant du boost en cours | s |

## 🔌 Entités de contrôle

| Entité | Domaine | Description |
|---|---|---|
| `select.healthbox_<pièce>_profile` | `select` | Profil de ventilation : Eco / Health / Intense |
| `switch.healthbox_<pièce>_boost` | `switch` | Démarre/arrête le boost ; reflète l'état réel de l'appareil (repasse tout seul à `off` à la fin du délai) |
| `number.healthbox_<pièce>_boost_level` | `number` | Niveau (%) à utiliser au prochain démarrage du boost |
| `number.healthbox_<pièce>_boost_timeout` | `number` | Durée (minutes) à utiliser au prochain démarrage du boost |

## 🔄 Services

- `healthbox.start_room_boost` - démarre le boost d'une pièce (niveau %, durée en minutes)
- `healthbox.stop_room_boost` - arrête le boost d'une pièce
- `healthbox.change_room_profile` - change le profil d'une pièce (Eco/Health/Intense)

Les trois ciblent un device **Healthbox Room**. Ils font exactement la même chose que le switch/select ci-dessus - utiles pour les automatisations qui préfèrent appeler un service plutôt que manipuler une entité.

```yaml
service: healthbox.start_room_boost
target:
  device_id: <device_id de la pièce>
data:
  boost_level: 150
  boost_timeout: 30
```

## 🚀 Installation

### Prérequis

- Home Assistant 2024.8+
- Accès réseau à la Healthbox
- Adresse IP de la Healthbox et sa **clé API** (obligatoire - visible dans l'interface web de l'appareil)

### Via HACS (dépôt personnalisé)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Knetus56&repository=ha-renson-healthbox&category=integration)

Ou manuellement :
1. **HACS** > **Intégrations** > menu **⋯** > **Dépôts personnalisés**
2. Ajouter l'URL `https://github.com/Knetus56/ha-renson-healthbox`, catégorie **Intégration**
3. Chercher et installer **Renson Healthbox**
4. Redémarrer Home Assistant

*(Pas encore soumis au store officiel HACS.)*

### Installation manuelle

1. Copier `custom_components/healthbox` dans le dossier `custom_components` de votre configuration Home Assistant
2. Redémarrer Home Assistant

## ⚙️ Configuration

### Ajout initial

1. **Paramètres** > **Appareils et services** > **Ajouter une intégration**
2. Chercher **Renson Healthbox**
3. Renseigner :
   - **Adresse IP** : obligatoire
   - **Clé API** : **obligatoire** - sans elle, l'intégration ne donne accès qu'à une poignée de capteurs globaux ; elle débloque les capteurs par pièce (température, humidité, CO2, COV, qualité d'air, boost, profil)

### Modifier la configuration après installation

1. **Paramètres** > **Appareils et services** > carte **Renson Healthbox** > **Configurer**
2. Mettre à jour la **clé API** et/ou l'**intervalle de scan**
3. Valider - l'intégration se recharge automatiquement

## 🔧 Configuration avancée

### Intervalle de scan

Par défaut, l'intégration interroge la Healthbox toutes les **30 secondes**. Réglable de 10 à 3600 secondes depuis l'écran **Configurer**.

### Capteurs qui n'apparaissent pas

Les capteurs par pièce dépendent des modules physiquement installés (ex. une pièce peut avoir un capteur CO2, une autre un capteur COV, une troisième ni l'un ni l'autre) et de la présence de la clé API. Un capteur qui devient disponible plus tard (clé API ajoutée, module détecté) est ajouté automatiquement au prochain cycle de scan, sans redémarrage ni reconfiguration.

## 🐛 Signaler un bug

Merci de joindre à toute issue :

1. **Les logs de debug** : **Paramètres** > **Appareils et services** > **Renson Healthbox** > menu **⋯** de l'appareil > **Activer la consignation du débogage**. Reproduire le problème, puis **Désactiver la consignation du débogage** depuis le même menu pour télécharger le fichier. Équivalent en YAML :
   ```yaml
   logger:
     logs:
       custom_components.healthbox: debug
       pyhealthbox3: debug
   ```
2. **Les diagnostics** : **Paramètres** > **Appareils et services** > **Renson Healthbox** > **⋯** > **Télécharger les diagnostics** (la clé API est automatiquement masquée).

Puis ouvrir une issue sur [Knetus56/ha-renson-healthbox/issues](https://github.com/Knetus56/ha-renson-healthbox/issues).

## 📦 Versions

- **1.1.0** (2026-09-06) - `select` pour le profil de pièce, `switch` + `number` pour piloter le boost (niveau/durée réglables, persistés entre redémarrages), logs de debug détaillés, capteurs arrondis à l'entier (température gardée à 1 décimale), traduction française.
- **1.0.0** (2026-09-06) - Réécriture complète : flow d'options qui valide réellement la clé API, services qui survivent au déchargement d'une autre Healthbox, capteurs résilients à une valeur manquante, `diagnostics.py`, icône de marque embarquée, entity_id namespacés, unités à jour (`UnitOfRatio`).

## 🙏 Remerciements

- [rmassch](https://github.com/rmassch/healthbox-hacs) pour l'intégration d'origine
- L'auteur de [pyhealthbox3](https://pypi.org/project/pyhealthbox3/), la librairie cliente utilisée telle quelle par cette intégration
