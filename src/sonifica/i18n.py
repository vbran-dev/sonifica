"""Italian / English translations."""

from __future__ import annotations

import locale

LANGUAGES = {"it": "Italiano", "en": "English"}
_current = "it"


def system_language() -> str:
    try:
        code = (locale.getlocale()[0] or "").lower()
    except ValueError:
        code = ""
    return "it" if code.startswith("it") else "en"


def set_language(lang: str) -> None:
    global _current
    if lang not in LANGUAGES:
        raise ValueError(f"Unknown language: {lang}")
    _current = lang


def language() -> str:
    return _current


def tr(key: str, **kwargs: object) -> str:
    it, en = STRINGS[key]
    text = it if _current == "it" else en
    return text.format(**kwargs) if kwargs else text


def number(v: float, digits: int = 4) -> str:
    text = f"{v:.{digits}g}"
    return text.replace(".", ",") if _current == "it" else text


def fixed(v: float, decimals: int = 3) -> str:
    text = f"{v:.{decimals}f}"
    return text.replace(".", ",") if _current == "it" else text


STRINGS: dict[str, tuple[str, str]] = {
    # --- dati ---------------------------------------------------------------
    "err.not_2d": ("I dati devono essere una tabella 2D non vuota.", "Data must be a non-empty 2D table."),
    "err.no_numbers": ("La tabella non contiene valori numerici.", "The table contains no numeric values."),
    "err.csv_empty": ("Il file CSV è vuoto.", "The CSV file is empty."),
    "err.csv_no_rows": ("Il file CSV non contiene righe di dati.", "The CSV file contains no data rows."),
    "row": ("riga", "row"),
    "col": ("colonna", "column"),
    "resized_name": ("{name} · {rows}×{cols}", "{name} · {rows}×{cols}"),
    # --- esempi -------------------------------------------------------------
    "ex.temperature": ("Temperature mensili", "Monthly temperatures"),
    "ex.traffic": ("Traffico settimanale", "Weekly traffic"),
    "ex.correlation": ("Matrice di correlazione", "Correlation matrix"),
    "ex.sensors": ("Sensori con dati mancanti", "Sensors with missing data"),
    "ex.terrain": ("Rilievo montuoso", "Mountain terrain"),
    "ex.waves": ("Interferenza di onde", "Wave interference"),
    "ex.synthetic": ("dati sintetici", "synthetic data"),
    "months": ("Gen Feb Mar Apr Mag Giu Lug Ago Set Ott Nov Dic", "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec"),
    "weekdays": ("Lun Mar Mer Gio Ven Sab Dom", "Mon Tue Wed Thu Fri Sat Sun"),
    # --- palette ------------------------------------------------------------
    "pal.standard": ("Standard", "Standard"),
    "pal.standard.desc": (
        "Percettivamente uniforme e leggibile anche con le discromatopsie più comuni. Buon punto di partenza.",
        "Perceptually uniform and readable with the most common colour vision deficiencies. A good start.",
    ),
    "pal.red_green": ("Daltonismo rosso–verde", "Red–green colour blindness"),
    "pal.red_green.desc": (
        "Per protanopia e deuteranopia: usa solo l'asse blu–giallo, che resta ben distinguibile.",
        "For protanopia and deuteranopia: uses only the blue–yellow axis, which stays distinguishable.",
    ),
    "pal.blue_yellow": ("Glaucoma, retinopatia diabetica, tritanopia", "Glaucoma, diabetic retinopathy, tritanopia"),
    "pal.blue_yellow.desc": (
        "Evita l'asse blu–giallo, spesso compromesso nelle discromatopsie acquisite. Va dal rosso scuro al bianco.",
        "Avoids the blue–yellow axis, often impaired in acquired deficiencies. Runs from dark red to white.",
    ),
    "pal.cataract": ("Cataratta", "Cataract"),
    "pal.cataract.desc": (
        "Il cristallino opacizzato filtra il blu e riduce il contrasto: solo colori caldi e massimo contrasto.",
        "A clouded lens filters blue and lowers contrast: warm colours only and maximum contrast.",
    ),
    "pal.macular": ("Maculopatia, bassa sensibilità al contrasto", "Macular degeneration, low contrast"),
    "pal.macular.desc": (
        "Cinque livelli netti con grandi salti di luminosità: più facili da riconoscere anche con visione "
        "centrale ridotta.",
        "Five distinct levels with large steps in lightness: easier to tell apart even with reduced central "
        "vision.",
    ),
    "pal.greyscale": ("Acromatopsia, scala di grigi", "Achromatopsia, greyscale"),
    "pal.greyscale.desc": (
        "Solo luminosità, nessun colore: per chi non percepisce i colori o stampa in bianco e nero.",
        "Lightness only, no colour: for people who do not perceive colour, or for black-and-white printing.",
    ),
    "pal.photophobia": ("Fotofobia (albinismo, aniridia)", "Photophobia (albinism, aniridia)"),
    "pal.photophobia.desc": (
        "Luminosità massima contenuta per ridurre l'abbagliamento, con toni freddi e tenui.",
        "Limited maximum brightness to reduce glare, with soft, cool tones.",
    ),
    # --- curva di Hilbert -----------------------------------------------------
    "quadrant.1": ("in alto a sinistra", "top left"),
    "quadrant.2": ("in basso a sinistra", "bottom left"),
    "quadrant.3": ("in basso a destra", "bottom right"),
    "quadrant.4": ("in alto a destra", "top right"),
    # --- analisi ------------------------------------------------------------
    "rt.hilbert": ("Curva di Hilbert (valore → altezza)", "Hilbert curve (value → pitch)"),
    "rt.sequence": ("Sequenza di note (valore → altezza)", "Note sequence (value → pitch)"),
    "rt.spectral": ("Heatmap come spettro (valore → volume)", "Heatmap as spectrum (value → loudness)"),
    "rt.verdict.na": ("non calcolabile", "cannot be computed"),
    "rt.verdict.1": ("quasi tutta l'informazione si conserva", "almost all information is preserved"),
    "rt.verdict.2": (
        "l'andamento generale si conserva molto bene, con piccoli errori",
        "the overall pattern is preserved very well, with small errors",
    ),
    "rt.verdict.3": (
        "l'andamento si riconosce, ma si perdono dettagli",
        "the pattern is recognisable, but detail is lost",
    ),
    "rt.verdict.4": ("buona parte dell'informazione va persa", "much of the information is lost"),
    "rt.describe": (
        "correlazione {r}, errore medio {mean} (massimo {max}) su una scala da 0 a 1: {verdict}.",
        "correlation {r}, mean error {mean} (max {max}) on a 0 to 1 scale: {verdict}.",
    ),
    "rt.skipped": (
        "Sequenza di note omessa: con {cells} celle durerebbe troppo. Ridimensiona la heatmap per includerla.",
        "Note sequence skipped: with {cells} cells it would be too long. Resize the heatmap to include it.",
    ),
    # --- coerenza -------------------------------------------------------------
    "coh.verdict.1": ("suonano quasi identiche", "they sound almost identical"),
    "coh.verdict.2": ("suonano molto simili", "they sound very similar"),
    "coh.verdict.3": ("si riconosce la stessa forma", "the same shape is recognisable"),
    "coh.verdict.4": ("suonano in modo diverso", "they sound different"),
}

STRINGS.update({
    # --- finestra principale ---------------------------------------------------
    "win.title": ("Sonifica {version} – {name}", "Sonifica {version} – {name}"),
    "btn.examples": ("Esempi", "Examples"),
    "btn.open": ("Apri file", "Open file"),
    "canvas.subtitle": (
        "{rows} righe × {cols} colonne · usa le frecce per ascoltare, F1 per i comandi",
        "{rows} rows × {cols} columns · use the arrow keys to listen, F1 for commands",
    ),
    "sec.cell": ("Cella selezionata", "Selected cell"),
    "sec.palette": ("Palette", "Palette"),
    "sec.listen": ("Ascolta", "Listen"),
    "sec.sound": ("Suono", "Sound"),
    "sec.access": ("Accessibilità e lingua", "Accessibility and language"),
    "stat.min": ("Minimo", "Minimum"),
    "stat.max": ("Massimo", "Maximum"),
    "stat.missing": ("Mancanti", "Missing"),
    "missing": ("mancante", "missing"),
    "pct": ("{pct}% dell'intervallo", "{pct}% of the range"),
    "pal.accessible": ("Palette dei colori", "Colour palette"),
    "pal.reverse": ("Inverti (valori alti più scuri)", "Reverse (high values darker)"),
    "pal.spoken": ("Palette {name}. {desc}", "Palette {name}. {desc}"),
    "btn.row": ("Riga", "Row"),
    "btn.col": ("Colonna", "Column"),
    "btn.all": ("Tutto", "All"),
    "btn.spectrum": ("Come spettro", "As spectrum"),
    "btn.stop": ("Stop", "Stop"),
    "btn.roundtrip": ("Analisi andata e ritorno", "Round-trip analysis"),
    "btn.compare": ("Ridimensiona e confronta", "Resize and compare"),
    "f.route": ("Percorso", "Path"),
    "f.total": ("Durata totale", "Total duration"),
    "f.note": ("Durata nota", "Note length"),
    "f.scale": ("Scala", "Scale"),
    "f.from": ("Da", "From"),
    "f.to": ("A", "To"),
    "f.noise": ("Rumore analisi", "Analysis noise"),
    "f.voice": ("Lettura a voce", "Speech"),
    "f.language": ("Lingua", "Language"),
    "route.hilbert": ("Curva di Hilbert", "Hilbert curve"),
    "route.rows": ("Righe, nota per nota", "Rows, note by note"),
    "route.tip": (
        "Hilbert: durata fissa, matrici simili suonano simili. Righe: una nota per cella, riga dopo riga.",
        "Hilbert: fixed duration, similar matrices sound similar. Rows: one note per cell, row after row.",
    ),
    "total.tip": (
        "Durata dell'ascolto lungo la curva di Hilbert, uguale per ogni matrice",
        "Length of the Hilbert-curve playback, the same for every matrix",
    ),
    "noise.tip": (
        "Rapporto segnale/rumore usato nell'analisi di andata e ritorno",
        "Signal-to-noise ratio used in the round-trip analysis",
    ),
    "noise.none": ("Nessuno", "None"),
    "scale.continuous": ("continua", "continuous"),
    "scale.chromatic": ("cromatica", "chromatic"),
    "scale.major": ("maggiore", "major"),
    "scale.pentatonic": ("pentatonica", "pentatonic"),
    "chk.markers": ("Segnali tra i quadranti", "Quadrant cues"),
    "chk.path": ("Mostra il percorso (Ctrl+H)", "Show the path (Ctrl+H)"),
    "chk.rich": ("Timbro con armonici", "Rich timbre (harmonics)"),
    "chk.hover": ("Suona al passaggio del mouse", "Play on mouse hover"),
    "voice.enter": ("Solo con Invio", "Only with Enter"),
    "voice.move": ("A ogni spostamento", "On every move"),
    "voice.never": ("Mai", "Never"),
    "voice.unavailable": (
        "Sintesi vocale non disponibile su questo sistema",
        "Text-to-speech is not available on this system",
    ),
    "menu.file": ("&File", "&File"),
    "menu.open": ("&Apri CSV o immagine…", "&Open CSV or image…"),
    "menu.examples": ("&Esempi", "&Examples"),
    "menu.export": ("E&sporta audio WAV…", "E&xport WAV audio…"),
    "menu.quit": ("&Esci", "&Quit"),
    "menu.listen": ("&Ascolto", "&Listen"),
    "menu.play_all": ("Ascolta &tutta la heatmap", "Play the &whole heatmap"),
    "menu.spectrum": ("Ascolta come s&pettro", "Play as s&pectrum"),
    "menu.stop": ("&Ferma", "&Stop"),
    "menu.path": ("Mostra il percorso di &Hilbert", "Show the &Hilbert path"),
    "menu.roundtrip": ("Analisi &andata e ritorno…", "&Round-trip analysis…"),
    "menu.resize": ("&Ridimensiona e confronta…", "Resi&ze and compare…"),
    "menu.focus": ("Torna alla &heatmap", "Back to the &heatmap"),
    "menu.help": ("A&iuto", "&Help"),
    "menu.shortcuts": ("&Comandi da tastiera", "&Keyboard commands"),
    "menu.about": ("&Informazioni su Sonifica", "&About Sonifica"),
    "about.title": ("Informazioni su Sonifica", "About Sonifica"),
    "about.text": (
        "<b>Sonifica {version}</b><br><br>"
        "Esplora heatmap e tabelle di dati con l'udito.<br>"
        "Pensata per persone non vedenti e ipovedenti.<br><br>"
        "Software libero con licenza MIT.<br>"
        "© 2026 Valentina Brancati · <a href=\"https://vbrane.it\">vbrane.it</a>",
        "<b>Sonifica {version}</b><br><br>"
        "Explore heatmaps and data tables by ear.<br>"
        "Designed for blind and low-vision people.<br><br>"
        "Free software under the MIT licence.<br>"
        "© 2026 Valentina Brancati · <a href=\"https://vbrane.it\">vbrane.it</a>",
    ),
    "version.tag": ("versione {version}", "version {version}"),
    "audio.unavailable": ("Audio non disponibile: {err}", "Audio not available: {err}"),
    "audio.no_device": ("nessun dispositivo", "no device"),
    "err.title": ("Errore", "Error"),
    "err.open_file": ("Impossibile aprire il file:\n{err}", "Could not open the file:\n{err}"),
    "err.range": ("La frequenza massima deve superare la minima.", "The maximum frequency must exceed the minimum."),
    "summary": (
        "{name}. {rows} righe per {cols} colonne. Minimo {vmin} in {pmin}. Massimo {vmax} in {pmax}.",
        "{name}. {rows} rows by {cols} columns. Minimum {vmin} at {pmin}. Maximum {vmax} at {pmax}.",
    ),
    "summary.missing": (" Dati mancanti: {n}.", " Missing values: {n}."),
    "play.end": ("Fine dell'ascolto", "End of playback"),
    "play.quadrant": ("Quadrante {q} di 4: {name}", "Quadrant {q} of 4: {name}"),
    "rows.too_long.title": ("Troppo lunga", "Too long"),
    "rows.too_long": (
        "La lettura nota per nota durerebbe circa {minutes} minuti. "
        "Usa la curva di Hilbert, che dura sempre uguale, oppure ridimensiona la heatmap.",
        "Note-by-note playback would last about {minutes} minutes. "
        "Use the Hilbert curve, which always lasts the same, or resize the heatmap.",
    ),
    "export.title": ("Esporta WAV", "Export WAV"),
    "export.label": ("Codifica:", "Encoding:"),
    "export.spectrum": ("Spettro", "Spectrum"),
    "export.save": ("Salva audio", "Save audio"),
    "export.filter": ("Audio WAV (*.wav)", "WAV audio (*.wav)"),
    "export.saved": ("Audio salvato in {path}", "Audio saved to {path}"),
    "open.title": ("Apri dati", "Open data"),
    "open.filter": ("Dati", "Data"),
    "open.all": ("Tutti i file", "All files"),
    "lang.changed": ("Lingua: Italiano", "Language: English"),
    "help.title": ("Comandi da tastiera", "Keyboard commands"),
    "help.text": (
        "Sulla heatmap:\n"
        "Frecce: spostati di una cella (senti il valore)\n"
        "Home / Fine: inizio / fine della riga\n"
        "Pagina su / giù: prima / ultima riga\n"
        "Ctrl+Home / Ctrl+Fine: prima / ultima cella\n"
        "Spazio: ascolta la riga intera, da sinistra a destra\n"
        "C: ascolta la colonna intera, dall'alto in basso\n"
        "Invio: leggi a voce la cella corrente\n"
        "I: riepilogo dei dati\n"
        "Esc: ferma l'audio\n\n"
        "Ovunque:\n"
        "Ctrl+O apri file, Ctrl+E esempi\n"
        "Ctrl+P ascolta tutta la heatmap, Ctrl+Maiusc+P ascolta come spettro\n"
        "Ctrl+H mostra o nasconde il percorso di Hilbert\n"
        "Ctrl+D ridimensiona e confronta, Ctrl+R analisi di andata e ritorno\n"
        "Ctrl+S esporta WAV, Ctrl+L cambia lingua\n"
        "F6 torna alla heatmap, F1 questa guida\n\n"
        "Suoni: più acuto e più forte = valore più alto.\n"
        "La posizione destra/sinistra indica la colonna.\n"
        "Un fruscio indica un dato mancante, un colpo grave il bordo della tabella.\n\n"
        "Tutta la heatmap lungo la curva di Hilbert: dura sempre lo stesso tempo.\n"
        "Parte in alto a sinistra, scende, attraversa il basso e finisce in alto a destra.\n"
        "Tre tocchi secchi segnano il passaggio tra i quattro quadranti.",
        "On the heatmap:\n"
        "Arrow keys: move one cell (hear the value)\n"
        "Home / End: start / end of the row\n"
        "Page Up / Down: first / last row\n"
        "Ctrl+Home / Ctrl+End: first / last cell\n"
        "Space: play the whole row, left to right\n"
        "C: play the whole column, top to bottom\n"
        "Enter: read the current cell aloud\n"
        "I: data summary\n"
        "Esc: stop the audio\n\n"
        "Anywhere:\n"
        "Ctrl+O open file, Ctrl+E examples\n"
        "Ctrl+P play the whole heatmap, Ctrl+Shift+P play as spectrum\n"
        "Ctrl+H show or hide the Hilbert path\n"
        "Ctrl+D resize and compare, Ctrl+R round-trip analysis\n"
        "Ctrl+S export WAV, Ctrl+L switch language\n"
        "F6 back to the heatmap, F1 this guide\n\n"
        "Sounds: higher and louder = higher value.\n"
        "Left/right position tells the column.\n"
        "A hiss marks a missing value, a low thud the edge of the table.\n\n"
        "Whole heatmap along the Hilbert curve: always the same duration.\n"
        "It starts top left, goes down, crosses the bottom and ends top right.\n"
        "Three short clicks mark the passage between the four quadrants.",
    ),
    # --- widget heatmap ------------------------------------------------------
    "hm.empty": ("Apri un file CSV o un'immagine (Ctrl+O)", "Open a CSV file or an image (Ctrl+O)"),
    "hm.name": ("Heatmap", "Heatmap"),
    "hm.desc": ("Usa le frecce per muoverti tra le celle.", "Use the arrow keys to move between cells."),
    # --- finestra andata e ritorno ---------------------------------------------
    "rtw.window": ("Sonifica – Andata e ritorno", "Sonifica – Round trip"),
    "rtw.title": ("Andata e ritorno", "Round trip"),
    "rtw.subtitle": (
        "Dati → audio → spettrogramma → dati ricostruiti. Quanta informazione si conserva?",
        "Data → audio → spectrogram → reconstructed data. How much information survives?",
    ),
    "rtw.original": ("Originale", "Original"),
    "rtw.spectrogram": ("Spettrogramma · {mode}", "Spectrogram · {mode}"),
    "rtw.time": ("tempo (s)", "time (s)"),
    "rtw.reconstructed": ("Ricostruita dall'audio", "Reconstructed from audio"),
    "rtw.error": ("Errore assoluto", "Absolute error"),
    "rtw.plots": ("Grafici di confronto", "Comparison plots"),
    "rtw.plots.desc": (
        "I risultati numerici sono descritti nei riquadri sotto i grafici.",
        "The numeric results are described in the boxes below the plots.",
    ),
    "rtw.results": ("Risultati {mode}", "Results {mode}"),
    "mode.hilbert": ("Hilbert", "Hilbert"),
    "mode.sequence": ("sequenza", "sequence"),
    "mode.spectral": ("spettrale", "spectral"),
    "m.corr": ("Correlazione", "Correlation"),
    "m.mean": ("Errore medio", "Mean error"),
    "m.max": ("Errore massimo", "Max error"),
    "btn.listen": ("Ascolta", "Listen"),
    "btn.close": ("Chiudi", "Close"),
    # --- finestra ridimensiona e confronta --------------------------------------
    "rs.window": ("Sonifica – Ridimensiona e confronta", "Sonifica – Resize and compare"),
    "rs.title": ("Ridimensiona e confronta", "Resize and compare"),
    "rs.subtitle": (
        "Riduci la heatmap come un'immagine: graficamente simile, numericamente diversa. Suona ancora uguale?",
        "Shrink the heatmap like an image: visually similar, numerically different. Does it still sound the same?",
    ),
    "rs.rows": ("Righe", "Rows"),
    "rs.cols": ("Colonne", "Columns"),
    "rs.keep": ("Mantieni le proporzioni", "Keep aspect ratio"),
    "rs.method": ("Metodo", "Method"),
    "method.area": ("Media dell'area", "Area average"),
    "method.nearest": ("Campionamento", "Nearest sample"),
    "rs.factor": ("Riduci a 1/{n}", "Reduce to 1/{n}"),
    "rs.original": ("Originale · {rows}×{cols}", "Original · {rows}×{cols}"),
    "rs.resized": ("Ridimensionata · {rows}×{cols}", "Resized · {rows}×{cols}"),
    "rs.track.hilbert": ("Curva di Hilbert: cosa si sente nel tempo", "Hilbert curve: what you hear over time"),
    "rs.track.rows": ("Riga per riga (stessa durata)", "Row by row (same duration)"),
    "rs.time": ("tempo (frazione della durata)", "time (fraction of the duration)"),
    "rs.value": ("valore", "value"),
    "rs.legend.original": ("originale", "original"),
    "rs.legend.resized": ("ridimensionata", "resized"),
    "rs.coh.hilbert": ("Coerenza · curva di Hilbert", "Coherence · Hilbert curve"),
    "rs.coh.rows": ("Coerenza · riga per riga", "Coherence · row by row"),
    "rs.summary": (
        "Da {r0}×{c0} a {r1}×{c1}. Curva di Hilbert: {h}, {hv}. Riga per riga: {w}, {wv}.",
        "From {r0}×{c0} to {r1}×{c1}. Hilbert curve: {h}, {hv}. Row by row: {w}, {wv}.",
    ),
    "btn.play_original": ("Ascolta l'originale", "Play the original"),
    "btn.play_resized": ("Ascolta la ridimensionata", "Play the resized one"),
    "btn.use_resized": ("Apri la ridimensionata", "Open the resized one"),
})
