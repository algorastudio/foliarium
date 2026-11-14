#!/usr/bin/env node
// prova_browser.cjs — verifica una postazione della demo con un browser vero.
//
// E' l'unica prova che percorre l'intera catena: proxy, credenziali, pagina,
// WebSocket, schermo remoto. Le altre (curl, psql) ne controllano i pezzi.
//
// Uso:
//   node prova_browser.cjs <indirizzo base> <nome> <password> <cartella esiti>
//   node prova_browser.cjs http://127.0.0.1:18080 prova-a 'la-password' ./esiti
//
// Richiede il pacchetto «playwright» con Chromium. Esce con 0 solo se tutte
// le verifiche passano.

'use strict';

const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const [base, nome, password, cartella] = process.argv.slice(2);
if (!base || !nome || !password || !cartella) {
    console.error('uso: prova_browser.cjs <indirizzo base> <nome> <password> <cartella esiti>');
    process.exit(2);
}

const indirizzo = `${base.replace(/\/$/, '')}/${nome}/`;
const ALTEZZA_BARRA = 36;
const esiti = [];

function registra(descrizione, riuscita, dettaglio) {
    esiti.push(riuscita);
    console.log(`${riuscita ? 'OK      ' : 'FALLITO '} ${descrizione}${dettaglio ? ` — ${dettaglio}` : ''}`);
}

async function finche(condizione, millisecondi) {
    const scadenza = Date.now() + millisecondi;
    let ultimo;
    while (Date.now() < scadenza) {
        ultimo = await condizione();
        if (ultimo.riuscita) {
            return ultimo;
        }
        await new Promise((risolvi) => setTimeout(risolvi, 250));
    }
    return ultimo;
}

// Dimensioni dello schermo remoto (attributi del canvas) e spazio che occupa
// nella pagina.
function misura(pagina) {
    return pagina.evaluate(() => {
        const riquadro = document.getElementById('schermo');
        const canvas = riquadro.querySelector('canvas');
        if (!canvas) {
            return null;
        }
        const occupato = canvas.getBoundingClientRect();
        return {
            remoto: { larghezza: canvas.width, altezza: canvas.height },
            mostrato: { larghezza: occupato.width, altezza: occupato.height },
            riquadro: { larghezza: riquadro.clientWidth, altezza: riquadro.clientHeight },
            richiesta: window.foliariumDemo.dimensioneRichiesta(),
        };
    });
}

function coloriDistinti(pagina) {
    return pagina.evaluate(() => {
        const canvas = document.querySelector('#schermo canvas');
        const contesto = canvas.getContext('2d');
        const colori = new Set();
        for (let colonna = 1; colonna < 24; colonna += 1) {
            for (let riga = 1; riga < 24; riga += 1) {
                const x = Math.floor((canvas.width * colonna) / 24);
                const y = Math.floor((canvas.height * riga) / 24);
                colori.add(contesto.getImageData(x, y, 1, 1).data.slice(0, 3).join(','));
            }
        }
        return colori.size;
    });
}

(async () => {
    fs.mkdirSync(cartella, { recursive: true });
    const browser = await chromium.launch();
    try {
        // 1. Senza credenziali non si entra.
        const anonimo = await browser.newContext();
        const paginaAnonima = await anonimo.newPage();
        const rifiuto = await paginaAnonima.goto(indirizzo).catch(() => null);
        registra('senza credenziali la pagina risponde 401',
                 rifiuto !== null && rifiuto.status() === 401,
                 rifiuto ? `stato ${rifiuto.status()}` : 'nessuna risposta');
        await anonimo.close();

        // 2. Con le credenziali compare lo schermo. Finestra grande: lo
        //    schermo remoto deve coincidere con il riquadro, punto per punto.
        const contesto = await browser.newContext({
            httpCredentials: { username: 'demo', password },
            viewport: { width: 1700, height: 1100 },
        });
        const pagina = await contesto.newPage();
        const errori = [];
        pagina.on('pageerror', (errore) => errori.push(String(errore)));
        await pagina.goto(indirizzo);

        const collegato = await finche(async () => {
            const stato = await pagina.evaluate(() => document.documentElement.dataset.stato);
            return { riuscita: stato === 'connesso', stato };
        }, 60000);
        registra('con le credenziali lo schermo si collega', collegato.riuscita,
                 `stato «${collegato.stato}»${errori.length ? `, errori: ${errori.join(' | ')}` : ''}`);
        if (!collegato.riuscita) {
            throw new Error('collegamento non riuscito: le verifiche successive non hanno senso');
        }

        // 3. Sullo schermo c'e' qualcosa.
        const disegnato = await finche(async () => {
            const colori = await coloriDistinti(pagina);
            return { riuscita: colori >= 4, colori };
        }, 30000);
        registra('lo schermo mostra il programma (non un colore uniforme)',
                 disegnato.riuscita, `${disegnato.colori} colori nei punti campionati`);

        // 4. Finestra grande: schermo remoto grande quanto il riquadro.
        const grande = await finche(async () => {
            const m = await misura(pagina);
            const riuscita = m !== null &&
                Math.abs(m.remoto.larghezza - m.riquadro.larghezza) <= 2 &&
                Math.abs(m.remoto.altezza - m.riquadro.altezza) <= 2;
            return { riuscita, m };
        }, 15000);
        registra('finestra 1700x1100: lo schermo remoto coincide con il riquadro',
                 grande.riuscita && grande.m.riquadro.altezza === 1100 - ALTEZZA_BARRA,
                 grande.m ? `remoto ${grande.m.remoto.larghezza}x${grande.m.remoto.altezza}, ` +
                            `riquadro ${grande.m.riquadro.larghezza}x${grande.m.riquadro.altezza}` : 'nessun canvas');
        await pagina.screenshot({ path: path.join(cartella, `schermo-${nome}.png`) });

        // 5. Finestra piccola: lo schermo remoto non scende sotto il minimo
        //    e viene rimpicciolito fino a stare nel riquadro, riempiendolo.
        await pagina.setViewportSize({ width: 1000, height: 640 });
        const piccola = await finche(async () => {
            const m = await misura(pagina);
            if (m === null) {
                return { riuscita: false, m };
            }
            const minimo = await pagina.evaluate(() => window.foliariumDemo.minimo);
            const riuscita =
                m.riquadro.larghezza === 1000 &&
                Math.abs(m.remoto.larghezza - m.richiesta.larghezza) <= 2 &&
                Math.abs(m.remoto.altezza - m.richiesta.altezza) <= 2 &&
                m.remoto.larghezza >= minimo.larghezza &&
                m.remoto.altezza >= minimo.altezza &&
                m.mostrato.larghezza <= m.riquadro.larghezza + 1 &&
                m.mostrato.altezza <= m.riquadro.altezza + 1 &&
                m.mostrato.larghezza >= m.riquadro.larghezza * 0.97;
            return { riuscita, m };
        }, 15000);
        registra('finestra 1000x640: schermo remoto al minimo, rimpicciolito nel riquadro',
                 piccola.riuscita,
                 piccola.m ? `remoto ${piccola.m.remoto.larghezza}x${piccola.m.remoto.altezza}, ` +
                             `mostrato ${Math.round(piccola.m.mostrato.larghezza)}x${Math.round(piccola.m.mostrato.altezza)}, ` +
                             `riquadro ${piccola.m.riquadro.larghezza}x${piccola.m.riquadro.altezza}` : 'nessun canvas');
        await pagina.screenshot({ path: path.join(cartella, `schermo-${nome}-piccolo.png`) });

        // 6. La pagina dei file esportati e' raggiungibile dal collegamento.
        const collegamento = await pagina.getAttribute('header nav a', 'href');
        const file = await contesto.request.get(new URL(collegamento, indirizzo).href);
        const testoFile = await file.text();
        registra('la pagina «File esportati» risponde',
                 file.status() === 200 && testoFile.includes('File esportati'),
                 `stato ${file.status()}`);

        await contesto.close();
    } catch (errore) {
        registra('esecuzione della prova', false, String(errore.message || errore));
    } finally {
        await browser.close();
    }

    const superate = esiti.filter(Boolean).length;
    console.log(`${superate}/${esiti.length} verifiche superate`);
    process.exit(superate === esiti.length && esiti.length >= 6 ? 0 : 1);
})();
