# Mobile Voice Gateway Setup for Stress Dialogue

During nocturnal waking, acute emotional friction, or sympathetic exhaustion, typing paragraphs on a mobile keyboard exacerbates cognitive friction and rumination. The mobile voice gateway enables the user to speak naturally via short voice notes over WhatsApp, Telegram, or Signal.

The coach evaluates cognitive appraisal, applies 3rd-person observer distancing, and responds with a calming voice note plus a 1-line text note containing **exactly one** tactical micro-action.

---

## 1. Sovereignty Boundary & Threat Model

Voice notes contain sensitive health and personal disclosures. When deploying the voice gateway, respect the sovereignty boundary:

| Layer | Sovereign Stack (Default) | Cloud Stack (Convenience) | Privacy Implications |
|---|---|---|---|
| **STT (Speech-to-Text)** | `faster-whisper` (local CPU/GPU) | Gemini 3.8 Flash Audio | Cloud STT transmits acoustic biometrics (voiceprints, emotional cadence, ambient sounds) to third-party infrastructure. |
| **TTS (Text-to-Speech)** | `piper-tts` (local CPU) | Gemini Flash TTS (`gemini-3.8-flash-tts`) | Local TTS ensures zero speech generation requests leave the box. |
| **Messaging Channel** | Signal (`signal-cli`) or WhatsApp (Baileys) | Telegram Bot API | Standard Telegram Bot API unencrypts voice notes on Telegram servers. Sovereign deployment requires local Bot API or E2EE bridges. |

---

## 2. Ingress Attachment Spooling & RAM-Disk Discipline

Deleting the scratch audio file inside Hermes alone is insufficient if the messaging bridge spools media to disk out-of-band:

- **Signal (`signal-cli`):** Default installs write attachments to `~/.local/share/signal-cli/attachments/` and do not delete them automatically.
- **WhatsApp (Baileys):** Bridge processes write incoming audio buffers to temporary directories.

### Hardening: Ephemeral RAM-Disk Staging

Mount messaging bridge attachments and Hermes voice scratch directories to RAM (`tmpfs`), ensuring raw voice recordings evaporate on reboot and never touch persistent disk blocks:

```bash
# 1. Create RAM-disk scratch path in /dev/shm
mkdir -p /dev/shm/hermes-audio
chmod 700 /dev/shm/hermes-audio

# 2. Configure systemd tmpfiles.d auto-purge (e.g. 15-minute cleanup)
cat << 'EOF' | sudo tee /etc/tmpfiles.d/hermes-audio.conf
d /dev/shm/hermes-audio 0700 ubuntu ubuntu 15m
EOF
```

---

## 3. Hermes Configuration

Configure voice settings in `~/.hermes/config.yaml`:

```yaml
# Skill configuration
stress:
  voice_enabled: true
  voice_scratch_dir: "/dev/shm/hermes-audio"
  max_turns: 3
  crisis_contact: "988 (US/Canada), 112 (Europe), 116 123 (UK)"

# Audio runtime options (Sovereign local pipeline)
voice:
  stt:
    provider: "whisper"
    model: "faster-whisper-medium"
    device: "cpu"
    compute_type: "int8"
  tts:
    provider: "piper"
    voice: "en_US-lessac-medium"
    socket: "/run/piper/piper.sock"
```

For cloud-assisted TTS (high naturalness over mobile messaging):

```bash
hermes config set tts.provider gemini
hermes config set tts.gemini.model gemini-3.8-flash-tts
hermes config set tts.gemini.voice Kore
```

---

## 4. Voice Safety Interlock & Acoustic Fail-Safe

Inbound voice audio introduces unique acoustic failure modes that require fail-safe handling:

1. **Acoustic Drift Under Distress:**
   Users experiencing acute panic or sobbing may whisper or slur words, increasing transcription error rates. If audio duration is significant but Whisper yields an empty transcript or low confidence (`is_low_confidence: true`), the engine must **fail safe**: emit a compassionate grounding prompt and provide emergency crisis helpline resources directly.
2. **Guaranteed Scratch Purge:**
   Audio files must be unlinked in a `finally` block via `ephemeral_audio_scratch()` immediately post-transcription.
3. **Zero Long-Term Memory Persistence on Crisis:**
   If `CRISIS_HALT` triggers, emergency hotline resources are delivered immediately, and zero conversation text, audio fragments, or summaries are persisted to disk or `MEMORY.md`.

---

## 5. Anti-Rumination Enforcement in Voice

Voice check-ins must not degrade into open-ended, 45-minute stream-of-consciousness venting. The anti-rumination circuit breaker is strictly enforced:

- **Turn Cap:** $\le 3$ total conversational turns (`stress.max_turns`).
- **Turn 1 (Validation):** Warm acknowledgement of somatic overwhelm; 3rd-person observer cognitive distance.
- **Turn 2 (Grounding):** Sensory check-in or single clarifying question.
- **Turn 3 (Commitment):** Exactly ONE tactical micro-action (e.g. physiological sigh, 60-minute focus boundary, or early sleep window).
- **Session Close:** Session terminates; coach stays silent until next morning's recovery verification.
