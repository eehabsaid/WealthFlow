"""French -> canonical English routing tokens (see lexicon_fr_de.py). All patterns are written against accent-FOLDED,
lowercase text. PHRASES run first, in order (multi-word, elisions, ranges, relative periods); WORDS is one final pass."""

ACCENTS = "éèêëàâçùûôîïœ"
DOMAIN_WORDS = frozenset({
    "depense", "depenses", "solde", "soldes", "salaire", "salaires", "certificat", "certificats", "actifs", "immobilisations",
    "taux", "devise", "devises", "prix", "comptes", "compte", "mois", "annee", "combien", "derniers", "derniere", "dernier",
    "banque", "banques", "achats", "factures", "recurrentes", "abonnements", "epargne", "gramme", "grammes",
    "janvier", "fevrier", "avril", "juin", "juillet", "aout", "septembre", "octobre", "novembre", "decembre", "mars",
})
POSSESSIVES = frozenset({"mon", "ma", "mes", "ton", "ta", "tes", "notre", "nos", "votre", "vos"})
EXTRA_DOMAIN = frozenset({"ordres", "permanents", "programmes", "periodiques", "reguliers", "terme", "immobilises", "fixes", "statut", "poids", "gramme", "grammes", "carats", "once", "ordre", "prelevements", "echeance", "echeances"})
ENGLISH_CLASH = frozenset({"once", "prime", "primes", "analyse", "comment", "mars", "limit", "reste", "villa", "villas", "plan"})
FUNCTION_WORDS = frozenset({"le", "la", "les", "des", "mon", "ma", "mes", "est", "sont", "pour", "dans", "avec", "et", "du", "quel",
                            "quelle", "quels", "quelles", "cette", "jai", "suis", "je", "moi", "sur", "par", "aux", "quoi"})
_M = "janvier|fevrier|mars|avril|mai|juin|juillet|aout|septembre|octobre|novembre|decembre|janv|fevr|avr|juil|sept"
_START = r"^\s*(?:s'il (?:te|vous) plait )?"

PHRASES = [
    (r"\bj'ai\b", " jai "), (r"\bai[- ]je\b", " aije "), (r"\bn'ai\b", " nai "), (r"\bqu'est[- ]ce (?:que|qu')", " quoi "),
    (r"\bc'est\b", " cest "), (r"\bs'il (?:te|vous) plait\b", " "),
    # actions (must start the sentence)
    (_START + r"(?:ajoute|ajouter|ajoutez)\b", " add "), (_START + r"(?:cree|creer|creez)\b", " create "),
    (_START + r"(?:supprime|supprimer|supprimez|efface|effacer|retire|retirer)\b", " delete "),
    (_START + r"(?:modifie|modifier|modifiez|change|changer|mets a jour)\b", " update "),
    (_START + r"(?:vire|virer|transfere|transferer|transferez)\b", " transfer "), (_START + r"(?:paye|payer|payez)\b", " pay "),
    (_START + r"(?:enregistre|enregistrer|enregistrez|saisis|saisir)\b", " record "), (_START + r"(?:definis|definir|fixe|fixer)\b", " set "),
    # spending / money questions
    (r"\b(?:aije|jai) depense\b", " i spent "), (r"\bcombien d'argent\b", " how much money "),
    (r"\b(?:prix|cours|tarif)(?: du| d'un| de)? grammes? d'or\b", " gold price per gram "),
    (r"\bcombien d'or\b|\bcombien de l'or\b", " how much gold "), (r"\bgrammes? d'or\b", " grams of gold "),
    (r"\bcombien (?:aije|jai)\b(?! .{0,40}(?:depense|paye|gagne|achete|recu))", " how much do i have "),
    (r"\bcombien (?:coute|couter|valent|vaut)\b", " how much is "), (r"\bcombien (?:de|d')", " how many "),
    # ranges and relative periods
    (rf"\b(?:a|au|jusqu'a|jusqu'au|jusqu'en)\s+(?=(?:{_M})\b)", " to "),
    (r"\b(?:les? |ces |au cours des )?(\d{1,2}) derniers? mois\b", r" last \1 months "),
    (r"\bce mois(?:[- ]ci)?\b|\ble mois en cours\b", " this month "), (r"\b(?:le )?mois (?:dernier|passe|precedent)\b", " last month "),
    (r"\bcette annee(?:[- ]ci)?\b", " this year "), (r"\b(?:l'|l )?(?:annee|an) (?:derniere|dernier|passee|precedente)\b", " last year "),
    (r"\b(\d{1,3}) derni(?:er|ere|eres|ers)\b", r" last \1 "), (r"\baujourd'hui\b|\ben ce moment\b|\bactuellement\b|\bmaintenant\b", " today "),
    # dimensions
    (r"\bpar (?:annee|an)\b|\bchaque annee\b|\bannuel(?:le)?s?\b|\bannuellement\b", " per year "),
    (r"\bpar mois\b|\bchaque mois\b|\bmensuel(?:le)?s?\b|\bmensuellement\b", " per month "),
    (r"\bpar jour\b|\bchaque jour\b|\bquotidien(?:ne)?s?\b|\bjournalier\w*", " per day "), (r"\bpar categorie\w*", " by category "),
    (r"\bpar devise\w*", " by currency "), (r"\bpar type\b", " by type "), (r"\bpar (?:banque|compte)s?\b", " by account "),
    (r"\bpar (?:societe|entreprise|employeur)s?\b", " by company "),
    # domain phrases
    (r"\blivres? sterling\b", " sterling "), (r"\blivres? egyptiennes?\b", " egp "), (r"\bfrancs? suisses?\b", " chf "),
    (r"\btaux de change\b|\bcours de change\b", " exchange rate "), (r"\b(?:cours|taux) des devises\b", " currency rates "),
    (r"\b(?:taux|cours) moyen\b", " mid rate "), (r"\bfiche de paie\b|\bbulletin de salaire\b|\bbulletin de paie\b", " payslip "),
    (r"\bdepots? a terme\b", " fixed deposit "), (r"\bactifs? (?:fixes?|immobilises?)\b|\bimmobilisations?\b", " fixed assets "),
    (r"\bordres? permanents?\b", " standing orders "), (r"\bpaiements? (?:programmes?|periodiques|reguliers?)\b", " scheduled payments "),
    (r"\bfactures? (?:a venir|prochaines?|echues?)\b|\bprochaines factures\b", " upcoming bills "),
    (r"\barrive(?:nt)? a echeance\b|\bvient a echeance\b|\bexpire(?:nt)?\b", " matures "),
    (r"\bplus (?:grande?s?|gros(?:se)?s?|eleve(?:e)?s?|cher(?:e)?s?)\b", " biggest "), (r"\bau total\b", " total "),
    (r"\bmontre(?:z)?[- ]moi\b|\baffiche(?:r|z)?\b|\bmontre(?:r)?\b", " show "), (r"\bcomment (?:puis|peux)[- ]je\b", " how can i "),
    (r"\b(?:devrais|dois)[- ]je\b", " should i "), (r"\bqu'en est[- ]il de\b|\bque dire de\b", " what about "),
    # elisions last
    (r"\b(?:l'or)\b|\bd'or\b", " gold "), (r"\bl'", " the "), (r"\bd'", " of "), (r"\b(?:j|m|t|s|n|c|qu)'", " "),
]

WORDS = {
    "statut": "status",
    # months
    "janvier": "january", "fevrier": "february", "mars": "march", "avril": "april", "mai": "may", "juin": "june", "juillet": "july",
    "aout": "august", "septembre": "september", "octobre": "october", "novembre": "november", "decembre": "december",
    "janv": "jan", "fevr": "feb", "avr": "apr", "juil": "jul",
    # expenses
    "depenses": "expenses", "depense": "expense", "depenser": "spend", "frais": "expenses", "achats": "purchases", "achat": "purchase",
    "factures": "bills", "facture": "bill", "transactions": "transactions", "transaction": "transaction", "operations": "transactions",
    "operation": "transaction",
    # balance / accounts
    "solde": "balance", "soldes": "balances", "comptes": "accounts", "compte": "account", "especes": "cash", "liquidite": "liquid",
    "liquidites": "liquid", "liquide": "liquid", "liquides": "liquid", "epargne": "savings", "fonds": "funds", "portefeuille": "wallet",
    "aije": "do i have", "jai": "i have", "banque": "bank", "banques": "banks",
    # salary
    "salaire": "salary", "salaires": "salaries", "remuneration": "salary", "paie": "pay", "paye": "paid", "prime": "bonus", "primes": "bonuses",
    "brut": "gross", "prevu": "expected", "prevue": "expected", "attendu": "expected", "attendue": "expected",
    # certificates
    "certificat": "certificate", "certificats": "certificates", "depot": "deposit", "depots": "deposits", "interet": "interest",
    "interets": "interest", "prochain": "next", "prochaine": "next", "prochains": "next", "prochaines": "next", "echeance": "maturity",
    "echeances": "maturity", "quand": "when",
    # budgets / recurring
    "depasse": "exceeded", "depasses": "exceeded", "depassent": "exceeded", "depassement": "exceeded", "depassements": "exceeded",
    "proche": "close to", "proches": "close to", "reste": "remaining", "restant": "remaining", "restante": "remaining",
    "restants": "remaining", "restantes": "remaining", "restent": "remaining", "disponible": "remaining", "plafond": "spending limit",
    "plafonds": "spending limits", "recurrent": "recurring", "recurrente": "recurring", "recurrents": "recurring",
    "recurrentes": "recurring", "abonnement": "subscription", "abonnements": "subscriptions", "prelevement": "direct debit",
    "prelevements": "direct debits",
    # assets
    "actif": "assets", "actifs": "assets", "immobilier": "real estate", "vehicule": "vehicle", "vehicules": "vehicles",
    "voiture": "car", "voitures": "cars", "appartement": "apartment", "appartements": "apartments", "terrain": "land",
    "terrains": "land", "villa": "villa", "villas": "villas", "propriete": "property", "proprietes": "properties",
    # gold / market
    "or": "gold", "prix": "price", "cours": "price", "taux": "rate", "gramme": "gram", "grammes": "grams", "carats": "carat",
    "once": "ounce", "onces": "ounce", "vente": "sell", "vendre": "sell", "vend": "sell", "devise": "currency", "devises": "currencies",
    # metrics
    "total": "total", "totale": "total", "somme": "total", "moyenne": "average", "moyen": "average",
    "liste": "list", "lister": "list", "details": "details", "detail": "details", "detaille": "detailed", "detaillee": "detailed",
    "detailles": "detailed", "tableau": "table", "tous": "all", "toutes": "all", "ventilation": "breakdown",
    "repartition": "breakdown", "maximum": "top", "dernier": "last", "derniere": "last", "derniers": "last", "dernieres": "last",
    "recent": "recent", "recente": "recent", "recents": "recent", "recentes": "recent", "actuel": "current", "actuelle": "current",
    # analytic
    "comparer": "compare", "compare": "compare", "comparaison": "compare", "tendance": "trend", "tendances": "trend",
    "pourquoi": "why", "prevision": "forecast", "previsions": "forecast", "prevoir": "forecast", "predire": "predict",
    "croissance": "growth", "explique": "explain", "expliquer": "explain", "explication": "explain", "raison": "reason",
    "conseil": "advice", "conseils": "advice", "conseille": "advise", "recommande": "recommend", "recommander": "recommend",
    "suggere": "suggest", "suggerer": "suggest", "analyse": "analyze", "analyser": "analyze", "ameliorer": "improve",
    "economiser": "save", "epargner": "save", "reduire": "reduce", "diminuer": "reduce", "couper": "cut", "scenario": "scenario",
    "simulation": "simulate", "simuler": "simulate", "comment": "how",
    # grammar
    "combien": "how much", "quel": "what", "quelle": "what", "quels": "what", "quelles": "what", "est": "is", "sont": "are",
    "mon": "my", "ma": "my", "mes": "my", "je": "i", "moi": "me", "en": "in", "pour": "for", "de": "of", "du": "of", "des": "of",
    "dans": "in", "et": "and", "le": "the", "la": "the", "les": "the", "un": "one", "une": "one", "ce": "this", "cette": "this",
    "aussi": "also", "alors": "then", "entre": "between", "depuis": "since", "avant": "before", "apres": "after",
}
