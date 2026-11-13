// schermo.js — porta nel browser lo schermo della postazione.
//
// Di noVNC si usa solo il client (core/rfb.js): la pagina e' nostra, cosi' il
// cliente vede «Foliarium — Demo» e non l'interfaccia di un prodotto VNC.
//
// L'indirizzo del WebSocket non e' fisso: contiene un token che il proxy
// consegna in sessione.json, cioe' solo a chi ha gia' superato la richiesta
// di credenziali. Vedi la funzione «frammento» in demo.sh.

import RFB from './novnc/core/rfb.js';

// Dimensione minima dello schermo remoto. Sotto i 960 pixel di altezza la
// pagina iniziale di Foliarium comprime i pulsanti delle azioni rapide fino
// a renderli illeggibili: se la finestra del browser e' piu' piccola, lo
// schermo remoto resta a questa misura e viene rimpicciolito in proporzione,
// invece di restringersi davvero.
const LARGHEZZA_MINIMA = 1280;
const ALTEZZA_MINIMA = 960;

const ATTESA_RICONNESSIONE_MS = 5000;

const radice = document.documentElement;
const riquadro = document.getElementById('schermo');
const testoStato = document.getElementById('stato');
const avviso = document.getElementById('avviso');
const avvisoTitolo = document.getElementById('avviso-titolo');
const avvisoNota = document.getElementById('avviso-nota');
const pulsanteRiconnetti = document.getElementById('riconnetti');
const pulsanteSchermoIntero = document.getElementById('schermo-intero');

let rfb = null;
let timerRiconnessione = null;

function imposta(stato, testo) {
    radice.dataset.stato = stato;
    testoStato.textContent = testo;
}

// Dimensione da chiedere al server: quella del riquadro, ingrandita quanto
// basta a raggiungere il minimo mantenendo le proporzioni, cosi' una volta
// rimpicciolita riempie il riquadro senza bande vuote.
function dimensioneRichiesta() {
    const larghezza = Math.max(1, riquadro.clientWidth);
    const altezza = Math.max(1, riquadro.clientHeight);
    const fattore = Math.max(1, LARGHEZZA_MINIMA / larghezza, ALTEZZA_MINIMA / altezza);
    return {
        larghezza: Math.round(larghezza * fattore),
        altezza: Math.round(altezza * fattore),
    };
}

// noVNC sa chiedere al server solo la dimensione esatta del riquadro. Per
// imporre un minimo si sostituisce, su questa sola connessione, il metodo che
// invia la richiesta. Usa nomi interni di noVNC 1.3 (quello del pacchetto
// Debian nell'immagine): se in una versione diversa non ci fossero, resta il
// comportamento originale, cioe' schermo grande quanto il riquadro.
function imponiDimensioneMinima(connessione) {
    const messaggi = RFB.messages;
    if (typeof connessione._requestRemoteResize !== 'function' ||
        !messaggi || typeof messaggi.setDesktopSize !== 'function') {
        return;
    }
    connessione._requestRemoteResize = function () {
        clearTimeout(this._resizeTimeout);
        this._resizeTimeout = null;
        if (!this._resizeSession || this._viewOnly || !this._supportsSetDesktopSize) {
            return;
        }
        const richiesta = dimensioneRichiesta();
        messaggi.setDesktopSize(this._sock, richiesta.larghezza, richiesta.altezza,
                                this._screenID, this._screenFlags);
    };
}

async function indirizzoSchermo() {
    const risposta = await fetch('sessione.json', { cache: 'no-store', credentials: 'same-origin' });
    if (!risposta.ok) {
        throw new Error(`sessione.json: ${risposta.status}`);
    }
    const sessione = await risposta.json();
    const indirizzo = new URL(sessione.ws, window.location.href);
    indirizzo.protocol = indirizzo.protocol === 'https:' ? 'wss:' : 'ws:';
    return indirizzo.href;
}

function interrotto(nota) {
    rfb = null;
    imposta('disconnesso', 'Collegamento interrotto');
    avvisoTitolo.textContent = 'Collegamento interrotto';
    avvisoNota.textContent = nota;
    avviso.hidden = false;
    clearTimeout(timerRiconnessione);
    timerRiconnessione = setTimeout(collega, ATTESA_RICONNESSIONE_MS);
}

async function collega() {
    clearTimeout(timerRiconnessione);
    if (rfb) {
        return;
    }
    imposta('connessione', 'Collegamento in corso…');

    let indirizzo;
    try {
        indirizzo = await indirizzoSchermo();
    } catch (errore) {
        interrotto('La postazione non risponde. Nuovo tentativo fra pochi secondi.');
        return;
    }

    const connessione = new RFB(riquadro, indirizzo, { shared: true });
    rfb = connessione;
    imponiDimensioneMinima(connessione);
    connessione.scaleViewport = true;
    connessione.resizeSession = true;
    connessione.focusOnClick = true;
    connessione.background = '#eef0f6';

    connessione.addEventListener('connect', () => {
        avviso.hidden = true;
        imposta('connesso', 'Collegato');
        connessione.focus();
    });
    connessione.addEventListener('disconnect', () => {
        if (rfb === connessione) {
            interrotto('Nuovo tentativo fra pochi secondi.');
        }
    });
}

pulsanteRiconnetti.addEventListener('click', () => {
    avviso.hidden = true;
    collega();
});

pulsanteSchermoIntero.addEventListener('click', () => {
    if (document.fullscreenElement) {
        document.exitFullscreen();
    } else if (radice.requestFullscreen) {
        radice.requestFullscreen().catch(() => {});
    }
});
document.addEventListener('fullscreenchange', () => {
    pulsanteSchermoIntero.textContent =
        document.fullscreenElement ? 'Esci da schermo intero' : 'Schermo intero';
    if (rfb) {
        rfb.focus();
    }
});

// Per la prova automatica (prova_browser.cjs).
window.foliariumDemo = {
    minimo: { larghezza: LARGHEZZA_MINIMA, altezza: ALTEZZA_MINIMA },
    dimensioneRichiesta,
};

collega();
