// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title AgricultureParametricInsurance
 * @author ECE Paris - Projet Blockchain MsC2 DEIA
 * @notice Smart contract d'assurance paramétrique agricole contre la sécheresse.
 *         L'indemnisation est déclenchée automatiquement si la pluviométrie
 *         annuelle fournie par un oracle descend sous le seuil trigger.
 *
 * @dev Architecture :
 *      - L'agriculteur souscrit et paie sa prime en ETH
 *      - Un oracle (Chainlink simulé ici) fournit les données météo
 *      - Si précipitations < TRIGGER → payout automatique
 *      - Inspiré de Fizzy by AXA (assurance retard vol, 2017-2019)
 *
 * Déploiement suggéré : Réseau Ethereum testnet (Sepolia)
 * IDE recommandé      : Remix (https://remix.ethereum.org)
 */

// ─── Interface Oracle ─────────────────────────────────────────────────────────
/**
 * @notice Interface que doit implémenter l'oracle météo.
 *         En production, utiliser Chainlink Data Feeds.
 */
interface IWeatherOracle {
    /**
     * @notice Retourne les précipitations annuelles en mm pour une région donnée.
     * @param regionId Identifiant de la région agricole
     * @return precipitation Précipitations annuelles en mm (entier)
     * @return timestamp Horodatage de la dernière mise à jour
     */
    function getPrecipitation(uint256 regionId)
        external
        view
        returns (uint256 precipitation, uint256 timestamp);
}

// ─── Contrat principal ────────────────────────────────────────────────────────
contract AgricultureParametricInsurance {

    // ── Structures de données ─────────────────────────────────────────────────

    /**
     * @notice Structure représentant une police d'assurance souscrite.
     */
    struct Policy {
        address payable insured;    // Adresse de l'assuré (agriculteur)
        uint256 regionId;           // Identifiant de la région (lié à l'oracle)
        uint256 premium;            // Prime payée en wei
        uint256 coverageAmount;     // Montant de l'indemnisation en wei
        uint256 triggerMm;          // Seuil de déclenchement en mm
        uint256 startDate;          // Date de souscription (timestamp Unix)
        uint256 endDate;            // Date d'expiration de la police
        bool    active;             // Police toujours active ?
        bool    claimed;            // Indemnisation déjà versée cette période ?
    }

    // ── Variables d'état ──────────────────────────────────────────────────────

    address public immutable owner;         // Propriétaire du contrat (assureur)
    IWeatherOracle public weatherOracle;    // Adresse de l'oracle météo

    // Paramètres globaux du produit
    uint256 public constant TRIGGER_MM         = 400;       // Seuil sécheresse (mm)
    uint256 public constant COVERAGE_AMOUNT    = 0.002 ether; // Indemnisation (5000€ ≈ 0.002 ETH)
    uint256 public constant PREMIUM_AMOUNT     = 0.00038 ether; // Prime (950€ ≈ 0.00038 ETH)
    uint256 public constant POLICY_DURATION    = 365 days;  // Durée de la police
    uint256 public constant ORACLE_MAX_AGE     = 7 days;    // Fraîcheur max des données oracle

    // Compteur de polices
    uint256 private _policyCounter;

    // Mapping : ID police → police
    mapping(uint256 => Policy) public policies;

    // Mapping : adresse assuré → liste de ses IDs de police
    mapping(address => uint256[]) public insuredPolicies;

    // ── Événements (logs blockchain) ──────────────────────────────────────────

    /**
     * @notice Émis lors de la souscription d'une nouvelle police.
     */
    event PolicyCreated(
        uint256 indexed policyId,
        address indexed insured,
        uint256 regionId,
        uint256 premium,
        uint256 coverageAmount,
        uint256 triggerMm,
        uint256 endDate
    );

    /**
     * @notice Émis lors du déclenchement automatique d'une indemnisation.
     */
    event PayoutTriggered(
        uint256 indexed policyId,
        address indexed insured,
        uint256 precipitationMm,    // Précipitations observées (mm)
        uint256 triggerMm,          // Seuil qui a été franchi
        uint256 payoutAmount,       // Montant versé en wei
        uint256 timestamp
    );

    /**
     * @notice Émis lors de l'annulation/expiration d'une police.
     */
    event PolicyExpired(
        uint256 indexed policyId,
        address indexed insured
    );

    /**
     * @notice Émis lors d'une vérification ne déclenchant pas de payout.
     */
    event ConditionChecked(
        uint256 indexed policyId,
        uint256 precipitationMm,
        bool    triggered,
        uint256 timestamp
    );

    /**
     * @notice Émis lors du dépôt de fonds par l'assureur.
     */
    event FundsDeposited(address indexed depositor, uint256 amount);

    /**
     * @notice Émis lors de la mise à jour de l'oracle.
     */
    event OracleUpdated(address indexed oldOracle, address indexed newOracle);

    // ── Modificateurs ─────────────────────────────────────────────────────────

    /**
     * @dev Restreint l'accès au propriétaire (assureur).
     */
    modifier onlyOwner() {
        require(msg.sender == owner, "Acces restreint au proprietaire");
        _;
    }

    /**
     * @dev Vérifie que la police existe et est active.
     */
    modifier policyActive(uint256 policyId) {
        require(policies[policyId].active, "Police inexistante ou inactive");
        require(block.timestamp <= policies[policyId].endDate, "Police expiree");
        _;
    }

    /**
     * @dev Vérifie que l'appelant est bien l'assuré de la police.
     */
    modifier onlyInsured(uint256 policyId) {
        require(
            policies[policyId].insured == msg.sender,
            "Seul l'assure peut appeler cette fonction"
        );
        _;
    }

    // ── Constructeur ──────────────────────────────────────────────────────────

    /**
     * @param _oracleAddress Adresse du contrat oracle météo.
     */
    constructor(address _oracleAddress) {
        require(_oracleAddress != address(0), "Adresse oracle invalide");
        owner          = msg.sender;
        weatherOracle  = IWeatherOracle(_oracleAddress);
    }

    // ── Fonctions principales ─────────────────────────────────────────────────

    /**
     * @notice Souscrire à une police d'assurance paramétrique.
     * @param regionId Identifiant de la région agricole (doit correspondre à l'oracle).
     * @dev L'agriculteur envoie exactement PREMIUM_AMOUNT en ETH.
     *      La prime est conservée dans le contrat jusqu'à son utilisation.
     */
    function subscribe(uint256 regionId) external payable returns (uint256 policyId) {
        // Vérification du montant de la prime envoyée
        require(
            msg.value == PREMIUM_AMOUNT,
            "Montant incorrect : envoyez exactement la prime requise"
        );

        // Vérification que le contrat peut payer l'indemnisation
        require(
            address(this).balance >= COVERAGE_AMOUNT,
            "Liquidite insuffisante dans le contrat"
        );

        // Création de la police
        policyId = ++_policyCounter;
        uint256 expiry = block.timestamp + POLICY_DURATION;

        policies[policyId] = Policy({
            insured        : payable(msg.sender),
            regionId       : regionId,
            premium        : msg.value,
            coverageAmount : COVERAGE_AMOUNT,
            triggerMm      : TRIGGER_MM,
            startDate      : block.timestamp,
            endDate        : expiry,
            active         : true,
            claimed        : false
        });

        insuredPolicies[msg.sender].push(policyId);

        emit PolicyCreated(
            policyId,
            msg.sender,
            regionId,
            msg.value,
            COVERAGE_AMOUNT,
            TRIGGER_MM,
            expiry
        );

        return policyId;
    }

    /**
     * @notice Vérifier les conditions météo et déclencher le payout si le seuil est franchi.
     * @param policyId Identifiant de la police à vérifier.
     * @dev Peut être appelé par l'assuré ou par un keeper automatisé (ex: Chainlink Automation).
     *      En production, cette fonction serait appelée automatiquement par Chainlink Keepers.
     *
     * Logique paramétrique :
     *   SI précipitations_annuelles < TRIGGER_MM → payout automatique
     *   SINON                                    → aucune action
     */
    function checkAndTriggerPayout(uint256 policyId)
        external
        policyActive(policyId)
        returns (bool payoutSent)
    {
        Policy storage policy = policies[policyId];

        // Empêcher le double paiement dans la même période
        require(!policy.claimed, "Indemnisation deja versee pour cette periode");

        // Récupération des données de l'oracle
        (uint256 precipMm, uint256 dataTimestamp) = weatherOracle.getPrecipitation(
            policy.regionId
        );

        // Vérification de la fraîcheur des données oracle (anti-manipulation)
        require(
            block.timestamp - dataTimestamp <= ORACLE_MAX_AGE,
            "Donnees oracle trop anciennes - risque de manipulation"
        );

        bool triggered = precipMm < policy.triggerMm;

        emit ConditionChecked(policyId, precipMm, triggered, block.timestamp);

        if (triggered) {
            // ── DÉCLENCHEMENT AUTOMATIQUE DU PAYOUT ──────────────────────────
            policy.claimed = true;  // Marquer avant le transfert (protection reentrancy)

            // Vérification des liquidités disponibles
            require(
                address(this).balance >= policy.coverageAmount,
                "Liquidite insuffisante pour le payout"
            );

            // Transfert automatique vers l'assuré
            policy.insured.transfer(policy.coverageAmount);

            emit PayoutTriggered(
                policyId,
                policy.insured,
                precipMm,
                policy.triggerMm,
                policy.coverageAmount,
                block.timestamp
            );

            return true;
        }

        return false;
    }

    /**
     * @notice Marquer une police comme expirée (nettoyage).
     * @param policyId Identifiant de la police.
     */
    function expirePolicy(uint256 policyId) external {
        Policy storage policy = policies[policyId];
        require(policy.active, "Police deja inactive");
        require(
            block.timestamp > policy.endDate || msg.sender == owner,
            "Police non expiree"
        );

        policy.active = false;
        emit PolicyExpired(policyId, policy.insured);
    }

    // ── Fonctions d'administration (assureur) ─────────────────────────────────

    /**
     * @notice Déposer des fonds dans le contrat pour couvrir les indemnisations.
     * @dev Seul l'assureur peut approvisionner le contrat.
     */
    function depositFunds() external payable onlyOwner {
        require(msg.value > 0, "Montant nul");
        emit FundsDeposited(msg.sender, msg.value);
    }

    /**
     * @notice Mettre à jour l'adresse de l'oracle météo.
     * @param newOracle Nouvelle adresse de l'oracle.
     * @dev Permet de migrer vers un oracle plus fiable sans redéployer le contrat.
     */
    function updateOracle(address newOracle) external onlyOwner {
        require(newOracle != address(0), "Adresse invalide");
        address old = address(weatherOracle);
        weatherOracle = IWeatherOracle(newOracle);
        emit OracleUpdated(old, newOracle);
    }

    /**
     * @notice Retirer l'excédent de liquidités (uniquement si le contrat n'a pas
     *         de polices actives ou après expiration).
     * @param amount Montant en wei à retirer.
     */
    function withdrawExcess(uint256 amount) external onlyOwner {
        require(amount <= address(this).balance, "Solde insuffisant");
        payable(owner).transfer(amount);
    }

    // ── Fonctions de lecture (view) ───────────────────────────────────────────

    /**
     * @notice Obtenir les détails d'une police.
     */
    function getPolicy(uint256 policyId) external view returns (Policy memory) {
        return policies[policyId];
    }

    /**
     * @notice Obtenir toutes les polices d'un assuré.
     */
    function getPoliciesOf(address insured) external view returns (uint256[] memory) {
        return insuredPolicies[insured];
    }

    /**
     * @notice Vérifier la liquidité disponible du contrat.
     */
    function getContractBalance() external view returns (uint256) {
        return address(this).balance;
    }

    /**
     * @notice Nombre total de polices créées.
     */
    function totalPolicies() external view returns (uint256) {
        return _policyCounter;
    }

    /**
     * @notice Obtenir les données météo actuelles pour une région.
     */
    function getCurrentPrecipitation(uint256 regionId)
        external
        view
        returns (uint256 precipitation, uint256 lastUpdate)
    {
        return weatherOracle.getPrecipitation(regionId);
    }

    // ── Sécurité : refus des ETH non sollicités ───────────────────────────────

    /**
     * @dev Rejette les transferts ETH directs (non via depositFunds ou subscribe).
     */
    receive() external payable {
        revert("Utilisez depositFunds() ou subscribe()");
    }

    fallback() external payable {
        revert("Fonction inexistante");
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// ORACLE DE TEST (simulé pour démonstration)
// En production : remplacer par Chainlink Data Feed
// ─────────────────────────────────────────────────────────────────────────────

/**
 * @title MockWeatherOracle
 * @notice Oracle météo simulé pour tests et démonstration.
 *         En production, utiliser Chainlink Any API ou Data Streams.
 *
 * @dev Chainlink en production :
 *      - Chainlink Data Feeds pour les données indexées
 *      - Chainlink Any API pour requêtes HTTP vers APIs météo (Open-Meteo, NOAA)
 *      - Chainlink Automation pour déclencher checkAndTriggerPayout() automatiquement
 */
contract MockWeatherOracle is IWeatherOracle {

    address public owner;

    // regionId → (precipitation_mm, timestamp)
    mapping(uint256 => uint256) public precipitationData;
    mapping(uint256 => uint256) public lastUpdateTime;

    event PrecipitationUpdated(
        uint256 indexed regionId,
        uint256 precipitationMm,
        uint256 timestamp
    );

    constructor() {
        owner = msg.sender;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "Acces restreint");
        _;
    }

    /**
     * @notice Mettre à jour les données de précipitations (appelé par le node Chainlink).
     * @param regionId Identifiant de la région
     * @param precipitationMm Précipitations annuelles cumulées en mm
     */
    function updatePrecipitation(uint256 regionId, uint256 precipitationMm)
        external
        onlyOwner
    {
        precipitationData[regionId] = precipitationMm;
        lastUpdateTime[regionId]    = block.timestamp;

        emit PrecipitationUpdated(regionId, precipitationMm, block.timestamp);
    }

    /**
     * @notice Retourne les précipitations pour une région (implémente IWeatherOracle).
     */
    function getPrecipitation(uint256 regionId)
        external
        view
        override
        returns (uint256 precipitation, uint256 timestamp)
    {
        require(precipitationData[regionId] > 0, "Aucune donnee pour cette region");
        return (precipitationData[regionId], lastUpdateTime[regionId]);
    }
}
