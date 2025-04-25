# MAX for Home

**Il tuo assistente per la casa, il tuo amico.**  
Gestisci i tuoi dispositivi SystemMax direttamente dal nostro sito o dall’app Home Assistant.

---

## Descrizione

Con MAX puoi:

- **Controllare** da smartphone o PC la tua abitazione in modo facile e sorprendente: registrati e scarica l’app, oppure usa il portale web.  
- **Usare comandi vocali**: MAX non è solo domotica, ma anche un amico con cui parlare e a cui assegnare compiti sui tuoi dispositivi.  
- **Condividere i dispositivi** con chi vuoi: ad esempio, chi possiede un dispositivo **GateMax** per il cancello automatico può concedere l’accesso tramite l’app **MaxLocator**, in modo che il cancello si apra automaticamente al tuo arrivo, senza premere alcun pulsante.

---

## Tipi di dispositivo supportati

| Tipo            | Piattaforma HA | Azioni disponibili                                           |
|-----------------|----------------|--------------------------------------------------------------|
| **Cancello**    | `button`       | APRI (type=22)                                               |
| **Interruttore**| `button`       | TOGGLE (APRI/SPEGNI, type=4)                                 |
| **Termostato**  | `climate`      | • Lettura temperatura corrente (°C)<br>• Lettura umidità (%)<br>• Setpoint target temperature<br>• Comando ACCENDI (type=4) e SPEGNI (type=3)<br>• Modalità AUTO/MANUALE |

---

## Requisiti

- Home Assistant Core ≥ 2025.4  
- Python 3.9+  
- Dipendenze Python: [`httpx`](https://pypi.org/project/httpx/)  

---

## Installazione

1. Clona o copia la cartella `max_for_home` in `config/custom_components/`.  
2. Riavvia Home Assistant.  
3. Vai in **Impostazioni → Dispositivi e servizi → Aggiungi integrazione**.  
4. Cerca **MAX for Home** e inserisci **email**, **password** e **device_code** (codice univoco del tuo dispositivo).

---

## Configurazione

La configurazione avviene tramite **Config Flow** (UI):

```yaml
# Niente da mettere in configuration.yaml!
```

Quando aggiungi l’integrazione, dovrai fornire:

- **Email** e **Password** del tuo account SystemMax.  
- **Device code**: ad esempio `hdh7td8v6`.

Il flow verifica immediatamente il tipo di dispositivo (type=16) e propone le entità corrispondenti.

---

## Utilizzo in Home Assistant

### Cancello (button)

- Entità: `button.cancello_<device_code>`
- Azione: “APRI” invia una richiesta `type=22`.

### Interruttore (button)

- Entità: `button.interruttore_<device_code>`
- Azione: “TOGGLE” invia `type=4` per commutare lo stato.

### Termostato (climate)

- Entità: `climate.thermostat_<device_code>`
- Viene automaticamente interrogato ogni 3 secondi (configurabile con `scan_interval`).
- **Climate card** mostra:
  - Temperatura corrente  
  - Umidità (campo `current_humidity`)  
  - Setpoint target temperature  
  - Stato ON/OFF con pulsante  

**Esempio di Lovelace:**

```yaml
type: thermostat
entity: climate.thermostat_rtcdmBoPVe
name: Termostato Cucina
```

---

## Personalizzazioni

- **Intervallo di polling**  
  Di default viene impostato a 3 s con:

  ```python
  async_add_entities(
    [MaxThermostatEntity(...)],
    update_before_add=False,
    scan_interval=timedelta(seconds=3),
  )
  ```
---

## Struttura dei file

```
custom_components/max_for_home/
├── __init__.py
├── button.py
├── climate.py
├── config_flow.py
├── const.py
└── manifest.json
```

- **button.py**: gateway e interruttore  
- **climate.py**: termostato unico con lettura temp/umidità e comandi  
- **config_flow.py**: wizard UI  
- **const.py**: costanti dominio, endpoint, chiavi di configurazione  
- **manifest.json**: dichiarazione integration metadata  

---

## Contribuire

1. Fai fork del repository.  
2. Crea un branch feature: `git checkout -b feature/tuo-feature`.  
3. Fai commit e push: `git push origin feature/tuo-feature`.  
4. Apri una Pull Request.  

---

## Licenza

MIT License © 2025 SystemMax  

---
