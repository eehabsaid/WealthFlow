"""Paraphrase corpus for the query-engine router in French and German: >=15 phrasings per capability per language.
Months are explicit or relative so results never depend on today's date."""

FR = {
    "expenses": [
        "Combien ai-je dépensé en septembre 2026 ?", "Mes dépenses de septembre 2026", "Total des dépenses pour août 2026",
        "Quelles sont mes dépenses ce mois-ci ?", "Combien ai-je dépensé le mois dernier ?", "Dépenses par catégorie en septembre 2026",
        "Dépenses quotidiennes pour juillet 2026", "Dépenses par mois en 2026", "Montre-moi mes dépenses de juin à septembre 2026",
        "Détail de mes dépenses pour juin 2026", "Ma dernière dépense", "Quelles sont mes 5 dernières dépenses ?",
        "Ma plus grosse dépense en septembre 2026", "Dépenses moyennes par mois en 2026", "Combien ai-je dépensé ces 3 derniers mois ?",
        "Liste de mes transactions d'août 2026", "Mes dépenses de l'année dernière", "Dépenses entre juin et août 2026",
    ],
    "salary": [
        "Quel a été mon salaire de janvier 2026 ?", "Mon salaire en septembre 2026", "Mon dernier salaire", "Salaire versé le mois dernier",
        "Total des salaires pour 2026", "Salaire moyen par mois en 2026", "Prime de décembre 2025", "Salaire par société en 2026",
        "Salaire par an", "Mes salaires de janvier à mars 2026", "Fiche de paie de juillet 2026", "Salaire prévu pour mars 2026",
        "Mes primes en 2025", "Quel est mon salaire actuel ?", "Rémunération de mai 2026", "Mon salaire d'août 2026",
    ],
    "balance": [
        "Quel est mon solde ?", "Combien d'argent ai-je ?", "Solde total de mes comptes", "Combien ai-je sur mes comptes ?",
        "Mes soldes par devise", "Solde par banque", "Liste de tous mes comptes", "Combien ai-je en espèces ?", "Mon solde en dollars",
        "Combien ai-je en dollars ?", "Solde en euros", "Quel est mon solde actuel ?", "Soldes par type de compte",
        "Total de tous mes comptes", "Combien y a-t-il sur mes comptes bancaires ?", "Mes liquidités", "Combien ai-je en banque ?",
    ],
    "certificates": [
        "Mes certificats", "Combien de certificats ai-je ?", "Capital total de mes certificats", "Résumé de mes certificats",
        "Liste de mes certificats", "Quand est le prochain paiement d'intérêts de mes certificats ?", "Prochains intérêts de mes certificats",
        "Quel certificat arrive à échéance en premier ?", "Dates d'échéance de mes certificats", "Quand expire mon certificat ?",
        "Combien d'intérêts mensuels mes certificats rapportent-ils ?", "Mes dépôts à terme", "Total des intérêts de mes certificats",
        "Détails de mes certificats",
    ],
    "fixed_assets": [
        "Mes immobilisations", "Quels sont mes actifs fixes ?", "Total de mes immobilisations", "Mon immobilier", "Mes véhicules",
        "Mes voitures", "Liste de mes actifs", "Combien d'actifs ai-je ?", "Actifs par type", "Répartition de mes actifs par type",
        "Valeur de mes appartements", "Mes terrains", "Valeur de ma villa", "Mes actifs fixes",
    ],
    "gold_holdings": [
        "Combien d'or ai-je ?", "Combien de grammes d'or ai-je ?", "Mon or", "Combien d'or est-ce que je possède ?", "Combien d'or détiens-je ?",
        "Mes grammes d'or", "Total de mon or en grammes", "Poids de mon or", "Mon or en grammes", "J'ai combien d'or ?",
        "Combien d'or j'ai dans mes comptes ?", "Mon or possédé", "Combien de grammes d'or je détiens ?", "Total de mes grammes d'or",
        "Combien d'or me reste-t-il ?",
    ],
    "gold_price": [
        "Prix de l'or aujourd'hui", "Quel est le prix de l'or 24 carats ?", "Prix du gramme d'or 21 carats", "Cours de l'or",
        "Prix d'achat de l'or 18 carats", "Prix de vente de l'or 24 carats", "Combien coûte l'or 22 carats ?", "Prix de l'once d'or",
        "Cours de l'once d'or en dollars", "Prix de l'or par gramme", "Tous les prix de l'or", "Or 24 carats prix",
        "Quel est le cours de l'or aujourd'hui ?", "Prix de l'or 21 carats à l'achat",
    ],
    "exchange_rates": [
        "Quel est le taux de change du dollar ?", "Taux de change de l'euro", "Cours du dollar aujourd'hui", "Combien vaut un dollar ?",
        "Combien vaut l'euro ?", "Tous les taux de change", "Taux de change USD", "Cours de change de la livre sterling",
        "Taux du dollar à l'achat", "Prix du dollar à la vente", "Taux de change moyen du dollar", "Taux de change dollar euro livre",
        "Quel est le taux de change aujourd'hui ?", "Cours du riyal", "Taux de change du dirham",
    ],
    "budgets": [
        "Quel est l'état de mes budgets ?", "Mes budgets", "Quels budgets sont dépassés ?", "Ai-je dépassé mon budget ?",
        "Combien reste-t-il sur mon budget ?", "Budgets proches de la limite", "Statut des budgets", "Budget restant par catégorie",
        "Mes plafonds de dépenses", "Quels budgets ai-je dépassés ?", "Montre-moi mes budgets", "Où en sont mes budgets ce mois-ci ?",
        "Budgets actifs", "Mes budgets dépassés", "Mes budgets restants",
    ],
    "recurring": [
        "Mes abonnements", "Mes paiements récurrents", "Factures à venir", "Prochaines factures", "Mes prélèvements automatiques",
        "Mes ordres permanents", "Combien me coûtent mes abonnements par mois ?", "Total de mes dépenses récurrentes",
        "Mes engagements récurrents mensuels", "Liste de mes opérations récurrentes", "Paiements programmés", "Mes paiements réguliers",
        "Prochains abonnements à payer", "Mes abonnements actifs", "Mes paiements récurrents du mois",
    ],
}

DE = {
    "expenses": [
        "Wie viel habe ich im September 2026 ausgegeben?", "Meine Ausgaben im September 2026", "Gesamtausgaben für August 2026",
        "Wie hoch sind meine Ausgaben diesen Monat?", "Wie viel habe ich letzten Monat ausgegeben?", "Ausgaben nach Kategorie im September 2026",
        "Tägliche Ausgaben für Juli 2026", "Ausgaben pro Monat 2026", "Zeige mir meine Ausgaben von Juni bis September 2026",
        "Details meiner Ausgaben für Juni 2026", "Meine letzte Ausgabe", "Meine letzten 5 Ausgaben", "Größte Ausgabe im September 2026",
        "Durchschnittliche Ausgaben pro Monat 2026", "Wie viel habe ich in den letzten 3 Monaten ausgegeben?", "Liste meiner Buchungen im August 2026",
        "Meine Ausgaben im letzten Jahr", "Ausgaben zwischen Juni und August 2026",
    ],
    "salary": [
        "Wie hoch war mein Gehalt im Januar 2026?", "Mein Gehalt im September 2026", "Mein letztes Gehalt", "Gezahltes Gehalt letzten Monat",
        "Summe der Gehälter für 2026", "Durchschnittliches Gehalt pro Monat 2026", "Bonus im Dezember 2025", "Gehalt nach Firma 2026",
        "Gehalt pro Jahr", "Meine Gehälter von Januar bis März 2026", "Gehaltsabrechnung Juli 2026", "Erwartetes Gehalt für März 2026",
        "Meine Boni 2025", "Aktuelles Gehalt", "Lohn im Mai 2026", "Gehalt Juni 2026",
    ],
    "balance": [
        "Wie hoch ist mein Kontostand?", "Wie viel Geld habe ich?", "Gesamtsaldo meiner Konten", "Wie viel habe ich auf meinen Konten?",
        "Meine Salden nach Währung", "Saldo pro Bank", "Liste aller meiner Konten", "Wie viel Bargeld habe ich?", "Mein Kontostand in Dollar",
        "Wie viel Dollar habe ich?", "Kontostand in Euro", "Salden nach Kontoart", "Wie viel ist auf meinen Bankkonten?", "Meine Liquidität",
        "Wie viel Geld ist auf meinem Konto?", "Zeige meine Kontostände", "Gesamtguthaben",
    ],
    "certificates": [
        "Meine Zertifikate", "Wie viele Zertifikate habe ich?", "Gesamtkapital meiner Zertifikate", "Übersicht meiner Zertifikate",
        "Liste meiner Zertifikate", "Wann ist die nächste Zinszahlung meiner Zertifikate?", "Nächste Zinsen meiner Zertifikate",
        "Welches Zertifikat wird zuerst fällig?", "Fälligkeitsdaten meiner Zertifikate", "Wann läuft mein Zertifikat ab?",
        "Wie viel Zinsen zahlen meine Zertifikate monatlich?", "Meine Festgelder", "Gesamtzinsen meiner Zertifikate", "Details meiner Zertifikate",
    ],
    "fixed_assets": [
        "Meine Anlagegüter", "Was sind meine Anlagegüter?", "Gesamtwert meiner Anlagegüter", "Meine Immobilien", "Meine Fahrzeuge",
        "Meine Autos", "Liste meiner Vermögenswerte", "Wie viele Anlagegüter habe ich?", "Anlagegüter nach Art",
        "Aufteilung meiner Vermögenswerte nach Art", "Wert meiner Wohnungen", "Meine Grundstücke", "Wert meiner Villa", "Mein Haus",
    ],
    "gold_holdings": [
        "Wie viel Gold habe ich?", "Wie viel Gold besitze ich?", "Mein Gold", "Mein Goldbestand", "Meine Goldbestände",
        "Wie viele Gramm Gold habe ich?", "Mein Goldbesitz", "Wie viel Gold habe ich auf meinen Konten?", "Wie viele Gramm Gold besitze ich?",
        "Wie viel Gold habe ich insgesamt?", "Mein Gold in Gramm", "Wie viel Gold habe ich noch?", "Wie viele Gramm Gold habe ich insgesamt?",
        "Mein gesamter Goldbestand", "Wie viel Gold habe ich gespeichert?",
    ],
    "gold_price": [
        "Goldpreis heute", "Wie hoch ist der Goldpreis für 24 Karat?", "Goldpreis pro Gramm 21 Karat", "Goldkurs", "Kaufpreis Gold 18 Karat",
        "Verkaufspreis Gold 24 Karat", "Was kostet Gold 22 Karat?", "Goldpreis pro Unze", "Preis der Goldunze in Dollar", "Alle Goldpreise",
        "Aktueller Goldpreis", "Goldpreis heute für 21 Karat", "Wie hoch ist der Goldkurs heute?", "Gold 24 Karat Preis",
    ],
    "exchange_rates": [
        "Wie hoch ist der Wechselkurs des Dollars?", "Wechselkurs Euro", "Dollarkurs heute", "Wie viel kostet ein Dollar?", "Was kostet ein Euro?",
        "Alle Wechselkurse", "Wechselkurs USD", "Wechselkurs Pfund Sterling", "Kaufkurs Dollar", "Verkaufskurs Dollar", "Mittelkurs Dollar",
        "Devisenkurse heute", "Wie hoch ist der Wechselkurs heute?", "Wechselkurs Riyal", "Wechselkurs Dirham",
    ],
    "budgets": [
        "Wie ist der Stand meiner Budgets?", "Meine Budgets", "Welche Budgets sind überschritten?", "Habe ich mein Budget überschritten?",
        "Wie viel ist von meinem Budget übrig?", "Budgets nahe am Limit", "Budgetstatus", "Verbleibendes Budget pro Kategorie",
        "Meine Ausgabenlimits", "Zeige meine Budgets", "Wo stehen meine Budgets diesen Monat?", "Aktive Budgets", "Meine überschrittenen Budgets",
        "Verbleibende Budgets", "Budgets knapp am Limit",
    ],
    "recurring": [
        "Meine Abonnements", "Meine wiederkehrenden Zahlungen", "Anstehende Rechnungen", "Kommende Rechnungen", "Meine Daueraufträge",
        "Meine Lastschriften", "Wie viel kosten mich meine Abonnements pro Monat?", "Summe meiner wiederkehrenden Ausgaben",
        "Monatliche Verpflichtungen durch wiederkehrende Zahlungen", "Liste meiner wiederkehrenden Buchungen", "Geplante Zahlungen",
        "Meine regelmäßigen Zahlungen", "Nächste fällige Abonnements", "Aktive Abonnements", "Meine wiederkehrenden Rechnungen",
    ],
}

FALL_THROUGH_FR = [
    "Pourquoi mes dépenses sont-elles si élevées en septembre 2026 ?", "Compare mes dépenses d'août et septembre 2026",
    "Comment puis-je réduire mes dépenses ?", "Devrais-je acheter de l'or maintenant ?", "Ajoute une dépense de 50 pour le déjeuner",
    "Supprime ma dernière dépense", "Prévision de mon solde pour l'année prochaine", "Conseille-moi sur mon budget", "Bonjour", "Merci",
    "Que peux-tu faire ?", "Transfère 500 vers l'épargne", "Recommande-moi comment économiser", "Pourquoi le dollar augmente-t-il ?",
]
FALL_THROUGH_DE = [
    "Warum sind meine Ausgaben im September 2026 so hoch?", "Vergleiche meine Ausgaben im August und September 2026", "Wie kann ich meine Ausgaben senken?",
    "Sollte ich jetzt Gold kaufen?", "Füge eine Ausgabe von 50 für Mittagessen hinzu", "Lösche meine letzte Ausgabe",
    "Prognose meines Kontostands für nächstes Jahr", "Gib mir einen Rat zu meinem Budget", "Hallo", "Danke", "Was kannst du?",
    "Überweise 500 auf mein Sparkonto", "Empfiehl mir, wie ich sparen kann", "Warum steigt der Dollar?",
]
