# Changelog

Le versioni seguono il [versionamento semantico](https://semver.org/lang/it/): MAGGIORE.MINORE.CORREZIONE.
Il numero di versione si trova solo in `src/sonifica/__init__.py`.

## [1.0.0] – 2026-10-30

Prima versione pubblica.

- Esplorazione di heatmap cella per cella con la tastiera o il mouse: altezza e volume per il valore, stereo per la colonna, fruscio per i dati mancanti.
- Ascolto dell'intera heatmap lungo una curva di Hilbert a durata fissa, con segnali tra i quadranti e percorso visibile.
- Ascolto riga per riga, per colonna e come spettro; esportazione WAV.
- Sette palette pensate per diversi tipi di ipovisione, verificate anche con la simulazione delle discromatopsie.
- Sei heatmap di esempio, fino a 120×160 celle.
- Ridimensiona e confronta: downscaling con media dell'area o campionamento e misura della coerenza dell'ascolto.
- Analisi di andata e ritorno (dati → audio → dati) con rumore regolabile.
- Interfaccia in italiano e in inglese, lettura a voce, supporto agli screen reader, impostazioni salvate.
